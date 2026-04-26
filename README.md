# GENESIS — The Autonomous Startup Gauntlet

**Training LLMs to build, break, and rebuild companies from zero**

[![OpenEnv](https://img.shields.io/badge/OpenEnv-compatible-6366f1)](https://huggingface.co/openenv) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

[OpenEnv hackathon (India 2026)](https://huggingface.co/openenv) · **Hugging Face Space:** [`https://huggingface.co/spaces/rhine-pereira/genesis_env`](https://huggingface.co/spaces/rhine-pereira/genesis_env)

---

## What this is (one paragraph)

> Most startups do not fail because the technology was wrong; they fail because **coordination, planning, and human management** were wrong under uncertainty. **GENESIS** is an [OpenEnv](https://huggingface.co/openenv)-compliant environment in which **five role-specialized LLM agents** co-found a B2B SaaS company: they manage runway and fundraising, ship product with realistic **tech-debt and morale tradeoffs**, negotiate with a simulated market, handle **personally and ethically charged crises**, and may **pivot** mid-episode. The world is **stateful and causal** (actions have delayed side effects), **partially observable** (each role sees a filtered slice of state), and **adversarially teachable** via a **MarketMaker** that escalates scenario difficulty. The repository ships a **FastMCP** server, a **composable 11-dimensional reward** aligned with the design doc, a **GRPO** training path (Unsloth + TRL), Colab-friendly scripts, and **observable training artifacts** (curves and summary metrics).

This README is the primary narrative artifact for the submission: it ties the **codebase** to the **problem statement** (`context/hackathon_idea_3.md`), the **official hackathon themes** (extract in `pdf_text.txt`), and the **published judging rubric**.

---

## Table of contents

1. [Problem and research gap](#problem-and-research-gap)
2. [What GENESIS simulates (design ↔ implementation)](#what-genesis-simulates-design--implementation)
3. [How we map the five OpenEnv themes](#how-we-map-the-five-openenv-themes)
4. [How this maps the official judging criteria (40 / 30 / 20 / 10)](#how-this-maps-the-official-judging-criteria-40--30--20--10)
5. [Architecture (runtime and modules)](#architecture-runtime-and-modules)
6. [The five agent roles, partial observability, and hidden incentives](#the-five-agent-roles-partial-observability-and-hidden-incentives)
7. [The 28 MCP tools (agent API)](#the-28-mcp-tools-agent-api)
8. [World model: state, time, and causality](#world-model-state-time-and-causality)
9. [Personal and ethical scenarios (Theme 3.2)](#personal-and-ethical-scenarios-theme-32)
10. [MarketMaker (adaptive curriculum, Theme 4)](#marketmaker-adaptive-curriculum-theme-4)
11. [Pivots (Wild Card, Theme 5)](#pivots-wild-card-theme-5)
12. [Reward: 11-component composable rubric](#reward-11-component-composable-rubric)
13. [USP: Founder Genome (LLM Capability Benchmark)](#usp-founder-genome-llm-capability-benchmark)
14. [Training pipeline (GRPO, reproducibility)](#training-pipeline-grpo-reproducibility)
15. [OpenEnv compliance](#openenv-compliance)
16. [Install, run, and develop](#install-run-and-develop)
17. [Project layout](#project-layout)
18. [Submission materials and artifacts](#submission-materials-and-artifacts)
19. [License](#license)

---

## Problem and research gap

- **Economic / practical:** A large share of new ventures fail for **organizational** reasons: misaligned co-founders, bad prioritization, runway collapse, team burnout, and mishandled stakeholder communication—not because code could not be written.
- **Modeling gap:** Instruction-tuned models excel at local tasks, but **multi-agent alignment**, **long-horizon commitment** beyond context, and **theory of mind** under **information asymmetry** remain weak. GENESIS is built to **stress-test and train** those capabilities in a single, coherent domain that every technical judge can relate to: **running a company**.

The conceptual specification (narrative depth, 18-month arc, rubric design intent, adversarial curriculum) lives in **`context/hackathon_idea_3.md`**. This repository is the **executable slice** of that vision: a deterministic simulation core, a tool surface for agents, and a training loop that can emit **measurable** improvement on the defined reward.

---

## What GENESIS simulates (design ↔ implementation)

| Idea doc concept | In this repo |
|------------------|--------------|
| **540 simulated business days** (18-month arc) for the full “gauntlet” | `WorldState.max_days` defaults to **540**; difficulty presets scale episode length (90 → 720 days). |
| **Five co-founder roles** with different information | `server/role_views.py` filters `get_company_state` (and related payloads) per `AgentRole`. |
| **Stateful tools with side effects and delays** | `server/event_engine.py` advances the clock; hiring, listings, and other actions **resolve over multiple days**; burn, morale, and tech debt **accumulate**. |
| **Shared strategic memory** | `write_company_brain` / `read_company_brain` on `WorldState.company_brain`; used in the rubric (coherence and quality). |
| **Personal and ethical stress tests** | `server/world_init.py` — **`PERSONAL_CRISIS_TEMPLATES`**; `handle_personal_crisis` scores natural-language responses. |
| **Mid-episode pivot** | `pivot_company` in `server/app.py` with state updates; rubric includes **pivot execution** when pivots occur. |
| **Adaptive difficulty** | `server/market_maker.py` — **MarketMaker** tracks weaknesses and emits escalations. |

The simulation is **seed-driven** (`reset(..., seed=...)`) so runs are **reproducible** for training and for judge inspection.

---

## How we map the five OpenEnv themes

The hackathon document (`pdf_text.txt`) defines **five themes** and encourages submissions that add **real value to LLM training** on a difficult task. GENESIS is scoped to address **all five**:

| Theme | Name (brief) | How GENESIS addresses it |
|-------|----------------|-------------------------|
| **#1** | **Multi-agent** — cooperation, competition, negotiation, coalitions, partial observability | Five agents with **role-based views**; **messaging**; conflicting incentives in the spec (e.g. speed vs. quality, growth vs. runway); must coordinate via **shared memory** and comms. |
| **#2** | **Long-horizon planning** — sparse/delayed rewards, many decisions, recovery from early mistakes | **Multi-day episodes**, delayed consequences in `event_engine` (burn, hiring pipelines, pivot fallout); rubric includes **decision coherence** and **CompanyBrain** usage as proxies for durable planning. |
| **#3.1** | **World modeling (professional)** — real tools, APIs, no shortcuts | **28 MCP tools** (engineering, GTM, finance, people, memory); actions change **durable state**, not a one-line win condition. |
| **#3.2** | **World modeling (personal)** | **Eight** crisis **templates** (retention, ethics, family conflict, press, etc.) with **scored** responses. |
| **#4** | **Self-improvement** | **MarketMaker** observes state/reward and **escalates**; training script maintains **self-play** state (e.g. difficulty promotion/demotion) in `train.py`. |
| **#5** | **Wild card** | **Pivots** with rubric **PivotExecution**; optional collective vote parameter in the tool. |

The brief also allows **out-of-the-box** ideas as long as they **meaningfully** improve LLM training: GENESIS does so by unifying **multi-agent**, **long-horizon**, and **rich tool use** in one **narrative** environment.

---

## How this maps the official judging criteria (40 / 30 / 20 / 10)

From the hackathon PDF, teams are scored as follows. Below is a direct **crosswalk** (judges can verify each point in this repo and linked artifacts).

| Weight | Criterion | GENESIS evidence |
|--------|------------|------------------|
| **40%** | **Environment innovation** — novel, creative, challenging; tests agent behavior | First-class **startup operator** simulation: partial observability, **pivot**, **persona crises**, **28 tools**, **MarketMaker**; not a grid-world or a single-turn QA task. |
| **30%** | **Storytelling** — clear problem, environment, and agent behavior; engaging demo | This README, `submission/hf_mini_blog.md`, and `submission/demo_video_script.md`; **HF Space** for live interaction. |
| **20%** | **Improvement in rewards** — evidence of training progress (curves, metrics, before/after) | Real evaluation artifacts in `outputs/evals/` (generated from `sessions.pkl`). `outputs/evals/reward_curves.png` shows per-episode curves and final-reward scatter, **grouped by `model_id`** for clean comparisons; `outputs/evals/reward_summary.json` includes per-model averages. |
| **10%** | **Reward + pipeline** — coherent reward, meaningful change in **inference** behavior | `server/reward_engine.py` documents weights and **normalization**; `train.py` uses **GRPO** with environment reward; smoke path for CI/local validation. |

**Minimum requirements (PDF):** OpenEnv (latest) · minimal training in **Colab** with **Unsloth** or **HF TRL** · mini-blog or **&lt;2 min** video · environment on **Hugging Face Spaces**. This project includes `openenv.yaml`, `colab/training.ipynb`, `train.py`, `train_colab.py`, and the submission docs above.

**Submission rule:** one submission per team; **judges use the submitted Space URL** to evaluate. The canonical URL is listed at the top of this README.

---

## Architecture (runtime and modules)

```
┌──────────────────────────────────────────────────────────────────┐
│                    FastAPI + FastMCP (`server/app.py`)            │
├──────────────────────────────────────────────────────────────────┤
│  WorldState          Event engine            MarketMaker          │
│  (`world_state.py`)  (`event_engine.py`)   (`market_maker.py`)  │
│  Role-filtered        Daily tick,            Weaknesses,         │
│  observation          delayed effects,       curriculum shocks   │
│                      crisis injection                             │
├──────────────────────────────────────────────────────────────────┤
│  Reward engine                     World initializer               │
│  (`reward_engine.py`)            (`world_init.py`)              │
│  11-term weighted rubric         Customers, investors,          │
│                                    competitors, crisis templates  │
├──────────────────────────────────────────────────────────────────┤
│  28 MCP tools  ←→  `GenesisEnv` / OpenEnv MCPToolClient         │
│                    (`client.py` / `train_colab.py` inline)        │
└──────────────────────────────────────────────────────────────────┘
```

- **HTTP:** Uvicorn serves the FastMCP `http_app()` (default **port 7860** per `openenv.yaml`).
- **Persistence:** training sessions are saved for plotting (`server/app.py` + pickle hooks as implemented).

---

## The five agent roles, partial observability, and hidden incentives

| Agent | Domain | Sees (high level) | Hidden or restricted |
|-------|--------|-------------------|------------------------|
| **CEO** | Strategy, narrative, external comms | **Broad** financial and investor context | Exact **toxic** flags, deep product internals |
| **CTO** | Engineering, architecture | **Tech debt**, engineering-facing signals | **Cash** and sensitive investor details |
| **Sales** (Head of Sales) | Revenue, pipeline | **Customers**, MRR/ARR, competitive hooks | **Full financials**, internal morale detail |
| **People** (Head of People) | Hiring, culture, HR risk | **Morale**, toxic flags, people signals | **Cap table / deep customer** detail |
| **CFO** | Runway, models, fundraise prep | **Precise** financials, investor **sentiment** | **Toxic** employee flags, some product minutiae |

**Why this matters for judges:** agents cannot “read the full board”; they must **communicate** and **write to CompanyBrain** to align—matching **Theme 1** (partial observability) and **Theme 2** (state beyond any single context window).

---

## The 28 MCP tools (agent API)

Tools are registered on the **FastMCP** server; clients call them via the **MCP** JSON-RPC surface (OpenEnv client).

| Category | Tools |
|----------|--------|
| **Session & reward** | `reset`, `get_daily_briefing`, `get_company_state`, `get_reward` |
| **Decisions & comms** | `make_decision`, `send_message` |
| **Product & engineering** | `build_feature`, `deploy_to_production`, `run_load_test`, `review_codebase_health` |
| **Sales & market** | `send_customer_email`, `update_crm`, `analyze_market`, `run_competitive_analysis` |
| **Finance** | `check_bank_balance`, `create_financial_model`, `send_investor_update`, `negotiate_with_investor` |
| **People** | `hire_candidate`, `fire_employee`, `check_team_morale`, `post_job_listing`, `conduct_interview`, `hold_one_on_one` |
| **Strategy** | `pivot_company`, `handle_personal_crisis` |
| **Shared memory** | `write_company_brain`, `read_company_brain` |

`train.py` restricts training-time tool use to a **stability subset** and mirrors **per-role** allowlists; the **full** server surface remains available for full agents and for Space demos.

---

## World model: state, time, and causality

- **Clock:** `WorldState.day` advances in `tick_day` (`server/event_engine.py`). Each tick can emit **events** (market, churn, press-like descriptions, etc.).
- **Finances:** starting **cash**, **burn**, runway derived from state; **valuation** and **Series A** flags feed the rubric.
- **Product:** `PendingFeature` models **in-flight** work; **tech debt** and **uptime** couple engineering choices to **customer** and **velocity** scores.
- **Team:** `Employee` includes **skill**, **morale**, **burnout**, **flight risk**, and **toxic** (hidden from some roles) — so “bad hire” and “toxic retain” can **hurt morale** in the rubric.
- **Market:** `Competitor`, **investors** with thesis and **sentiment**, and **candidates** for hiring pipelines.

**Design intent:** no single lever maximizes the rubric: e.g. shipping fast without debt control eventually **damages** product score; ignoring crises **degrades** `personal_crisis_handling`.

---

## Personal and ethical scenarios (Theme 3.2)

Crisis templates in `server/world_init.py` include situations such as **CTO retention** after a big-tech offer, **post-pivot team despair**, **metric inflation** pressure, **family vs. investor** scheduling, **knowledge bus factor**, and **press / reputation** events. The **`handle_personal_crisis`** tool scores free-text **responses** (length and substance heuristics in `app.py`) and feeds **`personal_crisis_handling`** in `reward_engine.py`.

This is explicitly aimed at **non-toy** “human” difficulty: the right action is not a single boolean—it depends on **context** and **stakeholder** tradeoffs.

---

## MarketMaker (adaptive curriculum, Theme 4)

`server/market_maker.py` implements a **MarketMaker** that:

- **Observes** team morale, runway, tech debt, co-founder **alignment**, and similar signals.
- **Records** a **weakness** list (e.g. `team_management`, `financial_planning`, `architecture_planning`, `communication`).
- **Escalates** with **market shocks** and **narrated** follow-on challenge (e.g. shift to reliability expectations, “funding winter” narrative when fundraising succeeded).

`train.py` extends this with **self-play** state: **rolling average reward** vs. **PROMOTE_THRESHOLD** / **DEMOTE_THRESHOLD** to **raise or lower** training difficulty, so the **outer loop** chases a curriculum rather than a static scenario.

---

## Pivots (Wild Card, Theme 5)

`pivot_company` updates company direction in state (see `server/app.py` and `_execute_pivot`). A pivot is **strategically costly**: existing product context becomes partially obsolete while **team** and **customer** variables still matter. The rubric’s **`pivot_execution`** term rewards better outcomes when pivots occur (customer retention and morale blend); if **no** pivot, the component is **neutral** (0.5) to avoid punishing a valid “stay the course” strategy.

---

## Reward: 11-component composable rubric

Implemented in `server/reward_engine.py` with **fixed weights** that sum to a single **`total` ∈ [0, 1]** (component-wise 0–1, then weighted).

| Component | Weight | Role |
|-----------|--------|------|
| `company_valuation` | **0.20** | Tied to valuation vs. a **$20M** normalization cap |
| `series_a_success` | **0.10** | **Binary** close flag |
| `runway_management` | **0.10** | Favors **healthy runway**; punishes the danger zone |
| `product_velocity` | **0.10** | Features vs. time, **debt** penalty, **uptime** boost |
| `customer_retention` | **0.10** | Satisfaction × (1 − churn risk), averaged over customers |
| `team_morale` | **0.10** | Team morale with **toxic** penalty while employed |
| `cofounder_alignment` | **0.05** | From `WorldState` alignment |
| `personal_crisis_handling` | **0.05** | Resolution quality and **ignored** crisis rate |
| `decision_coherence` | **0.10** | Proxy: **substantive** CompanyBrain keys (length-threshold) |
| `company_brain_quality` | **0.05** | **Total** stored characters (capped) |
| `pivot_execution` | **0.05** | If pivots **= 0** → neutral; else blend of **retention** and **morale** |

`get_reward` exposes this breakdown to trainers and evaluators. The design matches the **composable** rubric philosophy in `context/hackathon_idea_3.md`: **no single metric** is safe to overfit in isolation.

---

## USP: Founder Genome (LLM Capability Benchmark)

GENESIS creates a **Founder Assessment Profile** by aggregating performance across multiple episodes. This isn't just a high-score; it's a **behavioral fingerprint** of the LLM’s startup capability.

- **Founder Genome Card:** Every model run can generate an exportable **JSON + PNG** "Genome Card"—a radar chart of the 11 dimensions (Valuation, Series A, Morale, etc.).
- **Model Comparison:** Head-to-head comparisons (e.g., Claude vs GPT vs Gemini) show relative strengths. One model might be a "Product Visionary" (high velocity, low runway management), while another is a "Risk-Averse Operator" (high runway, low velocity).
- **Verifiable Benchmark:** Combined with **Blockchain Proofs**, these genomes provide a verifiable way to claim "Model X is better at handling pivot pressure than Model Y."

**Export a Genome:**
Use the `export_founder_genome(model_id="qwen2.5-7b")` tool to aggregate sessions from `sessions.pkl` and generate artifacts in `exports/founder_genomes/`.

---

## Training pipeline (GRPO, reproducibility)

| Artifact | Purpose |
|----------|---------|
| **`train.py`** | **GRPO** (TRL) on Unsloth-compatible models; **Windows** Triton **mock** for local dev; connects to a running server via `GenesisEnv`; **SelfPlayState** and role-scoped **ALLOWED_TOOLS**. |
| **`train_colab.py`** | **Colab-first**: clone/pull repo, **pin** `torch` to Colab’s build to **avoid Triton/PTX** mismatches, inline **GenesisEnv** for MCP, same training idea as `train.py`. |
| **`colab/training.ipynb`** | Notebook path for the hackathon’s **“minimal training in Colab”** requirement. |
| **`scripts/plot_rewards.py`** | Builds **`outputs/evals/reward_curves.png`** and **`outputs/evals/reward_summary.json`**. |

**Typical local checks:**

```bash
# Start the server (from repo root)
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

```bash
# In another shell: smoke test (no full GPU training required for validation)
python train.py --smoke
```

```bash
# Short training run (adjust --steps, --difficulty, --episode-days)
python train.py --steps 50
```

```bash
# Regenerate evaluation plots (expects session logs as implemented)
python scripts/plot_rewards.py --sessions sessions.pkl --out outputs/evals
```

**Defaults (from `train.py` args):** e.g. `unsloth/Qwen2.5-7B-Instruct-bnb-4bit`, **difficulty** levels **1–5**, configurable **`--episode-days`** for shorter **rollouts** during iteration.

---

## OpenEnv compliance

`openenv.yaml`:

```yaml
spec_version: 1
name: genesis_env
type: space
runtime: fastapi
app: server.app:app
port: 7860
```

Dependencies are listed in `pyproject.toml` (`openenv-core[core]>=0.2.3`, **FastMCP**, **FastAPI**, etc.).

---

## Install, run, and develop

**Install (editable):**

```bash
pip install -e .
# Optional: dev (pytest, etc.)
pip install -e ".[dev]"
```

**Run the server:**

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

Entry point also available as **`python -m server.app`** (see existing packaging).

**Minimal Python client (local):**

```python
from client import GenesisEnv

with GenesisEnv(base_url="http://127.0.0.1:7860") as env:
    env.reset()
    out = env.call_tool("get_daily_briefing", agent_role="ceo")
```

**Health check:** `GET /health` → `{"status":"ok"}`.

**Docker / Space:** `Dockerfile` in repo root for **Hugging Face Spaces** deployment.

---

## Project layout

```
├── server/
│   ├── app.py            # FastMCP server, 28 tools, session handling
│   ├── world_state.py    # WorldState, employees, customers, rubric inputs
│   ├── world_init.py     # Seeding, investors, crisis templates
│   ├── event_engine.py   # Daily tick, delays, events
│   ├── reward_engine.py  # 11-term composable rubric
│   ├── market_maker.py   # Adaptive adversary
│   └── role_views.py     # Per-role state filtering
├── client.py             # OpenEnv MCPToolClient wrapper (local)
├── train.py              # GRPO training (main script)
├── train_colab.py        # Colab-oriented training + install
├── colab/training.ipynb  # Colab notebook
├── scripts/
│   ├── plot_rewards.py
│   └── organize_repo.py  # Repo cleanup (dry-run by default)
├── tools/
│   └── dev/              # One-off dev utilities (route listing, validators, etc.)
├── docs/
│   └── design.md
├── openenv.yaml
├── Dockerfile
├── context/hackathon_idea_3.md   # full design narrative
├── submission/                    # blog draft + demo script
├── outputs/evals/                 # committed reward plot + JSON (evidence)
└── tests/
```

---

## Submission materials and artifacts

| Item | Location / URL |
|------|----------------|
| **Hugging Face Space** | [`https://huggingface.co/spaces/rhine-pereira/genesis_env`](https://huggingface.co/spaces/rhine-pereira/genesis_env) |
| **Mini-blog (publishable)** | `submission/hf_mini_blog.md` |
| **Demo script (≤2 min)** | `submission/demo_video_script.md` |
| **Reward curve image** | `outputs/evals/reward_curves.png` |
| **Reward summary** | `outputs/evals/reward_summary.json` |

**Snapshot of evaluation metrics (regenerate with `python scripts/plot_rewards.py --sessions sessions.pkl --out outputs/evals --summarize-models`):**

| Metric | Value (this repo) |
|--------|-------------------|
| Sessions with history | 110 |
| Avg final reward (all) | 0.4547 |
| Best / worst final reward (all) | 0.5022 / 0.2875 |
| Baseline (`baseline_static`) avg final reward | 0.4610 (n=40) |
| Ollama `mistral:latest` avg final reward | 0.4707 (n=31) |
| Ollama `deepseek-coder:6.7b` avg final reward | 0.4604 (n=30) |

> These numbers come from local GPU rollouts (Ollama) tagged with `model_id` and evaluated under identical settings (same difficulty, episode length, and seed range).

### Evaluation evidence (model-wise figure)

![GENESIS reward curves](outputs/evals/reward_curves.png)

*Left: reward curves grouped by `model_id` (mean ± std with moving average) to avoid mixed-model confusion.
Right: final reward per episode colored by `model_id` for a clean head-to-head comparison.*

---

## License

MIT

---

## Acknowledgment

**GENESIS** was conceived as a **multi-agent, long-horizon, tool-rich** training world for the **OpenEnv** ecosystem. This repository implements an **MCP-first** server, a **fully specified reward**, and a **reproducible** training and evaluation path so judges and researchers can **inspect**, **run**, and **extend** the environment without guesswork.
