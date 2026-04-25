"""
GENESIS FastAPI Server — The core MCP environment server.

Exposes:
- Environment initialization (reset)
- Daily step advancement (step)
- Tool calling interface (call_tool)
- Rendering/observation (render)
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
import json
import random
import uuid

from .world_state import WorldState, DifficultyLevel, AgentRole, PersonalCrisis
from .world_init import initialize_world
from .event_engine import tick_day
from .reward_engine import compute_reward
from .market_maker import MarketMaker
from .tools import ToolHandler

# ────────────────────────────────────────────────────────────────
# FastAPI Setup
# ────────────────────────────────────────────────────────────────

app = FastAPI(title="GENESIS Startup Gauntlet", version="0.1.0")

# Global state: one episode at a time
current_state: Optional[WorldState] = None
current_rng: Optional[random.Random] = None
tool_handler: Optional[ToolHandler] = None
market_maker: Optional[MarketMaker] = None


# ────────────────────────────────────────────────────────────────
# Request/Response Models
# ────────────────────────────────────────────────────────────────

class ResetRequest(BaseModel):
    difficulty: int = 2  # DifficultyLevel.SEED
    seed: int = 42


class StepRequest(BaseModel):
    pass


class CallToolRequest(BaseModel):
    tool_name: str
    agent_role: str
    kwargs: dict = {}


class RenderRequest(BaseModel):
    mode: str = "full"  # "full", "brief", "observations_only"


class ResetResponse(BaseModel):
    episode_id: str
    day: int
    max_days: int
    difficulty: str
    observations: dict


class StepResponse(BaseModel):
    day: int
    done: bool
    events: list[str]
    observations: dict
    reward: float


class CallToolResponse(BaseModel):
    success: bool
    tool_name: str
    agent_role: str
    result: Any
    error: Optional[str] = None


class RenderResponse(BaseModel):
    observations: dict
    reward_breakdown: dict
    full_state: Optional[dict] = None


# ────────────────────────────────────────────────────────────────
# Health Check
# ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "GENESIS"}


# ────────────────────────────────────────────────────────────────
# Environment API
# ────────────────────────────────────────────────────────────────

@app.post("/reset", response_model=ResetResponse)
def reset_env(req: ResetRequest):
    """Reset the environment and start a new episode."""
    global current_state, current_rng, tool_handler, market_maker

    difficulty = DifficultyLevel(req.difficulty)
    current_rng = random.Random(req.seed)
    current_state = initialize_world(difficulty=difficulty, seed=req.seed)
    tool_handler = ToolHandler(current_state, current_rng)
    market_maker = MarketMaker(current_state, current_rng)

    obs = _get_observations()
    return ResetResponse(
        episode_id=current_state.episode_id,
        day=current_state.day,
        max_days=current_state.max_days,
        difficulty=difficulty.name,
        observations=obs,
    )


@app.post("/step", response_model=StepResponse)
def step_env(req: StepRequest):
    """Advance the environment by one day."""
    global current_state, current_rng

    if current_state is None:
        raise HTTPException(status_code=400, detail="Environment not initialized. Call /reset first.")

    # Tick the world forward
    events = tick_day(current_state, current_rng)

    # Compute reward for this step
    reward_obj = compute_reward(current_state)
    current_state.cumulative_reward += reward_obj.total
    current_state.reward_history.append(reward_obj.total)

    # Check if episode is done
    done = current_state.is_done()

    obs = _get_observations()

    return StepResponse(
        day=current_state.day,
        done=done,
        events=events,
        observations=obs,
        reward=reward_obj.total,
    )


@app.post("/call_tool", response_model=CallToolResponse)
def call_tool_endpoint(req: CallToolRequest):
    """Call a tool on behalf of an agent."""
    global current_state, tool_handler

    if current_state is None:
        raise HTTPException(status_code=400, detail="Environment not initialized. Call /reset first.")

    try:
        agent_role = AgentRole(req.agent_role)
        result = tool_handler.call(
            tool_name=req.tool_name,
            agent_role=agent_role,
            kwargs=req.kwargs,
        )

        return CallToolResponse(
            success=True,
            tool_name=req.tool_name,
            agent_role=req.agent_role,
            result=result,
        )
    except Exception as e:
        return CallToolResponse(
            success=False,
            tool_name=req.tool_name,
            agent_role=req.agent_role,
            result=None,
            error=str(e),
        )


@app.post("/render", response_model=RenderResponse)
def render_env(req: RenderRequest):
    """Render the environment state."""
    if current_state is None:
        raise HTTPException(status_code=400, detail="Environment not initialized.")

    obs = _get_observations()
    reward_obj = compute_reward(current_state)

    response = RenderResponse(
        observations=obs,
        reward_breakdown=reward_obj.breakdown(),
    )

    if req.mode == "full":
        response.full_state = _get_full_state()

    return response


# ────────────────────────────────────────────────────────────────
# Helper Functions
# ────────────────────────────────────────────────────────────────

def _get_observations() -> dict:
    """Get the current observations visible to agents."""
    if current_state is None:
        return {}

    return {
        "day": current_state.day,
        "max_days": current_state.max_days,
        "difficulty": current_state.difficulty.name,
        "cash": round(current_state.cash, 2),
        "runway_days": round(current_state.runway_days(), 1),
        "mrr": round(current_state.mrr, 2),
        "arr": round(current_state.arr(), 2),
        "team_size": len(current_state.employees),
        "customer_count": len(current_state.customers),
        "avg_customer_satisfaction": round(
            sum(c.satisfaction for c in current_state.customers) / max(len(current_state.customers), 1), 2
        ),
        "product_maturity": round(current_state.product_maturity, 2),
        "tech_debt": round(current_state.tech_debt, 2),
        "uptime": round(current_state.uptime, 3),
        "team_avg_morale": round(current_state.team_avg_morale(), 2),
        "team_avg_burnout": round(current_state.team_avg_burnout(), 2),
        "cofounder_morale": {k: round(v, 2) for k, v in current_state.cofounder_morale.items()},
        "cofounder_alignment": round(current_state.cofounder_alignment, 2),
        "active_crises": len([c for c in current_state.personal_crises if not c.resolved]),
        "series_a_closed": current_state.series_a_closed,
    }


def _get_full_state() -> dict:
    """Get the complete internal state (for debugging/analysis)."""
    if current_state is None:
        return {}

    return {
        "episode_id": current_state.episode_id,
        "day": current_state.day,
        "cash": current_state.cash,
        "burn_rate_daily": current_state.burn_rate_daily,
        "mrr": current_state.mrr,
        "employees": [
            {
                "name": e.name,
                "role": e.role,
                "skill_level": e.skill_level,
                "morale": e.morale,
                "burnout_risk": e.burnout_risk,
                "is_toxic": e.is_toxic,
                "flight_risk": e.flight_risk,
            }
            for e in current_state.employees
        ],
        "customers": [
            {
                "name": c.name,
                "arr": c.arr,
                "satisfaction": c.satisfaction,
                "churn_risk": c.churn_risk,
            }
            for c in current_state.customers
        ],
        "competitors": [
            {
                "name": c.name,
                "strength": c.strength,
                "funding": c.funding,
                "recent_move": c.recent_move,
            }
            for c in current_state.competitors
        ],
        "pending_features": [
            {
                "name": f.name,
                "complexity": f.complexity,
                "engineers_assigned": f.engineers_assigned,
                "days_remaining": f.days_remaining,
            }
            for f in current_state.pending_features
        ],
        "company_brain": current_state.company_brain,
        "active_crises": [
            {
                "id": c.id,
                "target_role": c.target_role.value,
                "description": c.description,
                "severity": c.severity,
                "resolved": c.resolved,
            }
            for c in current_state.personal_crises
            if not c.resolved
        ],
        "messages": [
            {
                "from": m.from_role.value,
                "to": m.to_role.value,
                "subject": m.subject,
                "day": m.day,
            }
            for m in current_state.messages[-10:]  # Last 10 messages
        ],
        "cumulative_reward": current_state.cumulative_reward,
    }


def main():
    """Entry point for running the server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
