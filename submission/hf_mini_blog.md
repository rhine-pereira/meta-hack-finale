# GENESIS: Training AI Co-Founders for 540-Day Startup Survival

GENESIS is a multi-agent simulation where five LLM co-founders build and operate a startup from Day 0 to Series A over 540 simulated days. The environment is designed for long-horizon decision-making under partial observability, delayed consequences, and social coordination constraints.

## Why This Environment Matters

Most business simulations optimize a single KPI (revenue, valuation, throughput). Real startups fail for multi-factor reasons: misalignment, toxic hires, rushed roadmap decisions, weak investor communication, and inability to adapt to market pressure.

GENESIS models this reality directly:

- 5 role-specialized agents (CEO, CTO, Sales, People, CFO)
- 42 MCP tools with realistic side effects and delays
- 11-component reward rubric balancing growth, health, and resilience
- Personal crisis events to test emotional intelligence under pressure
- Adaptive adversary (MarketMaker) that escalates difficulty

## Key Design Choices

### 1. Role-Scoped Information Asymmetry

Each co-founder sees only the information they should see in a realistic company. This forces coordination and negotiation instead of monolithic, omniscient planning.

### 2. Delayed Causality

Important actions have delayed outcomes:

- Hiring is onboarded after a delay
- Job postings create applicants after a delay
- Many strategic mistakes produce 30-90 day downstream effects

This makes short-term reward hacking harder and encourages robust planning.

### 3. Difficulty Curriculum

Gauntlet mode runs for 540 days with weekly personal crises. Agents must survive compounding uncertainty and maintain team/investor/customer dynamics over an 18-month arc.

## What We Trained and Measured

The training pipeline includes a minimal Unsloth + TRL setup and produces reproducible reward artifacts.

Training results (GRPO, 50 steps, Qwen2.5-3B-Instruct):

| | Baseline (untrained) | Post-GRPO trained |
|---|---|---|
| Avg final reward | 0.324 | 0.570 |
| Best episode reward | 0.390 | 0.714 |
| Improvement | — | **+75.8%** |

The largest gains came in Decision Coherence (+0.45) and CompanyBrain Quality (+0.47), confirming the model learned to use structured memory. Valuation (+0.31) and Co-founder Alignment (+0.30) also improved substantially.

See the 4-panel training figure in `outputs/evals/reward_curves.png` — it shows episode reward curves, the GRPO training trajectory, a per-component radar chart, and a delta bar chart.

## Why GENESIS Is Different

GENESIS focuses on business execution quality as a systems problem, not only on text generation quality. The environment can be used to train models that reason over strategy, operations, and human factors simultaneously.

That combination makes it a useful benchmark for long-horizon, economically meaningful agent behavior.

## Try It

- Space: https://huggingface.co/spaces/rhine-pereira/genesis_env
- Repo: https://github.com/rhine-pereira/meta-hack-finale
