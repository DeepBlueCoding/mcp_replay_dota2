# Match Analysis Tools

These tools query match events, deaths, items, and timeline data. All require `match_id` as a parameter.

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

## get_hero_combat_analysis

**THE PRIMARY TOOL for analyzing a hero's performance in a match.** Use this for ANY question about how a player/hero performed.

**Use this for:**

- "How did Whitemon's Jakiro perform?"
- "What was Collapse's impact on Mars?"
- "How many Ice Paths landed?"
- "Show me Yatoro's fight participation"

Returns per-fight statistics including kills, deaths, assists, ability usage with hit rates, and damage dealt/received.

```python
get_hero_combat_analysis(
    match_id=8461956309,
    hero="earthshaker"
)
```

**Returns:**
```json
{
  "success": true,
  "match_id": 8461956309,
  "hero": "earthshaker",
  "total_fights": 3,
  "total_teamfights": 1,
  "total_kills": 2,
  "total_deaths": 2,
  "total_assists": 0,
  "ability_summary": [
    {"ability": "earthshaker_fissure", "total_casts": 3, "hero_hits": 6, "hit_rate": 200.0},
    {"ability": "earthshaker_enchant_totem", "total_casts": 3, "hero_hits": 2, "hit_rate": 66.7},
    {"ability": "earthshaker_echo_slam", "total_casts": 1, "hero_hits": 0, "hit_rate": 0.0}
  ],
  "fights": [
    {
      "fight_id": "fight_1",
      "fight_start": 288.0,
      "fight_start_str": "4:48",
      "fight_end": 295.0,
      "fight_end_str": "4:55",
      "is_teamfight": false,
      "kills": 0,
      "deaths": 1,
      "assists": 0,
      "damage_dealt": 53,
      "damage_received": 366,
      "abilities_used": [
        {"ability": "earthshaker_enchant_totem", "total_casts": 1, "hero_hits": 0, "hit_rate": 0.0}
      ]
    }
  ]
}
```

**Key fields:**

| Field | Description |
|-------|-------------|
| `ability_summary` | Overall ability usage across all fights |
| `hero_hits` | Times ability affected an enemy hero (includes stuns/debuffs from ground-targeted abilities like Ice Path, Fissure) |
| `hit_rate` | Can exceed 100% for AoE abilities that hit multiple heroes per cast |
| `fights` | Per-fight breakdown with K/D/A and ability usage |
| `is_teamfight` | True if the fight had 3+ deaths |

!!! tip "Ground-Targeted Abilities"
    Abilities like Ice Path, Fissure, and Kinetic Field are tracked via MODIFIER_ADD events (stun debuffs applied to heroes), not just the cast event. This ensures accurate hit detection for ground-targeted CC abilities.

---

## get_combat_log

Raw combat events for a **SPECIFIC TIME WINDOW ONLY**.

!!! warning "When NOT to use this tool"
    - "How did X hero perform?" → Use `get_hero_combat_analysis`
    - "Show me the fights" → Use `list_fights` or `get_teamfights`
    - "What happened in the game?" → Use `get_match_timeline`

**Use this only when** you need raw event-by-event details for a specific 30-second to 3-minute window.

```python
# Default: narrative detail (recommended for most queries)
get_combat_log(
    match_id=8461956309,
    start_time=280,
    end_time=300,
    hero_filter="earthshaker"
)

# Tactical: includes hero-to-hero damage
get_combat_log(
    match_id=8461956309,
    start_time=280,
    end_time=300,
    detail_level="tactical"
)

# Full: all events (WARNING: can overflow context)
get_combat_log(
    match_id=8461956309,
    start_time=280,
    end_time=290,  # Keep time range SHORT!
    detail_level="full"
)
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `match_id` | int | Required. The match ID |
| `start_time` | float | Optional. Filter events after this game time (seconds). **Note:** Pre-game purchases happen at negative times (~-80s). Use `-90` to include strategy phase, or omit entirely. `start_time=0` excludes pre-game. |
| `end_time` | float | Optional. Filter events before this game time (seconds) |
| `hero_filter` | string | Optional. Only events involving this hero (e.g., "earthshaker") |
| `detail_level` | string | Controls verbosity: `"narrative"` (default), `"tactical"`, or `"full"`. See below. |
| `max_events` | int | Maximum events to return (default 500, max 2000). Prevents overflow. |

**Detail Levels:**

| Level | ~Tokens | Best For |
|-------|---------|----------|
| `narrative` | 500-2,000 | "What happened?" - Deaths, abilities, items, purchases, buybacks |
| `tactical` | 2,000-5,000 | "How much damage?" - Adds hero-to-hero damage, debuffs on heroes |
| `full` | 50,000+ | Debugging only - All events including creeps. **⚠️ WARNING: Can overflow context** |

**Narrative Mode (default):**

| Included | Event Type | Description |
|----------|------------|-------------|
| ✅ | `ABILITY` | Hero ability casts |
| ✅ | `DEATH` | Hero deaths only |
| ✅ | `ITEM` | Active item usage |
| ✅ | `PURCHASE` | Item purchases |
| ✅ | `BUYBACK` | Buybacks |

**Tactical Mode (adds):**

| Added | Event Type | Description |
|-------|------------|-------------|
| ➕ | `DAMAGE` | Hero-to-hero damage only |
| ➕ | `MODIFIER_ADD` | Debuffs applied to heroes |

**Full Mode:**

| Added | Event Type | Reason to avoid |
|-------|------------|-----------------|
| ➕ | All `DAMAGE` | Creep/tower damage creates noise |
| ➕ | All `MODIFIER_*` | Buff/debuff spam |
| ➕ | `HEAL` | Minor heals flood log |

**When to use each level:**

- **`narrative`** (default): Fight overview, rotation analysis, item timings
- **`tactical`**: Damage breakdown, ability impact analysis
- **`full`**: Debugging only, with **short time windows (<30s)**

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

Event types: `DAMAGE`, `MODIFIER_ADD`, `MODIFIER_REMOVE`, `ABILITY`, `ITEM`, `DEATH`, `HEAL`, `PURCHASE`, `BUYBACK`

---

## get_fight_combat_log

Get combat log for **ONE SPECIFIC FIGHT** at a known time.

!!! warning "When NOT to use this tool"
    - "How did X hero perform?" → Use `get_hero_combat_analysis`
    - "Show me all teamfights" → Use `get_teamfights`
    - "List all fights" → Use `list_fights`

**Use this when** you have a specific death time and want details about that particular fight.

Auto-detects fight boundaries around a reference time. Returns combat events plus **fight highlights** including multi-hero abilities, kill streaks, and team wipes.

```python
# Default: narrative detail (recommended)
get_fight_combat_log(
    match_id=8461956309,
    reference_time=288,    # e.g., death time from get_hero_deaths
    hero="earthshaker"     # optional: anchor detection to this hero
)

# Tactical: for damage analysis
get_fight_combat_log(
    match_id=8461956309,
    reference_time=288,
    detail_level="tactical"
)
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `match_id` | int | Required. The match ID |
| `reference_time` | float | Required. Game time in seconds to anchor fight detection (e.g., death time) |
| `hero` | string | Optional. Hero name to anchor fight detection |
| `detail_level` | string | `"narrative"` (default), `"tactical"`, or `"full"`. Same as `get_combat_log`. |
| `max_events` | int | Maximum events (default 200). Prevents overflow. |

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
  "events": [...],
  "highlights": {
    "multi_hero_abilities": [
      {
        "game_time": 282.5,
        "game_time_str": "4:42",
        "ability": "faceless_void_chronosphere",
        "ability_display": "Chronosphere",
        "caster": "faceless_void",
        "targets": ["crystal_maiden", "lion", "earthshaker"],
        "hero_count": 3
      }
    ],
    "kill_streaks": [
      {
        "game_time": 290.0,
        "game_time_str": "4:50",
        "hero": "medusa",
        "streak_type": "triple_kill",
        "kills": 3,
        "victims": ["crystal_maiden", "lion", "earthshaker"]
      }
    ],
    "team_wipes": [
      {
        "game_time": 295.0,
        "game_time_str": "4:55",
        "team_wiped": "radiant",
        "killer_team": "dire",
        "duration": 13.0
      }
    ],
    "bkb_blink_combos": [
      {
        "game_time": 282.0,
        "game_time_str": "4:42",
        "hero": "earthshaker",
        "ability": "earthshaker_echo_slam",
        "ability_display": "Echo Slam",
        "bkb_time": 281.5,
        "blink_time": 281.8,
        "is_initiator": true
      }
    ],
    "coordinated_ults": [
      {
        "game_time": 282.0,
        "game_time_str": "4:42",
        "team": "radiant",
        "heroes": ["earthshaker", "nevermore"],
        "abilities": ["earthshaker_echo_slam", "nevermore_requiem"],
        "window_seconds": 1.5
      }
    ],
    "clutch_saves": [
      {
        "game_time": 290.0,
        "game_time_str": "4:50",
        "saved_hero": "medusa",
        "save_type": "self_banish",
        "save_ability": "item_outworld_staff",
        "saved_from": "juggernaut_omni_slash",
        "saver": null
      }
    ],
    "refresher_combos": [],
    "buybacks": [],
    "generic_aoe_hits": []
  }
}
```

**Highlights Explained:**

| Field | Description |
|-------|-------------|
| `multi_hero_abilities` | Big ultimates/abilities hitting 2+ enemy heroes (Chronosphere, Black Hole, Ravage, Ice Path, etc.) |
| `kill_streaks` | Double kill through Rampage (uses Dota 2's 18-second window between kills) |
| `team_wipes` | All 5 heroes of one team killed within the fight (Ace!) |
| `bkb_blink_combos` | BKB + Blink into big ability (classic initiation pattern). `is_initiator=true` for first combo, `false` for follow-ups |
| `coordinated_ults` | 2+ heroes from the **same team** using big abilities within 3 seconds. Includes `team` field (radiant/dire) |
| `clutch_saves` | Self-saves (Outworld Staff, Euls) or ally saves (Glimmer Cape on teammates under attack) |
| `refresher_combos` | Hero using Refresher to double-cast an ultimate (double Echo Slam, double Ravage, etc.) |
| `buybacks` | Heroes buying back during the fight |
| `generic_aoe_hits` | Any ability hitting 3+ heroes (catches abilities not in the big-ability list) |

**Tracked Abilities (60+):**
- **Ultimates**: Chronosphere, Black Hole, Ravage, Reverse Polarity, Echo Slam, Requiem of Souls, etc.
- **Control**: Ice Path, Kinetic Field, Dream Coil, Static Storm, etc.
- **Team wipe detectors**: Tracks all deaths to determine if entire team was killed
- **Initiation**: BKB + Blink combos with is_initiator flag for the first combo

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

Snapshot of all players at a specific minute. **Parallel-safe**: call for multiple minutes.

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

## get_match_heroes

Get the 10 heroes in a match with detailed stats and **counter picks data** for draft analysis.

```python
get_match_heroes(match_id=8461956309)
```

**Returns:**
```json
{
  "radiant_heroes": [
    {
      "hero_id": 1,
      "hero_name": "antimage",
      "localized_name": "Anti-Mage",
      "team": "radiant",
      "lane": "safe_lane",
      "role": "core",
      "kills": 8,
      "deaths": 2,
      "assists": 5,
      "last_hits": 420,
      "gpm": 650,
      "xpm": 580,
      "net_worth": 28500,
      "hero_damage": 15200,
      "items": ["Manta Style", "Battle Fury", "Abyssal Blade"],
      "player_name": "PlayerOne",
      "pro_name": "Yatoro",
      "counters": [
        {"hero_id": 6, "localized_name": "Doom", "reason": "Doom silences AM completely..."}
      ],
      "good_against": [
        {"hero_id": 94, "localized_name": "Medusa", "reason": "Mana Break devastates mana shield..."}
      ],
      "when_to_pick": ["Enemy has mana-dependent heroes", "Team can hold 4v5"]
    }
  ],
  "dire_heroes": [...]
}
```

!!! tip "Draft Analysis"
    Use the `counters` and `good_against` fields to analyze draft advantages. Check which enemy heroes counter each of your picks, and identify favorable matchups.

---

## get_match_players

Get the 10 players in a match with their hero assignments.

```python
get_match_players(match_id=8461956309)
```

**Returns:**
```json
{
  "radiant_players": [
    {
      "player_name": "PlayerOne",
      "pro_name": "Yatoro",
      "account_id": 311360822,
      "team": "radiant",
      "hero_id": 1,
      "hero_name": "antimage",
      "localized_name": "Anti-Mage"
    }
  ],
  "dire_players": [...]
}
```
