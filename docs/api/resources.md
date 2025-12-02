# Resources Reference

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
