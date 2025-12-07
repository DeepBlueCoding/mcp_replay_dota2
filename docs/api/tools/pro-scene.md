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
