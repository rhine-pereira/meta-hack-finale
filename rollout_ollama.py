"""
Roll out an Ollama model against the GENESIS MCP server.

Use this when your candidate models live in Ollama (e.g. deepseek-coder, mistral, llama)
and you want to benchmark / export Founder Genomes without downloading HF weights.

Requires:
- Ollama running locally (default http://127.0.0.1:11434)
- GENESIS server running (default http://127.0.0.1:7860)
"""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from typing import Any, Dict, Optional, Tuple

import requests


def _safe_json_obj(text: str) -> Optional[Dict[str, Any]]:
    text = (text or "").strip()
    if not text:
        return None
    if not text.startswith("{"):
        start = text.rfind("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1].strip()
    try:
        obj = json.loads(text)
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _build_ceo_prompt(briefing: Dict[str, Any]) -> str:
    role_obs = briefing.get("role_observation") or {}
    day = briefing.get("day")
    events = briefing.get("world_events") or []
    crises = briefing.get("active_crises") or []

    # Keep it short enough for Ollama defaults but still grounded in state.
    return (
        "You are the CEO agent in the GENESIS startup simulation.\n"
        "Return ONLY a JSON object with keys:\n"
        '- decision_type: "strategic" or "tactical"\n'
        "- decision: what to do now\n"
        "- reasoning: why\n\n"
        f"Day: {day}\n"
        f"World events: {json.dumps(events, ensure_ascii=False)[:800]}\n"
        f"Active crises: {json.dumps(crises, ensure_ascii=False)[:800]}\n"
        f"Role observation: {json.dumps(role_obs, ensure_ascii=False)[:1800]}\n"
    )


def ollama_generate(
    base_url: str,
    model: str,
    prompt: str,
    temperature: float = 0.7,
    top_p: float = 0.95,
) -> str:
    """
    Calls Ollama HTTP API (/api/generate). Uses non-streaming for simplicity.
    """
    resp = requests.post(
        f"{base_url}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
            },
        },
        timeout=300,
    )
    resp.raise_for_status()
    data = resp.json()
    return (data.get("response") or "").strip()


def main():
    parser = argparse.ArgumentParser(description="Roll out an Ollama model in GENESIS")
    parser.add_argument("--ollama-model", required=True, help='Ollama model name, e.g. "deepseek-coder:6.7b"')
    parser.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--server", default=os.environ.get("GENESIS_URL", "http://127.0.0.1:7860"))
    parser.add_argument("--model-id", default=None, help="GENESIS model_id tag used for genomes (defaults to ollama model)")
    parser.add_argument("--difficulty", type=int, default=1, choices=[1, 2, 3, 4, 5])
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--seed-start", type=int, default=2000)
    parser.add_argument("--export-genome", action="store_true")
    args = parser.parse_args()

    model_id = args.model_id or args.ollama_model.replace(":", "_").replace("/", "_")

    from client import GenesisEnv

    env = GenesisEnv(base_url=args.server).sync()
    env.async_client.use_production_mode = True

    try:
        rewards: list[float] = []
        for ep_idx in range(args.episodes):
            episode_id = f"oll-{uuid.uuid4().hex[:10]}"
            seed = args.seed_start + ep_idx

            env.call_tool(
                "reset",
                episode_id=episode_id,
                difficulty=args.difficulty,
                seed=seed,
                model_id=model_id,
                model_provider="ollama",
                model_version=args.ollama_model,
            )

            for _ in range(args.days):
                briefing = env.call_tool("get_daily_briefing", episode_id=episode_id, agent_role="ceo")
                if briefing.get("is_done"):
                    break

                prompt = _build_ceo_prompt(briefing)
                completion = ollama_generate(args.ollama_url, args.ollama_model, prompt)
                parsed = _safe_json_obj(completion) or {}

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

                time.sleep(0.05)

            r = env.call_tool("get_reward", episode_id=episode_id)
            reward = float(r.get("reward", 0.0))
            rewards.append(reward)
            print(f"[{ep_idx+1:02d}/{args.episodes}] episode_id={episode_id} seed={seed} reward={reward:.4f}")

        if rewards:
            avg = sum(rewards) / len(rewards)
            print(f"\nDone. model_id={model_id} avg_reward={avg:.4f} best={max(rewards):.4f} worst={min(rewards):.4f}")

        if args.export_genome:
            res = env.call_tool("export_founder_genome", model_id=model_id, difficulty=args.difficulty)
            if isinstance(res, dict) and res.get("artifacts"):
                print(f"Exported genome artifacts: {res['artifacts']}")
            else:
                print(f"Genome export response: {res}")

    finally:
        env.close()


if __name__ == "__main__":
    main()

