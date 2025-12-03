# LangChain

??? info "🤖 AI Summary"

    Install: `pip install langchain langchain-openai langchain-mcp-adapters`. Use `MCPToolkit` to connect, `toolkit.get_tools()` returns LangChain tools. Bind to any LLM: `llm.bind_tools(tools)`. Works with agents via `create_tool_calling_agent()`. Supports Claude via `langchain-anthropic`.

Use MCP tools as LangChain tools with any supported LLM.

## Install Dependencies

```bash
pip install langchain langchain-openai langchain-mcp-adapters
```

## Basic Setup

```python
import asyncio
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters import MCPToolkit

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
        print(f"Available tools: {[t.name for t in tools]}")

        # Use with any LangChain LLM
        llm = ChatOpenAI(model="gpt-4o")
        llm_with_tools = llm.bind_tools(tools)

        response = await llm_with_tools.ainvoke(
            "What happened at first blood in match 8461956309?"
        )
        print(response)

asyncio.run(main())
```

## With LangChain Agents

```python
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

async def main():
    toolkit = MCPToolkit(
        command="uv",
        args=["run", "python", "dota_match_mcp_server.py"],
        cwd="/path/to/mcp_replay_dota2"
    )

    async with toolkit:
        tools = toolkit.get_tools()
        llm = ChatOpenAI(model="gpt-4o")

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a Dota 2 analyst. Use the available tools to analyze matches."),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])

        agent = create_tool_calling_agent(llm, tools, prompt)
        executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        result = await executor.ainvoke({
            "input": "Analyze the teamfight at 25 minutes in match 8461956309"
        })
        print(result["output"])

asyncio.run(main())
```

## With Claude via LangChain

```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(model="claude-sonnet-4-20250514")
llm_with_tools = llm.bind_tools(tools)
```

## Tool Descriptions

The MCP adapter preserves tool descriptions, so the LLM knows when to use each tool:

| Tool | LangChain Description |
|------|----------------------|
| `get_hero_deaths` | Get all hero deaths in a Dota 2 match |
| `get_fight_combat_log` | Get combat log for a fight around a specific time |
| `get_item_purchases` | Get item purchase timings for heroes |
