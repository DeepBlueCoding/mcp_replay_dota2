---
name: add-mcp-tool
description: >-
  Adds a new MCP tool to the mcp-replay-dota2 Dota 2 replay-analysis server end to end
  (service method -> Pydantic response model -> register_<domain>_tools registration ->
  tool-selection instructions -> mkdocs page -> real-values test). Use whenever the user
  wants to add, expose, register, or wire up an MCP tool, a new @mcp.tool, a get_* tool,
  a tool that returns match/replay data, or "expose this analysis as a tool" for the dota
  MCP server, even if they don't spell out every step. Knows the non-obvious services-dict
  wiring, the NO-MCP-deps service boundary, and the mandatory per-change docs+test discipline.
---

# Add an MCP tool to mcp-replay-dota2

Read `CLAUDE.md` (repo root) first — it holds the python-manta attribute-access rules, the
enum rules, the lane-naming rules, and the mandatory tests+docs+changelog policy. This skill
adds the tool-specific vertical slice on top of that.

## Tool vs resource

- Dynamic, parameter-required query (needs a `match_id` or other args) -> `@mcp.tool`.
- Static reference data, no params (heroes, map, pro lists) -> `@mcp.resource` in the
  `dota2://` namespace (see `src/resources/`, registered in `dota_match_mcp_server.py`).

This skill is for tools. For a brand-new analysis domain (new service), use the
`add-replay-collector-service` skill first, then come back here to expose it.

## Workflow (do in this order)

1. **Service method first.** Put extraction logic in a service under `src/services/<domain>/`,
   not in the tool. The service must have ZERO MCP/fastmcp imports — it stays importable from
   CLI/web (the boundary is stated in `src/services/__init__.py`). Tools must contain no
   extraction logic; they only call services and shape the response.
2. **Response model.** Add or extend a Pydantic model in `src/models/` (NOT `src/services/models/`
   — those are the service-layer models). Write a `Field(description=...)` on every field; those
   descriptions become the LLM-visible schema. FastMCP auto-serializes the model — never return a
   raw dict.
3. **Register the tool** inside the correct `register_<domain>_tools(mcp, services)` in
   `src/tools/<domain>_tools.py`. Tools are NOT decorated at module top level — they live inside
   the register function so they capture `services`. Pull dependencies out of the dict, e.g.
   `replay_service = services["replay_service"]`. Decorate with `@mcp.tool` (bare, no parens — see
   `replay_tools.py`).
4. **Replay tools** follow this exact pattern for progress + cached parse:
   ```python
   @mcp.tool
   async def get_something(match_id: int, ctx: Context) -> SomethingResponse:
       async def progress_callback(current: int, total: int, message: str) -> None:
           await ctx.report_progress(current, total)
       data = await replay_service.get_parsed_data(match_id, progress=progress_callback)
       return some_service.do_thing(data)
   ```
   `get_parsed_data` returns a cached `ParsedReplayData`; never call python-manta `Parser`
   directly in a tool.
5. **Filtering** uses the shared filter models in `src/models/filters.py`
   (`DeathFilters`, `CombatFilters`, `EventFilters`, `FightFilters`, `HeroPerformanceFilters`).
   Build with `.from_params(killer=..., location=..., start_time=...)` then `.apply(items)`.
   Location filters accept the 37 named map regions — do not invent ad-hoc filtering.
6. **New tool module?** Add `register_<domain>_tools` to the imports and the call list in
   `src/tools/__init__.py::register_all_tools`. The six existing modules are: `replay_tools`,
   `combat_tools`, `fight_tools`, `match_tools`, `pro_scene_tools`, `analysis_tools`
   (registered in that order; ~41 tools total).
7. **New service dependency?** Instantiate the singleton in `dota_match_mcp_server.py` and add it
   to the `services` dict (~line 97). Available keys today:
   `replay_service`, `combat_service`, `fight_service`, `jungle_service`, `lane_service`,
   `seek_service`, `farming_service`, `rotation_service`, `heroes_resource`, `pro_scene_resource`,
   `constants_fetcher`, `match_fetcher`, `pro_scene_fetcher`.
8. **Tool-selection instructions — update BOTH surfaces** so the LLM knows when to pick the tool:
   - the `TOOL_INSTRUCTIONS` markdown table in `dota_match_mcp_server.py`, and
   - the "AI Summary - Tool Selection Guide" admonition table at the top of
     `docs/api/tools/index.md` (and bump the per-category tool count in the Categories table).
9. **Docs page** — add `## <tool_name>` with a one-line purpose, a python call example, and a
   JSON `Returns` block, on the page matching the tool's category (see map below). Use the
   `write-mkdocs-docs` skill for the admonition/changelog conventions.
10. **Real-values test** under `tests/<area>/` using conftest fixtures only — never parse a replay
    in a test. See the `run-ci-and-test-replays` skill.
11. **CI gate** — run all three before declaring done (also in `CLAUDE.md`):
    ```bash
    uv run ruff check src/ tests/ dota_match_mcp_server.py
    uv run mypy src/ dota_match_mcp_server.py --ignore-missing-imports
    uv run pytest
    ```

## Docs category -> page map

| Category | Page | Tools |
|---|---|---|
| Match analysis | `docs/api/tools/match-analysis.md` | download/delete_replay, hero_deaths, hero_performance, combat log, items, objectives, match_timeline/info/heroes/players, runes, courier, draft |
| Game state | `docs/api/tools/game-state.md` | list_fights, get_teamfights, get_fight, camp_stacks, jungle_summary, snapshot_at_time, hero_positions, position_timeline, fight_replay |
| Farming & rotation | `docs/api/tools/farming-rotation.md` | get_farming_pattern, get_rotation_analysis |
| Lane analysis | `docs/api/tools/lane-analysis.md` | lane_summary, cs_at_minute |
| Pro scene | `docs/api/tools/pro-scene.md` | search_pro_player, search_team, get_pro_matches, etc. |

## Gotchas

- Access python-manta data by attribute (`hero_snap.hero_name`), never `hero_snap["hero_name"]`.
- Use enums (`CombatLogType`, `Team`, `NeutralCampType`) — no magic numbers.
- `register_all_tools` order matters only for grouping; the real coupling is that every tool's
  service must already be in the `services` dict before `register_all_tools` runs.
- A tool that forgets its `services` lookup will `KeyError` at server startup, not at call time.
