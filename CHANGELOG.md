## v1.0.6.dev2 (2025-12-11)

### Fix

- use PEP 440 pre-release detection for TestPyPI vs PyPI

## v1.0.5 (2025-12-11)

### Feat

- add position (1-5) assignment and draft context to match tools
- add ability_filter to get_raw_combat_events and get_hero_performance
- add detail_level parameter for combat log token control
- add get_hero_combat_analysis tool for per-hero combat stats

### Fix

- count abilities across entire match, not just during fights
- add NOT FOR HERO PERFORMANCE warnings to competing tools
- blend team-specific and proMatches data for better coverage
- reduce combat log max_events caps and improve docstrings

### Refactor

- rename tools for clearer LLM selection

## v1.1.0 (2025-12-08)

### Feat

- add counter picks to get_match_heroes tool
- hero counter picks database for draft analysis
- combat-intensity fight detection and highlight improvements

### Fix

- correct field mappings in get_match_heroes (lane, gpm, xpm)

### Refactor

- split MCP tools into domain-specific modules

## v1.0.1 (2025-12-08)

## v1.0.0 (2025-12-08)

### Feat

- **pro_scene**: add player signature heroes and role data
- add Pydantic response models with descriptions for all MCP tools
- add fight highlights detection (multi-hero abilities, kill streaks, team wipes)
- upgrade to official PyPI releases and complete v2 migration
- add multi-camp detection and upgrade to python-manta dev12
- migrate to python-manta dev11 consolidated HeroSnapshot API
- add get_farming_pattern and get_rotation_analysis tools
- resolve pro player names from account_id
- add filtering options to get_pro_matches tool
- add Docker support, coaching instructions, and download validation
- cache test replay in CI for faster builds
- add pro scene resources, match info tools, and AI summaries
- add download_replay tool for pre-caching replays

### Fix

- **ci**: skip metadata parsing to avoid OOM in CI
- **ci**: correct parsed replay cache path to match ReplayCache
- **ci**: add pre-parse step to populate replay cache
- **ci**: cache parsed replay data and fix asyncio in conftest
- update test to expect actual game time duration
- use OpenDota SDK generic get() method for API calls
- update python-manta to dev8 and fix rune time test
- use entry.game_time directly instead of tick_to_game_time
- invalidate corrupt replay cache, add size verification
- handle None timeline in conftest fixtures
- cache only raw replay, not parsed data
- cache both replay and parsed data for faster CI
- skip tests when replay file unavailable in CI
- mypy type errors, add CI check requirement to CLAUDE.md
- remove build artifacts, fix lint errors, update gitignore
- resolve ruff lint errors
- use MkDocs Material admonition syntax for AI summaries
- commit constants files for CI
- fix pyproject.toml dependencies and CI workflow

### Refactor

- merge metadata parsing into single-pass replay parse
- migrate to ReplayService as single entry point for replay data
- convert parameterized resources to tools, single-pass parsing
