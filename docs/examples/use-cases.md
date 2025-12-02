# Real Use Cases

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
