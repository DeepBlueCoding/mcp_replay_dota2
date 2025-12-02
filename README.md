# MCP Dota 2 Match Analysis Server

> Model Context Protocol server for Dota 2 match analysis using replay files

[![Build Status](https://github.com/DeepBlueCoding/mcp_replay_dota2/actions/workflows/test.yml/badge.svg)](https://github.com/DeepBlueCoding/mcp_replay_dota2/actions/workflows/test.yml)
[![Documentation](https://img.shields.io/badge/docs-gh--pages-blue.svg)](https://deepbluecoding.github.io/mcp_replay_dota2/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A [FastMCP](https://github.com/jlowin/fastmcp) server that provides MCP tools and resources for analyzing Dota 2 matches using replay files and the OpenDota API.

## Features

- **MCP Resources** - Expose Dota 2 data through standardized MCP resource URIs
- **Match Analysis Tools** - Comprehensive tools for analyzing match replays
- **Combat Log Parsing** - Extract hero deaths, item purchases, objective kills
- **Timeline Analysis** - Track player stats throughout the match
- **Map Data** - Tower positions, neutral camps, rune spawns, landmarks

## Installation

```bash
git clone https://github.com/DeepBlueCoding/mcp_replay_dota2.git
cd mcp_replay_dota2
uv sync
```

## Usage

### Running the Server

```bash
uv run python dota_match_mcp_server.py
```

### MCP Resources

| URI | Description |
|-----|-------------|
| `dota2://heroes/all` | All Dota 2 heroes with attributes |
| `dota2://map` | Map positions and landmarks |
| `dota2://match/{match_id}/heroes` | Heroes in a specific match |
| `dota2://match/{match_id}/players` | Players in a specific match |

### MCP Tools

| Tool | Description |
|------|-------------|
| `get_match_timeline` | Time-series data for a match |
| `get_stats_at_minute` | Player stats at a specific minute |
| `get_hero_deaths` | All hero death events |
| `get_combat_log` | Filtered combat log events |
| `get_fight_combat_log` | Combat events around a fight |
| `get_item_purchases` | Item purchase timings |
| `get_courier_kills` | Courier kill events |
| `get_objective_kills` | Roshan, tower, barracks kills |

## Documentation

Full documentation is available at [deepbluecoding.github.io/mcp_replay_dota2](https://deepbluecoding.github.io/mcp_replay_dota2/)

## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run linting
uv run ruff check src/ tests/ dota_match_mcp_server.py

# Run type checking
uv run mypy src/ dota_match_mcp_server.py --ignore-missing-imports

# Run tests (excluding integration tests)
uv run pytest -m "not integration"
```

## License

MIT
