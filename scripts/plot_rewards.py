import argparse
import json
import os
import pickle
import sys

import matplotlib.pyplot as plt

# Add project root to sys.path to import local server modules for pickle deserialization.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from server.world_state import WorldState  # noqa: F401
except ImportError:
    print("Warning: Could not import server.world_state. Run from project root.")


def _moving_average(values, window=7):
    if len(values) < window:
        return values
    out = []
    running = 0.0
    for i, value in enumerate(values):
        running += value
        if i >= window:
            running -= values[i - window]
        if i >= window - 1:
            out.append(running / window)
    return out


def plot_rewards(sessions_file="sessions.pkl", output_dir="outputs/evals"):
    if not os.path.exists(sessions_file):
        raise FileNotFoundError(f"No sessions file found at {sessions_file}")

    with open(sessions_file, "rb") as f:
        sessions, _ = pickle.load(f)

    if not sessions:
        raise ValueError("No sessions found in sessions.pkl")

    os.makedirs(output_dir, exist_ok=True)

    plt.figure(figsize=(12, 7))

    final_rewards = []
    plotted = 0
    for episode_id, state in sessions.items():
        if not hasattr(state, "reward_history") or not state.reward_history:
            continue

        rewards = [float(x) for x in state.reward_history]
        days = list(range(1, len(rewards) + 1))
        label = f"Ep {episode_id[:6]}"

        plt.plot(days, rewards, alpha=0.25, linewidth=1)

        ma = _moving_average(rewards, window=7)
        if ma:
            ma_days = list(range(max(1, len(rewards) - len(ma) + 1), len(rewards) + 1))
            plt.plot(ma_days, ma, label=label, linewidth=2)

        final_rewards.append(rewards[-1])
        plotted += 1

    if plotted == 0:
        raise ValueError("No reward_history found in any session")

    plt.title("GENESIS Training Progress - Reward Curves", fontsize=14, fontweight="bold")
    plt.xlabel("Simulated Day", fontsize=12)
    plt.ylabel("Reward (0 to 1)", fontsize=12)
    plt.ylim(0, 1.05)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(loc="lower right", fontsize="small")
    plt.tight_layout()

    curve_path = os.path.join(output_dir, "reward_curves.png")
    plt.savefig(curve_path, dpi=200)
    plt.close()

    summary = {
        "num_sessions_with_history": plotted,
        "avg_final_reward": round(sum(final_rewards) / len(final_rewards), 4),
        "best_final_reward": round(max(final_rewards), 4),
        "worst_final_reward": round(min(final_rewards), 4),
    }
    summary_path = os.path.join(output_dir, "reward_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Saved: {curve_path}")
    print(f"Saved: {summary_path}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot GENESIS reward curves from sessions.pkl")
    parser.add_argument("--sessions", default="sessions.pkl", help="Path to sessions.pkl")
    parser.add_argument("--out", default="outputs/evals", help="Directory to write artifacts")
    args = parser.parse_args()
    plot_rewards(sessions_file=args.sessions, output_dir=args.out)
