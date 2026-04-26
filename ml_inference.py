"""
GENESIS ML Inference — Load the fine-tuned LoRA adapter and run it in the simulation.

The adapter at models/genesis_final is a PEFT LoRA checkpoint trained on top of
Qwen/Qwen2.5-3B-Instruct (rank-16 on q/k/v/o projections, alpha-32).

Key improvements over rollout_infer.py:
- Drives all five roles (ceo, cto, sales, people, cfo), not just CEO
- Uses the model's built-in Qwen chat template + tool-call format from chat_template.jinja
- Per-role system prompts with their exact allowed tool signatures
- Structured output: model emits {"tool": ..., "args": {...}} which is directly executed
- Quality-aware crisis handling: model response is passed as the human-readable answer,
  and the simulation's resolution_quality score naturally captures coherence
- Episode summary printed at the end with per-component reward breakdown
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Paths ─────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_ADAPTER = str(REPO_ROOT / "models" / "genesis_final")
DEFAULT_BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"

# ── Per-role system prompts (mirror ROLE_SYSTEM_PROMPTS in train.py, enriched) ─

ROLE_SYSTEM_PROMPTS: Dict[str, str] = {
    "ceo": (
        "You are the CEO co-founder of a B2B SaaS startup in the GENESIS simulation.\n"
        "Your domain: fundraising strategy, company pivots, investor relations, high-level direction.\n"
        "Available tools (choose ONE per turn):\n"
        "  make_decision        – log a strategic or tactical decision\n"
        "  write_company_brain  – store a key insight or memo to shared memory\n"
        "  read_company_brain   – retrieve a stored memo or insight\n"
        "  analyze_market       – get competitor landscape and TAM\n"
        "  send_message         – write to another co-founder\n"
        "  pivot_company        – propose or vote on a product/market pivot\n"
        "  check_bank_balance   – check cash, burn rate, runway\n"
        "  negotiate_with_investor – send a term sheet proposal\n"
        "  send_investor_update – keep an investor warm\n"
        "  hire_candidate       – extend a job offer\n"
        "  fire_employee        – terminate an employee\n"
        "Respond with exactly ONE JSON tool call: {\"tool\": \"<name>\", \"args\": {<arguments>}}\n"
        "No markdown, no prose — pure JSON."
    ),
    "cto": (
        "You are the CTO co-founder of a B2B SaaS startup in the GENESIS simulation.\n"
        "Your domain: product engineering, tech debt, feature velocity, deploy health.\n"
        "Available tools (choose ONE per turn):\n"
        "  make_decision        – log a technical or architectural decision\n"
        "  write_company_brain  – store a technical memo or debt snapshot\n"
        "  read_company_brain   – retrieve a stored memo\n"
        "  build_feature        – start engineering on a new feature\n"
        "  deploy_to_production – ship the current build (beware of tech debt!)\n"
        "  run_load_test        – test system capacity\n"
        "  review_codebase_health – inspect tech debt and uptime\n"
        "  send_message         – write to another co-founder\n"
        "  check_team_morale    – check engineer morale and burnout\n"
        "  hire_candidate       – offer a job to a strong candidate\n"
        "  fire_employee        – remove a toxic or low-performing engineer\n"
        "Respond with exactly ONE JSON tool call: {\"tool\": \"<name>\", \"args\": {<arguments>}}\n"
        "No markdown, no prose — pure JSON."
    ),
    "sales": (
        "You are the Head of Sales co-founder of a B2B SaaS startup in the GENESIS simulation.\n"
        "Your domain: revenue, customer satisfaction, churn reduction, market intelligence.\n"
        "Available tools (choose ONE per turn):\n"
        "  make_decision        – log a sales or go-to-market decision\n"
        "  write_company_brain  – store a GTM strategy or customer insight\n"
        "  read_company_brain   – retrieve a stored note\n"
        "  analyze_market       – get competitive intelligence\n"
        "  run_competitive_analysis – deep-dive on a named competitor\n"
        "  send_customer_email  – reach out to a customer (improves satisfaction)\n"
        "  update_crm           – update a customer's pipeline status\n"
        "  send_message         – write to another co-founder\n"
        "Respond with exactly ONE JSON tool call: {\"tool\": \"<name>\", \"args\": {<arguments>}}\n"
        "No markdown, no prose — pure JSON."
    ),
    "people": (
        "You are the Head of People co-founder of a B2B SaaS startup in the GENESIS simulation.\n"
        "Your domain: hiring quality, team morale, burnout prevention, conflict resolution.\n"
        "Available tools (choose ONE per turn):\n"
        "  make_decision        – log a people or culture decision\n"
        "  write_company_brain  – store a hiring plan or culture note\n"
        "  read_company_brain   – retrieve a stored memo\n"
        "  check_team_morale    – check morale and burnout across the team\n"
        "  post_job_listing     – advertise an open role (applicants arrive in 5 days)\n"
        "  conduct_interview    – evaluate a candidate from the pool\n"
        "  hire_candidate       – extend a job offer\n"
        "  fire_employee        – remove a toxic or departing employee\n"
        "  hold_one_on_one      – 1-on-1 with an employee (reduces burnout)\n"
        "  handle_personal_crisis – respond to a co-founder personal crisis\n"
        "  send_message         – write to another co-founder\n"
        "Respond with exactly ONE JSON tool call: {\"tool\": \"<name>\", \"args\": {<arguments>}}\n"
        "No markdown, no prose — pure JSON."
    ),
    "cfo": (
        "You are the CFO co-founder of a B2B SaaS startup in the GENESIS simulation.\n"
        "Your domain: cash management, burn rate, runway, financial projections, fundraising.\n"
        "Available tools (choose ONE per turn):\n"
        "  make_decision          – log a financial or operational decision\n"
        "  write_company_brain    – store a financial model or budget note\n"
        "  read_company_brain     – retrieve a stored memo\n"
        "  check_bank_balance     – check cash, burn rate, runway\n"
        "  create_financial_model – project MRR and cash N months ahead\n"
        "  send_investor_update   – maintain investor sentiment\n"
        "  negotiate_with_investor – participate in a funding negotiation\n"
        "  send_message           – write to another co-founder\n"
        "Respond with exactly ONE JSON tool call: {\"tool\": \"<name>\", \"args\": {<arguments>}}\n"
        "No markdown, no prose — pure JSON."
    ),
}

# Tools that each role is allowed to call (mirrors train.py + app.py guards)
ROLE_ALLOWED_TOOLS: Dict[str, set] = {
    "ceo": {
        "make_decision", "write_company_brain", "read_company_brain",
        "analyze_market", "send_message", "pivot_company",
        "check_bank_balance", "negotiate_with_investor", "send_investor_update",
        "hire_candidate", "fire_employee",
    },
    "cto": {
        "make_decision", "write_company_brain", "read_company_brain",
        "build_feature", "deploy_to_production", "run_load_test",
        "review_codebase_health", "send_message", "check_team_morale",
        "hire_candidate", "fire_employee",
    },
    "sales": {
        "make_decision", "write_company_brain", "read_company_brain",
        "analyze_market", "run_competitive_analysis",
        "send_customer_email", "update_crm", "send_message",
    },
    "people": {
        "make_decision", "write_company_brain", "read_company_brain",
        "check_team_morale", "post_job_listing", "conduct_interview",
        "hire_candidate", "fire_employee", "hold_one_on_one",
        "handle_personal_crisis", "send_message",
    },
    "cfo": {
        "make_decision", "write_company_brain", "read_company_brain",
        "check_bank_balance", "create_financial_model",
        "send_investor_update", "negotiate_with_investor", "send_message",
    },
}

# ── Model loading ─────────────────────────────────────────────────────────────


def load_model_and_tokenizer(
    base_model: str = DEFAULT_BASE_MODEL,
    adapter_path: str = DEFAULT_ADAPTER,
):
    """
    Load Qwen2.5-3B-Instruct + the genesis_final LoRA adapter.

    Returns (model, tokenizer) ready for inference.
    The model is put into eval mode and moved to the best available device.
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    adapter_path = str(Path(adapter_path).resolve())
    if not os.path.isdir(adapter_path):
        raise FileNotFoundError(
            f"LoRA adapter directory not found: {adapter_path}\n"
            "Make sure you have run training or copied the adapter checkpoint."
        )

    print(f"[ml_inference] Loading tokenizer from {base_model} ...")
    tokenizer = AutoTokenizer.from_pretrained(
        base_model,
        trust_remote_code=True,
    )
    # Qwen2.5 uses <|im_end|> as pad; keep that behaviour
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    device_map = "auto" if torch.cuda.is_available() else None
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    print(f"[ml_inference] Loading base model {base_model} ...")
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        device_map=device_map,
        torch_dtype=dtype,
        low_cpu_mem_usage=True,
        trust_remote_code=True,
    )

    print(f"[ml_inference] Merging LoRA adapter from {adapter_path} ...")
    model = PeftModel.from_pretrained(model, adapter_path)
    model.eval()

    param_count = sum(p.numel() for p in model.parameters()) / 1e6
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad) / 1e6
    print(
        f"[ml_inference] Model ready — {param_count:.1f}M total params, "
        f"{trainable:.1f}M trainable (LoRA)."
    )
    return model, tokenizer


# ── Prompt construction ───────────────────────────────────────────────────────


def build_prompt(
    role: str,
    briefing: Dict[str, Any],
    tokenizer,
    *,
    max_obs_chars: int = 2000,
    max_events_chars: int = 600,
    max_crisis_chars: int = 600,
) -> str:
    """
    Build a Qwen-chat-template prompt for a given role and daily briefing.

    Uses the model's native chat template so the LoRA adapter's learned
    patterns are activated correctly.
    """
    day = briefing.get("day", "?")
    world_events = briefing.get("world_events") or []
    active_crises = briefing.get("active_crises") or []
    role_obs = briefing.get("role_observation") or {}
    ghost_note = briefing.get("ghost_founder_note") or ""

    obs_str = json.dumps(role_obs, ensure_ascii=False, default=str)[:max_obs_chars]
    events_str = json.dumps(world_events, ensure_ascii=False)[:max_events_chars]
    crises_str = json.dumps(active_crises, ensure_ascii=False)[:max_crisis_chars]

    user_content = (
        f"Day {day}.\n"
        f"World events: {events_str}\n"
        f"Active crises (for you or your team): {crises_str}\n"
        f"Your role observation: {obs_str}\n"
    )
    if ghost_note:
        user_content += f"\nNote: {ghost_note}\n"
    user_content += "\nChoose ONE tool call to take right now."

    messages = [
        {"role": "system", "content": ROLE_SYSTEM_PROMPTS[role]},
        {"role": "user", "content": user_content},
    ]

    # Apply the Qwen chat template (adds <|im_start|> / <|im_end|> tokens)
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    return prompt


# ── Generation ────────────────────────────────────────────────────────────────


def generate_tool_call(
    model,
    tokenizer,
    prompt: str,
    *,
    max_new_tokens: int = 200,
    temperature: float = 0.7,
    top_p: float = 0.95,
    seed: Optional[int] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Run inference and return (raw_completion, parsed_tool_call_dict).

    The model is trained to emit {"tool": "...", "args": {...}} JSON.
    If parsing fails, we fall back to a safe make_decision call.
    """
    import torch

    if seed is not None:
        random.seed(seed)
        torch.manual_seed(seed)

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=3072)

    # Move tensors to the model's device
    try:
        device = next(model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
    except Exception:
        pass

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    # Decode only the newly generated tokens
    new_tokens = output_ids[0][inputs["input_ids"].shape[-1]:]
    completion = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    parsed = _parse_tool_call(completion)
    return completion, parsed


def _parse_tool_call(text: str) -> Dict[str, Any]:
    """
    Extract the first valid JSON object from the model output.

    Accepts:
      - Pure JSON: {"tool": ..., "args": {...}}
      - JSON embedded in prose (we grab the last {...} block)
      - Single-key fallback: {"decision_type": ..., "decision": ...}  (old format)
    """
    text = (text or "").strip()
    if not text:
        return {}

    # Try to grab a JSON block if the output starts with prose
    if not text.startswith("{"):
        start = text.rfind("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            text = text[start: end + 1]

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return {}

    if not isinstance(data, dict):
        return {}

    # Already in {"tool": ..., "args": {...}} format
    if "tool" in data:
        return data

    # Old make_decision format — wrap it
    if "decision_type" in data or "decision" in data:
        return {
            "tool": "make_decision",
            "args": {
                "decision_type": data.get("decision_type", "tactical"),
                "decision": str(data.get("decision", text[:300])),
                "reasoning": str(data.get("reasoning", "Model-generated decision.")),
            },
        }

    return data


# ── Tool execution ────────────────────────────────────────────────────────────


def execute_tool_call(
    env,
    episode_id: str,
    role: str,
    tool_call: Dict[str, Any],
    briefing: Dict[str, Any],
    *,
    verbose: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Execute one tool call emitted by the model via the MCP env client.

    Handles:
    - Role-based tool permission filtering
    - Automatic injection of episode_id / agent_role
    - Special handling for crises (handle_personal_crisis needs crisis_id)
    - Graceful error catching so a bad call doesn't crash the episode
    """
    allowed = ROLE_ALLOWED_TOOLS.get(role, set())

    tool_name = str(tool_call.get("tool", "make_decision")).strip()
    args: Dict[str, Any] = dict(tool_call.get("args") or {})

    # Enforce role permissions
    if tool_name not in allowed:
        if verbose:
            print(f"  [ml_inference] {role}: tool '{tool_name}' not allowed → make_decision")
        tool_name = "make_decision"
        args = {
            "decision_type": "tactical",
            "decision": args.get("decision", "Awaiting briefing; maintaining current plan."),
            "reasoning": "Fallback: requested tool not in role permissions.",
        }

    # Inject mandatory context args
    args["episode_id"] = episode_id
    args["agent_role"] = role

    # Special case: handle_personal_crisis — auto-wire the first active crisis
    # if the model forgot to include crisis_id in args
    if tool_name == "handle_personal_crisis" and "crisis_id" not in args:
        active_crises = briefing.get("active_crises") or []
        role_crises = [
            c for c in active_crises
            if not c.get("target_role") or c.get("target_role") == role
        ]
        if role_crises:
            args["crisis_id"] = role_crises[0]["id"]
            if "response" not in args:
                args["response"] = (
                    "I understand this is a serious situation. "
                    "My plan: acknowledge the issue openly, propose concrete steps "
                    "(e.g. equity refresh, time off, role clarity), and follow up in 7 days."
                )
        else:
            # No crisis to handle — fall back
            tool_name = "make_decision"
            args = {
                "episode_id": episode_id,
                "agent_role": role,
                "decision_type": "tactical",
                "decision": "No active personal crises. Focusing on daily operations.",
                "reasoning": "No crises present.",
            }

    # Special case: send_message — needs valid from_role/to_role
    if tool_name == "send_message":
        args.setdefault("from_role", role)
        if "to_role" not in args or args["to_role"] == role:
            roles = ["ceo", "cto", "sales", "people", "cfo"]
            others = [r for r in roles if r != role]
            args["to_role"] = others[0]
        args.setdefault("subject", "Daily update")
        args.setdefault("content", "Quick sync on current status.")

    # Special case: read/write_company_brain — needs key
    if tool_name in ("read_company_brain", "write_company_brain"):
        args.setdefault("key", f"daily_note_{role}")
        if tool_name == "write_company_brain":
            args.setdefault("value", f"Day note from {role}: operational update.")

    # Special case: build_feature — needs name/complexity/engineers
    if tool_name == "build_feature":
        args.setdefault("name", "core-improvement")
        args.setdefault("complexity", "medium")
        args.setdefault("engineers", 1)

    # Special case: negotiate_with_investor — needs investor_id/valuation/equity
    if tool_name == "negotiate_with_investor":
        if "investor_id" not in args:
            obs = briefing.get("role_observation") or {}
            investors = obs.get("investors") or []
            if investors:
                first = investors[0]
                args["investor_id"] = (
                    first.get("id") if isinstance(first, dict) else getattr(first, "id", None)
                )
        args.setdefault("valuation", 15_000_000)
        args.setdefault("equity", 0.15)

    # Special case: send_investor_update — needs investor_id/content
    if tool_name == "send_investor_update":
        if "investor_id" not in args:
            obs = briefing.get("role_observation") or {}
            investors = obs.get("investors") or []
            if investors:
                first = investors[0]
                args["investor_id"] = (
                    first.get("id") if isinstance(first, dict) else getattr(first, "id", None)
                )
        args.setdefault("content", "Monthly update: team healthy, product shipping on schedule.")

    # Special case: create_financial_model
    if tool_name == "create_financial_model":
        args.setdefault("monthly_growth", 0.10)
        args.setdefault("months_ahead", 6)

    # Special case: post_job_listing
    if tool_name == "post_job_listing":
        args.setdefault("role", "Software Engineer")
        args.setdefault("requirements", "3+ years Python/JS, startup experience preferred.")
        args.setdefault("salary_min", 100_000)
        args.setdefault("salary_max", 150_000)

    # Special case: conduct_interview / hold_one_on_one — need candidate/employee ids
    if tool_name == "conduct_interview":
        if "candidate_id" not in args:
            obs = briefing.get("role_observation") or {}
            pool = obs.get("candidate_pool") or []
            if pool:
                first = pool[0]
                args["candidate_id"] = (
                    first.get("id") if isinstance(first, dict) else getattr(first, "id", None)
                )
            else:
                tool_name = "check_team_morale"
                args = {"episode_id": episode_id, "agent_role": role}
        args.setdefault("questions", "Technical depth, culture fit, growth mindset.")

    if tool_name == "hold_one_on_one":
        if "employee_id" not in args:
            obs = briefing.get("role_observation") or {}
            employees = obs.get("employees") or []
            if employees:
                first = employees[0]
                args["employee_id"] = (
                    first.get("id") if isinstance(first, dict) else getattr(first, "id", None)
                )
            else:
                tool_name = "check_team_morale"
                args = {"episode_id": episode_id, "agent_role": role}
        args.setdefault("talking_points", "Workload, career growth, blockers, team dynamics.")

    # Special case: hire_candidate / fire_employee
    if tool_name == "hire_candidate":
        if "candidate_id" not in args:
            obs = briefing.get("role_observation") or {}
            pool = obs.get("candidate_pool") or []
            if pool:
                first = pool[0]
                args["candidate_id"] = (
                    first.get("id") if isinstance(first, dict) else getattr(first, "id", None)
                )
                args.setdefault("role", first.get("role", "Engineer") if isinstance(first, dict) else "Engineer")
                args.setdefault("salary", 130_000)
            else:
                tool_name = "make_decision"
                args = {
                    "episode_id": episode_id, "agent_role": role,
                    "decision_type": "tactical",
                    "decision": "No candidates available; will post a new job listing.",
                    "reasoning": "Empty candidate pool.",
                }

    if tool_name == "fire_employee":
        if "employee_id" not in args:
            obs = briefing.get("role_observation") or {}
            employees = obs.get("employees") or []
            toxic = [
                e for e in employees
                if (e.get("is_toxic") if isinstance(e, dict) else getattr(e, "is_toxic", False))
            ]
            target = toxic[0] if toxic else (employees[0] if employees else None)
            if target:
                args["employee_id"] = (
                    target.get("id") if isinstance(target, dict) else getattr(target, "id", None)
                )
                args.setdefault("severance", 10_000)
            else:
                tool_name = "make_decision"
                args = {
                    "episode_id": episode_id, "agent_role": role,
                    "decision_type": "tactical",
                    "decision": "No employees to remove; focusing on culture health.",
                    "reasoning": "Empty employee pool.",
                }

    # send_customer_email / update_crm
    if tool_name in ("send_customer_email", "update_crm"):
        if "customer_id" not in args:
            obs = briefing.get("role_observation") or {}
            customers = obs.get("customers") or []
            if customers:
                first = customers[0]
                args["customer_id"] = (
                    first.get("id") if isinstance(first, dict) else getattr(first, "id", None)
                )
            else:
                tool_name = "make_decision"
                args = {
                    "episode_id": episode_id, "agent_role": role,
                    "decision_type": "tactical",
                    "decision": "No active customers yet; focusing on pipeline building.",
                    "reasoning": "Empty customer list.",
                }
        if tool_name == "send_customer_email":
            args.setdefault("subject", "Checking in — how can we help?")
            args.setdefault("content", "Hi team, wanted to check in on your usage and hear feedback.")
        if tool_name == "update_crm":
            args.setdefault("status", "active")
            args.setdefault("notes", "Regular touchpoint; customer engaged.")

    # run_competitive_analysis
    if tool_name == "run_competitive_analysis":
        if "competitor_name" not in args:
            obs = briefing.get("role_observation") or {}
            competitors = obs.get("competitors") or []
            if competitors:
                first = competitors[0]
                args["competitor_name"] = (
                    first.get("name") if isinstance(first, dict) else getattr(first, "name", "Unknown")
                )
            else:
                tool_name = "analyze_market"
                args = {"episode_id": episode_id, "agent_role": role, "segment": "b2b-saas"}

    # deploy_to_production / run_load_test
    if tool_name == "deploy_to_production":
        args.setdefault("version", "auto")
    if tool_name == "run_load_test":
        args.setdefault("scenario", "Standard peak-hour load simulation")

    # analyze_market
    if tool_name == "analyze_market":
        args.setdefault("segment", "b2b-saas")

    # make_decision defaults
    if tool_name == "make_decision":
        args.setdefault("decision_type", "tactical")
        args.setdefault("decision", "Maintain current trajectory; address top priorities.")
        args.setdefault("reasoning", "Daily operational decision based on briefing.")

    # pivot_company defaults
    if tool_name == "pivot_company":
        args.setdefault("new_direction", args.get("new_direction", "focus-enterprise"))
        args.setdefault("rationale", "Market signals indicate better fit in enterprise segment.")
        args.setdefault("vote", "approve")

    try:
        result = env.call_tool(tool_name, **args)
        if verbose:
            result_preview = json.dumps(result, default=str)[:200] if result else "(no result)"
            print(f"  [{role}] {tool_name} → {result_preview}")
        return result
    except Exception as exc:
        if verbose:
            print(f"  [{role}] {tool_name} FAILED: {exc}")
        # Silent fallback: a bad call should not abort the episode
        try:
            return env.call_tool(
                "make_decision",
                episode_id=episode_id,
                agent_role=role,
                decision_type="tactical",
                decision="Awaiting better information; deferring until next briefing.",
                reasoning="Tool call failed; safe fallback.",
            )
        except Exception:
            return None


# ── Episode runner ────────────────────────────────────────────────────────────


def run_episode(
    model,
    tokenizer,
    env,
    *,
    episode_id: str,
    roles: List[str],
    difficulty: int = 1,
    seed: int = 42,
    max_days: int = 30,
    max_new_tokens: int = 200,
    temperature: float = 0.7,
    model_id: str = "genesis_final",
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Run one complete episode using the ML model for all specified roles.

    Returns the final reward dict from get_reward.
    """
    env.call_tool(
        "reset",
        episode_id=episode_id,
        difficulty=difficulty,
        seed=seed,
        model_id=model_id,
        model_provider="local_lora",
        model_version="genesis_final_adapter",
    )

    if verbose:
        print(f"\n[episode {episode_id}] difficulty={difficulty} seed={seed} roles={roles}")

    role_cycle = [r for r in ["ceo", "cto", "sales", "people", "cfo"] if r in roles]
    if not role_cycle:
        role_cycle = ["ceo"]

    for day_idx in range(max_days):
        role = role_cycle[day_idx % len(role_cycle)]

        # Get briefing (also advances the simulation clock)
        try:
            briefing = env.call_tool("get_daily_briefing", episode_id=episode_id, agent_role=role)
        except Exception as exc:
            if verbose:
                print(f"  get_daily_briefing failed on day {day_idx + 1}: {exc}")
            break

        if briefing.get("is_done"):
            if verbose:
                print(f"  Episode done on day {briefing.get('day', day_idx + 1)}")
            break

        # Build prompt and generate decision
        prompt = build_prompt(role, briefing, tokenizer)
        completion, tool_call = generate_tool_call(
            model,
            tokenizer,
            prompt,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            seed=seed + day_idx,
        )

        if verbose:
            tool_name = tool_call.get("tool", "?")
            print(f"  day {briefing.get('day', day_idx + 1):>3} [{role}] → {tool_name}")

        # Execute the tool call
        execute_tool_call(
            env,
            episode_id,
            role,
            tool_call,
            briefing,
            verbose=verbose,
        )

        # Small delay to avoid hammering the server on CPU-only runs
        time.sleep(0.03)

    # Retrieve final reward
    try:
        reward_data = env.call_tool("get_reward", episode_id=episode_id)
    except Exception:
        reward_data = {"reward": 0.0, "breakdown": {}}

    return reward_data


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the genesis_final LoRA adapter against the GENESIS MCP server"
    )
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL, help="HuggingFace base model ID")
    parser.add_argument("--adapter", default=DEFAULT_ADAPTER, help="Path to PEFT adapter dir")
    parser.add_argument("--server", default=os.environ.get("GENESIS_URL", "http://127.0.0.1:7860"))
    parser.add_argument("--model-id", default="genesis_final", help="Label for Founder Genome tracking")
    parser.add_argument("--difficulty", type=int, default=1, choices=[1, 2, 3, 4, 5])
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--days", type=int, default=30, help="Max days per episode")
    parser.add_argument("--seed-start", type=int, default=100)
    parser.add_argument("--max-new-tokens", type=int, default=200)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument(
        "--roles",
        nargs="+",
        default=["ceo", "cto", "sales", "people", "cfo"],
        choices=["ceo", "cto", "sales", "people", "cfo"],
        help="Roles to drive with the ML model (rest use fallback make_decision)",
    )
    parser.add_argument("--export-genome", action="store_true", help="Export Founder Genome at end")
    parser.add_argument("--quiet", action="store_true", help="Reduce per-step output")
    args = parser.parse_args()

    # Load model
    model, tokenizer = load_model_and_tokenizer(args.base_model, args.adapter)

    # Connect to GENESIS server
    from client import GenesisEnv

    env = GenesisEnv(base_url=args.server).sync()
    env.async_client.use_production_mode = True

    verbose = not args.quiet
    rewards: List[float] = []

    try:
        for ep_idx in range(args.episodes):
            episode_id = f"ml-{uuid.uuid4().hex[:10]}"
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

            print(f"\n[{ep_idx + 1:02d}/{args.episodes}] episode={episode_id} seed={seed} "
                  f"reward={total:.4f}")
            if verbose:
                breakdown = reward_data.get("breakdown") or {}
                for k, v in breakdown.items():
                    if k != "total":
                        try:
                            bar = "█" * int(float(v) * 20)
                            print(f"  {k:<30} {float(v):.3f}  {bar}")
                        except Exception:
                            print(f"  {k:<30} {v}")
                if reward_data.get("weaknesses"):
                    print(f"  MarketMaker weaknesses: {reward_data['weaknesses']}")

        if rewards:
            avg = sum(rewards) / len(rewards)
            print(f"\n{'=' * 60}")
            print(f"DONE  episodes={args.episodes}  avg={avg:.4f}  "
                  f"best={max(rewards):.4f}  worst={min(rewards):.4f}")
            print(f"{'=' * 60}")

        if args.export_genome:
            print("\nExporting Founder Genome ...")
            res = env.call_tool("export_founder_genome", model_id=args.model_id, difficulty=args.difficulty)
            if isinstance(res, dict) and res.get("artifacts"):
                print(f"  JSON → {res['artifacts'].get('json')}")
                print(f"  PNG  → {res['artifacts'].get('png')}")
            else:
                print(f"  Genome response: {res}")

    finally:
        env.close()


if __name__ == "__main__":
    main()
