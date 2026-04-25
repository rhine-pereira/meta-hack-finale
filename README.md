# GENESIS — The Autonomous Startup Gauntlet

> Training LLMs to Build, Break, and Rebuild Companies From Zero

**GENESIS** is a multi-agent startup simulation environment where 5 LLM agents co-found and operate a technology startup from Day 0 through Series A. Built for the [OpenEnv Hackathon](https://huggingface.co/openenv).

## The Problem

95% of startups fail — not because the technology was wrong, but because coordination, planning, and human management failed. GENESIS trains LLMs to handle all of this simultaneously across 540 simulated business days.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   GENESIS MCP Server                │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐ │
│  │ WorldState│  │  Event   │  │    MarketMaker    │ │
│  │  Engine   │  │  Engine  │  │ (Adaptive Adversary)│
│  └──────────┘  └──────────┘  └───────────────────┘ │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐ │
│  │  Reward  │  │   Role   │  │   28 MCP Tools    │ │
│  │  Engine  │  │  Views   │  │ (Agent-facing API) │ │
│  └──────────┘  └──────────┘  └───────────────────┘ │
└─────────────────────────────────────────────────────┘
         ▲              ▲              ▲
    CEO Agent      CTO Agent     Sales Agent ...
```

## The 5 Agent Roles

| Agent | Domain | Sees | Hidden From |
|---|---|---|---|
| **CEO** | Strategy, fundraising | Full financials, investors (approx) | Toxic flags, exact tech debt |
| **CTO** | Technology, architecture | Exact tech debt, full employee skills | Cash balance, investor sentiment |
| **Sales** | Revenue, customers | Full customer data, MRR/ARR | Cash, tech debt, team morale |
| **People** | HR, culture, hiring | Employee toxic flags, full morale | Financials, customers, investors |
| **CFO** | Finance, fundraising prep | Exact financials, investor sentiment | Toxic flags, deep product details |

## 28 MCP Tools

### Product & Engineering (CTO)
`build_feature` · `deploy_to_production` · `run_load_test` · `review_codebase_health`

### Sales & Market
`send_customer_email` · `update_crm` · `analyze_market` · `run_competitive_analysis`

### Finance & Fundraising (CEO/CFO)
`check_bank_balance` · `create_financial_model` · `send_investor_update` · `negotiate_with_investor`

### People & Culture
`hire_candidate` · `fire_employee` · `check_team_morale` · `hold_one_on_one` · `post_job_listing` · `conduct_interview`

### Strategy & Communication
`make_decision` · `send_message` · `pivot_company` · `handle_personal_crisis`

### Shared Memory
`write_company_brain` · `read_company_brain`

### System
`reset` · `get_daily_briefing` · `get_company_state` · `get_reward`

## 11-Component Reward Rubric

```
CompanyValuation     (0.20)  — ARR × 8x multiple + maturity bonus
SeriesASuccess       (0.10)  — Binary: did you close Series A?
RunwayManagement     (0.10)  — Never run out of cash
ProductVelocity      (0.10)  — Features shipped / tech debt ratio
CustomerRetention    (0.10)  — Net satisfaction × (1 - churn)
TeamMorale           (0.10)  — Average morale - toxic penalty
CofounderAlignment   (0.05)  — Are founders on the same page?
PersonalCrisisHandl. (0.05)  — Were crises resolved well?
DecisionCoherence    (0.10)  — Long-horizon planning quality
CompanyBrainQuality  (0.05)  — Is shared memory useful?
PivotExecution       (0.05)  — If pivoted: was it clean?
```

**Impossible to game:** Boosting one metric at the expense of another creates cascading crises 30-90 days later.

## Difficulty Levels (Curriculum Learning)

| Level | Days | Competitors | Crises | Description |
|---|---|---|---|---|
| 1 Tutorial | 90 | 1 weak | Rare | Learn the basics |
| 2 Seed | 180 | 2 moderate | Monthly | Standard seed stage |
| 3 Growth | 360 | 3 aggressive | Bi-weekly | Scaling challenges |
| 4 Gauntlet | 540 | 4 + incumbent | Weekly | Full 18-month arc |
| 5 Nightmare | 720 | 4 + market crash | Constant | Adversarial conditions |

The **MarketMaker** adaptive adversary observes agent weaknesses and generates counter-scenarios each episode.

## Quick Start

```bash
# Install
pip install -e .

# Run server
uvicorn server.app:app --host 0.0.0.0 --port 7860

# Or via MCP
python -m server.app
```

### Python Client

```python
from client import GenesisEnv

with GenesisEnv(base_url="http://localhost:7860") as env:
    env.reset()
    tools = env.list_tools()
    result = env.call_tool("get_daily_briefing", agent_role="ceo")
```

## OpenEnv Compliance

```yaml
spec_version: 1
name: genesis_env
type: space
runtime: fastapi
app: server.app:app
port: 7860
```

## Project Structure

```
├── server/
│   ├── app.py           # MCP server with 28 tools
│   ├── world_state.py   # Core simulation state
│   ├── world_init.py    # World initialization & crisis templates
│   ├── event_engine.py  # Daily simulation tick
│   ├── reward_engine.py # 11-component composable rubric
│   ├── market_maker.py  # Adaptive adversary
│   └── role_views.py    # Role-based observability filters
├── client.py            # OpenEnv client wrapper
├── openenv.yaml         # OpenEnv configuration
├── Dockerfile           # HF Space deployment
└── tests/
    └── test_role_views.py
```

## Hackathon Themes Coverage

| Theme | How GENESIS Covers It |
|---|---|
| **Multi-Agent (Theme 1)** | 5 agents with partial observability, hidden incentives, coalition formation |
| **Long-Horizon (Theme 2)** | 540-day episodes with cascading 30-90 day consequences |
| **Professional World (Theme 3.1)** | 28 MCP tools with realistic delays and side effects |
| **Personal World (Theme 3.2)** | 8 personal crisis templates testing emotional intelligence |
| **Self-Improvement (Theme 4)** | MarketMaker generates harder scenarios based on agent weaknesses |
| **Wild Card (Theme 5)** | Mid-episode pivot mechanic — strategic sunk-cost abandonment |

## Hackathon Submission Checklist

- [x] Uses OpenEnv with `openenv.yaml` manifest
- [x] OpenEnv runtime server with MCP tools (`server/app.py`)
- [x] Minimal training pipeline using Unsloth + TRL (`train.py`)
- [x] Colab notebook for training (`colab/training.ipynb`)
- [x] Reward plotting script (`scripts/plot_rewards.py`)
- [x] Reward plot artifact committed (`outputs/evals/reward_curves.png`)
- [x] Reward summary metrics committed (`outputs/evals/reward_summary.json`)
- [x] README includes embedded reward plot (below)
- [x] Hugging Face Space URL added below
- [x] Mini-blog draft + 90-second demo script added (`submission/`)

## Submission Links

- Hugging Face Space (required): `https://huggingface.co/spaces/rhine-pereira/genesis_env`
- Mini-blog draft (publishable to HF): `submission/hf_mini_blog.md`
- 90-second demo script (for YouTube upload): `submission/demo_video_script.md`

Judges are expected to use the Space URL for evaluation.

## Minimal Colab Training Script

Use the notebook at `colab/training.ipynb` for a reproducible baseline run in Colab using Unsloth + TRL.

Notebook flow:

1. Install dependencies.
2. Run a smoke test (`python train.py --smoke`) to validate environment + reward pipeline.
3. Run a short GRPO training command (`python train.py --steps 50`).
4. Generate reward artifacts with `python scripts/plot_rewards.py`.

## Training Evidence Artifacts

- Reward curves: `outputs/evals/reward_curves.png`
- Reward summary: `outputs/evals/reward_summary.json`

### Embedded Reward Plot

![GENESIS reward curves](outputs/evals/reward_curves.png)

### Reward Summary Snapshot

| Metric | Value |
|---|---|
| Sessions with history | 6 |
| Average final reward | 0.3477 |
| Best final reward | 0.4472 |
| Worst final reward | 0.2655 |

## Reproduce Artifacts Locally

```bash
python train.py --smoke
python scripts/plot_rewards.py --sessions sessions.pkl --out outputs/evals
```

## License

MIT
