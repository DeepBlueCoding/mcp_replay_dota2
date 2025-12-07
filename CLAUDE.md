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
from python_manta import EntitySnapshot, HeroSnapshot, CombatLogEntry

for hero_snap in snapshot.heroes:  # hero_snap is HeroSnapshot
    hero = hero_snap.hero_name     # attribute access
    cs = hero_snap.last_hits
    x, y = hero_snap.x, hero_snap.y  # position

# BAD - dict-style access (WILL FAIL)
for hero_snap in snapshot.heroes:
    hero = hero_snap.get('hero_name')  # NO! HeroSnapshot is not a dict
    hero = hero_snap['hero_name']       # NO!
```

### Services Layer (src/services/)

V2 services provide all replay data extraction:
- `CombatService` - hero deaths, combat log, objectives (roshan, towers, barracks), rune pickups
- `FightService` - fight detection with participants and deaths
- `ReplayService` - replay downloading and path management

Use `ReplayService` to get cached `ParsedReplayData`:

```python
from src.services.replay.replay_service import ReplayService
from src.services.combat.combat_service import CombatService

rs = ReplayService()
data = await rs.get_parsed_data(match_id)  # Cached on disk
combat = CombatService()
deaths = combat.get_hero_deaths(data)
fights = FightService().get_all_fights(data)
```

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
from python_manta import CombatLogType, Team, NeutralCampType
if entry.type == CombatLogType.DEATH:
    ...
if player.team == Team.RADIANT.value:
    ...

# Neutral camp tier detection (1.4.5.2+)
if entry.neutral_camp_type == NeutralCampType.HARD.value:  # large camp
    ...

# BAD - magic numbers
if entry.type == 4:  # what is 4?
    ...
```

### NeutralCampType (python-manta 1.4.5.2+)

Combat log entries for neutral creep kills include camp tier info:

```python
from python_manta import NeutralCampType

# NeutralCampType values:
# SMALL = 0   (kobolds, hill trolls, etc.)
# MEDIUM = 1  (wolves, ogres, harpies, etc.)
# HARD = 2    (large camps: centaurs, satyrs, hellbears, etc.)
# ANCIENT = 3 (black dragons, thunderhides, etc.)

# Access on CombatLogEntry:
entry.neutral_camp_type  # int value (0-3) or None for non-neutrals
entry.neutral_camp_team  # which team's jungle
```

### Tests: Use conftest.py Fixtures

Tests use `ReplayService` via session-scoped fixtures. With disk caching, tests run in ~3 seconds:

```python
def test_something(hero_deaths, combat_log_280_290):  # fixtures inject cached data
    assert len(hero_deaths) > 0
```

NEVER parse replays directly in tests. Always use fixtures from conftest.py.

### MCP Design: Resources vs Tools

- **Resources** = static reference data (all heroes, map positions)
- **Tools** = dynamic queries requiring parameters (match-specific data)

Resources are attached to context before conversation. Tools are called by the LLM.

### Hero Names

Heroes use internal names: `npc_dota_hero_antimage` (not IDs or display names).
Use `hero_fuzzy_search` for name matching.

### Lane Names (Team-Relative)

Lane names are **team-relative**, not absolute map positions:

```python
# OpenDota lane values: 1=bottom, 2=mid, 3=top, 4=jungle
# Radiant: bottom(1)=safe_lane, top(3)=off_lane
# Dire: top(3)=safe_lane, bottom(1)=off_lane

from src.utils.match_fetcher import get_lane_name

get_lane_name(lane=3, is_radiant=False)  # "safe_lane" (Dire top)
get_lane_name(lane=1, is_radiant=False)  # "off_lane" (Dire bot)
```

### Farming Pattern Tool

The `get_farming_pattern` tool returns detailed farming analysis:

```python
# Per-minute data shows actual farming ROUTE
{
    "minute": 14,
    "position_at_start": {"x": 5200, "y": 3800, "area": "dire_jungle"},
    "camp_sequence": [
        {"time_str": "14:05", "camp": "large_troll", "tier": "large", "area": "dire_jungle"},
        {"time_str": "14:18", "camp": "medium_satyr", "tier": "medium", "area": "dire_jungle"}
    ],
    "camps_cleared": 2,
    "lane_creeps_killed": 3
}

# Power spike tracking
"level_timings": [{"level": 6, "time_str": "7:00"}]
"item_timings": [{"item": "bfury", "time_str": "14:00"}]
```

Key features:
- `camp_sequence`: Ordered list showing which camps were cleared and when
- `position_at_start/end`: Where hero was at minute boundaries
- `level_timings`: For level-based power spikes (lvl 6 ultimate, etc.)
- `item_timings`: From OpenDota `purchase_log` for item power spikes
- Each `CreepKill` includes `map_area` showing which jungle (dire/radiant)
- Each `CreepKill` includes `camp_tier` from python-manta's `neutral_camp_type`
- `multi_camp_clears`: Detects when hero farms 2+ camps simultaneously (stacked/adjacent)

Multi-camp detection example:
```python
# Detects Medusa/Juggernaut farming stacked or adjacent camps
"multi_camp_clears": [
    {
        "time_str": "14:05",
        "camps": ["large_centaur", "medium_wolf"],  # 2 different camps
        "duration_seconds": 1.1,
        "creeps_killed": 4,
        "area": "dire_jungle"
    }
]
```

## When Making Changes

### Testing Workflow (CRITICAL)

**Follow this order - do NOT skip steps:**

1. **FIRST: Write tests for new code**
   - New feature/bug fix = new test FIRST
   - Add tests to appropriate test file in `tests/`
   - If no tests needed (pure refactor with existing coverage), skip to step 3

2. **THEN: Run only the new tests**
   ```bash
   # Run specific test class or function
   uv run pytest tests/test_farming_service.py::TestMultiCampDetection -v
   ```

3. **BEFORE PUSHING: Run full CI pipeline**
   ```bash
   uv run ruff check src/ tests/ dota_match_mcp_server.py
   uv run mypy src/ dota_match_mcp_server.py --ignore-missing-imports
   uv run pytest -m "not integration"
   ```

With disk caching (`ReplayService`), the full test suite runs in ~3 seconds once the replay is cached.

### Adding New Tests

1. Check if data already exists in conftest.py fixtures
2. If not, add a new fixture that parses ONCE at session start
3. Tests should use fixtures, not parse replays themselves

**For unit tests that don't need replay data:**
- Don't request any replay fixtures (hero_deaths, combat_log_*, etc.)
- Tests will run fast (<1 second) without triggering replay parsing
- Replay is only parsed when a fixture that needs it is requested

### Adding New Parsers/Tools

1. Use `ReplayService.get_parsed_data(match_id)` to get cached `ParsedReplayData`
2. Use v2 services (`CombatService`, `FightService`) for data extraction
3. Access python-manta types via attributes (not dicts)
4. Return Pydantic models, not raw dicts

```python
from src.services.replay.replay_service import ReplayService
from src.services.combat.combat_service import CombatService

rs = ReplayService()
data = await rs.get_parsed_data(match_id)
combat = CombatService()
deaths = combat.get_hero_deaths(data)
```

## Dependencies

- **python-manta** (>=1.4.5.2): Replay parser with NeutralCampType support
- **python-opendota-sdk** (>=7.39.5.2): OpenDota API client
- **fastmcp**: MCP server framework
- **diskcache**: Persistent replay cache
