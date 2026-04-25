"""
GENESIS Event Engine — Drives the simulation forward each day.

Handles:
- Daily world tick (cash burn, tech debt decay, employee morale drift)
- Cascading consequences of past decisions (30-90 day lag effects)
- Random market events (competitor moves, customer churn, press coverage)
- Personal crisis injection based on difficulty and game state
- Curriculum escalation via MarketMaker adversary
"""

import random
import uuid
from .world_state import WorldState, PersonalCrisis
from .world_init import PERSONAL_CRISIS_TEMPLATES


def tick_day(state: WorldState, rng: random.Random) -> list[str]:
    """
    Advance the world by one business day. Returns list of event descriptions.
    """
    events = []
    state.day += 1

    # ── 1. Financial simulation ───────────────────────────────────────
    daily_revenue = state.mrr / 30.0
    state.cash += daily_revenue - state.burn_rate_daily
    state.cash = max(0.0, state.cash)

    # Organic MRR growth from existing customers
    for customer in state.customers:
        customer.months_active = state.day // 30
        # Happy customers expand
        if customer.satisfaction > 0.75 and rng.random() < 0.005:
            expansion = customer.arr * rng.uniform(0.05, 0.20)
            customer.arr += expansion
            state.mrr += expansion / 12
            events.append(f"📈 {customer.name} expanded contract by ${expansion:,.0f} ARR")

    # ── 2. Product progress (pending features) ────────────────────────
    still_pending = []
    for feat in state.pending_features:
        feat.days_remaining -= feat.engineers_assigned
        if feat.days_remaining <= 0:
            state.features_shipped += 1
            state.product_maturity = min(1.0, state.product_maturity + 0.03)
            state.tech_debt = min(1.0, state.tech_debt + feat.tech_debt_added)
            events.append(f"🚀 Feature '{feat.name}' shipped!")
            # Boost customer satisfaction for features they wanted
            for c in state.customers:
                if c.wants_feature and feat.name.lower() in c.wants_feature.lower():
                    c.satisfaction = min(1.0, c.satisfaction + 0.10)
                    c.churn_risk = max(0.0, c.churn_risk - 0.05)
        else:
            still_pending.append(feat)
    state.pending_features = still_pending

    # Tech debt compounds: slows delivery and increases bug rate
    if state.tech_debt > 0.6:
        state.uptime = max(0.85, state.uptime - 0.001)
        if rng.random() < 0.02:
            events.append("🔥 Production incident! High tech debt caused an outage.")
            for c in state.customers:
                c.satisfaction = max(0.0, c.satisfaction - 0.05)
                c.churn_risk = min(1.0, c.churn_risk + 0.08)

    # ── 3. Customer churn simulation ──────────────────────────────────
    churned = []
    for customer in state.customers:
        # Low satisfaction + high churn risk → churn
        churn_prob = customer.churn_risk * (1 - customer.satisfaction) * 0.05
        if rng.random() < churn_prob:
            churned.append(customer)
            state.mrr -= customer.arr / 12
            events.append(f"📉 {customer.name} churned (lost ${customer.arr/12:,.0f}/mo MRR)")
    for c in churned:
        state.customers.remove(c)
    state.mrr = max(0.0, state.mrr)

    # ── 4. Team morale drift ──────────────────────────────────────────
    for emp in state.employees:
        emp.months_employed = state.day // 30
        # Burnout increases over time
        emp.burnout_risk = min(1.0, emp.burnout_risk + 0.002)
        # Toxic employees drag morale
        if emp.is_toxic:
            for other in state.employees:
                if other.id != emp.id:
                    other.morale = max(0.0, other.morale - 0.003)
        # High burnout → morale drop
        if emp.burnout_risk > 0.7:
            emp.morale = max(0.0, emp.morale - 0.005)
            emp.flight_risk = min(1.0, emp.flight_risk + 0.01)
        # Flight risk → potential resignation
        if emp.flight_risk > 0.8 and rng.random() < 0.02:
            events.append(
                f"😢 {emp.name} ({emp.role}) resigned! High burnout/flight risk. "
                f"Knowledge loss: {'HIGH' if emp.skill_level > 0.7 else 'MEDIUM'}"
            )
            state.employees.remove(emp)
            state.burn_rate_daily -= 250  # salary savings
            break

    # Co-founder morale drift
    avg_team_morale = state.team_avg_morale()
    for role in state.cofounder_morale:
        # Co-founders feel the team's energy
        drift = (avg_team_morale - 0.5) * 0.01
        state.cofounder_morale[role] = max(0.0, min(1.0,
            state.cofounder_morale[role] + drift + rng.uniform(-0.005, 0.005)))

    # ── 5. Competitor actions ─────────────────────────────────────────
    for comp in state.competitors:
        if rng.random() < 0.015 * comp.strength:
            moves = [
                f"{comp.name} launched a new feature: bulk export",
                f"{comp.name} just announced a $5M funding round",
                f"{comp.name} cut prices by 20% — targeting your key customers",
                f"{comp.name} launched an enterprise tier directly competing with you",
                f"{comp.name} poached one of your top prospects",
            ]
            move = rng.choice(moves)
            comp.recent_move = move
            events.append(f"⚔️ Competitor move: {move}")
            # Competitor moves increase customer churn risk
            for c in state.customers:
                c.churn_risk = min(1.0, c.churn_risk + 0.03 * comp.strength)

    # ── 6. Personal crisis injection ─────────────────────────────────
    # Crises inject based on difficulty and time
    crisis_freq = {1: 45, 2: 30, 3: 21, 4: 14, 5: 7}[state.difficulty.value]
    active_crises = [c for c in state.personal_crises if not c.resolved]
    if state.day % crisis_freq == 0 and len(active_crises) < 2:
        unused = [t for t in PERSONAL_CRISIS_TEMPLATES
                  if not any(c.description == t["description"] for c in state.personal_crises)]
        if unused:
            template = rng.choice(unused)
            new_crisis = PersonalCrisis(
                id=str(uuid.uuid4()),
                target_role=template["target_role"],
                description=template["description"],
                severity=template["severity"],
            )
            state.personal_crises.append(new_crisis)
            events.append(
                f"🆘 Personal crisis for {template['target_role'].value.upper()}: "
                f"{template['description'][:80]}..."
            )

    # ── 7. Milestone checkpoints ──────────────────────────────────────
    milestones = {
        state.max_days // 6: "seed_checkpoint",
        state.max_days // 2: "pmf_checkpoint",
        state.max_days * 5 // 6: "series_a_prep",
        state.max_days - 1: "final",
    }
    if state.day in milestones:
        key = milestones[state.day]
        events.append(f"🏁 MILESTONE: {key.replace('_', ' ').title()} reached on day {state.day}")

    # ── 8. Investor sentiment drift ───────────────────────────────────
    for inv in state.investors:
        # Investors forget you if you don't update them
        if state.day % 14 == 0:
            inv.sentiment = max(0.0, inv.sentiment - 0.03)

    # ── 9. Market adversary (escalation at higher difficulties) ───────
    if state.difficulty.value >= 4 and state.day % 60 == 0:
        shock_events = [
            "💸 Funding winter hit: VCs pausing new investments for 60 days",
            "📰 Negative press cycle — enterprise buyers on hold",
            "🏦 Banking sector stress — payment processing delays for customers",
        ]
        shock = rng.choice(shock_events)
        events.append(f"🌩️ Market shock: {shock}")
        for inv in state.investors:
            inv.sentiment = max(0.0, inv.sentiment - 0.15)

    return events
