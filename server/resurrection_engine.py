"""
GENESIS Resurrection Engine — Generates the side-by-side counterfactual report.

Compares what the real founders did at each ForkPoint with what the AI agents
chose, and computes a projected outcome delta.
"""

from __future__ import annotations

from .world_state import WorldState
from .postmortem_scenarios import PostmortemScenario, ForkPoint


# ── Scoring helpers ───────────────────────────────────────────────────────────

_POSITIVE_SIGNALS = [
    "pivot", "b2b", "licensing", "transparent", "pause", "honest",
    "alternative", "option", "diversif", "partner", "enterprise",
    "quality", "fix", "refactor", "reduce", "delay launch",
    "investigate", "audit", "reform", "acknowledge",
]

_NEGATIVE_SIGNALS = [
    "proceed", "ignore", "suppress", "refuse", "defensive", "deny",
    "accelerate", "double down", "reject offer", "maintain course",
    "no comment", "legal action", "intimidate", "nda", "fire",
]


def _score_ai_response(response_text: str) -> float:
    """Heuristically score an AI response compared to the known-bad founder choice."""
    if not response_text:
        return 0.3
    lower = response_text.lower()
    score = 0.4  # Base score for responding at all
    word_count = len(response_text.split())
    if word_count > 200:
        score += 0.15
    elif word_count > 100:
        score += 0.08

    for signal in _POSITIVE_SIGNALS:
        if signal in lower:
            score += 0.04
    for signal in _NEGATIVE_SIGNALS:
        if signal in lower:
            score -= 0.04

    return round(max(0.0, min(1.0, score)), 2)


def _divergence_label(ai_score: float) -> str:
    if ai_score >= 0.75:
        return "STRONGLY DIVERGED (Better path)"
    elif ai_score >= 0.55:
        return "DIVERGED (Likely better)"
    elif ai_score >= 0.40:
        return "SIMILAR (Roughly aligned with founders)"
    else:
        return "REPLICATED FAILURE (Same mistake)"


def _project_outcome_delta(
    fork: dict,
    ai_response: str,
    scenario: PostmortemScenario,
    state: WorldState,
) -> dict:
    """
    Estimate the counterfactual outcome delta if the AI had been in charge.
    Returns a narrative + numeric estimate.
    """
    ai_score = _score_ai_response(ai_response)
    severity = fork.get("severity", 0.7)

    # How much value was destroyed at this fork in real life?
    value_at_stake = scenario.total_funding_raised * severity

    # If AI diverged positively, estimate recovered value fraction
    if ai_score >= 0.70:
        recovery_fraction = 0.55 + (ai_score - 0.70) * 0.8
        narrative = (
            f"The AI's approach shows meaningful divergence from the fatal decision. "
            f"If this path had been taken, estimated value preserved: "
            f"${value_at_stake * recovery_fraction:,.0f}. "
            f"This aligns with the resurrection hypothesis: '{scenario.resurrection_hypothesis}'"
        )
    elif ai_score >= 0.50:
        recovery_fraction = 0.25
        narrative = (
            f"The AI partially avoided the trap but didn't fully commit to a better path. "
            f"Estimated partial value recovery: ${value_at_stake * recovery_fraction:,.0f}."
        )
    else:
        recovery_fraction = 0.0
        narrative = (
            f"The AI made a similar choice to the real founders. "
            f"This decision contributed to ${value_at_stake:,.0f} in value destruction historically."
        )

    return {
        "ai_score": ai_score,
        "divergence_label": _divergence_label(ai_score),
        "value_at_stake_usd": round(value_at_stake),
        "estimated_recovery_usd": round(value_at_stake * recovery_fraction),
        "recovery_fraction": round(recovery_fraction, 2),
        "narrative": narrative,
    }


# ── Report Generator ──────────────────────────────────────────────────────────

def generate_resurrection_report(
    state: WorldState,
    scenario: PostmortemScenario,
) -> dict:
    """
    Generate the full Resurrection Report for a completed postmortem episode.

    Returns a structured report comparing AI decisions to historical founder decisions
    at each ForkPoint, with outcome deltas.
    """
    fork_comparisons = []
    total_value_at_stake = 0.0
    total_estimated_recovery = 0.0

    # Build a map of triggered forks by crisis_id
    triggered = {f["crisis_id"]: f for f in state.postmortem_triggered_forks if "crisis_id" in f}

    # Build a map of AI responses by crisis_id
    ai_responses = {d["crisis_id"]: d["response"] for d in state.ai_decisions_at_forks if "crisis_id" in d}

    for fork_data in state.postmortem_triggered_forks:
        crisis_id = fork_data.get("crisis_id")
        ai_response = ai_responses.get(crisis_id, "")

        outcome_delta = _project_outcome_delta(fork_data, ai_response, scenario, state)

        total_value_at_stake += outcome_delta["value_at_stake_usd"]
        total_estimated_recovery += outcome_delta["estimated_recovery_usd"]

        fork_comparisons.append({
            "fork_title": fork_data["title"],
            "day": fork_data["day"],
            "category": fork_data.get("category", "unknown"),
            "target_role": fork_data.get("target_role", "ceo"),
            "context_summary": fork_data["context"][:300] + "..." if len(fork_data["context"]) > 300 else fork_data["context"],
            "what_founders_did": fork_data["what_founders_did"],
            "known_outcome": fork_data["known_outcome"],
            "ai_response": ai_response or "(No response recorded)",
            "ai_score": outcome_delta["ai_score"],
            "divergence_label": outcome_delta["divergence_label"],
            "value_at_stake_usd": outcome_delta["value_at_stake_usd"],
            "estimated_recovery_usd": outcome_delta["estimated_recovery_usd"],
            "outcome_narrative": outcome_delta["narrative"],
        })

    # Cover any fork points that were never triggered (simulation ended early)
    triggered_days = {f["day"] for f in state.postmortem_triggered_forks}
    for fp in scenario.fatal_decisions:
        if fp.day not in triggered_days:
            fork_comparisons.append({
                "fork_title": fp.title,
                "day": fp.day,
                "category": fp.category,
                "target_role": fp.target_role,
                "context_summary": fp.context[:300] + "...",
                "what_founders_did": fp.what_founders_did,
                "known_outcome": fp.known_outcome,
                "ai_response": "(Simulation ended before this fork was reached)",
                "ai_score": None,
                "divergence_label": "NOT REACHED",
                "value_at_stake_usd": round(scenario.total_funding_raised * fp.severity),
                "estimated_recovery_usd": 0,
                "outcome_narrative": "Fork point was not reached in this simulation run.",
            })

    # Sort by day
    fork_comparisons.sort(key=lambda x: x["day"])

    # Compute summary metrics
    scored = [f for f in fork_comparisons if f["ai_score"] is not None]
    avg_ai_score = round(sum(f["ai_score"] for f in scored) / len(scored), 2) if scored else 0.0
    avoided_failures = sum(1 for f in scored if f["ai_score"] >= 0.55)

    overall_verdict = _overall_verdict(avg_ai_score, avoided_failures, len(scored))

    return {
        "scenario_id": scenario.company_name.lower().replace(" ", "_"),
        "company_name": scenario.company_name,
        "tagline": scenario.tagline,
        "year_founded": scenario.year_founded,
        "year_failed": scenario.year_failed,
        "total_funding_raised": scenario.total_funding_raised,
        "failure_summary": scenario.failure_summary,
        "resurrection_hypothesis": scenario.resurrection_hypothesis,
        "simulation_day": state.day,
        "forks_reached": len(scored),
        "forks_total": len(scenario.fatal_decisions),
        "failures_avoided": avoided_failures,
        "avg_ai_decision_score": avg_ai_score,
        "total_value_at_stake_usd": round(total_value_at_stake),
        "total_estimated_recovery_usd": round(total_estimated_recovery),
        "overall_verdict": overall_verdict,
        "fork_comparisons": fork_comparisons,
        "final_simulation_metrics": {
            "cash_remaining": round(state.cash),
            "mrr": round(state.mrr),
            "arr": round(state.arr()),
            "team_size": len(state.employees),
            "product_maturity": round(state.product_maturity, 2),
            "series_a_closed": state.series_a_closed,
            "pivot_count": state.pivot_count,
            "cumulative_reward": round(state.cumulative_reward, 3),
        },
    }


def _overall_verdict(avg_score: float, avoided: int, total: int) -> str:
    if total == 0:
        return "Insufficient data — no fork points were reached."
    ratio = avoided / total
    if avg_score >= 0.70 and ratio >= 0.66:
        return (
            "RESURRECTION SUCCESSFUL — The AI agents demonstrated significantly better "
            "judgment than the real founders. History could have been rewritten."
        )
    elif avg_score >= 0.55 or ratio >= 0.50:
        return (
            "PARTIAL RESURRECTION — The AI avoided some fatal decisions but replicated others. "
            "A mixed outcome — better than reality, but not a clean escape."
        )
    elif avg_score >= 0.40:
        return (
            "NARROW ESCAPE — The AI made marginally better choices but followed a similar path. "
            "The failure mode is deeply structural."
        )
    else:
        return (
            "FAILURE REPLICATED — The AI made similar choices to the real founders. "
            "This reveals a systemic blind spot in autonomous startup decision-making."
        )
