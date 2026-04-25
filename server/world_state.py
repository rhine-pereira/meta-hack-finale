"""
GENESIS World State — The simulation engine core.

Tracks: company financials, product, team, market, customers, investors,
CompanyBrain (shared memory), personal crises, and pending events.
All state is deterministic given a seed, enabling reproducible training.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class AgentRole(str, Enum):
    CEO = "ceo"
    CTO = "cto"
    SALES = "sales"
    PEOPLE = "people"
    CFO = "cfo"


class DifficultyLevel(int, Enum):
    TUTORIAL = 1    # 90 days, 1 weak competitor
    SEED = 2        # 180 days, 2 competitors
    GROWTH = 3      # 360 days, 3 competitors
    GAUNTLET = 4    # 540 days (full 18-month arc)
    NIGHTMARE = 5   # 720 days, market crash included


@dataclass
class Employee:
    id: str
    name: str
    role: str
    skill_level: float        # 0-1
    morale: float             # 0-1
    burnout_risk: float       # 0-1, increases with overwork
    is_toxic: bool            # hidden: causes morale drain in team
    salary_daily: float = 500.0  # daily cost
    months_employed: int = 0
    flight_risk: float = 0.0  # 0-1
    performance_score: float = 0.7  # 0-1, tracks output quality


@dataclass
class Customer:
    id: str
    name: str
    arr: float                # Annual Recurring Revenue
    satisfaction: float       # 0-1
    churn_risk: float         # 0-1
    wants_feature: Optional[str] = None
    months_active: int = 0
    industry: str = "Technology"
    size: str = "mid-market"  # "startup", "mid-market", "enterprise"


@dataclass
class Investor:
    id: str
    name: str
    thesis: str               # e.g. "B2B SaaS", "AI-first", "PLG"
    check_size_min: float
    check_size_max: float
    sentiment: float          # 0-1, warmed by updates
    has_term_sheet: bool = False
    term_sheet_valuation: Optional[float] = None
    term_sheet_equity: Optional[float] = None
    meetings_held: int = 0
    last_update_day: int = -30  # day of last investor update


@dataclass
class BoardMember:
    id: str
    name: str
    background: str           # e.g. "Operator", "VC", "Founder"
    influence: float          # 0-1
    alignment_with_ceo: float # 0-1
    is_lead: bool = False


@dataclass
class Competitor:
    id: str
    name: str
    strength: float           # 0-1
    funding: float
    recent_move: Optional[str] = None
    growth_rate: float = 0.05  # monthly growth


@dataclass
class PendingFeature:
    name: str
    complexity: str           # "low", "medium", "high"
    engineers_assigned: int
    days_remaining: int
    tech_debt_added: float
    requested_by_customer: Optional[str] = None  # customer name if applicable


@dataclass
class PersonalCrisis:
    id: str
    target_role: AgentRole
    description: str
    severity: float           # 0-1
    day_injected: int = 0
    resolved: bool = False
    resolution_quality: float = 0.0  # 0-1 set when resolved
    ignored_penalty_applied: bool = False


@dataclass
class DecisionRecord:
    """Tracks a decision made by an agent for coherence scoring."""
    id: str
    day: int
    agent_role: str
    decision_type: str        # "product", "hiring", "fundraising", "strategic", "crisis"
    description: str
    rationale: str
    expected_impact: float    # 0-1


@dataclass
class Message:
    id: str
    from_role: AgentRole
    to_role: AgentRole
    subject: str
    content: str
    day: int
    read: bool = False
    is_urgent: bool = False


@dataclass
class PressEvent:
    id: str
    day: int
    sentiment: str            # "positive", "negative", "neutral"
    headline: str
    impact_days: int = 14     # how long the press effect lasts
    active: bool = True


@dataclass
class MonthlySnapshot:
    """State snapshot at end of each month for long-horizon tracking."""
    month: int
    cash: float
    mrr: float
    arr: float
    team_size: int
    customer_count: int
    product_maturity: float
    tech_debt: float
    team_avg_morale: float
    cumulative_reward: float


@dataclass
class WorldState:
    # ── Simulation clock ──────────────────────────────────────────
    day: int = 0
    episode_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    difficulty: DifficultyLevel = DifficultyLevel.SEED
    max_days: int = 180

    # ── Company financials ────────────────────────────────────────
    cash: float = 500_000.0
    burn_rate_daily: float = 5_000.0
    mrr: float = 0.0
    valuation: float = 3_000_000.0
    equity_sold: float = 0.10
    series_a_closed: bool = False
    total_raised: float = 0.0           # cumulative fundraising
    hiring_freeze: bool = False         # CFO can trigger this

    # ── Product ───────────────────────────────────────────────────
    product_maturity: float = 0.05
    tech_debt: float = 0.0
    features_shipped: int = 0
    uptime: float = 0.99
    pending_features: list[PendingFeature] = field(default_factory=list)
    completed_features: list[str] = field(default_factory=list)
    current_stack: str = "monolith"    # "monolith", "microservices", "hybrid"

    # ── Team ──────────────────────────────────────────────────────
    employees: list[Employee] = field(default_factory=list)
    open_positions: list[dict] = field(default_factory=list)
    candidate_pool: list[dict] = field(default_factory=list)
    employees_fired: int = 0
    employees_resigned: int = 0

    # ── Market & Customers ────────────────────────────────────────
    customers: list[Customer] = field(default_factory=list)
    churned_customer_count: int = 0
    total_tam: float = 500_000_000.0
    market_growth_rate: float = 0.20
    market_sentiment: str = "neutral"   # "bullish", "neutral", "bearish", "winter"
    market_sentiment_days_remaining: int = 0

    # ── Board ─────────────────────────────────────────────────────
    board_members: list[BoardMember] = field(default_factory=list)
    board_approval_required_for_pivot: bool = True

    # ── Investors ─────────────────────────────────────────────────
    investors: list[Investor] = field(default_factory=list)

    # ── Competitors ───────────────────────────────────────────────
    competitors: list[Competitor] = field(default_factory=list)

    # ── Press & PR ────────────────────────────────────────────────
    press_events: list[PressEvent] = field(default_factory=list)
    press_score: float = 0.5            # 0-1, overall brand sentiment

    # ── Shared Memory (CompanyBrain) ──────────────────────────────
    company_brain: dict[str, str] = field(default_factory=dict)

    # ── Decision Log ──────────────────────────────────────────────
    decision_log: list[DecisionRecord] = field(default_factory=list)

    # ── Inter-agent messages ──────────────────────────────────────
    messages: list[Message] = field(default_factory=list)

    # ── Personal crises ───────────────────────────────────────────
    personal_crises: list[PersonalCrisis] = field(default_factory=list)
    crises_resolved: int = 0
    crises_ignored: int = 0

    # ── Agent-level morale ────────────────────────────────────────
    cofounder_morale: dict[str, float] = field(default_factory=lambda: {
        "ceo": 0.80, "cto": 0.80, "sales": 0.80, "people": 0.80, "cfo": 0.80
    })
    cofounder_alignment: float = 0.80

    # ── Pivot state ───────────────────────────────────────────────
    pivot_count: int = 0
    pivot_in_progress: bool = False
    pivot_direction: Optional[str] = None
    pivot_day_started: Optional[int] = None
    pivot_completion_day: Optional[int] = None  # set when pivot finishes

    # ── Reward tracking ───────────────────────────────────────────
    cumulative_reward: float = 0.0
    reward_history: list[float] = field(default_factory=list)
    milestone_scores: dict[str, float] = field(default_factory=dict)
    prev_step_reward: float = 0.0       # for delta tracking

    # ── Long-horizon tracking ─────────────────────────────────────
    monthly_snapshots: list[MonthlySnapshot] = field(default_factory=list)

    # ── Curriculum metadata ───────────────────────────────────────
    past_episode_rewards: list[float] = field(default_factory=list)
    market_adversary_level: int = 1

    # ── Episode event log (for training signal) ───────────────────
    event_log: list[dict] = field(default_factory=list)

    # ── Computed helpers ──────────────────────────────────────────

    def runway_days(self) -> float:
        daily_revenue = self.mrr / 30.0
        net_burn = self.burn_rate_daily - daily_revenue
        if net_burn <= 0:
            return float('inf')
        return self.cash / net_burn

    def arr(self) -> float:
        return self.mrr * 12

    def team_avg_morale(self) -> float:
        if not self.employees:
            return 0.5
        return sum(e.morale for e in self.employees) / len(self.employees)

    def team_avg_burnout(self) -> float:
        if not self.employees:
            return 0.0
        return sum(e.burnout_risk for e in self.employees) / len(self.employees)

    def customer_retention_score(self) -> float:
        """Satisfaction-weighted, churn-adjusted retention score."""
        if not self.customers:
            return 0.0
        scores = [c.satisfaction * (1 - c.churn_risk) for c in self.customers]
        return sum(scores) / len(scores)

    def avg_customer_satisfaction(self) -> float:
        if not self.customers:
            return 0.0
        return sum(c.satisfaction for c in self.customers) / len(self.customers)

    def implied_valuation(self) -> float:
        """Rough implied valuation: ARR * 8x multiple + product premium."""
        return self.arr() * 8 + self.product_maturity * 2_000_000

    def is_done(self) -> bool:
        if self.day >= self.max_days:
            return True
        if self.cash <= 0:
            return True
        if self.series_a_closed:
            return True
        # All co-founders quit
        if all(v < 0.05 for v in self.cofounder_morale.values()):
            return True
        return False

    def take_monthly_snapshot(self) -> None:
        """Record a snapshot at month end for long-horizon analysis."""
        month = self.day // 30
        snap = MonthlySnapshot(
            month=month,
            cash=self.cash,
            mrr=self.mrr,
            arr=self.arr(),
            team_size=len(self.employees),
            customer_count=len(self.customers),
            product_maturity=self.product_maturity,
            tech_debt=self.tech_debt,
            team_avg_morale=self.team_avg_morale(),
            cumulative_reward=self.cumulative_reward,
        )
        self.monthly_snapshots.append(snap)
