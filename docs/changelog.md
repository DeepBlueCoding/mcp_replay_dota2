# Changelog

??? info "🤖 AI Summary"

    Project changelog following Keep a Changelog format. v1.0.0 release includes: MCP resources (heroes, map, pro scene), 30+ MCP tools for match analysis, replay parsing with python-manta, fight detection with highlights, farming pattern analysis, rotation tracking, pro scene integration with fuzzy search.

All notable changes to this project will be documented in this file.

## [Unreleased]

*No unreleased changes.*

---

## [1.0.1] - 2025-12-08

### Fixed

- Updated examples documentation to match v1.0.0 Pydantic response models
- Added fight highlights to `get_fight_combat_log` examples (multi_hero_abilities, kill_streaks, team_wipes)
- Fixed `get_farming_pattern` example to use `camp_sequence` and `level_timings`
- Added missing standard fields to all tool response examples

---

## [1.0.0] - 2025-12-08

### Added

#### MCP Resources
- `dota2://heroes/all` - All Dota 2 heroes with stats and abilities
- `dota2://map` - Map geometry with towers, barracks, neutral camps, runes, landmarks
- `dota2://pro/players` - Pro player database with team affiliations
- `dota2://pro/teams` - Pro team database with rosters

#### Match Analysis Tools
- `download_replay` - Pre-cache replay files before analysis (50-400MB files)
- `get_hero_deaths` - All hero deaths with positions and abilities
- `get_combat_log` - Raw combat events with time/hero filters
- `get_fight_combat_log` - Auto-detect fight boundaries with **highlights**:
  - Multi-hero abilities (Chronosphere, Black Hole, Ravage hitting 2+ heroes)
  - Kill streaks (Double kill through Rampage, 18-second window)
  - Team wipes (Aces)
  - Fight initiation detection
- `get_item_purchases` - Item purchase timeline
- `get_objective_kills` - Roshan, tormentors, towers, barracks
- `get_match_timeline` - Net worth, XP, KDA over time for all players
- `get_stats_at_minute` - Snapshot of all players at specific minute
- `get_courier_kills` - Courier snipes with positions
- `get_rune_pickups` - Rune pickup tracking
- `get_match_draft` - Complete draft order for Captains Mode
- `get_match_info` - Match metadata (teams, players, winner, duration)
- `get_match_heroes` - 10 heroes with KDA, items, stats
- `get_match_players` - 10 players with names and hero assignments

#### Game State Tools
- `list_fights` - All fights with teamfight/skirmish classification
- `get_teamfights` - Major teamfights (3+ deaths)
- `get_fight` - Detailed fight information with positions
- `get_camp_stacks` - Neutral camp stacking events
- `get_jungle_summary` - Stacking efficiency by hero
- `get_lane_summary` - Laning phase winners and hero stats (OpenDota integration)
- `get_cs_at_minute` - CS/gold/level at specific minute
- `get_hero_positions` - Hero positions at specific minute
- `get_snapshot_at_time` - High-resolution game state at specific time
- `get_position_timeline` - Hero movement over time range
- `get_fight_replay` - High-resolution replay data for fights

#### Farming & Rotation Analysis
- `get_farming_pattern` - Minute-by-minute farming breakdown:
  - Lane vs jungle creeps, camp type identification
  - Position tracking, key transitions (first jungle, left lane)
  - Summary stats: jungle %, GPM, CS/min, camps by type
- `get_rotation_analysis` - Hero rotation tracking:
  - Rotation detection when heroes leave assigned lane
  - Rune correlation (power runes → rotations)
  - Fight outcomes: kill, died, traded, fight, no_engagement
  - Power/wisdom rune event tracking

#### Pro Scene Features
- `search_pro_player` / `search_team` - Fuzzy search with alias support
- `get_pro_player` / `get_pro_player_by_name` - Player details
- `get_team` / `get_team_by_name` - Team details with roster
- `get_team_matches` - Recent matches for a team
- `get_leagues` / `get_league_matches` - League information
- `get_pro_matches` - Pro matches with filters (tier, team, league, days_back)
- Series grouping for Bo1/Bo3/Bo5 detection
- Player signature heroes and role data

#### Pydantic Response Models
- 40+ typed models with Field descriptions in `src/models/tool_responses.py`
- Timeline: `KDASnapshot`, `PlayerTimeline`, `TeamGraphs`
- Fights: `FightSummary`, `FightHighlights`, `MultiHeroAbility`, `KillStreak`
- Game state: `HeroSnapshot`, `HeroPosition`, `PositionPoint`
- Better IDE autocomplete and documentation

#### Developer Experience
- Comprehensive MkDocs documentation with Material theme
- AI Summary sections on all documentation pages
- Parallel-safe tool hints for LLM optimization
- Server instructions with Dota 2 game knowledge

### Technical

#### Replay Parsing
- Single-pass parsing with python-manta v2 API
- `ReplayService.get_parsed_data(match_id)` as main entry point
- Disk caching via diskcache for parsed replay data
- CDOTAMatchMetadataFile extraction for timeline data

#### Architecture
- Services layer: `CombatService`, `FightService`, `FarmingService`, `RotationService`
- Clean separation: services have no MCP dependencies
- Pydantic models throughout for type safety
