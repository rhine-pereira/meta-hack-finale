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
    pip install trl transformers unsloth datasets torch
    (unsloth: https://github.com/unslothai/unsloth)
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

# ── Argument Parsing ──────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Train LLMs on GENESIS startup simulation")
parser.add_argument("--smoke", action="store_true", help="Run a smoke test without training")
parser.add_argument("--steps", type=int, default=200, help="Max training steps")
parser.add_argument("--model", type=str, default="unsloth/Qwen2.5-7B-Instruct-bnb-4bit",
                    help="Model to fine-tune")
parser.add_argument("--output", type=str, default="./genesis-checkpoints",
                    help="Output directory for checkpoints")
parser.add_argument("--difficulty", type=int, default=1,
                    choices=[1, 2, 3, 4, 5],
                    help="GENESIS difficulty (1=Tutorial/90d, 2=Seed/180d)")
parser.add_argument("--episode-days", type=int, default=30,
                    help="Days per training episode (shorter = faster reward)")
parser.add_argument("--num-generations", type=int, default=4,
                    help="GRPO completions per prompt")
args, _ = parser.parse_known_args()

# ── OpenEnv Client (MCP) ──────────────────────────────────────────────────────
from client import GenesisEnv


def _create_env_client(base_url: str = "http://127.0.0.1:7860"):
    """Create a sync OpenEnv MCP client in production mode (/mcp HTTP JSON-RPC)."""
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
    PROMOTE_THRESHOLD: float = 0.65   # avg reward to level up
    DEMOTE_THRESHOLD: float = 0.30    # avg reward to level down
    WINDOW: int = 10                  # rolling window for avg

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

    # Use the OpenEnv client to interact with the environment.
    # Production mode calls FastMCP /mcp directly and avoids /ws assumptions.
    env = _create_env_client()
    try:
        # 1. Reset the environment
        env.call_tool("reset", episode_id=episode_id, difficulty=eff_difficulty, seed=seed or 42)
        
        # 2. Parse model output into tool calls
        tool_calls = _parse_tool_calls(action_text, role)
        
        # 3. Simulation loop
        for day in range(EPISODE_DAYS):
            # Step the day and get briefing
            obs = env.call_tool("get_daily_briefing", episode_id=episode_id, agent_role=role)
            
            if obs.get("is_done"):
                break
                
            # Execute one tool call per day
            if tool_calls:
                call = tool_calls[day % len(tool_calls)]
                tool_name = call.get("tool", "make_decision")
                args = call.get("args", {})
                
                # Inject required context if missing
                args["episode_id"] = episode_id
                args["agent_role"] = role
                
                try:
                    env.call_tool(tool_name, **args)
                except Exception:
                    # Invalid tool calls are ignored during training
                    pass
        
        # 4. Get final reward and weaknesses for self-play
        reward_data = env.call_tool("get_reward", episode_id=episode_id)

    finally:
        env.close()

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




# ── Reward Function for GRPO ──────────────────────────────────────────────────

def genesis_reward_fn(completions: list[str], prompts: list[str], **kwargs) -> list[float]:
    """
    GRPO reward function.

    For each completion, runs a mini GENESIS episode and returns
    compute_reward(state).total as the reward signal (0.0 – 1.0).

    Prompts encode the agent role in a system field; we extract it here.
    """
    rewards = []

    for completion, prompt in zip(completions, prompts):
        # Extract role from prompt metadata
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
            _self_play.record(reward, weaknesses)
            _self_play.next_difficulty()
            rewards.append(reward)
        except Exception as e:
            # Failed episode gets zero reward
            print(f"[WARN] Episode failed: {e}", file=sys.stderr)
            rewards.append(0.0)

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
Your goal: survive 18 months, reach Series A, keep the team motivated."""

ROLE_SYSTEM_PROMPTS = {
    "ceo": "You are the CEO. Focus on strategy, fundraising, and external relationships. "
           "You can negotiate with investors, pivot the company, and set strategic direction.",
    "cto": "You are the CTO. Focus on product, engineering velocity, and technical quality. "
           "You assign engineers to features and manage tech debt.",
    "sales": "You are Head of Sales. Focus on revenue, customer relationships, and market intel. "
             "Analyze the market and write strategic memos.",
    "people": "You are Head of People. Focus on hiring quality, team morale, and conflict resolution. "
              "Handle personal crises and prevent burnout.",
    "cfo": "You are the CFO. Focus on runway, burn rate, and financial modeling. "
           "Monitor cash and prepare for fundraising.",
}

DAY_SCENARIOS = [
    # Early stage (Day 1-30)
    "Day {day}. Cash: ${cash:,.0f}. Burn: ${burn}/day. Runway: {runway} days. "
    "Employees: {employees}. Customers: {customers}. MRR: ${mrr:,.0f}. "
    "What is your most important action today?",

    # Crisis scenario
    "Day {day}. ALERT: {crisis}. "
    "Cash: ${cash:,.0f}. Team morale: {morale:.0%}. "
    "How do you respond?",

    # Fundraising scenario
    "Day {day}. Series A preparation needed. ARR: ${arr:,.0f}. "
    "Investor {investor} has {sentiment:.0%} sentiment. Runway: {runway} days. "
    "What is your fundraising action?",
]

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
            crisis="Your CTO is considering leaving for a Google offer",
            investor="Sequoia Capital",
            sentiment=rng.uniform(0.3, 0.9),
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
    """Full training run using TRL GRPOTrainer with Unsloth QLoRA."""
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
        import transformers
        from transformers import AutoModel, AutoModelForCausalLM, AutoTokenizer
        from unsloth import FastLanguageModel
        from trl import GRPOConfig, GRPOTrainer
        from datasets import Dataset
    except ImportError as e:
        print(f"\n[ERROR] Missing dependency: {e}")
        print("Detailed error for debugging:")
        import traceback
        traceback.print_exc()
        print("\nInstall with: pip install trl transformers unsloth datasets torch")
        sys.exit(1)

    # ── Model Setup ───────────────────────────────────────────────
    print("\nLoading model...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model,
        max_seq_length=2048,
        load_in_4bit=True,
        dtype=None,  # Auto-detect
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"],
        lora_alpha=32,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )
    print(f"Model loaded. Trainable params: {model.num_parameters():,}")

    # ── Dataset ───────────────────────────────────────────────────
    print("\nBuilding dataset...")
    raw_data = build_dataset(n_samples=max(args.steps * 2, 200))

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
    training_args = GRPOConfig(
        output_dir=args.output,
        max_steps=args.steps,
        num_generations=args.num_generations,       # Completions per prompt for GRPO
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=5e-5,
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",
        optim="adamw_8bit",
        fp16=False,
        bf16=True,
        logging_steps=5,
        save_steps=50,
        save_total_limit=3,
        report_to="none",                           # Set to "wandb" if you want logging
        max_prompt_length=1024,
        max_completion_length=512,
        temperature=0.9,                            # High temp for exploration
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
    print(f"Expected time: ~{args.steps * 30 // 60} minutes on A100")
    trainer.train()

    # ── Save ──────────────────────────────────────────────────────
    save_path = f"{args.output}/final"
    model.save_pretrained(save_path)
    tokenizer.save_pretrained(save_path)
    print(f"\nTraining complete. Model saved to {save_path}")

    # ── Eval summary ──────────────────────────────────────────────
    print("\nRunning final eval episode...")
    test_reward_data, _ = run_episode(
        role="ceo",
        action_text='{"tool": "make_decision", "args": {"decision_type": "strategic", "decision": "Focus on PMF", "reasoning": "Early stage"}}',
        seed=999,
    )
    print(f"Baseline reward (random CEO action): {float(test_reward_data.get('reward', 0.0)):.4f}")


# ── Server Lifecycle ──────────────────────────────────────────────────────────

def start_openenv_server():
    """Start the GENESIS MCP server in a background process."""
    print("Starting GENESIS OpenEnv server (uvicorn server.app:app)...")
    # Clean up old session files to ensure a fresh state
    if os.path.exists("sessions.pkl"):
        os.remove("sessions.pkl")
        
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.app:app", "--host", "127.0.0.1", "--port", "7860", "--log-level", "warning"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for server to be ready
    import requests
    max_retries = 15
    for i in range(max_retries):
        try:
            # FastMCP is considered ready when /mcp responds.
            # GET usually returns 406 (missing Accept: text/event-stream), which is expected.
            response = requests.get("http://127.0.0.1:7860/mcp", timeout=2)
            if response.status_code in (200, 405, 406):
                print("Server ready.")
                return proc
        except requests.exceptions.RequestException:
            if i % 3 == 0:
                print(f"Waiting for server... ({i}/{max_retries})")
            time.sleep(1)
            
    proc.terminate()
    raise RuntimeError("Failed to start GENESIS server after 15 seconds.")


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
        if server_proc:
            print("Shutting down GENESIS server...")
            server_proc.terminate()
            server_proc.wait()
