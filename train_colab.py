import sys
import os
import subprocess
import time
import json
import random
import uuid
import argparse
from dataclasses import dataclass, field as dc_field

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
        pip("openenv-core[core]>=0.2.3", "fastapi", "uvicorn", "requests", "fastmcp")

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
# This removes the dependency on an external client.py file for Colab use.
from openenv.core.mcp_client import MCPToolClient
from openenv.core.env_server.mcp_types import Tool
from typing import Any, Dict, List, Optional

class GenesisEnv(MCPToolClient):
    """Client for the GENESIS Startup Gauntlet Environment."""
    def __init__(self, base_url: str, **kwargs):
        super().__init__(base_url=base_url, **kwargs)
        self._stateful_session_id: Optional[str] = None

    def _parse_mcp_response(self, raw_text: str) -> Dict[str, Any]:
        text = raw_text.strip()
        if text.startswith("{"): return json.loads(text)
        data_lines = [line[5:].strip() for line in text.splitlines() if line.startswith("data:")]
        if not data_lines: raise RuntimeError(f"Unable to parse MCP response: {text[:200]}")
        return json.loads(data_lines[-1])

    async def _stateful_mcp_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        client = await self._get_http_client()
        headers = {"accept": "application/json, text/event-stream"}
        if self._stateful_session_id: headers["mcp-session-id"] = self._stateful_session_id
        response = await client.post(self._production_mcp_url(), json={
            "jsonrpc": "2.0", "method": method, "params": params or {}, "id": self._next_request_id()
        }, headers=headers, timeout=self._message_timeout)
        response.raise_for_status()
        sid = response.headers.get("mcp-session-id")
        if sid: self._stateful_session_id = sid
        return self._parse_mcp_response(response.text)

    async def _ensure_stateful_session(self) -> None:
        if self._stateful_session_id: return
        data = await self._stateful_mcp_request("initialize", {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "genesis-env-client", "version": "0.1.0"}
        })
        if "error" in data: raise RuntimeError(f"Failed to initialize: {data['error']}")

    async def call_tool(self, name: str, **kwargs: Any) -> Any:
        await self._ensure_stateful_session()
        data = await self._stateful_mcp_request("tools/call", {"name": name, "arguments": kwargs})
        if "error" in data: raise RuntimeError(f"Tool '{name}' failed: {data['error']}")
        res = data.get("result", {})
        if isinstance(res, dict) and "content" in res:
            content = res["content"]
            if isinstance(content, list) and content:
                text = content[0].get("text")
                try: return json.loads(text)
                except: return text
        return res

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
args, _ = parser.parse_known_args()

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

def run_episode(role: str, action_text: str, seed: int = 42) -> tuple[dict, list[str]]:
    env = GenesisEnv(base_url="http://127.0.0.1:7860").sync()
    env.async_client.use_production_mode = True
    try:
        eid = str(uuid.uuid4())
        env.call_tool("reset", episode_id=eid, difficulty=_self_play.current_difficulty, seed=seed)
        obs = env.call_tool("get_daily_briefing", episode_id=eid, agent_role=role)
        # Execute action (simplified for standalone use)
        try:
            call = json.loads(action_text)
            if isinstance(call, list): call = call[0]
            env.call_tool(call.get("tool", "make_decision"), episode_id=eid, agent_role=role, **call.get("args", {}))
        except: pass
        reward_data = env.call_tool("get_reward", episode_id=eid)
    finally: env.close()
    return reward_data, reward_data.get("weaknesses", [])

def genesis_reward_fn(completions, prompts, **kwargs):
    rewards = []
    for comp, prompt in zip(completions, prompts):
        try:
            role = "ceo" # Simplified role detection
            for r in ROLES:
                if r in prompt.lower(): role = r; break
            data, weaknesses = run_episode(role, comp)
            reward = float(data.get("reward", 0.0))
            _self_play.record(reward, weaknesses)
            rewards.append(reward)
        except: rewards.append(0.0)
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
    )
    
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
    dataset = Dataset.from_list([{"prompt": f"You are the {r}. Day 1. Cash: $100k. What is your action?", "role": r} for r in ROLES] * 20)

    training_args = GRPOConfig(
        output_dir=args.output,
        max_steps=args.steps,
        num_generations=args.num_generations,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=args.num_generations * 4,
        learning_rate=5e-5,
        max_completion_length=256,
        fp16=False,
        bf16=False,
        logging_steps=5,
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
        print("Shutting down server...")
        proc.terminate()
        proc.wait()
        if hasattr(server_log, "close"):
            server_log.close()
