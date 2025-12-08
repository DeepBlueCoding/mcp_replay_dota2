# Changelog

??? info "🤖 AI Summary"

    Project changelog following Keep a Changelog format. Current features: MCP resources (heroes, map, match data), MCP tools (deaths, combat log, fights, items, objectives, timeline), map geometry data, combat log parsing with fight detection, hero fuzzy search, farming pattern analysis, rotation analysis with rune correlation.

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

#### Fight Highlights Detection
- `get_fight_combat_log` now returns `highlights` with key teamfight moments:
  - **Multi-hero abilities**: Detects Chronosphere, Black Hole, Ravage, etc. hitting 2+ heroes
  - **Kill streaks**: Double kill through Rampage (uses Dota 2's 18-second window)
  - **Team wipes (Aces)**: All 5 heroes of one team killed in a fight
  - **Fight initiation**: Who started the fight and with what ability
- 60+ teamfight abilities tracked (ultimates and key crowd control)

#### Pydantic Response Models
- All MCP tools now return properly typed Pydantic models with Field descriptions
- New `src/models/tool_responses.py` with comprehensive models:
  - Timeline: `KDASnapshot`, `PlayerTimeline`, `TeamGraphs`, `MatchTimelineResponse`
  - Match info: `HeroStats`, `MatchPlayerInfo`, `MatchHeroesResponse`
  - Fights: `FightSummary`, `FightDeath`, `FightDeathDetail`, `FightListResponse`
  - Lane/jungle: `CampStack`, `HeroLaneStats`, `LaneWinners`, `JungleSummaryResponse`
  - Game state: `HeroSnapshot`, `HeroPosition`, `PositionPoint`, `SnapshotAtTimeResponse`
- Better developer experience with IDE autocomplete and documentation

#### Pro Scene Signature Heroes
- `ProPlayerInfo` now includes `role` (position 1-5) and `signature_heroes` fields
- Signature heroes loaded from `data/pro_scene/player_signature_heroes.json`
- Example: Yatoro → Morphling, Slark, Faceless Void

### Changed

#### Single-Pass Replay Parsing
- `ReplayService._parse_replay` now fetches CDOTAMatchMetadataFile in the same pass
- Removed second parsing pass that was causing CI timeouts
- Timeline data now available without performance penalty

#### Dota 2 Game Knowledge in Server Instructions
- Added comprehensive laning phase roles documentation (Position 1-5 responsibilities)
- Added "Common Analysis Mistakes to AVOID" section for better match analysis
- Added "What Actually Creates Space" guidance for strategic understanding

#### Enhanced Lane Summary
- `get_lane_summary` now fetches OpenDota data for authoritative lane assignments
- Lane names and roles from OpenDota override replay-derived heuristics

#### Constants Fetcher
- Added `get_hero_name(hero_id)` method to convert hero IDs to internal names

### Changed

#### ReplayService as Main Entry Point
- `ReplayService.get_parsed_data(match_id)` is now the single entry point for all replay data
- Parses `CDOTAMatchMetadataFile` for timeline metadata in addition to combat log
- All tools now use `get_parsed_data()` instead of `download_only()` + separate parsing

#### Parsers Use ParsedReplayData Directly
- `timeline_parser.parse_timeline()` now accepts `ParsedReplayData` instead of `Path`
- `match_info_parser.get_draft()` now accepts `ParsedReplayData` instead of `Path`
- `match_info_parser.get_match_info()` now accepts `ParsedReplayData` instead of `Path`
- Entity snapshots now use v2 `snap.heroes` instead of `snap.players`

#### FightService Default
- `get_fight_combat_log` now defaults to `significant_only=True` for cleaner output

### Removed

#### Deprecated Modules
- Removed `src/utils/combat_log_parser.py` (replaced by v2 services)
- Removed `src/utils/replay_cache.py` (replaced by `src/services/cache/replay_cache.py`)

#### Parallel Tool Execution
- Added parallel-safe hints to tool descriptions for LLM optimization
- Tools marked as parallel-safe: `get_stats_at_minute`, `get_cs_at_minute`, `get_hero_positions`, `get_snapshot_at_time`, `get_fight`, `get_position_timeline`, `get_fight_replay`
- Server instructions now include guidance on parallel tool calls for efficiency

#### Farming Pattern Analysis
- `get_farming_pattern` - Analyze a hero's farming pattern with minute-by-minute breakdown
  - Lane creeps vs neutral creeps killed per minute
  - Neutral camp type identification (satyr, centaur, kobold, etc.)
  - Hero position tracking across the map
  - Key transitions: first jungle kill, first large camp, when they left lane
  - Summary stats: jungle %, GPM, CS/min, camps cleared by type
  - Reduces 25+ tool calls to a single tool call for "farming pattern" questions
  - Designed to answer: "How did X farm?", "When did they start jungling?", "Which camps did they clear?"

#### Rotation Analysis
- `get_rotation_analysis` - Analyze hero rotations between lanes
  - Rotation detection: tracks when heroes leave assigned lane
  - Rune correlation: links power rune pickups to subsequent rotations
  - Fight outcome: kill, died, traded, fight, or no_engagement
  - Fight linking: provides `fight_id` to use with `get_fight()` for combat details
  - Power rune events: tracks 6:00, 8:00, etc. spawns with who took them
  - Wisdom rune events: detects contested wisdom runes with deaths nearby
  - Per-hero statistics: total rotations, success rate, rune-assisted rotations
  - Designed to answer: "Did mid rotate after runes?", "Which rotations resulted in kills?", "Were wisdom runes contested?"

#### Game State Tools
- `list_fights` - List all fights with teamfight/skirmish classification
- `get_teamfights` - Get major teamfights (3+ deaths)
- `get_fight` - Detailed fight information with positions
- `get_camp_stacks` - Neutral camp stacking events
- `get_jungle_summary` - Stacking efficiency by hero
- `get_lane_summary` - Laning phase winners and hero stats
- `get_cs_at_minute` - CS/gold/level at specific minute
- `get_hero_positions` - Hero positions at specific minute
- `get_snapshot_at_time` - High-resolution game state at specific time
- `get_position_timeline` - Hero movement over time range
- `get_fight_replay` - High-resolution replay data for fights

#### Pro Scene Features
- Pro scene resources: `dota2://pro/players`, `dota2://pro/teams`
- Pro scene tools: `search_pro_player`, `search_team`, `get_pro_player`, `get_pro_player_by_name`, `get_team`, `get_team_by_name`, `get_team_matches`, `get_leagues`, `get_pro_matches`, `get_league_matches`
- Series grouping for pro matches (Bo1/Bo3/Bo5 detection, winner calculation)
- Fuzzy search for players and teams with alias support
- **NEW**: `get_pro_matches` filtering options: `tier`, `team_name`, `league_name`, `days_back` - helps narrow down results to relevant matches

#### Match Analysis Tools
- `get_match_heroes` - Get 10 heroes in match with KDA, items, stats
- `get_match_players` - Get 10 players with names and hero assignments
- `get_rune_pickups` - Track rune pickups by hero
- `get_match_draft` - Complete draft order for Captains Mode
- `get_match_info` - Match metadata (teams, players, winner, duration)
- `download_replay` - Pre-cache replay files before analysis

#### Core Features
- MCP Resources: `dota2://heroes/all`, `dota2://map`, `dota2://pro/players`, `dota2://pro/teams`
- MCP Tools: `get_match_timeline`, `get_stats_at_minute`, `get_hero_deaths`, `get_combat_log`, `get_fight_combat_log`, `get_item_purchases`, `get_courier_kills`, `get_objective_kills`
- Map data with tower, barracks, neutral camp, rune, and landmark positions
- Combat log parsing with fight detection
- Timeline parsing from replay metadata
- Hero fuzzy search for name matching
- MkDocs documentation with Material theme
- AI Summary sections on all documentation pages

### Changed
- Refactored parameterized resources to tools following MCP design principles:
  - Removed `dota2://match/{id}/heroes` → use `get_match_heroes(match_id)` tool
  - Removed `dota2://match/{id}/players` → use `get_match_players(match_id)` tool
  - Removed `dota2://pro/player/{id}` → use `get_pro_player(account_id)` tool
  - Removed `dota2://pro/team/{id}` → use `get_team(team_id)` tool
- Resources now only contain static reference data (all heroes, map, all pro players/teams)
- Tools are used for dynamic data that requires computation or parameters

### Fixed
- N/A
