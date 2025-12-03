# AutoGen

<details>
<summary><strong>🤖 AI Summary</strong></summary>

Install: `pip install pyautogen langchain-mcp-adapters`. Create `AssistantAgent` with function definitions, `UserProxyAgent` with `function_map` to execute MCP tools. Use `a_initiate_chat()` for conversation. For multi-agent: create specialists (FightExpert, MacroExpert) and use `GroupChat` + `GroupChatManager`.

</details>

Build conversational agents that analyze matches through dialogue.

## Install Dependencies

```bash
pip install pyautogen langchain-mcp-adapters
```

## Setup

```python
import asyncio
from autogen import AssistantAgent, UserProxyAgent, config_list_from_json
from langchain_mcp_adapters import MCPToolkit

# Connect to MCP server
toolkit = MCPToolkit(
    command="uv",
    args=["run", "python", "dota_match_mcp_server.py"],
    cwd="/path/to/mcp_replay_dota2"
)

# LLM config
config_list = [{"model": "gpt-4o", "api_key": "your-api-key"}]
llm_config = {"config_list": config_list}
```

## Define Tool Functions

```python
async def get_hero_deaths(match_id: int) -> dict:
    """Get all hero deaths in a Dota 2 match."""
    return await toolkit.acall_tool("get_hero_deaths", {"match_id": match_id})

async def get_fight_combat_log(match_id: int, reference_time: float, hero: str = None) -> dict:
    """Get combat log for a fight around a specific time."""
    return await toolkit.acall_tool("get_fight_combat_log", {
        "match_id": match_id,
        "reference_time": reference_time,
        "hero": hero
    })

async def get_objective_kills(match_id: int) -> dict:
    """Get Roshan, tower, and barracks kills."""
    return await toolkit.acall_tool("get_objective_kills", {"match_id": match_id})
```

## Create Agents

```python
# Analyst agent with tool access
analyst = AssistantAgent(
    name="DotaAnalyst",
    system_message="""You are an expert Dota 2 analyst. Use the available tools to analyze matches.
    Always explain your findings in terms casual players can understand.
    Focus on actionable insights - what could the losing team have done differently?""",
    llm_config={
        **llm_config,
        "functions": [
            {
                "name": "get_hero_deaths",
                "description": "Get all hero deaths in a match",
                "parameters": {
                    "type": "object",
                    "properties": {"match_id": {"type": "integer"}},
                    "required": ["match_id"]
                }
            },
            {
                "name": "get_fight_combat_log",
                "description": "Get combat log for a fight",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "match_id": {"type": "integer"},
                        "reference_time": {"type": "number"},
                        "hero": {"type": "string"}
                    },
                    "required": ["match_id", "reference_time"]
                }
            },
            {
                "name": "get_objective_kills",
                "description": "Get Roshan and tower kills",
                "parameters": {
                    "type": "object",
                    "properties": {"match_id": {"type": "integer"}},
                    "required": ["match_id"]
                }
            }
        ]
    }
)

# User proxy that can execute functions
user_proxy = UserProxyAgent(
    name="User",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    code_execution_config=False,
    function_map={
        "get_hero_deaths": get_hero_deaths,
        "get_fight_combat_log": get_fight_combat_log,
        "get_objective_kills": get_objective_kills
    }
)
```

## Run Analysis

```python
async def main():
    async with toolkit:
        await user_proxy.a_initiate_chat(
            analyst,
            message="Analyze match 8461956309. I was playing Earthshaker and we lost. What did I do wrong?"
        )

asyncio.run(main())
```

## Multi-Agent Discussion

Create multiple specialists that discuss the match:

```python
fight_expert = AssistantAgent(
    name="FightExpert",
    system_message="You specialize in teamfight analysis. Focus on ability usage and positioning.",
    llm_config=llm_config
)

macro_expert = AssistantAgent(
    name="MacroExpert",
    system_message="You specialize in macro gameplay - objectives, map control, and timing.",
    llm_config=llm_config
)

# Group chat for discussion
from autogen import GroupChat, GroupChatManager

groupchat = GroupChat(
    agents=[user_proxy, analyst, fight_expert, macro_expert],
    messages=[],
    max_round=12
)

manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)

async def main():
    async with toolkit:
        await user_proxy.a_initiate_chat(
            manager,
            message="Analyze match 8461956309 as a team. Each expert should contribute their specialty."
        )

asyncio.run(main())
```
