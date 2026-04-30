# Graph Report - meta-hack-finale  (2026-04-26)

## Corpus Check
- 71 files · ~180,566 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 620 nodes · 1976 edges · 14 communities detected
- Extraction: 44% EXTRACTED · 56% INFERRED · 0% AMBIGUOUS · INFERRED: 1100 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 16|Community 16]]

## God Nodes (most connected - your core abstractions)
1. `WorldState` - 157 edges
2. `AgentRole` - 126 edges
3. `DifficultyLevel` - 87 edges
4. `MarketMaker` - 75 edges
5. `SolanaProofClient` - 62 edges
6. `GenesisEnv` - 58 edges
7. `PendingFeature` - 55 edges
8. `Message` - 55 edges
9. `Employee` - 46 edges
10. `_get_state()` - 42 edges

## Surprising Connections (you probably didn't know these)
- `GenesisEnv` --uses--> `GENESIS Training Script — GRPO on startup simulation.  Train LLMs to co-found`  [INFERRED]
  client.py → train.py
- `GenesisEnv` --uses--> `Create a sync OpenEnv MCP client in production mode (/mcp HTTP JSON-RPC).`  [INFERRED]
  client.py → train.py
- `GenesisEnv` --uses--> `Persists MarketMaker knowledge across training episodes.`  [INFERRED]
  client.py → train.py
- `GenesisEnv` --uses--> `Run a single mini-episode using the OpenEnv GenesisEnv client.          This u`  [INFERRED]
  client.py → train.py
- `GenesisEnv` --uses--> `Parse model output into a list of tool call dicts.      Accepts two formats:`  [INFERRED]
  client.py → train.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (85): _ensure_ml_model(), ml_generate_decision(), ml_model_status(), GenesisEnv, GENESIS Environment Client. Connects to the GENESIS server to train LLMs on sta, Client for the GENESIS Startup Gauntlet Environment.      Exposes all tools vi, Parse JSON-RPC from either raw JSON or SSE-framed payloads., Send a JSON-RPC request to FastMCP's stateful /mcp endpoint. (+77 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (79): analyze_market(), build_feature(), check_bank_balance(), check_team_morale(), compare_founder_genomes(), conduct_interview(), create_financial_model(), deploy_to_production() (+71 more)

### Community 2 - "Community 2"
Cohesion: 0.14
Nodes (66): commit_simulation_proof(), get_simulation_proof_status(), GENESIS MCP Server — The main entry point. Exposes tools to LLM agents for co-f, Deploy current product to production. High tech debt increases failure risk., Run a load test to check system performance.      Args:         episode_id: U, Review codebase health: tech debt, coverage, dependency risks.      Args:, Send a personalized email to a customer. Affects satisfaction and churn., Update a customer's CRM record.      Args:         episode_id: Unique identif (+58 more)

### Community 3 - "Community 3"
Cohesion: 0.1
Nodes (34): CEOViewFilter, CFOViewFilter, CTOViewFilter, get_filtered_view(), PeopleViewFilter, RoleViewFilter, SalesViewFilter, fresh_state() (+26 more)

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (45): _legacy_filter_state(), removeModel(), Enum, _check_series_a(), Evaluate whether Series A conditions are met. Returns event string or None., compute_reward(), Compute the full composable rubric reward for the current state., _approximate_cash() (+37 more)

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (23): _inject_postmortem_forks(), GENESIS Event Engine — Drives the simulation forward each day.  Handles: - Da, Check if any PostmortemScenario ForkPoints are due today and surface them     a, Advance the world by one business day. Returns list of event descriptions., tick_day(), GENESIS MarketMaker — The adaptive market adversary.  Observes agent performan, Generates market scenarios that adapt to agent performance.          Tracks wh, Compute the appropriate difficulty level based on performance.         Returns (+15 more)

### Community 6 - "Community 6"
Cohesion: 0.1
Nodes (25): build_dataset(), _create_env_client(), _ensure_log_dir(), _extract_role_from_prompt(), genesis_reward_fn(), _get_shared_env(), _parse_tool_calls(), plot_training_progress() (+17 more)

### Community 7 - "Community 7"
Cohesion: 0.12
Nodes (23): build_dataset(), _ensure_log_dir(), _extract_role(), genesis_reward_fn(), _get_shared_env(), _init_openenv_client(), install_dependencies(), _is_colab() (+15 more)

### Community 8 - "Community 8"
Cohesion: 0.2
Nodes (19): ForkPoint, _jawbone_scenario(), _juicero_scenario(), PostmortemScenario, _quibi_scenario(), GENESIS Dead Startup Resurrection Engine — Postmortem Scenario System.  Encode, A critical decision moment in a startup's history.     Each one maps to a speci, A full startup failure encoded as a simulation seed.     Injected into the Mark (+11 more)

### Community 9 - "Community 9"
Cohesion: 0.2
Nodes (17): _annotate_improvement(), generate_demo_artifacts(), _ma_x(), main(), _make_figure(), _moving_average(), plot_from_sessions(), _radar_panel() (+9 more)

### Community 10 - "Community 10"
Cohesion: 0.15
Nodes (5): GenesisClient, fetchCustomModels(), fetchGenomes(), main(), checkServer()

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (3): cn(), handleNegotiate(), formatCurrency()

### Community 12 - "Community 12"
Cohesion: 0.38
Nodes (9): _delete_paths(), _ensure_parent(), _find_python_artifacts(), _iter_moves(), main(), Move, _move_file(), Repo organizer / cleanup utility.  Goals: - Reduce clutter in the repository (+1 more)

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (1): Pytest configuration — exclude root __init__.py from collection.

## Knowledge Gaps
- **30 isolated node(s):** `GENESIS Environment Client. Connects to the GENESIS server to train LLMs on sta`, `Client for the GENESIS Startup Gauntlet Environment.      Exposes all tools vi`, `Parse JSON-RPC from either raw JSON or SSE-framed payloads.`, `Send a JSON-RPC request to FastMCP's stateful /mcp endpoint.`, `Pytest configuration — exclude root __init__.py from collection.` (+25 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 16`** (2 nodes): `conftest.py`, `Pytest configuration — exclude root __init__.py from collection.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `WorldState` connect `Community 2` to `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 8`, `Community 9`?**
  _High betweenness centrality (0.165) - this node is a cross-community bridge._
- **Why does `AgentRole` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`?**
  _High betweenness centrality (0.152) - this node is a cross-community bridge._
- **Why does `GenesisEnv` connect `Community 0` to `Community 6`, `Community 7`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Are the 150 inferred relationships involving `WorldState` (e.g. with `GENESIS reward plotting utility.  Two modes:   1. --sessions sessions.pkl   R` and `Return x-axis indices aligned to the right end of the moving-average.`) actually correct?**
  _`WorldState` has 150 INFERRED edges - model-reasoned connections that need verification._
- **Are the 123 inferred relationships involving `AgentRole` (e.g. with `SessionIdMiddleware` and `GENESIS MCP Server — The main entry point. Exposes tools to LLM agents for co-f`) actually correct?**
  _`AgentRole` has 123 INFERRED edges - model-reasoned connections that need verification._
- **Are the 84 inferred relationships involving `DifficultyLevel` (e.g. with `SessionIdMiddleware` and `GENESIS MCP Server — The main entry point. Exposes tools to LLM agents for co-f`) actually correct?**
  _`DifficultyLevel` has 84 INFERRED edges - model-reasoned connections that need verification._
- **Are the 63 inferred relationships involving `MarketMaker` (e.g. with `SessionIdMiddleware` and `GENESIS MCP Server — The main entry point. Exposes tools to LLM agents for co-f`) actually correct?**
  _`MarketMaker` has 63 INFERRED edges - model-reasoned connections that need verification._