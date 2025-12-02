# Connecting to LLMs

This server uses the Model Context Protocol (MCP) to communicate with LLMs. Here's how to connect it to different clients.

## Claude Desktop

Add to `~/.config/claude/claude_desktop_config.json` (Linux) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "dota2": {
      "command": "uv",
      "args": ["run", "python", "dota_match_mcp_server.py"],
      "cwd": "/path/to/mcp_replay_dota2"
    }
  }
}
```

Restart Claude Desktop. You'll see a hammer icon indicating tools are available.

## Claude Code CLI

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "dota2": {
      "command": "uv",
      "args": ["run", "python", "/path/to/mcp_replay_dota2/dota_match_mcp_server.py"]
    }
  }
}
```

Or add globally to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "dota2": {
      "command": "uv",
      "args": ["run", "python", "/path/to/mcp_replay_dota2/dota_match_mcp_server.py"]
    }
  }
}
```

## OpenAI + LangChain

Use the `langchain-mcp-adapters` package to bridge MCP tools to LangChain:

```python
import asyncio
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters import MCPToolkit
from langgraph.prebuilt import create_react_agent

async def main():
    # Connect to MCP server
    toolkit = MCPToolkit(
        command="uv",
        args=["run", "python", "dota_match_mcp_server.py"],
        cwd="/path/to/mcp_replay_dota2"
    )

    async with toolkit:
        # Get tools as LangChain tools
        tools = toolkit.get_tools()

        # Create agent with OpenAI
        llm = ChatOpenAI(model="gpt-4o")
        agent = create_react_agent(llm, tools)

        # Ask about a match
        response = await agent.ainvoke({
            "messages": [{"role": "user", "content": "Analyze match 8461956309. What happened at first blood?"}]
        })
        print(response["messages"][-1].content)

asyncio.run(main())
```

## Custom Python Client

Use the `mcp` package directly:

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
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print("Available tools:", [t.name for t in tools.tools])

            # Call a tool
            result = await session.call_tool(
                "get_hero_deaths",
                arguments={"match_id": 8461956309}
            )
            print(result.content)

asyncio.run(main())
```

## FastMCP Client (Recommended for Python)

Since this server is built with FastMCP, you can use the FastMCP client:

```python
import asyncio
from fastmcp import Client

async def main():
    async with Client("uv run python dota_match_mcp_server.py") as client:
        # Call tools directly
        deaths = await client.call_tool(
            "get_hero_deaths",
            match_id=8461956309
        )
        print(f"Total deaths: {deaths['total_deaths']}")

        # Get resources
        heroes = await client.get_resource("dota2://heroes/all")
        print(f"Total heroes: {len(heroes)}")

asyncio.run(main())
```

## Anthropic API Direct

For programmatic access with Claude API:

```python
import anthropic

client = anthropic.Anthropic()

# Define MCP tools for Claude
tools = [
    {
        "name": "get_hero_deaths",
        "description": "Get all hero deaths in a Dota 2 match",
        "input_schema": {
            "type": "object",
            "properties": {
                "match_id": {"type": "integer", "description": "The match ID"}
            },
            "required": ["match_id"]
        }
    },
    # ... other tools
]

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    tools=tools,
    messages=[
        {"role": "user", "content": "Analyze match 8461956309"}
    ]
)

# Handle tool calls in your code by calling the MCP server
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENDOTA_API_KEY` | OpenDota API key for higher rate limits | None |

## Data Directories

| Directory | Purpose |
|-----------|---------|
| `data/constants/` | Hero, item, ability data from dotaconstants |
| `~/dota2/replays/` | Downloaded replay files (.dem) |

Replays are downloaded automatically when needed and cached locally.
