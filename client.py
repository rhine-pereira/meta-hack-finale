"""
GENESIS Environment Client.
Connects to the GENESIS server to train LLMs on startup operations.

Example:
    >>> with GenesisEnv(base_url="http://localhost:7860") as env:
    ...     env.reset()
    ...     tools = env.list_tools()
    ...     result = env.call_tool("get_daily_briefing", agent_role="ceo")
    ...     print(result)
"""

from openenv.core.mcp_client import MCPToolClient


class GenesisEnv(MCPToolClient):
    """
    Client for the GENESIS Startup Gauntlet Environment.

    Exposes all tools via MCP:
    - get_daily_briefing(agent_role): Get your inbox for the current day
    - make_decision(agent_role, decision_type, decision, reasoning): Act on an item
    - send_message(from_role, to_role, subject, content): Communicate with co-founders
    - build_feature(name, complexity, engineers, agent_role): Start feature development
    - check_bank_balance(agent_role): Check financials
    - hire_candidate(candidate_id, role, salary, agent_role): Make a hire
    - fire_employee(employee_id, severance, agent_role): Let someone go
    - negotiate_with_investor(investor_id, valuation, equity, agent_role): Fundraise
    - write_company_brain(key, value, agent_role): Save strategic context
    - read_company_brain(key, agent_role): Retrieve stored strategy
    - get_company_state(agent_role): Full company snapshot
    - analyze_market(segment, agent_role): Market intelligence
    - handle_personal_crisis(crisis_id, response, agent_role): Handle human situations
    - check_team_morale(agent_role): Team health
    - pivot_company(new_direction, rationale, agent_role): Declare a pivot

    Example with HuggingFace Space:
        >>> env = GenesisEnv.from_env("your-hf-org/genesis-env")
        >>> try:
        ...     env.reset()
        ...     result = env.call_tool("get_company_state", agent_role="ceo")
        ... finally:
        ...     env.close()
    """
    pass  # MCPToolClient provides all needed functionality
