# Anthropic API

??? info "🤖 AI Summary"

    Install: `pip install anthropic mcp`. Define tools with `input_schema`. Create `MCPToolExecutor` class to call MCP server. Implement agentic loop: call Claude with tools → check `stop_reason` → if `tool_use`, execute via MCP, return results → repeat until `end_turn`. Supports streaming with `messages.stream()`.

Integrate MCP tools directly with Claude API for full control.

## Overview

This approach gives you complete control over the tool calling loop. You define tools for Claude, handle tool calls yourself by calling the MCP server, and return results to Claude.

## Install

```bash
pip install anthropic mcp
```

## Setup

```python
import anthropic
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

client = anthropic.Anthropic()

# Tool definitions for Claude
TOOLS = [
    {
        "name": "get_hero_deaths",
        "description": "Get all hero deaths in a Dota 2 match. Returns killer, victim, ability, and timing for each death.",
        "input_schema": {
            "type": "object",
            "properties": {
                "match_id": {
                    "type": "integer",
                    "description": "The Dota 2 match ID"
                }
            },
            "required": ["match_id"]
        }
    },
    {
        "name": "get_fight_combat_log",
        "description": "Get combat log for a fight around a specific time. Auto-detects fight boundaries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "match_id": {"type": "integer"},
                "reference_time": {"type": "number", "description": "Game time in seconds"},
                "hero": {"type": "string", "description": "Optional hero to anchor detection"}
            },
            "required": ["match_id", "reference_time"]
        }
    },
    {
        "name": "get_objective_kills",
        "description": "Get Roshan, tormentor, tower, and barracks kills.",
        "input_schema": {
            "type": "object",
            "properties": {
                "match_id": {"type": "integer"}
            },
            "required": ["match_id"]
        }
    },
    {
        "name": "get_item_purchases",
        "description": "Get item purchase timings for heroes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "match_id": {"type": "integer"},
                "hero_filter": {"type": "string", "description": "Optional hero name filter"}
            },
            "required": ["match_id"]
        }
    }
]
```

## MCP Tool Executor

```python
class MCPToolExecutor:
    def __init__(self, server_path: str):
        self.server_path = server_path

    async def execute(self, tool_name: str, tool_input: dict) -> str:
        server_params = StdioServerParameters(
            command="uv",
            args=["run", "python", "dota_match_mcp_server.py"],
            cwd=self.server_path
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=tool_input)
                return result.content[0].text

executor = MCPToolExecutor("/path/to/mcp_replay_dota2")
```

## Agentic Loop

```python
async def analyze_match(user_message: str):
    messages = [{"role": "user", "content": user_message}]

    while True:
        # Call Claude
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            tools=TOOLS,
            messages=messages
        )

        # Check if done
        if response.stop_reason == "end_turn":
            # Extract final text response
            for block in response.content:
                if block.type == "text":
                    return block.text
            return ""

        # Handle tool use
        if response.stop_reason == "tool_use":
            # Add assistant message
            messages.append({"role": "assistant", "content": response.content})

            # Process each tool call
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"Calling {block.name}({block.input})")

                    # Execute via MCP
                    result = await executor.execute(block.name, block.input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            # Add tool results
            messages.append({"role": "user", "content": tool_results})

# Run
result = asyncio.run(analyze_match(
    "Analyze match 8461956309. Focus on the first blood and subsequent laning phase."
))
print(result)
```

## Streaming Response

```python
async def analyze_match_streaming(user_message: str):
    messages = [{"role": "user", "content": user_message}]

    while True:
        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            tools=TOOLS,
            messages=messages
        ) as stream:
            response = stream.get_final_message()

        if response.stop_reason == "end_turn":
            for block in response.content:
                if block.type == "text":
                    print(block.text)
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = await executor.execute(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})

asyncio.run(analyze_match_streaming("Why did Radiant lose match 8461956309?"))
```

## With System Prompt

```python
SYSTEM_PROMPT = """You are an expert Dota 2 analyst. When analyzing matches:

1. Start by getting hero deaths to understand the flow of the game
2. For important deaths, get the fight combat log to understand what happened
3. Check objectives to understand macro gameplay
4. Always explain findings in terms casual players can understand

Focus on actionable insights - what could the losing team have done differently?"""

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    system=SYSTEM_PROMPT,
    tools=TOOLS,
    messages=[{"role": "user", "content": "Analyze match 8461956309"}]
)
```
