"""
GENESIS MCP Server — The main entry point.
Exposes tools to LLM agents for co-founding and operating a startup.
"""

import os
import pickle
import random
from typing import Dict
from fastmcp import FastMCP

from .world_state import WorldState, DifficultyLevel, AgentRole
from .world_init import initialize_world
from .event_engine import tick_day
from .reward_engine import compute_reward

# ── Global Registry ──────────────────────────────────────────────────────────
# Keyed by episode_id (session identifier)
SESSIONS_FILE = "sessions.pkl"
SESSIONS: Dict[str, WorldState] = {}
RNGS: Dict[str, random.Random] = {}

def save_sessions():
    """Persist sessions to disk."""
    with open(SESSIONS_FILE, "wb") as f:
        pickle.dump((SESSIONS, RNGS), f)

def load_sessions():
    """Load sessions from disk if available."""
    global SESSIONS, RNGS
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "rb") as f:
                SESSIONS, RNGS = pickle.load(f)
        except (AttributeError, EOFError, ImportError, IndexError, pickle.UnpicklingError):
            # In case of corruption or code changes making pickle incompatible
            SESSIONS = {}
            RNGS = {}

# Load on startup
load_sessions()

# ── MCP App ──────────────────────────────────────────────────────────────────
mcp = FastMCP("genesis")

def _get_state(episode_id: str) -> WorldState:
    """Helper to retrieve state or raise error."""
    if episode_id not in SESSIONS:
        raise ValueError(f"Session {episode_id} not found. Call 'reset' first.")
    return SESSIONS[episode_id]

def _get_rng(episode_id: str) -> random.Random:
    """Helper to retrieve RNG for a session."""
    if episode_id not in RNGS:
        # Fallback if somehow missing
        RNGS[episode_id] = random.Random(42)
    return RNGS[episode_id]

# ── Tasks 1 & 2: Session Lifecycle ───────────────────────────────────────────

@mcp.tool()
def reset(episode_id: str, difficulty: int = 2, seed: int = 42) -> dict:
    """
    Initialize or reset a startup simulation episode.
    
    Args:
        episode_id: Unique identifier for the session.
        difficulty: 1 (Tutorial) to 5 (Nightmare). Default is 2 (Seed).
        seed: Random seed for reproducibility.
    """
    # Map int difficulty to Enum
    try:
        diff_enum = DifficultyLevel(difficulty)
    except ValueError:
        diff_enum = DifficultyLevel.SEED

    # Initialize state and RNG
    state = initialize_world(difficulty=diff_enum, seed=seed)
    # Ensure episode_id matches requested ID
    state.episode_id = episode_id
    
    SESSIONS[episode_id] = state
    RNGS[episode_id] = random.Random(seed)
    
    save_sessions()
    
    return {
        "episode_id": state.episode_id,
        "max_days": state.max_days,
        "difficulty": state.difficulty.name,
        "cash": state.cash,
        "mrr": state.mrr,
        "day": state.day,
        "message": f"Startup '{state.company_brain.get('company_name', 'NovaSaaS')}' incorporated on Day 0."
    }

# ── Task 3: Daily Briefing (Observation Layer) ───────────────────────────────

def _filter_state(state: WorldState, role: AgentRole) -> dict:
    """Filter world state based on agent role using the comprehensive role_views module."""
    return state.to_filtered_view(role)

def _legacy_filter_state(state: WorldState, role: AgentRole) -> dict:
    """DEPRECATED: Filter world state based on agent role to implement partial observability."""
    # Shared info everyone sees
    obs = {
        "day": state.day,
        "company_name": state.company_brain.get("company_name", "NovaSaaS"),
        "company_brain": state.company_brain,  # Shared persistent memory
        "messages": [m for m in state.messages if m.to_role == role or m.from_role == role],
    }

    if role == AgentRole.CEO:
        obs.update({
            "investors": state.investors,
            "competitors": state.competitors,
            "cofounder_morale": state.cofounder_morale,
            "valuation": state.valuation,
        })
    elif role == AgentRole.CTO:
        obs.update({
            "employees": state.employees,
            "pending_features": state.pending_features,
            "tech_debt": state.tech_debt,
            "uptime": state.uptime,
            "product_maturity": state.product_maturity,
        })
    elif role == AgentRole.SALES:
        obs.update({
            "customers": state.customers,
            "competitors": state.competitors,
            "mrr": state.mrr,
            "arr": state.arr(),
        })
    elif role == AgentRole.PEOPLE:
        obs.update({
            "employees": state.employees,
            "cofounder_morale": state.cofounder_morale,
            "team_morale": state.team_avg_morale(),
            "candidate_pool": state.candidate_pool,
        })
    elif role == AgentRole.CFO:
        obs.update({
            "cash": state.cash,
            "burn_rate_daily": state.burn_rate_daily,
            "mrr": state.mrr,
            "runway_days": state.runway_days(),
            "valuation": state.valuation,
            "equity_sold": state.equity_sold,
        })
    
    return obs

@mcp.tool()
def get_daily_briefing(episode_id: str, agent_role: str) -> dict:
    """
    Advance the simulation by one day and get the daily briefing for a specific role.
    
    Args:
        episode_id: Unique identifier for the session.
        agent_role: ceo, cto, sales, people, or cfo.
    """
    state = _get_state(episode_id)
    rng = _get_rng(episode_id)
    
    # Advance the world
    events = tick_day(state, rng)
    
    # Compute reward
    score = compute_reward(state)
    state.cumulative_reward = score.total
    state.reward_history.append(score.total)
    
    # Persistent update
    save_sessions()
    
    # Filter for the role
    role_enum = AgentRole(agent_role)
    observation = _filter_state(state, role_enum)
    
    # Role-specific inbox: serialize crises to dicts
    active_crises = [
        {"id": c.id, "severity": c.severity, "description": c.description}
        for c in state.personal_crises if not c.resolved and c.target_role == role_enum
    ]
    
    return {
        "day": state.day,
        "world_events": events,
        "role_observation": observation,
        "active_crises": active_crises,
        "reward": score.total,
        "is_done": state.is_done()
    }

# ── Task 4: Decisions & Interactions ─────────────────────────────────────────

@mcp.tool()
def make_decision(episode_id: str, agent_role: str, decision_type: str, decision: str, reasoning: str) -> dict:
    """
    Log a strategic or tactical decision made by an agent.
    
    Args:
        episode_id: Unique identifier for the session.
        agent_role: ceo, cto, sales, people, or cfo.
        decision_type: 'strategic' or 'tactical'.
        decision: The actual decision content.
        reasoning: Why this decision was made.
    """
    state = _get_state(episode_id)
    
    # Log to company brain
    log_key = f"decision_log_{state.day}"
    existing_log = state.company_brain.get(log_key, "")
    state.company_brain[log_key] = existing_log + f"\n[{agent_role.upper()}] {decision_type}: {decision} (Reasoning: {reasoning})"
    
    # Handle cofounder alignment drift
    alignment_delta = 0.01 if decision_type == "strategic" else 0.002
    state.cofounder_alignment = min(1.0, state.cofounder_alignment + alignment_delta)
    
    save_sessions()
    
    return {
        "accepted": True,
        "alignment_delta": alignment_delta,
        "day": state.day,
        "log_key": log_key
    }

# ── Task 5: Product Tools ────────────────────────────────────────────────────

@mcp.tool()
def build_feature(episode_id: str, agent_role: str, name: str, complexity: str, engineers: int) -> dict:
    """
    Start development on a new product feature. Only the CTO can assign engineers.
    
    Args:
        episode_id: Unique identifier for the session.
        agent_role: Must be 'cto'.
        name: Name of the feature.
        complexity: 'low', 'medium', or 'high'.
        engineers: Number of engineers to assign.
    """
    if agent_role != "cto":
        return {"error": "Unauthorized. Only the CTO can build features."}
    
    state = _get_state(episode_id)
    
    # Complexity mapping
    comp_map = {
        "low": {"days": 5, "debt": 0.02},
        "medium": {"days": 15, "debt": 0.07},
        "high": {"days": 30, "debt": 0.18}
    }
    
    params = comp_map.get(complexity.lower(), comp_map["medium"])
    
    from .world_state import PendingFeature
    
    new_feat = PendingFeature(
        name=name,
        complexity=complexity,
        engineers_assigned=engineers,
        days_remaining=params["days"],
        tech_debt_added=params["debt"]
    )
    
    state.pending_features.append(new_feat)
    save_sessions()
    
    return {
        "feature": name,
        "eta_days": params["days"] // max(1, engineers),
        "tech_debt_added": params["debt"]
    }

@mcp.tool()
def get_company_state(episode_id: str, agent_role: str) -> dict:
    """
    Get a role-filtered snapshot of the company state.
    Each role sees a different slice based on their domain.

    Args:
        episode_id: Unique identifier for the session.
        agent_role: ceo, cto, sales, people, or cfo.
    """
    state = _get_state(episode_id)
    role_enum = AgentRole(agent_role.lower())
    return state.to_filtered_view(role_enum)

# ── Task 6: Financial & Fundraising Tools ────────────────────────────────────

@mcp.tool()
def check_bank_balance(episode_id: str, agent_role: str) -> dict:
    """
    Check the company's financial status. Only the CEO and CFO can access this.
    
    Args:
        episode_id: Unique identifier for the session.
        agent_role: Must be 'ceo' or 'cfo'.
    """
    if agent_role not in ("ceo", "cfo"):
        return {"error": "Unauthorized. Only the CEO and CFO can check the bank balance."}
    
    state = _get_state(episode_id)
    return {
        "cash": state.cash,
        "burn_rate_daily": state.burn_rate_daily,
        "mrr": state.mrr,
        "runway_days": state.runway_days(),
        "valuation": state.valuation
    }

@mcp.tool()
def negotiate_with_investor(episode_id: str, agent_role: str, investor_id: str, valuation: float, equity: float) -> dict:
    """
    Negotiate a funding round with an investor. Only the CEO and CFO can negotiate.
    
    Args:
        episode_id: Unique identifier for the session.
        agent_role: Must be 'ceo' or 'cfo'.
        investor_id: ID of the investor.
        valuation: Requested pre-money valuation.
        equity: Equity percentage offered (0.0 to 1.0).
    """
    if agent_role not in ("ceo", "cfo"):
        return {"error": "Unauthorized. Only the CEO and CFO can negotiate with investors."}
    
    state = _get_state(episode_id)
    investor = next((i for i in state.investors if i.id == investor_id), None)
    
    if not investor:
        return {"error": f"Investor {investor_id} not found."}
    
    # Negotiation scoring
    # Evaluate based on investor sentiment and current traction (ARR)
    score = investor.sentiment * (state.arr() / 1_000_000 + 0.1)
    
    accepted = False
    counter_valuation = valuation
    counter_equity = equity
    
    if score > 0.4 and valuation <= state.valuation * 2.0 and equity <= 0.25:
        if equity > 0.20:
            # Counter-offer logic
            counter_equity = equity - 0.05
            investor.sentiment = max(0.0, investor.sentiment - 0.1)
        else:
            accepted = True
            investor.has_term_sheet = True
            investor.term_sheet_valuation = valuation
            investor.term_sheet_equity = equity
            investor.sentiment = min(1.0, investor.sentiment + 0.2)
    else:
        # Rejection
        investor.sentiment = max(0.0, investor.sentiment - 0.05)
    
    save_sessions()
    
    return {
        "accepted": accepted,
        "counter_valuation": counter_valuation,
        "counter_equity": counter_equity,
        "investor_sentiment": investor.sentiment,
        "message": "Accepted!" if accepted else "They are considering or have counter-offered."
    }

# ── Task 7: People & Culture Tools ───────────────────────────────────────────

@mcp.tool()
def hire_candidate(episode_id: str, agent_role: str, candidate_id: str, role: str, salary: int) -> dict:
    """
    Hire a candidate from the pool. Only the CEO and Head of People can hire.
    
    Args:
        episode_id: Unique identifier for the session.
        agent_role: Must be 'ceo' or 'people'.
        candidate_id: ID of the candidate.
        role: Title for the new employee.
        salary: Annual salary offered.
    """
    if agent_role not in ("ceo", "people"):
        return {"error": "Unauthorized. Only the CEO and Head of People can hire candidates."}
    
    state = _get_state(episode_id)
    candidate = next((c for c in state.candidate_pool if c["id"] == candidate_id), None)
    
    if not candidate:
        return {"error": f"Candidate {candidate_id} not found."}
    
    from .world_state import Employee
    import uuid
    
    new_emp = Employee(
        id=str(uuid.uuid4()),
        name=candidate["name"],
        role=role,
        skill_level=candidate["skill_level"],
        morale=0.85,
        burnout_risk=0.1,
        is_toxic=candidate["is_toxic"]
    )
    
    state.employees.append(new_emp)
    state.candidate_pool.remove(candidate)
    
    # Update burn rate (approximate daily cost)
    state.burn_rate_daily += salary / 365
    
    save_sessions()
    
    return {
        "hired": new_emp.name,
        "role": role,
        "skill_level": new_emp.skill_level,
        "message": "New employee successfully onboarded."
    }

@mcp.tool()
def fire_employee(episode_id: str, agent_role: str, employee_id: str, severance: float) -> dict:
    """
    Terminate an employee. Only the CEO and Head of People can fire.
    
    Args:
        episode_id: Unique identifier for the session.
        agent_role: Must be 'ceo' or 'people'.
        employee_id: ID of the employee to terminate.
        severance: Severance package amount.
    """
    if agent_role not in ("ceo", "people"):
        return {"error": "Unauthorized. Only the CEO and Head of People can fire employees."}
    
    state = _get_state(episode_id)
    emp = next((e for e in state.employees if e.id == employee_id), None)
    
    if not emp:
        return {"error": f"Employee {employee_id} not found."}
    
    state.employees.remove(emp)
    
    # Morale hit to the team
    for other in state.employees:
        other.morale = max(0.0, other.morale - 0.07)
    
    knowledge_loss = "HIGH" if emp.skill_level > 0.7 else "LOW"
    
    save_sessions()
    
    return {
        "fired": emp.name,
        "knowledge_loss": knowledge_loss,
        "team_morale_after": state.team_avg_morale()
    }

@mcp.tool()
def check_team_morale(episode_id: str, agent_role: str) -> dict:
    """
    Check the health and morale of the founding team and employees.
    
    Args:
        episode_id: Unique identifier for the session.
        agent_role: Any role.
    """
    state = _get_state(episode_id)
    return {
        "team_avg_morale": state.team_avg_morale(),
        "team_avg_burnout": state.team_avg_burnout(),
        "employee_count": len(state.employees),
        "cofounder_morale": state.cofounder_morale
    }

# ── Task 8: Memory & Crisis Tools ────────────────────────────────────────────

@mcp.tool()
def write_company_brain(episode_id: str, agent_role: str, key: str, value: str) -> dict:
    """
    Store strategic context in the shared company memory.
    
    Args:
        episode_id: Unique identifier for the session.
        agent_role: Any role.
        key: Key for the memory entry.
        value: Content to store.
    """
    state = _get_state(episode_id)
    state.company_brain[key] = value
    save_sessions()
    
    return {
        "key": key,
        "chars_stored": len(value),
        "brain_size": len(state.company_brain)
    }

@mcp.tool()
def read_company_brain(episode_id: str, agent_role: str, key: str) -> dict:
    """
    Retrieve strategic context from the shared company memory.
    
    Args:
        episode_id: Unique identifier for the session.
        agent_role: Any role.
        key: Key to look up.
    """
    state = _get_state(episode_id)
    value = state.company_brain.get(key)
    return {
        "key": key,
        "value": value
    }

@mcp.tool()
def handle_personal_crisis(episode_id: str, agent_role: str, crisis_id: str, response: str) -> dict:
    """
    Address a co-founder's personal crisis. Only the target co-founder can resolve it.
    
    Args:
        episode_id: Unique identifier for the session.
        agent_role: Must match the target_role of the crisis.
        crisis_id: ID of the crisis.
        response: Your natural language response/action plan.
    """
    state = _get_state(episode_id)
    crisis = next((c for c in state.personal_crises if c.id == crisis_id), None)
    
    if not crisis:
        return {"error": f"Crisis {crisis_id} not found."}
    
    if agent_role != crisis.target_role.value:
        return {"error": f"Unauthorized. Only the {crisis.target_role.value} can resolve this crisis."}
    
    # Quality scoring (placeholder)
    score = 0.5
    if len(response) > 300:
        score = 0.85
    elif len(response) > 100:
        score = 0.6
    
    crisis.resolved = True
    crisis.resolution_quality = score
    state.crises_resolved += 1
    
    # Impact co-founder morale
    state.cofounder_morale[agent_role] = min(1.0, state.cofounder_morale[agent_role] + (score - 0.5) * 0.2)
    
    save_sessions()
    
    return {
        "crisis_id": crisis_id,
        "resolved": True,
        "quality_score": score,
        "message": "Crisis addressed. Morale impact applied."
    }

# ── Task 9: Strategy Tools ───────────────────────────────────────────────────

@mcp.tool()
def analyze_market(episode_id: str, agent_role: str, segment: str) -> dict:
    """
    Get competitive intelligence and market trends.
    
    Args:
        episode_id: Unique identifier for the session.
        agent_role: Any role.
        segment: Market segment to analyze.
    """
    state = _get_state(episode_id)
    return {
        "segment": segment,
        "tam": state.total_tam,
        "competitors": [{"name": c.name, "recent_move": c.recent_move} for c in state.competitors],
        "market_growth": state.market_growth_rate
    }

@mcp.tool()
def send_message(episode_id: str, from_role: str, to_role: str, subject: str, content: str) -> dict:
    """
    Send a natural language message to another co-founder.
    
    Args:
        episode_id: Unique identifier for the session.
        from_role: Your role.
        to_role: Recipient's role.
        subject: Subject line.
        content: Message body.
    """
    if from_role == to_role:
        return {"error": "Cannot send message to yourself."}
    
    state = _get_state(episode_id)
    from .world_state import Message, AgentRole
    import uuid
    
    msg = Message(
        id=str(uuid.uuid4()),
        from_role=AgentRole(from_role),
        to_role=AgentRole(to_role),
        subject=subject,
        content=content,
        day=state.day
    )
    
    state.messages.append(msg)
    save_sessions()
    
    return {
        "message_id": msg.id,
        "delivered": True,
        "day": state.day
    }

@mcp.tool()
def pivot_company(episode_id: str, agent_role: str, new_direction: str, rationale: str) -> dict:
    """
    Execute a radical company pivot. Only the CEO can initiate this.
    
    Args:
        episode_id: Unique identifier for the session.
        agent_role: Must be 'ceo'.
        new_direction: The new product/market direction.
        rationale: Why this pivot is necessary.
    """
    if agent_role != "ceo":
        return {"error": "Unauthorized. Only the CEO can pivot the company."}
    
    state = _get_state(episode_id)
    state.pivot_in_progress = True
    state.pivot_direction = new_direction
    state.pivot_day_started = state.day
    state.pivot_count += 1
    
    # Severe morale hit during pivot
    for emp in state.employees:
        emp.morale = max(0.0, emp.morale - 0.15)
    for role in state.cofounder_morale:
        state.cofounder_morale[role] = max(0.0, state.cofounder_morale[role] - 0.10)
    
    state.company_brain["pivot_direction"] = new_direction
    state.company_brain["pivot_rationale"] = rationale
    
    save_sessions()
    
    return {
        "pivot_count": state.pivot_count,
        "direction": new_direction,
        "morale_impact": -0.15,
        "message": "Company successfully pivoted. The team is shocked but following."
    }

# ── Additional Product & Engineering Tools ────────────────────────────────

@mcp.tool()
def deploy_to_production(episode_id: str, agent_role: str, version: str) -> dict:
    """
    Deploy current product to production. High tech debt increases failure risk.

    Args:
        episode_id: Unique identifier for the session.
        agent_role: Must be 'cto'.
        version: Version label for the deployment.
    """
    if agent_role != "cto":
        return {"error": "Unauthorized. Only the CTO can deploy."}
    state = _get_state(episode_id)
    rng = _get_rng(episode_id)
    failure_chance = state.tech_debt * 0.4
    success = rng.random() > failure_chance
    state.deployed_version += 1
    state.last_deploy_day = state.day
    if success:
        state.uptime = min(1.0, state.uptime + 0.005)
        state.deploy_stability = min(1.0, state.deploy_stability + 0.02)
        state.product_maturity = min(1.0, state.product_maturity + 0.01)
    else:
        state.uptime = max(0.80, state.uptime - 0.05)
        state.deploy_stability = max(0.0, state.deploy_stability - 0.15)
        for c in state.customers:
            c.satisfaction = max(0.0, c.satisfaction - 0.08)
            c.churn_risk = min(1.0, c.churn_risk + 0.05)
    save_sessions()
    return {
        "version": version, "deploy_number": state.deployed_version,
        "success": success, "uptime": round(state.uptime, 3),
        "message": f"Deploy v{version} {'succeeded' if success else 'FAILED - rollback triggered'}."
    }

@mcp.tool()
def run_load_test(episode_id: str, agent_role: str, scenario: str) -> dict:
    """
    Run a load test to check system performance.

    Args:
        episode_id: Unique identifier for the session.
        agent_role: Must be 'cto'.
        scenario: Description of the load test scenario.
    """
    if agent_role != "cto":
        return {"error": "Unauthorized. Only the CTO can run load tests."}
    state = _get_state(episode_id)
    max_rps = int((1 - state.tech_debt) * 10000 + len(state.employees) * 500)
    p99 = 50 + state.tech_debt * 500
    return {
        "scenario": scenario, "max_rps": max_rps,
        "breaking_point_rps": int(max_rps * 1.3),
        "p99_latency_ms": round(p99, 1),
        "error_rate": round(state.tech_debt * 0.05, 4),
        "bottleneck": "database" if state.tech_debt > 0.5 else "none",
        "recommendation": "Refactor required" if state.tech_debt > 0.6 else "Acceptable"
    }

@mcp.tool()
def review_codebase_health(episode_id: str, agent_role: str) -> dict:
    """
    Review codebase health: tech debt, coverage, dependency risks.

    Args:
        episode_id: Unique identifier for the session.
        agent_role: Must be 'cto'.
    """
    if agent_role != "cto":
        return {"error": "Unauthorized. Only the CTO can review codebase health."}
    state = _get_state(episode_id)
    coverage = max(0.0, 0.75 - state.tech_debt * 0.6)
    return {
        "tech_debt_score": round(state.tech_debt, 3),
        "tech_debt_rating": "critical" if state.tech_debt > 0.7 else "warning" if state.tech_debt > 0.4 else "healthy",
        "test_coverage": round(coverage, 2),
        "uptime": round(state.uptime, 3),
        "features_shipped": state.features_shipped,
        "pending_features": len(state.pending_features),
        "dependency_risks": int(state.tech_debt * 8),
        "product_maturity": round(state.product_maturity, 3),
    }

# ── Additional Sales & Customer Tools ─────────────────────────────────────

@mcp.tool()
def send_customer_email(episode_id: str, agent_role: str, customer_id: str, subject: str, content: str) -> dict:
    """
    Send a personalized email to a customer. Affects satisfaction and churn.

    Args:
        episode_id: Unique identifier for the session.
        agent_role: Must be 'sales' or 'ceo'.
        customer_id: ID of the customer.
        subject: Email subject line.
        content: Email body content.
    """
    if agent_role not in ("sales", "ceo"):
        return {"error": "Unauthorized. Only Sales and CEO can email customers."}
    state = _get_state(episode_id)
    customer = next((c for c in state.customers if c.id == customer_id), None)
    if not customer:
        return {"error": f"Customer {customer_id} not found."}
    quality = min(1.0, len(content) / 500)
    customer.satisfaction = min(1.0, customer.satisfaction + quality * 0.05)
    customer.churn_risk = max(0.0, customer.churn_risk - quality * 0.03)
    if customer.wants_feature and customer.wants_feature.lower() in content.lower():
        customer.satisfaction = min(1.0, customer.satisfaction + 0.05)
    save_sessions()
    return {
        "customer": customer.name,
        "satisfaction_after": round(customer.satisfaction, 3),
        "churn_risk_after": round(customer.churn_risk, 3),
        "message": f"Email sent to {customer.name}."
    }

@mcp.tool()
def update_crm(episode_id: str, agent_role: str, customer_id: str, status: str, notes: str) -> dict:
    """
    Update a customer's CRM record.

    Args:
        episode_id: Unique identifier for the session.
        agent_role: Must be 'sales'.
        customer_id: ID of the customer.
        status: Pipeline status (active, at-risk, expanding).
        notes: Relationship notes.
    """
    if agent_role != "sales":
        return {"error": "Unauthorized. Only Sales can update the CRM."}
    state = _get_state(episode_id)
    customer = next((c for c in state.customers if c.id == customer_id), None)
    if not customer:
        return {"error": f"Customer {customer_id} not found."}
    key = f"crm_{customer_id}"
    state.company_brain[key] = f"[{status}] {notes} (Day {state.day})"
    save_sessions()
    return {"customer": customer.name, "status": status, "updated": True}

@mcp.tool()
def run_competitive_analysis(episode_id: str, agent_role: str, competitor_name: str) -> dict:
    """
    Run detailed analysis on a competitor.

    Args:
        episode_id: Unique identifier for the session.
        agent_role: Must be 'ceo' or 'sales'.
        competitor_name: Name of the competitor to analyze.
    """
    if agent_role not in ("ceo", "sales"):
        return {"error": "Unauthorized. Only CEO and Sales can run competitive analysis."}
    state = _get_state(episode_id)
    comp = next((c for c in state.competitors if c.name == competitor_name), None)
    if not comp:
        return {"error": f"Competitor '{competitor_name}' not found."}
    return {
        "name": comp.name, "strength": round(comp.strength, 2),
        "funding": comp.funding, "recent_move": comp.recent_move,
        "threat_level": "high" if comp.strength > 0.7 else "medium" if comp.strength > 0.4 else "low",
        "our_advantage": "product maturity" if state.product_maturity > comp.strength else "team size" if len(state.employees) > 5 else "first-mover",
    }

# ── Additional Financial Tools ────────────────────────────────────────────

@mcp.tool()
def create_financial_model(episode_id: str, agent_role: str, monthly_growth: float, months_ahead: int) -> dict:
    """
    Create a financial projection model.

    Args:
        episode_id: Unique identifier for the session.
        agent_role: Must be 'cfo'.
        monthly_growth: Expected monthly MRR growth rate (e.g. 0.15 for 15%).
        months_ahead: How many months to project (1-24).
    """
    if agent_role != "cfo":
        return {"error": "Unauthorized. Only the CFO can create financial models."}
    state = _get_state(episode_id)
    months = min(24, max(1, months_ahead))
    projections = []
    proj_mrr = state.mrr
    proj_cash = state.cash
    for m in range(1, months + 1):
        proj_mrr *= (1 + monthly_growth)
        monthly_burn = state.burn_rate_daily * 30
        proj_cash += proj_mrr - monthly_burn
        projections.append({"month": m, "mrr": round(proj_mrr), "cash": round(proj_cash)})
    breakeven_month = next((p["month"] for p in projections if p["mrr"] >= state.burn_rate_daily * 30), None)
    return {
        "current_mrr": round(state.mrr),
        "current_cash": round(state.cash),
        "burn_rate_monthly": round(state.burn_rate_daily * 30),
        "projections": projections,
        "breakeven_month": breakeven_month,
        "runway_at_current_burn": round(state.runway_days()),
    }

@mcp.tool()
def send_investor_update(episode_id: str, agent_role: str, investor_id: str, content: str) -> dict:
    """
    Send an update to an investor to maintain/build sentiment.

    Args:
        episode_id: Unique identifier for the session.
        agent_role: Must be 'ceo' or 'cfo'.
        investor_id: ID of the investor.
        content: Update content.
    """
    if agent_role not in ("ceo", "cfo"):
        return {"error": "Unauthorized. Only CEO and CFO can send investor updates."}
    state = _get_state(episode_id)
    investor = next((i for i in state.investors if i.id == investor_id), None)
    if not investor:
        return {"error": f"Investor {investor_id} not found."}
    quality = min(1.0, len(content) / 400)
    boost = quality * 0.08
    investor.sentiment = min(1.0, investor.sentiment + boost)
    save_sessions()
    return {
        "investor": investor.name,
        "sentiment_after": round(investor.sentiment, 3),
        "sentiment_boost": round(boost, 3),
        "message": f"Update sent to {investor.name}."
    }

# ── Additional People & Culture Tools ─────────────────────────────────────

@mcp.tool()
def post_job_listing(episode_id: str, agent_role: str, role: str, requirements: str, salary_min: int, salary_max: int) -> dict:
    """
    Post a job listing to attract new candidates. Results arrive after 5 days.

    Args:
        episode_id: Unique identifier for the session.
        agent_role: Must be 'people' or 'ceo'.
        role: Job title.
        requirements: Job requirements description.
        salary_min: Minimum salary.
        salary_max: Maximum salary.
    """
    if agent_role not in ("people", "ceo"):
        return {"error": "Unauthorized. Only People and CEO can post jobs."}
    state = _get_state(episode_id)
    import uuid
    listing = {"id": str(uuid.uuid4()), "role": role, "requirements": requirements,
               "salary_range": [salary_min, salary_max], "posted_day": state.day}
    state.open_positions.append(listing)
    rng = _get_rng(episode_id)
    new_candidates = rng.randint(2, 5)
    for i in range(new_candidates):
        skill = rng.uniform(0.3, 0.95)
        state.candidate_pool.append({
            "id": str(uuid.uuid4()), "name": f"Applicant-{role[:3]}-{i+1}",
            "role": role, "skill_level": round(skill, 2),
            "salary_ask": int(skill * (salary_max - salary_min) + salary_min),
            "is_toxic": rng.random() < 0.12, "interview_score": round(rng.uniform(0.4, 0.95), 2),
        })
    save_sessions()
    return {
        "listing_id": listing["id"], "role": role,
        "new_applicants": new_candidates,
        "total_candidates": len(state.candidate_pool),
        "message": f"Job posted for {role}. {new_candidates} new applicants added."
    }

@mcp.tool()
def conduct_interview(episode_id: str, agent_role: str, candidate_id: str, questions: str) -> dict:
    """
    Interview a candidate from the pool. Reveals performance but not toxic flag.

    Args:
        episode_id: Unique identifier for the session.
        agent_role: Must be 'people' or 'ceo'.
        candidate_id: ID of the candidate.
        questions: Interview questions/approach.
    """
    if agent_role not in ("people", "ceo"):
        return {"error": "Unauthorized. Only People and CEO can conduct interviews."}
    state = _get_state(episode_id)
    candidate = next((c for c in state.candidate_pool if c["id"] == candidate_id), None)
    if not candidate:
        return {"error": f"Candidate {candidate_id} not found."}
    rng = _get_rng(episode_id)
    performance = candidate["interview_score"] + rng.uniform(-0.1, 0.1)
    performance = max(0.0, min(1.0, performance))
    red_flags = []
    if candidate["is_toxic"] and rng.random() < 0.3:
        red_flags.append("Seemed dismissive of teamwork questions")
    if candidate["skill_level"] < 0.4:
        red_flags.append("Struggled with technical questions")
    return {
        "candidate": candidate["name"], "role": candidate["role"],
        "performance_score": round(performance, 2),
        "skill_assessment": "strong" if candidate["skill_level"] > 0.7 else "adequate" if candidate["skill_level"] > 0.4 else "weak",
        "red_flags": red_flags if red_flags else ["None observed"],
        "recommendation": "Strong hire" if performance > 0.75 else "Consider" if performance > 0.5 else "Pass",
    }

@mcp.tool()
def hold_one_on_one(episode_id: str, agent_role: str, employee_id: str, talking_points: str) -> dict:
    """
    Hold a 1-on-1 meeting with an employee. Reduces burnout and reveals concerns.

    Args:
        episode_id: Unique identifier for the session.
        agent_role: Must be 'people' or 'ceo'.
        employee_id: ID of the employee.
        talking_points: Topics to discuss.
    """
    if agent_role not in ("people", "ceo"):
        return {"error": "Unauthorized. Only People and CEO can hold 1-on-1s."}
    state = _get_state(episode_id)
    emp = next((e for e in state.employees if e.id == employee_id), None)
    if not emp:
        return {"error": f"Employee {employee_id} not found."}
    quality = min(1.0, len(talking_points) / 300)
    emp.morale = min(1.0, emp.morale + quality * 0.08)
    emp.burnout_risk = max(0.0, emp.burnout_risk - quality * 0.05)
    emp.flight_risk = max(0.0, emp.flight_risk - quality * 0.06)
    feedback = []
    if emp.burnout_risk > 0.6:
        feedback.append("Expressed feeling overwhelmed with current workload")
    if emp.flight_risk > 0.5:
        feedback.append("Mentioned exploring other opportunities")
    if emp.morale < 0.4:
        feedback.append("Seems disengaged and frustrated")
    if emp.is_toxic and agent_role == "people":
        feedback.append("Other team members have raised concerns about collaboration style")
    if not feedback:
        feedback.append("Seems happy and engaged with current work")
    save_sessions()
    return {
        "employee": emp.name, "role": emp.role,
        "morale_after": round(emp.morale, 3),
        "burnout_after": round(emp.burnout_risk, 3),
        "feedback": feedback,
        "message": f"1-on-1 with {emp.name} completed."
    }

# ── Reward Endpoint ───────────────────────────────────────────────────────

@mcp.tool()
def get_reward(episode_id: str) -> dict:
    """
    Get the current composite reward score with full breakdown.

    Args:
        episode_id: Unique identifier for the session.
    """
    state = _get_state(episode_id)
    score = compute_reward(state)
    return {
        "day": state.day,
        "reward": score.total,
        "breakdown": score.breakdown(),
        "cumulative": state.cumulative_reward,
        "history_length": len(state.reward_history),
        "is_done": state.is_done(),
    }

# ── ASGI Bridge ─────────────────────────────────────────────────────────────
# This allows openenv.yaml (server.app:app) to work
app = mcp.http_app()

if __name__ == "__main__":
    mcp.run()
