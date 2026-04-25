"""
GENESIS Utilities — Helper functions for the simulation.

Includes: decision tracking, state serialization, formatting utilities.
"""

import json
from datetime import datetime
from typing import Any, Dict
from .world_state import WorldState, AgentRole


def format_currency(amount: float) -> str:
    """Format currency values."""
    if amount >= 1_000_000:
        return f"${amount/1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"${amount/1_000:.0f}K"
    else:
        return f"${amount:.0f}"


def format_percentage(value: float) -> str:
    """Format percentages."""
    return f"{value*100:.1f}%"


def format_time_period(days: int) -> str:
    """Format number of days as a readable period."""
    if days >= 365:
        return f"{days//365} year{'s' if days//365 > 1 else ''}"
    elif days >= 30:
        months = days // 30
        return f"{months} month{'s' if months > 1 else ''}"
    else:
        return f"{days} day{'s' if days > 1 else ''}"


def get_company_health_status(state: WorldState) -> Dict[str, Any]:
    """
    Get a health scorecard for the company.
    Useful for agents to quickly assess their position.
    """
    return {
        "stage": "💚 HEALTHY" if state.runway_days() > 180 else
                 "🟡 CAUTION" if state.runway_days() > 90 else
                 "🔴 CRITICAL" if state.runway_days() > 30 else
                 "💀 DEAD",
        "runway": format_time_period(int(state.runway_days())),
        "cash": format_currency(state.cash),
        "arr": format_currency(state.arr()),
        "burn_rate": format_currency(state.burn_rate_daily * 22),  # monthly
        "team_sentiment": "🟢 STRONG" if state.team_avg_morale() > 0.7 else
                         "🟡 OKAY" if state.team_avg_morale() > 0.5 else
                         "🔴 WEAK",
        "tech_health": "🟢 GOOD" if state.tech_debt < 0.4 else
                       "🟡 CAUTION" if state.tech_debt < 0.7 else
                       "🔴 CRITICAL",
        "customer_health": "🟢 STRONG" if state.customer_retention >= 0.75 else
                          "🟡 OKAY" if state.customer_retention >= 0.5 else
                          "🔴 AT RISK",
    }


def track_decision(
    state: WorldState,
    agent_role: AgentRole,
    decision_type: str,
    description: str,
    impact_score: float,
) -> None:
    """
    Track a decision made by an agent in CompanyBrain.
    Improves decision_coherence metric.
    
    Args:
        state: World state
        agent_role: Who made the decision
        decision_type: Category (e.g., "hiring", "product", "fundraising")
        description: What was decided
        impact_score: Expected impact (0-1)
    """
    key = f"decision_{agent_role.value}_{state.day}"
    value = json.dumps({
        "day": state.day,
        "agent": agent_role.value,
        "type": decision_type,
        "description": description,
        "impact": impact_score,
    })
    state.company_brain[key] = value


def compute_decision_coherence(state: WorldState) -> float:
    """
    Measure how coherent the team's decisions have been over time.
    
    Factors:
    - CompanyBrain entries for strategic direction (high weight)
    - Consistency of decisions across agents
    - Alignment with stated strategy
    """
    if not state.company_brain:
        return 0.0

    # Count substantive strategic entries
    strategic_keys = [
        "strategy",
        "vision",
        "product_roadmap",
        "financial_plan",
        "hiring_plan",
        "market_positioning",
    ]

    strategic_entries = sum(1 for k in strategic_keys if k in state.company_brain)
    strategic_quality = sum(
        1 for k in strategic_keys
        if k in state.company_brain and len(state.company_brain[k]) > 100
    )

    # Base score from strategic planning
    base_score = (strategic_entries * 0.1) + (strategic_quality * 0.15)

    # Bonus for maintaining consistent decisions
    decision_entries = [k for k in state.company_brain if "decision_" in k]
    decision_bonus = min(0.3, len(decision_entries) * 0.02)

    return min(1.0, base_score + decision_bonus)


def serialize_state_for_logging(state: WorldState) -> Dict[str, Any]:
    """
    Serialize world state for logging/analysis.
    Excludes objects, includes only JSON-serializable types.
    """
    return {
        "day": state.day,
        "max_days": state.max_days,
        "episode_id": state.episode_id,
        "difficulty": state.difficulty.name,
        "cash": round(state.cash, 2),
        "mrr": round(state.mrr, 2),
        "arr": round(state.arr(), 2),
        "runway_days": round(state.runway_days(), 1),
        "burn_rate_daily": round(state.burn_rate_daily, 2),
        "product_maturity": round(state.product_maturity, 2),
        "tech_debt": round(state.tech_debt, 2),
        "uptime": round(state.uptime, 3),
        "team_size": len(state.employees),
        "customer_count": len(state.customers),
        "team_avg_morale": round(state.team_avg_morale(), 2),
        "team_avg_burnout": round(state.team_avg_burnout(), 2),
        "cofounder_alignment": round(state.cofounder_alignment, 2),
        "series_a_closed": state.series_a_closed,
        "pivot_count": state.pivot_count,
        "cumulative_reward": round(state.cumulative_reward, 3),
    }


class EpisodeRecorder:
    """Records important moments in an episode for later analysis."""

    def __init__(self, episode_id: str):
        self.episode_id = episode_id
        self.events = []
        self.decisions = []
        self.rewards = []
        self.checkpoints = {}

    def record_event(self, day: int, agent_role: str, event: str):
        """Record a game event."""
        self.events.append({
            "day": day,
            "agent": agent_role,
            "event": event,
            "timestamp": datetime.now().isoformat(),
        })

    def record_decision(self, day: int, agent_role: str, decision_type: str, description: str):
        """Record an agent decision."""
        self.decisions.append({
            "day": day,
            "agent": agent_role,
            "type": decision_type,
            "description": description,
        })

    def record_reward(self, day: int, reward: float):
        """Record reward for a step."""
        self.rewards.append({"day": day, "reward": reward})

    def record_checkpoint(self, name: str, state: WorldState):
        """Record a state checkpoint (e.g., end of month, milestone)."""
        self.checkpoints[name] = serialize_state_for_logging(state)

    def to_dict(self) -> Dict[str, Any]:
        """Export as dictionary."""
        return {
            "episode_id": self.episode_id,
            "events": self.events,
            "decisions": self.decisions,
            "rewards": self.rewards,
            "checkpoints": self.checkpoints,
        }

    def to_json(self) -> str:
        """Export as JSON string."""
        return json.dumps(self.to_dict(), indent=2)


def estimate_series_a_readiness(state: WorldState) -> Dict[str, Any]:
    """
    Estimate likelihood of Series A success based on current metrics.
    Useful feedback for agents.
    """
    scores = {}

    # ARR benchmark
    target_arr = 100_000
    arr = state.arr()
    scores["arr"] = {
        "current": arr,
        "target": target_arr,
        "score": min(1.0, arr / target_arr),
        "status": "✓" if arr >= target_arr else "✗",
    }

    # Growth rate
    if state.day > 60:
        monthly_growth = (state.arr() / max(state.mrr * 3, 1)) - 1  # Very rough
        scores["growth_rate"] = {
            "monthly_growth_estimate": monthly_growth,
            "target": 0.10,  # 10% monthly
            "status": "✓" if monthly_growth > 0.10 else "✗",
        }

    # Team strength
    scores["team_quality"] = {
        "size": len(state.employees),
        "avg_skill": round(sum(e.skill_level for e in state.employees) / max(len(state.employees), 1), 2),
        "morale": round(state.team_avg_morale(), 2),
        "status": "✓" if state.team_avg_morale() > 0.6 else "⚠" if state.team_avg_morale() > 0.4 else "✗",
    }

    # Product-market fit signals
    avg_satisfaction = sum(c.satisfaction for c in state.customers) / max(len(state.customers), 1)
    scores["pmf"] = {
        "customer_satisfaction": round(avg_satisfaction, 2),
        "customer_count": len(state.customers),
        "target": 5,
        "status": "✓" if avg_satisfaction > 0.7 and len(state.customers) >= 5 else "⚠" if avg_satisfaction > 0.5 else "✗",
    }

    # Financial health
    scores["financial"] = {
        "runway_days": round(state.runway_days(), 0),
        "target": 120,
        "status": "✓" if state.runway_days() > 120 else "⚠" if state.runway_days() > 60 else "✗",
    }

    # Overall readiness
    ready_count = sum(1 for s in scores.values() if s.get("status") == "✓")
    overall_score = ready_count / len(scores)

    return {
        "scores": scores,
        "overall_readiness": {
            "score": round(overall_score, 2),
            "status": "🟢 READY" if overall_score > 0.8 else
                     "🟡 ALMOST READY" if overall_score > 0.5 else
                     "🔴 NOT READY",
        },
    }
