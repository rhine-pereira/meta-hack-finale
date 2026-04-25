# Implement GENESIS Hackathon Features

## Goal
Implement advanced simulation features: reward curves/plots, smarter crisis quality scoring, cascade consequence tracking, and complex valuation updates.

## Tasks
- [ ] Task 1: **Reward Curves & Plots** - Create `scripts/plot_rewards.py` using `matplotlib` to parse `sessions.pkl` and plot `reward_history`, comparing different episodes (e.g., early untrained vs late trained). → Verify: Running script generates a `.png` file with visible reward curves.
- [ ] Task 2: **Crisis Quality Scoring** - Update `handle_personal_crisis` in `server/app.py` to evaluate the natural language `response` (length, keyword presence, or a lightweight heuristic metric) to calculate a continuous `quality_score` (0.0 to 1.0). → Verify: Handled crisis returns varying quality scores based on response detail.
- [ ] Task 3: **Consequence Tracking** - Add `EventGraph` or `ConsequenceTracker` to `server/world_state.py` and modify `server/event_engine.py`. Link causes (e.g., "bad hire") to delayed effects (e.g., "tech debt outage 30 days later") and record them. → Verify: Simulated day logs show "Event A caused Event B" relationships.
- [ ] Task 4: **Valuation Update Logic** - Update `event_engine.py` (section 10) to compute valuation incorporating MRR growth rate, tech debt penalties, team morale premium, and MarketMaker adversary level. → Verify: Valuation fluctuates dynamically with team/product health, not just static ARR multiples.

## Done When
- [ ] Reward curves plot generated from simulation data.
- [ ] Personal crises are scored properly based on content.
- [ ] Consequences are tracked across time and logged.
- [ ] Valuation correctly factors in holistic company health.
