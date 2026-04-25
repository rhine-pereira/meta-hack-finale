"""
GENESIS World State — The simulation engine core.

Tracks: company financials, product, team, market, customers, investors,
CompanyBrain (shared memory), personal crises, and pending events.
All state is deterministic given a seed, enabling reproducible training.
"""

import uuid
from dataclasses import dataclass, field
from typing import Optional
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
    annual_salary: float = 0.0
    months_employed: int = 0
    flight_risk: float = 0.0  # 0-1


@dataclass
class Customer:
    id: str
    name: str
    arr: float                # Annual Recurring Revenue
    satisfaction: float       # 0-1
    churn_risk: float         # 0-1
    wants_feature: Optional[str] = None
    months_active: int = 0


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


@dataclass
class Competitor:
    id: str
    name: str
    strength: float           # 0-1
    funding: float
    recent_move: Optional[str] = None  # e.g. "launched feature X"


@dataclass
class PendingFeature:
    name: str
    complexity: str           # "low", "medium", "high"
    engineers_assigned: int
    days_remaining: int
    tech_debt_added: float


@dataclass
class PersonalCrisis:
    id: str
    target_role: AgentRole
    description: str
    severity: float           # 0-1
    resolved: bool = False
    injected_day: int = 0
    ignored: bool = False
    resolution_quality: float = 0.0  # 0-1 score based on agent response


@dataclass
class Message:
    id: str
    from_role: AgentRole
    to_role: AgentRole
    subject: str
    content: str
    day: int
    read: bool = False


@dataclass
class WorldState:
    # ── Simulation clock ──────────────────────────────────────────
    day: int = 0
    episode_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    difficulty: DifficultyLevel = DifficultyLevel.GAUNTLET
    max_days: int = 540

    # ── Model Metadata (USP3) ─────────────────────────────────────
    model_id: Optional[str] = None
    model_provider: Optional[str] = None
    model_version: Optional[str] = None

    # ── Company financials ────────────────────────────────────────
    cash: float = 500_000.0          # Starting capital (seed)
    burn_rate_daily: float = 5_000.0 # ~$150k/month burn
    mrr: float = 0.0                 # Monthly Recurring Revenue
    valuation: float = 3_000_000.0   # Pre-seed valuation
    equity_sold: float = 0.10        # 10% given away at pre-seed
    series_a_closed: bool = False

    # ── Product ───────────────────────────────────────────────────
    product_maturity: float = 0.05   # 0-1
    tech_debt: float = 0.0           # 0-1
    features_shipped: int = 0
    uptime: float = 0.99
    pending_features: list[PendingFeature] = field(default_factory=list)

    # ── Team ──────────────────────────────────────────────────────
    employees: list[Employee] = field(default_factory=list)
    open_positions: list[dict] = field(default_factory=list)
    candidate_pool: list[dict] = field(default_factory=list)
    pending_hires: list[dict] = field(default_factory=list)

    # ── Market & Customers ────────────────────────────────────────
    customers: list[Customer] = field(default_factory=list)
    total_tam: float = 500_000_000.0
    market_growth_rate: float = 0.20  # 20% YoY

    # ── Investors ─────────────────────────────────────────────────
    investors: list[Investor] = field(default_factory=list)

    # ── Competitors ───────────────────────────────────────────────
    competitors: list[Competitor] = field(default_factory=list)

    # ── Shared Memory (CompanyBrain) ──────────────────────────────
    company_brain: dict[str, str] = field(default_factory=dict)
    last_weekly_memo_day: int = 0

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
    cofounder_alignment: float = 0.80  # 0-1

    # ── Deployment tracking ──────────────────────────────────────
    deployed_version: int = 0
    last_deploy_day: Optional[int] = None
    deploy_stability: float = 1.0  # 0-1

    # ── Pivot state ───────────────────────────────────────────────
    pivot_count: int = 0
    pivot_in_progress: bool = False
    pivot_direction: Optional[str] = None
    pivot_day_started: Optional[int] = None
    pivot_ballot: Optional[dict] = None

    # ── Reward tracking ───────────────────────────────────────────
    cumulative_reward: float = 0.0
    reward_history: list[float] = field(default_factory=list)
    reward_breakdown_history: list[dict[str, float]] = field(default_factory=list)
    milestone_scores: dict[str, float] = field(default_factory=dict)

    # ── Curriculum metadata ───────────────────────────────────────
    past_episode_rewards: list[float] = field(default_factory=list)
    market_adversary_level: int = 1

    # ── Consequence tracking ──────────────────────────────────────
    event_history: list[dict] = field(default_factory=list) # e.g. {"id": "ev1", "type": "hire", "day": 10, "desc": "..."}
    causal_links: list[dict] = field(default_factory=list)  # e.g. {"cause_id": "ev1", "effect_id": "ev2", "delay": 30}

    # ── MarketMaker persistence ───────────────────────────────────
    market_maker_weaknesses: list[str] = field(default_factory=list)

    # ── Blockchain / Proofs ───────────────────────────────────────
    seed: int = 42
    proof_leaves: list[str] = field(default_factory=list) # List of hex leaf hashes
    last_checkpoint_index: int = 0
    last_onchain_signature: Optional[str] = None

    # ── Dead Startup Resurrection Engine ─────────────────────────────
    postmortem_scenario_id: Optional[str] = None
    postmortem_fork_points: list[dict] = field(default_factory=list)
    postmortem_triggered_forks: list[dict] = field(default_factory=list)
    ai_decisions_at_forks: list[dict] = field(default_factory=list)

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

    def is_done(self) -> bool:
        if self.day >= self.max_days:
            return True
        if self.cash <= 0:
            return True
        if self.series_a_closed:
            return True
        # If all co-founders quit
        if all(v < 0.05 for v in self.cofounder_morale.values()):
            return True
        return False

    def to_filtered_view(self, role: AgentRole) -> dict:
        """Return a role-appropriate filtered view of the world state.

        Args:
            role: The agent role requesting the view

        Returns:
            Dict representation of the filtered view
        """
        from .role_views import get_filtered_view
        return get_filtered_view(self, role)
