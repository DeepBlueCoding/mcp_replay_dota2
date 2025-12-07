# Farming & Rotation Tools

High-level analysis tools that aggregate data from multiple sources to answer complex gameplay questions.

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
      "lane_creeps_killed": 28,
      "camps_cleared": 2,
      "camp_sequence": [
        {"time_str": "5:12", "camp": "large_centaur", "tier": "large", "area": "radiant_jungle"},
        {"time_str": "5:45", "camp": "medium_wolf", "tier": "medium", "area": "radiant_jungle"}
      ],
      "position_at_start": {"x": -5200, "y": -4100, "area": "radiant_safelane"},
      "gold": 2100,
      "level": 6
    }
  ],
  "creep_kills": [
    {
      "game_time": 312.5,
      "game_time_str": "5:12",
      "creep_name": "npc_dota_neutral_centaur_khan",
      "creep_type": "neutral",
      "neutral_camp": "large_centaur",
      "camp_tier": "large",
      "map_area": "radiant_jungle"
    }
  ],
  "multi_camp_clears": [
    {
      "time_str": "14:05",
      "camps": ["large_centaur", "medium_wolf"],
      "duration_seconds": 1.1,
      "creeps_killed": 4,
      "area": "dire_jungle"
    }
  ],
  "transitions": {
    "first_jungle_kill_str": "4:23",
    "first_large_camp_str": "5:12",
    "left_lane_str": "6:45"
  },
  "summary": {
    "total_lane_creeps": 85,
    "total_neutral_creeps": 42,
    "jungle_percentage": 33.1,
    "gpm": 520.0,
    "cs_per_min": 8.5,
    "multi_camp_clears": 3
  }
}
```

**Key Fields:**

| Field | Description |
|-------|-------------|
| `camp_sequence` | Ordered list of camps cleared each minute |
| `creep_kills[].camp_tier` | Tier from replay parser: `small`, `medium`, `large`, `ancient` |
| `multi_camp_clears` | Detects when hero farms 2+ camps simultaneously (stacked/adjacent camps) |
| `summary.multi_camp_clears` | Total count of multi-camp clear events |

**Multi-Camp Detection:**

Detects heroes like Medusa or Luna farming stacked or adjacent camps with AoE abilities. A multi-camp clear is recorded when creeps from 2+ different camp types are killed within 3 seconds.

**Example Questions This Tool Answers:**

- "What was Terrorblade's farming pattern in the first 10 minutes?"
- "When did Anti-Mage start jungling?"
- "Which camps did Luna clear between minutes 5-15?"
- "How did the carry move across the map while farming?"
- "Did Medusa farm stacked camps? How efficiently?"

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
