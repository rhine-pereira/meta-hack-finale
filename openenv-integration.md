# Compulsory OpenEnv Integration

## Goal
Refactor `train.py` to strictly use the OpenEnv architecture (`GenesisEnv` client and MCP tools) for the training loop, eliminating direct server imports and removing duplicated tool logic.

## Tasks
- [ ] Task 1: Update `server/app.py` `get_reward` tool → Verify: Ensure `get_reward` exposes MarketMaker weaknesses (needed for `train.py`'s self-play state).
- [ ] Task 2: Refactor `train.py` to initialize `GenesisEnv` → Verify: `train.py` successfully creates a `GenesisEnv` client instance (connecting to a local FastAPI server or via subprocess).
- [ ] Task 3: Rewrite `run_episode` in `train.py` → Verify: `run_episode` uses `env.call_tool("reset", ...)`, `env.call_tool("get_daily_briefing", ...)`, and `env.call_tool(action_name, args)`.
- [ ] Task 4: Remove `_execute_tool_call` from `train.py` → Verify: The duplicated logic in `train.py` is entirely deleted, enforcing reliance on `server/app.py` tools.
- [ ] Task 5: Handle background server lifecycle in `train.py` → Verify: `train.py` automatically starts the FastMCP server at the beginning of the run and tears it down at the end (or uses direct MCP stdio if supported by OpenEnv).

## Done When
- [ ] `python train.py --smoke` completes successfully without using any direct `from server...` imports in `train.py`.
- [ ] The simulation state is mutated entirely through OpenEnv/MCP tool calls.
- [ ] The hackathon requirement for "Clean OpenEnv compliance" is fully met in the core training pipeline.

## Notes
- Performance may decrease slightly due to HTTP/IPC overhead, but OpenEnv compliance is the priority for judging.
- Ensure the `MarketMaker` weaknesses are properly propagated from the server back to the training client so the dynamic difficulty curriculum still works.
