---
name: add-replay-collector-service
description: >-
  Adds a new analysis service (collector) to the mcp-replay-dota2 services layer — a new domain
  like farming/jungle/rotation/lane that extracts data from a ParsedReplayData and returns
  service-layer Pydantic models. Use whenever the user wants to add a new service, a collector
  for replay data, a new analysis domain, a new src/services subdir, or asks to "extract X from
  the replay" / "analyze Y from the match" in this Dota 2 MCP server. Knows the
  service+model+constructor-injection pattern, the ParsedReplayData input contract, the strict
  NO-MCP-dependencies boundary, and the entry-point singleton wiring.
---

# Add a replay collector service to mcp-replay-dota2

Read `CLAUDE.md` (repo root) first for python-manta attribute/enum rules, lane naming, and the
tests+docs policy. This skill covers the service-layer architecture those rules sit inside.

A "collector" is a service: business logic that takes a parsed replay and returns models. Tools
live one layer up. To then expose the service as a tool, use the `add-mcp-tool` skill.

## Layer order (never bypass)

`external (tools/CLI/web) -> services -> python-manta`. Tools must hold no extraction logic;
services must hold no MCP code. Adding a service is purely a services-layer change until step 7.

## The input contract

Every public service method takes a `ParsedReplayData` (from
`src.services.models.replay_data`). It is produced ONCE by
`await ReplayService.get_parsed_data(match_id)` and cached on disk. Services never call
python-manta `Parser` and never re-parse — they read everything from the single passed-in
`ParsedReplayData`. `ReplayService` does the one-and-only single-pass `parser.parse(...)` with the
combat-log types and entity `interval_ticks` requested together.

## Workflow

1. **Create the package:** `src/services/<domain>/__init__.py` and
   `src/services/<domain>/<domain>_service.py`. The `__init__.py` exports the class.
2. **Class shape:** a `class <Domain>Service:` whose public methods take `ParsedReplayData`
   (plus optional filters / a `GameContext`) and return Pydantic models.
3. **Constructor injection** for cross-service dependencies — match the existing pattern:
   ```python
   # src/services/rotation/rotation_service.py
   def __init__(self, combat_service=None, fight_service=None):
       self._combat = combat_service or CombatService()
       self._fight = fight_service or FightService()
   ```
   `FightService(combat_service=...)` and `RotationService(combat_service=..., fight_service=...)`
   are the live examples. The entry point wires the real singletons; the `or Default()` fallback
   keeps the service usable standalone (e.g. in tests).
4. **NO MCP imports.** Add `NO MCP DEPENDENCIES.` to the module docstring (every existing service
   does). Importing `fastmcp` here breaks the CLI/web reusability the whole layer exists for.
5. **Service-layer model:** add `src/services/models/<domain>_data.py` with the Pydantic return
   types. These are SEPARATE from the MCP response models in `src/models/` — keep them distinct.
   Existing ones: `combat_data`, `farming_data`, `jungle_data`, `lane_data`, `rotation_data`,
   `seek_data`, `replay_data`.
6. **GameContext when you need map geometry / team mapping:** build it once via
   `GameContext.from_parsed_data(data)` (`src/models/game_context.py`) and pass it in. Services
   that consume it import it under `TYPE_CHECKING` to avoid hard coupling.
7. **Wire the singleton** in `dota_match_mcp_server.py`: instantiate `_<domain>_service = ...`
   alongside the others (~line 86) and add `"<domain>_service": _<domain>_service` to the
   `services` dict (~line 97) so tools can reach it.
8. **Optional export** from `src/services/__init__.py` `__all__`. Note it currently lists
   replay/cache/combat/fight/analyzers/jungle/lane/seek but NOT farming/rotation — exporting is
   optional, dict-wiring in the entry point is what actually matters.
9. **Real-values tests** under `tests/services/<domain>/` using conftest fixtures only — see the
   `run-ci-and-test-replays` skill. Never instantiate `Parser`/`get_parsed_data` in a test.
10. **CI gate** (also in `CLAUDE.md`):
    ```bash
    uv run ruff check src/ tests/ dota_match_mcp_server.py
    uv run mypy src/ dota_match_mcp_server.py --ignore-missing-imports
    uv run pytest
    ```

## Existing service domains (for naming + dependency reference)

`replay` (the parser/cache facade), `cache`, `combat` (CombatService + FightService),
`analyzers` (FightDetector / FightAnalyzer), `farming`, `jungle`, `lane`, `rotation`, `seek`.

## Gotchas

- python-manta data is attribute-access: `entry.neutral_camp_type`, `hero_snap.last_hits` — never
  dict-style. Use enums `CombatLogType`, `NeutralCampType` (SMALL=0/MEDIUM=1/HARD=2/ANCIENT=3),
  `Team`, never magic numbers.
- Lane names are team-relative: OpenDota `1=bottom 2=mid 3=top 4=jungle`; Radiant bottom=safe_lane
  / top=off_lane, Dire top=safe_lane / bottom=off_lane. Use
  `src.utils.match_fetcher.get_lane_name(lane, is_radiant)` — do not hardcode lane strings.
- If two services need each other, inject via constructor at the entry point; don't build the
  dependency inside a method.
