"""
Roll out a local (base + LoRA adapter) model against the GENESIS MCP server.

This script is the missing "use it" step after training:
- Loads Qwen2.5-3B-Instruct (or any causal LM) + a PEFT adapter directory
- Runs N episodes by calling GENESIS tools (reset/get_daily_briefing/make_decision/get_reward)
- Leaves results in the server's `sessions.pkl`
- Optionally exports the Founder Genome card for the chosen `model_id`
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
import uuid
from typing import Any, Dict, Tuple


def _safe_json_loads(text: str) -> Dict[str, Any] | None:
    text = (text or "").strip()
    if not text:
        return None
    # Common pattern: model prints extra prose, then JSON. Grab last {...}.
    if not text.startswith("{"):
        start = text.rfind("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1].strip()
    try:
        parsed = json.loads(text)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def _build_ceo_prompt(briefing: Dict[str, Any]) -> str:
    # Keep prompt short and robust: the environment is the source of truth.
    role_obs = briefing.get("role_observation") or {}
    day = briefing.get("day")
    events = briefing.get("world_events") or []
    crises = briefing.get("active_crises") or []

    obs_snippet = json.dumps(role_obs, ensure_ascii=False)[:1800]
    events_snippet = json.dumps(events, ensure_ascii=False)[:800]
    crises_snippet = json.dumps(crises, ensure_ascii=False)[:800]

    return (
        "You are the CEO agent in the GENESIS startup simulation.\n"
        "You MUST respond with a single JSON object with keys:\n"
        '- decision_type: "strategic" or "tactical"\n'
        "- decision: a concise action to take now\n"
        "- reasoning: short justification\n\n"
        f"Day: {day}\n"
        f"World events: {events_snippet}\n"
        f"Active crises: {crises_snippet}\n"
        f"Role observation (partial): {obs_snippet}\n\n"
        "Return ONLY the JSON object, no markdown.\n"
    )


def _load_model(base_model: str, adapter_path: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    device_map = "auto" if torch.cuda.is_available() else None
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        device_map=device_map,
        torch_dtype=dtype,
        low_cpu_mem_usage=True,
    )
    model = PeftModel.from_pretrained(model, adapter_path)
    model.eval()
    return model, tokenizer


def _generate_decision(model, tokenizer, prompt: str, seed: int, max_new_tokens: int) -> Tuple[str, Dict[str, Any]]:
    import torch

    random.seed(seed)
    torch.manual_seed(seed)

    inputs = tokenizer(prompt, return_tensors="pt")
    if hasattr(model, "device") and inputs.get("input_ids") is not None:
        try:
            inputs = {k: v.to(model.device) for k, v in inputs.items()}
        except Exception:
            pass

    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.95,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    completion = tokenizer.decode(out[0][inputs["input_ids"].shape[-1] :], skip_special_tokens=True).strip()
    parsed = _safe_json_loads(completion) or {}
    return completion, parsed


def main():
    parser = argparse.ArgumentParser(description="Roll out a local adapter model in GENESIS")
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--adapter", default="models/genesis_final", help="Path to PEFT adapter dir")
    parser.add_argument("--server", default=os.environ.get("GENESIS_URL", "http://127.0.0.1:7860"))
    parser.add_argument("--model-id", default="genesis_final_200")
    parser.add_argument("--difficulty", type=int, default=1, choices=[1, 2, 3, 4, 5])
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--seed-start", type=int, default=1000)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument("--export-genome", action="store_true", help="Call export_founder_genome at end")
    args = parser.parse_args()

    adapter_path = os.path.abspath(args.adapter)
    if not os.path.isdir(adapter_path):
        raise SystemExit(f"Adapter path not found: {adapter_path}")

    print(f"Loading model: {args.base_model}")
    print(f"Loading adapter: {adapter_path}")
    model, tokenizer = _load_model(args.base_model, adapter_path)

    from client import GenesisEnv

    env = GenesisEnv(base_url=args.server).sync()
    env.async_client.use_production_mode = True

    try:
        rewards: list[float] = []
        for ep_idx in range(args.episodes):
            episode_id = f"inf-{uuid.uuid4().hex[:10]}"
            seed = args.seed_start + ep_idx

            env.call_tool(
                "reset",
                episode_id=episode_id,
                difficulty=args.difficulty,
                seed=seed,
                model_id=args.model_id,
                model_provider="local",
                model_version="peft_adapter",
            )

            for _ in range(args.days):
                briefing = env.call_tool("get_daily_briefing", episode_id=episode_id, agent_role="ceo")
                if briefing.get("is_done"):
                    break

                prompt = _build_ceo_prompt(briefing)
                completion, parsed = _generate_decision(
                    model=model,
                    tokenizer=tokenizer,
                    prompt=prompt,
                    seed=seed,
                    max_new_tokens=args.max_new_tokens,
                )

                decision_type = str(parsed.get("decision_type") or "tactical").lower()
                if decision_type not in {"strategic", "tactical"}:
                    decision_type = "tactical"

                decision = parsed.get("decision")
                if not isinstance(decision, str) or not decision.strip():
                    decision = completion[:300] if completion else "Continue with current plan and monitor risk."

                reasoning = parsed.get("reasoning")
                if not isinstance(reasoning, str) or not reasoning.strip():
                    reasoning = "Model-generated decision."

                env.call_tool(
                    "make_decision",
                    episode_id=episode_id,
                    agent_role="ceo",
                    decision_type=decision_type,
                    decision=decision[:800],
                    reasoning=reasoning[:1200],
                )

                # Small delay keeps local CPU-only runs responsive.
                time.sleep(0.05)

            r = env.call_tool("get_reward", episode_id=episode_id)
            reward = float(r.get("reward", 0.0))
            rewards.append(reward)
            print(f"[{ep_idx+1:02d}/{args.episodes}] episode_id={episode_id} seed={seed} reward={reward:.4f}")

        if rewards:
            avg = sum(rewards) / len(rewards)
            print(f"\nDone. avg_reward={avg:.4f} best={max(rewards):.4f} worst={min(rewards):.4f}")

        if args.export_genome:
            res = env.call_tool("export_founder_genome", model_id=args.model_id, difficulty=args.difficulty)
            if isinstance(res, dict) and res.get("artifacts"):
                print(f"Exported genome artifacts: {res['artifacts']}")
            else:
                print(f"Genome export response: {res}")

    finally:
        env.close()


if __name__ == "__main__":
    main()

