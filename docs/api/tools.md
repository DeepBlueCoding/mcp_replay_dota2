# Tools Reference

<details>
<summary><strong>🤖 AI Summary</strong></summary>

**Match Analysis Tools** (require `match_id`): `download_replay` (call first), `get_hero_deaths`, `get_combat_log`, `get_fight_combat_log`, `get_item_purchases`, `get_objective_kills`, `get_match_timeline`, `get_stats_at_minute`, `get_courier_kills`, `get_rune_pickups`, `get_match_draft`, `get_match_info`.

**Pro Scene Tools**: `search_pro_player(query)`, `search_team(query)`, `get_pro_player(account_id)`, `get_pro_player_by_name(name)`, `get_team(team_id)`, `get_team_by_name(name)`, `get_team_matches(team_id)`, `get_leagues(tier?)`, `get_pro_matches(limit?)`, `get_league_matches(league_id)`.

</details>

Tools are functions the LLM can call. All tools take `match_id` as required parameter.

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

Get recent professional matches with series grouping.

```python
get_pro_matches(limit=100)
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
