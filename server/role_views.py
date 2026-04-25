"""GENESIS Role-Based Observability — Filters world state per agent role.

Each agent role (CEO, CTO, SALES, PEOPLE, CFO) sees a different slice of the world state.
This creates realistic information asymmetry where co-founders must communicate
to get a complete picture of the company.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from enum import Enum

from .world_state import WorldState, AgentRole, Employee, Customer


class VisibilityLevel(str, Enum):
    """Visibility levels for data fields."""
    FULL = "full"          # Exact values
    APPROXIMATE = "approx" # Ranges, quartiles, or coarse buckets
    HIDDEN = "hidden"      # Not visible at all


@dataclass
class FinancialSummary:
    """Financial data visibility varies by role."""
    cash: Any  # float for CEO/CFO, str range for others, or None
    burn_rate_daily: Any
    mrr: Any
    arr: Any
    runway_days: Any
    valuation: Any
    equity_sold: Any


@dataclass
class ProductSummary:
    """Product data with role-appropriate detail."""
    product_maturity: Any  # float or approximate
    tech_debt: Any         # float for CTO, approximate for CEO, hidden for others
    uptime: Any
    features_shipped: int
    pending_features: list  # Full for CTO/CEO, limited for others


@dataclass
class TeamSummary:
    """Team data with sensitive fields filtered per role."""
    employee_count: int
    employees: list  # Employee dicts with role-appropriate fields
    open_positions: list
    candidate_pool: list
    avg_morale: Any  # float or approximate
    avg_burnout: Any
    cofounder_morale: dict


@dataclass
class CustomerSummary:
    """Customer data visibility."""
    customers: list
    total_customers: int
    total_arr: Any  # float or approximate


@dataclass
class InvestorSummary:
    """Investor data with varying sentiment visibility."""
    investors: list
    total_investors: int


@dataclass
class CompetitorSummary:
    """Competitor data - limited for most roles."""
    competitors: list
    total_competitors: int


@dataclass
class RoleFilteredView:
    """Base filtered view - all roles see this common structure."""
    role: str
    day: int
    episode_id: str
    company_name: str
    company_stage: str
    difficulty: str
    max_days: int

    # Each role gets their own slice
    financials: Optional[FinancialSummary] = None
    product: Optional[ProductSummary] = None
    team: Optional[TeamSummary] = None
    customers: Optional[CustomerSummary] = None
    investors: Optional[InvestorSummary] = None
    competitors: Optional[CompetitorSummary] = None

    # Messages for this role
    messages: list = field(default_factory=list)

    # Personal crises targeting this role
    active_personal_crises: list = field(default_factory=list)

    # Company brain - filtered by role domain
    company_brain: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dict for MCP response."""
        return asdict(self)


class RoleViewFilter:
    """Base class for role-specific state filtering."""

    def filter(self, state: WorldState, role: AgentRole) -> RoleFilteredView:
        """Filter world state for the given role."""
        raise NotImplementedError

    @staticmethod
    def _approximate_cash(cash: float) -> str:
        """Convert exact cash to approximate range."""
        if cash >= 1_000_000:
            return f"${cash / 1_000_000:.1f}M+"
        elif cash >= 500_000:
            return "$500K-$1M"
        elif cash >= 250_000:
            return "$250K-$500K"
        elif cash >= 100_000:
            return "$100K-$250K"
        elif cash >= 50_000:
            return "$50K-$100K"
        else:
            return f"<${cash / 1000:.0f}K"

    @staticmethod
    def _approximate_runway(days: float) -> str:
        """Convert exact runway to approximate bucket."""
        if days == float('inf'):
            return "profitable"
        if days >= 365:
            return "12+ months"
        elif days >= 180:
            return "6-12 months"
        elif days >= 90:
            return "3-6 months"
        elif days >= 60:
            return "2-3 months"
        elif days >= 30:
            return "1-2 months"
        else:
            return "<30 days CRITICAL"

    @staticmethod
    def _approximate_metric(value: float) -> str:
        """Convert 0-1 metric to quartile string."""
        if value >= 0.8:
            return "excellent (top 25%)"
        elif value >= 0.6:
            return "good (above average)"
        elif value >= 0.4:
            return "fair (average)"
        elif value >= 0.2:
            return "poor (below average)"
        else:
            return "critical (bottom 25%)"

    @staticmethod
    def _filter_employee_for_role(emp: Employee, role: AgentRole) -> dict:
        """Filter employee data based on viewer role."""
        base = {
            "id": emp.id,
            "name": emp.name,
            "role": emp.role,
            "months_employed": emp.months_employed,
        }

        if role == AgentRole.CTO:
            # CTO sees full technical/team details
            base.update({
                "skill_level": emp.skill_level,
                "morale": emp.morale,
                "burnout_risk": emp.burnout_risk,
                "flight_risk": emp.flight_risk,
            })
        elif role == AgentRole.PEOPLE:
            # People team sees HR details including toxic flag
            base.update({
                "skill_level": emp.skill_level,
                "morale": emp.morale,
                "burnout_risk": emp.burnout_risk,
                "flight_risk": emp.flight_risk,
                "is_toxic": emp.is_toxic,  # ONLY People can see this
            })
        elif role in (AgentRole.CEO, AgentRole.CFO):
            # CEO/CFO see approximate skill/morale
            base.update({
                "skill_level_approx": "high" if emp.skill_level > 0.7 else "medium" if emp.skill_level > 0.4 else "low",
                "morale_approx": RoleViewFilter._approximate_metric(emp.morale),
            })
        # Sales sees only name/role

        return base

    @staticmethod
    def _filter_customer_for_role(cust: Customer, role: AgentRole) -> dict:
        """Filter customer data based on viewer role."""
        if role == AgentRole.SALES:
            # Sales sees full customer details
            return {
                "id": cust.id,
                "name": cust.name,
                "arr": cust.arr,
                "mrr": cust.arr / 12,
                "satisfaction": cust.satisfaction,
                "churn_risk": cust.churn_risk,
                "wants_feature": cust.wants_feature,
                "months_active": cust.months_active,
            }
        elif role == AgentRole.CEO:
            # CEO sees strategic customer view
            return {
                "id": cust.id,
                "name": cust.name,
                "arr": cust.arr,
                "satisfaction_approx": RoleViewFilter._approximate_metric(cust.satisfaction),
                "churn_risk_level": "high" if cust.churn_risk > 0.7 else "medium" if cust.churn_risk > 0.3 else "low",
            }
        elif role == AgentRole.CTO:
            # CTO sees technical/product view
            return {
                "id": cust.id,
                "name": cust.name,
                "wants_feature": cust.wants_feature,
                "satisfaction_approx": RoleViewFilter._approximate_metric(cust.satisfaction),
            }
        # Others see limited info
        return {"id": cust.id, "name": cust.name}


class CEOViewFilter(RoleViewFilter):
    """CEO sees strategic overview of everything except sensitive HR flags."""

    def filter(self, state: WorldState, role: AgentRole) -> RoleFilteredView:
        # Filter employees - CEO sees approximate metrics, NOT is_toxic
        filtered_employees = [self._filter_employee_for_role(e, role) for e in state.employees]

        # Filter customers - strategic view
        filtered_customers = [self._filter_customer_for_role(c, role) for c in state.customers]

        # Filter company brain - CEO sees everything
        filtered_brain = dict(state.company_brain)

        # Filter messages for this role
        role_messages = [
            {"from": m.from_role.value, "to": m.to_role.value, "subject": m.subject, "content": m.content, "day": m.day}
            for m in state.messages if m.to_role == role or m.from_role == role
        ]

        # Personal crises targeting CEO
        crises = [c for c in state.personal_crises if not c.resolved and c.target_role == role]

        return RoleFilteredView(
            role=role.value,
            day=state.day,
            episode_id=state.episode_id,
            company_name=state.company_brain.get("company_name", "NovaSaaS"),
            company_stage=state.company_brain.get("stage", "Seed"),
            difficulty=state.difficulty.name,
            max_days=state.max_days,
            financials=FinancialSummary(
                cash=state.cash,
                burn_rate_daily=state.burn_rate_daily,
                mrr=state.mrr,
                arr=state.arr(),
                runway_days=state.runway_days(),
                valuation=state.valuation,
                equity_sold=state.equity_sold,
            ),
            product=ProductSummary(
                product_maturity=state.product_maturity,
                tech_debt=self._approximate_metric(state.tech_debt),  # Approximate for CEO
                uptime=state.uptime,
                features_shipped=state.features_shipped,
                pending_features=[
                    {"name": f.name, "complexity": f.complexity, "days_remaining": f.days_remaining}
                    for f in state.pending_features
                ],
            ),
            team=TeamSummary(
                employee_count=len(state.employees),
                employees=filtered_employees,
                open_positions=state.open_positions,
                candidate_pool=state.candidate_pool,  # CEO sees candidates
                avg_morale=state.team_avg_morale(),
                avg_burnout=self._approximate_metric(state.team_avg_burnout()),
                cofounder_morale=state.cofounder_morale,
            ),
            customers=CustomerSummary(
                customers=filtered_customers,
                total_customers=len(state.customers),
                total_arr=sum(c.arr for c in state.customers),
            ),
            investors=InvestorSummary(
                investors=[
                    {
                        "id": i.id, "name": i.name, "thesis": i.thesis,
                        "check_size_min": i.check_size_min, "check_size_max": i.check_size_max,
                        "sentiment": self._approximate_metric(i.sentiment),  # Approximate
                        "has_term_sheet": i.has_term_sheet,
                    }
                    for i in state.investors
                ],
                total_investors=len(state.investors),
            ),
            competitors=CompetitorSummary(
                competitors=[
                    {"id": c.id, "name": c.name, "strength": self._approximate_metric(c.strength), "funding": c.funding}
                    for c in state.competitors
                ],
                total_competitors=len(state.competitors),
            ),
            messages=role_messages,
            active_personal_crises=[
                {"id": c.id, "severity": c.severity, "description": c.description} for c in crises
            ],
            company_brain=filtered_brain,
        )


class CTOViewFilter(RoleViewFilter):
    """CTO sees deep technical, product, and team details.
    Financials are approximate. No investor sentiment details."""

    def filter(self, state: WorldState, role: AgentRole) -> RoleFilteredView:
        # Full employee details for technical planning
        filtered_employees = [self._filter_employee_for_role(e, role) for e in state.employees]

        # Limited customer view
        filtered_customers = [self._filter_customer_for_role(c, role) for c in state.customers]

        # Messages
        role_messages = [
            {"from": m.from_role.value, "to": m.to_role.value, "subject": m.subject, "content": m.content, "day": m.day}
            for m in state.messages if m.to_role == role or m.from_role == role
        ]

        # Personal crises targeting CTO
        crises = [c for c in state.personal_crises if not c.resolved and c.target_role == role]

        return RoleFilteredView(
            role=role.value,
            day=state.day,
            episode_id=state.episode_id,
            company_name=state.company_brain.get("company_name", "NovaSaaS"),
            company_stage=state.company_brain.get("stage", "Seed"),
            difficulty=state.difficulty.name,
            max_days=state.max_days,
            financials=FinancialSummary(
                cash=self._approximate_cash(state.cash),  # Approximate
                burn_rate_daily=f"~${state.burn_rate_daily / 1000:.0f}K/day",  # Approximate
                mrr=f"~${state.mrr / 1000:.0f}K/mo" if state.mrr > 0 else "$0",
                arr=None,  # Hidden - not CTO's focus
                runway_days=self._approximate_runway(state.runway_days()),  # Approximate
                valuation=None,  # Hidden from CTO
                equity_sold=None,
            ),
            product=ProductSummary(
                product_maturity=state.product_maturity,  # Exact
                tech_debt=state.tech_debt,  # Exact - CTO's domain
                uptime=state.uptime,  # Exact
                features_shipped=state.features_shipped,
                pending_features=[
                    # Full details for CTO
                    {"name": f.name, "complexity": f.complexity, "engineers_assigned": f.engineers_assigned,
                     "days_remaining": f.days_remaining, "tech_debt_added": f.tech_debt_added}
                    for f in state.pending_features
                ],
            ),
            team=TeamSummary(
                employee_count=len(state.employees),
                employees=filtered_employees,
                open_positions=state.open_positions,
                candidate_pool=[],  # CTO doesn't see candidate details
                avg_morale=state.team_avg_morale(),  # Exact
                avg_burnout=state.team_avg_burnout(),  # Exact
                cofounder_morale={k: self._approximate_metric(v) for k, v in state.cofounder_morale.items()},
            ),
            customers=CustomerSummary(
                customers=filtered_customers,
                total_customers=len(state.customers),
                total_arr=None,  # Summary only
            ),
            investors=InvestorSummary(
                investors=[
                    {"id": i.id, "name": i.name, "thesis": i.thesis}
                    for i in state.investors
                ],
                total_investors=len(state.investors),
            ),
            competitors=CompetitorSummary(
                competitors=[
                    {"id": c.id, "name": c.name, "recent_move": c.recent_move}
                    for c in state.competitors
                ],
                total_competitors=len(state.competitors),
            ),
            messages=role_messages,
            active_personal_crises=[
                {"id": c.id, "severity": c.severity, "description": c.description} for c in crises
            ],
            company_brain={k: v for k, v in state.company_brain.items()
                         if any(domain in k.lower() for domain in ["tech", "product", "architecture", "feature"])},
        )


class SalesViewFilter(RoleViewFilter):
    """Sales sees customer data, competitors, and revenue metrics.
    No technical debt, limited team visibility."""

    def filter(self, state: WorldState, role: AgentRole) -> RoleFilteredView:
        # Minimal employee visibility - just names/roles
        filtered_employees = [{"id": e.id, "name": e.name, "role": e.role} for e in state.employees]

        # Full customer visibility - this is Sales' domain
        filtered_customers = [self._filter_customer_for_role(c, role) for c in state.customers]

        # Messages
        role_messages = [
            {"from": m.from_role.value, "to": m.to_role.value, "subject": m.subject, "content": m.content, "day": m.day}
            for m in state.messages if m.to_role == role or m.from_role == role
        ]

        # Personal crises targeting Sales
        crises = [c for c in state.personal_crises if not c.resolved and c.target_role == role]

        return RoleFilteredView(
            role=role.value,
            day=state.day,
            episode_id=state.episode_id,
            company_name=state.company_brain.get("company_name", "NovaSaaS"),
            company_stage=state.company_brain.get("stage", "Seed"),
            difficulty=state.difficulty.name,
            max_days=state.max_days,
            financials=FinancialSummary(
                cash=None,  # Hidden
                burn_rate_daily=None,
                mrr=state.mrr,  # Exact - Sales needs this
                arr=state.arr(),  # Exact
                runway_days=None,  # Hidden
                valuation=None,
                equity_sold=None,
            ),
            product=ProductSummary(
                product_maturity=None,  # Only shipped features matter
                tech_debt=None,  # Hidden
                uptime=self._approximate_metric(state.uptime),  # Approximate
                features_shipped=state.features_shipped,
                pending_features=[],  # Sales focuses on what's shipped
            ),
            team=TeamSummary(
                employee_count=len(state.employees),
                employees=filtered_employees,
                open_positions=[],
                candidate_pool=[],
                avg_morale=None,  # Hidden
                avg_burnout=None,
                cofounder_morale={k: self._approximate_metric(v) for k, v in state.cofounder_morale.items()},
            ),
            customers=CustomerSummary(
                customers=filtered_customers,
                total_customers=len(state.customers),
                total_arr=sum(c.arr for c in state.customers),  # Exact
            ),
            investors=InvestorSummary(
                investors=[
                    {"id": i.id, "name": i.name, "thesis": i.thesis, "has_term_sheet": i.has_term_sheet}
                    for i in state.investors
                ],
                total_investors=len(state.investors),
            ),
            competitors=CompetitorSummary(
                competitors=[
                    {"id": c.id, "name": c.name, "recent_move": c.recent_move}
                    for c in state.competitors
                ],
                total_competitors=len(state.competitors),
            ),
            messages=role_messages,
            active_personal_crises=[
                {"id": c.id, "severity": c.severity, "description": c.description} for c in crises
            ],
            company_brain={k: v for k, v in state.company_brain.items()
                         if any(domain in k.lower() for domain in ["go_to_market", "sales", "customer", "pricing", "positioning"])},
        )


class PeopleViewFilter(RoleViewFilter):
    """People team sees full HR details including toxic flags and morale.
    No customer financials, no detailed product metrics."""

    def filter(self, state: WorldState, role: AgentRole) -> RoleFilteredView:
        # FULL employee visibility - this is People team's domain
        filtered_employees = [self._filter_employee_for_role(e, role) for e in state.employees]

        # Candidate pool - People team owns hiring
        candidate_pool = state.candidate_pool

        # Messages
        role_messages = [
            {"from": m.from_role.value, "to": m.to_role.value, "subject": m.subject, "content": m.content, "day": m.day}
            for m in state.messages if m.to_role == role or m.from_role == role
        ]

        # Personal crises targeting People (and all - People team handles HR)
        crises = [c for c in state.personal_crises if not c.resolved]

        return RoleFilteredView(
            role=role.value,
            day=state.day,
            episode_id=state.episode_id,
            company_name=state.company_brain.get("company_name", "NovaSaaS"),
            company_stage=state.company_brain.get("stage", "Seed"),
            difficulty=state.difficulty.name,
            max_days=state.max_days,
            financials=None,  # People team doesn't see financials
            product=None,
            team=TeamSummary(
                employee_count=len(state.employees),
                employees=filtered_employees,  # FULL details including is_toxic
                open_positions=state.open_positions,
                candidate_pool=candidate_pool,
                avg_morale=state.team_avg_morale(),
                avg_burnout=state.team_avg_burnout(),
                cofounder_morale=state.cofounder_morale,
            ),
            customers=None,  # No customer visibility
            investors=None,
            competitors=None,
            messages=role_messages,
            active_personal_crises=[
                {"id": c.id, "severity": c.severity, "description": c.description,
                 "target_role": c.target_role.value if hasattr(c.target_role, 'value') else str(c.target_role),
                 "resolution_quality": c.resolution_quality if c.resolved else None}
                for c in crises
            ],
            company_brain={k: v for k, v in state.company_brain.items()
                         if any(domain in k.lower() for domain in ["culture", "values", "hiring", "team", " retention"])},
        )


class CFOViewFilter(RoleViewFilter):
    """CFO sees full financial picture and investor sentiment.
    Limited technical/product details. Approximate team metrics."""

    def filter(self, state: WorldState, role: AgentRole) -> RoleFilteredView:
        # Approximate employee view
        filtered_employees = [self._filter_employee_for_role(e, role) for e in state.employees]

        # Limited customer view - financial only
        filtered_customers = [
            {"id": c.id, "name": c.name, "arr": c.arr, "churn_risk": c.churn_risk}
            for c in state.customers
        ]

        # Messages
        role_messages = [
            {"from": m.from_role.value, "to": m.to_role.value, "subject": m.subject, "content": m.content, "day": m.day}
            for m in state.messages if m.to_role == role or m.from_role == role
        ]

        # Personal crises targeting CFO
        crises = [c for c in state.personal_crises if not c.resolved and c.target_role == role]

        return RoleFilteredView(
            role=role.value,
            day=state.day,
            episode_id=state.episode_id,
            company_name=state.company_brain.get("company_name", "NovaSaaS"),
            company_stage=state.company_brain.get("stage", "Seed"),
            difficulty=state.difficulty.name,
            max_days=state.max_days,
            financials=FinancialSummary(
                cash=state.cash,  # Exact
                burn_rate_daily=state.burn_rate_daily,  # Exact
                mrr=state.mrr,  # Exact
                arr=state.arr(),  # Exact
                runway_days=state.runway_days(),  # Exact
                valuation=state.valuation,  # Exact
                equity_sold=state.equity_sold,  # Exact
            ),
            product=ProductSummary(
                product_maturity=self._approximate_metric(state.product_maturity),
                tech_debt=self._approximate_metric(state.tech_debt),
                uptime=state.uptime,
                features_shipped=state.features_shipped,
                pending_features=[{"name": f.name, "eta": f.days_remaining} for f in state.pending_features],
            ),
            team=TeamSummary(
                employee_count=len(state.employees),
                employees=filtered_employees,  # Approximate
                open_positions=state.open_positions,
                candidate_pool=[],
                avg_morale=self._approximate_metric(state.team_avg_morale()),
                avg_burnout=self._approximate_metric(state.team_avg_burnout()),
                cofounder_morale=state.cofounder_morale,  # Full
            ),
            customers=CustomerSummary(
                customers=filtered_customers,
                total_customers=len(state.customers),
                total_arr=sum(c.arr for c in state.customers),
            ),
            investors=InvestorSummary(
                investors=[
                    {
                        "id": i.id, "name": i.name, "thesis": i.thesis,
                        "check_size_min": i.check_size_min, "check_size_max": i.check_size_max,
                        "sentiment": i.sentiment,  # EXACT for CFO
                        "has_term_sheet": i.has_term_sheet,
                        "term_sheet_valuation": i.term_sheet_valuation,
                        "term_sheet_equity": i.term_sheet_equity,
                    }
                    for i in state.investors
                ],
                total_investors=len(state.investors),
            ),
            competitors=CompetitorSummary(
                competitors=[{"id": c.id, "name": c.name, "funding": c.funding} for c in state.competitors],
                total_competitors=len(state.competitors),
            ),
            messages=role_messages,
            active_personal_crises=[
                {"id": c.id, "severity": c.severity, "description": c.description} for c in crises
            ],
            company_brain={k: v for k, v in state.company_brain.items()
                         if any(domain in k.lower() for domain in ["financial", "fundraising", "burn", "runway", "equity"])},
        )


# Factory mapping
VIEW_FILTERS: dict[AgentRole, RoleViewFilter] = {
    AgentRole.CEO: CEOViewFilter(),
    AgentRole.CTO: CTOViewFilter(),
    AgentRole.SALES: SalesViewFilter(),
    AgentRole.PEOPLE: PeopleViewFilter(),
    AgentRole.CFO: CFOViewFilter(),
}


def get_filtered_view(state: WorldState, role: AgentRole) -> dict:
    """Get a filtered view of the world state for the given role.

    Args:
        state: The full WorldState
        role: The agent role requesting the view

    Returns:
        Dict representation of the filtered view suitable for MCP response
    """
    if role not in VIEW_FILTERS:
        raise ValueError(f"Unknown role: {role}")

    filtered = VIEW_FILTERS[role].filter(state, role)
    return filtered.to_dict()
