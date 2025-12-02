# MCP Resources

Resources are data exposed through the MCP protocol that users can select and include as context. They use URI-style addressing.

## dota2://heroes/all

Complete list of all Dota 2 heroes with their canonical names, aliases, and attributes.

**Response format:**

```json
{
  "npc_dota_hero_antimage": {
    "hero_id": 1,
    "canonical_name": "Anti-Mage",
    "aliases": ["anti-mage", "antimage", "am"],
    "attribute": "agility"
  },
  ...
}
```

## dota2://map

Complete Dota 2 map information including positions of all major landmarks.

**Includes:**

- **Towers**: All 22 towers with team, tier, lane, and position
- **Barracks**: All 12 barracks with team, lane, type (melee/ranged)
- **Ancients**: Both team ancients
- **Neutral camps**: All jungle camps with tier (small/medium/large/ancient)
- **Rune spawns**: Power, bounty, wisdom, and water runes
- **Outposts**: Both outpost locations
- **Shops**: Base, secret, and side shops
- **Landmarks**: Roshan pit, fountains, shrines, tormentors, high ground

**Coordinate system:**

- Origin (0,0) is approximately center of map
- Radiant base is bottom-left (negative X, negative Y)
- Dire base is top-right (positive X, positive Y)
- Map spans roughly -8000 to +8000 in both axes

## dota2://match/{match_id}/heroes

The 10 heroes in a match with full performance data.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `match_id` | string | The Dota 2 match ID |

**Response per hero:**

- **Hero**: hero_id, hero_name, localized_name, primary_attr, attack_type, roles
- **Performance**: kills, deaths, assists, last_hits, GPM, XPM, net_worth, hero_damage
- **Position**: team (radiant/dire), lane, role (core/support)
- **Items**: item_0 through item_5, item_neutral
- **Player**: player_name, pro_name (who is controlling this hero)

## dota2://match/{match_id}/players

The 10 players in a match with their player info and which hero they played.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `match_id` | string | The Dota 2 match ID |

**Response per player:**

- **Player**: player_name (Steam name), pro_name (professional name if known), account_id
- **Team**: radiant or dire
- **Hero**: hero_id, hero_name, localized_name
