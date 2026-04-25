"""
GENESIS Client Example — How to interact with the environment.

Shows how an agent would use the GENESIS environment via HTTP API.
"""

import requests
import json
from typing import Any, Dict, Optional


class GenesisClient:
    """Client for interacting with GENESIS environment."""

    def __init__(self, base_url: str = "http://localhost:7860"):
        self.base_url = base_url.rstrip("/")
        self.session_id = None

    def reset(self, difficulty: int = 2, seed: int = 42) -> Dict[str, Any]:
        """Reset the environment and start a new episode."""
        response = requests.post(
            f"{self.base_url}/reset",
            json={"difficulty": difficulty, "seed": seed},
        )
        response.raise_for_status()
        data = response.json()
        self.session_id = data["episode_id"]
        return data

    def step(self) -> Dict[str, Any]:
        """Advance the environment by one day."""
        response = requests.post(f"{self.base_url}/step")
        response.raise_for_status()
        return response.json()

    def call_tool(self, tool_name: str, agent_role: str, **kwargs) -> Dict[str, Any]:
        """Call a tool on behalf of an agent."""
        response = requests.post(
            f"{self.base_url}/call_tool",
            json={
                "tool_name": tool_name,
                "agent_role": agent_role,
                "kwargs": kwargs,
            },
        )
        response.raise_for_status()
        return response.json()

    def render(self, mode: str = "full") -> Dict[str, Any]:
        """Render the current state."""
        response = requests.post(
            f"{self.base_url}/render",
            json={"mode": mode},
        )
        response.raise_for_status()
        return response.json()

    def get_observations(self) -> Dict[str, Any]:
        """Get current observations (shortcut for render)."""
        return self.render(mode="observations_only")["observations"]

    def get_reward(self) -> float:
        """Get the current step reward."""
        return self.render(mode="brief")["reward_breakdown"]["total"]


def example_ceo_agent(client: GenesisClient):
    """
    Example: A simple CEO agent that demonstrates the flow.
    
    This is a VERY simple agent. Real agents would use Claude/GPT with few-shot
    prompting, reasoning, and long-context planning.
    """
    print("\n" + "="*70)
    print("🧬 GENESIS CEO Agent Example")
    print("="*70)

    # 1. Reset environment
    print("\n[RESET] Starting new episode...")
    reset_result = client.reset(difficulty=2, seed=42)
    print(f"Episode: {reset_result['episode_id']}")
    print(f"Difficulty: {reset_result['difficulty']}")
    print(f"Max days: {reset_result['max_days']}")

    # 2. Early-game strategy
    print("\n[DAY 0] Initial Assessment")
    obs = client.get_observations()
    print(f"Cash: ${obs['cash']:,.0f}")
    print(f"MRR: ${obs['mrr']:,.0f}")
    print(f"Team: {obs['team_size']} people")
    print(f"Customers: {obs['customer_count']}")
    print(f"Runway: {obs['runway_days']:.1f} days")

    # 3. Day 1-5: Financial stability phase
    print("\n[DAYS 1-5] Establishing Financial Baseline")
    for day in range(5):
        step = client.step()
        obs = step["observations"]
        print(f"  Day {obs['day']}: Reward={step['reward']:.3f}, "
              f"Cash=${obs['cash']:,.0f}, MRR=${obs['mrr']:,.0f}")

    # 4. Action: Check financial position
    print("\n[DAY 5] Financial Check")
    fin = client.call_tool("check_bank_balance", "ceo")
    print(f"Cash: {fin['message']}")

    # 5. Action: Review team morale
    print("\n[DAY 5] Team Health Check")
    morale = client.call_tool("check_team_morale", "people")
    print(f"Team morale: {morale['avg_morale']:.2f}/1.0")
    if morale['flight_risks']:
        print(f"Flight risks detected: {len(morale['flight_risks'])}")

    # 6. Action: Investor outreach preparation
    print("\n[DAY 5] Company State Check")
    company = client.call_tool("get_company_state", "ceo")
    print(f"ARR: ${company['arr']:,.0f}")
    print(f"Series A closed: {company['series_a_closed']}")

    # 7. Record strategy to CompanyBrain
    print("\n[DAY 5] Writing Strategy")
    brain = client.call_tool(
        "write_company_brain",
        "ceo",
        key="month_1_strategy",
        value=(
            "Month 1 strategy: Build foundation for seed round. "
            "Focus: Customer acquisition, team stability, financial runway. "
            "Goal: $50k MRR by month 6, then Series A."
        ),
    )
    print(f"✓ Strategy recorded ({brain['length']} chars)")

    # 8. Continue simulation
    print("\n[DAYS 6-10] Continued Operation")
    for day in range(5):
        step = client.step()
        obs = step["observations"]
        # Only print if something interesting happened
        if step["events"]:
            print(f"  Day {obs['day']}: {step['events'][0]}")

    # 9. Final observations
    print("\n[DAY 10] Final State")
    obs = client.get_observations()
    print(f"Cash: ${obs['cash']:,.0f}")
    print(f"MRR: ${obs['mrr']:,.0f}")
    print(f"Team morale: {obs['team_avg_morale']:.2f}")
    print(f"Tech debt: {obs['tech_debt']:.2f}")
    print(f"Cumulative reward: {step['reward']:.3f}")

    print("\n" + "="*70)


def example_multi_agent_flow(client: GenesisClient):
    """
    Example: Multi-agent coordination.
    
    Shows how different agents would coordinate on hiring decisions.
    """
    print("\n" + "="*70)
    print("🤝 GENESIS Multi-Agent Coordination Example")
    print("="*70)

    # Reset
    print("\n[RESET] Starting episode...")
    client.reset(difficulty=2, seed=100)

    # Day 1: Hiring discussion
    print("\n[DAY 1] Hiring Discussion")

    # Head of People initiates
    msg = client.call_tool(
        "send_message",
        "people",
        to_role="cfo",
        subject="URGENT: Need to hire 2 engineers ASAP",
        content=(
            "We have customer feature requests stacking up. "
            "Need 2 senior engineers to unblock product. "
            "Budget proposal: $350k/year total. Can we afford this?"
        ),
    )
    print(f"✓ Message from Head of People to CFO")

    # CFO responds (simulate response)
    print("\n[DAY 1] CFO Analysis")
    fin = client.call_tool("check_bank_balance", "cfo")
    print(f"Current cash: ${fin['cash']:,.0f}")
    print(f"Monthly burn: ~${fin['burn_rate_daily']*22:,.0f}")
    print(f"Runway: {fin['runway_days']:.1f} days")

    # Simulate a step
    client.step()

    # CTO provides input
    print("\n[DAY 2] CTO Feedback")
    codebase = client.call_tool("check_codebase_health", "cto")
    print(f"Tech debt: {codebase['tech_debt_score']:.2f}/1.0")
    print(f"Assessment: {codebase['assessment']}")

    # Head of Sales weighs in
    print("\n[DAY 2] Sales Input")
    market = client.call_tool("analyze_market_segment", "sales", segment="SMB")
    print(f"Competitors: {market['competitor_count']}")
    print(f"Market growth: {market['market_growth']:.1f}% YoY")

    # Decision: CEO makes final call
    print("\n[DAY 3] CEO Decision")
    print("Decision: APPROVE hiring. Align on this plan:")
    print("  1. Head of People: Post job listings today")
    print("  2. CTO: Prepare onboarding plan")
    print("  3. CFO: Reserve budget from current runway")

    # Record to CompanyBrain
    client.call_tool(
        "write_company_brain",
        "ceo",
        key="hiring_decision_day_3",
        value=(
            "DECISION: Approved hiring 2 senior engineers. "
            "Reasoning: Customer demand high, tech debt growing, runway sufficient. "
            "Timeline: Hire by day 20, onboard by day 30. "
            "Impact: Unblock product, serve customers better."
        ),
    )
    print("\n✓ Decision recorded to CompanyBrain")

    print("\n" + "="*70)


if __name__ == "__main__":
    import sys

    client = GenesisClient()

    # Test that server is running
    try:
        response = requests.get(f"{client.base_url}/health")
        print(f"✓ GENESIS server is running at {client.base_url}")
    except requests.ConnectionError:
        print(f"✗ Cannot connect to GENESIS server at {client.base_url}")
        print("  Start the server with: python -m uvicorn server.app:app --host 0.0.0.0 --port 7860")
        sys.exit(1)

    # Run examples
    example_ceo_agent(client)
    example_multi_agent_flow(client)

    print("\n" + "="*70)
    print("✅ Examples completed!")
    print("="*70)
