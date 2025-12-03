# OpenAI API

??? info "🤖 AI Summary"

    Install: `pip install openai mcp`. Define tools with `type: "function"` schema. Create `MCPToolExecutor` to call MCP server. Agentic loop: call `chat.completions.create()` with tools → check `message.tool_calls` → execute via MCP → add tool results → repeat until no tool_calls. Supports streaming and parallel tool calls.

Use MCP tools with OpenAI models (GPT-4, GPT-4o, etc.).

## Install

```bash
pip install openai mcp
```

## Setup

```python
from openai import OpenAI
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

client = OpenAI()

# Tool definitions for OpenAI
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_hero_deaths",
            "description": "Get all hero deaths in a Dota 2 match",
            "parameters": {
                "type": "object",
                "properties": {
                    "match_id": {"type": "integer", "description": "The Dota 2 match ID"}
                },
                "required": ["match_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_fight_combat_log",
            "description": "Get combat log for a fight around a specific time",
            "parameters": {
                "type": "object",
                "properties": {
                    "match_id": {"type": "integer"},
                    "reference_time": {"type": "number"},
                    "hero": {"type": "string"}
                },
                "required": ["match_id", "reference_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_objective_kills",
            "description": "Get Roshan, tower, and barracks kills",
            "parameters": {
                "type": "object",
                "properties": {
                    "match_id": {"type": "integer"}
                },
                "required": ["match_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_item_purchases",
            "description": "Get item purchase timings",
            "parameters": {
                "type": "object",
                "properties": {
                    "match_id": {"type": "integer"},
                    "hero_filter": {"type": "string"}
                },
                "required": ["match_id"]
            }
        }
    }
]
```

## MCP Tool Executor

```python
class MCPToolExecutor:
    def __init__(self, server_path: str):
        self.server_path = server_path

    async def execute(self, tool_name: str, tool_args: dict) -> str:
        server_params = StdioServerParameters(
            command="uv",
            args=["run", "python", "dota_match_mcp_server.py"],
            cwd=self.server_path
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=tool_args)
                return result.content[0].text

executor = MCPToolExecutor("/path/to/mcp_replay_dota2")
```

## Agentic Loop

```python
async def analyze_match(user_message: str):
    messages = [
        {"role": "system", "content": "You are an expert Dota 2 analyst. Use the available tools to analyze matches and provide insights."},
        {"role": "user", "content": user_message}
    ]

    while True:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"
        )

        message = response.choices[0].message

        # Check if done
        if message.tool_calls is None:
            return message.content

        # Add assistant message
        messages.append(message)

        # Process tool calls
        for tool_call in message.tool_calls:
            print(f"Calling {tool_call.function.name}...")

            # Parse arguments
            args = json.loads(tool_call.function.arguments)

            # Execute via MCP
            result = await executor.execute(tool_call.function.name, args)

            # Add tool result
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

# Run
result = asyncio.run(analyze_match("Analyze match 8461956309. What happened at first blood?"))
print(result)
```

## Streaming

```python
async def analyze_match_streaming(user_message: str):
    messages = [
        {"role": "system", "content": "You are an expert Dota 2 analyst."},
        {"role": "user", "content": user_message}
    ]

    while True:
        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOLS,
            stream=True
        )

        tool_calls = []
        content = ""

        for chunk in stream:
            delta = chunk.choices[0].delta

            if delta.content:
                print(delta.content, end="", flush=True)
                content += delta.content

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tc.index >= len(tool_calls):
                        tool_calls.append({"id": "", "name": "", "arguments": ""})
                    if tc.id:
                        tool_calls[tc.index]["id"] = tc.id
                    if tc.function.name:
                        tool_calls[tc.index]["name"] = tc.function.name
                    if tc.function.arguments:
                        tool_calls[tc.index]["arguments"] += tc.function.arguments

        if not tool_calls:
            print()
            return content

        # Process tool calls
        messages.append({
            "role": "assistant",
            "content": content,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]}
                }
                for tc in tool_calls
            ]
        })

        for tc in tool_calls:
            args = json.loads(tc["arguments"])
            result = await executor.execute(tc["name"], args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result
            })

asyncio.run(analyze_match_streaming("Full analysis of match 8461956309"))
```

## With Parallel Tool Calls

GPT-4o can request multiple tools in parallel:

```python
# The agentic loop above handles this automatically
# GPT-4o will return multiple tool_calls when it wants parallel execution

# Example response structure:
# message.tool_calls = [
#     ToolCall(id="1", function=Function(name="get_hero_deaths", arguments="{\"match_id\": 8461956309}")),
#     ToolCall(id="2", function=Function(name="get_objective_kills", arguments="{\"match_id\": 8461956309}"))
# ]
```
