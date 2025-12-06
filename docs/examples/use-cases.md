# Real Use Cases

??? info "🤖 AI Summary"

    Example LLM conversations: **Lost teamfight** - `get_hero_deaths` → `get_fight_combat_log` → analyze initiation, counters, positioning. **Carry farm tracking** - `get_item_purchases` → `get_stats_at_minute` → compare CS, deaths, item timings. **Farming pattern** - `get_farming_pattern` → minute-by-minute lane/jungle breakdown, camp types, transitions. **Rotation analysis** - `get_rotation_analysis` → detect mid rotations after runes, outcomes (kill/died/traded), wisdom rune fights. **Gank analysis** - deaths with position → fight log → identify root, damage chain, positioning mistake. **Roshan control** - `get_objective_kills` → timeline of objectives. **Laning comparison** - `get_stats_at_minute(10)` → compare LH, denies, net worth, level.

These are example conversations showing how an LLM uses the MCP tools to analyze matches.

## Analyzing a Lost Teamfight

**User:** "In match 8461956309, we lost a big fight around 25 minutes. What went wrong?"

**LLM thinks:** I need to find deaths around minute 25 and analyze the fight.

**LLM calls:** `get_hero_deaths(match_id=8461956309)`

**Tool returns:**
```json
{
  "deaths": [
    {"game_time": 1487, "game_time_str": "24:47", "victim": "pangolier", "killer": "medusa", "ability": "medusa_split_shot"},
    {"game_time": 1492, "game_time_str": "24:52", "victim": "earthshaker", "killer": "disruptor", "ability": "disruptor_static_storm"},
    {"game_time": 1495, "game_time_str": "24:55", "victim": "nevermore", "killer": "naga_siren", "ability": "naga_siren_rip_tide"},
    {"game_time": 1498, "game_time_str": "24:58", "victim": "dawnbreaker", "killer": "medusa", "ability": "medusa_mystic_snake"}
  ]
}
```

**LLM calls:** `get_fight_combat_log(match_id=8461956309, reference_time=1492, hero="earthshaker")`

**Tool returns:**
```json
{
  "fight_start": 1480,
  "fight_end": 1502,
  "duration": 22,
  "participants": ["pangolier", "earthshaker", "nevermore", "dawnbreaker", "medusa", "disruptor", "naga_siren", "luna", "necrophos"],
  "events": [
    {"type": "ABILITY", "game_time": 1481, "attacker": "earthshaker", "ability": "earthshaker_echo_slam", "value": 0},
    {"type": "DAMAGE", "game_time": 1481, "attacker": "earthshaker", "target": "medusa", "ability": "earthshaker_echo_slam", "value": 287},
    {"type": "MODIFIER_ADD", "game_time": 1482, "attacker": "disruptor", "target": "earthshaker", "ability": "disruptor_static_storm"},
    {"type": "DAMAGE", "game_time": 1485, "attacker": "medusa", "target": "pangolier", "ability": "medusa_split_shot", "value": 412},
    ...
  ]
}
```

**LLM responds:**

> The fight at 24:47 was a disaster for Radiant. Here's what happened:
>
> 1. **Earthshaker initiated with Echo Slam** at 24:41, hitting all 5 Dire heroes but dealing low damage (287 on Medusa) - likely because enemies were spread out
>
> 2. **Disruptor immediately countered** with Static Storm on Earthshaker, silencing him and preventing follow-up
>
> 3. **Medusa was the problem** - she had Split Shot farming Pangolier while tanking the initiation, then cleaned up with 3 kills
>
> 4. **4 Radiant deaths in 11 seconds** - Pangolier, Earthshaker, Nevermore, Dawnbreaker
>
> The issue: Earthshaker jumped in without BKB against a Disruptor. The moment he was silenced, Radiant had no follow-up damage and Medusa shredded everyone.

---

## Tracking Carry Farm

**User:** "How did their Anti-Mage get Battle Fury so fast in match 8461956309?"

**LLM calls:** `get_item_purchases(match_id=8461956309, hero_filter="antimage")`

**Tool returns:**
```json
{
  "purchases": [
    {"game_time": -89, "game_time_str": "-1:29", "item": "item_tango"},
    {"game_time": -89, "game_time_str": "-1:29", "item": "item_quelling_blade"},
    {"game_time": -89, "game_time_str": "-1:29", "item": "item_slippers"},
    {"game_time": 180, "game_time_str": "3:00", "item": "item_ring_of_health"},
    {"game_time": 420, "game_time_str": "7:00", "item": "item_boots"},
    {"game_time": 540, "game_time_str": "9:00", "item": "item_bfury"},
    {"game_time": 780, "game_time_str": "13:00", "item": "item_manta"}
  ]
}
```

**LLM calls:** `get_stats_at_minute(match_id=8461956309, minute=9)`

**Tool returns:**
```json
{
  "players": [
    {"hero": "antimage", "last_hits": 78, "net_worth": 5420, "kills": 0, "deaths": 0},
    {"hero": "nevermore", "last_hits": 62, "net_worth": 4100, "kills": 1, "deaths": 1}
  ]
}
```

**LLM responds:**

> Anti-Mage got a 9-minute Battle Fury, which is quite fast. Here's how:
>
> - **78 last hits by minute 9** - excellent lane farming
> - **0 deaths** - completely free lane, no pressure
> - **Ring of Health at 3:00** - sustain let him stay in lane indefinitely
>
> Compare to Nevermore mid who had 62 CS but died once - that death probably cost 300-400 gold and 30 seconds of farm.
>
> The real question is why Radiant's offlane didn't pressure AM. A 9-minute BFury usually means the safelane was uncontested.

---

## Understanding a Gank

**User:** "I was playing Earthshaker and got killed at first blood. What could I have done differently?"

**LLM calls:** `get_hero_deaths(match_id=8461956309)`

**Tool returns:**
```json
{
  "deaths": [
    {"game_time": 288, "game_time_str": "4:48", "victim": "earthshaker", "killer": "disruptor", "ability": "disruptor_thunder_strike", "position": {"x": 4200, "y": 1800, "region": "dire_safelane"}}
  ]
}
```

**LLM calls:** `get_fight_combat_log(match_id=8461956309, reference_time=288, hero="earthshaker")`

**Tool returns:**
```json
{
  "fight_start": 280,
  "fight_end": 290,
  "participants": ["earthshaker", "disruptor", "naga_siren", "medusa"],
  "events": [
    {"type": "MODIFIER_ADD", "game_time": 281, "attacker": "naga_siren", "target": "earthshaker", "ability": "naga_siren_ensnare"},
    {"type": "DAMAGE", "game_time": 282, "attacker": "disruptor", "target": "earthshaker", "ability": "disruptor_thunder_strike", "value": 160},
    {"type": "DAMAGE", "game_time": 284, "attacker": "medusa", "target": "earthshaker", "ability": "medusa_mystic_snake", "value": 140},
    {"type": "DAMAGE", "game_time": 286, "attacker": "naga_siren", "target": "earthshaker", "value": 58},
    {"type": "DEATH", "game_time": 288, "target": "earthshaker", "attacker": "disruptor"}
  ]
}
```

**LLM responds:**

> Here's what happened at first blood (4:48):
>
> 1. **Naga Siren caught you with Ensnare** at 4:41 - 3-second root
> 2. **Disruptor followed with Thunder Strike** - 160 damage over time
> 3. **Medusa hit you with Mystic Snake** - another 140 damage
> 4. **You died in 8 seconds** without being able to act
>
> **Position:** You were at x:4200, y:1800 - that's deep in Dire safelane near the tower.
>
> **What went wrong:** You were too far forward against a Naga (root) + Disruptor (slow + damage) dual lane. Once Naga lands Ensnare, you have no escape without Fissure (and even then it's not a disjoint).
>
> **What to do differently:**
> - Stay near trees for juke paths
> - Don't contest pulls against this lane - Naga root is too punishing
> - Play for XP, not kills - ES needs level 6 to fight this lane

---

## Objective Control Analysis

**User:** "When did Roshan die and who took the Aegis?"

**LLM calls:** `get_objective_kills(match_id=8461956309)`

**Tool returns:**
```json
{
  "roshan_kills": [
    {"game_time": 1392, "game_time_str": "23:12", "killer": "medusa", "team": "dire", "kill_number": 1},
    {"game_time": 2040, "game_time_str": "34:00", "killer": "medusa", "team": "dire", "kill_number": 2},
    {"game_time": 2580, "game_time_str": "43:00", "killer": "luna", "team": "dire", "kill_number": 3},
    {"game_time": 3120, "game_time_str": "52:00", "killer": "medusa", "team": "dire", "kill_number": 4}
  ],
  "tower_kills": [
    {"game_time": 669, "game_time_str": "11:09", "tower": "dire_t1_mid", "killer": "nevermore"},
    {"game_time": 1440, "game_time_str": "24:00", "tower": "radiant_t1_bot", "killer": "medusa"}
  ]
}
```

**LLM responds:**

> **Roshan Timeline:**
>
> | Rosh # | Time | Killer | Team |
> |--------|------|--------|------|
> | 1 | 23:12 | Medusa | Dire |
> | 2 | 34:00 | Medusa | Dire |
> | 3 | 43:00 | Luna | Dire |
> | 4 | 52:00 | Medusa | Dire |
>
> Dire took **all 4 Roshans**. Medusa got 3 of them personally - she was likely the Aegis carrier for most of the game.
>
> This is a big factor in why the game went late - Medusa with Aegis is extremely hard to kill, and Dire maintained complete Roshan control throughout.

---

## Comparing Laning Phase

**User:** "Compare the midlaners at 10 minutes"

**LLM calls:** `get_stats_at_minute(match_id=8461956309, minute=10)`

**Tool returns:**
```json
{
  "players": [
    {"hero": "nevermore", "team": "radiant", "last_hits": 68, "denies": 12, "net_worth": 4800, "kills": 2, "deaths": 0, "level": 11},
    {"hero": "pangolier", "team": "dire", "last_hits": 45, "denies": 3, "net_worth": 3200, "kills": 0, "deaths": 1, "level": 9}
  ]
}
```

**LLM responds:**

> **Mid Lane at 10:00 - Nevermore vs Pangolier:**
>
> | Stat | Nevermore (Radiant) | Pangolier (Dire) |
> |------|---------------------|------------------|
> | Last Hits | 68 | 45 |
> | Denies | 12 | 3 |
> | Net Worth | 4,800 | 3,200 |
> | K/D/A | 2/0/? | 0/1/? |
> | Level | 11 | 9 |
>
> **Nevermore dominated the lane:**
> - +23 CS advantage
> - +9 denies
> - +1,600 net worth
> - +2 levels
>
> Shadow Fiend's early damage from Necromastery stacks makes him strong in the 1v1. Pangolier likely struggled to last hit under tower after SF established raze control.

---

## Analyzing Carry Farming Pattern

**User:** "What was Anti-Mage's farming pattern in the first 10 minutes? When did he start jungling?"

**LLM calls:** `get_farming_pattern(match_id=8461956309, hero="antimage", start_minute=0, end_minute=10)`

**Tool returns:**
```json
{
  "success": true,
  "hero": "antimage",
  "minutes": [
    {"minute": 1, "lane_creeps_killed": 4, "neutral_creeps_killed": 0, "map_area": "dire_safelane", "gold": 320, "last_hits": 4},
    {"minute": 2, "lane_creeps_killed": 6, "neutral_creeps_killed": 0, "map_area": "dire_safelane", "gold": 580, "last_hits": 10},
    {"minute": 3, "lane_creeps_killed": 8, "neutral_creeps_killed": 0, "map_area": "dire_safelane", "gold": 890, "last_hits": 18},
    {"minute": 4, "lane_creeps_killed": 7, "neutral_creeps_killed": 0, "map_area": "dire_safelane", "gold": 1150, "last_hits": 25},
    {"minute": 5, "lane_creeps_killed": 5, "neutral_creeps_killed": 3, "neutral_camps_detail": {"medium wolf": 2, "small kobold": 1}, "map_area": "dire_jungle", "gold": 1580, "last_hits": 33},
    {"minute": 6, "lane_creeps_killed": 4, "neutral_creeps_killed": 5, "neutral_camps_detail": {"large centaur": 3, "medium wolf": 2}, "map_area": "dire_jungle", "gold": 2100, "last_hits": 42},
    {"minute": 7, "lane_creeps_killed": 3, "neutral_creeps_killed": 6, "neutral_camps_detail": {"large satyr": 4, "medium harpy": 2}, "map_area": "dire_jungle", "gold": 2680, "last_hits": 51},
    {"minute": 8, "lane_creeps_killed": 5, "neutral_creeps_killed": 4, "map_area": "dire_safelane", "gold": 3200, "last_hits": 60},
    {"minute": 9, "lane_creeps_killed": 6, "neutral_creeps_killed": 5, "map_area": "dire_triangle", "gold": 3850, "last_hits": 71},
    {"minute": 10, "lane_creeps_killed": 4, "neutral_creeps_killed": 6, "map_area": "dire_jungle", "gold": 4520, "last_hits": 81}
  ],
  "transitions": {
    "first_jungle_kill_time": 278.5,
    "first_jungle_kill_str": "4:38",
    "first_large_camp_time": 336.2,
    "first_large_camp_str": "5:36",
    "left_lane_time": 360.0,
    "left_lane_str": "6:00"
  },
  "summary": {
    "total_lane_creeps": 52,
    "total_neutral_creeps": 29,
    "jungle_percentage": 35.8,
    "gpm": 452.0,
    "cs_per_min": 8.1,
    "camps_cleared": {"large centaur": 3, "large satyr": 4, "medium wolf": 4, "medium harpy": 2, "small kobold": 1}
  }
}
```

**LLM responds:**

> **Anti-Mage's Farming Pattern (0-10 min):**
>
> **Key Transitions:**
>
> - **4:38** - First jungle creep killed (medium wolf camp)
> - **5:36** - First large camp cleared (centaur)
> - **6:00** - Transitioned to full jungle rotation pattern
>
> **Minute-by-Minute Movement:**
>
> | Min | Lane CS | Jungle CS | Location | Gold |
> |-----|---------|-----------|----------|------|
> | 1-4 | 25 | 0 | Dire safelane | 1,150 |
> | 5 | 5 | 3 | Starting jungle | 1,580 |
> | 6-7 | 7 | 11 | Full jungle mode | 2,680 |
> | 8-10 | 15 | 15 | Lane-jungle rotation | 4,520 |
>
> **Summary:**
> - **81 CS in 10 minutes** (8.1 CS/min) - excellent farming
> - **36% jungle farm** - healthy mix of lane and camps
> - Cleared mostly large camps (satyr, centaur) for efficiency
>
> **Pattern Analysis:**
> AM had an uncontested lane for 4 minutes, then started adding jungle camps at minute 5. By minute 6, he was doing the classic "shove wave → clear 2 camps → return for next wave" rotation. The transition timing (5:36 for first large camp) suggests he got his Ring of Health and immediately started sustaining through jungle.

---

## Analyzing Mid Rotations After Runes

**User:** "Did the mid player rotate after rune pickups in the early game?"

**LLM thinks:** I need to analyze rotations and correlate them with rune pickups.

**LLM calls:** `get_rotation_analysis(match_id=8461956309, start_minute=0, end_minute=15)`

**Tool returns:**
```json
{
  "success": true,
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
        "seconds_before_rotation": 3.0
      },
      "outcome": {
        "type": "kill",
        "fight_id": "fight_2",
        "kills_by_rotation_hero": ["antimage"]
      }
    },
    {
      "rotation_id": "rot_2",
      "hero": "nevermore",
      "role": "mid",
      "game_time": 485.0,
      "game_time_str": "8:05",
      "from_lane": "mid",
      "to_lane": "top",
      "rune_before": {
        "rune_type": "double_damage",
        "pickup_time": 482.0,
        "seconds_before_rotation": 3.0
      },
      "outcome": {
        "type": "traded",
        "fight_id": "fight_4",
        "rotation_hero_died": true,
        "kills_by_rotation_hero": ["earthshaker"]
      }
    }
  ],
  "summary": {
    "total_rotations": 5,
    "by_hero": {
      "nevermore": {
        "total_rotations": 3,
        "successful_ganks": 1,
        "failed_ganks": 1,
        "trades": 1,
        "rune_rotations": 3
      }
    },
    "runes_leading_to_kills": 2,
    "most_active_rotator": "nevermore"
  }
}
```

**LLM responds:**

> **Shadow Fiend's Rotation Pattern (0-15 min):**
>
> SF rotated 3 times in the early game, **all 3 after picking up power runes**.
>
> | Time | Rune | Target Lane | Outcome |
> |------|------|-------------|---------|
> | 6:05 | Haste | Bot | Kill on Anti-Mage |
> | 8:05 | DD | Top | Traded - killed ES but died |
> | 10:02 | Arcane | Bot | No engagement |
>
> **Analysis:**
> - **Rune discipline**: SF consistently contested and secured power runes
> - **Rotation efficiency**: 2/3 rotations resulted in kills (67% success)
> - **Risk management**: The 8:05 rotation was greedy - diving with DD against a counter-gank setup
>
> **Coaching point**: The DD rotation at 8:05 shows good aggression but poor awareness. Check the fight log with `get_fight(fight_id="fight_4")` to see if the counter-gank was telegraphed (TPs, missing enemies).
