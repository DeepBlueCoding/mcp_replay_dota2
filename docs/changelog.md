# Changelog

??? info "🤖 AI Summary"

    Project changelog following Keep a Changelog format. v1.0.0 release includes: MCP resources (heroes, map, pro scene), 30+ MCP tools for match analysis, replay parsing with python-manta, fight detection with highlights, farming pattern analysis, rotation tracking, pro scene integration with fuzzy search.

All notable changes to this project will be documented in this file.

## [1.0.9] - 2025-12-12

### Fixed

- **get_match_info and get_match_draft** returning generic "Could not parse" errors
- Exception handling now propagates actual error messages instead of swallowing with generic messages
- **get_pro_matches league_name filter** now uses bidirectional matching (e.g., "Blast Slam V" finds "SLAM V")

## [1.2.0] - 2025-12-11

### Added

- **Position (1-5) assignment** for all match tools:
  - `get_match_heroes`, `get_match_players`, `get_match_draft` now include `position` field
  - Position determined from OpenDota lane data (`lane_role`) and GPM:
    - **Pos 1** = Safelane core (lane_role=1, highest GPM)
    - **Pos 2** = Mid (lane_role=2)
    - **Pos 3** = Offlane core (lane_role=3, highest GPM)
    - **Pos 4** = Soft support (higher GPM support)
    - **Pos 5** = Hard support (lowest GPM support)
  - Fixes LLM incorrectly guessing positions (e.g., Axe as pos5 instead of pos3)

- **Draft context data** in `get_match_draft` picks:
  - `counters`: Heroes that counter this pick (bad matchups)
  - `good_against`: Heroes this pick counters (favorable matchups)
  - `when_to_pick`: Conditions when this hero is strong
  - Helps LLM understand draft decisions and counter-picking

### Changed

- `assign_roles()` renamed to `assign_positions()` in match_fetcher.py
- `DraftAction` model now includes `position`, `counters`, `good_against`, `when_to_pick` fields
- `HeroStats` and `MatchPlayerInfo` models now include `position` field

---

## [1.1.4] - 2025-12-11

### Changed

- **`get_pro_matches` tool** - Enhanced team filtering with head-to-head support:
  - Renamed `team_name` parameter to `team1_name`
  - Added `team2_name` parameter for head-to-head filtering
  - **Single team filter** (`team1_name` only): Returns all matches involving that team
  - **Head-to-head filter** (`team1_name` + `team2_name`): Returns only matches where both teams played against each other, regardless of radiant/dire side
  - Combine with `league_name`, `tier`, and `days_back` for deep filtering (e.g., Spirit vs OG at The International)

---

## [1.1.3] - 2025-12-10

### Added

- **`ability_filter` parameter** for focused ability analysis:
  - `get_raw_combat_events`: Filter combat log by specific ability (e.g., "ice_path", "chronosphere")
  - `get_hero_performance`: Filter ability summary and per-fight abilities by name
  - Case-insensitive partial matching (e.g., "fissure" matches "earthshaker_fissure")

### Changed

- **Tool renames for clarity** (LLM routing improvement):
  - `get_combat_log` → `get_raw_combat_events` (emphasizes raw event debugging)
  - `get_hero_combat_analysis` → `get_hero_performance` (clearer purpose)

- **Added routing hints** to competing tools:
  - `get_hero_deaths`, `list_fights`, `get_teamfights`, `get_rotation_analysis` now include "NOT FOR HERO PERFORMANCE QUESTIONS → Use get_hero_performance instead" in docstrings

### Fixed

- **Ability counting now covers entire match** - Previously only counted abilities used during detected fights; now counts ALL ability usage across the entire match with per-fight breakdown preserved

---

## [1.1.2] - 2025-12-09

### Added

- **`detail_level` parameter** for combat log tools - Controls token usage (~98% reduction with `narrative`):
  - `narrative` (default): Deaths, abilities, items, purchases, buybacks (~500-2,000 tokens)
  - `tactical`: Adds hero-to-hero damage and debuffs (~2,000-5,000 tokens)
  - `full`: All events including creeps (~50,000+ tokens, debugging only)
  - Applied to `get_combat_log` and `get_fight_combat_log` tools
  - `max_events` parameter added (default 500, max 2000) to prevent overflow
  - `truncated` field in response indicates if results were capped

### Changed

- **Removed `significant_only` parameter** - Replaced by `detail_level` enum for finer control
- Default behavior now uses `narrative` detail level (was equivalent to `significant_only=True`)

---

## [1.1.1] - 2025-12-08

### Added

- **`get_hero_combat_analysis` tool** - Per-hero combat performance analysis across all fights:
  - Tracks kills, deaths, assists per fight
  - Ability usage with hit rates (total casts vs hero hits)
  - Damage dealt and received per fight
  - Teamfight vs skirmish classification
  - **Ground-targeted ability tracking**: Ice Path, Fissure, etc. track hits via MODIFIER_ADD events (stun debuffs applied)
  - Hit rate can exceed 100% for AoE abilities hitting multiple heroes per cast
  - Aggregate stats across all fights for the hero

---

## [1.1.0] - 2025-12-08

### Changed

- **Major refactor: Tools split into domain-specific modules** (92% code reduction in main entry point)
  - `dota_match_mcp_server.py`: 2606 → 206 lines
  - New `src/tools/` directory with modular tool registration:
    - `replay_tools.py` - Replay download tool
    - `combat_tools.py` - Deaths, combat log, objectives, runes, couriers
    - `fight_tools.py` - Fight detection, teamfights, fight replay
    - `match_tools.py` - Match info, timeline, draft, heroes, positions
    - `pro_scene_tools.py` - Pro players, teams, leagues, matches
    - `analysis_tools.py` - Jungle, lane, farming patterns, rotations
  - Service injection pattern via `register_all_tools(mcp, services)` coordinator
  - No functional changes - all 30+ tools work identically

### Technical

- Clean separation of concerns: each tool module handles one domain
- Services dictionary pattern for dependency injection
- Easier maintenance and testing of individual tool groups

---

## [1.0.4] - 2025-12-08

### Added

- **Hero counter picks database** integrated into `/heroes` resource:
  - 848 counter matchups with mechanical explanations (WHY a hero counters another)
  - 438 favorable matchups (heroes each hero is good against)
  - 529 "when_to_pick" conditions describing optimal draft situations
  - Curated data based on game mechanics: BKB-piercing, silences, roots, mana burn, Blademail, saves, mobility

- New fields in `dota2://heroes/all` resource:
  - `counters`: List of heroes that counter this hero with reasons
  - `good_against`: List of heroes this hero counters with reasons
  - `when_to_pick`: Draft conditions when the hero is strong

- Pydantic models for counter data in `src/models/hero_counters.py`:
  - `CounterMatchup`, `HeroCounters`, `HeroCountersDatabase`
  - `CounterPickResponse`, `DraftCounterAnalysis`, `DraftAnalysisResponse`

- `HeroesResource` methods for counter data access:
  - `get_hero_counters(hero_id)`: Get counter data for a specific hero
  - `get_all_hero_counters()`: Get all hero counter data

- `get_match_heroes` tool now includes counter picks for each hero:
  - Enables draft analysis directly from match data
  - Each hero includes counters, good_against, when_to_pick

### Changed

- `dota2://heroes/all` now includes counter picks data for draft analysis
- `get_match_heroes` enriched with counter picks for draft analysis
- Updated documentation with counter picks examples

---

## [1.0.3] - 2025-12-08

### Added

- **Combat-intensity based fight detection** - Major refactor of fight detection algorithm:
  - Fights are now detected based on hero-to-hero combat activity, not just deaths
  - Catches teamfights where teams disengage before anyone dies
  - Properly captures fight initiation phase (BKB+Blink) before first death
  - Uses intensity-based windowing to separate distinct engagements
  - Filters out harassment/poke (brief exchanges that aren't real fights)
  - New `detect_fights_from_combat()` and `get_fight_at_time_from_combat()` methods

- Extended fight highlight detection with new patterns:
  - **BKB + Blink combos**: Detects BKB + Blink → Big Ability (either order), marks first as initiator, rest as follow-ups
  - **Coordinated ultimates**: Detects when 2+ heroes from the **same team** use big teamfight abilities within 3 seconds. Includes `team` field (radiant/dire)
  - **Refresher combos**: Detects when a hero uses Refresher to double-cast an ultimate
  - **Clutch saves**: Detects self-saves (Outworld Staff, Aeon Disk) and ally saves (Glimmer Cape, Lotus Orb, Force Staff, Shadow Demon Disruption)
  - Self-save detection includes tracking what ability the hero was saved FROM (e.g., Omnislash)

- New data models in `combat_data.py`:
  - `BKBBlinkCombo`: BKB + Blink combo with `is_initiator` flag
  - `CoordinatedUltimates`: Multiple heroes ulting together with `team` field and window tracking
  - `RefresherCombo`: Refresher double ultimate with cast times
  - `ClutchSave`: Save detection with saver, save type, and ability saved from
  - `CombatWindow`: Internal dataclass for combat-intensity based fight detection

- Added `nevermore_requiem` alias to BIG_TEAMFIGHT_ABILITIES (replays use old internal name)

### Changed

- `get_fight_combat_log` now uses combat-based detection by default (captures initiation)
- Fight detection parameters tuned: 8s combat gap, 3s intensity window, 5 min events per window
- Removed `fight_initiator` and `initiation_ability` fields (replaced by `bkb_blink_combos` with `is_initiator` flag)

### Fixed

- Generic AoE detection now properly filters self-targeting (e.g., Echo Slam damaging caster)
- BKB+Blink detection now accepts either order (BKB→Blink or Blink→BKB)
- Clutch saves now require target to be "in danger" (3+ hero damage hits in 2s) to filter false positives
- Hero deaths include position coordinates and location descriptions from entity snapshots
- `significant_only` filter now excludes non-hero deaths (creep kills) from combat events
- Autoattack kills now show `"ability": "attack"` instead of `"dota_unknown"`
- Coordinated ultimates now only detects same-team coordination (was incorrectly grouping opposing team abilities)
- Team hero extraction now correctly finds all 10 heroes by scanning entity snapshots after game start

---

## [1.0.2] - 2025-12-08

### Fixed

- Fixed `get_pro_matches` and `get_league_matches` returning `null` team names
  - OpenDota API doesn't always include team names in match responses
  - Now resolves team names from cached teams data when missing
  - Eliminates need for extra `get_team` tool calls to resolve team names

- Fixed `get_match_heroes` validation error with item fields
  - Items now return human-readable names (e.g., "Blink Dagger") instead of integer IDs
  - Added `get_item_name()` and `convert_item_ids_to_names()` to constants_fetcher
  - Neutral items also converted to display names

### Added

- Model validation tests (`tests/test_model_validation.py`)
  - Tests for HeroStats, MatchHeroesResponse, MatchPlayerInfo validation
  - Tests for item ID to name conversion
  - Ensures Pydantic models reject invalid data types

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
