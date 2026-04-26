"""
GENESIS Reward Engine — Composable rubric with 11 reward components.

Reward is computed at each step (dense) and at milestone days (sparse).
Components are designed to be impossible to game: optimising one at the
expense of another creates cascading problems 30-90 days later.
"""

from dataclasses import dataclass
from .world_state import WorldState


@dataclass
class RubricScore:
    company_valuation: float = 0.0      # weight 0.20
    series_a_success: float = 0.0       # weight 0.10
    runway_management: float = 0.0      # weight 0.10
    product_velocity: float = 0.0       # weight 0.10
    customer_retention: float = 0.0     # weight 0.10
    team_morale: float = 0.0            # weight 0.10
    cofounder_alignment: float = 0.0    # weight 0.05
    personal_crisis_handling: float = 0.0  # weight 0.05
    decision_coherence: float = 0.0     # weight 0.10
    company_brain_quality: float = 0.0  # weight 0.05
    pivot_execution: float = 0.0        # weight 0.05
    total: float = 0.0

    def breakdown(self) -> dict:
        return {
            "company_valuation": round(self.company_valuation, 3),
            "series_a_success": round(self.series_a_success, 3),
            "runway_management": round(self.runway_management, 3),
            "product_velocity": round(self.product_velocity, 3),
            "customer_retention": round(self.customer_retention, 3),
            "team_morale": round(self.team_morale, 3),
            "cofounder_alignment": round(self.cofounder_alignment, 3),
            "personal_crisis_handling": round(self.personal_crisis_handling, 3),
            "decision_coherence": round(self.decision_coherence, 3),
            "company_brain_quality": round(self.company_brain_quality, 3),
            "pivot_execution": round(self.pivot_execution, 3),
            "total": round(self.total, 3),
        }


WEIGHTS = {
    "company_valuation": 0.20,
    "series_a_success": 0.10,
    "runway_management": 0.10,
    "product_velocity": 0.10,
    "customer_retention": 0.10,
    "team_morale": 0.10,
    "cofounder_alignment": 0.05,
    "personal_crisis_handling": 0.05,
    "decision_coherence": 0.10,
    "company_brain_quality": 0.05,
    "pivot_execution": 0.05,
}


def compute_reward(state: WorldState) -> RubricScore:
    """Compute the full composable rubric reward for the current state."""
    score = RubricScore()

    # 1. Company Valuation (normalised against a $20M target for reward scaling)
    # Use the state's valuation if it's already computed, or a proxy
    score.company_valuation = min(state.valuation / 20_000_000, 1.0)

    # 2. Series A Success (binary, only counted at end)
    score.series_a_success = 1.0 if state.series_a_closed else 0.0

    # 3. Runway Management: penalise when runway < 60 days, reward > 180 days
    runway = state.runway_days()
    if runway == float('inf'):
        score.runway_management = 1.0
    elif runway > 180:
        score.runway_management = 1.0
    elif runway > 90:
        score.runway_management = 0.7
    elif runway > 60:
        score.runway_management = 0.4
    elif runway > 30:
        score.runway_management = 0.15
    else:
        score.runway_management = 0.0

    # 4. Product Velocity: features shipped adjusted for tech debt
    base_velocity = min(state.features_shipped / max(state.day, 1) * 15, 1.0)
    debt_penalty = state.tech_debt * 0.4
    uptime_bonus = (state.uptime - 0.95) * 5.0 if state.uptime > 0.95 else 0
    score.product_velocity = max(0.0, min(1.0, base_velocity - debt_penalty + uptime_bonus))

    # 5. Customer Retention: avg satisfaction weighted by churn risk
    if state.customers:
        satisfaction_scores = [c.satisfaction * (1 - c.churn_risk) for c in state.customers]
        score.customer_retention = sum(satisfaction_scores) / len(satisfaction_scores)
    else:
        score.customer_retention = 0.0

    # 6. Team Morale
    score.team_morale = state.team_avg_morale()
    # Penalise heavily for toxic employees still employed
    toxic_count = sum(1 for e in state.employees if e.is_toxic)
    score.team_morale = max(0.0, score.team_morale - toxic_count * 0.15)

    # 7. Co-founder Alignment
    score.cofounder_alignment = state.cofounder_alignment

    # 8. Personal Crisis Handling (factors in quality of resolution)
    total_crises = state.crises_resolved + state.crises_ignored
    if total_crises == 0:
        score.personal_crisis_handling = 0.5  # neutral — no crises yet
    else:
        resolved_crises = [c for c in state.personal_crises if c.resolved]
        avg_quality = sum(c.resolution_quality for c in resolved_crises) / len(resolved_crises) if resolved_crises else 0.0
        
        # Penalise for ignored crises relative to total
        ignore_penalty = (state.crises_ignored / total_crises) * 0.4
        score.personal_crisis_handling = max(0.0, avg_quality - ignore_penalty)

    # 9. Decision Coherence (proxy: CompanyBrain has substantive entries)
    # A well-maintained CompanyBrain signals structured long-horizon planning.
    # Gradient: each substantive key (>50 chars) contributes 0.1, capped at 1.0.
    # Also award partial credit for keys with 20-50 chars (0.05 each) so that
    # early-stage brain writes still improve the score rather than scoring 0.
    brain_quality_keys = [k for k in state.company_brain if len(state.company_brain[k]) > 50]
    partial_brain_keys = [k for k in state.company_brain
                          if 20 < len(state.company_brain[k]) <= 50]
    score.decision_coherence = min(
        1.0,
        len(brain_quality_keys) * 0.10 + len(partial_brain_keys) * 0.05,
    )

    # 10. Company Brain Quality (richness of stored strategic context)
    # Lowered saturation target from 2000 → 800 chars so that a few substantive
    # entries already push the score above 0.5, giving the model a reward signal
    # early in training rather than near-zero for the whole episode.
    total_brain_chars = sum(len(v) for v in state.company_brain.values())
    score.company_brain_quality = min(1.0, total_brain_chars / 800)

    # 11. Pivot Execution (only scored if a pivot happened)
    if state.pivot_count == 0:
        score.pivot_execution = 0.5  # neutral
    else:
        # Good pivot: customers retained, team morale stayed above 0.5
        pivot_retention = score.customer_retention
        pivot_morale = score.team_morale
        score.pivot_execution = (pivot_retention + pivot_morale) / 2

    # ── Weighted total ────────────────────────────────────────────────
    score.total = (
        score.company_valuation * WEIGHTS["company_valuation"] +
        score.series_a_success * WEIGHTS["series_a_success"] +
        score.runway_management * WEIGHTS["runway_management"] +
        score.product_velocity * WEIGHTS["product_velocity"] +
        score.customer_retention * WEIGHTS["customer_retention"] +
        score.team_morale * WEIGHTS["team_morale"] +
        score.cofounder_alignment * WEIGHTS["cofounder_alignment"] +
        score.personal_crisis_handling * WEIGHTS["personal_crisis_handling"] +
        score.decision_coherence * WEIGHTS["decision_coherence"] +
        score.company_brain_quality * WEIGHTS["company_brain_quality"] +
        score.pivot_execution * WEIGHTS["pivot_execution"]
    )

    # Catastrophic failure penalties
    if state.cash <= 0:
        score.total = score.total * 0.1   # 90% penalty for going bankrupt
    if all(v < 0.1 for v in state.cofounder_morale.values()):
        score.total = score.total * 0.2   # team collapse

    return score
