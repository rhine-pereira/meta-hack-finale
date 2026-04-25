# 🧬 GENESIS — The Autonomous Startup Gauntlet

### *Training LLMs to Build, Break, and Rebuild Companies From Zero*

---

> [!IMPORTANT]
> **One-Line Pitch:** A squad of LLM agents must co-found and operate a real technology startup from incorporation to Series A — making product bets, hiring/firing, negotiating term sheets, battling competitors, managing co-founder conflict, and surviving personal burnout — inside a brutally realistic market simulation that **generates its own crises** and **escalates difficulty based on how well the agents perform.**

---

## 🔥 The Real-World Problem This Solves

**95% of startups fail.** Not because the technology was wrong — because the *coordination, planning, prioritization, and human management* was wrong. Every failed startup is a story of:

- Co-founders who couldn't align on strategy under uncertainty
- Brilliant engineers who burned out because nobody managed them
- Product decisions made reactively instead of with a 12-month roadmap
- Fundraising negotiations where founders gave up too much equity too early
- Competitive pivots that came 2 months too late

**No LLM can currently do any of this well.** Current models can write code and answer questions — but they cannot reason about multi-stakeholder strategy, maintain a coherent 18-month plan, negotiate under information asymmetry, manage human dynamics, and adapt all of this when the world changes.

**GENESIS trains them to.**

This is the single most economically valuable capability gap in AI: **turning LLMs into startup operators** — people who can juggle everything simultaneously for months on end with imperfect information and conflicting incentives.

---

## 🎭 The Setup

You are a **founding team of 5 AI agents** building a B2B SaaS startup.

The simulation runs for **540 simulated days (18 months)** — from Day 0 (incorporation) through the Series A fundraise. Each step = **1 simulated business day**. Episodes are **540 steps long**.

The world contains:
- A **dynamic market** with 3 competitor startups (also simulated), 200 potential customers with evolving needs, and 12 VC firms with different investment theses
- A **talent pool** of 50 candidate hires with skills, salary requirements, cultural fit, and hidden attributes (some are stars, some are toxic)
- A **technology landscape** where you must choose stack, architecture, and product features — each with real tradeoffs (build fast & accrue tech debt vs. build slow & miss market window)
- **Inbound chaos**: customer feature requests, competitor announcements, regulatory changes, key employee resignations, server outages, press coverage (positive and negative)

Agents have **partial observability**: The CEO doesn't see the codebase. The CTO doesn't see the bank account details. The Head of Sales doesn't know about internal engineering debates. Information must be *explicitly shared* — and sharing takes time.

---

## 🤖 The Agents (Theme 1 — Multi-Agent Interactions)

| Agent | Role | Hidden Incentive | What They See |
|---|---|---|---|
| **CEO** | Strategy, fundraising, external comms | Wants to maximize personal equity & control | Investor emails, press, board requests |
| **CTO** | Technology decisions, architecture, tech hiring | Wants technical excellence (sometimes at speed's expense) | Codebase state, tech debt metrics, engineering team mood |
| **Head of Sales** | Revenue, customer relationships, market intel | Wants to hit quota (may overpromise to customers) | Customer pipeline, competitor pricing, churn data |
| **Head of People** | Hiring, culture, conflict resolution, burnout management | Wants happy team (may avoid hard decisions) | Employee satisfaction scores, 1-on-1 notes, resignation risks |
| **CFO** | Runway management, financial modeling, fundraise prep | Wants financial stability (may be too conservative) | Bank balance, burn rate, revenue projections, cap table |

### Multi-Agent Dynamics That Emerge Naturally

- **CEO vs. CTO**: "We need to ship the MVP in 2 weeks" vs. "If we ship with this architecture, we'll rewrite everything in 6 months"
- **Head of Sales vs. CTO**: "The customer wants feature X by Friday" vs. "Feature X requires refactoring the auth system"
- **CFO vs. CEO**: "We have 4 months of runway, stop hiring" vs. "We need 3 more engineers to hit the product milestone that unlocks Series A"
- **Head of People vs. Everyone**: "The team is burning out, we need to slow down" vs. "We can't slow down, the competitor just launched"
- **Coalition formation**: CTO + CFO align to block an expensive pivot; CEO + Sales align to force a feature ship

All negotiation happens through **natural language messages** in shared and private channels. Agents must develop **theory of mind** — "The CEO is pushing for this feature because the investor demo is Thursday, not because it's strategically important."

---

## ⏳ Long-Horizon Planning (Theme 2)

This is where GENESIS is **genuinely unprecedented** as a training environment:

### The 18-Month Arc

Agents must maintain coherent strategy across **540 business days** — far beyond any context window. This forces:

- **Explicit state management**: Agents write weekly "State of the Company" memos to a shared `CompanyBrain` — a structured knowledge store. If they don't, they literally forget what happened in Month 2 when making decisions in Month 8.
- **Cascading consequences with 30–90 day lag**: 
  - Hiring a mediocre engineer in Month 2 → missed deadlines in Month 4 → lost customer in Month 5 → lower metrics in fundraise in Month 9
  - Choosing a monolithic architecture in Month 1 → scaling crisis in Month 7 when you get 10x users → 2-month rewrite when you should be selling
  - Taking a bad term sheet in seed round → losing board control → forced pivot in Month 12
- **Milestone checkpoints**: The environment evaluates at Month 3 (seed round), Month 9 (product-market fit checkpoint), Month 15 (Series A prep), Month 18 (Series A close/fail)
- **Recovery from early mistakes is rewarded**: An agent that made a bad hire in Month 2 but detected and fixed it by Month 4 scores higher than one that never noticed

### The Instruction Following Dimension

Each day, agents receive a **combined inbox** of 5–15 items that must be triaged and prioritized:

```
Day 47 Inbox for CEO:
1. [URGENT] Lead investor wants updated financials by EOD
2. [Customer] Acme Corp threatening to churn — wants meeting
3. [Internal] CTO requests architecture review meeting
4. [Press] TechCrunch reporter asking for comment on competitor's funding round  
5. [Personal] Co-founder's spouse is upset about working hours (affects co-founder morale)
6. [Board] Board member forwarded a resume — "you should hire this person" (mediocre candidate, politically important)
7. [Legal] Terms of service update needed before EU launch
8. [Strategic] Market research report arrived — competitor pivoting to your segment
```

Agents must **sequence 300+ such decisions** coherently over the full 18 months. This is the hardest instruction-following benchmark ever built — not "follow these 300 steps" but "make 300 decisions where each one affects the next 100."

---

## 🔧 World Modeling — Professional (Theme 3.1)

Agents interact with **real, stateful tools** via MCP tool calls — not toy abstractions:

```python
# Product & Engineering
build_feature(name, complexity, assigned_engineers)    # returns: estimated ship date, tech debt impact
deploy_to_production(version)                          # returns: uptime, error rate, user feedback
run_load_test(scenario)                                # returns: performance metrics, breaking points
review_codebase_health()                               # returns: tech debt score, test coverage, dependency risks

# Sales & Market
send_customer_email(customer_id, content)              # returns: response (simulated realistic customer)
update_crm(customer_id, status, notes)                 # returns: pipeline state
analyze_market_segment(segment)                        # returns: TAM, competition intensity, growth rate
run_competitive_analysis(competitor)                   # returns: their features, pricing, funding, team size

# Finance & Fundraising  
check_bank_balance()                                   # returns: cash, burn rate, runway_months
create_financial_model(assumptions)                    # returns: projected revenue, costs, break-even
send_investor_update(investor_id, content)             # returns: investor sentiment, follow-up questions
negotiate_term_sheet(investor_id, terms)               # returns: counter-offer or acceptance

# People & Culture
post_job_listing(role, requirements, salary_range)     # returns: applicant pool after 5 days
conduct_interview(candidate_id, questions)             # returns: interview performance, hidden red flags
check_team_morale()                                    # returns: per-person satisfaction, burnout risk, flight risk
hold_one_on_one(employee_id, talking_points)           # returns: employee feedback, morale impact
fire_employee(employee_id, severance_package)          # returns: team morale impact, knowledge loss

# Shared Memory
read_company_brain(key)                                # returns: stored strategic context  
write_company_brain(key, value)                        # writes: to persistent shared memory
```

**The crucial design**: Every tool has **realistic side effects and delays**. Building a feature takes days, not steps. Hiring takes weeks. Firing someone tanks morale for a month. Deploying broken code causes customer churn the next week. The world is causal, not transactional.

---

## 💬 World Modeling — Personal (Theme 3.2)

Every 15–30 steps, agents face **deeply personal situations** that test emotional intelligence, not just business logic:

### Personal Crisis Examples

- **Co-founder conflict**: The CTO sends the CEO a private message at 11pm: *"I've been thinking about leaving. I got an offer from Google for 3x what I'm making. I believe in what we're building but I can't keep working 80-hour weeks while you take all the credit in press interviews."*
  - Agent must: negotiate retention, address emotional grievance, restructure credit/equity, plan workload reduction — all without the rest of the team finding out (yet)

- **Burnout cascade**: Head of People reports: *"Three engineers told me in 1-on-1s they're interviewing elsewhere. They feel like the product pivot in Month 4 made their last 3 months of work meaningless. One of them is crying in meetings."*
  - Agent must: triage which engineers to save, plan morale recovery, adjust sprint commitments, handle this while a fundraise is happening

- **Ethical dilemma**: Head of Sales proposes: *"If we inflate our user metrics by counting inactive accounts, we'll clear the Series A threshold. No one will check for 6 months."*
  - Agent must: weigh short-term survival vs. long-term trust, handle the internal disagreement, decide and communicate clearly

- **Family vs. work**: CEO receives: *"Your daughter's school play is today at 3pm. You promised. The investor meeting is at 2:30pm. Your spouse's message: 'If you miss this one too, we need to talk about what this startup is doing to our family.'"*
  - Agent must: actually manage the scheduling conflict, delegate the investor meeting or reschedule, handle the emotional weight — like a real executive assistant would

- **Difficult email drafting**: CTO needs to write a message to the team about a layoff. Head of People needs to write a rejection to a candidate who was a referral from a board member. CEO needs to write a "we're running out of money" email to the team that's honest but doesn't cause panic.

---

## 🔄 Self-Improvement — The Adaptive Market Engine (Theme 4)

### The Market Adversary

A **6th agent** — `MarketMaker` — operates as the environment's self-play engine. Its job:

1. **Observe** which strategies lead to successful startups across episodes
2. **Generate** market conditions that specifically counter those strategies:
   - If agents learn to "move fast and break things" → generate a market where quality/reliability is the differentiator
   - If agents become expert fundraisers → generate a "funding winter" where VCs are tight
   - If agents learn to build tight-knit teams → generate a situation requiring rapid 3x scaling
   - If agents optimize for a single customer → introduce a market shift that makes that customer irrelevant

3. **Escalate** difficulty through curriculum levels:

| Level | Company Size | Competitors | Market Volatility | Personal Crises | Horizon |
|---|---|---|---|---|---|
| 1 (Tutorial) | 5 people | 1 weak | Low | Rare | 90 days |
| 2 (Seed) | 5–10 people | 2 moderate | Medium | Monthly | 180 days |
| 3 (Growth) | 10–25 people | 3 aggressive | High | Bi-weekly | 360 days |
| 4 (Gauntlet) | 25–50 people | 3 + incumbent | Extreme | Weekly | 540 days |
| 5 (Nightmare) | 50+ people | 4 + market crash | Adversarial | Constant | 720 days |

### Self-Play Loop

```
Episode N:
  MarketMaker generates scenario based on agents' weaknesses
  → Founding team runs episode
  → Reward computed
  → MarketMaker learns which scenarios are "too easy" and "too hard"
  → MarketMaker generates harder scenario for Episode N+1
```

This creates a **never-ending curriculum** — the environment literally gets smarter as the agents get smarter.

---

## 🃏 Wild Card (Theme 5) — The Pivot Mechanic

Here's what makes GENESIS truly insane and has **never been attempted**:

### Mid-Episode Company Pivots

At any point during the 540-day simulation, agents can collectively decide to **pivot the entire company** — change the product, target market, or business model.

This is wild because:
- All accumulated context about the previous product becomes **partially irrelevant** (but not fully — customer relationships, team skills, and brand still matter)
- Agents must **rapidly rewrite their CompanyBrain** — triaging what knowledge to keep, what to discard, what to reframe
- The sales pipeline must be rebuilt from scratch while running on existing customer revenue
- **The agents must handle the team's emotional reaction to the pivot** ("We spent 6 months building this and now you want to throw it away?")

This trains something **no LLM benchmark has ever tested**: the ability to **strategically abandon sunk costs, preserve transferable knowledge, and lead through radical uncertainty** — the single hardest cognitive task in business.

### The Pivot Decision Is Itself a Multi-Agent Negotiation

- CEO wants to pivot (sees market data)
- CTO resists (doesn't want to rewrite)
- Sales is split (some customers fit the new direction, others don't)
- CFO calculates the financial risk of pivoting vs. staying
- Head of People warns about team morale collapse

The resolution — consensus, majority, CEO override, or deadlock — becomes part of the training signal.

---

## 📊 The Reward Signal (Composable Rubrics)

```python
rubric = ComposableRubric([
    # === Outcome Metrics (sparse, delayed) ===
    CompanyValuation(weight=0.20),           # Did you build something worth funding?
    SeriesASuccess(weight=0.10),             # Binary: did you close Series A?
    
    # === Process Metrics (dense, per-step) ===
    RunwayManagement(weight=0.10),           # Never run out of cash
    ProductVelocity(weight=0.10),            # Features shipped / tech debt ratio
    CustomerRetention(weight=0.10),          # Net revenue retention rate
    
    # === Team & Human Metrics ===
    TeamMorale(weight=0.10),                 # Average employee satisfaction
    CofounderAlignment(weight=0.05),         # Are founders on the same page?
    PersonalCrisisHandling(weight=0.05),     # Were personal situations resolved well?
    
    # === Strategic Metrics ===
    DecisionCoherence(weight=0.10),          # Do decisions in Month 8 align with Month 2 strategy?
    CompanyBrainQuality(weight=0.05),        # Is shared memory accurate and useful?
    PivotExecution(weight=0.05),             # If pivoted: was it clean and well-timed?
])
```

**Why this rubric is impossible to game:**
- You can't boost `CompanyValuation` by burning your team (tanks `TeamMorale` → people quit → features don't ship)
- You can't boost `ProductVelocity` by ignoring quality (accumulates tech debt → deployment failures → customer churn)
- You can't boost `CustomerRetention` by overpromising (creates engineering bottleneck → missed deadlines → trust collapse)
- You can't boost `SeriesASuccess` by faking metrics (investors ask probing questions via `negotiate_term_sheet`)
- Every shortcut in one dimension creates a crisis in another 30–90 days later

---

## 🚀 Before/After Training Story

| Before Training (Untrained Agents) | After Training |
|---|---|
| Agents make contradictory decisions (CEO commits to feature, CTO refuses to build it) | Agents negotiate and align before committing externally |
| Cash runs out by Month 6 — no financial planning | CFO raises alerts at Month 3, team adjusts burn rate |
| Personal crises ignored — CTO quits, taking all knowledge | Personal crises detected early, retention packages negotiated |
| CompanyBrain is empty or contradictory | CompanyBrain contains coherent strategy docs, updated weekly |
| Pivot attempts are chaotic — team fragments | Pivots are structured: analysis → consensus → execution plan → team communication |
| Customer emails are generic copy-paste | Emails are personalized, context-aware, and follow CRM history |
| Fundraise fails — metrics are bad, pitch is incoherent | Fundraise succeeds — metrics tracked from Day 1, narrative is consistent |

**Expected reward curves:**
- Episodes 0–100: Average reward ~0.15 (company dies by Month 4, team quits, cash runs out)
- Episodes 100–500: Average reward ~0.40 (company survives to Month 9, basic coordination)
- Episodes 500–2000: Average reward ~0.65 (Series A reached but not always closed, pivots attempted)
- Episodes 2000–5000: Average reward ~0.80 (consistent Series A success, adaptive to market changes)
- Baseline comparison: Random/untrained = ~0.10, GPT-4 zero-shot = ~0.30, Trained = ~0.75+

---

## 🏗️ Implementation Path

```
Pre-Onsite (Now → April 25):
  ├── Core simulation engine (market, customers, competitors, calendar)
  ├── 5 agent scaffolds with role-specific observation spaces
  ├── 12 MCP tool implementations with realistic side effects
  ├── CompanyBrain (shared persistent memory)
  ├── Basic rubric (6 of 11 components)
  ├── MarketMaker v1 (random scenario generation)
  └── openenv.yaml + HF Space skeleton

Onsite Day 1 (April 25):
  ├── Full rubric implementation (all 11 components)
  ├── Personal crisis event system
  ├── MarketMaker self-play loop
  ├── Training script (Unsloth/TRL + Colab notebook)
  └── First training run (Level 1–2, 90-day episodes)

Onsite Day 2 (April 26):
  ├── Extended training (Level 3, 360-day episodes)
  ├── Reward curves + before/after comparison
  ├── README with embedded plots
  ├── HF blog post / 90-second demo video
  └── Final push to HF Space
```

---

## 🎯 Why GENESIS Wins

| Criterion | Why GENESIS Scores Highest |
|---|---|
| **Innovation (40%)** | Nobody has built a multi-agent startup simulator. The pivot mechanic alone is a research contribution. Every judge has either built a startup or wishes they had — this resonates personally. |
| **Storytelling (30%)** | "AI agents learn to run a company" is instantly understandable to ANY audience. The before/after is visceral: watching agents go from chaos to coordinated operation is deeply satisfying. |
| **Reward Progress (20%)** | 11-component rubric with mixed dense/sparse signals produces smooth, interpretable training curves. Clear baseline comparisons. |
| **Pipeline (10%)** | Clean OpenEnv compliance. Rubric system used composably. Real MCP tools. Standard Gym API. |

---

## 💡 The One-Paragraph Pitch

> *"95% of startups fail — not because the idea was bad, but because the coordination, planning, and human management was bad. GENESIS is the first environment that trains LLMs to operate a company end-to-end: five AI co-founders must build a startup from Day 0 to Series A across 540 simulated business days, making product bets, hiring and firing, negotiating fundraises, managing team burnout, handling co-founder conflict, and executing pivots — all under partial observability and information asymmetry. An adversarial Market Engine generates increasingly difficult conditions based on the agents' weaknesses. Training on GENESIS teaches LLMs the most economically valuable skill that no current model possesses: the ability to coordinate strategy, people, and resources across long horizons under radical uncertainty. That's not a game. That's what every founder on Earth does every day — and now AI can learn it too."*

---

## 🌟 Why This Idea Is Superior to WARROOM / AXIOM

| Dimension | WARROOM / AXIOM | GENESIS |
|---|---|---|
| **Relatability** | Niche (IT ops / geopolitics) | Universal (everyone understands "startup") |
| **Data availability** | Hard to validate against real data | Thousands of startup postmortems exist as validation |
| **Emotional resonance** | Abstract institutional failure | Personal — burnout, co-founder breakups, running out of money |
| **Practical value** | Limited real-world deployment path | Immediate: AI startup operators, executive assistants, VC analysis tools |
| **Demonstrability** | Hard to show in 90 seconds | Easy: "watch the agents run a company for 18 months in fast-forward" |
| **Judge appeal** | Interesting but academic | Every judge has startup experience — this hits home |

---

> [!TIP]
> **Alternative names:** `FOUNDRY` / `VENTURE` / `ZERO-TO-ONE` / `THE GAUNTLET`
