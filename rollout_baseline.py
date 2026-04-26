"""
Fast baseline rollouts (no LLM).

Runs GENESIS episodes where the "agent" always takes a fixed generic decision.
This provides a reproducible baseline for reward comparisons, without downloading
any base model weights or depending on Ollama.
"""

from __future__ import annotations

import argparse
import os
import time
import uuid


def main():
    parser = argparse.ArgumentParser(description="Run a fixed-policy baseline in GENESIS")
    parser.add_argument("--server", default=os.environ.get("GENESIS_URL", "http://127.0.0.1:7860"))
    parser.add_argument("--model-id", default="baseline_static")
    parser.add_argument("--difficulty", type=int, default=1, choices=[1, 2, 3, 4, 5])
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--seed-start", type=int, default=2000)
    args = parser.parse_args()

    from client import GenesisEnv

    env = GenesisEnv(base_url=args.server).sync()
    env.async_client.use_production_mode = True

    # Same action every day: intentionally weak baseline.
    decision_type = "tactical"
    decision = "Continue current plan. Avoid major changes today."
    reasoning = "Baseline policy: generic low-information action."

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

            for _ in range(args.days):
                briefing = env.call_tool("get_daily_briefing", episode_id=episode_id, agent_role="ceo")
                if briefing.get("is_done"):
                    break

                env.call_tool(
                    "make_decision",
                    episode_id=episode_id,
                    agent_role="ceo",
                    decision_type=decision_type,
                    decision=decision,
                    reasoning=reasoning,
                )
                time.sleep(0.02)

            r = env.call_tool("get_reward", episode_id=episode_id)
            reward = float(r.get("reward", 0.0))
            rewards.append(reward)
            print(f"[{ep_idx+1:02d}/{args.episodes}] episode_id={episode_id} seed={seed} reward={reward:.4f}")

        if rewards:
            avg = sum(rewards) / len(rewards)
            print(f"\nDone. model_id={args.model_id} avg_reward={avg:.4f} best={max(rewards):.4f} worst={min(rewards):.4f}")

    finally:
        env.close()


if __name__ == "__main__":
    main()

