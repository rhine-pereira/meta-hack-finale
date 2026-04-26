"""
Roll out the genesis_final LoRA adapter against the GENESIS MCP server.

Delegates all model loading, prompt construction, and tool execution to
ml_inference.py so this file stays thin and focused on CLI orchestration.

Usage examples:
    # All 5 roles, 10 episodes, 30 days each, difficulty 1
    python rollout_infer.py

    # CEO + CTO only, difficulty 3, export Founder Genome at end
    python rollout_infer.py --roles ceo cto --difficulty 3 --export-genome

    # Quick single episode smoke-check
    python rollout_infer.py --episodes 1 --days 10 --quiet
"""

from __future__ import annotations

import argparse
import os

from ml_inference import (
    DEFAULT_ADAPTER,
    DEFAULT_BASE_MODEL,
    load_model_and_tokenizer,
    run_episode,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Roll out the genesis_final LoRA adapter in GENESIS"
    )
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--adapter", default=DEFAULT_ADAPTER, help="Path to PEFT adapter dir")
    parser.add_argument("--server", default=os.environ.get("GENESIS_URL", "http://127.0.0.1:7860"))
    parser.add_argument("--model-id", default="genesis_final")
    parser.add_argument("--difficulty", type=int, default=1, choices=[1, 2, 3, 4, 5])
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--seed-start", type=int, default=1000)
    parser.add_argument("--max-new-tokens", type=int, default=200)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument(
        "--roles",
        nargs="+",
        default=["ceo", "cto", "sales", "people", "cfo"],
        choices=["ceo", "cto", "sales", "people", "cfo"],
        help="Roles to drive with the ML model in round-robin order.",
    )
    parser.add_argument("--export-genome", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    model, tokenizer = load_model_and_tokenizer(args.base_model, args.adapter)

    from client import GenesisEnv
    import uuid

    env = GenesisEnv(base_url=args.server).sync()
    env.async_client.use_production_mode = True

    verbose = not args.quiet
    rewards: list[float] = []

    try:
        for ep_idx in range(args.episodes):
            episode_id = f"inf-{uuid.uuid4().hex[:10]}"
            seed = args.seed_start + ep_idx

            reward_data = run_episode(
                model=model,
                tokenizer=tokenizer,
                env=env,
                episode_id=episode_id,
                roles=args.roles,
                difficulty=args.difficulty,
                seed=seed,
                max_days=args.days,
                max_new_tokens=args.max_new_tokens,
                temperature=args.temperature,
                model_id=args.model_id,
                verbose=verbose,
            )

            total = float(reward_data.get("reward", 0.0))
            rewards.append(total)
            print(
                f"[{ep_idx + 1:02d}/{args.episodes}] "
                f"episode_id={episode_id} seed={seed} reward={total:.4f}"
            )

        if rewards:
            avg = sum(rewards) / len(rewards)
            print(
                f"\nDone. avg_reward={avg:.4f} "
                f"best={max(rewards):.4f} worst={min(rewards):.4f}"
            )

        if args.export_genome:
            res = env.call_tool(
                "export_founder_genome",
                model_id=args.model_id,
                difficulty=args.difficulty,
            )
            if isinstance(res, dict) and res.get("artifacts"):
                print(f"Exported genome: {res['artifacts']}")
            else:
                print(f"Genome export: {res}")

    finally:
        env.close()


if __name__ == "__main__":
    main()
