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

import json
from typing import Any, Dict, List, Optional

from openenv.core.mcp_client import MCPToolClient
from openenv.core.env_server.mcp_types import Tool


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
    def __init__(
        self,
        base_url: str,
        connect_timeout_s: float = 10.0,
        message_timeout_s: float = 60.0,
        provider: Optional[Any] = None,
        mode: Optional[str] = None,
    ):
        super().__init__(
            base_url=base_url,
            connect_timeout_s=connect_timeout_s,
            message_timeout_s=message_timeout_s,
            provider=provider,
            mode=mode,
        )
        self._stateful_session_id: Optional[str] = None

    def _parse_mcp_response(self, raw_text: str) -> Dict[str, Any]:
        """Parse JSON-RPC from either raw JSON or SSE-framed payloads."""
        text = raw_text.strip()
        if not text:
            raise RuntimeError("Empty response from MCP server")

        if text.startswith("{"):
            return json.loads(text)

        data_lines = []
        for line in text.splitlines():
            if line.startswith("data:"):
                data_lines.append(line[len("data:") :].strip())

        if not data_lines:
            raise RuntimeError(f"Unable to parse MCP response: {text[:200]}")

        return json.loads(data_lines[-1])

    async def _stateful_mcp_request(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a JSON-RPC request to FastMCP's stateful /mcp endpoint."""
        client = await self._get_http_client()
        headers = {
            "accept": "application/json, text/event-stream",
        }
        if self._stateful_session_id:
            headers["mcp-session-id"] = self._stateful_session_id

        response = await client.post(
            self._production_mcp_url(),
            json={
                "jsonrpc": "2.0",
                "method": method,
                "params": params or {},
                "id": self._next_request_id(),
            },
            headers=headers,
            timeout=self._message_timeout,
        )
        response.raise_for_status()

        new_session_id = response.headers.get("mcp-session-id")
        if new_session_id:
            self._stateful_session_id = new_session_id

        return self._parse_mcp_response(response.text)

    async def _ensure_stateful_session(self) -> None:
        if self._stateful_session_id:
            return

        data = await self._stateful_mcp_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "genesis-env-client",
                    "version": "0.1.0",
                },
            },
        )
        if "error" in data:
            message = data.get("error", {}).get("message", "unknown error")
            raise RuntimeError(f"Failed to initialize MCP session: {message}")

    async def list_tools(self, use_cache: bool = True) -> List[Tool]:
        if use_cache and self._tools_cache is not None:
            return self._tools_cache

        await self._ensure_stateful_session()
        data = await self._stateful_mcp_request("tools/list", {})
        if "error" in data:
            message = data.get("error", {}).get("message", "unknown error")
            raise RuntimeError(f"list_tools failed: {message}")

        tools_data = data.get("result", {}).get("tools", [])
        tools = [
            Tool(
                name=t.get("name", ""),
                description=t.get("description", ""),
                input_schema=t.get("inputSchema", t.get("input_schema", {})),
            )
            for t in tools_data
        ]
        self._tools_cache = tools
        return tools

    async def call_tool(self, name: str, **kwargs: Any) -> Any:
        await self._ensure_stateful_session()
        data = await self._stateful_mcp_request(
            "tools/call",
            {
                "name": name,
                "arguments": kwargs,
            },
        )

        if "error" in data:
            message = data.get("error", {}).get("message", "unknown error")
            raise RuntimeError(f"Tool '{name}' failed: {message}")

        result = data.get("result", {})
        if isinstance(result, dict):
            if result.get("isError"):
                raise RuntimeError(f"Tool '{name}' returned an error response")

            if "structuredContent" in result:
                return result["structuredContent"]

            content = result.get("content")
            if isinstance(content, list) and content:
                text = content[0].get("text") if isinstance(content[0], dict) else None
                if isinstance(text, str):
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return text

            if "data" in result:
                return result["data"]

        return result
