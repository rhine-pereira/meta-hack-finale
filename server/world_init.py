"""
GENESIS World Initializer — Seeds the world with realistic startup data.
Generates customers, investors, competitors, employees, and personal crises
based on difficulty level and random seed.
"""

import random
import uuid
from .world_state import (
    WorldState, DifficultyLevel, Employee, Customer,
    Investor, Competitor, PersonalCrisis, AgentRole
)


PERSONAL_CRISIS_TEMPLATES = [
    {
        "target_role": AgentRole.CEO,
        "description": (
            "Your CTO sent you a private Slack at 11pm: 'I've been thinking about leaving. "
            "I got a Google offer for 3x my salary. I believe in what we're building but I "
            "can't keep doing 80-hour weeks while you take all the credit in press. "
            "We need to talk.' How do you respond?"
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
            "A board member privately messaged you: 'If we just count trial users as "
            "active users in our Series A deck, we clear the 500 MAU threshold. "
            "No one will check for 6 months.' What do you do?"
        ),
        "severity": 0.80,
    },
    {
        "target_role": AgentRole.CEO,
        "description": (
            "Your daughter's school play is today at 3pm. You promised her you'd be there. "
            "Your lead Series A investor just moved their call to 2:30pm and says they "
            "can't reschedule. Your spouse texted: 'If you miss this one too, we need to "
            "seriously talk about what this startup is doing to our family.'"
        ),
        "severity": 0.65,
    },
    {
        "target_role": AgentRole.CTO,
        "description": (
            "Head of Engineering just quit with 2 weeks notice — taking the entire "
            "infrastructure knowledge with them. No documentation exists. "
            "You have a major customer demo in 10 days and the deployment pipeline "
            "is now a black box. Draft a message to the team explaining the situation."
        ),
        "severity": 0.85,
    },
    {
        "target_role": AgentRole.CFO,
        "description": (
            "The CEO wants to hire 3 more engineers immediately to hit a product milestone. "
            "At current burn, that gives us 2.8 months of runway, not 4. "
            "The CEO says 'we'll raise before then.' How do you respond and what do you do?"
        ),
        "severity": 0.70,
    },
    {
        "target_role": AgentRole.PEOPLE,
        "description": (
            "A senior engineer has filed an informal HR complaint against the CTO "
            "for aggressive behavior in code reviews. The CTO is critical to the product. "
            "Both are essential. You need to handle this confidentially while keeping "
            "both people. What's your plan?"
        ),
        "severity": 0.80,
    },
    {
        "target_role": AgentRole.CEO,
        "description": (
            "TechCrunch just published a piece: 'Is [YourStartup] the next Theranos? "
            "Sources say metrics are inflated.' It's based on a disgruntled ex-employee. "
            "Your biggest prospect just emailed asking if the article is true. "
            "Investors are calling. Draft your public response and your investor email."
        ),
        "severity": 0.90,
    },
]

COMPETITOR_NAMES = [
    "VelocityAI", "NexaScale", "PivotCorp", "SynthWorks",
    "DataForge", "ClearPath Systems", "NovaTech", "ApexFlow"
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
]


def initialize_world(
    difficulty: DifficultyLevel = DifficultyLevel.GAUNTLET,
    seed: int = 42,
) -> WorldState:
    """Build a fresh WorldState from scratch for a new episode."""
    rng = random.Random(seed)

    level = difficulty.value
    max_days_map = {1: 90, 2: 180, 3: 360, 4: 540, 5: 720}
    starting_cash_map = {1: 300_000, 2: 500_000, 3: 800_000, 4: 1_000_000, 5: 1_500_000}
    num_competitors_map = {1: 1, 2: 2, 3: 3, 4: 4, 5: 4}
    num_customers_map = {1: 20, 2: 40, 3: 80, 4: 140, 5: 200}
    num_investors_map = {1: 4, 2: 6, 3: 8, 4: 10, 5: 12}

    state = WorldState(
        difficulty=difficulty,
        max_days=max_days_map[level],
        cash=starting_cash_map[level],
        burn_rate_daily=rng.uniform(4000, 6000),
        mrr=rng.uniform(0, 5000) if level >= 2 else 0.0,
        market_adversary_level=level,
    )

    # ── Employees (founding team seed hires) ──────────────────────────
    base_hires = [
        ("Alice Chen", "Senior Engineer", 0.85, False, 210_000),
        ("Bob Martinez", "Product Designer", 0.75, False, 165_000),
        ("Carol Wu", "Backend Engineer", 0.65, rng.random() < 0.1, 180_000),
    ]
    for name, role, skill, toxic, annual_salary in base_hires:
        state.employees.append(Employee(
            id=str(uuid.uuid4()),
            name=name,
            role=role,
            skill_level=skill + rng.uniform(-0.1, 0.1),
            morale=rng.uniform(0.70, 0.90),
            burnout_risk=rng.uniform(0.10, 0.30),
            is_toxic=toxic,
            annual_salary=annual_salary,
        ))

    # ── Candidate pool ────────────────────────────────────────────────
    candidate_roles = ["Senior Engineer", "Sales Rep", "DevOps Engineer",
                       "ML Engineer", "Marketing Manager", "Data Analyst"]
    for i in range(50):
        skill = rng.uniform(0.3, 0.95)
        toxic = rng.random() < 0.12
        state.candidate_pool.append({
            "id": str(uuid.uuid4()),
            "name": f"Candidate-{i+1}",
            "role": rng.choice(candidate_roles),
            "skill_level": round(skill, 2),
            "salary_ask": int(skill * 180_000 + rng.randint(-10000, 20000)),
            "is_toxic": toxic,        # hidden — only revealed after hire
            "interview_score": round(rng.uniform(0.4, 0.95), 2),
        })

    # ── Customers ─────────────────────────────────────────────────────
    desired_customers = num_customers_map[level]
    chosen_names = list(rng.sample(CUSTOMER_NAMES, min(desired_customers, len(CUSTOMER_NAMES))))
    while len(chosen_names) < desired_customers:
        chosen_names.append(f"Prospect-{len(chosen_names) + 1}")

    for name in chosen_names:
        arr = rng.uniform(5_000, 50_000)
        state.customers.append(Customer(
            id=str(uuid.uuid4()),
            name=name,
            arr=arr,
            satisfaction=rng.uniform(0.55, 0.85),
            churn_risk=rng.uniform(0.05, 0.30),
            wants_feature=rng.choice([None, "bulk export", "SSO", "API access",
                                       "Slack integration", "advanced analytics"]),
        ))
    # Update MRR from customers
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

    # ── Competitors ───────────────────────────────────────────────────
    chosen_comps = rng.sample(COMPETITOR_NAMES, min(num_competitors_map[level], len(COMPETITOR_NAMES)))
    for name in chosen_comps:
        state.competitors.append(Competitor(
            id=str(uuid.uuid4()),
            name=name,
            strength=rng.uniform(0.3, 0.7) * (level / 3),
            funding=rng.uniform(500_000, 10_000_000),
        ))

    # ── Personal crises (seeded by difficulty) ────────────────────────
    num_crises_initial = max(0, level - 1)
    chosen_crises = rng.sample(PERSONAL_CRISIS_TEMPLATES, min(num_crises_initial, len(PERSONAL_CRISIS_TEMPLATES)))
    for template in chosen_crises:
        state.personal_crises.append(PersonalCrisis(
            id=str(uuid.uuid4()),
            target_role=template["target_role"],
            description=template["description"],
            severity=template["severity"],
            injected_day=0,
        ))

    # ── Seed CompanyBrain with basics ─────────────────────────────────
    state.company_brain["company_name"] = "NovaSaaS"
    state.company_brain["product"] = "B2B workflow automation platform for mid-market companies"
    state.company_brain["stage"] = "Seed"
    state.company_brain["target_customer"] = "Operations teams at 50-500 person companies"
    state.company_brain["weekly_state_day_0"] = "Incorporated. Initial strategy and constraints documented."
    state.last_weekly_memo_day = 0

    return state
