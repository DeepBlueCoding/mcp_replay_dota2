# CrewAI

Build multi-agent systems where specialized agents collaborate on match analysis.

## Install Dependencies

```bash
pip install crewai crewai-tools langchain-mcp-adapters
```

## Setup MCP Tools for CrewAI

```python
import asyncio
from crewai import Agent, Task, Crew
from crewai_tools import tool
from langchain_mcp_adapters import MCPToolkit

# Connect to MCP server
toolkit = MCPToolkit(
    command="uv",
    args=["run", "python", "dota_match_mcp_server.py"],
    cwd="/path/to/mcp_replay_dota2"
)

# Wrap MCP tools as CrewAI tools
@tool("Get Hero Deaths")
def get_hero_deaths(match_id: int) -> dict:
    """Get all hero deaths in a Dota 2 match."""
    return toolkit.call_tool("get_hero_deaths", {"match_id": match_id})

@tool("Get Fight Combat Log")
def get_fight_combat_log(match_id: int, reference_time: float, hero: str = None) -> dict:
    """Get combat log for a fight around a specific time."""
    return toolkit.call_tool("get_fight_combat_log", {
        "match_id": match_id,
        "reference_time": reference_time,
        "hero": hero
    })

@tool("Get Item Purchases")
def get_item_purchases(match_id: int, hero_filter: str = None) -> dict:
    """Get item purchase timings for heroes."""
    return toolkit.call_tool("get_item_purchases", {
        "match_id": match_id,
        "hero_filter": hero_filter
    })

@tool("Get Objectives")
def get_objective_kills(match_id: int) -> dict:
    """Get Roshan, tower, and barracks kills."""
    return toolkit.call_tool("get_objective_kills", {"match_id": match_id})
```

## Define Specialized Agents

```python
# Agent that analyzes teamfights
fight_analyst = Agent(
    role="Teamfight Analyst",
    goal="Analyze teamfights and identify what went wrong or right",
    backstory="Expert at breaking down Dota 2 teamfights, understanding ability usage and positioning",
    tools=[get_hero_deaths, get_fight_combat_log],
    verbose=True
)

# Agent that analyzes economy
economy_analyst = Agent(
    role="Economy Analyst",
    goal="Track gold, items, and farm efficiency",
    backstory="Specialist in Dota 2 economy, item timings, and net worth analysis",
    tools=[get_item_purchases],
    verbose=True
)

# Agent that tracks objectives
objective_analyst = Agent(
    role="Objective Analyst",
    goal="Track Roshan, towers, and map control",
    backstory="Expert at macro gameplay, objective timings, and strategic decisions",
    tools=[get_objective_kills],
    verbose=True
)

# Lead analyst that synthesizes everything
lead_analyst = Agent(
    role="Lead Analyst",
    goal="Synthesize analysis from all specialists into actionable insights",
    backstory="Senior Dota 2 coach who combines tactical and strategic analysis",
    verbose=True
)
```

## Create Analysis Tasks

```python
match_id = 8461956309

fight_task = Task(
    description=f"Analyze all major teamfights in match {match_id}. Find the 3 most impactful fights and explain what happened.",
    expected_output="Detailed breakdown of 3 key teamfights with ability usage and positioning analysis",
    agent=fight_analyst
)

economy_task = Task(
    description=f"Analyze carry item timings in match {match_id}. Compare farming efficiency.",
    expected_output="Item timing analysis for carries with efficiency comparison",
    agent=economy_analyst
)

objective_task = Task(
    description=f"Track all objective kills in match {match_id}. Analyze Roshan control and tower trading.",
    expected_output="Timeline of objectives with strategic analysis",
    agent=objective_analyst
)

synthesis_task = Task(
    description="Combine all analyses into a match report. Identify the key reasons for the outcome.",
    expected_output="Complete match analysis with 3-5 key takeaways",
    agent=lead_analyst,
    context=[fight_task, economy_task, objective_task]
)
```

## Run the Crew

```python
crew = Crew(
    agents=[fight_analyst, economy_analyst, objective_analyst, lead_analyst],
    tasks=[fight_task, economy_task, objective_task, synthesis_task],
    verbose=True
)

async def main():
    async with toolkit:
        result = crew.kickoff()
        print(result)

asyncio.run(main())
```

## Example Output

```
[Fight Analyst] Analyzing deaths in match 8461956309...
[Fight Analyst] Found 45 deaths. Identifying major fights...
[Fight Analyst] Key fight at 24:47 - 4 deaths in 11 seconds...

[Economy Analyst] Checking item timings...
[Economy Analyst] Anti-Mage Battle Fury at 9:00 (excellent)
[Economy Analyst] Medusa Manta at 18:00 (good)

[Objective Analyst] Tracking objectives...
[Objective Analyst] Dire took all 4 Roshans
[Objective Analyst] 14 towers destroyed...

[Lead Analyst] Synthesizing analysis...

MATCH ANALYSIS - 8461956309
===========================
Radiant lost due to:
1. Lost Roshan control (0/4)
2. Teamfight at 24:47 cost them high ground
3. Medusa snowballed with uncontested farm
...
```
