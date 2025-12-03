# LangGraph

??? info "🤖 AI Summary"

    Install: `pip install langgraph langchain-openai langchain-mcp-adapters`. Use `create_react_agent(llm, tools)` for simple ReAct agent. Build custom `StateGraph` for specialized flows: get_deaths → identify_fights → get_objectives → synthesize. Supports streaming via `astream_events()`.

Build stateful, multi-step Dota 2 analysis agents with LangGraph.

## Install Dependencies

```bash
pip install langgraph langchain-openai langchain-mcp-adapters
```

## ReAct Agent

The simplest LangGraph agent - reasons and acts in a loop:

```python
import asyncio
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters import MCPToolkit
from langgraph.prebuilt import create_react_agent

async def main():
    toolkit = MCPToolkit(
        command="uv",
        args=["run", "python", "dota_match_mcp_server.py"],
        cwd="/path/to/mcp_replay_dota2"
    )

    async with toolkit:
        tools = toolkit.get_tools()
        llm = ChatOpenAI(model="gpt-4o")

        # Create ReAct agent
        agent = create_react_agent(llm, tools)

        # Run analysis
        response = await agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": "Analyze match 8461956309. First get all deaths, then analyze the biggest teamfight."
            }]
        })

        print(response["messages"][-1].content)

asyncio.run(main())
```

## Custom Graph for Match Analysis

Build a specialized graph that follows a specific analysis flow:

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class AnalysisState(TypedDict):
    match_id: int
    deaths: list
    fights: list
    objectives: list
    analysis: str
    messages: Annotated[list, operator.add]

def get_deaths(state: AnalysisState):
    # Call get_hero_deaths tool
    deaths = tools["get_hero_deaths"].invoke({"match_id": state["match_id"]})
    return {"deaths": deaths["deaths"]}

def identify_fights(state: AnalysisState):
    # Find clusters of deaths = teamfights
    fights = []
    for death in state["deaths"]:
        fight = tools["get_fight_combat_log"].invoke({
            "match_id": state["match_id"],
            "reference_time": death["game_time"],
            "hero": death["victim"]
        })
        if fight["duration"] > 10 and len(fight["participants"]) > 4:
            fights.append(fight)
    return {"fights": fights}

def get_objectives(state: AnalysisState):
    objectives = tools["get_objective_kills"].invoke({"match_id": state["match_id"]})
    return {"objectives": objectives}

def synthesize(state: AnalysisState):
    # Use LLM to synthesize analysis
    prompt = f"""Analyze this match:
    - {len(state['deaths'])} total deaths
    - {len(state['fights'])} major teamfights
    - Roshan kills: {len(state['objectives']['roshan_kills'])}
    - Towers: {len(state['objectives']['tower_kills'])}

    Key fights: {state['fights'][:3]}
    """
    response = llm.invoke(prompt)
    return {"analysis": response.content}

# Build graph
graph = StateGraph(AnalysisState)
graph.add_node("get_deaths", get_deaths)
graph.add_node("identify_fights", identify_fights)
graph.add_node("get_objectives", get_objectives)
graph.add_node("synthesize", synthesize)

graph.set_entry_point("get_deaths")
graph.add_edge("get_deaths", "identify_fights")
graph.add_edge("get_deaths", "get_objectives")  # parallel
graph.add_edge("identify_fights", "synthesize")
graph.add_edge("get_objectives", "synthesize")
graph.add_edge("synthesize", END)

app = graph.compile()
```

## Streaming Results

LangGraph supports streaming for long analyses:

```python
async for event in agent.astream_events(
    {"messages": [{"role": "user", "content": "Full analysis of match 8461956309"}]},
    version="v2"
):
    if event["event"] == "on_chat_model_stream":
        print(event["data"]["chunk"].content, end="", flush=True)
```
