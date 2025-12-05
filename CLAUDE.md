# CLAUDE.md

Guidance for working on this Dota 2 MCP Server codebase.

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
  services/                # v2 services layer (NO MCP deps)
tests/
  conftest.py              # Session-scoped fixtures - reuses parsed data
data/
  constants/               # Cached dotaconstants JSON
  pro_scene/               # Player/team aliases
```

## Key Patterns

### Always Reuse Parsed Replay Data

Replay parsing is expensive (~8 min per file). The codebase has two caching layers:

1. **`replay_cache`** (src/utils/replay_cache.py) - diskcache for production
2. **`conftest.py`** fixtures - session-scoped for tests

When writing tests, USE THE FIXTURES from conftest.py:
```python
def test_something(hero_deaths, combat_log_280_290):  # fixtures inject cached data
    assert len(hero_deaths) > 0
```

NEVER parse replays directly in tests. Add new fixtures to conftest.py if needed.

### Single-Pass Parsing with python_manta v2

Always use the v2 API with multiple collectors in one pass:
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

### Use Enum Types, Not Magic Numbers

```python
# GOOD
from python_manta import CombatLogType, Team
if entry.type == CombatLogType.DEATH:
    ...
if player.team == Team.RADIANT:
    ...

# BAD - magic numbers
if entry.type == 4:  # what is 4?
    ...
```

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

1. Use `replay_cache.get_parsed_data()` to get cached ParsedReplayData
2. Extract what you need from the cached data
3. Return Pydantic models, not raw dicts

## Dependencies

- **python-manta** (>=1.4.5): Replay parser with v2 API
- **python-opendota**: OpenDota API client (local at `../python-opendota-sdk`)
- **fastmcp**: MCP server framework
- **diskcache**: Persistent replay cache
