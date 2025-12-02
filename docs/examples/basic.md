# Basic Usage

## Starting the Server

```bash
uv run python dota_match_mcp_server.py
```

The server outputs available resources and tools on startup:

```
Dota 2 Match MCP Server starting...
Resources:
   dota2://heroes/all
   dota2://map
   dota2://match/{match_id}/heroes
   dota2://match/{match_id}/players
Tools:
   get_match_timeline
   get_stats_at_minute
   get_hero_deaths
   get_combat_log
   get_fight_combat_log
   get_item_purchases
   get_courier_kills
   get_objective_kills
```

## Using with MCP Clients

### Accessing Resources

Resources are accessed via URI:

```
# Get all heroes
dota2://heroes/all

# Get map data
dota2://map

# Get heroes in a specific match
dota2://match/8461956309/heroes

# Get players in a specific match
dota2://match/8461956309/players
```

### Calling Tools

Tools are called with parameters:

```python
# Get match timeline
get_match_timeline(match_id=8461956309)

# Get stats at minute 10
get_stats_at_minute(match_id=8461956309, minute=10)

# Get all hero deaths
get_hero_deaths(match_id=8461956309)

# Get combat log for a specific hero
get_combat_log(match_id=8461956309, hero_filter="earthshaker")
```

## Direct Python Usage

You can also use the components directly:

```python
import asyncio
from src.resources.heroes_resources import heroes_resource
from src.utils.replay_downloader import ReplayDownloader
from src.utils.combat_log_parser import combat_log_parser

async def main():
    # Get all heroes
    heroes = await heroes_resource.get_all_heroes()
    print(f"Total heroes: {len(heroes)}")

    # Get heroes in a match
    match_heroes = await heroes_resource.get_match_heroes(8461956309)
    for hero in match_heroes:
        print(f"{hero['localized_name']} - {hero['team']}")

    # Download and parse a replay
    downloader = ReplayDownloader()
    replay_path = await downloader.download_replay(8461956309)

    if replay_path:
        deaths = combat_log_parser.get_hero_deaths(replay_path)
        print(f"Total deaths: {len(deaths)}")

asyncio.run(main())
```
