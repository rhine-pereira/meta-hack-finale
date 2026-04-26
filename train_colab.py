import sys
import os
import subprocess
import time
import json
import uuid
import argparse
from dataclasses import dataclass, field as dc_field
from typing import Any, Dict, Optional

# ── Colab Dependency Installation ─────────────────────────────────────────────
REPO_URL = "https://github.com/rhine-pereira/meta-hack-finale.git"
COLAB_REPO_DIR = "/content/meta-hack-finale"

def install_dependencies():
    """Clone repo + install required libraries when running in Google Colab."""
    try:
        import google.colab
        print("Detected Google Colab. Setting up environment...")

        def pip(*args):
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *args])

        # 0. Clone the project repo so server/ modules are available
        if not os.path.isdir(COLAB_REPO_DIR):
            print(f"  [0/3] Cloning repo → {COLAB_REPO_DIR} ...")
            subprocess.check_call(["git", "clone", "--depth=1", REPO_URL, COLAB_REPO_DIR])
        else:
            print(f"  [0/3] Repo already cloned at {COLAB_REPO_DIR}, pulling latest...")
            subprocess.check_call(["git", "-C", COLAB_REPO_DIR, "pull", "--ff-only"])

        # Switch CWD to repo root so `server.app` is importable and relative paths work
        os.chdir(COLAB_REPO_DIR)
        if COLAB_REPO_DIR not in sys.path:
            sys.path.insert(0, COLAB_REPO_DIR)

        # Colab already has CUDA-enabled PyTorch + Triton — do NOT let pip upgrade them.
        # Upgrading torch pulls in a newer Triton that generates PTX 8.7, but Colab's T4
        # CUDA toolkit ptxas only supports up to PTX 8.4 → PTXASError at runtime.
        import importlib.metadata
        _torch_pin = f"torch=={importlib.metadata.version('torch')}"

        # 1. Core Simulation & OpenEnv
        print("  [1/3] Installing OpenEnv + server deps...")
        # base58 is required by server/proof/solana_client.py even if you never call Solana tools
        pip("openenv-core[core]>=0.2.3", "fastapi", "uvicorn", "requests", "fastmcp", "base58")

        # 2. HF training stack — torch pinned to prevent Triton upgrade
        print("  [2/3] Installing trl / peft / bitsandbytes / accelerate...")
        pip(_torch_pin, "trl", "peft", "bitsandbytes", "accelerate")

        print("  [3/3] Dependencies complete.")
        print("Installation complete. Restart runtime now if prompted about version conflicts.")
    except ImportError:
        pass

# ── Windows/Colab Triton Mock ─────────────────────────────────────────────────
try:
    import triton
except ImportError:
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

# ── Inlined OpenEnv Client (GenesisEnv) ───────────────────────────────────────
# Kept lazy so Colab dependency installation can run before import resolution.
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
        if not value:
            return ""
        return _to_text(value[0])
    return str(value)


def _init_openenv_client() -> None:
    global GenesisEnv
    if GenesisEnv is not None:
        return

    from openenv.core.mcp_client import MCPToolClient

    class _GenesisEnv(MCPToolClient):
        """Client for the GENESIS Startup Gauntlet Environment."""

        def __init__(self, base_url: str, **kwargs):
            super().__init__(base_url=base_url, **kwargs)
            self._stateful_session_id: Optional[str] = None

        def _parse_mcp_response(self, raw_text: str) -> Dict[str, Any]:
            text = raw_text.strip()
            if text.startswith("{"):
                return json.loads(text)
            data_lines = [line[5:].strip() for line in text.splitlines() if line.startswith("data:")]
            if not data_lines:
                raise RuntimeError(f"Unable to parse MCP response: {text[:200]}")
            return json.loads(data_lines[-1])

        async def _stateful_mcp_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
                raise RuntimeError(f"Failed to initialize: {data['error']}")

        async def call_tool(self, name: str, **kwargs: Any) -> Any:
            await self._ensure_stateful_session()
            data = await self._stateful_mcp_request("tools/call", {"name": name, "arguments": kwargs})
            if "error" in data:
                raise RuntimeError(f"Tool '{name}' failed: {data['error']}")
            res = data.get("result", {})
            if isinstance(res, dict) and "content" in res:
                content = res["content"]
                if isinstance(content, list) and content:
                    text = content[0].get("text")
                    try:
                        return json.loads(text)
                    except Exception:
                        return text
            return res

    GenesisEnv = _GenesisEnv

# ── Argument Parsing ──────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Train LLMs on GENESIS startup simulation")
parser.add_argument("--smoke", action="store_true", help="Run a smoke test without training")
parser.add_argument("--steps", type=int, default=200, help="Max training steps")
parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-3B-Instruct",
                    help="Model to fine-tune. 3B fits on a free Colab T4 (15 GB).")
parser.add_argument("--output", type=str, default="./genesis-checkpoints", help="Output directory")
parser.add_argument("--difficulty", type=int, default=1, choices=[1, 2, 3, 4, 5])
parser.add_argument("--episode-days", type=int, default=30)
parser.add_argument("--num-generations", type=int, default=2,
                    help="Completions per prompt. 2 is safe on T4; increase to 4 on A100.")
parser.add_argument("--max-completion-length", type=int, default=128,
                    help="Token budget per completion. Lower is faster.")
parser.add_argument("--dataset-multiplier", type=int, default=20,
                    help="How many role prompts to replicate in the synthetic train set.")
parser.add_argument("--skip-briefing", action="store_true",
                    help="Skip get_daily_briefing in reward rollouts to reduce MCP calls.")
parser.add_argument("--fast", action="store_true",
                    help="Apply a speed-first training profile (fewer generations, shorter completions, less overhead).")
args, _ = parser.parse_known_args()

if args.fast:
    # GRPO requires >=2 generations per prompt (advantage calculation).
    if args.num_generations != 2:
        args.num_generations = 2
    if args.max_completion_length > 96:
        args.max_completion_length = 96
    if args.dataset_multiplier > 8:
        args.dataset_multiplier = 8
    if args.steps > 100:
        args.steps = 100
    args.skip_briefing = True

# ── Training Helpers ──────────────────────────────────────────────────────────
ROLES = ["ceo", "cto", "sales", "people", "cfo"]
ALLOWED_TOOLS = {"make_decision", "build_feature", "write_company_brain", "read_company_brain", "check_bank_balance", "check_team_morale", "analyze_market", "send_message", "hire_candidate", "fire_employee", "negotiate_with_investor", "handle_personal_crisis", "pivot_company"}

@dataclass
class SelfPlayState:
    episode_rewards: list[float] = dc_field(default_factory=list)
    detected_weaknesses: list[str] = dc_field(default_factory=list)
    current_difficulty: int = args.difficulty
    episodes_at_current_level: int = 0
    WINDOW: int = 10

    def record(self, reward: float, weaknesses: list[str]) -> None:
        self.episode_rewards.append(reward)
        for w in weaknesses:
            if w not in self.detected_weaknesses: self.detected_weaknesses.append(w)
        self.episodes_at_current_level += 1

    def next_difficulty(self) -> int:
        if len(self.episode_rewards) < self.WINDOW: return self.current_difficulty
        recent_avg = sum(self.episode_rewards[-self.WINDOW:]) / self.WINDOW
        if recent_avg > 0.65 and self.current_difficulty < 5:
            self.current_difficulty += 1
            print(f"[MarketMaker] ⬆ Promoted to difficulty {self.current_difficulty}")
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

def run_episode(role: str, action_text: Any, seed: int = 42) -> tuple[dict, list[str]]:
    env = _get_shared_env()
    try:
        eid = str(uuid.uuid4())
        env.call_tool("reset", episode_id=eid, difficulty=_self_play.current_difficulty, seed=seed)
        if not args.skip_briefing:
            env.call_tool("get_daily_briefing", episode_id=eid, agent_role=role)
        # Execute action (simplified for standalone use)
        try:
            call_payload = action_text
            if not isinstance(call_payload, (dict, list)):
                call_payload = json.loads(_to_text(action_text))

            if isinstance(call_payload, list):
                call_payload = call_payload[0] if call_payload else {}

            if not isinstance(call_payload, dict):
                call_payload = {}

            tool_name = call_payload.get("tool", "make_decision")
            tool_args = call_payload.get("args", {})
            if not isinstance(tool_args, dict):
                tool_args = {}

            if tool_name not in ALLOWED_TOOLS:
                tool_name = "make_decision"
                tool_args = {"decision": "Continue with current plan and monitor risk."}

            env.call_tool(tool_name, episode_id=eid, agent_role=role, **tool_args)
        except Exception:
            pass
        reward_data = env.call_tool("get_reward", episode_id=eid)
    finally:
        pass
    return reward_data, reward_data.get("weaknesses", [])

def genesis_reward_fn(completions, prompts, **kwargs):
    rewards = []
    for comp, prompt in zip(completions, prompts):
        try:
            prompt_text = _to_text(prompt).lower()
            completion_text = _to_text(comp)

            role = "ceo" # Simplified role detection
            for r in ROLES:
                if r in prompt_text:
                    role = r
                    break
            data, weaknesses = run_episode(role, completion_text)
            reward = float(data.get("reward", 0.0))
            _self_play.record(reward, weaknesses)
            rewards.append(reward)
        except Exception:
            rewards.append(0.0)
    return rewards

# ── Main Training Loop ────────────────────────────────────────────────────────
def train():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import get_peft_model, LoraConfig, TaskType
    from trl import GRPOConfig, GRPOTrainer
    from datasets import Dataset

    print(f"\nLoading {args.model}...")

    # 4-bit quantization config
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
    tokenizer.pad_token = tokenizer.eos_token # Standard for Qwen/Llama

    # LoRA config
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    print("\nBuilding dataset...")
    dataset = Dataset.from_list(
        [{"prompt": f"You are the {r}. Day 1. Cash: $100k. What is your action?", "role": r} for r in ROLES]
        * args.dataset_multiplier
    )

    grad_accum = max(1, args.num_generations * (2 if args.fast else 4))

    training_args = GRPOConfig(
        output_dir=args.output,
        max_steps=args.steps,
        num_generations=args.num_generations,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=grad_accum,
        learning_rate=5e-5,
        max_completion_length=args.max_completion_length,
        fp16=False,
        bf16=False,
        logging_steps=20 if args.fast else 5,
        report_to="none",
    )

    trainer = GRPOTrainer(model=model, processing_class=tokenizer, args=training_args, train_dataset=dataset, reward_funcs=genesis_reward_fn)
    print("\nStarting training...")
    trainer.train()
    model.save_pretrained(f"{args.output}/final")
    tokenizer.save_pretrained(f"{args.output}/final")
    print(f"\nTraining complete. Saved to {args.output}/final")

# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    install_dependencies()
    _init_openenv_client()

    # Ensure we're in the repo root even when install step was skipped (re-runs)
    try:
        import google.colab
        if os.path.isdir(COLAB_REPO_DIR):
            os.chdir(COLAB_REPO_DIR)
            if COLAB_REPO_DIR not in sys.path:
                sys.path.insert(0, COLAB_REPO_DIR)
    except ImportError:
        pass

    # Start server — log to file so startup errors are visible on failure
    server_log = open("/tmp/genesis_server.log", "w") if os.path.exists("/tmp") else subprocess.DEVNULL
    print("Starting GENESIS OpenEnv server...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.app:app", "--host", "127.0.0.1", "--port", "7860"],
        stdout=server_log, stderr=server_log,
    )

    try:
        # Wait up to 30 s for server to become ready
        import requests
        ready = False
        for i in range(30):
            try:
                if requests.get("http://127.0.0.1:7860/mcp", timeout=2).status_code in (200, 405, 406):
                    ready = True
                    break
            except Exception:
                pass
            time.sleep(1)

        if not ready:
            # Dump server log to help diagnose startup failures
            try:
                if hasattr(server_log, "name"):
                    server_log.flush()
                    with open(server_log.name) as f:
                        print("\n--- Server startup log ---")
                        print(f.read()[-3000:])
                        print("--- End server log ---\n")
            except Exception:
                pass
            raise RuntimeError("GENESIS server did not start within 30 s. See server log above.")

        if args.smoke:
            print("Running smoke test...")
            run_episode("ceo", '{"tool": "make_decision", "args": {"decision": "test"}}')
            print("Smoke test passed!")
        else:
            train()
    finally:
        _close_shared_env()
        print("Shutting down server...")
        proc.terminate()
        proc.wait()
        if hasattr(server_log, "close"):
            server_log.close()
