# Resources Reference

<details>
<summary><strong>🤖 AI Summary</strong></summary>

Static data via URI. **Core**: `dota2://heroes/all` (124+ heroes with aliases, roles), `dota2://map` (towers, camps, runes, landmarks). **Match-specific**: `dota2://match/{id}/heroes` (10 heroes with KDA, GPM, items), `dota2://match/{id}/players` (player names, heroes). **Pro scene**: `dota2://pro/players`, `dota2://pro/teams`, `dota2://pro/player/{id}`, `dota2://pro/team/{id}`.

</details>

Resources are static data the LLM can include as context. Access via URI.

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

## dota2://match/{match_id}/heroes

The 10 heroes in a specific match with performance data.

```
dota2://match/8461956309/heroes
```

```json
{
  "heroes": [
    {
      "hero_id": 1,
      "hero_name": "npc_dota_hero_antimage",
      "localized_name": "Anti-Mage",
      "team": "dire",
      "player_name": "SteamUser123",
      "pro_name": null,
      "kills": 8,
      "deaths": 3,
      "assists": 5,
      "last_hits": 412,
      "gpm": 652,
      "xpm": 598,
      "net_worth": 24500,
      "hero_damage": 18200,
      "lane": "safelane",
      "role": "core",
      "items": ["item_manta", "item_bfury", "item_basher", "item_heart", "item_butterfly", "item_travel_boots"],
      "neutral_item": "item_mind_breaker"
    }
  ]
}
```

Use for: Match context, hero matchups, team composition analysis.

---

## dota2://match/{match_id}/players

Player info for a match.

```
dota2://match/8461956309/players
```

```json
{
  "players": [
    {
      "account_id": 123456789,
      "player_name": "SteamUser123",
      "pro_name": null,
      "team": "dire",
      "hero_id": 1,
      "hero_name": "npc_dota_hero_antimage",
      "localized_name": "Anti-Mage"
    }
  ]
}
```

Use for: Identifying players, looking up pros, correlating with external data.

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

---

## dota2://pro/player/{account_id}

Detailed info for a specific pro player.

```
dota2://pro/player/311360822
```

```json
{
  "account_id": 311360822,
  "name": "Yatoro",
  "personaname": "Yatoro",
  "team_id": 8599101,
  "team_name": "Team Spirit",
  "team_tag": "Spirit",
  "country_code": "UA",
  "fantasy_role": 1,
  "is_active": true,
  "aliases": ["yatoro", "raddan"]
}
```

Use for: Getting detailed player info including aliases.

---

## dota2://pro/team/{team_id}

Detailed info for a specific team including roster.

```
dota2://pro/team/8599101
```

```json
{
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
    {
      "account_id": 311360822,
      "player_name": "Yatoro",
      "games_played": 300,
      "wins": 200,
      "is_current": true
    }
  ]
}
```

Use for: Getting team roster, win/loss stats, team aliases.
