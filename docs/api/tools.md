# MCP Tools

Tools are model-controlled functions that the AI can autonomously decide to call based on the conversation context. They return structured data that the model can use to formulate responses.

## get_match_timeline

Get time-series data for a Dota 2 match.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id` | int | Yes | The Dota 2 match ID |

**Returns per player:**

- `net_worth`: Array of net worth values (sampled every 30 seconds)
- `hero_damage`: Array of cumulative hero damage
- `kda_timeline`: Array of {game_time, kills, deaths, assists, level} snapshots

Also returns team-level graphs for experience and gold.

---

## get_stats_at_minute

Get player stats at a specific minute in a Dota 2 match.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id` | int | Yes | The Dota 2 match ID |
| `minute` | int | Yes | Game minute to get stats for (0-based) |

**Returns per player:**

- `net_worth`: Net worth at that minute
- `hero_damage`: Cumulative hero damage at that minute
- `kills`, `deaths`, `assists`: KDA at that minute
- `level`: Hero level at that minute

---

## get_hero_deaths

Get all hero deaths in a Dota 2 match.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id` | int | Yes | The Dota 2 match ID |

**Returns list of death events:**

- `game_time`: Seconds since game start
- `game_time_str`: Formatted as M:SS
- `killer`: Hero or unit that got the kill
- `victim`: Hero that died
- `killer_is_hero`: Whether the killer was a hero
- `ability`: Ability or item that dealt the killing blow (if available)

---

## get_combat_log

Get combat log events from a Dota 2 match with optional filters.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id` | int | Yes | The Dota 2 match ID |
| `start_time` | float | No | Filter events after this game time in seconds |
| `end_time` | float | No | Filter events before this game time in seconds |
| `hero_filter` | str | No | Only include events involving this hero, e.g. "earthshaker" |

**Returns combat events:**

- `type`: DAMAGE, MODIFIER_ADD, ABILITY, DEATH, etc.
- `game_time`: Seconds since game start
- `game_time_str`: Formatted as M:SS
- `attacker`: Source of the event (hero name without prefix)
- `attacker_is_hero`: Whether attacker is a hero
- `target`: Target of the event
- `target_is_hero`: Whether target is a hero
- `ability`: Ability or item involved (if any)
- `value`: Damage amount or other numeric value

---

## get_fight_combat_log

Get combat log for a fight leading up to a specific moment (e.g., a death).

Automatically detects fight boundaries by analyzing combat activity and participant connectivity. Separate skirmishes happening simultaneously in different lanes are correctly identified as distinct fights.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id` | int | Yes | The Dota 2 match ID |
| `reference_time` | float | Yes | Reference game time in seconds (e.g., death time) |
| `hero` | str | No | Optional hero name to anchor fight detection |

**Returns:**

- `fight_start`, `fight_end`: Fight boundaries in seconds
- `fight_start_str`, `fight_end_str`: Formatted as M:SS
- `duration`: Fight duration in seconds
- `participants`: List of heroes involved in the fight
- `events`: Combat log events within the fight

---

## get_item_purchases

Get item purchase timings for heroes in a Dota 2 match.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id` | int | Yes | The Dota 2 match ID |
| `hero_filter` | str | No | Only include purchases by this hero |

**Returns list of purchases:**

- `game_time`: Seconds since game start (can be negative for pre-horn purchases)
- `game_time_str`: Formatted as M:SS
- `hero`: Hero that purchased the item
- `item`: Item name (e.g., "item_bfury", "item_power_treads")

---

## get_courier_kills

Get all courier kills in a Dota 2 match.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id` | int | Yes | The Dota 2 match ID |

**Returns list of courier kills:**

- `game_time`: Seconds since game start
- `game_time_str`: Formatted as M:SS
- `killer`: Hero that killed the courier
- `killer_is_hero`: Whether the killer was a hero
- `team`: Team whose courier was killed (radiant/dire)

---

## get_objective_kills

Get all major objective kills in a Dota 2 match.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `match_id` | int | Yes | The Dota 2 match ID |

**Returns:**

- `roshan_kills`: List of Roshan kills with game_time, killer, team, kill_number
- `tormentor_kills`: List of Tormentor kills with game_time, killer, team, side
- `tower_kills`: List of tower destructions with game_time, tower name, team, tier, lane, killer
- `barracks_kills`: List of barracks destructions with game_time, name, team, lane, type, killer
