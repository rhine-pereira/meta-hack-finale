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
    
    # Persistent update
    save_sessions()
    
    # Filter for the role
    role_enum = AgentRole(agent_role)
    observation = _filter_state(state, role_enum)
    
    # Role-specific inbox: filter crises for this role
    active_crises = [c for c in state.personal_crises if not c.resolved and c.target_role == role_enum]
    
    return {
        "day": state.day,
        "world_events": events,
        "role_observation": observation,
        "active_crises": active_crises,
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

# ── Task 10: Wire __init__.py & Verify ──────────────────────────────────────

# ── ASGI Bridge ─────────────────────────────────────────────────────────────
# This allows openenv.yaml (server.app:app) to work
app = mcp.http_app()

if __name__ == "__main__":
    mcp.run()
