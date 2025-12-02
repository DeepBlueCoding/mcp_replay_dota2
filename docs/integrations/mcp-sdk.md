# MCP SDK

Use the official MCP Python SDK for low-level control.

## Install

```bash
pip install mcp
```

## Basic Client

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "dota_match_mcp_server.py"],
        cwd="/path/to/mcp_replay_dota2"
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize connection
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print("Available tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")

            # List available resources
            resources = await session.list_resources()
            print("\nAvailable resources:")
            for resource in resources.resources:
                print(f"  - {resource.uri}")

asyncio.run(main())
```

## Calling Tools

```python
async def call_tool_example():
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "dota_match_mcp_server.py"],
        cwd="/path/to/mcp_replay_dota2"
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call get_hero_deaths
            result = await session.call_tool(
                "get_hero_deaths",
                arguments={"match_id": 8461956309}
            )

            # Result is a list of content blocks
            for content in result.content:
                if content.type == "text":
                    import json
                    data = json.loads(content.text)
                    print(f"Total deaths: {data['total_deaths']}")

asyncio.run(call_tool_example())
```

## Reading Resources

```python
async def read_resource_example():
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "dota_match_mcp_server.py"],
        cwd="/path/to/mcp_replay_dota2"
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Read hero resource
            result = await session.read_resource("dota2://heroes/all")

            for content in result.contents:
                if content.mimeType == "application/json":
                    import json
                    heroes = json.loads(content.text)
                    print(f"Total heroes: {len(heroes)}")

asyncio.run(read_resource_example())
```

## Building a Custom Client Class

```python
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class Dota2MCPClient:
    def __init__(self, server_path: str):
        self.server_params = StdioServerParameters(
            command="uv",
            args=["run", "python", "dota_match_mcp_server.py"],
            cwd=server_path
        )
        self._session = None
        self._read = None
        self._write = None

    async def __aenter__(self):
        transport = stdio_client(self.server_params)
        self._read, self._write = await transport.__aenter__()
        self._session = ClientSession(self._read, self._write)
        await self._session.__aenter__()
        await self._session.initialize()
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.__aexit__(*args)

    async def get_hero_deaths(self, match_id: int) -> dict:
        result = await self._session.call_tool(
            "get_hero_deaths",
            arguments={"match_id": match_id}
        )
        return json.loads(result.content[0].text)

    async def get_objectives(self, match_id: int) -> dict:
        result = await self._session.call_tool(
            "get_objective_kills",
            arguments={"match_id": match_id}
        )
        return json.loads(result.content[0].text)

    async def get_fight(self, match_id: int, time: float, hero: str = None) -> dict:
        args = {"match_id": match_id, "reference_time": time}
        if hero:
            args["hero"] = hero
        result = await self._session.call_tool("get_fight_combat_log", arguments=args)
        return json.loads(result.content[0].text)

# Usage
async def main():
    async with Dota2MCPClient("/path/to/mcp_replay_dota2") as client:
        deaths = await client.get_hero_deaths(8461956309)
        print(f"Deaths: {deaths['total_deaths']}")

asyncio.run(main())
```
