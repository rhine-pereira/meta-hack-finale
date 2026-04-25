#!/usr/bin/env python3
"""Quick integration test for GENESIS."""

import sys
import random
from server.world_init import initialize_world
from server.world_state import AgentRole
from server.tools import ToolHandler
from server.event_engine import tick_day
from server.reward_engine import compute_reward
from server.market_maker import MarketMaker


def test_basic_flow():
    """Test a basic flow: init → step → tool call → reward."""
    print("🧬 GENESIS Integration Test")
    print("=" * 60)

    # 1. Initialize
    print("\n1️⃣ Initializing world...")
    state = initialize_world(seed=42)
    rng = random.Random(42)
    print(f"   ✓ Episode: {state.episode_id}")
    print(f"   ✓ Cash: ${state.cash:,.0f}")
    print(f"   ✓ Team: {len(state.employees)} employees")
    print(f"   ✓ Customers: {len(state.customers)}")

    # 2. Setup tool handler
    print("\n2️⃣ Setting up tool handler...")
    handler = ToolHandler(state, rng)
    print(f"   ✓ Tools available: {len(handler._tool_list_tools(AgentRole.CEO)['available_tools'])}")

    # 3. Tool calls
    print("\n3️⃣ Testing tool calls...")
    
    # Financial check
    fin = handler.call("check_bank_balance", AgentRole.CEO, {})
    print(f"   ✓ check_bank_balance: ${fin['cash']:,.0f} cash, {fin['runway_days']:.1f} days runway")
    
    # Team morale
    morale = handler.call("check_team_morale", AgentRole.PEOPLE, {})
    print(f"   ✓ check_team_morale: {morale['avg_morale']:.2f} avg morale")
    
    # Company state
    company = handler.call("get_company_state", AgentRole.CEO, {})
    print(f"   ✓ get_company_state: ARR ${company['arr']:,.0f}")

    # 4. Event simulation
    print("\n4️⃣ Simulating 5 days...")
    for day in range(5):
        events = tick_day(state, rng)
        reward = compute_reward(state)
        print(f"   Day {state.day}: Reward={reward.total:.3f}, Cash=${state.cash:,.0f}")
        if events:
            for event in events[:2]:  # Show first 2 events
                print(f"      → {event[:70]}")

    # 5. Market maker
    print("\n5️⃣ Market adaptation...")
    market_maker = MarketMaker(state, rng)
    market_maker.observe_performance(compute_reward(state).total)
    escalation = market_maker.escalate_difficulty()
    print(f"   ✓ Escalation shocks: {len(escalation['market_shocks'])}")
    print(f"   ✓ New challenges: {len(escalation['new_challenges'])}")

    # 6. Crisis handling
    print("\n6️⃣ Testing crisis handling...")
    if state.personal_crises:
        crisis = state.personal_crises[0]
        result = handler.call(
            "handle_personal_crisis",
            crisis.target_role,
            {
                "crisis_id": crisis.id,
                "response": "Addressing the root cause",
                "resolution_quality": 0.8,
            },
        )
        print(f"   ✓ Crisis resolved: {crisis.description[:60]}...")
        print(f"     Quality: {result.get('quality', 'N/A')}")

    # 7. Final state
    print("\n7️⃣ Final state summary...")
    print(f"   ✓ Day: {state.day}")
    print(f"   ✓ Cash: ${state.cash:,.0f}")
    print(f"   ✓ MRR: ${state.mrr:,.0f}")
    print(f"   ✓ Team morale: {state.team_avg_morale():.2f}")
    print(f"   ✓ Tech debt: {state.tech_debt:.2f}")

    print("\n" + "=" * 60)
    print("✅ Integration test PASSED!")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(test_basic_flow())
    except Exception as e:
        print(f"\n❌ Integration test FAILED!")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
