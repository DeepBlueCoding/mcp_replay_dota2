# FastMCP Client

??? info "🤖 AI Summary"

    Install: `pip install fastmcp`. Use `Client("uv run python dota_match_mcp_server.py")` as async context manager. Call tools: `await client.call_tool("get_hero_deaths", match_id=123)`. Get resources: `await client.get_resource("dota2://heroes/all")`. Handles errors and supports batch processing.

The simplest Python integration - use the same library the server is built with.

## Install

```bash
pip install fastmcp
```

## Basic Usage

```python
import asyncio
from fastmcp import Client

async def main():
    async with Client("uv run python dota_match_mcp_server.py") as client:
        # Call tools directly
        deaths = await client.call_tool("get_hero_deaths", match_id=8461956309)
        print(f"Total deaths: {deaths['total_deaths']}")

        for death in deaths['deaths'][:5]:
            print(f"  {death['game_time_str']}: {death['killer']} killed {death['victim']}")

asyncio.run(main())
```

## Working with Resources

```python
async def main():
    async with Client("uv run python dota_match_mcp_server.py") as client:
        # Get static hero reference data
        heroes = await client.get_resource("dota2://heroes/all")
        print(f"Total heroes: {len(heroes)}")

        # Get match-specific data using tools
        match_heroes = await client.call_tool("get_match_heroes", match_id=8461956309)
        for hero in match_heroes['radiant'] + match_heroes['dire']:
            print(f"{hero['localized_name']} - {hero['team']} - K/D/A: {hero['kills']}/{hero['deaths']}/{hero['assists']}")

asyncio.run(main())
```

## Complete Analysis Script

```python
import asyncio
from fastmcp import Client

async def analyze_match(match_id: int):
    async with Client("uv run python dota_match_mcp_server.py") as client:
        # Get all data
        deaths = await client.call_tool("get_hero_deaths", match_id=match_id)
        objectives = await client.call_tool("get_objective_kills", match_id=match_id)

        print(f"\n=== Match {match_id} Analysis ===\n")

        # Deaths summary
        print(f"Total Deaths: {deaths['total_deaths']}")

        # First blood
        if deaths['deaths']:
            fb = deaths['deaths'][0]
            print(f"First Blood: {fb['game_time_str']} - {fb['killer']} killed {fb['victim']}")

        # Roshan control
        rosh = objectives['roshan_kills']
        print(f"\nRoshan Kills: {len(rosh)}")
        for r in rosh:
            print(f"  Rosh #{r['kill_number']} at {r['game_time_str']} by {r['team']}")

        # Tower score
        towers = objectives['tower_kills']
        radiant_towers = len([t for t in towers if t['team'] == 'radiant'])
        dire_towers = len([t for t in towers if t['team'] == 'dire'])
        print(f"\nTowers Lost - Radiant: {radiant_towers}, Dire: {dire_towers}")

if __name__ == "__main__":
    asyncio.run(analyze_match(8461956309))
```

## Error Handling

```python
async def safe_analysis(match_id: int):
    try:
        async with Client("uv run python dota_match_mcp_server.py") as client:
            result = await client.call_tool("get_hero_deaths", match_id=match_id)

            if not result.get('success', True):
                print(f"Error: {result.get('error', 'Unknown error')}")
                return None

            return result

    except Exception as e:
        print(f"Connection error: {e}")
        return None
```

## Batch Processing

```python
async def analyze_multiple_matches(match_ids: list[int]):
    async with Client("uv run python dota_match_mcp_server.py") as client:
        results = {}

        for match_id in match_ids:
            print(f"Analyzing {match_id}...")
            deaths = await client.call_tool("get_hero_deaths", match_id=match_id)
            objectives = await client.call_tool("get_objective_kills", match_id=match_id)

            results[match_id] = {
                "deaths": deaths['total_deaths'],
                "roshans": len(objectives['roshan_kills']),
                "towers": len(objectives['tower_kills'])
            }

        return results

# Analyze recent matches
matches = [8461956309, 8461956310, 8461956311]
results = asyncio.run(analyze_multiple_matches(matches))
```
