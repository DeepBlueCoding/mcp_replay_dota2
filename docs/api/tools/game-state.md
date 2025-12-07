# Game State Tools

High-resolution game state analysis tools. Many of these are **parallel-safe** and can be called simultaneously with different parameters.

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
