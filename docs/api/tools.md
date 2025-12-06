# Tools Reference

??? info "🤖 AI Summary"

    **Match Analysis Tools** (require `match_id`): `download_replay` (call first), `get_hero_deaths`, `get_combat_log`, `get_fight_combat_log`, `get_item_purchases`, `get_objective_kills`, `get_match_timeline`, `get_stats_at_minute`, `get_courier_kills`, `get_rune_pickups`, `get_match_draft`, `get_match_info`.

    **Game State Tools**: `list_fights`, `get_teamfights`, `get_fight`, `get_camp_stacks`, `get_jungle_summary`, `get_lane_summary`, `get_cs_at_minute`, `get_hero_positions`, `get_snapshot_at_time`, `get_position_timeline`, `get_fight_replay`.

    **Farming Analysis**: `get_farming_pattern(hero, start_minute, end_minute)` - THE tool for "how did X farm?" questions. Returns minute-by-minute lane/neutral kills, camp types, positions, transitions (first jungle, first large camp), and summary stats. **Replaces 25+ tool calls with 1 call.**

    **Rotation Analysis**: `get_rotation_analysis(start_minute, end_minute)` - THE tool for "what rotations happened?" questions. Detects when heroes leave assigned lanes, correlates with rune pickups, links outcomes to fight_ids. Returns rotations, power/wisdom rune events, and per-hero statistics.

    **Pro Scene Tools**: `search_pro_player(query)`, `search_team(query)`, `get_pro_player(account_id)`, `get_pro_player_by_name(name)`, `get_team(team_id)`, `get_team_by_name(name)`, `get_team_matches(team_id)`, `get_leagues(tier?)`, `get_pro_matches(limit?, tier?, team_name?, league_name?, days_back?)`, `get_league_matches(league_id)`.

    **Parallel-safe tools**: `get_stats_at_minute`, `get_cs_at_minute`, `get_hero_positions`, `get_snapshot_at_time`, `get_fight`, `get_position_timeline`, `get_fight_replay` - call multiple times with different parameters in parallel for efficiency.

Tools are functions the LLM can call. All match analysis tools take `match_id` as required parameter.

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

---

## download_replay

Pre-download and cache a replay file. **Use this first** before asking analysis questions about a new match. Replay files are large (50-400MB) and can take 1-5 minutes to download.

```python
download_replay(match_id=8461956309)
```

**Returns:**
```json
{
  "success": true,
  "match_id": 8461956309,
  "replay_path": "/home/user/dota2/replays/8461956309.dem",
  "file_size_mb": 398.0,
  "already_cached": false
}
```

If already cached:
```json
{
  "success": true,
  "match_id": 8461956309,
  "replay_path": "/home/user/dota2/replays/8461956309.dem",
  "file_size_mb": 398.0,
  "already_cached": true
}
```

---

## get_hero_deaths

All hero deaths in the match.

```python
get_hero_deaths(match_id=8461956309)
```

**Returns:**
```json
{
  "total_deaths": 45,
  "deaths": [
    {
      "game_time": 288,
      "game_time_str": "4:48",
      "victim": "earthshaker",
      "killer": "disruptor",
      "killer_is_hero": true,
      "ability": "disruptor_thunder_strike",
      "position": {"x": 4200, "y": 1800, "region": "dire_safelane", "location": "Dire safelane near tower"}
    }
  ]
}
```

---

## get_combat_log

Raw combat events with optional filters.

```python
get_combat_log(
    match_id=8461956309,
    start_time=280,      # optional: filter by time range
    end_time=300,
    hero_filter="earthshaker"  # optional: only events involving this hero
)
```

**Returns:**
```json
{
  "events": [
    {
      "type": "DAMAGE",
      "game_time": 285,
      "game_time_str": "4:45",
      "attacker": "disruptor",
      "attacker_is_hero": true,
      "target": "earthshaker",
      "target_is_hero": true,
      "ability": "disruptor_thunder_strike",
      "value": 160
    }
  ]
}
```

Event types: `DAMAGE`, `MODIFIER_ADD`, `MODIFIER_REMOVE`, `ABILITY`, `ITEM`, `DEATH`, `HEAL`

---

## get_fight_combat_log

Auto-detects fight boundaries around a reference time. Use this to analyze what happened leading up to a death.

```python
get_fight_combat_log(
    match_id=8461956309,
    reference_time=288,    # e.g., death time
    hero="earthshaker"     # optional: anchor detection to this hero
)
```

**Returns:**
```json
{
  "fight_start": 280,
  "fight_end": 295,
  "fight_start_str": "4:40",
  "fight_end_str": "4:55",
  "duration": 15,
  "participants": ["earthshaker", "disruptor", "naga_siren", "medusa"],
  "total_events": 47,
  "events": [...]
}
```

---

## get_item_purchases

When items were bought.

```python
get_item_purchases(
    match_id=8461956309,
    hero_filter="antimage"  # optional
)
```

**Returns:**
```json
{
  "purchases": [
    {"game_time": -89, "game_time_str": "-1:29", "hero": "antimage", "item": "item_tango"},
    {"game_time": 540, "game_time_str": "9:00", "hero": "antimage", "item": "item_bfury"}
  ]
}
```

Negative times = purchased before horn (0:00).

---

## get_objective_kills

Roshan, tormentor, towers, barracks.

```python
get_objective_kills(match_id=8461956309)
```

**Returns:**
```json
{
  "roshan_kills": [
    {"game_time": 1392, "game_time_str": "23:12", "killer": "medusa", "team": "dire", "kill_number": 1}
  ],
  "tormentor_kills": [
    {"game_time": 1215, "game_time_str": "20:15", "killer": "medusa", "team": "dire", "side": "dire"}
  ],
  "tower_kills": [
    {"game_time": 669, "game_time_str": "11:09", "tower": "dire_t1_mid", "team": "dire", "tier": 1, "lane": "mid", "killer": "nevermore"}
  ],
  "barracks_kills": [
    {"game_time": 2373, "game_time_str": "39:33", "barracks": "radiant_melee_mid", "team": "radiant", "lane": "mid", "type": "melee", "killer": "medusa"}
  ]
}
```

---

## get_match_timeline

Net worth, XP, KDA over time for all players.

```python
get_match_timeline(match_id=8461956309)
```

**Returns:**
```json
{
  "players": [
    {
      "hero": "antimage",
      "team": "dire",
      "net_worth": [500, 800, 1200, ...],  // every 30 seconds
      "hero_damage": [0, 0, 150, ...],
      "kda_timeline": [
        {"game_time": 0, "kills": 0, "deaths": 0, "assists": 0, "level": 1},
        {"game_time": 300, "kills": 0, "deaths": 0, "assists": 0, "level": 5}
      ]
    }
  ],
  "team_graphs": {
    "radiant_xp": [0, 1200, 2500, ...],
    "dire_xp": [0, 1100, 2400, ...],
    "radiant_gold": [0, 600, 1300, ...],
    "dire_gold": [0, 650, 1400, ...]
  }
}
```

---

## get_stats_at_minute

Snapshot of all players at a specific minute.

```python
get_stats_at_minute(match_id=8461956309, minute=10)
```

**Returns:**
```json
{
  "minute": 10,
  "players": [
    {
      "hero": "antimage",
      "team": "dire",
      "net_worth": 5420,
      "last_hits": 78,
      "denies": 8,
      "kills": 0,
      "deaths": 0,
      "assists": 0,
      "level": 10,
      "hero_damage": 450
    }
  ]
}
```

---

## get_courier_kills

Courier snipes.

```python
get_courier_kills(match_id=8461956309)
```

**Returns:**
```json
{
  "kills": [
    {
      "game_time": 420,
      "game_time_str": "7:00",
      "killer": "bounty_hunter",
      "killer_is_hero": true,
      "owner": "antimage",
      "team": "dire",
      "position": {"x": 2100, "y": -1500, "region": "river", "location": "River near Radiant outpost"}
    }
  ]
}
```

---

## get_rune_pickups

All rune pickups in the match.

```python
get_rune_pickups(match_id=8461956309)
```

**Returns:**
```json
{
  "pickups": [
    {
      "game_time": 0,
      "game_time_str": "0:00",
      "hero": "pangolier",
      "rune_type": "bounty"
    }
  ],
  "total_pickups": 42
}
```

---

## get_match_draft

Complete draft with bans and picks in order (for Captains Mode matches).

```python
get_match_draft(match_id=8461956309)
```

**Returns:**
```json
{
  "match_id": 8461956309,
  "game_mode": 2,
  "game_mode_name": "Captains Mode",
  "actions": [
    {"order": 1, "is_pick": false, "team": "radiant", "hero_id": 23, "hero_name": "kunkka", "localized_name": "Kunkka"},
    {"order": 8, "is_pick": true, "team": "dire", "hero_id": 89, "hero_name": "naga_siren", "localized_name": "Naga Siren"}
  ],
  "radiant_picks": [...],
  "radiant_bans": [...],
  "dire_picks": [...],
  "dire_bans": [...]
}
```

---

## get_match_info

Match metadata including teams, players, winner, duration.

```python
get_match_info(match_id=8461956309)
```

**Returns:**
```json
{
  "match_id": 8461956309,
  "is_pro_match": true,
  "league_id": 18324,
  "game_mode": 2,
  "game_mode_name": "Captains Mode",
  "winner": "dire",
  "duration_seconds": 4672,
  "duration_str": "77:52",
  "radiant_team": {"team_id": 8291895, "team_tag": "XG", "team_name": "XG"},
  "dire_team": {"team_id": 8894818, "team_tag": "FLCN", "team_name": "FLCN"},
  "players": [
    {"player_name": "Ame", "hero_name": "juggernaut", "hero_localized": "Juggernaut", "team": "radiant", "steam_id": 123456}
  ],
  "radiant_players": [...],
  "dire_players": [...]
}
```

---

# Pro Scene Tools

These tools query professional Dota 2 data from OpenDota.

## search_pro_player

Fuzzy search for pro players by name or alias.

```python
search_pro_player(query="yatoro", max_results=5)
```

**Returns:**
```json
{
  "success": true,
  "query": "yatoro",
  "total_results": 1,
  "results": [
    {"id": 311360822, "name": "Yatoro", "matched_alias": "Yatoro", "similarity": 1.0}
  ]
}
```

---

## search_team

Fuzzy search for teams by name or tag.

```python
search_team(query="spirit", max_results=5)
```

**Returns:**
```json
{
  "success": true,
  "query": "spirit",
  "total_results": 2,
  "results": [
    {"id": 8599101, "name": "Team Spirit", "matched_alias": "spirit", "similarity": 0.95}
  ]
}
```

---

## get_pro_player

Get pro player details by account ID.

```python
get_pro_player(account_id=311360822)
```

**Returns:**
```json
{
  "success": true,
  "player": {
    "account_id": 311360822,
    "name": "Yatoro",
    "personaname": "Yatoro",
    "team_id": 8599101,
    "team_name": "Team Spirit",
    "country_code": "UA",
    "fantasy_role": 1,
    "is_active": true,
    "aliases": ["yatoro", "raddan"]
  }
}
```

---

## get_pro_player_by_name

Get pro player details by name (uses fuzzy search).

```python
get_pro_player_by_name(name="Yatoro")
```

---

## get_team

Get team details by team ID.

```python
get_team(team_id=8599101)
```

**Returns:**
```json
{
  "success": true,
  "team": {
    "team_id": 8599101,
    "name": "Team Spirit",
    "tag": "Spirit",
    "rating": 1500.0,
    "wins": 450,
    "losses": 200,
    "aliases": ["ts", "spirit"]
  },
  "roster": [
    {"account_id": 311360822, "player_name": "Yatoro", "games_played": 300, "wins": 200, "is_current": true}
  ]
}
```

---

## get_team_by_name

Get team details by name (uses fuzzy search).

```python
get_team_by_name(name="Team Spirit")
```

---

## get_team_matches

Get recent matches for a team with series grouping.

```python
get_team_matches(team_id=8599101, limit=20)
```

**Returns:**
```json
{
  "success": true,
  "team_id": 8599101,
  "team_name": "Team Spirit",
  "total_matches": 20,
  "series": [
    {
      "series_id": 123,
      "series_type": "bo3",
      "games_in_series": 2,
      "wins_needed": 2,
      "radiant_team_id": 8599101,
      "dire_team_id": 7391077,
      "winner_team_id": 8599101,
      "league_name": "ESL One"
    }
  ],
  "matches": [...]
}
```

---

## get_leagues

Get all leagues/tournaments, optionally filtered by tier.

```python
get_leagues(tier="premium")  # "premium", "professional", "amateur", or None for all
```

**Returns:**
```json
{
  "success": true,
  "total_leagues": 15,
  "leagues": [
    {"league_id": 15728, "name": "The International 2023", "tier": "premium"}
  ]
}
```

---

## get_pro_matches

Get recent professional matches with series grouping. By default returns ALL matches including low-tier leagues - use filters to narrow down results.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | int | Maximum matches to return (default: 100) |
| `tier` | string | Filter by league tier: `"premium"` (TI, Majors), `"professional"`, or `"amateur"` |
| `team_name` | string | Fuzzy match team name (e.g., "OG", "Spirit", "Navi") |
| `league_name` | string | Contains match on league name (e.g., "SLAM", "ESL", "DreamLeague") |
| `days_back` | int | Only return matches from the last N days |

```python
# Get top-tier tournament matches only
get_pro_matches(tier="premium")

# Find matches for a specific team
get_pro_matches(team_name="OG")

# Find matches in a specific tournament
get_pro_matches(league_name="SLAM")

# Combine filters
get_pro_matches(tier="premium", team_name="Team Spirit", days_back=30)
```

**Returns:**
```json
{
  "success": true,
  "total_matches": 100,
  "series": [...],
  "matches": [
    {
      "match_id": 8461956309,
      "radiant_team_id": 8291895,
      "radiant_team_name": "XG",
      "dire_team_id": 8894818,
      "dire_team_name": "FLCN",
      "radiant_win": false,
      "duration": 4672,
      "league_name": "Elite League"
    }
  ]
}
```

---

## get_league_matches

Get matches from a specific league with series grouping.

```python
get_league_matches(league_id=15728, limit=50)
```

**Returns:**
```json
{
  "success": true,
  "league_id": 15728,
  "league_name": "The International 2023",
  "total_matches": 50,
  "series": [...],
  "matches": [...]
}
```

---

# Game State Tools

High-resolution game state analysis tools.

## list_fights

List all fights in a match. Fights are grouped by deaths occurring within 15 seconds of each other.

```python
list_fights(match_id=8461956309)
```

**Returns:**
```json
{
  "success": true,
  "total_fights": 12,
  "teamfights": 5,
  "skirmishes": 7,
  "total_deaths": 45,
  "fights": [
    {
      "fight_id": "fight_1",
      "start_time": "4:48",
      "total_deaths": 2,
      "participants": ["earthshaker", "disruptor"]
    }
  ]
}
```

---

## get_teamfights

Get only major teamfights (3+ deaths by default).

```python
get_teamfights(match_id=8461956309, min_deaths=3)
```

---

## get_fight

Get detailed information about a specific fight. **Parallel-safe**: call with multiple fight_ids.

```python
get_fight(match_id=8461956309, fight_id="fight_5")
```

**Returns:**
```json
{
  "success": true,
  "fight_id": "fight_5",
  "start_time": "23:15",
  "end_time": "23:42",
  "duration_seconds": 27,
  "is_teamfight": true,
  "total_deaths": 4,
  "participants": ["medusa", "earthshaker", "naga_siren", "disruptor", "pangolier"],
  "deaths": [
    {"game_time": "23:18", "killer": "medusa", "victim": "earthshaker", "ability": "medusa_stone_gaze"}
  ]
}
```

---

## get_camp_stacks

Get all neutral camp stacks in the match.

```python
get_camp_stacks(match_id=8461956309, hero_filter="crystal_maiden")
```

**Returns:**
```json
{
  "success": true,
  "total_stacks": 8,
  "stacks": [
    {"game_time": "0:53", "stacker": "crystal_maiden", "camp_type": "large", "stack_count": 2}
  ]
}
```

---

## get_jungle_summary

Overview of jungle activity - stacking efficiency by hero.

```python
get_jungle_summary(match_id=8461956309)
```

**Returns:**
```json
{
  "success": true,
  "total_stacks": 15,
  "stacks_by_hero": {"crystal_maiden": 5, "chen": 4, "medusa": 6},
  "stack_efficiency_per_10min": {"crystal_maiden": 1.2, "chen": 1.0, "medusa": 1.5}
}
```

---

## get_lane_summary

Laning phase analysis (first 10 minutes).

```python
get_lane_summary(match_id=8461956309)
```

**Returns:**
```json
{
  "success": true,
  "lane_winners": {"top": "dire", "mid": "radiant", "bot": "even"},
  "team_scores": {"radiant": 2.5, "dire": 1.5},
  "hero_stats": [
    {
      "hero": "antimage",
      "lane": "bot",
      "role": "core",
      "team": "dire",
      "last_hits_5min": 35,
      "last_hits_10min": 82,
      "gold_10min": 4850,
      "level_10min": 10
    }
  ]
}
```

---

## get_cs_at_minute

Get CS, gold, and level for all heroes at a specific minute. **Parallel-safe**: call for multiple minutes.

```python
get_cs_at_minute(match_id=8461956309, minute=10)
```

**Returns:**
```json
{
  "success": true,
  "minute": 10,
  "heroes": [
    {"hero": "antimage", "team": "dire", "last_hits": 82, "denies": 5, "gold": 4850, "level": 10}
  ]
}
```

---

## get_hero_positions

Get X,Y coordinates for all heroes at a specific minute. **Parallel-safe**: call for multiple minutes.

```python
get_hero_positions(match_id=8461956309, minute=5)
```

**Returns:**
```json
{
  "success": true,
  "minute": 5,
  "positions": [
    {"hero": "antimage", "team": "dire", "x": -5200.5, "y": -4100.2, "game_time": 300}
  ]
}
```

---

## get_snapshot_at_time

High-resolution game state at a specific second. **Parallel-safe**: call for multiple times.

```python
get_snapshot_at_time(match_id=8461956309, game_time=300.0)
```

**Returns:**
```json
{
  "success": true,
  "tick": 18000,
  "game_time": 300.0,
  "game_time_str": "5:00",
  "radiant_gold": 12500,
  "dire_gold": 11800,
  "heroes": [
    {
      "hero": "antimage",
      "team": "dire",
      "x": -5200.5,
      "y": -4100.2,
      "health": 720,
      "max_health": 720,
      "mana": 291,
      "max_mana": 291,
      "level": 7,
      "alive": true
    }
  ]
}
```

---

## get_position_timeline

Hero positions over a time range. **Parallel-safe**: call for different ranges or heroes.

```python
get_position_timeline(
    match_id=8461956309,
    start_time=300.0,
    end_time=360.0,
    hero_filter="antimage",
    interval_seconds=1.0
)
```

**Returns:**
```json
{
  "success": true,
  "heroes": [
    {
      "hero": "antimage",
      "team": "dire",
      "positions": [
        {"tick": 18000, "game_time": 300.0, "x": -5200.5, "y": -4100.2},
        {"tick": 18060, "game_time": 301.0, "x": -5180.3, "y": -4120.1}
      ]
    }
  ]
}
```

---

## get_fight_replay

High-resolution replay data for a fight. **Parallel-safe**: call for multiple fights.

```python
get_fight_replay(
    match_id=8461956309,
    start_time=1395.0,
    end_time=1420.0,
    interval_seconds=0.5
)
```

**Returns:**
```json
{
  "success": true,
  "start_time": 1395.0,
  "end_time": 1420.0,
  "total_snapshots": 50,
  "snapshots": [
    {
      "tick": 83700,
      "game_time": 1395.0,
      "game_time_str": "23:15",
      "heroes": [
        {"hero": "medusa", "team": "dire", "x": 1200.5, "y": 800.2, "health": 2100, "alive": true}
      ]
    }
  ]
}
```

---

## get_farming_pattern

Analyze a hero's farming pattern - creep kills, camp rotations, and map movement.

This is THE tool for questions about "farming pattern", "how did X farm", "when did they start jungling", or "show me the farming movement minute by minute".

```python
get_farming_pattern(
    match_id=8461956309,
    hero="antimage",
    start_minute=0,
    end_minute=15
)
```

**Returns:**
```json
{
  "success": true,
  "match_id": 8461956309,
  "hero": "antimage",
  "start_minute": 0,
  "end_minute": 15,
  "minutes": [
    {
      "minute": 5,
      "lane_creeps": 28,
      "neutral_creeps": 2,
      "position": {"x": -5200, "y": -4100},
      "gold": 2100,
      "level": 6
    },
    {
      "minute": 10,
      "lane_creeps": 52,
      "neutral_creeps": 18,
      "position": {"x": -4800, "y": -3200},
      "gold": 5200,
      "level": 11
    }
  ],
  "transitions": {
    "first_jungle_kill": "4:23",
    "first_large_camp": "5:12",
    "left_lane": "6:45"
  },
  "summary": {
    "total_lane_creeps": 85,
    "total_neutral_creeps": 42,
    "jungle_percentage": 33.1,
    "gpm": 520,
    "cs_per_min": 8.5
  }
}
```

**Example Questions This Tool Answers:**

- "What was Terrorblade's farming pattern in the first 10 minutes?"
- "When did Anti-Mage start jungling?"
- "Which camps did Luna clear between minutes 5-15?"
- "How did the carry move across the map while farming?"

---

## get_rotation_analysis

Analyze hero rotations - movement patterns between lanes, rune correlations, and outcomes.

This is THE tool for questions about rotations, ganks, mid rotations after rune pickups, or support movements between lanes.

```python
get_rotation_analysis(
    match_id=8461956309,
    start_minute=0,
    end_minute=20
)
```

**Returns:**
```json
{
  "success": true,
  "match_id": 8461956309,
  "start_minute": 0,
  "end_minute": 20,
  "rotations": [
    {
      "rotation_id": "rot_1",
      "hero": "nevermore",
      "role": "mid",
      "game_time": 365.0,
      "game_time_str": "6:05",
      "from_lane": "mid",
      "to_lane": "bot",
      "rune_before": {
        "rune_type": "haste",
        "pickup_time": 362.0,
        "pickup_time_str": "6:02",
        "seconds_before_rotation": 3.0
      },
      "outcome": {
        "type": "kill",
        "fight_id": "fight_3",
        "deaths_in_window": 1,
        "rotation_hero_died": false,
        "kills_by_rotation_hero": ["antimage"]
      },
      "travel_time_seconds": 45.0,
      "returned_to_lane": true,
      "return_time_str": "7:30"
    }
  ],
  "rune_events": {
    "power_runes": [
      {
        "spawn_time": 360.0,
        "spawn_time_str": "6:00",
        "location": "top",
        "taken_by": "nevermore",
        "pickup_time": 362.0,
        "led_to_rotation": true,
        "rotation_id": "rot_1"
      }
    ],
    "wisdom_runes": [
      {
        "spawn_time": 420.0,
        "spawn_time_str": "7:00",
        "location": "radiant_jungle",
        "contested": true,
        "fight_id": "fight_4",
        "deaths_nearby": 2
      }
    ]
  },
  "summary": {
    "total_rotations": 8,
    "by_hero": {
      "nevermore": {
        "hero": "nevermore",
        "role": "mid",
        "total_rotations": 3,
        "successful_ganks": 2,
        "failed_ganks": 0,
        "trades": 1,
        "rune_rotations": 3
      }
    },
    "runes_leading_to_kills": 4,
    "wisdom_rune_fights": 2,
    "most_active_rotator": "nevermore"
  }
}
```

**Key Features:**

- **Rotation Detection**: Tracks when heroes leave their assigned lane and go to another lane
- **Rune Correlation**: Links power rune pickups (within 60s) to subsequent rotations
- **Fight Outcome**: Determines if rotation resulted in kill, death, trade, or no engagement
- **Fight Linking**: Provides `fight_id` - use `get_fight(fight_id)` for detailed combat log
- **Wisdom Rune Fights**: Detects contested wisdom rune spawns with deaths nearby

**Outcome Types:**

| Type | Description |
|------|-------------|
| `kill` | Rotating hero got a kill without dying |
| `died` | Rotating hero died without getting a kill |
| `traded` | Rotating hero got a kill but also died |
| `fight` | Rotation led to a fight but no kills by/on rotating hero |
| `no_engagement` | No deaths occurred within 60s of rotation |

**Example Questions This Tool Answers:**

- "How many rotations did the mid player make after power runes?"
- "Which rotations resulted in kills vs deaths?"
- "Were there any fights at wisdom rune spawns?"
- "Who was the most active rotator in the early game?"
- "Did the mid rotate after the 6-minute rune?"
