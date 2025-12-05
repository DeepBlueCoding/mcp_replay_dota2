# MCP Dota 2 Match Analysis Server

[![Build Status](https://github.com/DeepBlueCoding/mcp_replay_dota2/actions/workflows/test.yml/badge.svg)](https://github.com/DeepBlueCoding/mcp_replay_dota2/actions/workflows/test.yml)
[![Documentation](https://img.shields.io/badge/docs-gh--pages-blue.svg)](https://deepbluecoding.github.io/mcp_replay_dota2/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)

[FastMCP](https://github.com/jlowin/fastmcp) server for Dota 2 match analysis using replay files and OpenDota API.

## Quick Start

```bash
git clone https://github.com/DeepBlueCoding/mcp_replay_dota2.git
cd mcp_replay_dota2
uv sync
uv run python dota_match_mcp_server.py
```

## What It Does

- **Resources**: Static reference data (heroes, map, pro players/teams)
- **Tools**: Match analysis (deaths, combat log, objectives, timelines, drafts)

See [full documentation](https://deepbluecoding.github.io/mcp_replay_dota2/) for API reference and integration guides.

## Development

```bash
uv run pytest                    # Run tests
uv run pytest -m "not integration"  # Skip slow tests
```

## License

MIT
