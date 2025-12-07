# Tools Reference

??? info "AI Summary"

    **Match Analysis Tools** (require `match_id`): `download_replay` (call first), `get_hero_deaths`, `get_combat_log`, `get_fight_combat_log`, `get_item_purchases`, `get_objective_kills`, `get_match_timeline`, `get_stats_at_minute`, `get_courier_kills`, `get_rune_pickups`, `get_match_draft`, `get_match_info`, `get_match_heroes`, `get_match_players`.

    **Game State Tools**: `list_fights`, `get_teamfights`, `get_fight`, `get_camp_stacks`, `get_jungle_summary`, `get_lane_summary`, `get_cs_at_minute`, `get_hero_positions`, `get_snapshot_at_time`, `get_position_timeline`, `get_fight_replay`.

    **Farming Analysis**: `get_farming_pattern(hero, start_minute, end_minute)` - THE tool for "how did X farm?" questions. Returns minute-by-minute lane/neutral kills, camp types, positions, transitions (first jungle, first large camp), and summary stats. **Replaces 25+ tool calls with 1 call.**

    **Rotation Analysis**: `get_rotation_analysis(start_minute, end_minute)` - THE tool for "what rotations happened?" questions. Detects when heroes leave assigned lanes, correlates with rune pickups, links outcomes to fight_ids. Returns rotations, power/wisdom rune events, and per-hero statistics.

    **Pro Scene Tools**: `search_pro_player(query)`, `search_team(query)`, `get_pro_player(account_id)`, `get_pro_player_by_name(name)`, `get_team(team_id)`, `get_team_by_name(name)`, `get_team_matches(team_id)`, `get_leagues(tier?)`, `get_pro_matches(limit?, tier?, team_name?, league_name?, days_back?)`, `get_league_matches(league_id)`.

    **Parallel-safe tools**: `get_stats_at_minute`, `get_cs_at_minute`, `get_hero_positions`, `get_snapshot_at_time`, `get_fight`, `get_position_timeline`, `get_fight_replay` - call multiple times with different parameters in parallel for efficiency.

Tools are functions the LLM can call. All match analysis tools take `match_id` as required parameter.

## Tool Categories

| Category | Description | Tools |
|----------|-------------|-------|
| [Match Analysis](match-analysis.md) | Query match events, deaths, items, timeline | 14 tools |
| [Pro Scene](pro-scene.md) | Search players, teams, leagues, pro matches | 10 tools |
| [Game State](game-state.md) | High-resolution positions, snapshots, fights | 11 tools |
| [Farming & Rotation](farming-rotation.md) | Farming patterns and rotation analysis | 2 tools |

## Parallel Tool Execution

Many tools are **parallel-safe** and can be called simultaneously with different parameters. This significantly speeds up analysis when comparing multiple time points or fights.

### Parallel-Safe Tools

| Tool | Parallelize By |
|------|----------------|
| `get_stats_at_minute` | Different minutes (e.g., 10, 20, 30) |
| `get_cs_at_minute` | Different minutes (e.g., 5, 10, 15) |
| `get_hero_positions` | Different minutes |
| `get_snapshot_at_time` | Different game times |
| `get_fight` | Different fight_ids |
| `get_position_timeline` | Different time ranges or heroes |
| `get_fight_replay` | Different fights |

### Example: Laning Analysis

Instead of calling sequentially:
```python
# Slow - sequential calls
get_cs_at_minute(match_id=123, minute=5)
get_cs_at_minute(match_id=123, minute=10)
```

Call both in parallel:
```python
# Fast - parallel calls in same LLM response
get_cs_at_minute(match_id=123, minute=5)  # AND
get_cs_at_minute(match_id=123, minute=10)
```

The LLM can issue multiple tool calls in a single response, and the runtime executes them concurrently.
