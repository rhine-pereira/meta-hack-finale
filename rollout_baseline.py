"""
Fast baseline rollouts (no LLM).

Runs GENESIS episodes where the "agent" always takes a fixed generic decision.
This provides a reproducible baseline for reward comparisons, without downloading
any base model weights or depending on Ollama.

Two modes:
  --ceo-only   Legacy: only the CEO role acts (original behaviour).
  default       All 5 roles act with role-appropriate fixed actions (fair multi-role baseline).
"""

from __future__ import annotations

import argparse
import os
import time
import uuid


# Fixed per-role actions — still intentionally generic but role-appropriate,
# so the baseline is a fair comparison point for multi-role LLM rollouts.
ROLE_FIXED_ACTIONS = {
    "ceo": {
        "tool": "make_decision",
        "args": {
            "decision_type": "tactical",
            "decision": "Continue current plan. Avoid major changes today.",
            "reasoning": "Baseline policy: generic low-information action.",
        },
    },
    "cto": {
        "tool": "make_decision",
        "args": {
            "decision_type": "tactical",
            "decision": "Maintain current engineering velocity and monitor tech debt.",
            "reasoning": "Baseline policy: no-op engineering action.",
        },
    },
    "sales": {
        "tool": "make_decision",
        "args": {
            "decision_type": "tactical",
            "decision": "Follow up with existing pipeline. No new outbound today.",
            "reasoning": "Baseline policy: passive sales action.",
        },
    },
    "people": {
        "tool": "make_decision",
        "args": {
            "decision_type": "tactical",
            "decision": "Hold standard weekly standup. No personnel changes.",
            "reasoning": "Baseline policy: passive people action.",
        },
    },
    "cfo": {
        "tool": "make_decision",
        "args": {
            "decision_type": "tactical",
            "decision": "Review burn rate. No financial actions needed today.",
            "reasoning": "Baseline policy: passive financial monitoring.",
        },
    },
}

ROLES_IN_ORDER = ["ceo", "cto", "cfo", "people", "sales"]


def main():
    parser = argparse.ArgumentParser(description="Run a fixed-policy baseline in GENESIS")
    parser.add_argument("--server", default=os.environ.get("GENESIS_URL", "http://127.0.0.1:7860"))
    parser.add_argument("--model-id", default="baseline_static")
    parser.add_argument("--difficulty", type=int, default=1, choices=[1, 2, 3, 4, 5])
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--days", type=int, default=60,
                        help="Days per episode (default 60 to match rollout_ollama default).")
    parser.add_argument("--seed-start", type=int, default=2000)
    parser.add_argument(
        "--ceo-only",
        action="store_true",
        help="Legacy mode: only the CEO role acts (matches original baseline behaviour).",
    )
    args = parser.parse_args()

    active_roles = ["ceo"] if args.ceo_only else ROLES_IN_ORDER

    from client import GenesisEnv

    env = GenesisEnv(base_url=args.server).sync()
    env.async_client.use_production_mode = True

    try:
        rewards: list[float] = []
        for ep_idx in range(args.episodes):
            episode_id = f"base-{uuid.uuid4().hex[:10]}"
            seed = args.seed_start + ep_idx

            env.call_tool(
                "reset",
                episode_id=episode_id,
                difficulty=args.difficulty,
                seed=seed,
                model_id=args.model_id,
                model_provider="baseline",
                model_version="static_policy_v1",
            )

            is_done = False
            for _ in range(args.days):
                if is_done:
                    break
                for role in active_roles:
                    briefing = env.call_tool(
                        "get_daily_briefing", episode_id=episode_id, agent_role=role
                    )
                    if briefing.get("is_done"):
                        is_done = True
                        break

                    action = ROLE_FIXED_ACTIONS[role]
                    tool_name = action["tool"]
                    tool_args = dict(action["args"])

                    env.call_tool(
                        tool_name,
                        episode_id=episode_id,
                        agent_role=role,
                        **tool_args,
                    )
                    time.sleep(0.02)

            r = env.call_tool("get_reward", episode_id=episode_id)
            reward = float(r.get("reward", 0.0))
            rewards.append(reward)
            breakdown = r.get("breakdown") or {}
            print(
                f"[{ep_idx+1:02d}/{args.episodes}] episode_id={episode_id} seed={seed} "
                f"reward={reward:.4f}  "
                f"brain={breakdown.get('company_brain_quality', 0):.3f} "
                f"coh={breakdown.get('decision_coherence', 0):.3f}"
            )

        if rewards:
            avg = sum(rewards) / len(rewards)
            print(
                f"\nDone. model_id={args.model_id} "
                f"avg_reward={avg:.4f} best={max(rewards):.4f} worst={min(rewards):.4f}"
            )

    finally:
        env.close()


if __name__ == "__main__":
    main()

