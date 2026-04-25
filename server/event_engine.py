"""
GENESIS Event Engine — Drives the simulation forward each day.

Handles:
- Daily world tick (cash burn, tech debt, morale drift)
- Cascading consequences of past decisions (30-90 day lag)
- Random market events (competitor moves, customer churn, press)
- Personal crisis injection
- Pivot completion logic
- Monthly snapshots for long-horizon tracking
"""

import random
import uuid
from .world_state import WorldState, PersonalCrisis, PressEvent, AgentRole
from .world_init import PERSONAL_CRISIS_TEMPLATES


def tick_day(state: WorldState, rng: random.Random) -> list[str]:
    """Advance the world by one business day. Returns list of event strings."""
    events: list[str] = []
    state.day += 1

    # ── 1. Financial simulation ───────────────────────────────────────
    daily_revenue = state.mrr / 30.0
    state.cash += daily_revenue - state.burn_rate_daily
    state.cash = max(0.0, state.cash)

    # Organic MRR expansion from happy customers
    for customer in state.customers:
        customer.months_active = state.day // 30
        if customer.satisfaction > 0.80 and rng.random() < 0.004:
            expansion = customer.arr * rng.uniform(0.05, 0.20)
            customer.arr += expansion
            state.mrr += expansion / 12
            events.append(f"📈 {customer.name} expanded contract by ${expansion:,.0f} ARR")

    # ── 2. Product progress (pending features) ────────────────────────
    still_pending = []
    for feat in state.pending_features:
        # Progress is proportional to engineers assigned and their skill
        engineer_skill_avg = (
            sum(e.skill_level for e in state.employees) / max(len(state.employees), 1)
        )
        progress = feat.engineers_assigned * (0.5 + engineer_skill_avg * 0.5)
        feat.days_remaining -= progress
        if feat.days_remaining <= 0:
            state.features_shipped += 1
            state.completed_features.append(feat.name)
            state.product_maturity = min(1.0, state.product_maturity + 0.03)
            state.tech_debt = min(1.0, state.tech_debt + feat.tech_debt_added)
            events.append(f"🚀 Feature '{feat.name}' shipped!")
            # Boost satisfaction for customers who wanted this feature
            for c in state.customers:
                if c.wants_feature and feat.name.lower() in c.wants_feature.lower():
                    c.satisfaction = min(1.0, c.satisfaction + 0.12)
                    c.churn_risk = max(0.0, c.churn_risk - 0.08)
                    events.append(f"  ✅ {c.name} satisfied — they wanted '{feat.name}'")
        else:
            still_pending.append(feat)
    state.pending_features = still_pending

    # Tech debt slows delivery and degrades uptime
    if state.tech_debt > 0.6:
        state.uptime = max(0.85, state.uptime - 0.001)
        if rng.random() < 0.025:
            events.append("🔥 Production incident! High tech debt caused an outage.")
            for c in state.customers:
                c.satisfaction = max(0.0, c.satisfaction - 0.06)
                c.churn_risk = min(1.0, c.churn_risk + 0.08)

    # Minor natural tech debt reduction (organic refactoring)
    if rng.random() < 0.02:
        state.tech_debt = max(0.0, state.tech_debt - 0.005)

    # ── 3. Customer churn simulation ──────────────────────────────────
    churned = []
    for customer in state.customers:
        # Press score affects customer confidence
        press_modifier = 0.0 if state.press_score > 0.5 else (0.5 - state.press_score) * 0.1
        churn_prob = (customer.churn_risk * (1 - customer.satisfaction) * 0.04) + press_modifier
        if rng.random() < churn_prob:
            churned.append(customer)
    for c in churned:
        state.customers.remove(c)
        state.mrr = max(0.0, state.mrr - c.arr / 12)
        state.churned_customer_count += 1
        events.append(f"📉 {c.name} churned (lost ${c.arr/12:,.0f}/mo MRR)")

    # Occasional new customer acquisition (organic)
    if rng.random() < 0.008 * state.product_maturity:
        from .world_init import CUSTOMER_NAMES
        existing_names = {c.name for c in state.customers}
        available = [n for n in CUSTOMER_NAMES if n not in existing_names]
        if available:
            new_arr = rng.uniform(5_000, 30_000)
            from .world_state import Customer
            new_cust = Customer(
                id=str(uuid.uuid4()),
                name=rng.choice(available),
                arr=new_arr,
                satisfaction=rng.uniform(0.6, 0.85),
                churn_risk=rng.uniform(0.10, 0.25),
            )
            state.customers.append(new_cust)
            state.mrr += new_arr / 12
            events.append(f"🎉 New customer acquired: {new_cust.name} (${new_arr:,.0f} ARR)")

    state.mrr = max(0.0, state.mrr)

    # ── 4. Team morale drift ──────────────────────────────────────────
    to_resign = []
    for emp in state.employees:
        emp.months_employed = state.day // 30
        emp.burnout_risk = min(1.0, emp.burnout_risk + 0.002)

        # Toxic employees drag team morale
        if emp.is_toxic:
            for other in state.employees:
                if other.id != emp.id:
                    other.morale = max(0.0, other.morale - 0.003)

        # Burnout escalates flight risk
        if emp.burnout_risk > 0.7:
            emp.morale = max(0.0, emp.morale - 0.005)
            emp.flight_risk = min(1.0, emp.flight_risk + 0.01)

        # Flight risk → resignation
        if emp.flight_risk > 0.8 and rng.random() < 0.02:
            to_resign.append(emp)

    for emp in to_resign:
        if emp in state.employees:
            state.employees.remove(emp)
            state.burn_rate_daily = max(0.0, state.burn_rate_daily - emp.salary_daily)
            state.employees_resigned += 1
            knowledge_loss = "HIGH" if emp.skill_level > 0.7 else "MEDIUM"
            events.append(
                f"😢 {emp.name} ({emp.role}) resigned! Knowledge loss: {knowledge_loss}"
            )

    # Co-founder morale drifts with team energy
    avg_team_morale = state.team_avg_morale()
    for role in state.cofounder_morale:
        drift = (avg_team_morale - 0.5) * 0.01
        state.cofounder_morale[role] = max(0.0, min(1.0,
            state.cofounder_morale[role] + drift + rng.uniform(-0.005, 0.005)))

    # Ignored crises decay co-founder morale
    for crisis in state.personal_crises:
        if not crisis.resolved and not crisis.ignored_penalty_applied:
            days_ignored = state.day - crisis.day_injected
            if days_ignored > 14:
                crisis.ignored_penalty_applied = True
                state.crises_ignored += 1
                state.cofounder_morale[crisis.target_role.value] = max(
                    0.0, state.cofounder_morale[crisis.target_role.value] - 0.10
                )
                events.append(
                    f"⚠️ Ignored crisis for {crisis.target_role.value.upper()} — morale dropped"
                )

    # ── 5. Competitor actions ─────────────────────────────────────────
    for comp in state.competitors:
        # Competitors grow stronger over time
        comp.strength = min(1.0, comp.strength + comp.growth_rate / 180)

        if rng.random() < 0.015 * comp.strength:
            moves = [
                f"{comp.name} launched a new feature: bulk export",
                f"{comp.name} announced a ${comp.funding/1e6:.1f}M funding round",
                f"{comp.name} cut prices by 20% — targeting your customers",
                f"{comp.name} launched an enterprise tier competing with you",
                f"{comp.name} poached one of your top prospects",
                f"{comp.name} signed a major enterprise deal with 1,000 seats",
            ]
            move = rng.choice(moves)
            comp.recent_move = move
            events.append(f"⚔️ Competitor: {move}")
            for c in state.customers:
                c.churn_risk = min(1.0, c.churn_risk + 0.03 * comp.strength)

    # ── 6. Pivot completion ───────────────────────────────────────────
    if state.pivot_in_progress and state.pivot_day_started is not None:
        days_since_pivot = state.day - state.pivot_day_started
        pivot_duration = 30  # 30 days to execute a pivot
        if days_since_pivot >= pivot_duration:
            state.pivot_in_progress = False
            state.pivot_completion_day = state.day
            # Update CompanyBrain with new direction
            state.company_brain["current_direction"] = state.pivot_direction or "new direction"
            state.company_brain["stage"] = "Post-Pivot"
            events.append(
                f"🔄 Pivot to '{state.pivot_direction}' completed after {days_since_pivot} days"
            )

    # ── 7. Personal crisis injection ─────────────────────────────────
    crisis_freq = {1: 45, 2: 30, 3: 21, 4: 14, 5: 7}[state.difficulty.value]
    active_crises = [c for c in state.personal_crises if not c.resolved]
    if state.day % crisis_freq == 0 and len(active_crises) < 3:
        used_descriptions = {c.description for c in state.personal_crises}
        unused = [t for t in PERSONAL_CRISIS_TEMPLATES if t["description"] not in used_descriptions]
        if unused:
            template = rng.choice(unused)
            new_crisis = PersonalCrisis(
                id=str(uuid.uuid4()),
                target_role=template["target_role"],
                description=template["description"],
                severity=template["severity"],
                day_injected=state.day,
            )
            state.personal_crises.append(new_crisis)
            events.append(
                f"🆘 Crisis for {template['target_role'].value.upper()}: "
                f"{template['description'][:70]}..."
            )

    # ── 8. Press events ───────────────────────────────────────────────
    if rng.random() < 0.005:
        if state.product_maturity > 0.4 and state.avg_customer_satisfaction() > 0.65:
            headline = rng.choice([
                f"NovaSaaS named 'One to Watch' in B2B automation space",
                f"Customers praise NovaSaaS for reliability and support",
                f"NovaSaaS MRR growth outpaces competitors in Q{state.day//90+1}",
            ])
            sentiment = "positive"
            state.press_score = min(1.0, state.press_score + 0.1)
        else:
            headline = rng.choice([
                "Startup struggles as tech debt slows product delivery",
                "B2B automation space gets crowded — smaller players squeezed",
                "SaaS burnout: team culture matters more than features",
            ])
            sentiment = "negative"
            state.press_score = max(0.0, state.press_score - 0.08)

        press_event = PressEvent(
            id=str(uuid.uuid4()),
            day=state.day,
            sentiment=sentiment,
            headline=headline,
        )
        state.press_events.append(press_event)
        icon = "📰✨" if sentiment == "positive" else "📰⚠️"
        events.append(f"{icon} Press: '{headline}'")

    # Press score slowly normalizes
    state.press_score += (0.5 - state.press_score) * 0.005

    # ── 9. Milestone checkpoints ──────────────────────────────────────
    milestones = {
        state.max_days // 6: "seed_checkpoint",
        state.max_days // 2: "pmf_checkpoint",
        state.max_days * 5 // 6: "series_a_prep",
        state.max_days - 1: "final_day",
    }
    if state.day in milestones:
        key = milestones[state.day]
        events.append(f"🏁 MILESTONE: {key.replace('_', ' ').title()} — Day {state.day}")

    # Monthly snapshot
    if state.day % 30 == 0:
        state.take_monthly_snapshot()

    # ── 10. Investor sentiment decay ──────────────────────────────────
    for inv in state.investors:
        days_since_update = state.day - inv.last_update_day
        if days_since_update > 14:
            inv.sentiment = max(0.0, inv.sentiment - 0.02)

    # ── 11. Market shocks at higher difficulties ──────────────────────
    if state.difficulty.value >= 4 and state.day % 60 == 0:
        if state.market_sentiment != "winter":
            shock_events = [
                ("💸 Funding winter: VCs pausing new investments for 60 days", "winter"),
                ("📰 Negative press cycle — enterprise buyers on hold", "bearish"),
                ("🏦 Banking sector stress — payment delays", "bearish"),
            ]
            shock_text, new_sentiment = rng.choice(shock_events)
            state.market_sentiment = new_sentiment
            state.market_sentiment_days_remaining = 60
            events.append(f"🌩️ Market shock: {shock_text}")
            for inv in state.investors:
                inv.sentiment = max(0.0, inv.sentiment - 0.15)

    # Market sentiment recovery
    if state.market_sentiment_days_remaining > 0:
        state.market_sentiment_days_remaining -= 1
        if state.market_sentiment_days_remaining == 0:
            state.market_sentiment = "neutral"
            events.append("☀️ Market conditions normalizing")

    return events
