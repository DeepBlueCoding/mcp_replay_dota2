# Installation

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/) package manager

## Install

```bash
git clone https://github.com/DeepBlueCoding/mcp_replay_dota2.git
cd mcp_replay_dota2
uv sync
```

## Verify

```bash
uv run python dota_match_mcp_server.py
```

You should see:
```
Dota 2 Match MCP Server starting...
Resources: dota2://heroes/all, dota2://map, ...
Tools: get_hero_deaths, get_combat_log, ...
```

## Next Step

[Connect to your LLM](configuration.md)
