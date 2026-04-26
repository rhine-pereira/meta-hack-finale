"""
GENESIS MCP Server — The main entry point.
Exposes tools to LLM agents for co-founding and operating a startup.
"""

import asyncio
import json
import os
import pickle
import random
import uuid
from collections import deque
from typing import Dict, List, Any
from datetime import datetime
from fastmcp import FastMCP

from .world_state import WorldState, DifficultyLevel, AgentRole
from .world_init import initialize_world
from .event_engine import tick_day
from .reward_engine import compute_reward
from .market_maker import MarketMaker
from .proof.canonical import hash_state
from .proof.merkle import sha256_leaf, build_merkle_root
from .proof.solana_client import SolanaProofClient
from .genome_utils import aggregate_genome, generate_radar_chart, generate_comparison_chart

# ── Global Registry ──────────────────────────────────────────────────────────
from fastapi import Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Create the FastMCP instance
mcp = FastMCP("genesis")

# Get the underlying FastAPI app from FastMCP
app = mcp.http_app()

# Serve exported artifacts (Founder Genome cards, etc.)
# This enables the UI to fetch e.g. /exports/founder_genomes/genome_<model>_<ts>.png
os.makedirs("exports", exist_ok=True)
app.mount("/exports", StaticFiles(directory="exports"), name="exports")

# Add CORS for local training compliance
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["mcp-session-id"],
)

from starlette.middleware.base import BaseHTTPMiddleware

class SessionIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        session_id = request.headers.get("mcp-session-id")
        response = await call_next(request)
        if "mcp-session-id" not in response.headers and session_id:
            response.headers["mcp-session-id"] = session_id
        return response

app.add_middleware(SessionIdMiddleware)

from starlette.responses import JSONResponse, StreamingResponse

async def health(request: Request):
    return JSONResponse({"status": "ok"})

app.router.add_route("/health", health, methods=["GET"])

# ── Demo Event Stream (Judge UI) ──────────────────────────────────────────────
DEMO_EVENTS = deque(maxlen=500)
DEMO_UPDATE_EVENT = asyncio.Event()

async def log_demo_event(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
        
    event = {
        "id": len(DEMO_EVENTS) + 1,
        "ts": datetime.now().isoformat(),
        "phase": data.get("phase"),
        "phase_title": data.get("phase_title"),
        "step": data.get("step"),
        "detail": data.get("detail"),
        "status": data.get("status", "info"),
        "data": data.get("data", {})
    }
    DEMO_EVENTS.append(event)
    DEMO_UPDATE_EVENT.set()
    DEMO_UPDATE_EVENT.clear()
    return JSONResponse({"status": "ok", "event_id": event["id"]})

async def get_demo_state(request: Request):
    return JSONResponse({
        "events": list(DEMO_EVENTS),
        "current_phase": DEMO_EVENTS[-1]["phase"] if DEMO_EVENTS else 0,
        "phase_title": DEMO_EVENTS[-1]["phase_title"] if DEMO_EVENTS else None
    })

async def demo_events(request: Request):
    async def event_generator():
        while True:
            await DEMO_UPDATE_EVENT.wait()
            if await request.is_disconnected():
                break
            
            if DEMO_EVENTS:
                latest = DEMO_EVENTS[-1]
                yield f"data: {json.dumps(latest)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

app.router.add_route("/demo/log", log_demo_event, methods=["POST"])
app.router.add_route("/demo/state", get_demo_state, methods=["GET"])
app.router.add_route("/demo/events", demo_events, methods=["GET"])

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


def _execute_pivot(state: WorldState, new_direction: str, rationale: str) -> None:
    """Apply pivot side effects once a ballot is approved or overridden."""
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

# ── Tasks 1 & 2: Session Lifecycle ───────────────────────────────────────────

@mcp.tool()
def reset(episode_id: str, difficulty: int = 4, seed: int = 42, 
          model_id: str = None, model_provider: str = None, model_version: str = None) -> dict:
    """
    Initialize or reset a startup simulation episode.
    
    Args:
        episode_id: Unique identifier for the session.
        difficulty: 1 (Tutorial) to 5 (Nightmare). Default is 4 (Gauntlet).
        seed: Random seed for reproducibility.
        model_id: (USP3) Identifier for the model being benchmarked.
        model_provider: (USP3) Optional provider name.
        model_version: (USP3) Optional model version.
    """
    # Map int difficulty to Enum
    try:
        diff_enum = DifficultyLevel(difficulty)
    except ValueError:
        diff_enum = DifficultyLevel.GAUNTLET

    # Initialize state and RNG
    state = initialize_world(difficulty=diff_enum, seed=seed)
    # Ensure episode_id matches requested ID
    state.episode_id = episode_id
    state.seed = seed
    state.model_id = model_id
    state.model_provider = model_provider
    state.model_version = model_version
    
    # Initialize proof with Day 0 state
    day0_hash = hash_state(state)
    state.proof_leaves = [sha256_leaf(day0_hash).hex()]
    
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
    state.reward_breakdown_history.append(score.breakdown())
    
    # Update proof leaves
    current_hash = hash_state(state)
    state.proof_leaves.append(sha256_leaf(current_hash).hex())
    
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
    
    # Ghost Founder context: tell the AI which roles are currently
    # human-controlled and surface the most recent human ghost actions
    # so the AI can adapt its decisions to a heterodox co-founder.
    controllers = dict(getattr(state, "role_controllers", {}))
    human_roles = [r for r, c in controllers.items() if c == "human"]
    recent_human_actions = list(getattr(state, "human_action_log", []))[-10:]
    ghost_note = None
    if human_roles:
        ghost_note = (
            "Heads up: a human ghost-founder currently controls "
            + ", ".join(r.upper() for r in human_roles)
            + ". Their decision style may diverge from yours — read their recent "
            "actions and adapt rather than assume."
        )

    return {
        "day": state.day,
        "world_events": events,
        "role_observation": observation,
        "active_crises": active_crises,
        "reward": score.total,
        "is_done": state.is_done(),
        "role_controllers": controllers,
        "human_roles": human_roles,
        "recent_human_actions": recent_human_actions,
        "ghost_founder_note": ghost_note,
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
    
    # Log event for consequence tracking
    event_id = str(uuid.uuid4())
    state.event_history.append({
        "id": event_id, "type": "feature_start", "day": state.day, 
        "desc": f"Started building {name} ({complexity})", "feat_name": name
    })
    
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
    
    start_day = state.day + 14
    pending_hire = {
        "name": candidate["name"],
        "role": role,
        "skill_level": candidate["skill_level"],
        "is_toxic": candidate["is_toxic"],
        "annual_salary": max(int(salary), 1),
        "start_day": start_day,
    }

    state.pending_hires.append(pending_hire)
    state.candidate_pool.remove(candidate)

    # Hiring has delayed effect: compensation only starts at onboarding.
    # Log event for consequence tracking
    event_id = str(uuid.uuid4())
    state.event_history.append({
        "id": event_id,
        "type": "hire_offer",
        "day": state.day,
        "desc": f"Offer accepted by {pending_hire['name']} for {role}",
        "start_day": start_day,
        "is_toxic": pending_hire["is_toxic"],
    })
    
    save_sessions()
    
    return {
        "hired": pending_hire["name"],
        "role": role,
        "skill_level": pending_hire["skill_level"],
        "start_day": start_day,
        "days_until_start": 14,
        "message": "Offer accepted. Onboarding completes in 14 days."
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

    import uuid

    state = _get_state(episode_id)
    emp = next((e for e in state.employees if e.id == employee_id), None)
    
    if not emp:
        return {"error": f"Employee {employee_id} not found."}

    if emp.skill_level >= 0.75:
        knowledge_loss = "high"
    elif emp.skill_level >= 0.45:
        knowledge_loss = "medium"
    else:
        knowledge_loss = "low"
    
    state.employees.remove(emp)
    state.cash = max(0.0, state.cash - severance)
    salary_savings = emp.annual_salary / 365.0 if emp.annual_salary > 0 else 250
    state.burn_rate_daily = max(0.0, state.burn_rate_daily - salary_savings)
    
    # Morale hit to the team
    for other in state.employees:
        other.morale = max(0.0, other.morale - 0.07)
    
    # Log event for consequence tracking
    event_id = str(uuid.uuid4())
    state.event_history.append({
        "id": event_id, "type": "fire", "day": state.day, 
        "desc": f"Fired {emp.name}", "entity_id": emp.id
    })
    
    save_sessions()
    
    return {
        "fired": emp.name,
        "knowledge_loss": knowledge_loss,
        "team_morale_after": state.team_avg_morale(),
        "cash_after_severance": state.cash,
        "burn_rate_daily_after": state.burn_rate_daily,
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

    lowered = key.lower()
    if any(token in lowered for token in ("weekly_state", "state_of_company", "weekly_memo")):
        state.last_weekly_memo_day = state.day

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
    
    # Quality scoring — multi-dimensional rubric that rewards empathy,
    # structured action plans, concrete commitments, and appropriate length.
    def score_response(text: str) -> float:
        lower = text.lower()
        word_count = len(text.split())
        s = 0.25  # baseline — any response beats ignoring the crisis

        # Length: reward substantive responses; diminishing returns above ~300 words
        if word_count >= 250:
            s += 0.25
        elif word_count >= 100:
            s += 0.15
        elif word_count >= 40:
            s += 0.05

        # Empathy signals (acknowledging the person's experience)
        empathy_kws = {
            "understand": 0.04, "appreciate": 0.04, "hear you": 0.05,
            "feel": 0.03, "difficult": 0.03, "hard": 0.02,
            "respect": 0.03, "matter": 0.02, "care": 0.03,
        }
        for kw, bonus in empathy_kws.items():
            if kw in lower:
                s += bonus

        # Action & structure signals (concrete next steps)
        action_kws = {
            "plan": 0.05, "steps": 0.05, "step 1": 0.07, "step 2": 0.05,
            "first": 0.03, "second": 0.03, "third": 0.03,
            "action": 0.04, "commit": 0.04, "will": 0.02,
            "schedule": 0.04, "meeting": 0.03, "follow up": 0.05,
            "follow-up": 0.05, "7 days": 0.04, "next week": 0.04,
        }
        for kw, bonus in action_kws.items():
            if kw in lower:
                s += bonus

        # Concrete retention / compensation signals
        retention_kws = {
            "equity": 0.06, "bonus": 0.06, "raise": 0.05, "salary": 0.04,
            "vacation": 0.05, "time off": 0.05, "sabbatical": 0.06,
            "ownership": 0.05, "refresh": 0.05, "vesting": 0.04,
            "role change": 0.04, "promotion": 0.04, "autonomy": 0.03,
        }
        for kw, bonus in retention_kws.items():
            if kw in lower:
                s += bonus

        # Communication signals (transparency, alignment)
        comm_kws = {
            "transparent": 0.03, "open": 0.02, "honest": 0.03,
            "team": 0.02, "together": 0.02, "talk": 0.03, "discuss": 0.03,
            "alignment": 0.03, "cofounder": 0.02, "co-founder": 0.02,
        }
        for kw, bonus in comm_kws.items():
            if kw in lower:
                s += bonus

        # Penalty for vague / dismissive responses
        dismissal_kws = ["just ignore", "not important", "later", "too busy"]
        for kw in dismissal_kws:
            if kw in lower:
                s -= 0.10

        return max(0.0, min(1.0, s))

    score = score_response(response)
    
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
def pivot_company(episode_id: str, agent_role: str, new_direction: str, rationale: str, vote: str = "approve") -> dict:
    """
    Propose or vote on a radical company pivot.

    By default, a pivot executes when there is a majority approval (3/5)
    including the CEO. The CEO can also force execution with vote='override'.

    Args:
        episode_id: Unique identifier for the session.
        agent_role: One of ceo/cto/sales/people/cfo.
        new_direction: The new product/market direction.
        rationale: Why this pivot is necessary.
        vote: approve, reject, or override (CEO only).
    """
    state = _get_state(episode_id)

    try:
        normalized_role = AgentRole(agent_role.lower()).value
    except ValueError:
        return {"error": f"Unknown role '{agent_role}'."}

    vote = vote.lower().strip()
    if vote not in {"approve", "reject", "override"}:
        return {"error": "Invalid vote. Use approve, reject, or override."}

    if vote == "override" and normalized_role != "ceo":
        return {"error": "Only the CEO can use override for a pivot."}

    if state.pivot_in_progress and state.pivot_direction == new_direction:
        return {
            "executed": True,
            "direction": state.pivot_direction,
            "pivot_count": state.pivot_count,
            "message": "Pivot already in progress for this direction.",
        }

    ballot = state.pivot_ballot
    if ballot is None or ballot.get("status") in {"executed", "rejected"}:
        ballot = {
            "new_direction": new_direction,
            "rationale": rationale,
            "proposed_by": normalized_role,
            "created_day": state.day,
            "approvals": [],
            "rejections": [],
            "status": "pending",
        }
        state.pivot_ballot = ballot
    elif ballot.get("new_direction") != new_direction:
        return {
            "error": "An active pivot ballot already exists for a different direction.",
            "active_direction": ballot.get("new_direction"),
        }

    approvals = set(ballot.get("approvals", []))
    rejections = set(ballot.get("rejections", []))
    approvals.discard(normalized_role)
    rejections.discard(normalized_role)

    if vote == "approve":
        approvals.add(normalized_role)
    elif vote == "reject":
        rejections.add(normalized_role)
    else:
        _execute_pivot(state, new_direction, rationale)
        approvals.add(normalized_role)
        ballot["approvals"] = sorted(approvals)
        ballot["rejections"] = sorted(rejections)
        ballot["status"] = "executed"
        ballot["resolved_day"] = state.day
        state.pivot_ballot = ballot
        save_sessions()
        return {
            "executed": True,
            "resolution": "ceo_override",
            "approvals": ballot["approvals"],
            "rejections": ballot["rejections"],
            "direction": new_direction,
            "pivot_count": state.pivot_count,
            "morale_impact": -0.15,
            "message": "Pivot executed via CEO override.",
        }

    ballot["approvals"] = sorted(approvals)
    ballot["rejections"] = sorted(rejections)

    if len(approvals) >= 3 and "ceo" in approvals:
        _execute_pivot(state, new_direction, rationale)
        ballot["status"] = "executed"
        ballot["resolved_day"] = state.day
        state.pivot_ballot = ballot
        save_sessions()
        return {
            "executed": True,
            "resolution": "majority",
            "approvals": ballot["approvals"],
            "rejections": ballot["rejections"],
            "direction": new_direction,
            "pivot_count": state.pivot_count,
            "morale_impact": -0.15,
            "message": "Pivot approved by majority (including CEO) and executed.",
        }

    if len(rejections) >= 3:
        ballot["status"] = "rejected"
        ballot["resolved_day"] = state.day
        state.pivot_ballot = ballot
        save_sessions()
        return {
            "executed": False,
            "status": "rejected",
            "approvals": ballot["approvals"],
            "rejections": ballot["rejections"],
            "message": "Pivot rejected by majority vote.",
        }

    ballot["status"] = "pending"
    state.pivot_ballot = ballot
    save_sessions()
    return {
        "executed": False,
        "status": "pending",
        "approvals": ballot["approvals"],
        "rejections": ballot["rejections"],
        "required_for_execution": "3 approvals including CEO",
        "message": "Pivot vote recorded. Awaiting additional votes.",
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
    # Log event for consequence tracking
    event_id = str(uuid.uuid4())
    state.event_history.append({
        "id": event_id, "type": "deploy", "day": state.day, 
        "desc": f"Deployed v{version}", "success": success, "tech_debt": state.tech_debt
    })
    
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
    listing = {
        "id": str(uuid.uuid4()),
        "role": role,
        "requirements": requirements,
        "salary_range": [salary_min, salary_max],
        "posted_day": state.day,
        "applicants_arrive_day": state.day + 5,
        "applicants_generated": False,
    }
    rng = _get_rng(episode_id)
    listing["pending_applicants_count"] = rng.randint(2, 5)
    state.open_positions.append(listing)
    save_sessions()
    return {
        "listing_id": listing["id"],
        "role": role,
        "new_applicants_now": 0,
        "expected_new_applicants": listing["pending_applicants_count"],
        "applicants_arrive_day": listing["applicants_arrive_day"],
        "total_candidates": len(state.candidate_pool),
        "message": f"Job posted for {role}. Applicants will arrive after a 5-day delay."
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

@mcp.tool()
def list_founder_genomes() -> dict:
    """
    List all model identifiers that have exported Founder Genomes.
    """
    export_dir = "exports/founder_genomes"
    if not os.path.exists(export_dir):
        return {"model_ids": []}
    
    files = os.listdir(export_dir)
    model_ids = set()
    for f in files:
        if f.startswith("genome_") and f.endswith(".json"):
            # Format: genome_modelid_timestamp.json
            parts = f.split("_")
            if len(parts) >= 3:
                model_ids.add(parts[1])
    
    return {"model_ids": sorted(list(model_ids))}

# ── Task 9: Founder Genome (USP 3) ───────────────────────────────────────────

@mcp.tool()
def export_founder_genome(model_id: str, difficulty: int = None) -> dict:
    """
    Aggregate episode data for a model and export its Founder Genome card (JSON + PNG).
    
    Args:
        model_id: Identifier of the model to aggregate.
        difficulty: Optional filter for simulation difficulty.
    """
    states = [s for s in SESSIONS.values() if s.model_id == model_id]
    if difficulty:
        states = [s for s in states if int(s.difficulty) == difficulty]
    
    if not states:
        return {"error": f"No sessions found for model '{model_id}'."}
    
    genome = aggregate_genome(states)
    if not genome:
        return {"error": "No reward breakdown history found in sessions."}
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = "exports/founder_genomes"
    json_path = f"{export_dir}/genome_{model_id}_{timestamp}.json"
    png_path = f"{export_dir}/genome_{model_id}_{timestamp}.png"
    
    os.makedirs(export_dir, exist_ok=True)
    
    with open(json_path, "w") as f:
        json.dump(genome, f, indent=2)
    
    generate_radar_chart(genome, model_id, png_path)
    
    return {
        "model_id": model_id,
        "genome": genome,
        "artifacts": {
            "json": json_path,
            "png": png_path
        }
    }

@mcp.tool()
def compare_founder_genomes(model_ids: List[str]) -> dict:
    """
    Compare multiple models and export a combined comparison card.
    
    Args:
        model_ids: List of model identifiers to compare.
    """
    comparison = {}
    valid_ids = []
    
    for mid in model_ids:
        states = [s for s in SESSIONS.values() if s.model_id == mid]
        if not states:
            continue
        genome = aggregate_genome(states)
        if genome:
            comparison[mid] = genome
            valid_ids.append(mid)
    
    if not comparison:
        return {"error": "No valid genomes found for comparison."}
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = "exports/founder_genomes"
    comparison_id = "_vs_".join(valid_ids[:3]) # Limit name length
    png_path = f"{export_dir}/comparison_{comparison_id}_{timestamp}.png"
    
    generate_comparison_chart(comparison, png_path)
    
    return {
        "compared_models": valid_ids,
        "comparison": comparison,
        "artifacts": {
            "png": png_path
        }
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
    rng = _get_rng(episode_id)
    score = compute_reward(state)
    
    # Observe performance and get weaknesses for self-play
    mm = MarketMaker(state, rng)
    mm.observe_performance(score.total)
    
    return {
        "day": state.day,
        "reward": score.total,
        "breakdown": score.breakdown(),
        "weaknesses": list(mm.weaknesses),
        "cumulative": state.cumulative_reward,
        "history_length": len(state.reward_history),
        "is_done": state.is_done(),
    }

# ── Task 10: Blockchain & Proofs ───────────────────────────────────────────

@mcp.tool()
async def commit_simulation_proof(episode_id: str, dry_run: bool = False) -> dict:
    """
    Compute the Merkle root of all state hashes so far and commit it to Solana.
    This creates a tamper-evident, verifiable proof of the simulation's integrity.
    
    Args:
        episode_id: Unique identifier for the session.
        dry_run: If true, compute the root but don't send the transaction.
    """
    state = _get_state(episode_id)
    
    if not state.proof_leaves:
        return {"success": False, "error": "No state hashes recorded yet."}
    
    # Convert hex leaves back to bytes
    leaf_bytes = [bytes.fromhex(l) for l in state.proof_leaves]
    merkle_root = build_merkle_root(leaf_bytes)
    
    client = SolanaProofClient()
    
    if dry_run:
        episode_fingerprint = client.get_episode_fingerprint(state.episode_id, state.seed)
        # Derive PDA when the Solana SDK is available; otherwise return a
        # clear, non-fatal payload so the dry-run still proves we have a valid
        # Merkle root and the env is wired up correctly.
        pda_str: str
        try:
            pda_str = str(client.derive_checkpoint_pda(
                episode_fingerprint, state.last_checkpoint_index
            ))
            pda_available = True
        except RuntimeError as exc:
            pda_str = f"<unavailable: {exc}>"
            pda_available = False
        return {
            "success": True,
            "dry_run": True,
            "merkle_root_hex": merkle_root.hex(),
            "episode_fingerprint_hex": episode_fingerprint.hex(),
            "leaf_count": len(state.proof_leaves),
            "checkpoint_index": state.last_checkpoint_index,
            "pda": pda_str,
            "pda_available": pda_available,
            "solana_sdk_available": client.is_configured() or pda_available,
            "day": state.day,
            "message": (
                "Dry-run successful: Merkle root computed locally."
                if not pda_available
                else "Dry-run successful: Merkle root + on-chain PDA derived."
            ),
        }
    
    # Execute on-chain commit
    result = await client.commit_checkpoint(
        episode_id=state.episode_id,
        seed=state.seed,
        merkle_root=merkle_root,
        checkpoint_index=state.last_checkpoint_index,
        day=state.day,
        leaf_count=len(state.proof_leaves)
    )
    
    if result.get("success"):
        state.last_onchain_signature = result["signature"]
        state.last_checkpoint_index += 1
        save_sessions()
        
    return result

@mcp.tool()
def get_simulation_proof_status(episode_id: str) -> dict:
    """
    Get the current status of on-chain verifiable proofs for this simulation.
    
    Args:
        episode_id: Unique identifier for the session.
    """
    state = _get_state(episode_id)
    
    client = SolanaProofClient()
    episode_fingerprint = client.get_episode_fingerprint(state.episode_id, state.seed)
    
    return {
        "episode_id": state.episode_id,
        "day": state.day,
        "leaf_count": len(state.proof_leaves),
        "last_checkpoint_index": state.last_checkpoint_index,
        "last_signature": state.last_onchain_signature,
        "explorer_url": f"https://explorer.solana.com/tx/{state.last_onchain_signature}?cluster=devnet" if state.last_onchain_signature else None,
        "is_solana_configured": client.is_configured(),
        "episode_fingerprint_hex": episode_fingerprint.hex()
    }

# ── Dead Startup Resurrection Engine ─────────────────────────────────────────

@mcp.tool()
def list_postmortem_scenarios() -> dict:
    """
    List all available real-world startup failure scenarios for the Resurrection Engine.
    Returns a catalogue of companies whose timelines can be loaded as simulation seeds.
    """
    from .postmortem_scenarios import list_scenarios
    return {
        "scenarios": list_scenarios(),
        "message": (
            "Use 'load_postmortem_scenario' with a scenario_id to replay a startup's "
            "fatal decision points. The AI agents will face the same forks as the real founders."
        )
    }


@mcp.tool()
def load_postmortem_scenario(episode_id: str, scenario_id: str) -> dict:
    """
    Load a real-world startup failure as a simulation seed into an existing episode.
    This injects the historical ForkPoints as PersonalCrisis events that will fire
    at the specified simulation days, allowing AI agents to rewrite history.

    Args:
        episode_id: Existing session to inject the scenario into.
        scenario_id: One of: quibi, jawbone, juicero, wework, theranos
    """
    from .postmortem_scenarios import get_scenario
    state = _get_state(episode_id)

    scenario = get_scenario(scenario_id)
    if not scenario:
        from .postmortem_scenarios import list_scenarios
        valid = [s["id"] for s in list_scenarios()]
        return {"error": f"Unknown scenario '{scenario_id}'. Valid options: {valid}"}

    # Tag the state with the scenario
    state.postmortem_scenario_id = scenario_id

    # Apply market condition overrides
    mc = scenario.market_conditions
    if "total_tam" in mc:
        state.total_tam = mc["total_tam"]
    if "market_growth_rate" in mc:
        state.market_growth_rate = mc["market_growth_rate"]

    # Apply team profile overrides
    tp = scenario.team_profile
    if "cofounder_alignment" in tp:
        state.cofounder_alignment = tp["cofounder_alignment"]
    if "avg_morale" in tp:
        for role in state.cofounder_morale:
            state.cofounder_morale[role] = tp["avg_morale"]
    if "burn_rate_multiplier" in tp:
        state.burn_rate_daily = state.burn_rate_daily * tp["burn_rate_multiplier"]

    # Apply funding constraints (set starting cash based on first funding round)
    if scenario.funding_history:
        first_round = scenario.funding_history[0]
        state.cash = max(state.cash, first_round["amount"] * 0.3)  # Simulate pre-burn cash

    # Encode fork points as lightweight dicts for the state
    state.postmortem_fork_points = [
        {
            "day": fp.day,
            "title": fp.title,
            "context": fp.context,
            "what_founders_did": fp.what_founders_did,
            "known_outcome": fp.known_outcome,
            "severity": fp.severity,
            "target_role": fp.target_role,
            "category": fp.category,
        }
        for fp in scenario.fatal_decisions
    ]
    state.postmortem_triggered_forks = []
    state.ai_decisions_at_forks = []

    # Seed the company brain with scenario context
    state.company_brain["postmortem_company"] = scenario.company_name
    state.company_brain["postmortem_context"] = (
        f"You are re-running {scenario.company_name} ({scenario.year_founded}-{scenario.year_failed}). "
        f"Tagline: {scenario.tagline}. "
        f"Historical failure: {scenario.failure_summary[:300]}"
    )

    save_sessions()

    return {
        "scenario_loaded": scenario.company_name,
        "scenario_id": scenario_id,
        "company": scenario.company_name,
        "tagline": scenario.tagline,
        "total_funding_raised": scenario.total_funding_raised,
        "fork_points_loaded": len(scenario.fatal_decisions),
        "fork_schedule": [
            {"day": fp.day, "title": fp.title, "target_role": fp.target_role}
            for fp in scenario.fatal_decisions
        ],
        "message": (
            f"Scenario '{scenario.company_name}' loaded. "
            f"{len(scenario.fatal_decisions)} historical fork points will fire during the simulation. "
            f"When a fork arrives, the target agent will receive it as a personal crisis. "
            f"Their response will be logged for the Resurrection Report."
        )
    }


@mcp.tool()
def record_fork_decision(episode_id: str, agent_role: str, crisis_id: str, decision_summary: str) -> dict:
    """
    Record an agent's decision at a historical ForkPoint for the Resurrection Report.
    Call this alongside handle_personal_crisis when responding to a HISTORICAL FORK crisis.

    Args:
        episode_id: Session identifier.
        agent_role: The role making the decision.
        crisis_id: The crisis ID from the active_crises list (must be a fork-point crisis).
        decision_summary: A clear description of what the AI agent decided to do.
    """
    state = _get_state(episode_id)

    # Find the matching triggered fork
    matching_fork = next(
        (f for f in state.postmortem_triggered_forks if f.get("crisis_id") == crisis_id),
        None
    )
    if not matching_fork:
        return {
            "error": f"Crisis '{crisis_id}' is not a historical fork point, or was not yet triggered.",
            "hint": "Only use this tool for crises tagged as [HISTORICAL FORK] in their description."
        }

    # Record the AI decision
    existing = next(
        (d for d in state.ai_decisions_at_forks if d.get("crisis_id") == crisis_id),
        None
    )
    if existing:
        existing["response"] = decision_summary
        existing["day_decided"] = state.day
    else:
        state.ai_decisions_at_forks.append({
            "crisis_id": crisis_id,
            "fork_title": matching_fork["title"],
            "day": matching_fork["day"],
            "agent_role": agent_role,
            "response": decision_summary,
            "day_decided": state.day,
        })

    save_sessions()

    return {
        "recorded": True,
        "fork_title": matching_fork["title"],
        "historical_choice": matching_fork["what_founders_did"][:200],
        "message": (
            "Decision recorded. This will be compared against the real founders' choice "
            "in the final Resurrection Report."
        )
    }


@mcp.tool()
def get_resurrection_report(episode_id: str) -> dict:
    """
    Generate the Resurrection Report for a postmortem scenario episode.
    Returns a side-by-side comparison of real founder decisions vs AI agent decisions,
    with projected outcome deltas and an overall verdict.

    Args:
        episode_id: Session identifier (must have a postmortem scenario loaded).
    """
    from .postmortem_scenarios import get_scenario
    from .resurrection_engine import generate_resurrection_report

    state = _get_state(episode_id)

    if not state.postmortem_scenario_id:
        return {
            "error": "No postmortem scenario loaded for this episode.",
            "hint": "Call 'load_postmortem_scenario' first, then run the simulation."
        }

    scenario = get_scenario(state.postmortem_scenario_id)
    if not scenario:
        return {"error": f"Scenario '{state.postmortem_scenario_id}' not found in registry."}

    report = generate_resurrection_report(state, scenario)
    return report

# ── USP 2: Ghost Founder (Human-in-the-Loop Takeover) ───────────────────────

_VALID_CONTROLLERS = {"ai", "human"}
_VALID_ROLES = {"ceo", "cto", "sales", "people", "cfo"}


def _ensure_role_controllers(state: WorldState) -> dict:
    """Backfill role_controllers on legacy sessions that predate the field."""
    if not getattr(state, "role_controllers", None):
        state.role_controllers = {r: "ai" for r in _VALID_ROLES}
    if not hasattr(state, "human_action_log") or state.human_action_log is None:
        state.human_action_log = []
    return state.role_controllers


@mcp.tool()
def set_role_controller(episode_id: str, role: str, controller: str) -> dict:
    """
    Take or release human control of one of the five co-founder roles.

    While a role is set to 'human', the training/inference loop should
    skip auto tool calls for that role. The frontend "Ghost Founder"
    console drives that role on the human's behalf instead.

    Args:
        episode_id: Session identifier.
        role: ceo, cto, sales, people, or cfo.
        controller: 'human' to take control, 'ai' to release.
    """
    role = role.lower().strip()
    controller = controller.lower().strip()
    if role not in _VALID_ROLES:
        return {"error": f"Unknown role '{role}'."}
    if controller not in _VALID_CONTROLLERS:
        return {"error": f"controller must be one of {_VALID_CONTROLLERS}."}

    state = _get_state(episode_id)
    controllers = _ensure_role_controllers(state)
    previous = controllers.get(role, "ai")
    controllers[role] = controller

    state.human_action_log.append({
        "day": state.day,
        "role": role,
        "action": "take_control" if controller == "human" else "release_control",
        "details": {"previous": previous, "controller": controller},
    })

    save_sessions()

    return {
        "role": role,
        "controller": controller,
        "previous_controller": previous,
        "role_controllers": dict(controllers),
        "day": state.day,
        "message": (
            f"Ghost-founder is now driving {role.upper()}."
            if controller == "human"
            else f"AI has resumed control of {role.upper()}."
        ),
    }


@mcp.tool()
def get_role_controllers(episode_id: str) -> dict:
    """
    Inspect which roles are currently AI-driven vs human-driven, plus a
    rolling tail of human ghost-founder actions taken this episode.

    Args:
        episode_id: Session identifier.
    """
    state = _get_state(episode_id)
    controllers = _ensure_role_controllers(state)
    return {
        "day": state.day,
        "role_controllers": dict(controllers),
        "human_roles": [r for r, c in controllers.items() if c == "human"],
        "human_action_log": list(state.human_action_log[-25:]),
        "human_action_count": len(state.human_action_log),
    }


@mcp.tool()
def log_human_action(episode_id: str, role: str, action: str, details: str = "") -> dict:
    """
    Record an action taken by the human ghost-founder. The frontend calls
    this on every decision (build feature, send message, hire, negotiate,
    handle crisis, etc.) so the AI co-founders can see what the human did
    and adapt at the next briefing.

    Args:
        episode_id: Session identifier.
        role: The role the human is currently driving.
        action: Short label, e.g. 'build_feature', 'pivot_company', 'send_message'.
        details: Optional free-form details (string-serialisable).
    """
    role = role.lower().strip()
    if role not in _VALID_ROLES:
        return {"error": f"Unknown role '{role}'."}

    state = _get_state(episode_id)
    _ensure_role_controllers(state)

    if state.role_controllers.get(role) != "human":
        # Allow logging anyway but flag — useful for debugging.
        warning = (
            f"Note: {role} is currently AI-controlled; logging anyway."
        )
    else:
        warning = None

    entry = {
        "day": state.day,
        "role": role,
        "action": action,
        "details": details if isinstance(details, str) else str(details),
    }
    state.human_action_log.append(entry)
    save_sessions()

    return {
        "logged": True,
        "entry": entry,
        "human_action_count": len(state.human_action_log),
        "warning": warning,
    }


# ── USP 4: On-Demand ML Model Inference ──────────────────────────────────────
#
# These tools load the genesis_final LoRA adapter once into a process-level
# singleton and expose it as callable MCP tools.  The adapter is loaded lazily
# on first use so the server starts instantly even without GPU / large RAM.

_ML_MODEL = None        # PeftModel once loaded
_ML_TOKENIZER = None    # Qwen tokenizer once loaded
_ML_LOAD_ERROR: str | None = None   # Error message if loading failed


def _ensure_ml_model():
    """Lazily load the LoRA adapter.  No-op if already loaded or failed."""
    global _ML_MODEL, _ML_TOKENIZER, _ML_LOAD_ERROR

    if _ML_MODEL is not None or _ML_LOAD_ERROR is not None:
        return

    adapter_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "models", "genesis_final",
    )
    if not os.path.isdir(adapter_path):
        _ML_LOAD_ERROR = (
            f"Adapter directory not found: {adapter_path}. "
            "Run training first or place the adapter at models/genesis_final/."
        )
        return

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel

        base_model = "Qwen/Qwen2.5-3B-Instruct"
        device_map = "auto" if torch.cuda.is_available() else None
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            base_model,
            device_map=device_map,
            torch_dtype=dtype,
            low_cpu_mem_usage=True,
            trust_remote_code=True,
        )
        model = PeftModel.from_pretrained(model, adapter_path)
        model.eval()

        _ML_MODEL = model
        _ML_TOKENIZER = tokenizer

    except Exception as exc:
        _ML_LOAD_ERROR = f"Failed to load ML model: {exc}"


@mcp.tool()
def ml_model_status() -> dict:
    """
    Check whether the genesis_final LoRA adapter is loaded and ready.

    Returns loading status, device info, and parameter counts.
    """
    _ensure_ml_model()
    if _ML_LOAD_ERROR:
        return {"loaded": False, "error": _ML_LOAD_ERROR}

    if _ML_MODEL is None:
        return {"loaded": False, "status": "not_attempted"}

    try:
        import torch
        total = sum(p.numel() for p in _ML_MODEL.parameters()) / 1e6
        trainable = sum(p.numel() for p in _ML_MODEL.parameters() if p.requires_grad) / 1e6
        device = str(next(_ML_MODEL.parameters()).device)
    except Exception:
        total = trainable = 0.0
        device = "unknown"

    return {
        "loaded": True,
        "base_model": "Qwen/Qwen2.5-3B-Instruct",
        "adapter": "genesis_final",
        "total_params_M": round(total, 1),
        "trainable_params_M": round(trainable, 1),
        "device": device,
    }


@mcp.tool()
def ml_generate_decision(
    episode_id: str,
    agent_role: str,
    max_new_tokens: int = 200,
    temperature: float = 0.7,
    execute: bool = True,
) -> dict:
    """
    Use the fine-tuned genesis_final LoRA model to generate and (optionally)
    execute a tool call for the given agent role in the current episode.

    The model reads the latest daily briefing, builds a role-specific prompt
    using the Qwen chat template, generates a JSON tool call, and executes it
    against the simulation state.

    Args:
        episode_id:      Existing session identifier.
        agent_role:      ceo, cto, sales, people, or cfo.
        max_new_tokens:  Max tokens to generate (default 200).
        temperature:     Sampling temperature (default 0.7).
        execute:         If True (default), execute the generated tool call.
                         Set to False to preview without side effects.
    """
    _ensure_ml_model()
    if _ML_LOAD_ERROR:
        return {"success": False, "error": _ML_LOAD_ERROR}
    if _ML_MODEL is None:
        return {"success": False, "error": "ML model not loaded."}

    valid_roles = {"ceo", "cto", "sales", "people", "cfo"}
    if agent_role not in valid_roles:
        return {"success": False, "error": f"Unknown role '{agent_role}'."}

    state = _get_state(episode_id)

    # Build a briefing dict from the current state (no tick — read-only snapshot)
    from .role_views import get_filtered_view
    from .world_state import AgentRole as _AgentRole

    role_enum = _AgentRole(agent_role)
    role_obs = get_filtered_view(state, role_enum)
    active_crises = [
        {"id": c.id, "severity": c.severity, "description": c.description,
         "target_role": c.target_role.value}
        for c in state.personal_crises if not c.resolved and c.target_role == role_enum
    ]
    briefing = {
        "day": state.day,
        "world_events": [],
        "role_observation": role_obs,
        "active_crises": active_crises,
        "reward": state.cumulative_reward,
        "is_done": state.is_done(),
    }

    # Import prompt builder + generator from ml_inference (no circular import —
    # ml_inference only imports from client, not from server)
    try:
        from ml_inference import build_prompt, generate_tool_call, execute_tool_call
    except ImportError as exc:
        return {"success": False, "error": f"Could not import ml_inference: {exc}"}

    prompt = build_prompt(agent_role, briefing, _ML_TOKENIZER)

    completion, tool_call = generate_tool_call(
        _ML_MODEL,
        _ML_TOKENIZER,
        prompt,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
    )

    result = None
    execution_error = None
    if execute and tool_call:
        # Map tool names to the Python functions defined in this module.
        # This avoids any HTTP round-trip or internal MCP registry lookups.
        _TOOL_MAP = {
            "make_decision": make_decision,
            "build_feature": build_feature,
            "write_company_brain": write_company_brain,
            "read_company_brain": read_company_brain,
            "check_bank_balance": check_bank_balance,
            "check_team_morale": check_team_morale,
            "analyze_market": analyze_market,
            "send_message": send_message,
            "hire_candidate": hire_candidate,
            "fire_employee": fire_employee,
            "negotiate_with_investor": negotiate_with_investor,
            "handle_personal_crisis": handle_personal_crisis,
            "pivot_company": pivot_company,
            "deploy_to_production": deploy_to_production,
            "run_load_test": run_load_test,
            "review_codebase_health": review_codebase_health,
            "send_customer_email": send_customer_email,
            "update_crm": update_crm,
            "run_competitive_analysis": run_competitive_analysis,
            "create_financial_model": create_financial_model,
            "send_investor_update": send_investor_update,
            "post_job_listing": post_job_listing,
            "conduct_interview": conduct_interview,
            "hold_one_on_one": hold_one_on_one,
            "get_company_state": get_company_state,
        }

        class _DirectEnv:
            """Calls tool functions directly without HTTP."""
            def call_tool(self_inner, name: str, **kwargs):
                fn = _TOOL_MAP.get(name)
                if fn is None:
                    raise ValueError(f"Tool '{name}' not found in direct dispatch map.")
                return fn(**kwargs)

        try:
            direct_env = _DirectEnv()
            result = execute_tool_call(
                direct_env, episode_id, agent_role, tool_call, briefing, verbose=False
            )
        except Exception as exc:
            execution_error = str(exc)

    return {
        "success": True,
        "role": agent_role,
        "day": state.day,
        "generated_tool": tool_call.get("tool") if tool_call else None,
        "generated_args": tool_call.get("args") if tool_call else None,
        "raw_completion": completion[:500],
        "executed": execute and tool_call is not None and execution_error is None,
        "execution_result": result,
        "execution_error": execution_error,
    }


# ── ASGI Bridge ─────────────────────────────────────────────────────────────
# This allows openenv.yaml (server.app:app) to work
if __name__ == "__main__":
    mcp.run()
