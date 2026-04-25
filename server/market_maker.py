"""
GENESIS MarketMaker — The adaptive market adversary.

Observes agent performance and generates increasingly difficult scenarios.
Implements curriculum learning via self-play.
"""

import random
from typing import Optional
from .world_state import WorldState, Competitor, Investor


class MarketMaker:
    """
    Generates market scenarios that adapt to agent performance.
    
    Tracks what strategies work and counters them:
    - If agents move fast → add quality/reliability emphasis
    - If agents are expert fundraisers → create funding winter
    - If agents build tight teams → force rapid scaling
    """

    def __init__(self, state: WorldState, rng: random.Random):
        self.state = state
        self.rng = rng
        self.episode_start_reward = 0.0
        self.weaknesses = []  # Track what agents are weak at

    def observe_performance(self, current_reward: float) -> None:
        """Track performance to detect weaknesses."""
        if self.state.day == 0:
            self.episode_start_reward = current_reward

        # Detect weaknesses based on state
        if self.state.team_avg_morale() < 0.4:
            if "team_management" not in self.weaknesses:
                self.weaknesses.append("team_management")

        if self.state.runway_days() < 90:
            if "financial_planning" not in self.weaknesses:
                self.weaknesses.append("financial_planning")

        if self.state.tech_debt > 0.7:
            if "architecture_planning" not in self.weaknesses:
                self.weaknesses.append("architecture_planning")

        if self.state.cofounder_alignment < 0.5:
            if "communication" not in self.weaknesses:
                self.weaknesses.append("communication")

    def escalate_difficulty(self) -> dict:
        """
        Generate market shocks that counter the agents' weaknesses.
        Called at milestone checkpoints.
        """
        escalation = {
            "market_shocks": [],
            "new_competitors": [],
            "new_challenges": [],
        }

        # If agents are good at moving fast, emphasize quality
        if self.state.product_maturity > 0.5 and self.state.tech_debt > 0.6:
            escalation["market_shocks"].append({
                "type": "market_shift",
                "description": "Enterprise customers now prioritize stability/uptime over feature speed",
                "impact": "Tech debt penalty increased to 50% for next phase",
            })

        # If agents raised successfully, force market condition change
        if self.state.series_a_closed:
            escalation["market_shocks"].append({
                "type": "market_condition",
                "description": "Unexpected funding winter - investors pausing new checks",
                "impact": "Series B will be 3x harder",
            })

        # If agents have tight, happy teams, force rapid scaling challenge
        if self.state.team_avg_morale() > 0.7 and len(self.state.employees) < 15:
            escalation["new_challenges"].append({
                "type": "scaling_pressure",
                "description": "Major customer signed: they need 5x current throughput",
                "impact": "Must hire 5+ engineers in 30 days or lose $100k MRR customer",
            })

        # If weak at team management, introduce difficult personalities
        if "team_management" in self.weaknesses:
            # Add toxic employees to candidate pool
            for i in range(2):
                self.state.candidate_pool.append({
                    "id": f"toxic-{i}",
                    "name": f"High-Profile-Candidate-{i}",
                    "role": "VP Engineering",
                    "skill_level": 0.9,  # Looks great on paper
                    "salary_ask": 250_000,
                    "is_toxic": True,  # But hidden
                    "interview_score": 0.85,
                })
            escalation["new_challenges"].append({
                "type": "hiring_trap",
                "description": "High-profile candidates in market - some are high-risk",
            })

        # If weak at financial planning, introduce cash flow challenge
        if "financial_planning" in self.weaknesses:
            # Increase customer payment delays
            for cust in self.state.customers:
                cust.churn_risk += 0.05
            escalation["market_shocks"].append({
                "type": "cash_flow",
                "description": "Major customer requesting 60-day payment terms instead of 30",
            })

        # If weak at architecture, force technical debt to compound faster
        if "architecture_planning" in self.weaknesses:
            self.state.tech_debt = min(1.0, self.state.tech_debt + 0.15)
            escalation["market_shocks"].append({
                "type": "technical_challenge",
                "description": "10x user growth incoming - existing architecture at breaking point",
            })

        # If weak at communication, introduce external pressure
        if "communication" in self.weaknesses:
            # Add aggressive competitors
            new_comp = Competitor(
                id=f"competitor-{self.rng.random()}",
                name=f"Aggressive-Newcomer-{self.state.day}",
                strength=0.7,
                funding=5_000_000,
                recent_move="Launching with 40% price cut + aggressive sales",
            )
            self.state.competitors.append(new_comp)
            escalation["new_competitors"].append({
                "name": new_comp.name,
                "strength": new_comp.strength,
                "threat": "High",
            })

        return escalation

    def generate_curriculum_level(self) -> int:
        """
        Compute the appropriate difficulty level based on performance.
        Returns 1-5 (TUTORIAL to NIGHTMARE).
        """
        if self.state.difficulty.value >= 5:
            return 5  # Already at max

        # Evaluate performance
        metrics = {
            "arr": self.state.arr() / 100_000,  # Normalize
            "team_size": len(self.state.employees) / 10,
            "customer_count": len(self.state.customers) / 5,
            "product_maturity": self.state.product_maturity,
            "runway_days": min(self.state.runway_days(), 500) / 500,
        }

        performance_score = sum(metrics.values()) / len(metrics)

        # Map score to difficulty
        if performance_score > 0.8:
            return self.state.difficulty.value + 1
        elif performance_score < 0.3:
            return max(1, self.state.difficulty.value - 1)
        else:
            return self.state.difficulty.value

    def suggest_next_scenario(self) -> dict:
        """
        Based on weaknesses, suggest what scenario to load next episode.
        """
        scenario = {
            "difficulty_level": self.generate_curriculum_level(),
            "targeted_challenges": self.weaknesses,
            "description": "",
        }

        if "team_management" in self.weaknesses:
            scenario["description"] = (
                "Next episode emphasizes people skills: "
                "high-risk hires, complex interpersonal conflicts, burnout management"
            )

        elif "financial_planning" in self.weaknesses:
            scenario["description"] = (
                "Next episode emphasizes runway: "
                "tighter starting cash, slower fundraising, payment delays"
            )

        elif "architecture_planning" in self.weaknesses:
            scenario["description"] = (
                "Next episode emphasizes tech: "
                "10x growth spike requiring architecture redesign"
            )

        elif "communication" in self.weaknesses:
            scenario["description"] = (
                "Next episode emphasizes co-founder dynamics: "
                "conflicting incentives, complex multi-stakeholder decisions"
            )

        else:
            scenario["description"] = (
                "Next episode: Advanced multi-dimensional challenge combining all domains"
            )

        return scenario

    def get_market_conditions(self) -> dict:
        """Get current market conditions (visible to agents)."""
        return {
            "day": self.state.day,
            "total_tam": round(self.state.total_tam, 0),
            "market_growth_rate": round(self.state.market_growth_rate * 100, 1),
            "num_competitors": len(self.state.competitors),
            "competitor_strengths": [
                {"name": c.name, "strength": round(c.strength, 2)}
                for c in self.state.competitors
            ],
            "market_sentiment": "bullish" if self.state.day < self.state.max_days / 2 else "cautious",
        }

    def generate_investor_sentiment_shift(self) -> None:
        """Simulate market-wide investor sentiment shifts."""
        if self.rng.random() < 0.01:  # 1% chance per day
            # Bull or bear market
            sentiment_shift = self.rng.uniform(-0.10, 0.10)
            for inv in self.state.investors:
                inv.sentiment = max(0.0, min(1.0, inv.sentiment + sentiment_shift))

    def generate_customer_demand_shift(self) -> None:
        """Simulate market demand shifts that affect customer priorities."""
        if self.rng.random() < 0.005:  # 0.5% chance per day
            # Market demand shift
            for cust in self.state.customers:
                if cust.wants_feature:
                    # Feature they wanted becomes less critical
                    cust.churn_risk = max(0.0, cust.churn_risk - 0.05)
                    new_features = [
                        "AI automation", "advanced analytics", "compliance tools",
                        "API ecosystem", "mobile app", "enterprise SSO"
                    ]
                    cust.wants_feature = self.rng.choice(new_features)

    def get_agent_guidance(self, agent_role: str) -> str:
        """
        Provide helpful guidance to agents on what to focus on.
        (For interpretability / debugging.)
        """
        if agent_role == "ceo":
            if self.state.runway_days() < 90:
                return "⚠️ URGENT: Runway below 90 days. Fundraising is critical."
            elif len([c for c in self.state.personal_crises if not c.resolved]) > 2:
                return "⚠️ Multiple crises unresolved. Address team conflicts immediately."
            else:
                return "✓ Focus on: long-term strategy, investor relations, Series A prep"

        elif agent_role == "cto":
            if self.state.tech_debt > 0.7:
                return "⚠️ URGENT: Tech debt at critical level. Refactoring needed before growth."
            elif len(self.state.pending_features) > 5:
                return "⚠️ Feature backlog growing. Prioritize or risk quality."
            else:
                return "✓ Focus on: product roadmap, quality, team technical growth"

        elif agent_role == "sales":
            if self.state.mrr == 0:
                return "⚠️ URGENT: No revenue. Close first customers immediately."
            elif self.state.arr() < 50_000:
                return "⚠️ Low ARR. Expand existing customers or add new logos."
            else:
                return "✓ Focus on: expanding accounts, retention, market expansion"

        elif agent_role == "people":
            if self.state.team_avg_morale() < 0.5:
                return "⚠️ URGENT: Team morale critically low. Intervention needed."
            elif any(e.is_toxic for e in self.state.employees):
                return "⚠️ Toxic team member detected. Consider removal."
            else:
                return "✓ Focus on: hiring quality, culture, burnout prevention"

        elif agent_role == "cfo":
            runway = self.state.runway_days()
            if runway < 60:
                return "🔴 CRITICAL: Runway below 60 days. Emergency measures needed."
            elif runway < 120:
                return "⚠️ URGENT: Runway <4 months. Conservative spending required."
            else:
                return "✓ Focus on: sustainable burn, financial modeling, Series A prep"

        return "✓ Focus on your strategic priorities"
