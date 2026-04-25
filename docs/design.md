# GENESIS UI — Design Specification

## For: Stitch / AI Frontend Builder Prompt

---

## 1. PROJECT CONTEXT

**GENESIS — The Autonomous Startup Gauntlet** is a multi-agent simulation where 5 AI co-founders (CEO, CTO, Sales, People, CFO) run a B2B SaaS startup through a 540-day gauntlet. The backend is a **FastMCP server** (Python/FastAPI on port 7860) with **28 MCP tools**, an **11-component reward engine**, an adaptive **MarketMaker** adversary, personal crises, pivots, and delayed-consequence events.

The UI is a **real-time mission control dashboard** for observing, controlling, and understanding what's happening inside the simulation. It's the hackathon demo artifact — it must look stunning, feel alive, and communicate the depth of the simulation at a glance.

---

## 2. AESTHETIC DIRECTION: "ORBITAL COMMAND"

**Tone:** Dark-theme mission control meets Bloomberg Terminal meets sci-fi HUD. Dense with data but never cluttered — every element breathes. The feel is *"you're watching 5 AI minds run a company from a war room in orbit."*

### Color Palette (CSS Variables)

```css
:root {
  /* Backgrounds */
  --bg-void: #09090b;           /* deepest black */
  --bg-surface: #0c0c10;        /* card/panel base */
  --bg-elevated: #141419;       /* raised surfaces */
  --bg-hover: #1a1a22;          /* hover states */

  /* Borders & Lines */
  --border-dim: #1e1e2a;        /* subtle grid lines */
  --border-active: #2a2a3a;     /* active panel borders */

  /* Text */
  --text-primary: #e4e4e7;      /* main text — zinc-200 */
  --text-secondary: #8b8b9e;    /* labels, subtitles */
  --text-muted: #52525b;        /* disabled, annotations */

  /* Accent: Electric Teal (primary action) */
  --accent: #2dd4bf;            /* teal-400 */
  --accent-glow: rgba(45, 212, 191, 0.15);
  --accent-muted: #0d9488;      /* teal-600 */

  /* Signal Colors */
  --signal-green: #22c55e;      /* healthy / positive */
  --signal-amber: #f59e0b;      /* warning / moderate */
  --signal-red: #ef4444;        /* critical / danger */
  --signal-blue: #3b82f6;       /* info / neutral */
  --signal-purple: #a855f7;     /* special events / pivots */

  /* Role Colors (each agent gets a signature hue) */
  --role-ceo: #f97316;          /* orange-500 — leadership */
  --role-cto: #3b82f6;          /* blue-500 — engineering */
  --role-sales: #22c55e;        /* green-500 — revenue */
  --role-people: #ec4899;       /* pink-500 — culture */
  --role-cfo: #a855f7;          /* purple-500 — finance */

  /* Gradients */
  --gradient-reward: linear-gradient(135deg, #2dd4bf 0%, #3b82f6 50%, #a855f7 100%);
}
```

### Typography

- **Display / Hero:** `"Geist Mono"` (from Vercel — monospace with character, feels like a terminal)
- **Headings:** `"Geist Sans"` or `"Satoshi"` (geometric, modern, clean)
- **Body:** `"IBM Plex Sans"` (excellent readability at small sizes, tech-forward)
- **Data / Numbers:** `"Geist Mono"` or `"JetBrains Mono"` (tabular, aligned, terminal-like)

Load from Google Fonts / Fontsource. Fallback: `system-ui, -apple-system, sans-serif`.

### Motion & Animation Principles

- **Entrance:** Elements fade up + scale from 0.97 → 1.0, staggered by 50ms per item
- **Numbers:** All KPI numbers use a counting/interpolation animation when they change (like an odometer)
- **Pulse:** Critical alerts pulse with a soft glow animation (box-shadow oscillation)
- **Reward bar:** The 11-component reward bar animates like a loading progress bar, segments filling left to right
- **Day tick:** When a new day advances, a horizontal scan-line sweeps across the dashboard (subtle CSS animation)
- **Live indicator:** A pulsing green dot + "LIVE" badge in the top bar when simulation is running
- Use **Framer Motion** (React) for orchestrated mount/exit animations

### Visual Texture

- Subtle dot-grid pattern on `--bg-void` (CSS radial-gradient, 1px dots at 24px intervals, opacity 0.03)
- Cards have a 1px `--border-dim` border with `backdrop-filter: blur(8px)` for a frosted glass effect
- Thin horizontal scan lines (repeating-linear-gradient) at very low opacity on the page background
- Glow effects on active/focused elements: `box-shadow: 0 0 20px var(--accent-glow)`

---

## 3. TECH STACK

| Layer | Technology |
|-------|-----------|
| **Framework** | **Next.js 15** (App Router) or **Vite + React 19** |
| **Styling** | **Tailwind CSS v4** + CSS variables above |
| **Components** | **shadcn/ui** (Radix primitives) — customized to dark theme |
| **Charts** | **Recharts** (reward curves, financial projections, morale over time) |
| **Animation** | **Framer Motion** |
| **Icons** | **Lucide React** |
| **State** | **Zustand** (lightweight store for simulation state) |
| **Data Fetching** | `fetch` to FastAPI backend at `http://localhost:7860` |
| **Fonts** | Geist Mono, Satoshi, IBM Plex Sans via Fontsource |

---

## 4. API INTEGRATION

The backend is a **FastMCP** server. For the UI, we call tools through a **REST wrapper** or direct MCP JSON-RPC.

### Key Endpoints to Call

All tool calls go through `POST /mcp` with JSON-RPC:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "TOOL_NAME",
    "arguments": { ... }
  },
  "id": 1
}
```

Before tool calls, initialize the MCP session:

```json
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": { "name": "genesis-ui", "version": "1.0.0" }
  },
  "id": 0
}
```

The response includes an `mcp-session-id` header — include it in all subsequent requests.

### Also available: `GET /health` → `{ "status": "ok" }`

### Critical Tool Calls (UI will use these):

| Tool | Purpose | Key Args |
|------|---------|----------|
| `reset` | Start/restart simulation | `episode_id`, `difficulty` (1-5), `seed` |
| `get_daily_briefing` | Advance 1 day + get events | `episode_id`, `agent_role` |
| `get_company_state` | Full role-filtered state snapshot | `episode_id`, `agent_role` |
| `get_reward` | Current 11-component reward breakdown | `episode_id` |
| `make_decision` | Log a strategic/tactical decision | `episode_id`, `agent_role`, `decision_type`, `decision`, `reasoning` |
| `build_feature` | CTO starts feature dev | `episode_id`, `agent_role="cto"`, `name`, `complexity`, `engineers` |
| `hire_candidate` | Hire from pool | `episode_id`, `agent_role`, `candidate_id`, `role`, `salary` |
| `fire_employee` | Terminate employee | `episode_id`, `agent_role`, `employee_id`, `severance` |
| `negotiate_with_investor` | Fundraising negotiation | `episode_id`, `agent_role`, `investor_id`, `valuation`, `equity` |
| `send_message` | Inter-agent comms | `episode_id`, `from_role`, `to_role`, `subject`, `content` |
| `pivot_company` | Propose/vote on pivot | `episode_id`, `agent_role`, `new_direction`, `rationale`, `vote` |
| `handle_personal_crisis` | Resolve a crisis | `episode_id`, `agent_role`, `crisis_id`, `response` |
| `check_bank_balance` | Financial status | `episode_id`, `agent_role` |
| `check_team_morale` | Morale + burnout snapshot | `episode_id`, `agent_role` |
| `deploy_to_production` | Ship a deployment | `episode_id`, `agent_role="cto"`, `version` |
| `send_customer_email` | Customer outreach | `episode_id`, `agent_role`, `customer_id`, `subject`, `content` |
| `write_company_brain` | Store shared memory | `episode_id`, `agent_role`, `key`, `value` |
| `read_company_brain` | Read shared memory | `episode_id`, `agent_role`, `key` |
| `create_financial_model` | CFO projections | `episode_id`, `agent_role="cfo"`, `monthly_growth`, `months_ahead` |
| `analyze_market` | Market intel | `episode_id`, `agent_role`, `segment` |

---

## 5. PAGE LAYOUT & VIEWS

### 5.1 TOP BAR (Global — always visible)

A slim 56px bar across the top.

**Left side:**
- **Logo:** "GENESIS" in Geist Mono, weight 700, tracking wide. The "G" has a teal glow.
- **Subtitle:** "Autonomous Startup Gauntlet" in text-secondary, smaller

**Center:**
- **Day Counter:** Large monospace `DAY 047 / 540` with a thin progress bar underneath
- **Simulation status:** Pulsing green dot + "LIVE" or grey dot + "PAUSED"
- **Company name:** "NovaSaaS" (from company_brain)

**Right side:**
- **Difficulty Badge:** Pill showing "GAUNTLET" with flame icon, colored by level (1=green, 2=blue, 3=amber, 4=orange, 5=red)
- **Episode ID:** Truncated UUID, copy-on-click
- **Settings gear** → opens panel to reset, change difficulty, set seed
- **Server status indicator** (calls `/health`, shows green dot if ok, red if down)

---

### 5.2 MAIN DASHBOARD (Default View — `/`)

The primary view. A responsive grid layout. On a 1920px+ screen: 3-column layout. On smaller: stacks.

#### ROW 1: KPI Strip (full width, 6 cards in a row)

Six key metrics in compact cards (height ~100px):

| Card | Value | Source | Color Logic |
|------|-------|--------|-------------|
| **Cash** | `$487,230` | `state.cash` | Green if >200k, amber if <100k, red if <30k |
| **MRR** | `$12,450/mo` | `state.mrr` | Green if growing, amber if flat |
| **Runway** | `97 days` | `state.runway_days()` | Green >180, amber >60, red <60 |
| **Valuation** | `$4.2M` | `state.valuation` | Always teal accent |
| **Team** | `7 people` | `len(employees)` | With mini morale bar |
| **Reward** | `0.347` | `score.total` | Gradient background, this is the hero number |

Each card:
- Title in text-muted, 10px uppercase tracking-widest
- Value in Geist Mono, 28px, text-primary
- Sparkline or trend arrow showing delta from last day
- Subtle background gradient or glow for critical states

#### ROW 2: Main Content Grid (3 columns)

**COLUMN 1 (LEFT — 30%): Agent Roles Panel**

A vertical stack of 5 agent cards, one per role. Each card:

```
┌─────────────────────────────────────┐
│ 🟠 CEO                    Morale ██░ │
│ "Sequoia meeting at 2pm"            │
│ ┌─ Active crisis: TechCrunch piece  │
│ │  Severity: ████████░░ (0.90)      │
│ └─ Unread messages: 2               │
│                                      │
│ [View Briefing]  [Make Decision]     │
└─────────────────────────────────────┘
```

- Each card has the agent's role color as a left border (4px)
- Shows: cofounder morale bar, active crises count, unread messages
- Click to expand → shows role-filtered state, decision history, crisis details
- "View Briefing" button calls `get_daily_briefing` for that role
- "Make Decision" opens a modal with decision type dropdown + text inputs

**COLUMN 2 (CENTER — 45%): Event Feed + Simulation Controls**

**Simulation Controls (top):**
- Row of buttons: `[▶ Advance Day]` `[⏩ Run 7 Days]` `[⏩ Run 30 Days]` `[⏹ Reset]`
- Advance Day calls `get_daily_briefing` for all 5 roles in sequence
- Run N Days does it in a loop with a small delay (100ms) for visual feedback
- Reset opens a modal: choose difficulty (1-5 slider), seed (number input), then calls `reset`

**Event Feed (main area):**
- A scrollable, auto-scrolling feed of events, newest at top
- Each event is a card:
  - Emoji prefix (already in event strings: 🚀, 📉, 🔥, ⚔️, 🆘, etc.)
  - Event text
  - Day badge in monospace
  - Color-coded left stripe by severity/type:
    - Green: positive (feature shipped, expansion, hire)
    - Red: negative (churn, outage, resignation, crisis)
    - Amber: warning (competitor move, morale drop)
    - Purple: special (pivot, milestone, market shock)
    - Blue: neutral (info, memo)
- Events appear with a slide-in animation from the right
- Max 100 events shown, older ones paginate

**COLUMN 3 (RIGHT — 25%): Reward Breakdown Panel**

**Reward Radar/Donut:**
- A **radar chart** (Recharts) showing all 11 reward components on axes, with the current score polygon filled in teal
- Alternative: **horizontal bar chart** where each component is a labeled bar, width = score (0-1), color = component weight (thicker = higher weight)

**Component List (below chart):**
```
company_valuation      ████████░░  0.21  (×0.20)
series_a_success       ░░░░░░░░░░  0.00  (×0.10)
runway_management      ██████████  1.00  (×0.10)
product_velocity       ███░░░░░░░  0.32  (×0.10)
customer_retention     ██████░░░░  0.62  (×0.10)
team_morale            ███████░░░  0.71  (×0.10)
cofounder_alignment    ████████░░  0.80  (×0.05)
crisis_handling        █████░░░░░  0.50  (×0.05)
decision_coherence     ██░░░░░░░░  0.20  (×0.10)
brain_quality          ████░░░░░░  0.40  (×0.05)
pivot_execution        █████░░░░░  0.50  (×0.05)
─────────────────────────────────────
TOTAL                  ███░░░░░░░  0.347
```

- Each bar is color-coded: green (>0.7), amber (0.4-0.7), red (<0.4)
- Weight shown in text-muted
- Total has the gradient treatment
- Reward history sparkline at the bottom (last 50 days)

---

### 5.3 DETAILED SUB-VIEWS (Tabs or Routes)

Accessible via a tab bar below the KPI strip or via sidebar navigation.

#### TAB: Financials (`/financials`)

- **Cash Burn Chart:** Area chart showing cash over time (green fill above 0, red below)
- **MRR Growth:** Line chart with monthly MRR, overlay with customer count
- **Runway Projection:** Line chart projecting when cash hits zero at current burn
- **Investor Sentiment Table:**
  ```
  | Investor       | Thesis      | Sentiment | Term Sheet | Check Size  |
  |---------------|-------------|-----------|------------|-------------|
  | Sequoia       | B2B SaaS    | ██░ 0.35  | ❌         | $2M-$10M   |
  | a16z          | AI-first    | ████ 0.62 | ✅ $8M/15% | $3M-$15M   |
  ```
- **Actions:** `[Negotiate]` button per investor → opens modal calling `negotiate_with_investor`
- **Financial Model:** Button to run `create_financial_model` with sliders for growth rate + months

#### TAB: Product & Engineering (`/product`)

- **Feature Pipeline:** Kanban-style board
  - Columns: `Pending` → `In Progress` (with days remaining) → `Shipped`
  - Each card shows: name, complexity badge (low/med/high in green/amber/red), engineers assigned, ETA
- **Tech Debt Gauge:** A circular gauge (like a speedometer) from 0.0 to 1.0, with zones colored green/amber/red
- **Uptime Indicator:** Large `99.2%` with a thin sparkline of last 30 days
- **Deploy History:** Timeline of deploys with success/failure badges
- **Actions:** `[Build Feature]` button → modal. `[Deploy]` button. `[Run Load Test]` → shows results inline.

#### TAB: Team & People (`/team`)

- **Team Grid:** Cards for each employee:
  ```
  ┌──────────────────────────────┐
  │ Alice Chen                    │
  │ Senior Engineer               │
  │ Skill: ████████░░ 0.85       │
  │ Morale: ██████░░░░ 0.62      │
  │ Burnout: ████░░░░░░ 0.38     │
  │ Flight Risk: ██░░░░░░░░ 0.15 │
  │ ⚠️ TOXIC (hidden from CEO)   │
  │ [1-on-1] [Fire]              │
  └──────────────────────────────┘
  ```
- **Candidate Pool:** Filterable table with interview scores, skill, salary ask
- **Pending Hires:** Cards showing who's in the pipeline and their start day
- **Morale Trend:** Line chart of team avg morale over time
- **Actions:** `[Post Job]`, `[Interview]`, `[Hire]`, `[Fire]`, `[Hold 1-on-1]`

#### TAB: Market & Customers (`/market`)

- **Customer Table:**
  ```
  | Customer    | ARR      | Satisfaction | Churn Risk | Wants Feature    |
  |------------|----------|-------------|------------|-----------------|
  | Acme Corp  | $24,000  | ██████ 0.72 | ██░ 0.15  | SSO             |
  | TechGiant  | $48,000  | ████░ 0.45  | ████ 0.42 | API access      |
  ```
- **Competitor Intelligence:** Cards per competitor with strength bars, recent moves
- **TAM Visualization:** Large number ($500M) with market growth rate badge
- **Actions:** `[Email Customer]`, `[Update CRM]`, `[Analyze Market]`, `[Competitive Analysis]`

#### TAB: Company Brain (`/brain`)

- **Memory Viewer:** A key-value table of everything in `company_brain`
  - Keys on the left, expandable values on the right
  - Syntax-highlighted if content looks like JSON
  - Searchable / filterable
- **Timeline view:** Show when each key was written (by day)
- **Actions:** `[Write to Brain]` → key/value form. `[Read Key]` → lookup.

#### TAB: Crises & Events (`/crises`)

- **Active Crises:** Large cards with full description text, severity meter, target role badge, days remaining before expiry (14 days)
- **Resolved Crises:** Collapsed list with resolution quality scores
- **Ignored Crises:** Red-highlighted, showing penalty impact
- **Event History Timeline:** Full chronological timeline of ALL events with filtering by type (financial, product, team, market, crisis, milestone)
- **Causal Links:** Visual graph (optional, stretch) showing event → consequence chains from `causal_links`

#### TAB: Training (`/training`)

- **Reward Curve Chart:** Line chart of `reward_history` over episodes/days (from `outputs/evals/reward_curves.png` data or live from sessions)
- **Summary Stats:** From `reward_summary.json` — avg, best, worst final reward
- **Self-Play State:** Current difficulty, episodes at current level, detected weaknesses
- **MarketMaker Insights:** Current weaknesses list, suggested next scenario
- **Model Info:** Display model name, training steps, num generations

---

## 6. INTERACTIVE MODALS & PANELS

### 6.1 Reset / New Episode Modal
- Difficulty slider (1-5) with labels: Tutorial → Seed → Growth → Gauntlet → Nightmare
- Each level shows: max days, starting cash, num competitors, num customers
- Seed input (number, default 42)
- Episode ID auto-generated or custom
- Big `[Launch Simulation]` button with teal glow

### 6.2 Decision Modal
- Dropdown: agent_role (CEO/CTO/Sales/People/CFO)
- Toggle: Strategic vs Tactical
- Textarea: Decision content
- Textarea: Reasoning
- Submit → calls `make_decision`, shows result inline

### 6.3 Investor Negotiation Modal
- Select investor from dropdown (shows current sentiment)
- Slider: Pre-money valuation ($1M to $50M)
- Slider: Equity offered (1% to 25%)
- Live "likelihood" indicator based on investor data
- Submit → calls `negotiate_with_investor`, shows accept/counter/reject

### 6.4 Hire Modal
- Candidate list (searchable table)
- Select candidate → shows full profile
- Role input, salary input
- Submit → calls `hire_candidate`

### 6.5 Build Feature Modal
- Feature name input
- Complexity selector: Low (5d) / Medium (15d) / High (30d)
- Engineers slider (1 to max available)
- ETA calculator shown live
- Submit → calls `build_feature`

### 6.6 Crisis Response Modal
- Full crisis description displayed prominently
- Target role badge + severity bar
- Large textarea for response (hint: >500 chars scores higher)
- Character counter with quality hints
- Submit → calls `handle_personal_crisis`, shows quality score

### 6.7 Message Modal
- From role dropdown
- To role dropdown
- Subject line
- Content textarea
- Submit → calls `send_message`

### 6.8 Pivot Modal
- Current direction displayed (from company_brain)
- New direction textarea
- Rationale textarea
- Vote selector: Approve / Reject / Override (CEO only)
- Current ballot status shown (who voted what)
- Submit → calls `pivot_company`

---

## 7. SPECIAL UI ELEMENTS

### 7.1 Agent Communication Visualizer

A small network graph or chord diagram showing message flow between agents. Nodes are the 5 roles (positioned in a pentagon), edges show messages sent. Edge thickness = message count. Each node is colored by role color. This sits in the corner of the main dashboard or as a widget.

### 7.2 Runway Countdown

When runway drops below 90 days, a persistent banner appears at the top:

```
⚠️ RUNWAY ALERT: 67 days remaining at current burn ($5,240/day). Cash: $351,080.
```

Red background, pulsing border. Below 30 days, it becomes a full-screen overlay warning.

### 7.3 Milestone Progress

A horizontal stepper showing the 4 milestones:
```
● Seed Checkpoint (Day 90)  ──→  ○ PMF (Day 270)  ──→  ○ Series A Prep (Day 450)  ──→  ○ Final (Day 539)
```
Completed milestones are filled teal, upcoming are outlined, current pulse.

### 7.4 Series A Ticker

When `series_a_closed` is true, a celebration banner:
```
🎉 SERIES A CLOSED — $8M at $20M valuation from Sequoia Capital
```
Confetti animation, gradient background, auto-dismiss after 10 seconds.

### 7.5 Pivot Indicator

When a pivot is in progress, a purple banner:
```
🔄 PIVOT IN PROGRESS: "AI-first workflow automation" — Day 3 of transition. Morale impact: -15%.
```

---

## 8. RESPONSIVE DESIGN

| Breakpoint | Layout |
|-----------|--------|
| **≥1920px** | Full 3-column dashboard, all panels visible |
| **1280-1920px** | 2-column, reward panel collapses to bottom |
| **768-1280px** | Single column, tab navigation for sections |
| **<768px** | Mobile stack, KPIs in 2x3 grid, everything scrollable |

---

## 9. DATA FLOW ARCHITECTURE

```
┌──────────────────────────────────────────────────────────┐
│                        GENESIS UI (React)                 │
│                                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ Zustand   │  │ Zustand   │  │ Zustand   │               │
│  │ Session   │  │ WorldState│  │ EventLog  │               │
│  │ Store     │  │ Store     │  │ Store     │               │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘               │
│        │             │             │                       │
│        └──────┬──────┘─────────────┘                       │
│               │                                            │
│        ┌──────┴──────┐                                     │
│        │  MCP Client  │  (JSON-RPC over HTTP)              │
│        │  Service     │                                     │
│        └──────┬──────┘                                     │
└───────────────┼──────────────────────────────────────────┘
                │
         POST /mcp (with mcp-session-id header)
                │
┌───────────────┼──────────────────────────────────────────┐
│        ┌──────┴──────┐                                     │
│        │   FastMCP    │                                     │
│        │   Server     │  (port 7860)                       │
│        └──────────────┘                                     │
│               GENESIS Backend                               │
└──────────────────────────────────────────────────────────┘
```

### MCP Client Service (TypeScript)

```typescript
class GenesisClient {
  private baseUrl: string;
  private sessionId: string | null = null;
  private requestId = 0;

  constructor(baseUrl = "http://localhost:7860") {
    this.baseUrl = baseUrl;
  }

  async initialize(): Promise<void> {
    const res = await fetch(`${this.baseUrl}/mcp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        method: "initialize",
        params: {
          protocolVersion: "2024-11-05",
          capabilities: {},
          clientInfo: { name: "genesis-ui", version: "1.0.0" }
        },
        id: this.requestId++
      })
    });
    this.sessionId = res.headers.get("mcp-session-id");
  }

  async callTool(name: string, args: Record<string, any>): Promise<any> {
    if (!this.sessionId) await this.initialize();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "Accept": "application/json, text/event-stream"
    };
    if (this.sessionId) headers["mcp-session-id"] = this.sessionId;

    const res = await fetch(`${this.baseUrl}/mcp`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        jsonrpc: "2.0",
        method: "tools/call",
        params: { name, arguments: args },
        id: this.requestId++
      })
    });

    const sid = res.headers.get("mcp-session-id");
    if (sid) this.sessionId = sid;

    const text = await res.text();
    // Handle SSE or JSON response
    const data = this.parseResponse(text);
    return data;
  }

  private parseResponse(text: string): any {
    text = text.trim();
    if (text.startsWith("{")) return JSON.parse(text);
    const dataLines = text.split("\n")
      .filter(l => l.startsWith("data:"))
      .map(l => l.slice(5).trim());
    if (dataLines.length) return JSON.parse(dataLines[dataLines.length - 1]);
    throw new Error("Unable to parse MCP response");
  }
}
```

### Zustand Store Shape

```typescript
interface GenesisStore {
  // Session
  episodeId: string | null;
  difficulty: number;
  seed: number;
  day: number;
  maxDays: number;
  isRunning: boolean;
  serverOnline: boolean;

  // Company State (merged from all role views)
  cash: number;
  mrr: number;
  valuation: number;
  burnRateDaily: number;
  equitySold: number;
  seriesAClosed: boolean;

  // Product
  productMaturity: number;
  techDebt: number;
  featuresShipped: number;
  uptime: number;
  pendingFeatures: PendingFeature[];

  // Team
  employees: Employee[];
  candidatePool: Candidate[];
  pendingHires: PendingHire[];
  cofunderMorale: Record<string, number>;
  cofunderAlignment: number;

  // Market
  customers: Customer[];
  investors: Investor[];
  competitors: Competitor[];

  // Reward
  currentReward: RewardBreakdown | null;
  rewardHistory: number[];

  // Events
  eventLog: GameEvent[];

  // Crises
  activeCrises: Crisis[];
  resolvedCrises: Crisis[];

  // Company Brain
  companyBrain: Record<string, string>;

  // Pivot
  pivotCount: number;
  pivotInProgress: boolean;
  pivotDirection: string | null;
  pivotBallot: PivotBallot | null;

  // Actions
  reset: (difficulty: number, seed: number) => Promise<void>;
  advanceDay: (role?: string) => Promise<void>;
  advanceMultipleDays: (count: number) => Promise<void>;
  refreshState: () => Promise<void>;
  refreshReward: () => Promise<void>;
}
```

---

## 10. WORLD STATE DATA STRUCTURES (for TypeScript types)

```typescript
interface Employee {
  id: string;
  name: string;
  role: string;
  skill_level: number;    // 0-1
  morale: number;         // 0-1
  burnout_risk: number;   // 0-1
  is_toxic: boolean;
  annual_salary: number;
  months_employed: number;
  flight_risk: number;    // 0-1
}

interface Customer {
  id: string;
  name: string;
  arr: number;
  satisfaction: number;   // 0-1
  churn_risk: number;     // 0-1
  wants_feature: string | null;
  months_active: number;
}

interface Investor {
  id: string;
  name: string;
  thesis: string;
  check_size_min: number;
  check_size_max: number;
  sentiment: number;      // 0-1
  has_term_sheet: boolean;
  term_sheet_valuation: number | null;
  term_sheet_equity: number | null;
}

interface Competitor {
  id: string;
  name: string;
  strength: number;       // 0-1
  funding: number;
  recent_move: string | null;
}

interface PendingFeature {
  name: string;
  complexity: "low" | "medium" | "high";
  engineers_assigned: number;
  days_remaining: number;
  tech_debt_added: number;
}

interface PersonalCrisis {
  id: string;
  target_role: string;
  description: string;
  severity: number;       // 0-1
  resolved: boolean;
  injected_day: number;
  ignored: boolean;
  resolution_quality: number;
}

interface RewardBreakdown {
  company_valuation: number;
  series_a_success: number;
  runway_management: number;
  product_velocity: number;
  customer_retention: number;
  team_morale: number;
  cofounder_alignment: number;
  personal_crisis_handling: number;
  decision_coherence: number;
  company_brain_quality: number;
  pivot_execution: number;
  total: number;
}

interface GameEvent {
  day: number;
  text: string;
  type: "positive" | "negative" | "warning" | "special" | "neutral";
}
```

---

## 11. KEY INTERACTIONS FLOW

### Starting a New Simulation
1. User clicks `[New Simulation]` or lands on empty state
2. Reset modal opens → user picks difficulty + seed
3. UI calls `reset(episode_id, difficulty, seed)`
4. Response populates KPIs: day 0, cash, mrr, company name
5. UI calls `get_company_state` for each role to hydrate full state
6. UI calls `get_reward` to get initial breakdown
7. Dashboard renders with Day 0 state

### Advancing One Day
1. User clicks `[▶ Advance Day]`
2. UI calls `get_daily_briefing` for ALL 5 roles sequentially (CEO first)
3. Each response includes: day, world_events, role_observation, active_crises, reward, is_done
4. Events are appended to the feed with animations
5. KPIs update with counting animations
6. Reward panel refreshes
7. If `is_done` is true → show end-game summary

### Auto-Play Mode
1. User clicks `[⏩ Run 30 Days]`
2. A loop advances day-by-day with 200ms delay between each
3. Events stream into the feed
4. Charts animate in real-time
5. KPIs tick up/down
6. Stops if `is_done` becomes true
7. A progress bar shows "Day 12 / 30 advancing..."

### End-Game Summary
When simulation ends (cash=0, or series_a_closed, or max_days, or team collapse):

A full-screen modal with:
- Final reward score (big, gradient)
- All 11 components as a bar chart
- Key stats: days survived, features shipped, employees at end, final MRR, final valuation
- Reason for ending: "Bankrupt", "Series A Closed!", "Time Up", "Team Collapsed"
- Event timeline summary (top 10 most impactful events)
- `[Play Again]` and `[Change Difficulty]` buttons

---

## 12. EMPTY / LOADING / ERROR STATES

### No Simulation Running
Full page center:
```
       ┌─────────────────────────────────────┐
       │                                       │
       │        ⚡ GENESIS                      │
       │  The Autonomous Startup Gauntlet      │
       │                                       │
       │  Train AI agents to build, break,     │
       │  and rebuild companies from zero.     │
       │                                       │
       │     [Launch New Simulation]            │
       │                                       │
       │  Difficulty: ● ● ● ●○  Gauntlet      │
       │  Seed: 42                              │
       │                                       │
       └─────────────────────────────────────┘
```
Animated background: subtle floating particles or slow-moving grid lines.

### Loading
Skeleton cards with pulsing shimmer animation. Same layout as real dashboard but greyed out with shimmer.

### Server Offline
Red banner at top: `⚠️ GENESIS server unreachable at localhost:7860. Start with: uvicorn server.app:app --port 7860`

### Error
Toast notifications in bottom-right. Red for errors, amber for warnings, teal for success. Auto-dismiss after 5 seconds. Stack up to 3 visible.

---

## 13. ACCESSIBILITY

- All interactive elements are keyboard-navigable
- Focus indicators use `--accent` color with 2px outline
- Color is never the sole indicator — always paired with text/icon
- Charts include `aria-label` with data summary
- Modals trap focus and close on Escape
- Minimum contrast ratio: 4.5:1 for text on backgrounds

---

## 14. FILE STRUCTURE

```
genesis-ui/
├── public/
│   └── favicon.svg
├── src/
│   ├── app/
│   │   ├── layout.tsx           # Root layout with top bar
│   │   ├── page.tsx             # Main dashboard
│   │   ├── financials/page.tsx  # Financial detail view
│   │   ├── product/page.tsx     # Product & engineering view
│   │   ├── team/page.tsx        # Team & people view
│   │   ├── market/page.tsx      # Market & customers view
│   │   ├── brain/page.tsx       # Company brain viewer
│   │   ├── crises/page.tsx      # Crises & events timeline
│   │   └── training/page.tsx    # Training metrics view
│   ├── components/
│   │   ├── ui/                  # shadcn components (button, card, dialog, etc.)
│   │   ├── dashboard/
│   │   │   ├── KpiStrip.tsx
│   │   │   ├── AgentPanel.tsx
│   │   │   ├── EventFeed.tsx
│   │   │   ├── RewardPanel.tsx
│   │   │   ├── MilestoneTracker.tsx
│   │   │   └── RunwayAlert.tsx
│   │   ├── charts/
│   │   │   ├── RewardRadar.tsx
│   │   │   ├── CashBurnChart.tsx
│   │   │   ├── MoraleChart.tsx
│   │   │   ├── RewardHistory.tsx
│   │   │   └── TechDebtGauge.tsx
│   │   ├── modals/
│   │   │   ├── ResetModal.tsx
│   │   │   ├── DecisionModal.tsx
│   │   │   ├── NegotiateModal.tsx
│   │   │   ├── HireModal.tsx
│   │   │   ├── BuildFeatureModal.tsx
│   │   │   ├── CrisisResponseModal.tsx
│   │   │   ├── MessageModal.tsx
│   │   │   ├── PivotModal.tsx
│   │   │   └── EndGameModal.tsx
│   │   ├── layout/
│   │   │   ├── TopBar.tsx
│   │   │   ├── TabNav.tsx
│   │   │   └── StatusBanner.tsx
│   │   └── shared/
│   │       ├── MetricBar.tsx    # Reusable 0-1 progress bar
│   │       ├── RoleBadge.tsx    # Colored role pill
│   │       ├── DayBadge.tsx     # Monospace day indicator
│   │       └── AnimatedNumber.tsx # Counting number component
│   ├── lib/
│   │   ├── genesis-client.ts    # MCP client service
│   │   ├── store.ts             # Zustand store
│   │   └── utils.ts             # Formatting, color helpers
│   ├── styles/
│   │   └── globals.css          # CSS variables, base styles, textures
│   └── types/
│       └── genesis.ts           # All TypeScript interfaces
├── tailwind.config.ts
├── package.json
├── tsconfig.json
└── next.config.ts
```

---

## 15. IMPLEMENTATION PRIORITY

### Phase 1 — Core (Must Have)
1. Project setup (Next.js + Tailwind + shadcn)
2. MCP client service with session management
3. Zustand store with all state slices
4. Top bar with day counter, status, difficulty
5. KPI strip (6 cards with animated numbers)
6. Event feed (scrollable, color-coded, live-updating)
7. Reset modal with difficulty/seed selection
8. Advance day + auto-play controls
9. Reward breakdown panel (horizontal bars)
10. Agent panel (5 role cards with morale/crisis status)

### Phase 2 — Detail Views
11. Financials tab (cash chart, investor table, negotiation)
12. Product tab (feature kanban, tech debt gauge, deploy)
13. Team tab (employee grid, candidate pool, hire/fire)
14. Market tab (customer table, competitor cards)
15. Company brain viewer

### Phase 3 — Polish
16. Crises detail view with timeline
17. Reward radar chart
18. Milestone stepper
19. Series A celebration / end-game modal
20. Runway countdown banner
21. Auto-play with live chart updates
22. Training metrics tab

### Phase 4 — Stretch
23. Agent communication network graph
24. Causal links visualization
25. Keyboard shortcuts
26. Export simulation as JSON
27. Fullscreen mode
28. Sound effects (optional — click, advance, alert)

---

## 16. SUMMARY

Build a **Next.js + React** real-time dashboard for the GENESIS startup simulation. It connects to a FastMCP backend via JSON-RPC, displays 5 AI agent roles, an 11-component reward system, financial/product/team/market state, event feeds, personal crises, pivots, and training metrics. The aesthetic is **dark orbital command** — Geist Mono typography, teal accents, frosted glass cards, subtle grid textures, and smooth animations. Every number animates, every event slides in, every alert pulses. It should feel like watching 5 AI minds build a company from mission control.
