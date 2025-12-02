# Match Analysis Examples

## Analyzing a Team Fight

To understand what happened in a team fight:

1. First, get all hero deaths to find when fights occurred:

```python
deaths = get_hero_deaths(match_id=8461956309)
# Find a death of interest, e.g., at game_time=1234
```

2. Get the full combat log for that fight:

```python
fight = get_fight_combat_log(
    match_id=8461956309,
    reference_time=1234,
    hero="earthshaker"
)

# Returns:
# - fight_start, fight_end: When the fight started/ended
# - participants: All heroes involved
# - events: Full combat log
```

3. Analyze the fight events to understand:
   - Who initiated
   - Key abilities used
   - Damage dealt by each hero
   - Who died and in what order

## Tracking Item Timings

To analyze a carry's item progression:

```python
purchases = get_item_purchases(
    match_id=8461956309,
    hero_filter="antimage"
)

# Returns chronological list of items:
# [
#   {"game_time": -60, "item": "item_tango"},
#   {"game_time": 120, "item": "item_quelling_blade"},
#   {"game_time": 840, "item": "item_bfury"},
#   {"game_time": 1200, "item": "item_manta"},
#   ...
# ]
```

## Laning Phase Analysis

To analyze the laning phase (first 10 minutes):

```python
# Get stats at minute 10
stats = get_stats_at_minute(match_id=8461956309, minute=10)

# Compare carries:
# - Net worth differential
# - Last hits
# - Hero damage (for trading)
# - Deaths (ganks)
```

## Objective Control

To see when objectives were taken:

```python
objectives = get_objective_kills(match_id=8461956309)

# Roshan timings
for rosh in objectives["roshan_kills"]:
    print(f"Rosh #{rosh['kill_number']} at {rosh['game_time_str']} by {rosh['team']}")

# Tower progression
for tower in objectives["tower_kills"]:
    print(f"T{tower['tier']} {tower['lane']} at {tower['game_time_str']}")
```

## Using Resources for Context

Resources provide static context data:

```python
# Get map positions for landmark references
map_data = resource("dota2://map")

# Tower positions for analyzing pushes
towers = map_data["towers"]

# Neutral camps for farming patterns
camps = map_data["neutral_camps"]
```

## Combining Tools for Analysis

Example: "Why did the carry lose their lane?"

```python
# 1. Get player stats at 10 min
stats = get_stats_at_minute(match_id, minute=10)
carry_stats = stats["players"][0]

# 2. Get deaths in first 10 min
deaths = get_hero_deaths(match_id)
early_deaths = [d for d in deaths["deaths"] if d["game_time"] < 600]

# 3. For each death, get the fight context
for death in early_deaths:
    if death["victim"] == "antimage":
        fight = get_fight_combat_log(match_id, death["game_time"], "antimage")
        # Analyze who rotated, abilities used, etc.

# 4. Get timeline for CS comparison
timeline = get_match_timeline(match_id)
```

The model can synthesize all this data to explain:
- How many times the carry died
- Who ganked them
- What abilities were used
- How it affected their farm
