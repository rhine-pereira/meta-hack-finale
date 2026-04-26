---
name: Frontend cleanup plan
overview: "Complete frontend cleanup: remove all mock/hardcoded data, wire up dead buttons to existing server MCP tools, and strip cosmetic-only UI elements. No server changes needed -- all required APIs already exist."
todos:
  - id: crises-cleanup
    content: "Clean up /crises: remove mock KPIs (System Load, Response T, Stability), remove Resolution Efficiency sidebar, replace Recently Mitigated with real resolved crises, remove dead Override All and Delegate Role buttons, fix EmergencyIcon bug"
    status: pending
  - id: product-cleanup
    content: "Clean up /product: remove fake shipped feature names, remove hardcoded deploy history, wire Run Load Test to run_load_test tool, wire Deploy button to deploy_to_production tool"
    status: pending
  - id: market-cleanup
    content: "Clean up /market: replace hardcoded TAM/growth with server data from analyze_market, remove mock Market Penetration and Churn Velocity, wire Email Customer to send_customer_email tool, remove or wire customer action buttons"
    status: pending
  - id: team-cleanup
    content: "Clean up /team: remove hardcoded Org Morale Trend chart, wire Post Job to post_job_listing tool, wire employee Briefcase to hold_one_on_one tool, wire employee UserX to fire_employee tool"
    status: pending
  - id: financials-cleanup
    content: "Clean up /financials: remove both hardcoded charts (AreaChart + LineChart) and recharts, wire Recalculate Model to create_financial_model tool, fix Negotiate button crash (undefined valuation), remove duplicate Activity SVG"
    status: pending
  - id: brain-cleanup
    content: "Clean up /brain: replace mock KPIs (Sync Status, Access Control) with real data or remove"
    status: pending
  - id: benchmark-cleanup
    content: "Clean up /benchmark: replace mock KPIs with real counts from list_founder_genomes, remove hardcoded Model Distribution bar"
    status: pending
  - id: training-cleanup
    content: "Clean up /training: remove all fake metrics (epsilon, Training Protocol, Convergence Velocity), remove dead Export Model and Pause Inference buttons, keep only reward chart + completed models"
    status: pending
  - id: sidebar-cleanup
    content: Remove EMERGENCY OVERRIDE button from Sidebar
    status: pending
isProject: false
---

# Frontend Cleanup Plan

## Current State

The frontend has 11 pages. Every page uses [`frontend/src/lib/genesis-client.ts`](frontend/src/lib/genesis-client.ts) via a Zustand store ([`frontend/src/lib/store.ts`](frontend/src/lib/store.ts)) to call MCP tools on the server. The plumbing works, but many pages have:
- Hardcoded/mock data displayed alongside real server data
- Buttons that aren't wired to any server call
- Cosmetic KPIs with invented values

**Server changes: NONE needed.** Every button we need to wire up has a corresponding MCP tool already.

---

## Page-by-Page Changes

### 1. `/` Dashboard ([`frontend/src/app/page.tsx`](frontend/src/app/page.tsx))
- **Status**: Works. No mock data. No changes needed.

### 2. `/demo` Live Demo ([`frontend/src/app/demo/page.tsx`](frontend/src/app/demo/page.tsx))
- **Status**: Works. Fetches from `/demo/state` and `/demo/events` SSE. No changes needed.

### 3. `/crises` Incident Control ([`frontend/src/app/crises/page.tsx`](frontend/src/app/crises/page.tsx))
- **Remove mock data**:
  - KPIs "System Load: 92%", "Response T: 4.2h", "Stability: 84%" -- replace with real counts from store (e.g. total crises count, resolved count, active count) or remove
  - "Resolution Efficiency" sidebar (hardcoded bars: 45, 12, 89) -- remove entirely
  - "Recently Mitigated" sidebar (hardcoded fake items: "Supply Chain Disruption", "Compliance Audit Flag", etc.) -- replace with actual `resolvedCrises` from the store
- **Wire up buttons**:
  - "Override All" button -- remove (no meaningful server action)
  - "Delegate Role" button -- remove (the Ghost Founder console already handles this)
- **Bug fix**: `EmergencyIcon` import doesn't exist in lucide-react; fix the local `Emergency` SVG component usage

### 4. `/product` Product Matrix ([`frontend/src/app/product/page.tsx`](frontend/src/app/product/page.tsx))
- **Remove mock data**:
  - "Shipped" column generates fake `Feature ${featuresShipped - i}` entries -- show just the count or remove the column
  - "Deploy History" section (hardcoded "v2.0.4 - System Stability Patch", "v2.0.3 - Auth Layer Rollout") -- remove or replace with event history from store
- **Wire up buttons**:
  - "Run Load Test" button -- wire to `run_load_test` MCP tool, show result in a toast/modal
  - "Deploy" button -- wire to `deploy_to_production` MCP tool, show success/failure result

### 5. `/market` Market Intel ([`frontend/src/app/market/page.tsx`](frontend/src/app/market/page.tsx))
- **Remove mock data**:
  - TAM "$500M" -- replace with value from `analyze_market` response (the tool returns `state.total_tam`)
  - "+14.2% YoY Growth" -- replace with `state.market_growth_rate` from server
  - "Market Penetration: 7.8%" and "Avg Churn Velocity: 1.2% / mo" -- remove (no server source)
- **Wire up buttons**:
  - "Email Customer" button -- wire to `send_customer_email` MCP tool via a prompt dialog for subject/content
  - Customer row action buttons (ArrowUpRight) -- either wire to CRM update or remove
- **Approach**: Call `analyze_market` on page load (or on button click) and store TAM/growth in local state for display

### 6. `/team` Founders & Team ([`frontend/src/app/team/page.tsx`](frontend/src/app/team/page.tsx))
- **Remove mock data**:
  - "Org Morale Trend" chart with hardcoded bars [40, 45, 38, 52, 48, 60, 55, 42] and "-2.4%" -- remove the chart entirely (no historical morale data on server)
- **Wire up buttons**:
  - "Post Job" button -- wire to `post_job_listing` MCP tool via a dialog for role/requirements/salary range
  - Employee Briefcase icon button -- wire to `hold_one_on_one` MCP tool
  - Employee UserX (fire) icon button -- wire to `fire_employee` MCP tool with confirmation

### 7. `/financials` Financial Command ([`frontend/src/app/financials/page.tsx`](frontend/src/app/financials/page.tsx))
- **Remove mock data**:
  - Remove both charts entirely (AreaChart for cash, LineChart for MRR) -- the hardcoded `chartData` array has no server backing. Just keep the KPI cards.
  - Remove recharts imports
- **Wire up buttons**:
  - "Recalculate Model" button -- wire to `create_financial_model` MCP tool, show projections in a result panel
  - "Negotiate" button on investors -- **fix crash**: currently references undefined `valuation` variable. Wire up properly using store's `valuation` value via `negotiateWithInvestor`.
- **Bug fix**: The `Activity` component at the bottom shadows the lucide-react import; remove the duplicate SVG

### 8. `/brain` Cognitive Core ([`frontend/src/app/brain/page.tsx`](frontend/src/app/brain/page.tsx))
- **Remove mock data**:
  - KPIs "Sync Status: OPTIMAL" and "Access Control: L5-BIO" -- replace with real values (e.g. "Total Keys" count is real, "Storage Used" is real, replace the other two with something useful or remove)
- **Status**: Otherwise works well. Inject Memory button calls server.

### 9. `/benchmark` Benchmarks ([`frontend/src/app/benchmark/page.tsx`](frontend/src/app/benchmark/page.tsx))
- **Remove mock data**:
  - KPIs "256 Aggregate Episodes", "12 Active Models", "GAUNTLET" -- fetch real counts from `list_founder_genomes` and store
  - "Benchmark Methodology" text block with hardcoded percentages -- remove or simplify to static explainer
  - "Model Distribution" bar (45% Claude, 30% GPT, 25% Gemini) -- remove
- **Approach**: Fetch `list_founder_genomes` on load, derive episode/model counts from available data

### 10. `/postmortem` Resurrection Engine ([`frontend/src/app/postmortem/page.tsx`](frontend/src/app/postmortem/page.tsx))
- **Status**: Works well. All data fetched from server. No mock data. No changes needed.

### 11. `/training` Training ([`frontend/src/app/training/page.tsx`](frontend/src/app/training/page.tsx))
- **Remove mock data**:
  - "Exploration epsilon: 0.05" KPI -- remove
  - "Training Protocol" section (hardcoded GRPO, observation space, learning rate) -- remove entirely
  - "Convergence Velocity: 58% STABLE" -- remove
  - "Pause Inference" button -- remove (no server action)
  - "Export Model" button -- remove (no server action for model export)
- **Keep**: Reward history chart (real data from store), Completed Founders list (fetched from server), Current Reward / Steps KPIs

### 12. Sidebar ([`frontend/src/components/layout/Sidebar.tsx`](frontend/src/components/layout/Sidebar.tsx))
- **Remove**: "EMERGENCY OVERRIDE" button at the bottom -- does nothing, no server action
- **Keep**: Founder Morale indicators (data from store, which comes from server)

---

## Summary of Work

| Category | Count |
|----------|-------|
| Pages with no changes | 3 (`/`, `/demo`, `/postmortem`) |
| Pages with mock data removal | 8 |
| Dead buttons to wire up | ~10 (across 4 pages) |
| Dead buttons to remove | ~6 (no useful server mapping) |
| Bug fixes | 2 (`/crises` EmergencyIcon, `/financials` undefined `valuation`) |
| Server changes needed | 0 |
