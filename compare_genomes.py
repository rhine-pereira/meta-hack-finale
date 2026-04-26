"""
Compare multiple model genomes (exports a combined comparison PNG).

Prereq: You already ran rollouts that saved episodes into `sessions.pkl`
with distinct `model_id` values (via rollout_infer.py or rollout_ollama.py).
"""

from __future__ import annotations

import argparse
import os

from client import GenesisEnv


def main():
    parser = argparse.ArgumentParser(description="Compare Founder Genomes for multiple model_ids")
    parser.add_argument("--server", default=os.environ.get("GENESIS_URL", "http://127.0.0.1:7860"))
    parser.add_argument("--model-ids", nargs="+", required=True)
    args = parser.parse_args()

    env = GenesisEnv(base_url=args.server).sync()
    env.async_client.use_production_mode = True
    try:
        res = env.call_tool("compare_founder_genomes", model_ids=args.model_ids)
        print(res)
    finally:
        env.close()


if __name__ == "__main__":
    main()

