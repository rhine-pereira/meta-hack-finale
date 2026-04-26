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
from requests.exceptions import ReadTimeout, ConnectionError as RequestsConnectionError


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


ROLE_INSTRUCTIONS = {
    "ceo": (
        "You are the CEO agent in the GENESIS startup simulation.\n"
        "Your tools: make_decision, write_company_brain, read_company_brain, "
        "analyze_market, negotiate_with_investor, pivot_company, hire_candidate, fire_employee.\n"
        "IMPORTANT: Regularly use write_company_brain to record strategic decisions, "
        "market insights, and long-term plans. This is critical for company health scoring.\n"
        "Return ONLY a JSON object:\n"
        '{"tool": "<tool_name>", "args": {<arguments>}}\n\n'
        "Example brain write: "
        '{"tool": "write_company_brain", "args": {"key": "strategy_q1", "value": '
        '"Focus on enterprise sales for Q1: target 5 new logos at $10k ARR each..."}}\n\n'
        "Example decision: "
        '{"tool": "make_decision", "args": {"decision_type": "strategic", '
        '"decision": "Pursue Series A in 90 days", "reasoning": "Runway at 120 days, need capital"}}\n\n'
    ),
    "cto": (
        "You are the CTO agent in the GENESIS startup simulation.\n"
        "Your tools: make_decision, build_feature, write_company_brain, check_team_morale, "
        "hire_candidate, fire_employee.\n"
        "IMPORTANT: Build features regularly and write technical decisions to company_brain.\n"
        "Return ONLY a JSON object:\n"
        '{"tool": "<tool_name>", "args": {<arguments>}}\n\n'
        "Example feature build: "
        '{"tool": "build_feature", "args": {"name": "API Rate Limiting", '
        '"complexity": "medium", "engineers": 2}}\n\n'
        "Example brain write: "
        '{"tool": "write_company_brain", "args": {"key": "tech_roadmap", '
        '"value": "Q1 priorities: SSO, API v2, reduce tech_debt by 20%..."}}\n\n'
    ),
    "sales": (
        "You are the Head of Sales agent in the GENESIS startup simulation.\n"
        "Your tools: make_decision, analyze_market, write_company_brain.\n"
        "IMPORTANT: Analyze market regularly and record go-to-market insights in company_brain.\n"
        "Return ONLY a JSON object:\n"
        '{"tool": "<tool_name>", "args": {<arguments>}}\n\n'
        "Example: "
        '{"tool": "write_company_brain", "args": {"key": "gtm_strategy", '
        '"value": "Target mid-market B2B: 50-200 employees, SaaS verticals, US+EU..."}}\n\n'
    ),
    "people": (
        "You are the Head of People agent in the GENESIS startup simulation.\n"
        "Your tools: make_decision, check_team_morale, hire_candidate, fire_employee, "
        "handle_personal_crisis, write_company_brain.\n"
        "IMPORTANT: Monitor morale, handle crises quickly, record hiring plans in company_brain.\n"
        "Return ONLY a JSON object:\n"
        '{"tool": "<tool_name>", "args": {<arguments>}}\n\n'
        "Example: "
        '{"tool": "write_company_brain", "args": {"key": "people_ops", '
        '"value": "Hiring plan: 2 senior engineers by day 60, 1 sales rep by day 90..."}}\n\n'
    ),
    "cfo": (
        "You are the CFO agent in the GENESIS startup simulation.\n"
        "Your tools: make_decision, check_bank_balance, negotiate_with_investor, "
        "write_company_brain.\n"
        "IMPORTANT: Track cash runway carefully and record financial model in company_brain.\n"
        "Return ONLY a JSON object:\n"
        '{"tool": "<tool_name>", "args": {<arguments>}}\n\n'
        "Example: "
        '{"tool": "write_company_brain", "args": {"key": "financial_model", '
        '"value": "Burn: $5k/day. At current growth, need $2M raise by day 90 for 12mo runway..."}}\n\n'
    ),
}

# Rotate strategy so each role writes different brain keys on different days
ROLE_BRAIN_KEYS = {
    "ceo": ["strategy_overview", "series_a_plan", "competitive_response", "pivot_criteria", "board_update"],
    "cto": ["tech_roadmap", "debt_reduction_plan", "feature_priorities", "engineering_culture", "infra_decisions"],
    "sales": ["gtm_strategy", "icp_definition", "pricing_strategy", "customer_feedback", "market_analysis"],
    "people": ["people_ops", "hiring_plan", "morale_initiatives", "performance_framework", "culture_values"],
    "cfo": ["financial_model", "burn_rate_analysis", "fundraising_timeline", "unit_economics", "investor_updates"],
}


def _build_role_prompt(role: str, briefing: Dict[str, Any], day_in_episode: int) -> str:
    role_obs = briefing.get("role_observation") or {}
    day = briefing.get("day")
    events = briefing.get("world_events") or []
    crises = briefing.get("active_crises") or []

    instructions = ROLE_INSTRUCTIONS.get(role, ROLE_INSTRUCTIONS["ceo"])

    # Suggest a brain key to write on this day so the model rotates coverage
    brain_keys = ROLE_BRAIN_KEYS.get(role, ROLE_BRAIN_KEYS["ceo"])
    suggested_key = brain_keys[day_in_episode % len(brain_keys)]

    brain_hint = (
        f"\nToday's suggested brain key to update: '{suggested_key}' "
        f"(write a substantive strategic note ≥ 60 characters).\n"
        f"Alternate with make_decision/build_feature every other day.\n"
    )

    return (
        f"{instructions}"
        f"Day: {day}\n"
        f"World events: {json.dumps(events, ensure_ascii=False)[:600]}\n"
        f"Active crises: {json.dumps(crises, ensure_ascii=False)[:600]}\n"
        f"Role observation: {json.dumps(role_obs, ensure_ascii=False)[:1400]}\n"
        f"{brain_hint}"
    )


def _build_ceo_prompt(briefing: Dict[str, Any]) -> str:
    """Legacy single-role prompt kept for backward compatibility."""
    return _build_role_prompt("ceo", briefing, day_in_episode=0)


def ollama_generate(
    base_url: str,
    model: str,
    prompt: str,
    temperature: float = 0.7,
    top_p: float = 0.95,
    timeout_s: int = 300,
    max_tokens: Optional[int] = 256,
    num_ctx: Optional[int] = 4096,
    retries: int = 2,
) -> str:
    """
    Calls Ollama HTTP API (/api/generate). Uses non-streaming for simplicity.
    """
    url = f"{base_url}/api/generate"

    # Retry strategy: first try normal; if it times out, retry with shorter output.
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        effective_max = max_tokens
        effective_timeout = timeout_s
        if attempt >= 1:
            # Make retries more likely to return quickly
            effective_timeout = max(timeout_s, 900)
            if effective_max is None:
                effective_max = 128
            else:
                effective_max = max(64, int(effective_max * 0.6))

        options: Dict[str, Any] = {"temperature": temperature, "top_p": top_p}
        if effective_max is not None:
            options["num_predict"] = int(effective_max)
        if num_ctx is not None:
            options["num_ctx"] = int(num_ctx)

        try:
            resp = requests.post(
                url,
                json={"model": model, "prompt": prompt, "stream": False, "options": options},
                timeout=effective_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return (data.get("response") or "").strip()
        except (ReadTimeout, RequestsConnectionError, requests.HTTPError) as e:
            last_err = e
            time.sleep(1.0 + attempt * 0.5)

    raise last_err if last_err else RuntimeError("Ollama request failed with unknown error")


ROLE_TOOL_PERMISSIONS = {
    "ceo":    {"make_decision", "write_company_brain", "read_company_brain",
               "analyze_market", "send_message", "pivot_company",
               "check_bank_balance", "negotiate_with_investor",
               "hire_candidate", "fire_employee"},
    "cto":    {"make_decision", "write_company_brain", "read_company_brain",
               "build_feature", "send_message", "check_team_morale",
               "hire_candidate", "fire_employee"},
    "sales":  {"make_decision", "write_company_brain", "read_company_brain",
               "analyze_market", "send_message"},
    "people": {"make_decision", "write_company_brain", "read_company_brain",
               "check_team_morale", "send_message",
               "hire_candidate", "fire_employee", "handle_personal_crisis"},
    "cfo":    {"make_decision", "write_company_brain", "read_company_brain",
               "check_bank_balance", "send_message", "negotiate_with_investor"},
}

ROLES_IN_ORDER = ["ceo", "cto", "cfo", "people", "sales"]


def _dispatch_tool_call(
    env,
    episode_id: str,
    role: str,
    completion: str,
    briefing: Dict[str, Any],
    day_in_episode: int,
) -> None:
    """
    Parse completion as a generic tool call JSON and dispatch it.
    Falls back to make_decision if the output is not a valid tool call
    or the tool is not permitted for this role.
    """
    parsed = _safe_json_obj(completion) or {}
    allowed = ROLE_TOOL_PERMISSIONS.get(role, set())

    tool_name = str(parsed.get("tool") or "").strip()
    tool_args = parsed.get("args") or {}

    # Legacy decision-only format (old CEO prompts): {"decision_type": ..., "decision": ..., "reasoning": ...}
    if not tool_name and "decision" in parsed:
        tool_name = "make_decision"
        tool_args = {
            "decision_type": str(parsed.get("decision_type") or "tactical").lower(),
            "decision": str(parsed.get("decision") or completion[:300]),
            "reasoning": str(parsed.get("reasoning") or "Model-generated."),
        }

    if not tool_name or tool_name not in allowed:
        # Fallback: either write_company_brain or make_decision alternating
        brain_keys = ROLE_BRAIN_KEYS.get(role, ROLE_BRAIN_KEYS["ceo"])
        if day_in_episode % 2 == 0:
            tool_name = "write_company_brain"
            key = brain_keys[day_in_episode % len(brain_keys)]
            # Use the raw completion text as the brain value if it's substantial
            value = completion.strip() if len(completion.strip()) > 50 else (
                f"Day {briefing.get('day', '?')} update: monitoring {key.replace('_', ' ')} "
                f"and adjusting strategy based on latest observations."
            )
            tool_args = {"key": key, "value": value[:1000]}
        else:
            tool_name = "make_decision"
            tool_args = {
                "decision_type": "tactical",
                "decision": completion[:300] if completion.strip() else "Continue current plan and monitor risks.",
                "reasoning": "Model-generated action.",
            }

    # Validate tool args types
    if tool_name == "make_decision":
        tool_args.setdefault("decision_type", "tactical")
        tool_args.setdefault("decision", "Continue current plan.")
        tool_args.setdefault("reasoning", "Model-generated.")
        dt = str(tool_args.get("decision_type") or "tactical").lower()
        if dt not in {"strategic", "tactical"}:
            tool_args["decision_type"] = "tactical"
        tool_args["decision"] = str(tool_args.get("decision") or "")[:800]
        tool_args["reasoning"] = str(tool_args.get("reasoning") or "")[:1200]
    elif tool_name == "write_company_brain":
        tool_args.setdefault("key", "notes")
        tool_args.setdefault("value", "No content provided.")
        tool_args["key"] = str(tool_args["key"])[:80]
        tool_args["value"] = str(tool_args["value"])[:2000]
    elif tool_name == "build_feature":
        tool_args.setdefault("name", "Feature")
        tool_args.setdefault("complexity", "low")
        tool_args.setdefault("engineers", 1)
        if str(tool_args.get("complexity", "")).lower() not in {"low", "medium", "high"}:
            tool_args["complexity"] = "low"
        tool_args["engineers"] = max(1, min(int(tool_args.get("engineers") or 1), 5))

    try:
        env.call_tool(tool_name, episode_id=episode_id, agent_role=role, **tool_args)
    except Exception as exc:
        # Invalid call — silent fallback (same as training)
        _ = exc


def main():
    parser = argparse.ArgumentParser(description="Roll out an Ollama model in GENESIS")
    parser.add_argument("--ollama-model", required=True, help='Ollama model name, e.g. "deepseek-coder:6.7b"')
    parser.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--server", default=os.environ.get("GENESIS_URL", "http://127.0.0.1:7860"))
    parser.add_argument("--model-id", default=None, help="GENESIS model_id tag used for genomes (defaults to ollama model)")
    parser.add_argument("--difficulty", type=int, default=1, choices=[1, 2, 3, 4, 5])
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--days", type=int, default=60,
                        help="Days per episode (default 60; use ≥90 for Series A signal).")
    parser.add_argument("--seed-start", type=int, default=2000)
    parser.add_argument("--ollama-timeout", type=int, default=900, help="HTTP timeout per generation (seconds).")
    parser.add_argument("--ollama-retries", type=int, default=2, help="Retries on timeout/connection errors.")
    parser.add_argument("--max-tokens", type=int, default=256, help="Max tokens to generate per day.")
    parser.add_argument("--num-ctx", type=int, default=4096, help="Context window sent to Ollama.")
    parser.add_argument("--export-genome", action="store_true")
    parser.add_argument(
        "--roles",
        default="ceo,cto,cfo,people,sales",
        help="Comma-separated list of roles to run each day (default: all 5).",
    )
    parser.add_argument(
        "--ceo-only",
        action="store_true",
        help="Legacy mode: only run the CEO role (matches old behaviour).",
    )
    args = parser.parse_args()

    model_id = args.model_id or args.ollama_model.replace(":", "_").replace("/", "_")
    active_roles = ["ceo"] if args.ceo_only else [r.strip() for r in args.roles.split(",") if r.strip()]

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

            is_done = False
            for day_idx in range(args.days):
                if is_done:
                    break

                for role in active_roles:
                    briefing = env.call_tool(
                        "get_daily_briefing", episode_id=episode_id, agent_role=role
                    )
                    if briefing.get("is_done"):
                        is_done = True
                        break

                    prompt = _build_role_prompt(role, briefing, day_in_episode=day_idx)
                    completion = ollama_generate(
                        args.ollama_url,
                        args.ollama_model,
                        prompt,
                        timeout_s=args.ollama_timeout,
                        retries=args.ollama_retries,
                        max_tokens=args.max_tokens,
                        num_ctx=args.num_ctx,
                    )

                    _dispatch_tool_call(env, episode_id, role, completion, briefing, day_idx)
                    time.sleep(0.05)

            r = env.call_tool("get_reward", episode_id=episode_id)
            reward = float(r.get("reward", 0.0))
            rewards.append(reward)
            breakdown = r.get("breakdown") or {}
            print(
                f"[{ep_idx+1:02d}/{args.episodes}] episode_id={episode_id} seed={seed} "
                f"reward={reward:.4f}  "
                f"val={breakdown.get('company_valuation', 0):.3f} "
                f"brain={breakdown.get('company_brain_quality', 0):.3f} "
                f"coh={breakdown.get('decision_coherence', 0):.3f}"
            )

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

