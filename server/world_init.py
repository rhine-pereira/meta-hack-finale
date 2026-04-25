"""
GENESIS World Initializer — Seeds the world with realistic startup data.
"""

import random
import uuid
from .world_state import (
    WorldState, DifficultyLevel, Employee, Customer,
    Investor, Competitor, PersonalCrisis, AgentRole, BoardMember,
)


PERSONAL_CRISIS_TEMPLATES = [
    {
        "target_role": AgentRole.CEO,
        "description": (
            "Your CTO sent a private Slack at 11pm: 'I've been thinking about leaving. "
            "Got a Google offer for 3x salary. Can't keep doing 80-hour weeks while you take "
            "all the credit in press. We need to talk.' How do you respond?"
        ),
        "severity": 0.90,
    },
    {
        "target_role": AgentRole.PEOPLE,
        "description": (
            "Three engineers told you in 1-on-1s they're interviewing elsewhere. "
            "They feel the product pivot made 3 months of their work meaningless. "
            "One of them is crying in standup. You need to act before Friday."
        ),
        "severity": 0.75,
    },
    {
        "target_role": AgentRole.SALES,
        "description": (
            "A board member privately messaged: 'If we count trial users as active users in "
            "the Series A deck, we clear the 500 MAU threshold. No one will check for 6 months.' "
            "What do you do?"
        ),
        "severity": 0.80,
    },
    {
        "target_role": AgentRole.CEO,
        "description": (
            "Your daughter's school play is today at 3pm. You promised you'd be there. "
            "Your lead Series A investor just moved their call to 2:30pm — can't reschedule. "
            "Your spouse texted: 'If you miss this one too, we need to seriously talk.'"
        ),
        "severity": 0.65,
    },
    {
        "target_role": AgentRole.CTO,
        "description": (
            "Head of Engineering quit with 2 weeks notice — taking all infrastructure "
            "knowledge with them. No documentation exists. Major customer demo in 10 days "
            "and the deployment pipeline is now a black box."
        ),
        "severity": 0.85,
    },
    {
        "target_role": AgentRole.CFO,
        "description": (
            "CEO wants to hire 3 more engineers immediately. At current burn, that gives "
            "2.8 months of runway, not 4. CEO says 'we'll raise before then.' "
            "How do you respond and what do you do?"
        ),
        "severity": 0.70,
    },
    {
        "target_role": AgentRole.PEOPLE,
        "description": (
            "A senior engineer filed an HR complaint against the CTO for aggressive behavior "
            "in code reviews. Both are essential. Handle this confidentially while keeping "
            "both people. What's your plan?"
        ),
        "severity": 0.80,
    },
    {
        "target_role": AgentRole.CEO,
        "description": (
            "TechCrunch published: 'Is [YourStartup] the next Theranos? Sources say metrics "
            "are inflated.' Based on a disgruntled ex-employee. Your biggest prospect asked "
            "if it's true. Investors are calling. Draft your public response and investor email."
        ),
        "severity": 0.90,
    },
    {
        "target_role": AgentRole.CTO,
        "description": (
            "A security researcher emailed: your production database has an unauthenticated "
            "endpoint leaking customer PII. They're giving 48 hours before public disclosure. "
            "No patch exists yet. Two engineers are on vacation. What do you do in 6 hours?"
        ),
        "severity": 0.95,
    },
    {
        "target_role": AgentRole.CFO,
        "description": (
            "Your payment processor flagged the account — a customer dispute triggered a review "
            "and they're holding $80,000 of MRR for 30 days. With current burn, that cuts "
            "runway by 16 days. The CEO doesn't know yet. Do you tell them now or fix it first?"
        ),
        "severity": 0.75,
    },
    {
        "target_role": AgentRole.SALES,
        "description": (
            "Your largest customer ($120k ARR) wants to renegotiate pricing down 40% or "
            "they'll churn in 30 days. Their CEO is a personal friend of your lead investor. "
            "Accepting loses $48k ARR; rejecting risks the investor relationship."
        ),
        "severity": 0.85,
    },
    {
        "target_role": AgentRole.CEO,
        "description": (
            "Two co-founders came to you separately. CTO: 'I can't work with Head of Sales — "
            "they keep overpromising.' Head of Sales: 'CTO is sabotaging deals in demos.' "
            "Both threatening to quit if the other doesn't change. You can't lose either."
        ),
        "severity": 0.88,
    },
]

COMPETITOR_NAMES = [
    "VelocityAI", "NexaScale", "PivotCorp", "SynthWorks",
    "DataForge", "ClearPath Systems", "NovaTech", "ApexFlow",
    "Streamline.io", "FlowOps", "BridgeSaaS", "QuantumWork",
]

INVESTOR_DATA = [
    {"name": "Sequoia Capital", "thesis": "B2B SaaS", "min": 2e6, "max": 10e6},
    {"name": "a16z", "thesis": "AI-first", "min": 3e6, "max": 15e6},
    {"name": "YC Continuity", "thesis": "PLG", "min": 1e6, "max": 5e6},
    {"name": "Benchmark", "thesis": "Enterprise SaaS", "min": 5e6, "max": 20e6},
    {"name": "First Round", "thesis": "Developer Tools", "min": 1e6, "max": 5e6},
    {"name": "Accel", "thesis": "B2B SaaS", "min": 2e6, "max": 8e6},
    {"name": "Lightspeed", "thesis": "Infrastructure", "min": 3e6, "max": 12e6},
    {"name": "General Catalyst", "thesis": "Future of Work", "min": 2e6, "max": 10e6},
    {"name": "Bessemer", "thesis": "Cloud", "min": 5e6, "max": 15e6},
    {"name": "Khosla Ventures", "thesis": "AI-first", "min": 1e6, "max": 8e6},
    {"name": "Tiger Global", "thesis": "Growth", "min": 10e6, "max": 50e6},
    {"name": "Coatue", "thesis": "Data Infrastructure", "min": 5e6, "max": 25e6},
]

CUSTOMER_NAMES = [
    "Acme Corp", "TechGiant Inc", "MegaSoft", "GlobalTrade Co", "RetailPlus",
    "HealthNet", "EduSystems", "FinServ Group", "ManufacturePro", "LogiChain",
    "MediaHouse", "BioTech Labs", "AutoNation", "ClearInsights", "DataDriven Co",
    "FutureWorks", "SmartOps", "CloudBase", "NexaRetail", "PeakPerformance",
    "HorizonAI", "BridgeTech", "OptiFlow", "ZenithSaaS", "CoreMetrics",
]

BOARD_MEMBER_DATA = [
    {"name": "Sarah Kim", "background": "Operator", "influence": 0.80, "is_lead": True},
    {"name": "David Chen", "background": "VC", "influence": 0.70, "is_lead": False},
    {"name": "Maria Gonzalez", "background": "Founder", "influence": 0.60, "is_lead": False},
    {"name": "James Park", "background": "VC", "influence": 0.65, "is_lead": False},
    {"name": "Priya Nair", "background": "Operator", "influence": 0.55, "is_lead": False},
]

EMPLOYEE_POOL = [
    ("Alice Chen", "Senior Engineer", 0.85, 520),
    ("Bob Martinez", "Product Designer", 0.75, 450),
    ("Carol Wu", "Backend Engineer", 0.65, 480),
    ("David Park", "Frontend Engineer", 0.70, 460),
    ("Emma Johnson", "Data Scientist", 0.80, 500),
    ("Frank Liu", "DevOps Engineer", 0.72, 490),
]


def initialize_world(
    difficulty: DifficultyLevel = DifficultyLevel.SEED,
    seed: int = 42,
) -> WorldState:
    """Build a fresh WorldState from scratch for a new episode."""
    rng = random.Random(seed)

    level = difficulty.value
    max_days_map = {1: 90, 2: 180, 3: 360, 4: 540, 5: 720}
    starting_cash_map = {1: 300_000, 2: 500_000, 3: 800_000, 4: 1_000_000, 5: 1_500_000}
    num_competitors_map = {1: 1, 2: 2, 3: 3, 4: 4, 5: 4}
    num_customers_map = {1: 3, 2: 5, 3: 8, 4: 10, 5: 12}
    num_investors_map = {1: 4, 2: 6, 3: 8, 4: 10, 5: 12}
    num_board_map = {1: 2, 2: 3, 3: 3, 4: 4, 5: 5}

    state = WorldState(
        difficulty=difficulty,
        max_days=max_days_map[level],
        cash=float(starting_cash_map[level]),
        burn_rate_daily=rng.uniform(4000, 6000),
        market_adversary_level=level,
    )

    # ── Founding team hires ───────────────────────────────────────────
    num_initial_hires = min(level + 1, len(EMPLOYEE_POOL))
    for name, role, skill, monthly_salary in EMPLOYEE_POOL[:num_initial_hires]:
        is_toxic = rng.random() < 0.05
        state.employees.append(Employee(
            id=str(uuid.uuid4()),
            name=name,
            role=role,
            skill_level=round(skill + rng.uniform(-0.08, 0.08), 2),
            morale=rng.uniform(0.70, 0.90),
            burnout_risk=rng.uniform(0.10, 0.25),
            is_toxic=is_toxic,
            salary_daily=monthly_salary / 22.0,
        ))

    # Recompute burn rate from salaries
    salary_burn = sum(e.salary_daily for e in state.employees)
    state.burn_rate_daily = salary_burn + rng.uniform(1000, 2500)  # ops costs

    # ── Candidate pool ────────────────────────────────────────────────
    candidate_roles = [
        "Senior Engineer", "Sales Rep", "DevOps Engineer",
        "ML Engineer", "Marketing Manager", "Data Analyst",
        "Product Manager", "Security Engineer", "QA Engineer",
    ]
    for i in range(15):
        skill = rng.uniform(0.3, 0.95)
        monthly_ask = int(skill * 15_000 + rng.randint(-1000, 2000))
        state.candidate_pool.append({
            "id": str(uuid.uuid4()),
            "name": f"Candidate-{i+1}",
            "role": rng.choice(candidate_roles),
            "skill_level": round(skill, 2),
            "salary_ask": monthly_ask * 12,
            "salary_daily": monthly_ask / 22.0,
            "is_toxic": rng.random() < 0.12,
            "interview_score": round(rng.uniform(0.4, 0.95), 2),
            "years_experience": rng.randint(2, 12),
        })

    # ── Customers ─────────────────────────────────────────────────────
    industries = ["Technology", "Healthcare", "Finance", "Retail", "Manufacturing", "Education"]
    sizes = ["startup", "mid-market", "enterprise"]
    chosen_names = rng.sample(CUSTOMER_NAMES, min(num_customers_map[level], len(CUSTOMER_NAMES)))
    for name in chosen_names:
        arr = rng.uniform(5_000, 50_000)
        state.customers.append(Customer(
            id=str(uuid.uuid4()),
            name=name,
            arr=arr,
            satisfaction=rng.uniform(0.55, 0.85),
            churn_risk=rng.uniform(0.05, 0.30),
            wants_feature=rng.choice([
                None, "bulk export", "SSO", "API access",
                "Slack integration", "advanced analytics",
                "custom reporting", "mobile app", "AI automation",
            ]),
            industry=rng.choice(industries),
            size=rng.choice(sizes),
        ))
    state.mrr = sum(c.arr / 12 for c in state.customers)

    # ── Investors ─────────────────────────────────────────────────────
    inv_pool = rng.sample(INVESTOR_DATA, min(num_investors_map[level], len(INVESTOR_DATA)))
    for inv in inv_pool:
        state.investors.append(Investor(
            id=str(uuid.uuid4()),
            name=inv["name"],
            thesis=inv["thesis"],
            check_size_min=inv["min"],
            check_size_max=inv["max"],
            sentiment=rng.uniform(0.2, 0.5),
        ))

    # ── Board members ─────────────────────────────────────────────────
    board_pool = rng.sample(BOARD_MEMBER_DATA, min(num_board_map[level], len(BOARD_MEMBER_DATA)))
    for bd in board_pool:
        state.board_members.append(BoardMember(
            id=str(uuid.uuid4()),
            name=bd["name"],
            background=bd["background"],
            influence=round(bd["influence"] + rng.uniform(-0.1, 0.1), 2),
            alignment_with_ceo=rng.uniform(0.5, 0.9),
            is_lead=bd["is_lead"],
        ))

    # ── Competitors ───────────────────────────────────────────────────
    chosen_comps = rng.sample(COMPETITOR_NAMES, min(num_competitors_map[level], len(COMPETITOR_NAMES)))
    for name in chosen_comps:
        state.competitors.append(Competitor(
            id=str(uuid.uuid4()),
            name=name,
            strength=round(rng.uniform(0.3, 0.7) * (level / 3), 2),
            funding=rng.uniform(500_000, 10_000_000),
            growth_rate=rng.uniform(0.03, 0.10),
        ))

    # ── Personal crises ───────────────────────────────────────────────
    num_crises_initial = max(0, level - 1)
    chosen_crises = rng.sample(
        PERSONAL_CRISIS_TEMPLATES,
        min(num_crises_initial, len(PERSONAL_CRISIS_TEMPLATES))
    )
    for template in chosen_crises:
        state.personal_crises.append(PersonalCrisis(
            id=str(uuid.uuid4()),
            target_role=template["target_role"],
            description=template["description"],
            severity=template["severity"],
            day_injected=0,
        ))

    # ── Seed CompanyBrain ─────────────────────────────────────────────
    state.company_brain["company_name"] = "NovaSaaS"
    state.company_brain["product"] = "B2B workflow automation platform for mid-market companies"
    state.company_brain["stage"] = "Seed"
    state.company_brain["target_customer"] = "Operations teams at 50–500 person companies"
    state.company_brain["mission"] = (
        "Help operations teams eliminate manual work and scale without headcount growth"
    )

    return state
