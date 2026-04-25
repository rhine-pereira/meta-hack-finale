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
from .world_state import WorldState, PersonalCrisis, Employee
from .world_init import PERSONAL_CRISIS_TEMPLATES


def tick_day(state: WorldState, rng: random.Random) -> list[str]:
    """
    Advance the world by one business day. Returns list of event descriptions.
    """
    events = []
    state.day += 1

    # ── 0. Delayed hiring/recruiting and memory hygiene ───────────────
    for listing in state.open_positions:
        if listing.get("applicants_generated"):
            continue
        if state.day < listing.get("applicants_arrive_day", state.day):
            continue

        pending_count = int(listing.get("pending_applicants_count", 0))
        salary_min, salary_max = listing.get("salary_range", [90_000, 160_000])
        salary_floor = min(salary_min, salary_max)
        salary_ceiling = max(salary_min, salary_max)
        for idx in range(pending_count):
            skill = rng.uniform(0.3, 0.95)
            state.candidate_pool.append({
                "id": str(uuid.uuid4()),
                "name": f"Applicant-{listing['role'][:3]}-{state.day}-{idx + 1}",
                "role": listing["role"],
                "skill_level": round(skill, 2),
                "salary_ask": int(skill * (salary_ceiling - salary_floor) + salary_floor),
                "is_toxic": rng.random() < 0.12,
                "interview_score": round(rng.uniform(0.4, 0.95), 2),
            })
        listing["applicants_generated"] = True
        events.append(
            f"📨 Job listing for {listing['role']} produced {pending_count} new applicants after pipeline delay."
        )

    still_pending_hires = []
    for hire in state.pending_hires:
        if state.day < hire.get("start_day", state.day):
            still_pending_hires.append(hire)
            continue

        new_emp = Employee(
            id=str(uuid.uuid4()),
            name=hire["name"],
            role=hire["role"],
            skill_level=hire["skill_level"],
            morale=0.85,
            burnout_risk=0.1,
            is_toxic=hire["is_toxic"],
            annual_salary=hire["annual_salary"],
        )
        state.employees.append(new_emp)
        state.burn_rate_daily += hire["annual_salary"] / 365.0
        events.append(f"👋 {new_emp.name} joined as {new_emp.role} after onboarding delay.")

        onboard_ev = {
            "id": str(uuid.uuid4()),
            "type": "hire_onboard",
            "day": state.day,
            "desc": f"{new_emp.name} started as {new_emp.role}",
            "entity_id": new_emp.id,
        }
        state.event_history.append(onboard_ev)

    state.pending_hires = still_pending_hires

    if state.day % 7 == 0 and (state.day - state.last_weekly_memo_day) > 7:
        state.cofounder_alignment = max(0.0, state.cofounder_alignment - 0.03)
        events.append("📝 Weekly company memo missing. Alignment slipped due to stale shared context.")

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
            
            # Consequence tracking: Link ship to start
            start_ev = next((e for e in state.event_history if e.get("type") == "feature_start" and e.get("feat_name") == feat.name), None)
            ship_ev = {"id": str(uuid.uuid4()), "type": "feature_ship", "day": state.day, "desc": f"Shipped {feat.name}"}
            state.event_history.append(ship_ev)
            if start_ev:
                state.causal_links.append({"cause_id": start_ev["id"], "effect_id": ship_ev["id"], "delay": state.day - start_ev["day"]})

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
            
            # Consequence tracking: Link to recent high-debt deploy
            recent_deploys = [e for e in state.event_history if e.get("type") == "deploy" and e.get("tech_debt", 0) > 0.5]
            outage_ev = {"id": str(uuid.uuid4()), "type": "tech_debt_outage", "day": state.day, "desc": "Outage caused by tech debt"}
            state.event_history.append(outage_ev)
            if recent_deploys:
                cause = recent_deploys[-1]
                state.causal_links.append({"cause_id": cause["id"], "effect_id": outage_ev["id"], "delay": state.day - cause["day"]})
            
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
            salary_savings = emp.annual_salary / 365.0 if emp.annual_salary > 0 else 250
            state.burn_rate_daily = max(0.0, state.burn_rate_daily - salary_savings)
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
    crisis_freq = {1: 30, 2: 30, 3: 21, 4: 15, 5: 7}[state.difficulty.value]
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
                injected_day=state.day,
            )
            state.personal_crises.append(new_crisis)
            events.append(
                f"🆘 Personal crisis for {template['target_role'].value.upper()}: "
                f"{template['description'][:80]}..."
            )

    # ── 6b. Mark stale unresolved crises as ignored ──────────────────
    CRISIS_EXPIRY_DAYS = 14  # If unresolved after 14 days → ignored
    for crisis in state.personal_crises:
        if not crisis.resolved and not crisis.ignored:
            age = state.day - crisis.injected_day
            if age >= CRISIS_EXPIRY_DAYS:
                crisis.ignored = True
                state.crises_ignored += 1

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

    # ── 9. MarketMaker integration (adaptive adversary) ─────────────
    from .market_maker import MarketMaker
    mm = MarketMaker(state, rng)
    mm.observe_performance(0)  # State-based weakness detection
    mm.generate_investor_sentiment_shift()
    mm.generate_customer_demand_shift()

    # At milestones, escalate difficulty via MarketMaker
    if state.day in milestones:
        escalation = mm.escalate_difficulty()
        for shock in escalation.get("market_shocks", []):
            desc = shock.get("description", "Unknown market shift")
            events.append(f"Market shift: {desc}")
            for inv in state.investors:
                inv.sentiment = max(0.0, inv.sentiment - 0.10)
        for challenge in escalation.get("new_challenges", []):
            desc = challenge.get("description", challenge.get("type", "unknown"))
            events.append(f"New challenge: {desc}")

    # High-difficulty periodic shocks (in addition to MarketMaker)
    if state.difficulty.value >= 4 and state.day % 60 == 0:
        shock_events = [
            "Funding winter hit: VCs pausing new investments for 60 days",
            "Negative press cycle - enterprise buyers on hold",
            "Banking sector stress - payment processing delays for customers",
        ]
        shock = rng.choice(shock_events)
        events.append(f"Market shock: {shock}")
        for inv in state.investors:
            inv.sentiment = max(0.0, inv.sentiment - 0.15)

    # ── 10. Valuation drift (monthly) ─────────────────────────────────
    if state.day % 30 == 0 and state.arr() > 0:
        # Advanced valuation: ARR multiple + team/product premiums - debt penalties
        base_multiple = 7.0
        # Premiums
        if state.team_avg_morale() > 0.75: base_multiple += 2.5
        if state.product_maturity > 0.5: base_multiple += 1.5
        if state.difficulty.value >= 4: base_multiple += 1.0  # survivor premium
        # Penalties
        if state.tech_debt > 0.5: base_multiple -= 2.0
        if state.uptime < 0.98: base_multiple -= 1.0
        
        implied = state.arr() * max(3.0, base_multiple) + state.product_maturity * 2_500_000
        state.valuation = max(state.valuation, implied)

    mm.persist_weaknesses()

    # ── 11. Check Series A Closing ───────────────────────────────────
    series_a_event = _check_series_a(state)
    if series_a_event:
        events.append(series_a_event)

    return events


def _check_series_a(state: WorldState) -> str | None:
    """Evaluate whether Series A conditions are met. Returns event string or None."""
    if state.series_a_closed:
        return None
    if state.day < state.max_days // 3:
        return None

    term_sheet_investors = [i for i in state.investors if i.has_term_sheet]
    if not term_sheet_investors:
        return None

    if state.arr() < 500_000:
        return None

    if state.runway_days() < 30:
        return None

    # Pick the investor with the best term sheet
    best = max(term_sheet_investors, key=lambda i: i.term_sheet_valuation or 0)

    state.series_a_closed = True
    state.valuation = best.term_sheet_valuation or state.valuation * 3
    state.cash += best.check_size_min  # inject the funding round cash

    return (
        f"🎉 SERIES A CLOSED! {best.name} invested at "
        f"${state.valuation:,.0f} valuation. "
        f"${best.check_size_min:,.0f} added to treasury."
    )
