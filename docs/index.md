# MCP Dota 2 Match Analysis Server

A Model Context Protocol (MCP) server that gives LLMs the ability to analyze Dota 2 matches by parsing replay files and querying the OpenDota API.

## What This Does

This server exposes **tools** and **resources** that an LLM can call to answer questions about Dota 2 matches:

- "Why did we lose the teamfight at 25 minutes?"
- "How did the enemy Anti-Mage get such a fast Battle Fury?"
- "When did Roshan die and who took the Aegis?"
- "Show me what happened when I died at minute 12"

The LLM reads the replay data and provides analysis based on actual game events, not guesswork.

## How MCP Works

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   LLM Client    │ ──MCP── │   This Server   │ ──────▸ │  Replay Parser  │
│ (Claude, GPT)   │         │                 │         │  OpenDota API   │
└─────────────────┘         └─────────────────┘         └─────────────────┘
         │                           │
         │   "Analyze match 123"     │
         │ ─────────────────────────▸│
         │                           │
         │                           │── calls get_hero_deaths(123)
         │                           │── calls get_combat_log(123, ...)
         │                           │── calls get_objective_kills(123)
         │                           │
         │   structured JSON data    │
         │ ◂─────────────────────────│
         │                           │
         ▼                           ▼
   LLM synthesizes response: "The fight was lost because..."
```

**Resources** = Static data the LLM can reference (hero list, map positions)
**Tools** = Functions the LLM can call with parameters (get deaths, get combat log)

## Quick Start

### 1. Install

```bash
git clone https://github.com/DeepBlueCoding/mcp_replay_dota2.git
cd mcp_replay_dota2
uv sync
```

### 2. Connect to Your LLM

See [Integrations](integrations/index.md) for setup with:

- Claude Desktop
- Claude Code CLI
- OpenAI + LangChain
- Custom Python clients

### 3. Ask Questions

Once connected, just ask naturally:

> "Analyze match 8461956309. Why did Radiant lose?"

The LLM will automatically call the appropriate tools and synthesize an analysis.

## Available Tools

| Tool | What It Does |
|------|--------------|
| `get_hero_deaths` | All deaths with killer, victim, ability used |
| `get_combat_log` | Damage events, abilities, modifiers in a time range |
| `get_fight_combat_log` | Auto-detects fight boundaries around a death |
| `get_item_purchases` | When each item was bought |
| `get_objective_kills` | Roshan, towers, barracks timings |
| `get_match_timeline` | Net worth, XP, KDA over time |
| `get_stats_at_minute` | Snapshot of all players at a specific minute |
| `get_courier_kills` | Courier snipes with position |

## Available Resources

| URI | Data |
|-----|------|
| `dota2://heroes/all` | All 124 heroes with attributes |
| `dota2://map` | Tower, camp, rune, landmark positions |
| `dota2://match/{id}/heroes` | 10 heroes in match with stats |
| `dota2://match/{id}/players` | 10 players with names and heroes |

## Example Conversations

See [Use Cases](examples/use-cases.md) for detailed examples:

- Analyzing why a teamfight was lost
- Tracking a carry's item timings
- Understanding a gank that went wrong
- Comparing laning phase performance
