"""
GENESIS Training Script — GRPO on startup simulation.

Train LLMs to co-found and operate a startup using GENESIS as the
reward environment. Uses TRL's GRPOTrainer with the 11-component
composable rubric from reward_engine.compute_reward() as the signal.

Usage:
    python train.py                     # Full training run
    python train.py --smoke             # 1 episode smoke test (no GPU needed)
    python train.py --steps 50          # Quick dev run

Requirements:
    pip install trl transformers datasets accelerate peft bitsandbytes
"""

import sys
from unittest.mock import MagicMock

# --- Windows Triton Mock ---
try:
    import triton
except ImportError:
    # Mock Triton to bypass import errors on Windows
    from unittest.mock import MagicMock
    from importlib.machinery import ModuleSpec
    
    mock_triton = MagicMock()
    mock_triton.__version__ = "3.0.0"
    mock_triton.__spec__ = ModuleSpec("triton", None)
    mock_triton.__path__ = []
    
    sys.modules["triton"] = mock_triton
    sys.modules["triton.compiler"] = MagicMock()
    sys.modules["triton.language"] = MagicMock()
    sys.modules["triton.runtime"] = MagicMock()

import argparse
import json
import os
import random
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field as dc_field
from typing import Any, Dict, Optional, Tuple

# --- Windows UTF-8 guard (fixes TRL template read on cp1252) ---
# Some TRL versions ship Jinja templates containing bytes that fail under the default
# Windows "cp1252" locale when pathlib.read_text() is called without encoding.
# Force UTF-8 mode early so downstream libraries read text as UTF-8.
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# --- Torch compile / Triton guard (Windows + venv safe) ---
# On Windows, PyTorch wheels often do NOT ship Triton, but newer Transformers paths can
# indirectly import torch._dynamo / torch._inductor which then tries `import triton.backends`
# and crashes. We do not need torch.compile/inductor for GRPO, so disable them *hard*.
os.environ["TORCHDYNAMO_DISABLE"] = "1"
os.environ["TORCHINDUCTOR_DISABLE"] = "1"
os.environ["TORCH_COMPILE_DISABLE"] = "1"
os.environ["DISABLE_TORCH_COMPILE"] = "1"

# ── Argument Parsing ──────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Train LLMs on GENESIS startup simulation")
parser.add_argument("--smoke", action="store_true", help="Run a smoke test without training")
parser.add_argument("--steps", type=int, default=200, help="Max training steps")
parser.add_argument(
    "--model",
    type=str,
    default="Qwen/Qwen2.5-3B-Instruct",
    help="Base model to fine-tune (adapter will be saved, base remains external).",
)
parser.add_argument("--output", type=str, default="./genesis-checkpoints",
                    help="Output directory for checkpoints")
parser.add_argument("--difficulty", type=int, default=1,
                    choices=[1, 2, 3, 4, 5],
                    help="GENESIS difficulty (1=Tutorial/90d, 2=Seed/180d)")
parser.add_argument("--episode-days", type=int, default=60,
                    help="Days per training episode (default 60; use 90 for full Series A signal).")
parser.add_argument("--num-generations", type=int, default=2, help="GRPO completions per prompt")
parser.add_argument(
    "--max-completion-length",
    type=int,
    default=192,
    help="Token budget per completion (default 192; write_company_brain needs ~80-100 tokens for good values).",
)
parser.add_argument(
    "--dataset-multiplier",
    type=int,
    default=20,
    help="Replicate role prompts to create a synthetic training set.",
)
parser.add_argument(
    "--skip-briefing",
    action="store_true",
    help="Skip get_daily_briefing calls during reward rollouts (faster, less signal).",
)
parser.add_argument(
    "--fast",
    action="store_true",
    help="Speed-first profile (fewer generations, shorter completions, fewer days).",
)
parser.add_argument(
    "--log-dir",
    type=str,
    default="outputs/evals",
    help="Directory for training_log.jsonl and training_progress.png.",
)
args, _ = parser.parse_known_args()

# Apply a conservative speed profile for laptop GPUs / time-boxed runs.
if args.fast:
    # GRPO requires ≥ 2 generations per prompt (group advantage calculation).
    args.num_generations = max(2, min(args.num_generations, 2))
    if args.max_completion_length > 96:
        args.max_completion_length = 96
    if args.dataset_multiplier > 8:
        args.dataset_multiplier = 8
    if args.episode_days > 15:
        args.episode_days = 15
    args.skip_briefing = True

# ── OpenEnv Client (MCP) ──────────────────────────────────────────────────────
from client import GenesisEnv


def _create_env_client(base_url: str = None):
    """Create a sync OpenEnv MCP client in production mode (/mcp HTTP JSON-RPC)."""
    if base_url is None:
        port = os.environ.get("GENESIS_PORT", "7860")
        base_url = f"http://127.0.0.1:{port}"
    env = GenesisEnv(base_url=base_url).sync()
    env.async_client.use_production_mode = True
    return env

# ── Constants ─────────────────────────────────────────────────────────────────

ROLES = ["ceo", "cto", "sales", "people", "cfo"]
DIFFICULTY = args.difficulty
EPISODE_DAYS = args.episode_days

# Tool names agents are allowed to call (subset for training stability)
ALLOWED_TOOLS = {
    "make_decision", "build_feature", "write_company_brain", "read_company_brain",
    "check_bank_balance", "check_team_morale", "analyze_market", "send_message",
    "hire_candidate", "fire_employee", "negotiate_with_investor", "handle_personal_crisis",
    "pivot_company",
}

# Role-specific tool permissions (mirrors app.py role guards)
ROLE_ALLOWED_TOOLS = {
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

# ── Self-Play State ──────────────────────────────────────────────────────────

@dataclass
class SelfPlayState:
    """Persists MarketMaker knowledge across training episodes."""
    episode_rewards: list[float] = dc_field(default_factory=list)
    detected_weaknesses: list[str] = dc_field(default_factory=list)
    current_difficulty: int = DIFFICULTY
    episodes_at_current_level: int = 0
    # Lowered promote threshold (0.55 vs 0.65): the new brain-writing behaviour
    # means models reach ~0.55 sooner; 0.65 was too high and the curriculum
    # never advanced, giving the model a stale, easy environment throughout training.
    PROMOTE_THRESHOLD: float = 0.55   # avg reward to level up
    DEMOTE_THRESHOLD: float = 0.30    # avg reward to level down
    WINDOW: int = 8                   # rolling window (reduced from 10 for faster response)

    def record(self, reward: float, weaknesses: list[str]) -> None:
        self.episode_rewards.append(reward)
        for w in weaknesses:
            if w not in self.detected_weaknesses:
                self.detected_weaknesses.append(w)
        self.episodes_at_current_level += 1

    def next_difficulty(self) -> int:
        if len(self.episode_rewards) < self.WINDOW:
            return self.current_difficulty
        recent_avg = sum(self.episode_rewards[-self.WINDOW:]) / self.WINDOW
        if recent_avg > self.PROMOTE_THRESHOLD and self.current_difficulty < 5:
            self.current_difficulty = min(5, self.current_difficulty + 1)
            self.episodes_at_current_level = 0
            print(f"[MarketMaker] ⬆ Promoted to difficulty {self.current_difficulty} (avg={recent_avg:.3f})")
        elif recent_avg < self.DEMOTE_THRESHOLD and self.current_difficulty > 1:
            self.current_difficulty = max(1, self.current_difficulty - 1)
            self.episodes_at_current_level = 0
            print(f"[MarketMaker] ⬇ Demoted to difficulty {self.current_difficulty} (avg={recent_avg:.3f})")
        return self.current_difficulty

# Module-level persistent self-play state
_self_play = SelfPlayState()

# Shared env client (significant speedup vs reconnecting per completion)
_shared_env = None


def _get_shared_env():
    global _shared_env
    if _shared_env is None:
        _shared_env = _create_env_client()
    return _shared_env


def _close_shared_env():
    global _shared_env
    if _shared_env is not None:
        try:
            _shared_env.close()
        except Exception:
            pass
        _shared_env = None

# ── Episode Runner ────────────────────────────────────────────────────────────

def run_episode(role: str, action_text: str, seed: int | None = None,
                difficulty_override: int | None = None) -> tuple[dict, list[str]]:
    """
    Run a single mini-episode using the OpenEnv GenesisEnv client.
    
    This uses the standardized MCP tool interface, ensuring the training
    environment matches the production environment exactly.
    """
    episode_id = str(uuid.uuid4())
    eff_difficulty = difficulty_override if difficulty_override else DIFFICULTY

    env = _get_shared_env()
    # 1. Reset the environment
    env.call_tool("reset", episode_id=episode_id, difficulty=eff_difficulty, seed=seed or 42)

    # 2. Parse model output into tool calls
    tool_calls = _parse_tool_calls(action_text, role)

    # 3. Simulation loop
    for day in range(EPISODE_DAYS):
        # Step the day and optionally get briefing (briefing adds signal but costs time)
        if args.skip_briefing:
            obs = {"is_done": False}
        else:
            obs = env.call_tool("get_daily_briefing", episode_id=episode_id, agent_role=role)

        if obs.get("is_done"):
            break

        # Execute one tool call per day
        if tool_calls:
            call = tool_calls[day % len(tool_calls)]
            tool_name = call.get("tool", "make_decision")
            tool_args = call.get("args", {})

            # Inject required context if missing
            tool_args["episode_id"] = episode_id
            tool_args["agent_role"] = role

            try:
                env.call_tool(tool_name, **tool_args)
            except Exception:
                # Invalid tool calls are ignored during training
                pass

    # 4. Get final reward and weaknesses for self-play
    reward_data = env.call_tool("get_reward", episode_id=episode_id)

    return reward_data, reward_data.get("weaknesses", [])


def _parse_tool_calls(text: str, role: str) -> list[dict]:
    """
    Parse model output into a list of tool call dicts.

    Accepts two formats:
    1. JSON object: {"tool": "build_feature", "args": {"name": "...", ...}}
    2. JSON array:  [{"tool": ..., "args": ...}, ...]
    3. Plain text fallback: treated as make_decision content
    """
    text = text.strip()
    allowed = ROLE_ALLOWED_TOOLS.get(role, ALLOWED_TOOLS)

    try:
        parsed = json.loads(text)

        # Normalize to list
        if isinstance(parsed, dict):
            parsed = [parsed]

        calls = []
        for item in parsed:
            tool = item.get("tool", "make_decision")
            if tool not in allowed:
                # Tool not allowed for this role — fallback to make_decision
                tool = "make_decision"
            calls.append({"tool": tool, "args": item.get("args", {})})
        return calls

    except (json.JSONDecodeError, ValueError):
        # Treat plain text as a make_decision action
        return [{
            "tool": "make_decision",
            "args": {
                "decision_type": "tactical",
                "decision": text[:300],
                "reasoning": "Model-generated action",
            }
        }]




# ── Training-time JSONL logging ───────────────────────────────────────────────

_log_path: str | None = None
_step_counter = {"n": 0}


def _ensure_log_dir() -> str:
    global _log_path
    if _log_path is not None:
        return _log_path
    os.makedirs(args.log_dir, exist_ok=True)
    _log_path = os.path.join(args.log_dir, "training_log.jsonl")
    if os.path.exists(_log_path):
        os.remove(_log_path)
    return _log_path


# ── Reward Function for GRPO ──────────────────────────────────────────────────

def genesis_reward_fn(completions: list[str], prompts: list[str], **kwargs) -> list[float]:
    """
    GRPO reward function.

    For each completion, runs a mini GENESIS episode and returns
    compute_reward(state).total as the reward signal (0.0 – 1.0).

    Prompts encode the agent role in a system field; we extract it here.
    Every call is logged to training_log.jsonl for post-hoc plotting.
    """
    log_path = _ensure_log_dir()
    rewards = []

    for completion, prompt in zip(completions, prompts):
        role = _extract_role_from_prompt(prompt)
        seed = random.randint(0, 2**31)

        try:
            reward_data, weaknesses = run_episode(
                role=role,
                action_text=completion,
                seed=seed,
                difficulty_override=_self_play.current_difficulty,
            )
            reward = float(reward_data.get("reward", 0.0))
            breakdown = reward_data.get("breakdown", {}) if isinstance(reward_data, dict) else {}
            _self_play.record(reward, weaknesses)
            _self_play.next_difficulty()
        except Exception as e:
            print(f"[WARN] Episode failed: {e}", file=sys.stderr)
            reward = 0.0
            breakdown = {}
            weaknesses = []

        rewards.append(reward)

        _step_counter["n"] += 1
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "step": _step_counter["n"],
                    "role": role,
                    "reward": reward,
                    "difficulty": _self_play.current_difficulty,
                    "completion_preview": completion[:160] if isinstance(completion, str) else str(completion)[:160],
                    "breakdown": {k: float(v) for k, v in breakdown.items() if isinstance(v, (int, float))},
                    "weaknesses": weaknesses,
                }) + "\n")
        except Exception:
            pass

    return rewards


def _extract_role_from_prompt(prompt: str) -> str:
    """Extract the agent role from the prompt string."""
    prompt_lower = prompt.lower()
    for role in ROLES:
        if f"you are the {role}" in prompt_lower or f"you are {role}" in prompt_lower:
            return role
    # Default to CEO if not found
    return "ceo"


# ── Training Dataset ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an AI agent co-founding a B2B SaaS startup.
Respond with a JSON tool call to take action. Format:
{"tool": "<tool_name>", "args": {<arguments>}}

Available tools depend on your role. Always reason about long-term consequences.
Your goal: survive 18 months, reach Series A, keep the team motivated.

CRITICAL REWARD SIGNALS — your score improves when you:
1. Regularly call write_company_brain to store strategic plans, market insights, and decisions.
   Each substantive brain entry (>50 chars) directly increases your decision_coherence score.
   Example: {"tool": "write_company_brain", "args": {"key": "strategy_q1", "value": "Focus on enterprise sales..."}}
2. Build features (CTO) to improve product velocity.
3. Maintain runway > 90 days (CFO).
4. Keep customer satisfaction high (everyone).
5. Resolve personal crises quickly (People head).
"""

ROLE_SYSTEM_PROMPTS = {
    "ceo": (
        "You are the CEO. Focus on strategy, fundraising, and external relationships. "
        "You can negotiate with investors, pivot the company, and set strategic direction. "
        "Key tools: make_decision, write_company_brain, negotiate_with_investor, pivot_company. "
        "Alternate between make_decision and write_company_brain each day to build strategic memory."
    ),
    "cto": (
        "You are the CTO. Focus on product, engineering velocity, and technical quality. "
        "You assign engineers to features and manage tech debt. "
        "Key tools: build_feature, write_company_brain, check_team_morale. "
        "Regularly build features and document your technical roadmap in company_brain."
    ),
    "sales": (
        "You are Head of Sales. Focus on revenue, customer relationships, and market intel. "
        "Analyze the market and write strategic memos to company_brain. "
        "Key tools: analyze_market, write_company_brain, make_decision. "
        "Store ICP definitions, pricing strategy, and customer feedback in company_brain."
    ),
    "people": (
        "You are Head of People. Focus on hiring quality, team morale, and conflict resolution. "
        "Handle personal crises and prevent burnout. "
        "Key tools: check_team_morale, hire_candidate, handle_personal_crisis, write_company_brain. "
        "Document your people strategy and hiring plan in company_brain."
    ),
    "cfo": (
        "You are the CFO. Focus on runway, burn rate, and financial modeling. "
        "Monitor cash and prepare for fundraising. "
        "Key tools: check_bank_balance, negotiate_with_investor, write_company_brain. "
        "Always document the financial model and fundraising timeline in company_brain."
    ),
}

# Brain keys each role should populate — used in scenario prompts to give the model a target
ROLE_BRAIN_KEY_HINTS = {
    "ceo":    "strategy_overview, series_a_plan, competitive_response",
    "cto":    "tech_roadmap, debt_reduction_plan, feature_priorities",
    "sales":  "gtm_strategy, icp_definition, customer_feedback",
    "people": "people_ops, hiring_plan, morale_initiatives",
    "cfo":    "financial_model, burn_rate_analysis, fundraising_timeline",
}

DAY_SCENARIOS = [
    # Early stage: explicit brain-writing nudge
    "Day {day}. Cash: ${cash:,.0f}. Burn: ${burn}/day. Runway: {runway} days. "
    "Employees: {employees}. Customers: {customers}. MRR: ${mrr:,.0f}. "
    "Company brain has {brain_entries} entries so far. "
    "Suggested brain keys to update: {brain_keys}. "
    "What is your most important action today? "
    "(Tip: writing substantive notes to company_brain boosts your decision_coherence score.)",

    # Crisis scenario
    "Day {day}. ALERT: {crisis}. "
    "Cash: ${cash:,.0f}. Team morale: {morale:.0%}. "
    "How do you respond? If relevant, record your crisis response strategy in company_brain.",

    # Fundraising scenario
    "Day {day}. Series A preparation needed. ARR: ${arr:,.0f}. "
    "Investor {investor} has {sentiment:.0%} sentiment. Runway: {runway} days. "
    "Brain entries: {brain_entries}. "
    "What is your fundraising action? Consider writing your Series A narrative to company_brain.",

    # Growth milestone
    "Day {day}. MRR just crossed ${mrr:,.0f}. Burn: ${burn}/day. "
    "Tech debt: {tech_debt:.0%}. Runway: {runway} days. "
    "You have {brain_entries} company_brain entries. "
    "What should {role} prioritise to accelerate growth while managing risk?",
]

CRISIS_TEMPLATES = [
    "Your CTO is considering leaving for a Google offer (3x salary)",
    "Three engineers are interviewing elsewhere after a product pivot",
    "A board member is suggesting inflating MAU numbers in the Series A deck",
    "Your lead investor moved a critical call to conflict with a family commitment",
    "Head of Engineering quit with 2 weeks notice; no documentation exists",
    "AWS bill came in 4x expected due to a logging bug in production",
    "A major customer (30% of ARR) is threatening to churn over a missing feature",
]

INVESTOR_NAMES = ["Sequoia Capital", "a16z", "Benchmark", "Y Combinator", "First Round"]


def build_dataset(n_samples: int = 200) -> list[dict]:
    """
    Build training prompts. Each prompt encodes a startup scenario
    and the agent role. The model must produce a valid tool call.
    """
    dataset = []
    rng = random.Random(42)

    for i in range(n_samples):
        role = rng.choice(ROLES)
        day = rng.randint(1, 90)

        # Generate a realistic scenario
        cash = rng.uniform(50_000, 500_000)
        burn = rng.randint(3_000, 8_000)
        runway = int(cash / burn)
        employees = rng.randint(2, 15)
        customers = rng.randint(0, 20)
        mrr = rng.uniform(0, 50_000)
        morale = rng.uniform(0.3, 0.9)
        # How many brain entries exist already — gives model context on coverage gap
        brain_entries = rng.randint(0, 8)
        tech_debt = rng.uniform(0.1, 0.7)

        scenario = DAY_SCENARIOS[i % len(DAY_SCENARIOS)].format(
            day=day,
            cash=cash,
            burn=burn,
            runway=runway,
            employees=employees,
            customers=customers,
            mrr=mrr,
            arr=mrr * 12,
            morale=morale,
            crisis=rng.choice(CRISIS_TEMPLATES),
            investor=rng.choice(INVESTOR_NAMES),
            sentiment=rng.uniform(0.3, 0.9),
            brain_entries=brain_entries,
            brain_keys=ROLE_BRAIN_KEY_HINTS.get(role, "strategy_overview"),
            tech_debt=tech_debt,
            role=role,
        )

        messages = [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{ROLE_SYSTEM_PROMPTS[role]}"},
            {"role": "user", "content": scenario},
        ]

        dataset.append({
            "messages": messages,
            "role": role,
            "day": day,
        })

    return dataset


# ── Training-evidence plot ─────────────────────────────────────────────

def plot_training_progress() -> str | None:
    """Render reward + difficulty curves from training_log.jsonl."""
    log_path = os.path.join(args.log_dir, "training_log.jsonl")
    if not os.path.exists(log_path):
        return None

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("[plot] matplotlib/numpy unavailable; skipping plot.")
        return None

    rows = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    if not rows:
        return None

    steps = [r["step"] for r in rows]
    rewards = [r["reward"] for r in rows]
    difficulty = [r.get("difficulty", 1) for r in rows]
    window = max(5, len(rewards) // 20)
    if len(rewards) >= window:
        ma = np.convolve(rewards, np.ones(window) / window, mode="valid")
        ma_x = list(range(window, len(rewards) + 1))
    else:
        ma, ma_x = [], []

    out_path = os.path.join(args.log_dir, "training_progress.png")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), dpi=110)

    ax = axes[0]
    ax.scatter(steps, rewards, s=14, alpha=0.35, color="#6366f1", label="reward / step")
    if len(ma) > 0:
        ax.plot(ma_x, ma, color="#ef4444", linewidth=2.0, label=f"MA ({window})")
    ax.set_xlabel("training step (reward-fn call)")
    ax.set_ylabel("episode reward (0–1)")
    ax.set_ylim(0, 1)
    ax.set_title("GENESIS GRPO — reward over training")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right")

    ax2 = axes[1]
    ax2.plot(steps, difficulty, color="#06b6d4", linewidth=2.0)
    ax2.set_xlabel("training step")
    ax2.set_ylabel("MarketMaker difficulty (1–5)")
    ax2.set_yticks([1, 2, 3, 4, 5])
    ax2.set_title("Adaptive curriculum")
    ax2.grid(True, alpha=0.25)

    fig.suptitle("GENESIS — training evidence", fontweight="bold")
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"[plot] wrote {out_path}")
    return out_path


# ── Smoke Test ────────────────────────────────────────────────────────────────

def smoke_test():
    """Quick sanity check — runs 5 episodes without ML, just reward function."""
    print("=" * 60)
    print("GENESIS Training Script — Smoke Test")
    print("=" * 60)

    test_cases = [
        ("ceo",    '{"tool": "make_decision", "args": {"decision_type": "strategic", "decision": "Focus on Series A fundraising", "reasoning": "Runway is below 6 months"}}'),
        ("cto",    '{"tool": "build_feature", "args": {"name": "SSO Integration", "complexity": "medium", "engineers": 2}}'),
        ("sales",  '{"tool": "write_company_brain", "args": {"key": "go_to_market", "value": "Focus on mid-market B2B SaaS companies with 50-200 employees in US and EU"}}'),
        ("people", '{"tool": "make_decision", "args": {"decision_type": "tactical", "decision": "Schedule 1-on-1s with all engineers this week", "reasoning": "Team morale dropping"}}'),
        ("cfo",    '{"tool": "write_company_brain", "args": {"key": "financial_model", "value": "Current burn: $5K/day. At current growth rate, need to raise $2M in 90 days to maintain 12-month runway"}}'),
    ]

    for role, action in test_cases:
        reward_data, weaknesses = run_episode(role=role, action_text=action, seed=42)
        reward = reward_data.get("reward", 0.0)
        _self_play.record(reward, weaknesses)
        print(f"\n  Role: {role.upper()}")
        print(f"  Action: {action[:60]}...")
        print(f"  Reward: {reward:.4f}")
        print("  Breakdown:")
        for k, v in reward_data.get("breakdown", {}).items():
            if k != "total" and v > 0:
                print(f"    {k}: {v:.3f}")
        print(f"  Weaknesses: {weaknesses}")

    print(f"\nFinal self-play state: difficulty={_self_play.current_difficulty}, weaknesses={_self_play.detected_weaknesses}")

    print("\n" + "=" * 60)
    print("Smoke test passed!")
    print("=" * 60)

    # Verify reward function signature
    print("\nVerifying genesis_reward_fn signature...")
    rewards = genesis_reward_fn(
        completions=[test_cases[0][1]],
        prompts=["Day 1. You are the CEO of a startup. What do you do?"],
    )
    assert len(rewards) == 1, "Expected 1 reward"
    assert 0.0 <= rewards[0] <= 1.0, f"Reward out of range: {rewards[0]}"
    print(f"genesis_reward_fn returned: {rewards[0]:.4f} [OK]")


# ── Main Training Loop ────────────────────────────────────────────────────────

def train():
    """Full training run using TRL GRPOTrainer + bitsandbytes 4-bit + LoRA (PEFT)."""
    print("=" * 60)
    print("GENESIS — Training LLMs to Co-Found a Startup")
    print(f"Model:      {args.model}")
    print(f"Difficulty: Level {DIFFICULTY}")
    print(f"Episode:    {EPISODE_DAYS} days/episode")
    print(f"Steps:      {args.steps}")
    print(f"Output:     {args.output}")
    print("=" * 60)

    # ── Import ML dependencies (only when training) ───────────────
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from peft import LoraConfig, TaskType, get_peft_model
        from trl import GRPOConfig, GRPOTrainer
        from datasets import Dataset
    except ImportError as e:
        print(f"\n[ERROR] Missing dependency: {e}")
        print("Detailed error for debugging:")
        import traceback
        traceback.print_exc()
        print("\nInstall with: pip install trl transformers datasets accelerate peft bitsandbytes")
        sys.exit(1)

    # ── Model Setup ───────────────────────────────────────────────
    print("\nLoading model...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
    )
    model.config.use_cache = False

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Qwen2.5 works well with these projection modules for LoRA
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_config)
    try:
        model.print_trainable_parameters()
    except Exception:
        pass

    # ── Dataset ───────────────────────────────────────────────────
    print("\nBuilding dataset...")
    raw_data = build_dataset(n_samples=max(args.steps * 2, 200) * args.dataset_multiplier)

    # Apply chat template to convert messages → prompt strings
    def format_sample(sample):
        prompt = tokenizer.apply_chat_template(
            sample["messages"],
            tokenize=False,
            add_generation_prompt=True,
        )
        return {"prompt": prompt, "role": sample["role"]}

    dataset = Dataset.from_list(raw_data).map(format_sample)
    print(f"Dataset: {len(dataset)} samples")

    # ── GRPO Config ───────────────────────────────────────────────
    grad_accum = max(1, args.num_generations * (2 if args.fast else 4))
    training_args = GRPOConfig(
        output_dir=args.output,
        max_steps=args.steps,
        num_generations=args.num_generations,       # Completions per prompt for GRPO
        per_device_train_batch_size=1,
        gradient_accumulation_steps=grad_accum,
        learning_rate=5e-5,
        warmup_ratio=0.05,
        lr_scheduler_type="cosine",
        optim="adamw_8bit",
        fp16=False,
        bf16=False,
        logging_steps=20 if args.fast else 5,
        report_to="none",                           # Set to "wandb" if you want logging
        max_prompt_length=1024,
        max_completion_length=args.max_completion_length,
        seed=42,
    )

    # ── Trainer ───────────────────────────────────────────────────
    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        args=training_args,
        train_dataset=dataset,
        reward_funcs=genesis_reward_fn,
    )

    # ── Train ─────────────────────────────────────────────────────
    print("\nStarting training...")
    trainer.train()

    # ── Save ──────────────────────────────────────────────────────
    save_path = f"{args.output}/final"
    model.save_pretrained(save_path)
    tokenizer.save_pretrained(save_path)
    print(f"\nTraining complete. Model saved to {save_path}")

    # ── Plot training evidence ─────────────────────────────────────
    plot_training_progress()

    # ── Eval summary ──────────────────────────────────────────────
    print("\nRunning final eval episode...")
    test_reward_data, _ = run_episode(
        role="ceo",
        action_text='{"tool": "write_company_brain", "args": {"key": "strategy_overview", "value": "Focus on enterprise PMF + Series A fundraising while maintaining 18-month runway."}}',
        seed=999,
    )
    print(f"Post-training eval reward (CEO): {float(test_reward_data.get('reward', 0.0)):.4f}")


# ── Server Lifecycle ──────────────────────────────────────────────────────────

def start_openenv_server():
    """Start the GENESIS MCP server in a background process if not already running."""
    port = os.environ.get("GENESIS_PORT", "7860")
    host = "127.0.0.1"
    url = f"http://{host}:{port}"
    
    import requests
    try:
        # FastMCP ready check
        response = requests.get(f"{url}/mcp", timeout=1)
        if response.status_code in (200, 405, 406):
            print(f"Using existing GENESIS server at {url}")
            return None
    except requests.exceptions.RequestException:
        pass

    print(f"Starting GENESIS OpenEnv server (uvicorn server.app:app) on port {port}...")
    # Clean up old session files to ensure a fresh state
    if os.path.exists("sessions.pkl"):
        os.remove("sessions.pkl")
        
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.app:app", "--host", host, "--port", port, "--log-level", "warning"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for server to be ready
    max_retries = 15
    for i in range(max_retries):
        try:
            response = requests.get(f"{url}/mcp", timeout=2)
            if response.status_code in (200, 405, 406):
                print("Server ready.")
                return proc
        except requests.exceptions.RequestException:
            if i % 3 == 0:
                print(f"Waiting for server... ({i}/{max_retries})")
            time.sleep(1)
            
    proc.terminate()
    raise RuntimeError(f"Failed to start GENESIS server on port {port} after 15 seconds.")


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    server_proc = None
    try:
        server_proc = start_openenv_server()
        if args.smoke:
            smoke_test()
        else:
            train()
    finally:
        _close_shared_env()
        if server_proc:
            print("Shutting down GENESIS server...")
            server_proc.terminate()
            server_proc.wait()
