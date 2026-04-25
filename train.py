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

import argparse
import json
import os
import random
import sys
import uuid

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

# ── Server imports (direct, no subprocess) ────────────────────────────────────
# We import server internals directly for speed — no IPC overhead.
sys.path.insert(0, os.path.dirname(__file__))

from server.world_state import WorldState, AgentRole, DifficultyLevel  # noqa: E402
from server.world_init import initialize_world  # noqa: E402
from server.event_engine import tick_day  # noqa: E402
from server.reward_engine import compute_reward, RubricScore  # noqa: E402

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

# ── Episode Runner ────────────────────────────────────────────────────────────

def run_episode(role: str, action_text: str, seed: int | None = None) -> RubricScore:
    """
    Run a single mini-episode using one model completion as the agent action.

    The model output is parsed as JSON tool call(s). Each day the agent:
    1. Receives the daily briefing (observation)
    2. Executes its parsed tool call
    3. World ticks forward

    Returns the final RubricScore after EPISODE_DAYS days.
    """
    rng = random.Random(seed or random.randint(0, 2**31))
    state = initialize_world(difficulty=DifficultyLevel(DIFFICULTY), seed=rng.randint(0, 2**31))
    state.episode_id = str(uuid.uuid4())

    role_enum = AgentRole(role)

    # Parse model output into tool calls (list of dicts)
    tool_calls = _parse_tool_calls(action_text, role)

    for day in range(EPISODE_DAYS):
        tick_day(state, rng)

        if state.is_done():
            break

        # Execute one tool call per day (round-robin through parsed calls)
        if tool_calls:
            call = tool_calls[day % len(tool_calls)]
            _execute_tool_call(state, rng, role_enum, call)
        else:
            # No valid tool call — agent is silent, small penalty via inaction
            pass

    return compute_reward(state)


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


def _execute_tool_call(state: WorldState, rng: random.Random,
                        role: AgentRole, call: dict) -> None:
    """Execute a single parsed tool call against the world state."""
    tool = call.get("tool", "make_decision")
    args = call.get("args", {})

    try:
        if tool == "make_decision":
            decision = args.get("decision", "No decision")
            reasoning = args.get("reasoning", "")
            decision_type = args.get("decision_type", "tactical")
            log_key = f"decision_log_{state.day}"
            state.company_brain[log_key] = (
                state.company_brain.get(log_key, "") +
                f"\n[{role.value.upper()}] {decision_type}: {decision} ({reasoning})"
            )
            align_delta = 0.01 if decision_type == "strategic" else 0.002
            state.cofounder_alignment = min(1.0, state.cofounder_alignment + align_delta)

        elif tool == "build_feature" and role == AgentRole.CTO:
            from server.world_state import PendingFeature
            comp_map = {"low": (5, 0.02), "medium": (15, 0.07), "high": (30, 0.18)}
            complexity = args.get("complexity", "medium")
            days, debt = comp_map.get(complexity, comp_map["medium"])
            engineers = max(1, int(args.get("engineers", 1)))
            state.pending_features.append(PendingFeature(
                name=args.get("name", "Feature"),
                complexity=complexity,
                engineers_assigned=engineers,
                days_remaining=days,
                tech_debt_added=debt,
            ))

        elif tool == "write_company_brain":
            key = args.get("key", f"note_{state.day}")
            value = args.get("value", "")
            state.company_brain[key] = value

        elif tool == "read_company_brain":
            pass  # Read-only — no state change

        elif tool == "analyze_market":
            pass  # Observation only — no state change

        elif tool == "send_message":
            from server.world_state import Message
            try:
                to_role = AgentRole(args.get("to_role", "ceo"))
            except ValueError:
                to_role = AgentRole.CEO
            state.messages.append(Message(
                id=str(uuid.uuid4()),
                from_role=role,
                to_role=to_role,
                subject=args.get("subject", "Update"),
                content=args.get("content", ""),
                day=state.day,
            ))

        elif tool == "check_bank_balance" and role in (AgentRole.CEO, AgentRole.CFO):
            pass  # Observation only

        elif tool == "check_team_morale":
            pass  # Observation only

        elif tool == "negotiate_with_investor" and role in (AgentRole.CEO, AgentRole.CFO):
            investor_id = args.get("investor_id", "")
            inv = next((i for i in state.investors if i.id == investor_id), None)
            if inv:
                valuation = float(args.get("valuation", state.valuation))
                equity = float(args.get("equity", 0.15))
                score = inv.sentiment * (state.arr() / 1_000_000 + 0.1)
                if score > 0.4 and valuation <= state.valuation * 2.0 and equity <= 0.25:
                    inv.has_term_sheet = True
                    inv.term_sheet_valuation = valuation
                    inv.term_sheet_equity = equity
                    state.equity_sold += equity
                    inv.sentiment = min(1.0, inv.sentiment + 0.2)

        elif tool == "pivot_company" and role == AgentRole.CEO:
            state.pivot_count += 1
            state.pivot_in_progress = True
            state.pivot_direction = args.get("new_direction", "new market")
            for emp in state.employees:
                emp.morale = max(0.0, emp.morale - 0.15)
            for r in state.cofounder_morale:
                state.cofounder_morale[r] = max(0.0, state.cofounder_morale[r] - 0.10)

        elif tool == "handle_personal_crisis" and role == AgentRole.PEOPLE:
            crisis_id = args.get("crisis_id", "")
            response = args.get("response", "")
            crisis = next((c for c in state.personal_crises if c.id == crisis_id), None)
            if crisis and not crisis.resolved:
                quality = min(1.0, len(response) / 300)
                crisis.resolved = True
                crisis.resolution_quality = 0.5 + quality * 0.5
                state.crises_resolved += 1

        elif tool in ("hire_candidate", "fire_employee"):
            pass  # Simplified — skip complex hiring logic in training

    except Exception:
        # Any execution error is silently swallowed during training
        pass


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
            score = run_episode(role=role, action_text=completion, seed=seed)
            rewards.append(float(score.total))
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
        score = run_episode(role=role, action_text=action, seed=42)
        print(f"\n  Role: {role.upper()}")
        print(f"  Action: {action[:60]}...")
        print(f"  Reward: {score.total:.4f}")
        print("  Breakdown:")
        for k, v in score.breakdown().items():
            if k != "total" and v > 0:
                print(f"    {k}: {v:.3f}")

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
        from unsloth import FastLanguageModel
        from trl import GRPOConfig, GRPOTrainer
        from datasets import Dataset
    except ImportError as e:
        print(f"\n[ERROR] Missing dependency: {e}")
        print("Install with: pip install trl transformers unsloth datasets")
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
    test_score = run_episode(
        role="ceo",
        action_text='{"tool": "make_decision", "args": {"decision_type": "strategic", "decision": "Focus on PMF", "reasoning": "Early stage"}}',
        seed=999,
    )
    print(f"Baseline reward (random CEO action): {test_score.total:.4f}")


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if args.smoke:
        smoke_test()
    else:
        train()
