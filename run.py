"""
GENESIS — One-shot launcher.

Run *every* feature of the project in the correct sequence from a single
file. This is the only entry point you need to demo, develop, or smoke-test
the full stack.

Usage (PowerShell / bash, from repo root):

    python run.py                    # interactive menu (recommended)
    python run.py --mode full        # backend + frontend + demo rollout
    python run.py --mode stack       # backend + frontend only (long-running)
    python run.py --mode backend     # MCP / FastAPI server only
    python run.py --mode frontend    # Next.js UI only (assumes backend is up)
    python run.py --mode demo        # backend + scripted demo rollout, then exit
    python run.py --mode smoke       # quick training smoke test
    python run.py --mode plots       # regenerate reward curves & summary
    python run.py --mode doctor      # check environment / dependencies only

Flags:
    --skip-install         Don't auto-install Python or npm dependencies.
    --no-frontend          Disable the frontend (when the chosen mode would start it).
    --backend-port 7860    Override the backend port.
    --frontend-port 3000   Override the frontend dev port.
    --episodes 1           Number of demo rollout episodes.
    --difficulty 2         Demo rollout difficulty (1=Tutorial .. 5=Nightmare).
    --episode-days 30      Days simulated per demo episode.
    --model-id demo-model  Model id used for the demo rollout / Founder Genome.

Lifecycle:
    Phase 0  Doctor         — verify python, node, pip, npm.
    Phase 1  Dependencies   — install Python (editable) + frontend npm deps.
    Phase 2  Backend        — start uvicorn server (server.app:app) and wait
                              for /health to return 200.
    Phase 3  Frontend       — start `npm run dev` (Next.js).
    Phase 4  Demo / Smoke   — drive a scripted rollout, generate the Founder
                              Genome card, print a Resurrection-Engine
                              scenario list, and surface artifact paths.
    Phase 5  Idle / Exit    — for long-running modes, block until Ctrl+C and
                              tear down all child processes cleanly.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"
EXPORTS_DIR = ROOT / "exports" / "founder_genomes"
OUTPUTS_DIR = ROOT / "outputs" / "evals"

IS_WINDOWS = os.name == "nt"

# Force UTF-8 on Windows consoles so we can print box-drawing / arrows safely.
if IS_WINDOWS:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

_UNICODE_OK = True
try:
    "═▶✓✗•→".encode(sys.stdout.encoding or "utf-8")
except Exception:
    _UNICODE_OK = False

# ── pretty printing ─────────────────────────────────────────────────────────

class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"

def _supports_color() -> bool:
    if IS_WINDOWS and not os.environ.get("WT_SESSION") and not os.environ.get("TERM"):
        return False
    return sys.stdout.isatty()

if not _supports_color():
    for name in dir(C):
        if not name.startswith("_") and name.isupper():
            setattr(C, name, "")

_HR = "═" if _UNICODE_OK else "="
_ARROW = "▶" if _UNICODE_OK else ">"
_OK = "✓" if _UNICODE_OK else "+"
_BAD = "✗" if _UNICODE_OK else "x"

def banner(text: str) -> None:
    line = _HR * max(len(text) + 4, 60)
    print(f"\n{C.CYAN}{line}\n  {C.BOLD}{text}{C.RESET}{C.CYAN}\n{line}{C.RESET}")

def step(text: str) -> None:
    print(f"{C.CYAN}{_ARROW} {C.BOLD}{text}{C.RESET}")
    time.sleep(0.8)

def ok(text: str) -> None:
    print(f"  {C.GREEN}{_OK}{C.RESET} {text}")
    time.sleep(0.5)

def warn(text: str) -> None:
    print(f"  {C.YELLOW}!{C.RESET} {text}")

def err(text: str) -> None:
    print(f"  {C.RED}{_BAD}{C.RESET} {text}")

def info(text: str) -> None:
    print(f"  {C.DIM}{text}{C.RESET}")


# ── demo event pushing ──────────────────────────────────────────────────────

_DEMO_BACKEND_PORT = 7860

def _push_demo_event(phase: int, phase_title: str, step: str, detail: str = "", status: str = "info", data: dict = None):
    """Push a structured event to the backend's /demo/log endpoint."""
    url = f"http://127.0.0.1:{_DEMO_BACKEND_PORT}/demo/log"
    payload = {
        "phase": phase,
        "phase_title": phase_title,
        "step": step,
        "detail": detail,
        "status": status,
        "data": data or {}
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=1) as resp:
            pass
    except Exception:
        # Fire and forget: don't let log failures break the demo
        pass


# ── child-process registry ──────────────────────────────────────────────────

_CHILDREN: List[subprocess.Popen] = []

def _spawn(cmd: List[str], *, cwd: Optional[Path] = None, env: Optional[dict] = None,
           label: str = "process") -> subprocess.Popen:
    """Spawn a child process attached to this script's lifetime."""
    info(f"spawn[{label}]: {' '.join(cmd)} (cwd={cwd or ROOT})")
    creationflags = 0
    preexec_fn = None
    if IS_WINDOWS:
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    else:
        preexec_fn = os.setsid  # type: ignore[assignment]
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=None,
        stderr=None,
        creationflags=creationflags,
        preexec_fn=preexec_fn,
    )
    _CHILDREN.append(proc)
    return proc

def _terminate_all() -> None:
    if not _CHILDREN:
        return
    print()
    step("Shutting down child processes")
    for proc in _CHILDREN:
        if proc.poll() is not None:
            continue
        try:
            if IS_WINDOWS:
                proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass
    deadline = time.time() + 6
    for proc in _CHILDREN:
        remaining = max(0.1, deadline - time.time())
        try:
            proc.wait(timeout=remaining)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    ok("All child processes stopped.")


# ── phase 0: doctor ─────────────────────────────────────────────────────────

def doctor() -> bool:
    banner("Phase 0 — Environment doctor")
    healthy = True

    step("Python")
    info(f"executable: {sys.executable}")
    info(f"version:    {sys.version.split()[0]}")
    if sys.version_info < (3, 10):
        err("Python 3.10+ required."); healthy = False
    else:
        ok("Python version is OK.")

    step("pip")
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True,
                       stdout=subprocess.PIPE)
        ok("pip available.")
    except Exception as e:
        err(f"pip not available: {e}"); healthy = False

    step("Node.js + npm (for the frontend)")
    node = shutil.which("node")
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if node:
        ok(f"node: {node}")
    else:
        warn("node not found — frontend will be unavailable.")
    if npm:
        ok(f"npm:  {npm}")
    else:
        warn("npm not found — frontend will be unavailable.")

    step("Repo layout")
    for required in ("server/app.py", "client.py", "openenv.yaml", "frontend/package.json"):
        if (ROOT / required).exists():
            ok(required)
        else:
            err(f"missing: {required}"); healthy = False

    step("Optional artifact directories")
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    ok(f"exports → {EXPORTS_DIR}")
    ok(f"outputs → {OUTPUTS_DIR}")

    return healthy


# ── phase 1: dependencies ───────────────────────────────────────────────────

def install_python_deps() -> None:
    step("Installing Python package (editable)")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", "."],
            cwd=str(ROOT), check=True,
        )
        ok("Python deps installed.")
    except subprocess.CalledProcessError as e:
        err(f"pip install failed (exit {e.returncode}). Continuing — server may still start "
            "if deps are already present.")

def install_frontend_deps() -> bool:
    if not (FRONTEND_DIR / "package.json").exists():
        warn("frontend/package.json missing; skipping npm install.")
        return False
    if (FRONTEND_DIR / "node_modules").exists():
        ok("frontend node_modules already present.")
        return True
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        warn("npm not available; skipping frontend install.")
        return False
    step("Installing frontend dependencies (npm install)")
    try:
        subprocess.run([npm, "install"], cwd=str(FRONTEND_DIR), check=True)
        ok("Frontend deps installed.")
        return True
    except subprocess.CalledProcessError as e:
        err(f"npm install failed: {e}")
        return False


# ── phase 2: backend ────────────────────────────────────────────────────────

def _port_is_free(host: str, port: int) -> bool:
    """Best-effort check if we can bind to (host, port)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
        except OSError:
            return False
    return True

def _pick_free_port(start_port: int, *, host: str = "127.0.0.1", max_tries: int = 40) -> int:
    """Choose a free port, scanning upward from start_port."""
    for p in range(start_port, start_port + max_tries):
        if _port_is_free(host, p):
            return p
    raise RuntimeError(f"No free ports found in range [{start_port}, {start_port + max_tries - 1}] on {host}")

def _wait_for_health(url: str, timeout_s: float = 60.0, *, proc: Optional[subprocess.Popen] = None) -> bool:
    start = time.time()
    last_err: Optional[str] = None
    while time.time() - start < timeout_s:
        if proc is not None and proc.poll() is not None:
            err(f"Backend process exited early (pid={proc.pid}, code={proc.returncode}).")
            return False
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            last_err = str(e)
        time.sleep(0.7)
    err(f"Backend did not become healthy within {timeout_s:.0f}s ({last_err}).")
    return False

def start_backend(requested_port: int) -> tuple[subprocess.Popen, int]:
    banner("Phase 2 — Backend (FastMCP / FastAPI)")
    port = requested_port
    if not _port_is_free("127.0.0.1", port):
        new_port = _pick_free_port(port + 1)
        warn(f"Port {port} is already in use. Switching backend to port {new_port}.")
        port = new_port
    step(f"Launching uvicorn on http://127.0.0.1:{port}")
    env = os.environ.copy()
    # Force matplotlib's non-interactive backend so genome/comparison chart
    # generation never tries to spin up Tk on a server thread.
    env["MPLBACKEND"] = "Agg"
    proc = _spawn(
        [sys.executable, "-m", "uvicorn", "server.app:app",
         "--host", "0.0.0.0", "--port", str(port)],
        cwd=ROOT, env=env, label="backend",
    )
    ok("uvicorn process started; waiting for /health …")
    if _wait_for_health(f"http://127.0.0.1:{port}/health", timeout_s=60, proc=proc):
        ok("Backend is healthy.")
    else:
        err("Backend health check failed. Check the uvicorn logs above.")
    return proc, port


# ── phase 3: frontend ───────────────────────────────────────────────────────

def start_frontend(port: int, backend_port: int) -> Optional[subprocess.Popen]:
    banner("Phase 3 — Frontend (Next.js)")
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        warn("npm not available — skipping frontend.")
        return None
    if not (FRONTEND_DIR / "node_modules").exists():
        warn("frontend/node_modules missing — run with --skip-install=false or `npm install` first.")
        return None
    env = os.environ.copy()
    env["NEXT_PUBLIC_GENESIS_URL"] = f"http://localhost:{backend_port}"
    env["PORT"] = str(port)
    step(f"Launching Next.js dev server on http://localhost:{port}")
    info(f"NEXT_PUBLIC_GENESIS_URL={env['NEXT_PUBLIC_GENESIS_URL']}")
    proc = _spawn([npm, "run", "dev", "--", "-p", str(port)],
                  cwd=FRONTEND_DIR, env=env, label="frontend")
    ok("Frontend dev server launching (first compile takes ~10–30s).")
    return proc


# ── phase 4: demo rollout ───────────────────────────────────────────────────

def _call_tool(env, _tool_name: str, _args: Optional[dict] = None, **kwargs):
    """Call an MCP tool, supporting tool arguments that collide with the
    'name' keyword (e.g. build_feature(name=...)). Pass colliding args via
    the optional ``_args`` dict.
    """
    args = dict(kwargs)
    if _args:
        args.update(_args)
    # Bypass GenesisEnv.call_tool's positional 'name' parameter by calling
    # the lower-level stateful MCP request directly (the sync wrapper exposes
    # it via __getattr__).
    data = env._stateful_mcp_request(
        "tools/call", {"name": _tool_name, "arguments": args}
    )
    if "error" in data:
        raise RuntimeError(data["error"].get("message", "unknown error"))
    result = data.get("result", {})
    if isinstance(result, dict):
        if result.get("isError"):
            raise RuntimeError(f"Tool '{_tool_name}' returned an error response")
        if "structuredContent" in result:
            return result["structuredContent"]
        content = result.get("content")
        if isinstance(content, list) and content:
            text = content[0].get("text") if isinstance(content[0], dict) else None
            if isinstance(text, str):
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return text
        if "data" in result:
            return result["data"]
    return result


def _safe_call(env, _tool_name, _args: Optional[dict] = None, **kwargs):
    """Call an MCP tool and return None on failure (logging the error)."""
    try:
        return _call_tool(env, _tool_name, _args=_args, **kwargs)
    except Exception as e:
        err(f"{_tool_name} failed: {e}")
        return None

def _short(value, limit: int = 220) -> str:
    text = json.dumps(value, default=str) if not isinstance(value, str) else value
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 3] + "..."

def _unwrap(view: dict, outer: str, inner: Optional[str] = None) -> list:
    """Pull a list out of role-filtered views, where the top-level 'outer'
    key holds a sub-dict whose 'inner' field contains the list.
    Falls back to returning the raw value if it's already a list."""
    raw = (view or {}).get(outer) if isinstance(view, dict) else None
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return raw.get(inner or outer) or []
    return []


def _first_entity(collection, id_key: str = "id"):
    """Return (entity_id, entity_dict, name) from a list-of-dicts/objects or
    a dict keyed by id. Returns (None, None, None) when empty."""
    if not collection:
        return None, None, None
    if isinstance(collection, dict):
        for k, v in collection.items():
            ent_id = (v.get(id_key) if isinstance(v, dict) else getattr(v, id_key, None)) or k
            name = (v.get("name") if isinstance(v, dict) else getattr(v, "name", None)) or str(ent_id)
            return ent_id, v, name
        return None, None, None
    first = next(iter(collection), None)
    if first is None:
        return None, None, None
    ent_id = first.get(id_key) if isinstance(first, dict) else getattr(first, id_key, None)
    name = first.get("name") if isinstance(first, dict) else getattr(first, "name", None) or str(ent_id)
    return ent_id, first, name

def _scene(title: str) -> None:
    bar = "─" if _UNICODE_OK else "-"
    print(f"\n{C.MAGENTA}{bar * 4} {C.BOLD}{title}{C.RESET}{C.MAGENTA} {bar * (max(0, 70 - len(title)))}{C.RESET}")
    time.sleep(1.5)


def _load_ml_model(adapter: str, base_model: str):
    """
    Try to load the fine-tuned LoRA adapter for use in the demo.
    Returns (model, tokenizer) on success, or (None, None) on failure
    (e.g. missing deps or adapter path).  Never raises.
    """
    try:
        from ml_inference import load_model_and_tokenizer
        model, tokenizer = load_model_and_tokenizer(base_model, adapter)
        return model, tokenizer
    except FileNotFoundError as e:
        warn(f"ML adapter not found — demo will use fallback decisions. ({e})")
    except ImportError as e:
        warn(f"ML deps not installed (transformers/peft) — using fallback. ({e})")
    except Exception as e:
        warn(f"ML model failed to load — using fallback. ({e})")
    return None, None


def _ml_decide(
    ml_model, ml_tokenizer, role: str, briefing: dict, *, max_new_tokens: int = 200
) -> tuple[str, str]:
    """
    Ask the ML model for a decision given a role + briefing dict.
    Returns (decision_text, reasoning_text).
    Falls back gracefully if inference fails.
    """
    if ml_model is None or ml_tokenizer is None:
        return (
            f"{role.upper()}: maintain plan; address top inbox items.",
            "Fallback — ML model not loaded.",
        )
    try:
        from ml_inference import build_prompt, generate_tool_call
        prompt = build_prompt(role, briefing, ml_tokenizer)
        completion, tool_call = generate_tool_call(
            ml_model, ml_tokenizer, prompt, max_new_tokens=max_new_tokens
        )
        tool = tool_call.get("tool", "make_decision")
        args = tool_call.get("args") or {}
        decision = args.get("decision") or f"[{tool}] {json.dumps(args, default=str)[:200]}"
        reasoning = args.get("reasoning") or completion[:300]
        return str(decision)[:800], str(reasoning)[:1200]
    except Exception as e:
        return (
            f"{role.upper()}: maintain plan (ML error: {e}).",
            "Fallback due to inference error.",
        )


def run_demo(backend_port: int, *, episodes: int, difficulty: int,
             episode_days: int, model_id: str,
             use_ml: bool = True,
             ml_adapter: str = None,
             ml_base_model: str = "Qwen/Qwen2.5-3B-Instruct") -> None:
    """
    Comprehensive Phase-4 demo.

    Walks every major capability of the GENESIS environment in a logical order
    so a watcher can see the *whole* system in one run:
      1. Session setup       (reset, list_tools, role-filtered observation)
      2. Product engineering (CTO tools)
      3. Sales & market      (Sales / CEO tools)
      4. Finance             (CFO tools)
      5. People & culture    (Head of People tools)
      6. Memory & messaging  (CompanyBrain + cross-role messaging)
      7. Crisis handling     (personal crises)
      8. Strategy & pivots   (pivot ballot, voting, override)
      9. Time advancement    (ML model drives every day-tick)
     10. USP-1 Resurrection  (ML model responds to historical fork crises)
     11. USP-2 Ghost Founder (human takeover / release)
     12. USP-3 Founder Genome (export + compare across models)
     13. Blockchain proofs   (Merkle status + dry-run on-chain commit)
     14. Final reward        (composite breakdown)
    """
    global _DEMO_BACKEND_PORT
    _DEMO_BACKEND_PORT = backend_port

    # ── ML model bootstrap ────────────────────────────────────────────────────
    if ml_adapter is None:
        ml_adapter = str(ROOT / "models" / "genesis_final")

    ml_model, ml_tokenizer = None, None
    if use_ml:
        step("Loading ML model (genesis_final LoRA adapter) ...")
        ml_model, ml_tokenizer = _load_ml_model(ml_adapter, ml_base_model)
        if ml_model is not None:
            ok("ML model loaded — demo decisions will be driven by the fine-tuned model.")
        else:
            warn("ML model unavailable — demo will continue with fallback static decisions.")

    banner("Phase 4 — Full feature demo")
    _push_demo_event(4, "Full Feature Demo", "demo_start", "Starting scripted rollout tour", "info")
    base_url = f"http://127.0.0.1:{backend_port}"

    try:
        from client import GenesisEnv  # type: ignore
    except Exception as e:
        err(f"Could not import GenesisEnv from client.py: {e}")
        return

    env = GenesisEnv(base_url=base_url).sync()
    try:
        env.async_client.use_production_mode = True
    except Exception:
        pass
    try:
        env._ensure_stateful_session()
    except Exception as e:
        warn(f"Could not initialize MCP session up-front: {e}")

    primary_id = f"demo-{model_id}-{uuid.uuid4().hex[:8]}"
    secondary_model = f"{model_id}-rival"
    secondary_id = f"demo-{secondary_model}-{uuid.uuid4().hex[:8]}"
    roles = ["ceo", "cto", "sales", "people", "cfo"]

    try:
        # ── 1. Session setup ────────────────────────────────────────────────
        _scene("1/14  Session setup")
        _push_demo_event(4, "Session Setup", "1/14 Session setup", "Initializing MCP session", "info")
        step(f"reset(episode={primary_id}, difficulty={difficulty}, model={model_id})")
        reset_resp = _safe_call(
            env, "reset",
            episode_id=primary_id, difficulty=difficulty, seed=42,
            model_id=model_id, model_provider="demo", model_version="run.py",
        )
        if reset_resp:
            info(_short(reset_resp))
            ok(f"Day {reset_resp.get('day')}, cash={reset_resp.get('cash')}, "
               f"max_days={reset_resp.get('max_days')}, mode={reset_resp.get('difficulty')}")
            _push_demo_event(4, "Session Setup", "reset", f"Day {reset_resp.get('day')}, cash=${reset_resp.get('cash')}", "ok", reset_resp)

        step("list_tools — full MCP tool surface")
        _push_demo_event(4, "Session Setup", "list_tools", "Discovering available MCP tools", "info")
        try:
            tools = env.list_tools()
            ok(f"{len(tools)} tools registered.")
            preview = ", ".join(t.name for t in tools[:8])
            info(f"first 8: {preview} ...")
            _push_demo_event(4, "Session Setup", "list_tools", f"{len(tools)} tools registered", "ok")
        except Exception as e:
            warn(f"list_tools failed: {e}")
            _push_demo_event(4, "Session Setup", "list_tools", str(e), "warn")

        step("get_company_state — role-filtered observation per role")
        _push_demo_event(4, "Session Setup", "get_company_state", "Verifying role-filtered views", "info")
        for r in roles:
            snap = _safe_call(env, "get_company_state", episode_id=primary_id, agent_role=r)
            if isinstance(snap, dict):
                keys = sorted(snap.keys())
                ok(f"{r.upper():<6} → {len(keys)} keys: {', '.join(keys[:6])}{'...' if len(keys) > 6 else ''}")
                _push_demo_event(4, "Session Setup", f"get_company_state ({r})", f"{len(keys)} keys visible", "ok")

        # ── 2. Product engineering (CTO) ────────────────────────────────────
        _scene("2/14  Product engineering (CTO tools)")
        _push_demo_event(4, "Product Engineering", "2/14 Product Engineering", "CTO domain tools", "info")
        for feat_name, complexity, engineers in [
            ("core-api-v2",    "medium", 2),
            ("billing-portal", "low",    1),
            ("ml-recommender", "high",   3),
        ]:
            step(f"build_feature {feat_name} ({complexity})")
            _push_demo_event(4, "Product Engineering", "build_feature", f"{feat_name} ({complexity})", "info")
            res = _safe_call(
                env, "build_feature",
                _args={"name": feat_name},
                episode_id=primary_id, agent_role="cto",
                complexity=complexity, engineers=engineers,
            )
            if res: 
                info(_short(res))
                _push_demo_event(4, "Product Engineering", "build_feature", f"ETA: {res.get('eta_days')} days", "ok", res)

        step("run_load_test — peak-hour simulation")
        res = _safe_call(env, "run_load_test", episode_id=primary_id, agent_role="cto",
                         scenario="Black-Friday traffic burst — 8x normal RPS")
        if res: 
            info(_short(res))
            _push_demo_event(4, "Product Engineering", "run_load_test", f"Max RPS: {res.get('max_rps')}", "ok", res)

        step("review_codebase_health")
        res = _safe_call(env, "review_codebase_health", episode_id=primary_id, agent_role="cto")
        if res: 
            info(_short(res))
            _push_demo_event(4, "Product Engineering", "review_codebase_health", f"Tech Debt: {res.get('tech_debt_score')}", "ok", res)

        step("deploy_to_production v0.9.0")
        res = _safe_call(env, "deploy_to_production", episode_id=primary_id, agent_role="cto", version="0.9.0")
        if res: 
            info(_short(res))
            _push_demo_event(4, "Product Engineering", "deploy_to_production", f"Success: {res.get('success')}", "ok" if res.get('success') else "warn", res)

        # ── 3. Sales & market ───────────────────────────────────────────────
        _scene("3/14  Sales & market intelligence")
        _push_demo_event(4, "Sales & Market", "3/14 Sales & Market", "CEO/Sales domain tools", "info")
        step("analyze_market(segment=mid-market SaaS)")
        market = _safe_call(env, "analyze_market", episode_id=primary_id,
                            agent_role="ceo", segment="mid-market-saas")
        if isinstance(market, dict):
            info(f"TAM={market.get('tam')}, growth={market.get('market_growth')}, "
                 f"competitors={len(market.get('competitors', []))}")
            _push_demo_event(4, "Sales & Market", "analyze_market", f"TAM: ${market.get('tam'):,}", "ok", market)

        comp_name = None
        if isinstance(market, dict):
            _cid, _c, comp_name = _first_entity(market.get("competitors"), id_key="name")
        if not comp_name:
            ceo_view = _safe_call(env, "get_company_state", episode_id=primary_id, agent_role="ceo") or {}
            _cid, _c, comp_name = _first_entity(_unwrap(ceo_view, "competitors"), id_key="name")
        if comp_name:
            step(f"run_competitive_analysis({comp_name})")
            res = _safe_call(env, "run_competitive_analysis", episode_id=primary_id,
                             agent_role="ceo", competitor_name=comp_name)
            if res: 
                info(_short(res))
                _push_demo_event(4, "Sales & Market", "run_competitive_analysis", f"Target: {comp_name}", "ok", res)

        sales_view = _safe_call(env, "get_company_state", episode_id=primary_id, agent_role="sales") or {}
        cust_id, _cust, cust_name = _first_entity(_unwrap(sales_view, "customers"))
        if cust_id:
            if True:
                step(f"send_customer_email → {cust_name}")
                res = _safe_call(env, "send_customer_email", episode_id=primary_id,
                                 agent_role="sales", customer_id=cust_id,
                                 subject="Quarterly check-in & roadmap preview",
                                 content=("Hi team — wanted to share what we shipped this quarter, "
                                          "and preview the analytics dashboard you asked for. "
                                          "Happy to jump on a call if useful."))
                if res: 
                    info(_short(res))
                    _push_demo_event(4, "Sales & Market", "send_customer_email", f"Sent to {cust_name}", "ok", res)
                step(f"update_crm({cust_name}, status=expanding)")
                res = _safe_call(env, "update_crm", episode_id=primary_id, agent_role="sales",
                                 customer_id=cust_id, status="expanding",
                                 notes="Strong signal on multi-seat upgrade after roadmap call.")
                if res: 
                    info(_short(res))
                    _push_demo_event(4, "Sales & Market", "update_crm", f"Status: expanding", "ok", res)
        else:
            warn("No customers visible — skipping customer-facing tools.")

        # ── 4. Finance (CFO) ────────────────────────────────────────────────
        _scene("4/14  Finance & fundraising (CFO tools)")
        _push_demo_event(4, "Finance & Fundraising", "4/14 Finance & Fundraising", "CFO domain tools", "info")
        step("check_bank_balance")
        bank = _safe_call(env, "check_bank_balance", episode_id=primary_id, agent_role="cfo")
        if bank: 
            info(_short(bank))
            _push_demo_event(4, "Finance & Fundraising", "check_bank_balance", f"Cash: ${bank.get('cash'):,}", "ok", bank)

        step("create_financial_model(growth=15%/mo, 12mo)")
        res = _safe_call(env, "create_financial_model", episode_id=primary_id,
                         agent_role="cfo", monthly_growth=0.15, months_ahead=12)
        if isinstance(res, dict):
            info(f"breakeven_month={res.get('breakeven_month')}, "
                 f"runway={res.get('runway_at_current_burn')}d, "
                 f"projection_points={len(res.get('projections', []))}")
            _push_demo_event(4, "Finance & Fundraising", "create_financial_model", f"Runway: {res.get('runway_at_current_burn')} days", "ok", res)

        cfo_view = _safe_call(env, "get_company_state", episode_id=primary_id, agent_role="ceo") or {}
        inv_id, _inv, inv_name = _first_entity(_unwrap(cfo_view, "investors"))
        if inv_id:
            if True:
                step(f"send_investor_update → {inv_name}")
                res = _safe_call(env, "send_investor_update", episode_id=primary_id,
                                 agent_role="ceo", investor_id=inv_id,
                                 content=("Q-end update: ARR up 22% MoM, NRR holding above 1.10, "
                                          "shipped 3 features incl. ML recommender. Cash position healthy. "
                                          "Asks: warm intros to mid-market sales advisors."))
                if res: 
                    info(_short(res))
                    _push_demo_event(4, "Finance & Fundraising", "send_investor_update", f"Sent to {inv_name}", "ok", res)

                step(f"negotiate_with_investor({inv_name}, $30M @ 15% equity)")
                res = _safe_call(env, "negotiate_with_investor", episode_id=primary_id,
                                 agent_role="ceo", investor_id=inv_id,
                                 valuation=30_000_000, equity=0.15)
                if res: 
                    info(_short(res))
                    _push_demo_event(4, "Finance & Fundraising", "negotiate_with_investor", f"Offer: $30M @ 15%", "ok", res)
        else:
            warn("No investors visible — skipping investor tools.")

        # ── 5. People & culture ─────────────────────────────────────────────
        _scene("5/14  People & culture (Head of People tools)")
        _push_demo_event(4, "People & Culture", "5/14 People & Culture", "Head of People domain tools", "info")
        step("post_job_listing(Senior Backend Engineer)")
        res = _safe_call(env, "post_job_listing", episode_id=primary_id, agent_role="people",
                         role="Senior Backend Engineer",
                         requirements="5+ yrs Python, distributed systems, on-call willing.",
                         salary_min=140_000, salary_max=190_000)
        if res: 
            info(_short(res))
            _push_demo_event(4, "People & Culture", "post_job_listing", f"Posted: Senior Backend Engineer", "ok", res)

        people_view = _safe_call(env, "get_company_state", episode_id=primary_id, agent_role="people") or {}
        cand_id, _cand, cand_name = _first_entity(_unwrap(people_view, "team", "candidate_pool"))
        if cand_id:
            if True:
                step(f"conduct_interview → {cand_name}")
                res = _safe_call(env, "conduct_interview", episode_id=primary_id, agent_role="people",
                                 candidate_id=cand_id,
                                 questions="System design + leadership + values fit.")
                if res: 
                    info(_short(res))
                    _push_demo_event(4, "People & Culture", "conduct_interview", f"Interviewed {cand_name}", "ok", res)

                step(f"hire_candidate({cand_name})")
                res = _safe_call(env, "hire_candidate", episode_id=primary_id, agent_role="people",
                                 candidate_id=cand_id, role="Senior Backend Engineer", salary=160_000)
                if res: 
                    info(_short(res))
                    _push_demo_event(4, "People & Culture", "hire_candidate", f"Hired {cand_name}", "ok", res)

        emp_id, _emp, emp_name = _first_entity(_unwrap(people_view, "team", "employees"))
        if emp_id:
            if True:
                step(f"hold_one_on_one → {emp_name}")
                res = _safe_call(env, "hold_one_on_one", episode_id=primary_id, agent_role="people",
                                 employee_id=emp_id,
                                 talking_points=("Career growth, current workload, blockers, "
                                                 "how the recent deploy stress affected you, "
                                                 "what you want to learn next quarter."))
                if res: 
                    info(_short(res))
                    _push_demo_event(4, "People & Culture", "hold_one_on_one", f"Meeting with {emp_name}", "ok", res)

        step("check_team_morale")
        res = _safe_call(env, "check_team_morale", episode_id=primary_id, agent_role="people")
        if res: 
            info(_short(res))
            _push_demo_event(4, "People & Culture", "check_team_morale", f"Avg Morale: {res.get('team_avg_morale')}", "ok", res)

        # ── 6. Memory & messaging ───────────────────────────────────────────
        _scene("6/14  Memory & messaging")
        _push_demo_event(4, "Memory & Messaging", "6/14 Memory & Messaging", "CompanyBrain & cross-role comms", "info")
        step("write_company_brain(weekly_state_of_company)")
        res = _safe_call(env, "write_company_brain", episode_id=primary_id, agent_role="ceo",
                         key="weekly_state_of_company",
                         value=("Theme: convert mid-market pilots to multi-seat. "
                                "Product: ML recommender in beta. Finance: 14mo runway. "
                                "Risk: deploy stability after v0.9.0; CTO owns mitigation."))
        if res: 
            info(_short(res))
            _push_demo_event(4, "Memory & Messaging", "write_company_brain", "Stored weekly state", "ok", res)

        step("read_company_brain(weekly_state_of_company)")
        res = _safe_call(env, "read_company_brain", episode_id=primary_id, agent_role="cfo",
                         key="weekly_state_of_company")
        if res: 
            info(_short(res))
            _push_demo_event(4, "Memory & Messaging", "read_company_brain", "CFO retrieved state", "ok", res)

        step("send_message ceo → cto")
        res = _safe_call(env, "send_message", episode_id=primary_id,
                         from_role="ceo", to_role="cto",
                         subject="Deploy stability target",
                         content="Let's hold v1.0 until uptime ≥ 99.5% over 7 days. Risk-adjusted launch.")
        if res: 
            info(_short(res))
            _push_demo_event(4, "Memory & Messaging", "send_message", "CEO -> CTO: Deploy stability", "ok", res)

        # ── 7. Personal crises ──────────────────────────────────────────────
        _scene("7/14  Personal crisis handling")
        _push_demo_event(4, "Personal Crises", "7/14 Personal Crises", "Handling co-founder burnout", "info")
        crisis_resolved = False
        for r in roles:
            briefing = _safe_call(env, "get_daily_briefing", episode_id=primary_id, agent_role=r)
            if not isinstance(briefing, dict):
                continue
            for crisis in briefing.get("active_crises", []):
                if crisis.get("target_role") and crisis["target_role"] != r:
                    continue
                step(f"handle_personal_crisis [{r}] {crisis.get('description', '')[:80]}")
                _push_demo_event(4, "Personal Crises", "handle_personal_crisis", f"Role: {r}", "info", crisis)
                res = _safe_call(env, "handle_personal_crisis", episode_id=primary_id,
                                 agent_role=r, crisis_id=crisis["id"],
                                 response=("I understand this matters and want to act in good faith. "
                                           "Plan: 1) acknowledge openly, 2) propose equity refresh + 2-week vacation, "
                                           "3) schedule talk with team to clarify next steps. "
                                           "I'll personally own follow-through and report back in 7 days."))
                if res: 
                    info(_short(res))
                    _push_demo_event(4, "Personal Crises", "handle_personal_crisis", "Crisis resolved", "ok", res)
                crisis_resolved = True
                break
            if crisis_resolved:
                break
        if not crisis_resolved:
            info("No active crisis surfaced this tick — that's normal early in an episode.")
            _push_demo_event(4, "Personal Crises", "handle_personal_crisis", "No active crisis", "info")

        # ── 8. Strategy & pivots ────────────────────────────────────────────
        _scene("8/14  Strategy & pivots")
        _push_demo_event(4, "Strategy & Pivots", "8/14 Strategy & Pivots", "Strategic direction shift", "info")
        new_direction = "vertical-saas-for-fintech"
        rationale = "Mid-market signal is strongest in fintech ops; refocus to win that wedge."
        step(f"pivot_company propose [ceo] → {new_direction}")
        _push_demo_event(4, "Strategy & Pivots", "pivot_company (propose)", f"New dir: {new_direction}", "info")
        res = _safe_call(env, "pivot_company", episode_id=primary_id, agent_role="ceo",
                         new_direction=new_direction, rationale=rationale, vote="approve")
        if res: 
            info(_short(res))
            _push_demo_event(4, "Strategy & Pivots", "pivot_company (propose)", "Proposed by CEO", "ok", res)
        for voter in ("cto", "cfo"):
            step(f"pivot_company vote [{voter}] approve")
            res = _safe_call(env, "pivot_company", episode_id=primary_id, agent_role=voter,
                             new_direction=new_direction, rationale=rationale, vote="approve")
            if res: 
                info(_short(res))
                _push_demo_event(4, "Strategy & Pivots", f"pivot_company (vote {voter})", "Vote recorded", "ok", res)

        # ── 9. Time advancement (ML-driven) ─────────────────────────────────
        _scene(f"9/14  Time advancement — {episode_days} day(s) [{('ML model' if ml_model else 'fallback')}]")
        _push_demo_event(4, "Time Advancement", "9/14 Time Advancement",
                         f"Advancing {episode_days} days — driven by {'ML model' if ml_model else 'fallback'}",
                         "info")
        for day in range(1, episode_days + 1):
            role = roles[day % len(roles)]
            briefing = _safe_call(env, "get_daily_briefing", episode_id=primary_id, agent_role=role)
            if not isinstance(briefing, dict):
                continue

            # Ask the ML model what to do, then post it as a make_decision call
            decision, reasoning = _ml_decide(
                ml_model, ml_tokenizer, role, briefing
            )
            decision_type = "strategic" if day % 5 == 0 else "tactical"
            _safe_call(env, "make_decision", episode_id=primary_id, agent_role=role,
                       decision_type=decision_type,
                       decision=decision,
                       reasoning=reasoning)

            src = "ML" if ml_model else "fallback"
            info(f"  day {briefing.get('day', day):>3} [{role}] [{src}] {decision[:80]}")
            _push_demo_event(4, "Time Advancement", f"day_{day}",
                             f"[{role}] {decision[:100]}", "ok",
                             {"role": role, "decision": decision, "source": src})

            if briefing.get("is_done"):
                info(f"episode finished early on day {day}")
                _push_demo_event(4, "Time Advancement", "get_daily_briefing",
                                 f"Finished early on day {day}", "ok", briefing)
                break
            if day == episode_days:
                ok(f"Advanced through {episode_days} day-ticks.")
                _push_demo_event(4, "Time Advancement", "get_daily_briefing",
                                 f"Advanced {episode_days} days", "ok", briefing)

        # ── 10. USP-1 Resurrection Engine ──────────────────────────────────
        _scene("10/14  USP-1 Dead Startup Resurrection Engine")
        _push_demo_event(4, "Resurrection Engine", "10/14 Resurrection Engine", "Replaying historical failures", "info")
        step("list_postmortem_scenarios")
        scenarios = _safe_call(env, "list_postmortem_scenarios")
        scenario_id = None
        if isinstance(scenarios, dict):
            for s in scenarios.get("scenarios", [])[:5]:
                info(f"• {s.get('id', ''):<10} {s.get('company_name', '')} "
                     f"({s.get('year_founded', '?')}–{s.get('year_failed', '?')})")
            if scenarios.get("scenarios"):
                scenario_id = scenarios["scenarios"][0].get("id")
            _push_demo_event(4, "Resurrection Engine", "list_postmortem_scenarios", f"Found {len(scenarios.get('scenarios', []))} scenarios", "ok", scenarios)

        if scenario_id:
            res_id = f"resurrect-{scenario_id}-{uuid.uuid4().hex[:6]}"
            step(f"reset new episode for resurrection: {res_id}")
            _safe_call(env, "reset", episode_id=res_id, difficulty=difficulty, seed=99,
                       model_id=model_id, model_provider="demo", model_version="run.py")
            step(f"load_postmortem_scenario({scenario_id})")
            loaded = _safe_call(env, "load_postmortem_scenario", episode_id=res_id, scenario_id=scenario_id)
            if isinstance(loaded, dict):
                ok(f"Loaded {loaded.get('company')} — {loaded.get('fork_points_loaded')} fork points.")
                _push_demo_event(4, "Resurrection Engine", "load_postmortem_scenario", f"Loaded {loaded.get('company')}", "ok", loaded)

            step("Advancing 25 days to trigger fork-point crises")
            _push_demo_event(4, "Resurrection Engine", "advance", "Triggering historical fork points", "info")
            for day in range(1, 26):
                role = roles[day % len(roles)]
                b = _safe_call(env, "get_daily_briefing", episode_id=res_id, agent_role=role)
                if not isinstance(b, dict):
                    continue
                for c in b.get("active_crises", []):
                    if "[HISTORICAL FORK]" in c.get("description", ""):
                        target = c.get("target_role") or role
                        step(f"day {day} fork triggered → {target}")
                        _push_demo_event(4, "Resurrection Engine", "fork_triggered",
                                         f"Day {day}: {c.get('description')[:50]}", "warn", c)

                        # Ask the ML model how it would respond to this historical fork
                        fork_briefing = dict(b)
                        fork_briefing["active_crises"] = [c]
                        ml_response, ml_reasoning = _ml_decide(
                            ml_model, ml_tokenizer, target, fork_briefing, max_new_tokens=300
                        )
                        src = "ML" if ml_model else "fallback"
                        info(f"  [{src}] fork response: {ml_response[:120]}")

                        _safe_call(env, "handle_personal_crisis", episode_id=res_id,
                                   agent_role=target, crisis_id=c["id"],
                                   response=ml_response)
                        _safe_call(env, "record_fork_decision", episode_id=res_id,
                                   agent_role=target, crisis_id=c["id"],
                                   decision_summary=ml_response[:500])
                        _push_demo_event(4, "Resurrection Engine", "fork_response",
                                         f"[{src}] {ml_response[:100]}", "ok",
                                         {"source": src, "response": ml_response})
                        break
                if b.get("is_done"):
                    break

            step("get_resurrection_report")
            report = _safe_call(env, "get_resurrection_report", episode_id=res_id)
            if isinstance(report, dict):
                info(_short(report, limit=400))
                _push_demo_event(4, "Resurrection Engine", "get_resurrection_report", "Report generated", "ok", report)
        else:
            warn("No scenarios available — skipping resurrection demo.")

        # ── 11. USP-2 Ghost Founder ────────────────────────────────────────
        _scene("11/14  USP-2 Ghost Founder (human-in-the-loop)")
        _push_demo_event(4, "Ghost Founder", "11/14 Ghost Founder", "Human-in-the-loop takeover", "info")
        step("set_role_controller(ceo, human) — ghost takes over")
        res = _safe_call(env, "set_role_controller", episode_id=primary_id, role="ceo", controller="human")
        if res: 
            info(_short(res))
            _push_demo_event(4, "Ghost Founder", "set_role_controller", "CEO -> Human", "ok", res)
        step("log_human_action — ghost makes a decision")
        res = _safe_call(env, "log_human_action", episode_id=primary_id, role="ceo",
                        action="strategic_call",
                        details="Ghost CEO chose to delay Series-A negotiation 30d to push valuation.")
        if res: 
            info(_short(res))
            _push_demo_event(4, "Ghost Founder", "log_human_action", "Human decision logged", "ok", res)
        step("get_role_controllers")
        res = _safe_call(env, "get_role_controllers", episode_id=primary_id)
        if isinstance(res, dict):
            ok(f"Controllers: {res.get('role_controllers')}, "
               f"human_action_count={res.get('human_action_count')}")
            _push_demo_event(4, "Ghost Founder", "get_role_controllers", f"Roles: {res.get('role_controllers')}", "ok", res)
        step("set_role_controller(ceo, ai) — release back to AI")
        res = _safe_call(env, "set_role_controller", episode_id=primary_id, role="ceo", controller="ai")
        if res: 
            info(_short(res))
            _push_demo_event(4, "Ghost Founder", "set_role_controller", "CEO -> AI", "ok", res)

        # ── 12. USP-3 Founder Genome ───────────────────────────────────────
        _scene("12/14  USP-3 Founder Genome (capability benchmark)")
        _push_demo_event(4, "Founder Genome", "12/14 Founder Genome", "Capability benchmarking", "info")
        step(f"export_founder_genome({model_id})")
        res = _safe_call(env, "export_founder_genome", model_id=model_id)
        if isinstance(res, dict) and "artifacts" in res:
            ok(f"Genome JSON: {res['artifacts'].get('json')}")
            ok(f"Genome PNG : {res['artifacts'].get('png')}")
            _push_demo_event(4, "Founder Genome", "export_founder_genome", f"Exported {model_id}", "ok", res)
        elif res:
            info(_short(res))

        step(f"Running short rival episode ({secondary_model}) so we can compare")
        _push_demo_event(4, "Founder Genome", "rival_rollout", f"Rolling out {secondary_model}", "info")
        _safe_call(env, "reset", episode_id=secondary_id, difficulty=difficulty, seed=123,
                   model_id=secondary_model, model_provider="demo", model_version="run.py")
        for day in range(1, 11):
            role = roles[day % len(roles)]
            rival_briefing = _safe_call(env, "get_daily_briefing",
                                        episode_id=secondary_id, agent_role=role)
            if not isinstance(rival_briefing, dict):
                continue
            # Use the ML model for the rival too — different seed gives different outputs,
            # creating a genuine comparison of two ML-driven playthroughs
            rival_decision, rival_reasoning = _ml_decide(
                ml_model, ml_tokenizer, role, rival_briefing
            )
            _safe_call(env, "make_decision", episode_id=secondary_id, agent_role=role,
                       decision_type="tactical",
                       decision=rival_decision,
                       reasoning=rival_reasoning)
            if rival_briefing.get("is_done"):
                break
        _safe_call(env, "export_founder_genome", model_id=secondary_model)
        _push_demo_event(4, "Founder Genome", "export_founder_genome", f"Exported {secondary_model}", "ok")

        step("list_founder_genomes")
        listing = _safe_call(env, "list_founder_genomes")
        if isinstance(listing, dict):
            ok(f"Models with genomes: {listing.get('model_ids')}")
            _push_demo_event(4, "Founder Genome", "list_founder_genomes", f"Models: {len(listing.get('model_ids', []))}", "ok", listing)

        step(f"compare_founder_genomes([{model_id}, {secondary_model}])")
        res = _safe_call(env, "compare_founder_genomes", model_ids=[model_id, secondary_model])
        if isinstance(res, dict) and "artifacts" in res:
            ok(f"Comparison PNG: {res['artifacts'].get('png')}")
            _push_demo_event(4, "Founder Genome", "compare_founder_genomes", "Comparison chart generated", "ok", res)
        elif res:
            info(_short(res))

        # ── 13. Blockchain proofs ──────────────────────────────────────────
        _scene("13/14  Verifiable Simulation Proofs (blockchain layer)")
        _push_demo_event(4, "Blockchain Proofs", "13/14 Blockchain Proofs", "Simulation integrity (Merkle/Solana)", "info")
        step("get_simulation_proof_status")
        res = _safe_call(env, "get_simulation_proof_status", episode_id=primary_id)
        if isinstance(res, dict):
            ok(f"leaves={res.get('leaf_count')}, "
               f"checkpoint_index={res.get('last_checkpoint_index')}, "
               f"solana_configured={res.get('is_solana_configured')}")
            if res.get("explorer_url"):
                info(f"explorer: {res['explorer_url']}")
            _push_demo_event(4, "Blockchain Proofs", "get_simulation_proof_status", f"Leaves: {res.get('leaf_count')}", "ok", res)

        step("commit_simulation_proof(dry_run=True)")
        res = _safe_call(env, "commit_simulation_proof", episode_id=primary_id, dry_run=True)
        if isinstance(res, dict):
            ok(f"dry-run ok | leaves={res.get('leaf_count')} | "
               f"merkle_root={(res.get('merkle_root_hex') or '')[:16]}... | "
               f"fingerprint={(res.get('episode_fingerprint_hex') or '')[:16]}...")
            if res.get("pda_available"):
                info(f"on-chain PDA: {res.get('pda')}")
            else:
                info("Solana SDK not installed — Merkle root verified locally only. "
                     "Install with `pip install solana solders base58` to enable on-chain PDAs.")
            _push_demo_event(4, "Blockchain Proofs", "commit_simulation_proof", "Dry-run verified", "ok", res)

        # ── 14. Final reward ───────────────────────────────────────────────
        _scene("14/14  Final reward & breakdown")
        _push_demo_event(4, "Final Reward", "14/14 Final Reward", "Demo completion & final scorecard", "info")
        reward = _safe_call(env, "get_reward", episode_id=primary_id)
        if isinstance(reward, dict):
            ok(f"day={reward.get('day')}  total reward={reward.get('reward'):.3f}  "
               f"cumulative={reward.get('cumulative')}")
            breakdown = reward.get("breakdown") or {}
            for k, v in breakdown.items():
                try:
                    print(f"    · {k:<28} {float(v):.3f}")
                except Exception:
                    print(f"    · {k:<28} {v}")
            if reward.get("weaknesses"):
                info(f"MarketMaker weaknesses: {reward['weaknesses']}")
            _push_demo_event(4, "Final Reward", "get_reward", f"Final Score: {reward.get('reward'):.3f}", "ok", reward)

        ok("Demo complete — every major feature exercised.")
        _push_demo_event(4, "Final Reward", "demo_complete", "Full feature demo finished successfully", "ok")
    finally:
        try:
            env.close()
        except Exception:
            pass


# ── phase 4b: smoke test (training pipeline) ────────────────────────────────

def run_smoke() -> None:
    banner("Phase 4 — Training smoke test")
    step("python train.py --smoke")
    try:
        subprocess.run([sys.executable, "train.py", "--smoke"], cwd=str(ROOT), check=False)
    except FileNotFoundError:
        err("train.py not found.")


# ── phase 4c: regenerate reward plots ───────────────────────────────────────

def regenerate_plots() -> None:
    banner("Phase 4 — Regenerate reward plots")
    sessions = ROOT / "sessions.pkl"
    if not sessions.exists():
        warn("sessions.pkl missing; running plot script in --demo mode.")
        cmd = [sys.executable, str(ROOT / "scripts" / "plot_rewards.py"), "--demo"]
    else:
        cmd = [sys.executable, str(ROOT / "scripts" / "plot_rewards.py"),
               "--sessions", str(sessions), "--out", str(OUTPUTS_DIR)]
    step(" ".join(cmd))
    subprocess.run(cmd, cwd=str(ROOT), check=False)
    out_png = OUTPUTS_DIR / "reward_curves.png"
    out_json = OUTPUTS_DIR / "reward_summary.json"
    if out_png.exists(): ok(f"plot: {out_png}")
    if out_json.exists():
        try:
            data = json.loads(out_json.read_text())
            ok(f"summary keys: {list(data)[:6]}")
        except Exception:
            pass


# ── phase 5: idle / exit ────────────────────────────────────────────────────

def block_until_interrupt(backend_port: int, frontend_port: Optional[int]) -> None:
    banner("Phase 5 — Stack is live (Ctrl+C to stop)")
    print(f"  {C.GREEN}backend  {C.RESET}→ http://localhost:{backend_port}")
    print(f"  {C.GREEN}health   {C.RESET}→ http://localhost:{backend_port}/health")
    if frontend_port:
        print(f"  {C.GREEN}frontend {C.RESET}→ http://localhost:{frontend_port}")
    print(f"  {C.DIM}Founder Genomes → {EXPORTS_DIR}{C.RESET}")
    print(f"  {C.DIM}Reward plots    → {OUTPUTS_DIR}{C.RESET}")
    try:
        while True:
            time.sleep(1)
            for proc in list(_CHILDREN):
                if proc.poll() is not None:
                    err(f"child exited (pid={proc.pid}, code={proc.returncode}); shutting down.")
                    return
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}Ctrl+C received.{C.RESET}")


# ── interactive menu ────────────────────────────────────────────────────────

MENU = """
Pick a mode:

  [1] full        backend + frontend + demo rollout
  [2] stack       backend + frontend (long-running)
  [3] backend     backend only
  [4] frontend    frontend only (assumes backend already running)
  [5] demo        backend + scripted rollout, then exit
  [6] smoke       quick training smoke test
  [7] plots       regenerate reward curves & summary
  [8] doctor      environment / dependency check
  [q] quit
"""

def interactive_menu() -> str:
    print(MENU)
    while True:
        choice = input(f"{C.BOLD}>{C.RESET} ").strip().lower()
        mapping = {
            "1": "full", "full": "full",
            "2": "stack", "stack": "stack",
            "3": "backend", "backend": "backend",
            "4": "frontend", "frontend": "frontend",
            "5": "demo", "demo": "demo",
            "6": "smoke", "smoke": "smoke",
            "7": "plots", "plots": "plots",
            "8": "doctor", "doctor": "doctor",
            "q": "quit", "quit": "quit", "exit": "quit",
        }
        if choice in mapping:
            return mapping[choice]
        warn("Unrecognised choice; try again.")


# ── main ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="GENESIS one-shot launcher")
    parser.add_argument("--mode", choices=[
        "full", "stack", "backend", "frontend", "demo", "smoke", "plots", "doctor"
    ], default=None)
    parser.add_argument("--skip-install", action="store_true",
                        help="Skip pip install -e . and npm install.")
    parser.add_argument("--no-frontend", action="store_true",
                        help="Disable frontend even in modes that would start it.")
    parser.add_argument("--backend-port", type=int, default=7860)
    parser.add_argument("--frontend-port", type=int, default=3000)
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument("--difficulty", type=int, default=2)
    parser.add_argument("--episode-days", type=int, default=20)
    parser.add_argument("--model-id", type=str, default="demo-model")
    # ML model flags
    parser.add_argument("--no-ml", action="store_true",
                        help="Disable ML model — demo uses static fallback decisions.")
    parser.add_argument("--ml-adapter", type=str, default=None,
                        help="Path to PEFT LoRA adapter (default: models/genesis_final).")
    parser.add_argument("--ml-base-model", type=str, default="Qwen/Qwen2.5-3B-Instruct",
                        help="HuggingFace base model ID for the LoRA adapter.")
    args = parser.parse_args()

    mode = args.mode or interactive_menu()
    if mode == "quit":
        return 0

    healthy = doctor()
    if mode == "doctor":
        return 0 if healthy else 1
    if not healthy:
        warn("Continuing despite doctor warnings.")

    if not args.skip_install:
        banner("Phase 1 — Dependencies")
        if mode in {"full", "stack", "backend", "demo", "smoke", "plots"}:
            install_python_deps()
        if mode in {"full", "stack", "frontend"} and not args.no_frontend:
            install_frontend_deps()

    backend_proc: Optional[subprocess.Popen] = None
    backend_port: int = args.backend_port
    frontend_proc: Optional[subprocess.Popen] = None
    frontend_port: Optional[int] = None

    try:
        if mode in {"full", "stack", "backend", "demo"}:
            backend_proc, backend_port = start_backend(args.backend_port)

        if mode in {"full", "stack"} and not args.no_frontend:
            frontend_proc = start_frontend(args.frontend_port, backend_port)
            if frontend_proc:
                frontend_port = args.frontend_port

        if mode == "frontend" and not args.no_frontend:
            frontend_proc = start_frontend(args.frontend_port, backend_port)
            if frontend_proc:
                frontend_port = args.frontend_port

        if mode in {"full", "demo"}:
            run_demo(
                backend_port,
                episodes=args.episodes,
                difficulty=args.difficulty,
                episode_days=args.episode_days,
                model_id=args.model_id,
                use_ml=not args.no_ml,
                ml_adapter=args.ml_adapter,
                ml_base_model=args.ml_base_model,
            )

        if mode == "smoke":
            run_smoke()
            return 0

        if mode == "plots":
            regenerate_plots()
            return 0

        if mode == "demo":
            ok("Demo finished. Backend remaining active for inspection.")
            block_until_interrupt(backend_port, frontend_port)
            return 0

        block_until_interrupt(backend_port, frontend_port)
        return 0
    finally:
        _terminate_all()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        _terminate_all()
        sys.exit(130)
