# Real Use Cases

??? info "🤖 AI Summary"

    Example LLM conversations showing tool usage with realistic JSON responses. **Lost teamfight** - `get_hero_deaths` → `get_fight_combat_log` with **highlights** (multi-hero abilities, kill streaks, team wipes, fight initiator). **Carry farm tracking** - `get_item_purchases` → `get_stats_at_minute`. **Farming pattern** - `get_farming_pattern` → `camp_sequence`, `level_timings`, `item_timings`, position tracking. **Rotation analysis** - `get_rotation_analysis` → rune-rotation correlation, outcomes. **Gank analysis** - death positions → fight highlights → initiator detection. **Roshan control** - `get_objective_kills` → full objective timeline. **Laning comparison** - `get_stats_at_minute(10)` → net worth, hero damage, KDA, level.

These are example conversations showing how an LLM uses the MCP tools to analyze matches.

## Analyzing a Lost Teamfight

**User:** "In match 8461956309, we lost a big fight around 25 minutes. What went wrong?"

**LLM thinks:** I need to find deaths around minute 25 and analyze the fight.

**LLM calls:** `get_hero_deaths(match_id=8461956309)`

**Tool returns:**
```json
{
  "success": true,
  "match_id": 8461956309,
  "total_deaths": 45,
  "deaths": [
    {"game_time": 1487, "game_time_str": "24:47", "victim": "pangolier", "killer": "medusa", "killer_is_hero": true, "ability": "medusa_split_shot"},
    {"game_time": 1492, "game_time_str": "24:52", "victim": "earthshaker", "killer": "disruptor", "killer_is_hero": true, "ability": "disruptor_static_storm"},
    {"game_time": 1495, "game_time_str": "24:55", "victim": "nevermore", "killer": "naga_siren", "killer_is_hero": true, "ability": "naga_siren_rip_tide"},
    {"game_time": 1498, "game_time_str": "24:58", "victim": "dawnbreaker", "killer": "medusa", "killer_is_hero": true, "ability": "medusa_mystic_snake"}
  ]
}
```

**LLM calls:** `get_fight_combat_log(match_id=8461956309, reference_time=1492, hero="earthshaker")`

**Tool returns:**
```json
{
  "success": true,
  "match_id": 8461956309,
  "fight_start": 1480,
  "fight_start_str": "24:40",
  "fight_end": 1502,
  "fight_end_str": "25:02",
  "duration": 22,
  "participants": ["pangolier", "earthshaker", "nevermore", "dawnbreaker", "medusa", "disruptor", "naga_siren", "luna", "necrophos"],
  "total_events": 47,
  "events": [
    {"type": "ABILITY", "game_time": 1481, "game_time_str": "24:41", "attacker": "earthshaker", "attacker_is_hero": true, "target": "medusa", "target_is_hero": true, "ability": "earthshaker_echo_slam"},
    {"type": "DAMAGE", "game_time": 1481, "game_time_str": "24:41", "attacker": "earthshaker", "attacker_is_hero": true, "target": "medusa", "target_is_hero": true, "ability": "earthshaker_echo_slam", "value": 287},
    {"type": "MODIFIER_ADD", "game_time": 1482, "game_time_str": "24:42", "attacker": "disruptor", "attacker_is_hero": true, "target": "earthshaker", "target_is_hero": true, "ability": "disruptor_static_storm"},
    {"type": "DAMAGE", "game_time": 1485, "game_time_str": "24:45", "attacker": "medusa", "attacker_is_hero": true, "target": "pangolier", "target_is_hero": true, "ability": "medusa_split_shot", "value": 412}
  ],
  "highlights": {
    "multi_hero_abilities": [
      {
        "game_time": 1481.0,
        "game_time_str": "24:41",
        "ability": "earthshaker_echo_slam",
        "ability_display": "Echo Slam",
        "caster": "earthshaker",
        "targets": ["medusa", "disruptor", "naga_siren", "luna", "necrophos"],
        "hero_count": 5
      }
    ],
    "kill_streaks": [
      {
        "game_time": 1498.0,
        "game_time_str": "24:58",
        "hero": "medusa",
        "streak_type": "triple_kill",
        "kills": 3,
        "victims": ["pangolier", "nevermore", "dawnbreaker"]
      }
    ],
    "team_wipes": [],
    "fight_initiator": "earthshaker",
    "initiation_ability": "Echo Slam"
  }
}
```

**LLM responds:**

> The fight at 24:40 was a disaster for Radiant. Here's the breakdown from the highlights:
>
> **The Initiation:**
> - **Earthshaker initiated with Echo Slam** at 24:41, hitting all 5 Dire heroes (Medusa, Disruptor, Naga, Luna, Necrophos)
> - Despite hitting 5 targets, the damage was underwhelming (287 on Medusa) - likely low Aftershock stacks
>
> **What Went Wrong:**
> 1. **Disruptor immediately countered** with Static Storm on Earthshaker at 24:42, silencing him before any follow-up
> 2. **Medusa cleaned house** - achieved a **Triple Kill** on Pangolier, Nevermore, and Dawnbreaker
> 3. **22-second fight** with 4 Radiant deaths
>
> **The Issue:** The Echo Slam was mechanically good (5 heroes hit!) but strategically bad:
> - No BKB against Disruptor Static Storm
> - Radiant had no follow-up damage after ES was silenced
> - Medusa tanked the initiation and turned the fight with Split Shot

---

## Tracking Carry Farm

**User:** "How did their Anti-Mage get Battle Fury so fast in match 8461956309?"

**LLM calls:** `get_item_purchases(match_id=8461956309, hero_filter="antimage")`

**Tool returns:**
```json
{
  "success": true,
  "match_id": 8461956309,
  "hero_filter": "antimage",
  "total_purchases": 7,
  "purchases": [
    {"game_time": -89, "game_time_str": "-1:29", "hero": "antimage", "item": "item_tango"},
    {"game_time": -89, "game_time_str": "-1:29", "hero": "antimage", "item": "item_quelling_blade"},
    {"game_time": -89, "game_time_str": "-1:29", "hero": "antimage", "item": "item_slippers"},
    {"game_time": 180, "game_time_str": "3:00", "hero": "antimage", "item": "item_ring_of_health"},
    {"game_time": 420, "game_time_str": "7:00", "hero": "antimage", "item": "item_boots"},
    {"game_time": 540, "game_time_str": "9:00", "hero": "antimage", "item": "item_bfury"},
    {"game_time": 780, "game_time_str": "13:00", "hero": "antimage", "item": "item_manta"}
  ]
}
```

**LLM calls:** `get_stats_at_minute(match_id=8461956309, minute=9)`

**Tool returns:**
```json
{
  "success": true,
  "match_id": 8461956309,
  "minute": 9,
  "players": [
    {"hero": "antimage", "team": "dire", "net_worth": 5420, "hero_damage": 450, "kills": 0, "deaths": 0, "assists": 0, "level": 10},
    {"hero": "nevermore", "team": "radiant", "net_worth": 4100, "hero_damage": 1200, "kills": 1, "deaths": 1, "assists": 0, "level": 9}
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
  "success": true,
  "match_id": 8461956309,
  "total_deaths": 45,
  "deaths": [
    {"game_time": 288, "game_time_str": "4:48", "victim": "earthshaker", "killer": "disruptor", "killer_is_hero": true, "ability": "disruptor_thunder_strike", "position": {"x": 4200, "y": 1800, "region": "dire_safelane", "location": "Dire safelane near tower"}}
  ]
}
```

**LLM calls:** `get_fight_combat_log(match_id=8461956309, reference_time=288, hero="earthshaker")`

**Tool returns:**
```json
{
  "success": true,
  "match_id": 8461956309,
  "hero": "earthshaker",
  "fight_start": 280,
  "fight_start_str": "4:40",
  "fight_end": 290,
  "fight_end_str": "4:50",
  "duration": 10,
  "participants": ["earthshaker", "disruptor", "naga_siren", "medusa"],
  "total_events": 12,
  "events": [
    {"type": "MODIFIER_ADD", "game_time": 281, "game_time_str": "4:41", "attacker": "naga_siren", "attacker_is_hero": true, "target": "earthshaker", "target_is_hero": true, "ability": "naga_siren_ensnare"},
    {"type": "DAMAGE", "game_time": 282, "game_time_str": "4:42", "attacker": "disruptor", "attacker_is_hero": true, "target": "earthshaker", "target_is_hero": true, "ability": "disruptor_thunder_strike", "value": 160},
    {"type": "DAMAGE", "game_time": 284, "game_time_str": "4:44", "attacker": "medusa", "attacker_is_hero": true, "target": "earthshaker", "target_is_hero": true, "ability": "medusa_mystic_snake", "value": 140},
    {"type": "DAMAGE", "game_time": 286, "game_time_str": "4:46", "attacker": "naga_siren", "attacker_is_hero": true, "target": "earthshaker", "target_is_hero": true, "value": 58},
    {"type": "DEATH", "game_time": 288, "game_time_str": "4:48", "attacker": "disruptor", "attacker_is_hero": true, "target": "earthshaker", "target_is_hero": true}
  ],
  "highlights": {
    "multi_hero_abilities": [],
    "kill_streaks": [],
    "team_wipes": [],
    "fight_initiator": "naga_siren",
    "initiation_ability": "Ensnare"
  }
}
```

**LLM responds:**

> Here's what happened at first blood (4:48):
>
> **Fight Summary:**
> - **Duration:** 10 seconds (4:40 - 4:50)
> - **Initiator:** Naga Siren with Ensnare (detected automatically in highlights)
> - **Participants:** 3v1 gank (Naga, Disruptor, Medusa vs Earthshaker)
>
> **Kill Timeline:**
> 1. **4:41** - Naga Siren lands Ensnare (3-second root)
> 2. **4:42** - Disruptor Thunder Strike (160 damage over time)
> 3. **4:44** - Medusa Mystic Snake (140 damage)
> 4. **4:46** - Naga right-click (58 damage)
> 5. **4:48** - Death
>
> **Position:** x:4200, y:1800 - deep in Dire safelane near their tower.
>
> **What went wrong:** You were caught in a 3v1 without escape. Once Naga lands Ensnare, you have no mobility and they chain their damage perfectly.
>
> **What to do differently:**
> - Stay near trees for juke paths against Naga
> - Track enemy positions before contesting pulls
> - ES needs level 6 to threaten this trilane - play for XP until then

---

## Objective Control Analysis

**User:** "When did Roshan die and who took the Aegis?"

**LLM calls:** `get_objective_kills(match_id=8461956309)`

**Tool returns:**
```json
{
  "success": true,
  "match_id": 8461956309,
  "roshan_kills": [
    {"game_time": 1392, "game_time_str": "23:12", "killer": "medusa", "team": "dire", "kill_number": 1},
    {"game_time": 2040, "game_time_str": "34:00", "killer": "medusa", "team": "dire", "kill_number": 2},
    {"game_time": 2580, "game_time_str": "43:00", "killer": "luna", "team": "dire", "kill_number": 3},
    {"game_time": 3120, "game_time_str": "52:00", "killer": "medusa", "team": "dire", "kill_number": 4}
  ],
  "tormentor_kills": [],
  "tower_kills": [
    {"game_time": 669, "game_time_str": "11:09", "tower": "dire_t1_mid", "team": "dire", "tier": 1, "lane": "mid", "killer": "nevermore", "killer_is_hero": true},
    {"game_time": 1440, "game_time_str": "24:00", "tower": "radiant_t1_bot", "team": "radiant", "tier": 1, "lane": "bot", "killer": "medusa", "killer_is_hero": true}
  ],
  "barracks_kills": []
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
  "success": true,
  "match_id": 8461956309,
  "minute": 10,
  "players": [
    {"hero": "nevermore", "team": "radiant", "net_worth": 4800, "hero_damage": 2100, "kills": 2, "deaths": 0, "assists": 1, "level": 11},
    {"hero": "pangolier", "team": "dire", "net_worth": 3200, "hero_damage": 1400, "kills": 0, "deaths": 1, "assists": 0, "level": 9}
  ]
}
```

**LLM responds:**

> **Mid Lane at 10:00 - Nevermore vs Pangolier:**
>
> | Stat | Nevermore (Radiant) | Pangolier (Dire) |
> |------|---------------------|------------------|
> | Net Worth | 4,800 | 3,200 |
> | Hero Damage | 2,100 | 1,400 |
> | K/D/A | 2/0/1 | 0/1/0 |
> | Level | 11 | 9 |
>
> **Nevermore dominated the lane:**
> - **+1,600 net worth** advantage (50% more gold)
> - **+700 hero damage** dealt - SF was more aggressive
> - **+2 levels** (level 11 vs 9)
> - **2 kills, 0 deaths** vs 0/1 for Pango
>
> Shadow Fiend's early damage from Necromastery stacks and Raze harass let him win trades. The 2 kills suggest SF was rotating or getting ganks, while Pango's death cost him farm time.

---

## Analyzing Carry Farming Pattern

**User:** "What was Anti-Mage's farming pattern in the first 10 minutes? When did he start jungling?"

**LLM calls:** `get_farming_pattern(match_id=8461956309, hero="antimage", start_minute=0, end_minute=10)`

**Tool returns:**
```json
{
  "success": true,
  "match_id": 8461956309,
  "hero": "antimage",
  "start_minute": 0,
  "end_minute": 10,
  "level_timings": [
    {"level": 6, "time": 420.0, "time_str": "7:00"},
    {"level": 10, "time": 600.0, "time_str": "10:00"}
  ],
  "item_timings": [
    {"item": "ring_of_health", "time": 180.0, "time_str": "3:00"},
    {"item": "bfury", "time": 540.0, "time_str": "9:00"}
  ],
  "minutes": [
    {
      "minute": 5,
      "position_at_start": {"x": 5800, "y": 3200, "area": "dire_safelane"},
      "position_at_end": {"x": 6200, "y": 4800, "area": "dire_jungle"},
      "camp_sequence": [
        {"time_str": "5:15", "camp": "medium_wolf", "tier": "medium", "area": "dire_jungle"},
        {"time_str": "5:42", "camp": "small_kobold", "tier": "small", "area": "dire_jungle"}
      ],
      "lane_creeps_killed": 5,
      "camps_cleared": 2,
      "gold": 1580,
      "last_hits": 33,
      "level": 5
    },
    {
      "minute": 6,
      "position_at_start": {"x": 6200, "y": 4800, "area": "dire_jungle"},
      "position_at_end": {"x": 5500, "y": 5200, "area": "dire_jungle"},
      "camp_sequence": [
        {"time_str": "6:08", "camp": "large_centaur", "tier": "hard", "area": "dire_jungle"},
        {"time_str": "6:35", "camp": "medium_wolf", "tier": "medium", "area": "dire_jungle"}
      ],
      "lane_creeps_killed": 4,
      "camps_cleared": 2,
      "gold": 2100,
      "last_hits": 42,
      "level": 6
    }
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
    "camps_cleared": {"large_centaur": 3, "large_satyr": 4, "medium_wolf": 4, "medium_harpy": 2, "small_kobold": 1},
    "multi_camp_clears": 0
  },
  "multi_camp_clears": []
}
```

**LLM responds:**

> **Anti-Mage's Farming Pattern (0-10 min):**
>
> **Power Spike Timeline:**
>
> | Time | Event |
> |------|-------|
> | 3:00 | Ring of Health purchased |
> | 4:38 | First jungle creep killed |
> | 5:36 | First large camp (centaur) |
> | 6:00 | Left lane for jungle rotation |
> | 7:00 | Level 6 (Blink available) |
> | 9:00 | **Battle Fury completed** |
> | 10:00 | Level 10 |
>
> **Minute 5-6 Farming Route:**
>
> The `camp_sequence` shows his exact route:
> - **5:15** → Medium wolf camp (first jungle stop)
> - **5:42** → Small kobold camp
> - **6:08** → Large centaur camp
> - **6:35** → Back to medium wolf (respawned)
>
> Position tracking shows he went from `dire_safelane` at 5:00 to `dire_jungle` by 5:59.
>
> **Summary:**
> - **8.1 CS/min** with **36% jungle farm** - excellent efficiency
> - Ring of Health at 3:00 enabled jungle sustain
> - Hit level 6 at 7:00 (Blink for escape) just as he committed to jungle
> - **9-minute Battle Fury** from uncontested lane + efficient jungle rotation

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
