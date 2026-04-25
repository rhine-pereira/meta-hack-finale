import pickle
import matplotlib.pyplot as plt
import sys
import os

# Add project root to sys.path to import server modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import WorldState so pickle can unfreeze it
try:
    from server.world_state import WorldState
except ImportError:
    print("Warning: Could not import server.world_state. Ensure the script is run from the project root or sys.path is correct.")

def plot_rewards(sessions_file="sessions.pkl"):
    if not os.path.exists(sessions_file):
        print(f"No sessions file found at {sessions_file}")
        return

    with open(sessions_file, "rb") as f:
        try:
            sessions, _ = pickle.load(f)
        except Exception as e:
            print(f"Error loading sessions: {e}")
            return

    if not sessions:
        print("No sessions found in file.")
        return

    plt.figure(figsize=(12, 7))
    
    plotted = False
    for episode_id, state in sessions.items():
        if not hasattr(state, 'reward_history') or not state.reward_history:
            continue
        
        days = list(range(len(state.reward_history)))
        label = f"Ep {episode_id[:6]} (Day {state.day})"
        plt.plot(days, state.reward_history, label=label, alpha=0.8, linewidth=2)
        plotted = True

    if not plotted:
        print("No reward history found in any session.")
        return

    plt.title("🧬 GENESIS Training Progress — Reward Curves", fontsize=14, fontweight='bold')
    plt.xlabel("Simulated Day", fontsize=12)
    plt.ylabel("Rubric Reward (0-1)", fontsize=12)
    plt.ylim(0, 1.05)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='small')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    
    output_path = "reward_curves.png"
    plt.savefig(output_path, dpi=300)
    print(f"✅ Successfully saved reward curves to {output_path}")

if __name__ == "__main__":
    plot_rewards()
