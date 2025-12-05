# Resources Reference

??? info "AI Summary"

    Static reference data via URI. **Core**: `dota2://heroes/all` (124+ heroes with aliases, roles), `dota2://map` (towers, camps, runes, landmarks). **Pro scene**: `dota2://pro/players`, `dota2://pro/teams`. Resources are for static data the user attaches to context. For match-specific data, use tools like `get_match_heroes` and `get_match_players`.

Resources are static reference data that users can attach to their context before a conversation. Access via URI.

!!! note "Resources vs Tools"
    Resources provide **static reference data** (all heroes, map positions, all pro players).
    For **match-specific data** that requires computation, use the corresponding tools:

    - Match heroes: `get_match_heroes(match_id)` tool
    - Match players: `get_match_players(match_id)` tool
    - Pro player details: `get_pro_player(account_id)` tool
    - Team details: `get_team(team_id)` tool

## dota2://heroes/all

All 124+ Dota 2 heroes.

```json
{
  "npc_dota_hero_antimage": {
    "hero_id": 1,
    "canonical_name": "Anti-Mage",
    "aliases": ["am", "antimage", "anti-mage"],
    "attribute": "agility",
    "attack_type": "melee",
    "roles": ["Carry", "Escape", "Nuker"]
  },
  "npc_dota_hero_axe": {
    "hero_id": 2,
    "canonical_name": "Axe",
    "attribute": "strength"
  }
}
```

Use for: Hero name resolution, attribute lookups, role classification.

---

## dota2://map

Full map geometry - towers, camps, runes, landmarks.

```json
{
  "towers": [
    {"name": "radiant_t1_mid", "team": "radiant", "tier": 1, "lane": "mid", "x": -1544, "y": -1408},
    {"name": "dire_t1_mid", "team": "dire", "tier": 1, "lane": "mid", "x": 524, "y": 652}
  ],
  "barracks": [
    {"name": "radiant_melee_mid", "team": "radiant", "lane": "mid", "type": "melee", "x": -4672, "y": -4016}
  ],
  "neutral_camps": [
    {"name": "radiant_small_camp_1", "tier": "small", "side": "radiant", "x": -3200, "y": -400}
  ],
  "runes": [
    {"type": "power", "location": "top", "x": -1792, "y": 1232},
    {"type": "bounty", "location": "radiant_jungle", "x": -4096, "y": -1664}
  ],
  "landmarks": [
    {"name": "roshan_pit", "x": -2432, "y": 2016},
    {"name": "radiant_ancient", "x": -6144, "y": -6016}
  ]
}
```

**Coordinate system:**
- Center of map ≈ (0, 0)
- Radiant base = bottom-left (negative X, negative Y)
- Dire base = top-right (positive X, positive Y)
- Range: roughly -8000 to +8000

Use for: Understanding death positions, analyzing rotations, tower/rax context.

---

# Pro Scene Resources

Static data about professional Dota 2 players and teams.

## dota2://pro/players

All professional players from OpenDota.

```
dota2://pro/players
```

```json
{
  "players": [
    {
      "account_id": 311360822,
      "name": "Yatoro",
      "personaname": "Yatoro",
      "team_id": 8599101,
      "team_name": "Team Spirit",
      "team_tag": "Spirit",
      "country_code": "UA",
      "fantasy_role": 1,
      "is_active": true
    }
  ],
  "total_players": 2500
}
```

Use for: Looking up pro player info, finding players by team.

---

## dota2://pro/teams

All professional teams from OpenDota.

```
dota2://pro/teams
```

```json
{
  "teams": [
    {
      "team_id": 8599101,
      "name": "Team Spirit",
      "tag": "Spirit",
      "rating": 1500.0,
      "wins": 450,
      "losses": 200
    }
  ],
  "total_teams": 500
}
```

Use for: Looking up team info, comparing team ratings.

!!! tip "For detailed player/team info"
    Use the `get_pro_player(account_id)` and `get_team(team_id)` tools for detailed information including aliases and rosters.
