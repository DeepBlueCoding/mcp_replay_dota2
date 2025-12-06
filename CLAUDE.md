# CLAUDE.md

Guidance for working on this Dota 2 MCP Server codebase.

## CRITICAL: Before Pushing Code

**ALWAYS run the FULL CI pipeline locally before pushing:**

```bash
# 1. Lint check
uv run ruff check src/ tests/ dota_match_mcp_server.py

# 2. Type check
uv run mypy src/ dota_match_mcp_server.py --ignore-missing-imports

# 3. Tests (skip integration if no replay available)
uv run pytest -m "not integration"
```

**ALL THREE must pass before committing.** Do not push code that fails any step.

## Commands

```bash
# Always use uv, never python/pip directly
uv run python script.py
uv add package-name
uv run pytest tests/

# Run specific tests
uv run pytest tests/test_combat_log_parser.py -v

# Skip integration tests (require replays)
uv run pytest -m "not integration"

# Fetch latest constants from dotaconstants
uv run python scripts/fetch_constants.py
```

## Project Structure

```
dota_match_mcp_server.py   # MCP server entry point (tools + resources)
src/
  resources/               # Data providers (heroes, map, pro_scene)
  models/                  # Pydantic response models
  utils/                   # Parsers, downloaders, caches
  services/                # Services layer (NO MCP deps)
tests/
  conftest.py              # Session-scoped fixtures - reuses parsed data
data/
  constants/               # Cached dotaconstants JSON
  pro_scene/               # Player/team aliases
```

## Key Patterns

### Use python-manta Types, Not Dicts

**CRITICAL**: Always use python-manta Pydantic models and access attributes directly:

```python
# GOOD - python-manta types with attribute access
from python_manta import EntitySnapshot, PlayerState, CombatLogEntry

for player in snapshot.players:  # player is PlayerState
    hero = player.hero_name      # attribute access
    cs = player.last_hits

# BAD - dict-style access (WILL FAIL)
for player in snapshot.players:
    hero = player.get('hero_name')  # NO! PlayerState is not a dict
    hero = player['hero_name']       # NO!
```

### Services Layer (src/services/)

Services use python-manta types directly:
- `ReplayService` returns `ParsedReplayData` wrapping python-manta `ParseResult`
- `EntitySnapshot.players` contains `List[PlayerState]` (Pydantic models)
- `CombatLogResult.entries` contains `List[CombatLogEntry]` (Pydantic models)

### Single-Pass Parsing with python-manta

```python
from python_manta import Parser, CombatLogType

parser = Parser(replay_path)
result = parser.parse(
    combat_log={"types": [CombatLogType.DEATH.value, CombatLogType.DAMAGE.value]},
    entities={"interval_ticks": 900},
)
# Extract from single result - don't parse again
deaths = [e for e in result.combat_log.entries if e.type == CombatLogType.DEATH]
```

### Use Enums, Not Magic Numbers

```python
# GOOD
from python_manta import CombatLogType, Team
if entry.type == CombatLogType.DEATH:
    ...
if player.team == Team.RADIANT.value:
    ...

# BAD - magic numbers
if entry.type == 4:  # what is 4?
    ...
```

### Tests: Use conftest.py Fixtures

Replay parsing is expensive (~8 min per file). Use session-scoped fixtures:

```python
def test_something(hero_deaths, combat_log_280_290):  # fixtures inject cached data
    assert len(hero_deaths) > 0
```

NEVER parse replays directly in tests.

### MCP Design: Resources vs Tools

- **Resources** = static reference data (all heroes, map positions)
- **Tools** = dynamic queries requiring parameters (match-specific data)

Resources are attached to context before conversation. Tools are called by the LLM.

### Hero Names

Heroes use internal names: `npc_dota_hero_antimage` (not IDs or display names).
Use `hero_fuzzy_search` for name matching.

## When Making Changes

### After Changing Code

1. Run relevant tests: `uv run pytest tests/test_<module>.py -v`
2. Update CLAUDE.md if patterns/locations change
3. Update docs/ if user-facing behavior changes

### Adding New Tests

1. Check if data already exists in conftest.py fixtures
2. If not, add a new fixture that parses ONCE at session start
3. Tests should use fixtures, not parse replays themselves

### Adding New Parsers/Tools

1. Use `_replay_service.get_parsed_data(match_id)` to get `ParsedReplayData`
2. Access python-manta types via attributes (not dicts)
3. Return Pydantic models, not raw dicts

## Dependencies

- **python-manta** (>=1.4.5): Replay parser
- **python-opendota**: OpenDota API client (local at `../python-opendota-sdk`)
- **fastmcp**: MCP server framework
- **diskcache**: Persistent replay cache
