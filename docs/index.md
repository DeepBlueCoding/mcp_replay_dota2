# MCP Dota 2 Match Analysis Server

> Model Context Protocol server for Dota 2 match analysis using replay files

[![Build Status](https://github.com/DeepBlueCoding/mcp_replay_dota2/actions/workflows/test.yml/badge.svg)](https://github.com/DeepBlueCoding/mcp_replay_dota2/actions/workflows/test.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A FastMCP server that provides MCP tools and resources for analyzing Dota 2 matches using replay files and the OpenDota API.

## Features

- **MCP Resources** - Expose Dota 2 data through standardized MCP resource URIs
- **Match Analysis Tools** - Comprehensive tools for analyzing match replays
- **Combat Log Parsing** - Extract hero deaths, item purchases, objective kills
- **Timeline Analysis** - Track player stats throughout the match
- **Map Data** - Tower positions, neutral camps, rune spawns, landmarks

## Quick Start

```python
# Configure your MCP client to connect to this server
# The server exposes resources and tools via the MCP protocol

# Resources available:
# - dota2://heroes/all - All Dota 2 heroes
# - dota2://map - Map positions and landmarks
# - dota2://match/{match_id}/heroes - Heroes in a specific match
# - dota2://match/{match_id}/players - Players in a specific match

# Tools available:
# - get_match_timeline - Time-series data for a match
# - get_stats_at_minute - Player stats at a specific minute
# - get_hero_deaths - All hero death events
# - get_combat_log - Filtered combat log events
# - get_fight_combat_log - Combat events around a fight
# - get_item_purchases - Item purchase timings
# - get_courier_kills - Courier kill events
# - get_objective_kills - Roshan, tower, barracks kills
```

## Architecture

```
MCP Server (dota_match_mcp_server.py)
    ↓
Resources Layer (src/resources/)
    ↓
Utilities Layer (src/utils/)
    ↓
External APIs (OpenDota, dotaconstants, python_manta)
```

## Links

- [GitHub Repository](https://github.com/DeepBlueCoding/mcp_replay_dota2)
- [OpenDota API Docs](https://docs.opendota.com/)
- [MCP Specification](https://modelcontextprotocol.io/)
