"""
GENESIS — Colab-first GRPO training script (HF TRL).

This script is the canonical Colab entrypoint for the OpenEnv hackathon
submission. It:

  1. Bootstraps deps in Google Colab (no-op when run locally).
  2. Starts the OpenEnv-compliant GENESIS MCP server (server.app:app).
  3. Loads a small instruction-tuned LLM with bitsandbytes (4-bit) + LoRA.
  4. Runs GRPO (TRL) with the GENESIS reward function (an 11-component
     composable rubric served over MCP via `get_reward`).
  5. Logs per-step rewards to JSONL and renders training curves to
     `outputs/evals/training_progress.png` so judges can see learning
     evidence end-to-end without re-running anything.

Designed to work on a free-tier Colab T4 (Qwen2.5-3B-Instruct) and to
"just work" in <10 minutes for a smoke run.

Usage (Colab):
    !python train_colab.py --steps 60

Usage (Colab smoke test, no GPU required):
    !python train_colab.py --smoke

Usage (local laptop, CUDA optional):
    python train_colab.py --steps 30 --fast
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field as dc_field
from typing import Any, Dict, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# 0. Environment guards (must run *before* torch / transformers import)
# ─────────────────────────────────────────────────────────────────────────────
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Disable torch.compile / dynamo / inductor — they require Triton, which is
# absent on Windows wheels and can break on Colab when versions mismatch.
for k in (
    "TORCHDYNAMO_DISABLE",
    "TORCHINDUCTOR_DISABLE",
    "TORCH_COMPILE_DISABLE",
    "DISABLE_TORCH_COMPILE",
):
    os.environ[k] = "1"


# ─────────────────────────────────────────────────────────────────────────────
# 1. Colab dependency bootstrap
# ─────────────────────────────────────────────────────────────────────────────
REPO_URL = "https://github.com/rhine-pereira/meta-hack-finale.git"
COLAB_REPO_DIR = "/content/meta-hack-finale"


def _is_colab() -> bool:
    try:
        import google.colab  # noqa: F401
        return True
    except ImportError:
        return False


def install_dependencies() -> None:
    """Clone repo + install required libs. No-op outside Colab."""
    if not _is_colab():
        return

    print("[setup] Detected Google Colab → bootstrapping environment.")

    def pip(*args: str) -> None:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *args])

    if not os.path.isdir(COLAB_REPO_DIR):
        print(f"[setup] Cloning repo → {COLAB_REPO_DIR}")
        subprocess.check_call(
            ["git", "clone", "--depth=1", REPO_URL, COLAB_REPO_DIR]
        )
    else:
        print(f"[setup] Repo present at {COLAB_REPO_DIR}, pulling latest")
        subprocess.check_call(["git", "-C", COLAB_REPO_DIR, "pull", "--ff-only"])

    os.chdir(COLAB_REPO_DIR)
    if COLAB_REPO_DIR not in sys.path:
        sys.path.insert(0, COLAB_REPO_DIR)

    # Pin torch to whatever Colab already shipped — upgrading torch typically
    # pulls a Triton that emits PTX > T4 ptxas can consume.
    import importlib.metadata
    try:
        _torch_pin = f"torch=={importlib.metadata.version('torch')}"
    except Exception:
        _torch_pin = "torch"

    print("[setup] Installing OpenEnv core + server deps…")
    pip(
        "openenv-core[core]>=0.2.3",
        "fastapi",
        "uvicorn[standard]",
        "fastmcp",
        "requests",
        "numpy",
        "matplotlib",
        "base58",
    )

    print("[setup] Installing HF training stack (TRL / PEFT / bitsandbytes)…")
    pip(_torch_pin, "trl>=0.11.0", "peft>=0.12.0", "bitsandbytes>=0.43.0", "accelerate>=0.34.0", "datasets>=2.20.0", "transformers>=4.44.0")

    print("[setup] Done. If Colab prompts to restart runtime, do it once and re-run.")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Triton mock (for Windows + minimal Colab fallbacks)
# ─────────────────────────────────────────────────────────────────────────────
try:
    import triton  # noqa: F401
except ImportError:
    from importlib.machinery import ModuleSpec
    from unittest.mock import MagicMock

    mock_triton = MagicMock()
    mock_triton.__version__ = "3.0.0"
    mock_triton.__spec__ = ModuleSpec("triton", None)
    mock_triton.__path__ = []
    sys.modules["triton"] = mock_triton
    sys.modules["triton.compiler"] = MagicMock()
    sys.modules["triton.language"] = MagicMock()
    sys.modules["triton.runtime"] = MagicMock()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Argument parsing
# ─────────────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(
    description="Train an LLM on the GENESIS startup environment with TRL GRPO."
)
parser.add_argument("--smoke", action="store_true", help="Skip training; run 5 reward rollouts to verify env+reward.")
parser.add_argument("--steps", type=int, default=60, help="GRPO max optimization steps (default 60).")
parser.add_argument(
    "--model",
    type=str,
    default="Qwen/Qwen2.5-3B-Instruct",
    help=(
        "Base model. Defaults to Qwen2.5-3B-Instruct (loaded in 4-bit via bitsandbytes). "
        "Use 'Qwen/Qwen2.5-7B-Instruct' for an A100."
    ),
)
parser.add_argument("--output", type=str, default="./genesis-checkpoints", help="Adapter checkpoint dir.")
parser.add_argument("--difficulty", type=int, default=1, choices=[1, 2, 3, 4, 5])
parser.add_argument("--episode-days", type=int, default=20, help="Days simulated per training episode.")
parser.add_argument("--num-generations", type=int, default=2, help="GRPO completions per prompt (≥2).")
parser.add_argument("--max-completion-length", type=int, default=160, help="Token budget per completion.")
parser.add_argument("--dataset-multiplier", type=int, default=8, help="Replicate role prompts to size training set.")
parser.add_argument("--skip-briefing", action="store_true", help="Skip get_daily_briefing inside reward rollouts.")
parser.add_argument("--fast", action="store_true", help="Aggressive speed profile (Colab T4 friendly).")
parser.add_argument("--log-dir", type=str, default="outputs/evals", help="Where to write training_log.jsonl + plot.")
parser.add_argument(
    "--reward-min-fraction",
    type=float,
    default=0.0,
    help="If > 0, clamp training rewards into [reward_min_fraction, 1.0] to amplify gradient signal.",
)
args, _ = parser.parse_known_args()


if args.fast:
    if args.num_generations != 2:
        args.num_generations = 2  # GRPO needs ≥ 2 generations to compute advantages
    args.max_completion_length = min(args.max_completion_length, 96)
    args.dataset_multiplier = min(args.dataset_multiplier, 4)
    args.steps = min(args.steps, 40)
    args.episode_days = min(args.episode_days, 12)
    args.skip_briefing = True


# ─────────────────────────────────────────────────────────────────────────────
# 4. Inlined OpenEnv MCP client (so this script is fully self-contained)
# ─────────────────────────────────────────────────────────────────────────────
GenesisEnv = None


def _to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("text", "content", "completion", "response", "prompt"):
            if key in value:
                return _to_text(value[key])
        try:
            return json.dumps(value)
        except Exception:
            return str(value)
    if isinstance(value, list):
        return _to_text(value[0]) if value else ""
    return str(value)


def _init_openenv_client() -> None:
    global GenesisEnv
    if GenesisEnv is not None:
        return

    from openenv.core.mcp_client import MCPToolClient

    class _GenesisEnv(MCPToolClient):
        """OpenEnv MCP client for the GENESIS environment.

        Mirrors the canonical client.py in the repo, inlined here so this
        single file can run on Colab even before the repo has been imported.
        """

        def __init__(self, base_url: str, **kwargs: Any) -> None:
            super().__init__(base_url=base_url, **kwargs)
            self._stateful_session_id: Optional[str] = None

        def _parse_mcp_response(self, raw_text: str) -> Dict[str, Any]:
            text = raw_text.strip()
            if text.startswith("{"):
                return json.loads(text)
            data_lines = [
                line[5:].strip()
                for line in text.splitlines()
                if line.startswith("data:")
            ]
            if not data_lines:
                raise RuntimeError(f"Unable to parse MCP response: {text[:200]}")
            return json.loads(data_lines[-1])

        async def _stateful_mcp_request(
            self, method: str, params: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            client = await self._get_http_client()
            headers = {"accept": "application/json, text/event-stream"}
            if self._stateful_session_id:
                headers["mcp-session-id"] = self._stateful_session_id
            response = await client.post(
                self._production_mcp_url(),
                json={
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": params or {},
                    "id": self._next_request_id(),
                },
                headers=headers,
                timeout=self._message_timeout,
            )
            response.raise_for_status()
            sid = response.headers.get("mcp-session-id")
            if sid:
                self._stateful_session_id = sid
            return self._parse_mcp_response(response.text)

        async def _ensure_stateful_session(self) -> None:
            if self._stateful_session_id:
                return
            data = await self._stateful_mcp_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "genesis-env-client", "version": "0.1.0"},
                },
            )
            if "error" in data:
                raise RuntimeError(f"Failed to initialize MCP session: {data['error']}")

        async def call_tool(self, name: str, **kwargs: Any) -> Any:
            await self._ensure_stateful_session()
            data = await self._stateful_mcp_request(
                "tools/call", {"name": name, "arguments": kwargs}
            )
            if "error" in data:
                raise RuntimeError(f"Tool '{name}' failed: {data['error']}")
            res = data.get("result", {})
            if isinstance(res, dict):
                if res.get("isError"):
                    raise RuntimeError(f"Tool '{name}' returned an error response")
                if "structuredContent" in res:
                    return res["structuredContent"]
                content = res.get("content")
                if isinstance(content, list) and content:
                    text = content[0].get("text") if isinstance(content[0], dict) else None
                    if isinstance(text, str):
                        try:
                            return json.loads(text)
                        except json.JSONDecodeError:
                            return text
                if "data" in res:
                    return res["data"]
            return res

    GenesisEnv = _GenesisEnv


# ─────────────────────────────────────────────────────────────────────────────
# 5. Roles, tool allowlists, scenario templates
# ─────────────────────────────────────────────────────────────────────────────
ROLES: List[str] = ["ceo", "cto", "sales", "people", "cfo"]

ROLE_ALLOWED_TOOLS: Dict[str, set] = {
    "ceo": {
        "make_decision", "write_company_brain", "read_company_brain",
        "analyze_market", "send_message", "pivot_company",
        "check_bank_balance", "negotiate_with_investor",
        "hire_candidate", "fire_employee",
    },
    "cto": {
        "make_decision", "write_company_brain", "read_company_brain",
        "build_feature", "send_message", "check_team_morale",
        "hire_candidate", "fire_employee",
    },
    "sales": {
        "make_decision", "write_company_brain", "read_company_brain",
        "analyze_market", "send_message",
    },
    "people": {
        "make_decision", "write_company_brain", "read_company_brain",
        "check_team_morale", "send_message", "hire_candidate",
        "fire_employee", "handle_personal_crisis",
    },
    "cfo": {
        "make_decision", "write_company_brain", "read_company_brain",
        "check_bank_balance", "send_message", "negotiate_with_investor",
    },
}
ALLOWED_TOOLS = {t for tools in ROLE_ALLOWED_TOOLS.values() for t in tools}

SYSTEM_PROMPT = (
    "You are an AI agent co-founding a B2B SaaS startup inside the GENESIS simulation.\n"
    "Respond with EXACTLY ONE JSON object and nothing else: "
    '{"tool": "<tool_name>", "args": {<arguments>}}\n\n'
    "Reward signal favors: substantive write_company_brain entries (>50 chars), "
    "shipping features, maintaining runway >90d, retaining customers, and resolving "
    "personal crises. Do not narrate; emit the JSON tool call."
)

ROLE_SYSTEM_PROMPTS: Dict[str, str] = {
    "ceo": "You are the CEO. Strategy, fundraising, external comms. Tools: make_decision, write_company_brain, negotiate_with_investor, pivot_company, analyze_market, hire_candidate, fire_employee.",
    "cto": "You are the CTO. Engineering velocity & tech debt. Tools: build_feature, write_company_brain, check_team_morale, hire_candidate, fire_employee, send_message.",
    "sales": "You are Head of Sales. Revenue & customer relationships. Tools: analyze_market, write_company_brain, make_decision, send_message.",
    "people": "You are Head of People. Hiring quality, morale, conflict resolution. Tools: check_team_morale, hire_candidate, handle_personal_crisis, write_company_brain, fire_employee, send_message.",
    "cfo": "You are the CFO. Runway, burn, fundraising prep. Tools: check_bank_balance, negotiate_with_investor, write_company_brain, make_decision, send_message.",
}

ROLE_BRAIN_KEY_HINTS: Dict[str, str] = {
    "ceo":    "strategy_overview, series_a_plan, competitive_response",
    "cto":    "tech_roadmap, debt_reduction_plan, feature_priorities",
    "sales":  "gtm_strategy, icp_definition, customer_feedback",
    "people": "people_ops, hiring_plan, morale_initiatives",
    "cfo":    "financial_model, burn_rate_analysis, fundraising_timeline",
}

DAY_SCENARIOS = [
    "Day {day}. Cash: ${cash:,.0f}. Burn: ${burn}/day. Runway: {runway}d. "
    "Employees: {employees}. Customers: {customers}. MRR: ${mrr:,.0f}. "
    "Brain entries so far: {brain_entries}. Brain keys to consider: {brain_keys}. "
    "What is your single most important action today?",

    "Day {day}. ALERT — {crisis}. Cash: ${cash:,.0f}. Morale: {morale:.0%}. "
    "Brain entries: {brain_entries}. Respond and (if helpful) record your strategy.",

    "Day {day}. Series A prep. ARR: ${arr:,.0f}. Investor {investor} sentiment {sentiment:.0%}. "
    "Runway: {runway}d. Brain entries: {brain_entries}. What is the next fundraising action?",

    "Day {day}. Growth milestone — MRR crossed ${mrr:,.0f}. Burn ${burn}/day. "
    "Tech debt {tech_debt:.0%}. Brain entries {brain_entries}. "
    "What should the {role} prioritise to accelerate growth without risking runway?",
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


# ─────────────────────────────────────────────────────────────────────────────
# 6. Self-play / curriculum state
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class SelfPlayState:
    episode_rewards: List[float] = dc_field(default_factory=list)
    detected_weaknesses: List[str] = dc_field(default_factory=list)
    current_difficulty: int = args.difficulty
    episodes_at_current_level: int = 0
    PROMOTE_THRESHOLD: float = 0.55
    DEMOTE_THRESHOLD: float = 0.30
    WINDOW: int = 8

    def record(self, reward: float, weaknesses: List[str]) -> None:
        self.episode_rewards.append(reward)
        for w in weaknesses:
            if w not in self.detected_weaknesses:
                self.detected_weaknesses.append(w)
        self.episodes_at_current_level += 1

    def maybe_advance(self) -> int:
        if len(self.episode_rewards) < self.WINDOW:
            return self.current_difficulty
        recent = sum(self.episode_rewards[-self.WINDOW:]) / self.WINDOW
        if recent > self.PROMOTE_THRESHOLD and self.current_difficulty < 5:
            self.current_difficulty += 1
            self.episodes_at_current_level = 0
            print(f"[MarketMaker] ⬆ promoted to L{self.current_difficulty} (avg={recent:.3f})")
        elif recent < self.DEMOTE_THRESHOLD and self.current_difficulty > 1:
            self.current_difficulty -= 1
            self.episodes_at_current_level = 0
            print(f"[MarketMaker] ⬇ demoted to L{self.current_difficulty} (avg={recent:.3f})")
        return self.current_difficulty


_self_play = SelfPlayState()
_shared_env = None


def _get_shared_env():
    global _shared_env
    _init_openenv_client()
    if _shared_env is None:
        _shared_env = GenesisEnv(base_url="http://127.0.0.1:7860").sync()
        _shared_env.async_client.use_production_mode = True
    return _shared_env


def _close_shared_env() -> None:
    global _shared_env
    if _shared_env is not None:
        try:
            _shared_env.close()
        except Exception:
            pass
        _shared_env = None


# ─────────────────────────────────────────────────────────────────────────────
# 7. Tool-call parsing + multi-day rollout
# ─────────────────────────────────────────────────────────────────────────────
def _parse_tool_calls(text: str, role: str) -> List[Dict[str, Any]]:
    """Parse model output into tool-call dicts. Tolerates plain text."""
    text = (text or "").strip()
    allowed = ROLE_ALLOWED_TOOLS.get(role, ALLOWED_TOOLS)

    # Try to strip ``` fences if the model wrote them anyway.
    if text.startswith("```"):
        text = text.strip("` \n")
        if text.startswith("json"):
            text = text[4:].strip()

    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return [{
            "tool": "make_decision",
            "args": {
                "decision_type": "tactical",
                "decision": text[:280] or "Continue executing the current plan.",
                "reasoning": "Model emitted non-JSON output.",
            },
        }]

    if isinstance(parsed, dict):
        parsed = [parsed]

    calls: List[Dict[str, Any]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        tool = item.get("tool", "make_decision")
        if tool not in allowed:
            tool = "make_decision"
        tool_args = item.get("args", {}) if isinstance(item.get("args"), dict) else {}
        calls.append({"tool": tool, "args": tool_args})

    if not calls:
        calls.append({
            "tool": "make_decision",
            "args": {"decision_type": "tactical", "decision": "Continue with current plan.", "reasoning": "Empty parse."},
        })
    return calls


def run_episode(
    role: str,
    action_text: str,
    seed: int = 42,
    difficulty_override: Optional[int] = None,
) -> tuple[dict, List[str]]:
    """Run a multi-day mini-episode and return (reward_data, weaknesses)."""
    env = _get_shared_env()
    episode_id = str(uuid.uuid4())
    eff_difficulty = difficulty_override or _self_play.current_difficulty

    env.call_tool("reset", episode_id=episode_id, difficulty=eff_difficulty, seed=seed)
    tool_calls = _parse_tool_calls(action_text, role)

    for day in range(args.episode_days):
        if not args.skip_briefing:
            try:
                obs = env.call_tool("get_daily_briefing", episode_id=episode_id, agent_role=role)
                if isinstance(obs, dict) and obs.get("is_done"):
                    break
            except Exception:
                pass

        call = tool_calls[day % len(tool_calls)]
        tool_name = call["tool"]
        tool_args = dict(call["args"])
        tool_args["episode_id"] = episode_id
        tool_args["agent_role"] = role
        try:
            env.call_tool(tool_name, **tool_args)
        except Exception:
            # Bad arg shapes get swallowed during training; reward still computed.
            pass

    reward_data = env.call_tool("get_reward", episode_id=episode_id)
    if not isinstance(reward_data, dict):
        reward_data = {"reward": 0.0, "weaknesses": []}
    return reward_data, list(reward_data.get("weaknesses", []))


# ─────────────────────────────────────────────────────────────────────────────
# 8. GRPO reward function + training-time logging
# ─────────────────────────────────────────────────────────────────────────────
_log_path: Optional[str] = None
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


def _extract_role(prompt: str) -> str:
    p = (prompt or "").lower()
    for r in ROLES:
        if f"you are the {r}" in p or f"you are {r}" in p:
            return r
    return "ceo"


def genesis_reward_fn(completions: List[Any], prompts: List[Any], **kwargs) -> List[float]:
    """GRPO reward function: roll a mini-episode and return total ∈ [0, 1]."""
    log_path = _ensure_log_dir()
    rewards: List[float] = []

    for completion, prompt in zip(completions, prompts):
        prompt_text = _to_text(prompt)
        completion_text = _to_text(completion)
        role = _extract_role(prompt_text)
        seed = random.randint(0, 2**31 - 1)

        try:
            reward_data, weaknesses = run_episode(
                role=role,
                action_text=completion_text,
                seed=seed,
                difficulty_override=_self_play.current_difficulty,
            )
            reward = float(reward_data.get("reward", 0.0))
            breakdown = reward_data.get("breakdown", {}) if isinstance(reward_data, dict) else {}
            _self_play.record(reward, weaknesses)
            _self_play.maybe_advance()
        except Exception as e:
            print(f"[reward_fn] episode failed: {e}", file=sys.stderr)
            reward = 0.0
            breakdown = {}
            weaknesses = []

        if args.reward_min_fraction > 0:
            reward = max(args.reward_min_fraction, reward)

        rewards.append(reward)
        _step_counter["n"] += 1
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "step": _step_counter["n"],
                "role": role,
                "reward": reward,
                "difficulty": _self_play.current_difficulty,
                "completion_preview": completion_text[:160],
                "breakdown": {k: float(v) for k, v in breakdown.items() if isinstance(v, (int, float))},
                "weaknesses": weaknesses,
            }) + "\n")

    return rewards


# ─────────────────────────────────────────────────────────────────────────────
# 9. Dataset construction
# ─────────────────────────────────────────────────────────────────────────────
def build_dataset(n_samples: int = 200) -> List[Dict[str, Any]]:
    """Synthesize role-aware startup scenarios. Lives entirely in-process."""
    out: List[Dict[str, Any]] = []
    rng = random.Random(42)

    for i in range(n_samples):
        role = rng.choice(ROLES)
        day = rng.randint(1, 90)
        cash = rng.uniform(50_000, 500_000)
        burn = rng.randint(3_000, 8_000)
        runway = int(cash / burn)
        scenario = DAY_SCENARIOS[i % len(DAY_SCENARIOS)].format(
            day=day,
            cash=cash,
            burn=burn,
            runway=runway,
            employees=rng.randint(2, 15),
            customers=rng.randint(0, 20),
            mrr=rng.uniform(0, 50_000),
            arr=rng.uniform(0, 50_000) * 12,
            morale=rng.uniform(0.3, 0.9),
            crisis=rng.choice(CRISIS_TEMPLATES),
            investor=rng.choice(INVESTOR_NAMES),
            sentiment=rng.uniform(0.3, 0.9),
            brain_entries=rng.randint(0, 8),
            brain_keys=ROLE_BRAIN_KEY_HINTS.get(role, "strategy_overview"),
            tech_debt=rng.uniform(0.1, 0.7),
            role=role,
        )
        out.append({
            "messages": [
                {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{ROLE_SYSTEM_PROMPTS[role]}"},
                {"role": "user", "content": scenario},
            ],
            "role": role,
            "day": day,
        })

    return out


# ─────────────────────────────────────────────────────────────────────────────
# 10. Training-curve plotting
# ─────────────────────────────────────────────────────────────────────────────
def plot_training_progress() -> Optional[str]:
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


# ─────────────────────────────────────────────────────────────────────────────
# 11. Smoke test
# ─────────────────────────────────────────────────────────────────────────────
def smoke_test() -> None:
    print("=" * 60)
    print("GENESIS Colab Trainer — Smoke Test (no GPU required)")
    print("=" * 60)
    cases = [
        ("ceo",    '{"tool": "make_decision", "args": {"decision_type": "strategic", "decision": "Focus on Series A fundraising", "reasoning": "Runway is below 6 months"}}'),
        ("cto",    '{"tool": "build_feature", "args": {"name": "SSO Integration", "complexity": "medium", "engineers": 2}}'),
        ("sales",  '{"tool": "write_company_brain", "args": {"key": "go_to_market", "value": "Focus on mid-market B2B SaaS, 50–200 employees, US + EU."}}'),
        ("people", '{"tool": "make_decision", "args": {"decision_type": "tactical", "decision": "Schedule 1:1s with all engineers this week", "reasoning": "Morale dropping"}}'),
        ("cfo",    '{"tool": "write_company_brain", "args": {"key": "financial_model", "value": "Burn $5K/day; need $2M Series A in 90d to hold 12-month runway."}}'),
    ]
    for role, action in cases:
        data, weak = run_episode(role=role, action_text=action, seed=42)
        r = float(data.get("reward", 0.0))
        _self_play.record(r, weak)
        print(f"\n  role={role:<6} reward={r:.4f}  weaknesses={weak}")
        for k, v in (data.get("breakdown") or {}).items():
            if k != "total" and isinstance(v, (int, float)) and v > 0:
                print(f"    {k:<26} {v:.3f}")
    rewards = genesis_reward_fn(
        completions=[cases[0][1]],
        prompts=["Day 1. You are the CEO of a startup. What do you do?"],
    )
    assert len(rewards) == 1 and 0.0 <= rewards[0] <= 1.0
    print(f"\n  genesis_reward_fn → {rewards[0]:.4f}  [OK]")
    print("=" * 60)
    print("Smoke test passed.")
    print("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# 12. Training (HF TRL + bitsandbytes)
# ─────────────────────────────────────────────────────────────────────────────
def _load_model(model_name: str):
    """Load model with bitsandbytes 4-bit quantization + LoRA."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig, TaskType, get_peft_model

    print(f"[hf] loading {model_name} (bnb 4-bit)…")
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb,
        device_map="auto",
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
    )
    model.config.use_cache = False
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = get_peft_model(model, LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    ))
    return model, tokenizer


def train() -> None:
    print("=" * 60)
    print("GENESIS — GRPO Training")
    print(f"  model      = {args.model}")
    print(f"  steps      = {args.steps}")
    print(f"  num_gens   = {args.num_generations}")
    print(f"  ep_days    = {args.episode_days}")
    print(f"  difficulty = {args.difficulty}")
    print(f"  output     = {args.output}")
    print(f"  log_dir    = {args.log_dir}")
    print("=" * 60)

    try:
        from trl import GRPOConfig, GRPOTrainer
        from datasets import Dataset
    except ImportError as e:
        print(f"[ERROR] missing dependency: {e}")
        print("Run: pip install trl transformers peft bitsandbytes accelerate datasets")
        sys.exit(1)

    model, tokenizer = _load_model(args.model)
    try:
        model.print_trainable_parameters()
    except Exception:
        pass

    print("\n[data] building dataset…")
    raw = build_dataset(n_samples=max(args.steps * 2, 200) * args.dataset_multiplier)

    def format_sample(s: Dict[str, Any]) -> Dict[str, Any]:
        prompt = tokenizer.apply_chat_template(
            s["messages"], tokenize=False, add_generation_prompt=True
        )
        return {"prompt": prompt, "role": s["role"]}

    dataset = Dataset.from_list(raw).map(format_sample)
    print(f"[data] {len(dataset)} prompts")

    grad_accum = max(1, args.num_generations * (2 if args.fast else 4))

    grpo_args = GRPOConfig(
        output_dir=args.output,
        max_steps=args.steps,
        num_generations=args.num_generations,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=grad_accum,
        learning_rate=5e-5,
        warmup_ratio=0.05,
        lr_scheduler_type="cosine",
        optim="adamw_8bit",
        fp16=False,
        bf16=False,
        logging_steps=5 if not args.fast else 10,
        report_to="none",
        max_prompt_length=1024,
        max_completion_length=args.max_completion_length,
        seed=42,
    )

    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        args=grpo_args,
        train_dataset=dataset,
        reward_funcs=genesis_reward_fn,
    )

    print("\n[train] launching GRPO…")
    t0 = time.time()
    trainer.train()
    print(f"[train] done in {time.time() - t0:.1f}s")

    save_path = os.path.join(args.output, "final")
    model.save_pretrained(save_path)
    tokenizer.save_pretrained(save_path)
    print(f"[save] adapter → {save_path}")

    # Render training-evidence plot directly so the Colab notebook displays it.
    plot_training_progress()

    # Final post-training rollout for a quick eyeball metric.
    print("\n[eval] post-training rollout (CEO)…")
    eval_data, _ = run_episode(
        role="ceo",
        action_text='{"tool": "write_company_brain", "args": {"key": "strategy_overview", "value": "Focus on enterprise Series A fundraising while maintaining 18-month runway."}}',
        seed=999,
    )
    print(f"[eval] post-training reward = {float(eval_data.get('reward', 0.0)):.4f}")


# ─────────────────────────────────────────────────────────────────────────────
# 13. Server lifecycle
# ─────────────────────────────────────────────────────────────────────────────
def _wait_for_server(url: str = "http://127.0.0.1:7860", max_s: int = 30) -> bool:
    import requests
    for _ in range(max_s):
        try:
            r = requests.get(f"{url}/mcp", timeout=2)
            if r.status_code in (200, 405, 406):
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    return False


# ─────────────────────────────────────────────────────────────────────────────
# 14. Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    install_dependencies()
    _init_openenv_client()

    # Make sure CWD = repo root inside Colab so server.app:app is importable.
    if _is_colab() and os.path.isdir(COLAB_REPO_DIR):
        os.chdir(COLAB_REPO_DIR)
        if COLAB_REPO_DIR not in sys.path:
            sys.path.insert(0, COLAB_REPO_DIR)

    # Stale session pickle can poison plots from the previous run.
    if os.path.exists("sessions.pkl"):
        try:
            os.remove("sessions.pkl")
        except OSError:
            pass

    server_log_path = "/tmp/genesis_server.log" if os.path.isdir("/tmp") else None
    server_log = open(server_log_path, "w") if server_log_path else subprocess.DEVNULL

    print("[server] starting `uvicorn server.app:app` on :7860 …")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.app:app",
         "--host", "127.0.0.1", "--port", "7860", "--log-level", "warning"],
        stdout=server_log, stderr=server_log,
    )

    try:
        if not _wait_for_server():
            if server_log_path:
                try:
                    server_log.flush()
                    with open(server_log_path) as f:
                        tail = f.read()[-3000:]
                    print("\n--- server startup log ---\n" + tail + "\n--- end ---")
                except Exception:
                    pass
            raise RuntimeError("GENESIS server did not become ready within 30 s.")
        print("[server] ready.")

        if args.smoke:
            smoke_test()
        else:
            train()

    finally:
        _close_shared_env()
        print("[server] shutting down…")
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        if hasattr(server_log, "close"):
            server_log.close()
