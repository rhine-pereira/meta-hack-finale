"""Full validation of GENESIS components."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from server.world_state import WorldState, AgentRole, DifficultyLevel
from server.world_init import initialize_world
from server.event_engine import tick_day
from server.reward_engine import compute_reward
from server.market_maker import MarketMaker
from server.role_views import get_filtered_view, VIEW_FILTERS
import random

# Test 1: Initialize all difficulty levels
print("=== Test 1: Difficulty levels ===")
for d in DifficultyLevel:
    s = initialize_world(d, seed=42)
    print(f"  {d.name}: {s.max_days} days, {len(s.employees)} emp, {len(s.customers)} cust, {len(s.investors)} inv, {len(s.competitors)} comp, {len(s.personal_crises)} crises")

# Test 2: Run simulation 30 days
print("\n=== Test 2: 30-day simulation ===")
s = initialize_world(DifficultyLevel.SEED, 42)
rng = random.Random(42)
all_events = []
for i in range(30):
    events = tick_day(s, rng)
    all_events.extend(events)
print(f"  Day 30: cash={s.cash:.0f}, mrr={s.mrr:.0f}, shipped={s.features_shipped}, emp={len(s.employees)}, cust={len(s.customers)}")
print(f"  Total events generated: {len(all_events)}")
for e in all_events[:5]:
    print(f"    - {e}")

# Test 3: Reward engine
print("\n=== Test 3: Reward engine ===")
score = compute_reward(s)
print(f"  Total: {score.total:.3f}")
bd = score.breakdown()
for k, v in bd.items():
    print(f"    {k}: {v}")

# Test 4: MarketMaker
print("\n=== Test 4: MarketMaker ===")
mm = MarketMaker(s, rng)
mm.observe_performance(score.total)
esc = mm.escalate_difficulty()
shocks = esc["market_shocks"]
challenges = esc["new_challenges"]
print(f"  Shocks: {len(shocks)}, Challenges: {len(challenges)}")
curriculum = mm.generate_curriculum_level()
print(f"  Curriculum suggestion: {curriculum}")
scenario = mm.suggest_next_scenario()
print(f"  Next scenario: {scenario['description'][:80]}")

# Test 5: Role views for all agents
print("\n=== Test 5: Role-based observability ===")
for role in AgentRole:
    v = get_filtered_view(s, role)
    sections = [k for k, val in v.items() if val is not None]
    print(f"  {role.value}: {len(sections)} sections -> {sections}")

# Test 6: Information asymmetry checks
print("\n=== Test 6: Information asymmetry ===")
ceo_v = get_filtered_view(s, AgentRole.CEO)
cto_v = get_filtered_view(s, AgentRole.CTO)
cfo_v = get_filtered_view(s, AgentRole.CFO)
sales_v = get_filtered_view(s, AgentRole.SALES)
people_v = get_filtered_view(s, AgentRole.PEOPLE)

# CEO sees approximate tech debt
assert isinstance(ceo_v["product"]["tech_debt"], str), "CEO should see approx tech debt"
# CTO sees exact tech debt
assert isinstance(cto_v["product"]["tech_debt"], (int, float)), "CTO should see exact tech debt"
# CFO sees exact cash
assert isinstance(cfo_v["financials"]["cash"], (int, float)), "CFO should see exact cash"
# CTO sees approximate cash
assert isinstance(cto_v["financials"]["cash"], str), "CTO should see approx cash"
# Sales cannot see cash
assert sales_v["financials"]["cash"] is None, "Sales should NOT see cash"
# People cannot see financials
assert people_v["financials"] is None, "People should NOT see financials"
# Only People sees is_toxic
for emp in people_v["team"]["employees"]:
    assert "is_toxic" in emp, "People MUST see is_toxic"
for emp in ceo_v["team"]["employees"]:
    assert "is_toxic" not in emp, "CEO should NOT see is_toxic"
print("  All asymmetry checks PASSED")

# Test 7: MCP tools registered
print("\n=== Test 7: MCP tool registration ===")
from server.app import mcp
tools = list(mcp._tools.keys()) if hasattr(mcp, '_tools') else "could not enumerate"
print(f"  Tools: {tools}")

# Test 8: is_done conditions
print("\n=== Test 8: Terminal conditions ===")
s2 = initialize_world(DifficultyLevel.TUTORIAL, 42)
assert not s2.is_done(), "Fresh state should not be done"
s2.cash = 0
assert s2.is_done(), "Zero cash should be done"
s2.cash = 100000
s2.series_a_closed = True
assert s2.is_done(), "Series A closed should be done"
s2.series_a_closed = False
s2.day = s2.max_days
assert s2.is_done(), "Max days should be done"
print("  All terminal conditions PASSED")

print("\n" + "=" * 60)
print("ALL VALIDATION TESTS PASSED")
print("=" * 60)
