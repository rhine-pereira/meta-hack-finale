"""Regression tests for GENESIS spec-alignment mechanics."""

import uuid
import importlib

from server import app as fastapi_app
from server.world_init import initialize_world
from server.world_state import DifficultyLevel

server_app = importlib.import_module("server.app")


def _episode_id() -> str:
    return f"test-{uuid.uuid4()}"


def _reset_episode(difficulty: int = 4) -> str:
    episode_id = _episode_id()
    server_app.reset(episode_id=episode_id, difficulty=difficulty, seed=42)
    return episode_id


def test_exported_app_keeps_health_and_mcp_routes():
    paths = {route.path for route in fastapi_app.router.routes if hasattr(route, "path")}
    assert "/mcp" in paths
    assert "/health" in paths


def test_reset_defaults_to_gauntlet_horizon():
    result = server_app.reset(episode_id=_episode_id(), seed=42)
    assert result["difficulty"] == "GAUNTLET"
    assert result["max_days"] == 540


def test_world_init_scales_candidate_and_customer_counts():
    state = initialize_world(difficulty=DifficultyLevel.NIGHTMARE, seed=42)
    assert len(state.candidate_pool) == 50
    assert len(state.customers) == 200
    assert len(state.investors) == 12


def test_job_listing_applicants_arrive_after_delay():
    episode_id = _reset_episode(difficulty=2)
    before_candidates = len(server_app._get_state(episode_id).candidate_pool)

    listing = server_app.post_job_listing(
        episode_id=episode_id,
        agent_role="people",
        role="Data Engineer",
        requirements="Python, SQL, ETL",
        salary_min=100000,
        salary_max=180000,
    )

    assert listing["new_applicants_now"] == 0

    for _ in range(4):
        server_app.get_daily_briefing(episode_id=episode_id, agent_role="people")

    assert len(server_app._get_state(episode_id).candidate_pool) == before_candidates

    server_app.get_daily_briefing(episode_id=episode_id, agent_role="people")
    assert len(server_app._get_state(episode_id).candidate_pool) > before_candidates


def test_hire_onboards_after_delay_and_increases_burn():
    episode_id = _reset_episode(difficulty=2)
    state = server_app._get_state(episode_id)
    candidate = state.candidate_pool[0]

    before_employees = len(state.employees)
    before_burn = state.burn_rate_daily

    offer = server_app.hire_candidate(
        episode_id=episode_id,
        agent_role="people",
        candidate_id=candidate["id"],
        role=candidate["role"],
        salary=candidate["salary_ask"],
    )

    assert offer["days_until_start"] == 14
    state = server_app._get_state(episode_id)
    assert len(state.employees) == before_employees
    assert len(state.pending_hires) == 1

    for _ in range(13):
        server_app.get_daily_briefing(episode_id=episode_id, agent_role="people")

    assert len(server_app._get_state(episode_id).employees) == before_employees

    server_app.get_daily_briefing(episode_id=episode_id, agent_role="people")
    state = server_app._get_state(episode_id)
    assert len(state.employees) == before_employees + 1
    assert state.burn_rate_daily > before_burn


def test_pivot_requires_collective_majority_including_ceo():
    episode_id = _reset_episode(difficulty=2)
    direction = "Enterprise security analytics"
    rationale = "Core SMB segment is saturated and growth is stalling"

    vote_1 = server_app.pivot_company(
        episode_id=episode_id,
        agent_role="ceo",
        new_direction=direction,
        rationale=rationale,
        vote="approve",
    )
    assert vote_1["status"] == "pending"

    vote_2 = server_app.pivot_company(
        episode_id=episode_id,
        agent_role="cto",
        new_direction=direction,
        rationale=rationale,
        vote="approve",
    )
    assert vote_2["status"] == "pending"

    vote_3 = server_app.pivot_company(
        episode_id=episode_id,
        agent_role="cfo",
        new_direction=direction,
        rationale=rationale,
        vote="approve",
    )
    assert vote_3["executed"] is True
    assert vote_3["resolution"] == "majority"

    state = server_app._get_state(episode_id)
    assert state.pivot_in_progress is True
    assert state.pivot_direction == direction


def test_ceo_can_override_pivot_vote():
    episode_id = _reset_episode(difficulty=2)

    result = server_app.pivot_company(
        episode_id=episode_id,
        agent_role="ceo",
        new_direction="AI-native compliance platform",
        rationale="Market pulled by new enterprise regulations",
        vote="override",
    )

    assert result["executed"] is True
    assert result["resolution"] == "ceo_override"


def test_gauntlet_crisis_cadence_is_weekly():
    episode_id = _reset_episode(difficulty=4)
    state = server_app._get_state(episode_id)
    before_count = len(state.personal_crises)

    for crisis in list(state.personal_crises):
        server_app.handle_personal_crisis(
            episode_id=episode_id,
            agent_role=crisis.target_role.value,
            crisis_id=crisis.id,
            response="I understand the situation, let's talk through a clear plan and concrete next steps.",
        )

    for _ in range(6):
        server_app.get_daily_briefing(episode_id=episode_id, agent_role="ceo")

    state = server_app._get_state(episode_id)
    assert len(state.personal_crises) == before_count

    server_app.get_daily_briefing(episode_id=episode_id, agent_role="ceo")
    state = server_app._get_state(episode_id)
    assert len(state.personal_crises) > before_count
