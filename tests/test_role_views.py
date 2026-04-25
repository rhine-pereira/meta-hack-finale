"""Tests for role-based observability filtering.

This test suite verifies that each agent role sees only the data
appropriate to their domain, creating realistic information asymmetry.
"""

import pytest
from server.world_state import WorldState, AgentRole, DifficultyLevel
from server.world_init import initialize_world
from server.role_views import (
    CEOViewFilter, CTOViewFilter, SalesViewFilter,
    PeopleViewFilter, CFOViewFilter, get_filtered_view
)


@pytest.fixture
def fresh_state():
    """Create a fresh world state for testing."""
    return initialize_world(difficulty=DifficultyLevel.SEED, seed=42)


class TestRoleFiltersExist:
    """Verify all role filters are implemented."""

    def test_all_roles_have_filters(self):
        """Each AgentRole should have a corresponding filter."""
        from server.role_views import VIEW_FILTERS

        for role in AgentRole:
            assert role in VIEW_FILTERS, f"No filter for role: {role}"
            assert VIEW_FILTERS[role] is not None


class TestCEOVisibility:
    """CEO sees strategic overview with full financials but NOT toxic flags."""

    def test_ceo_sees_full_financials(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.CEO)
        fin = view["financials"]

        assert fin is not None
        assert isinstance(fin["cash"], (int, float))
        assert isinstance(fin["burn_rate_daily"], (int, float))
        assert isinstance(fin["mrr"], (int, float))
        assert isinstance(fin["runway_days"], (int, float))
        assert isinstance(fin["valuation"], (int, float))

    def test_ceo_sees_investors_check_sizes(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.CEO)
        assert view["investors"] is not None

        # CEO sees check sizes
        inv = view["investors"]["investors"][0]
        assert "check_size_min" in inv
        assert "check_size_max" in inv

    def test_ceo_sees_approximate_sentiment(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.CEO)

        # Sentiment is approximate for CEO (string description)
        inv = view["investors"]["investors"][0]
        assert isinstance(inv["sentiment"], str)
        assert any(word in inv["sentiment"].lower() for word in ["excellent", "good", "fair", "poor", "critical"])

    def test_ceo_does_not_see_toxic_flag(self, fresh_state):
        """CEO cannot see is_toxic - only People team can."""
        view = get_filtered_view(fresh_state, AgentRole.CEO)
        team = view["team"]

        for emp in team["employees"]:
            assert "is_toxic" not in emp, "CEO should NOT see is_toxic flag"

    def test_ceo_sees_approximate_team_metrics(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.CEO)
        team = view["team"]

        # CEO sees approximate metrics for teams
        assert isinstance(team["avg_burnout"], str)


class TestCTOVisibility:
    """CTO sees deep technical details, approximate financials, no investor sentiment."""

    def test_cto_sees_exact_tech_debt(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.CTO)

        # CTO sees exact tech debt value
        assert view["product"]["tech_debt"] == fresh_state.tech_debt

    def test_cto_sees_full_employee_details(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.CTO)
        team = view["team"]

        # CTO sees exact morale, burnout, etc
        emp = team["employees"][0]
        assert isinstance(emp["morale"], (int, float))
        assert isinstance(emp["burnout_risk"], (int, float))
        assert "skill_level" in emp

    def test_cto_does_not_see_toxic_flag(self, fresh_state):
        """CTO cannot see is_toxic - only People team can."""
        view = get_filtered_view(fresh_state, AgentRole.CTO)

        for emp in view["team"]["employees"]:
            assert "is_toxic" not in emp, "CTO should NOT see is_toxic flag"

    def test_cto_sees_approximate_financials(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.CTO)
        fin = view["financials"]

        # Cash is approximate (string)
        assert isinstance(fin["cash"], str)
        assert "$" in fin["cash"]

    def test_cto_sees_no_investor_sentiment(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.CTO)
        inv = view["investors"]["investors"][0]

        # CTO sees name/thesis only
        assert "sentiment" not in inv or inv["sentiment"] is None

    def test_cto_does_not_see_valuation(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.CTO)
        assert view["financials"]["valuation"] is None


class TestSalesVisibility:
    """Sales sees customer data, competitors, revenue - no technical debt."""

    def test_sales_sees_full_customer_arr(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.SALES)
        cust = view["customers"]["customers"][0]

        # Sales sees exact ARR
        assert isinstance(cust["arr"], (int, float))

    def test_sales_sees_full_mrr(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.SALES)

        # Sales sees exact MRR
        assert view["financials"]["mrr"] == fresh_state.mrr

    def test_sales_does_not_see_cash(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.SALES)

        # Sales doesn't see cash/burn
        assert view["financials"]["cash"] is None
        assert view["financials"]["burn_rate_daily"] is None

    def test_sales_does_not_see_tech_debt(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.SALES)

        # Sales can't see tech debt
        assert view["product"] is not None
        assert view["product"]["tech_debt"] is None

    def test_sales_sees_minimal_employee_info(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.SALES)

        # Sales only sees name and role for employees
        emp = view["team"]["employees"][0]
        assert "name" in emp
        assert "role" in emp
        assert "morale" not in emp
        assert "skill_level" not in emp


class TestPeopleVisibility:
    """People team sees full HR details including toxic flags - nothing else."""

    def test_people_see_toxic_flag(self, fresh_state):
        """CRITICAL: Only People team can see is_toxic."""
        view = get_filtered_view(fresh_state, AgentRole.PEOPLE)

        emp = view["team"]["employees"][0]
        assert "is_toxic" in emp, "People team MUST see is_toxic flag"

    def test_people_see_full_team_metrics(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.PEOPLE)
        team = view["team"]

        # Exact metrics
        assert isinstance(team["avg_morale"], (int, float))
        assert isinstance(team["avg_burnout"], (int, float))

    def test_people_see_candidate_pool(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.PEOPLE)

        # People team sees candidate pool for hiring
        assert len(view["team"]["candidate_pool"]) > 0

    def test_people_do_not_see_financials(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.PEOPLE)

        # No financial data for People team
        assert view.get("financials") is None

    def test_people_do_not_see_customers(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.PEOPLE)

        # No customer data
        assert view.get("customers") is None

    def test_people_do_not_see_investors(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.PEOPLE)

        # No investor data
        assert view.get("investors") is None


class TestCFOVisibility:
    """CFO sees full financial picture, investor sentiment - limited product details."""

    def test_cfo_sees_exact_investor_sentiment(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.CFO)

        # CFO sees exact sentiment values
        inv = view["investors"]["investors"][0]
        assert isinstance(inv["sentiment"], (int, float))

    def test_cfo_sees_term_sheet_details(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.CFO)

        inv = view["investors"]["investors"][0]
        assert "term_sheet_valuation" in inv

    def test_cfo_sees_full_financials(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.CFO)
        fin = view["financials"]

        assert fin["cash"] == fresh_state.cash
        assert fin["burn_rate_daily"] == fresh_state.burn_rate_daily
        assert fin["mrr"] == fresh_state.mrr
        assert fin["runway_days"] == fresh_state.runway_days()
        assert fin["valuation"] == fresh_state.valuation
        assert fin["equity_sold"] == fresh_state.equity_sold

    def test_cfo_sees_approximate_team_metrics(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.CFO)
        team = view["team"]

        # CFO sees approximate strings for team morale
        assert isinstance(team["avg_morale"], str)

    def test_cfo_sees_limited_product_details(self, fresh_state):
        view = get_filtered_view(fresh_state, AgentRole.CFO)
        prod = view["product"]

        # Approximate tech debt
        assert isinstance(prod["tech_debt"], str)


class TestInformationAsymmetry:
    """Test that information asymmetry creates coordination challenges."""

    def test_ceo_cannot_see_exact_tech_debt(self, fresh_state):
        """CEO must ask CTO for exact tech debt status."""
        ceo_view = get_filtered_view(fresh_state, AgentRole.CEO)
        cto_view = get_filtered_view(fresh_state, AgentRole.CTO)

        # CEO sees approximate
        assert isinstance(ceo_view["product"]["tech_debt"], str)
        # CTO sees exact
        assert isinstance(cto_view["product"]["tech_debt"], (int, float))

    def test_cto_cannot_see_exact_runway(self, fresh_state):
        """CTO must trust CFO/CEO on financial runway."""
        cto_view = get_filtered_view(fresh_state, AgentRole.CTO)
        cfo_view = get_filtered_view(fresh_state, AgentRole.CFO)

        # CTO sees approximate bucket
        assert isinstance(cto_view["financials"]["runway_days"], str)
        assert "months" in cto_view["financials"]["runway_days"]
        # CFO sees exact days
        assert isinstance(cfo_view["financials"]["runway_days"], (int, float))

    def test_sales_sees_different_customer_view_than_product(self, fresh_state):
        """Sales sees full revenue; CEO sees strategic summary."""
        sales_view = get_filtered_view(fresh_state, AgentRole.SALES)
        ceo_view = get_filtered_view(fresh_state, AgentRole.CEO)

        # Sales sees satisfaction as exact
        sales_cust = sales_view["customers"]["customers"][0]
        assert "satisfaction" in sales_cust

        # CEO sees approximate
        ceo_cust = ceo_view["customers"]["customers"][0]
        assert "satisfaction_approx" in ceo_cust


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_unknown_role_raises_error(self, fresh_state):
        with pytest.raises(ValueError, match="Unknown role"):
            get_filtered_view(fresh_state, "invalid_role")

    def test_empty_state_handles_gracefully(self):
        """Test filtering works even with minimal state."""
        state = WorldState()
        view = get_filtered_view(state, AgentRole.CEO)

        assert view["role"] == "ceo"
        assert view["day"] == 0
