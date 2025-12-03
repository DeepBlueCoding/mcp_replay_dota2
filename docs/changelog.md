# Changelog

??? info "🤖 AI Summary"

    Project changelog following Keep a Changelog format. Current features: MCP resources (heroes, map, match data), MCP tools (deaths, combat log, fights, items, objectives, timeline), map geometry data, combat log parsing with fight detection, hero fuzzy search.

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

#### Pro Scene Features
- Pro scene resources: `dota2://pro/players`, `dota2://pro/teams`, `dota2://pro/player/{id}`, `dota2://pro/team/{id}`
- Pro scene tools: `search_pro_player`, `search_team`, `get_pro_player`, `get_pro_player_by_name`, `get_team`, `get_team_by_name`, `get_team_matches`, `get_leagues`, `get_pro_matches`, `get_league_matches`
- Series grouping for pro matches (Bo1/Bo3/Bo5 detection, winner calculation)
- Fuzzy search for players and teams with alias support

#### Match Analysis Tools
- `get_rune_pickups` - Track rune pickups by hero
- `get_match_draft` - Complete draft order for Captains Mode
- `get_match_info` - Match metadata (teams, players, winner, duration)
- `download_replay` - Pre-cache replay files before analysis

#### Core Features
- MCP Resources: `dota2://heroes/all`, `dota2://map`, `dota2://match/{id}/heroes`, `dota2://match/{id}/players`
- MCP Tools: `get_match_timeline`, `get_stats_at_minute`, `get_hero_deaths`, `get_combat_log`, `get_fight_combat_log`, `get_item_purchases`, `get_courier_kills`, `get_objective_kills`
- Map data with tower, barracks, neutral camp, rune, and landmark positions
- Combat log parsing with fight detection
- Timeline parsing from replay metadata
- Hero fuzzy search for name matching
- MkDocs documentation with Material theme
- AI Summary sections on all documentation pages

### Changed
- N/A

### Fixed
- N/A
