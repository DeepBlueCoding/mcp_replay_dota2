# Configuration

## MCP Client Configuration

To use this server with an MCP client, add it to your client's configuration.

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dota2-match": {
      "command": "uv",
      "args": ["run", "python", "dota_match_mcp_server.py"],
      "cwd": "/path/to/mcp_replay_dota2"
    }
  }
}
```

### Generic MCP Client

```json
{
  "servers": {
    "dota2-match": {
      "command": "uv run python dota_match_mcp_server.py",
      "workingDirectory": "/path/to/mcp_replay_dota2"
    }
  }
}
```

## Data Directories

The server uses the following directories:

| Directory | Purpose |
|-----------|---------|
| `data/constants/` | Cached dotaconstants JSON files |
| `data/heroes_fuzzy.json` | Simplified hero data for fuzzy search |
| `~/dota2/replays/` | Downloaded replay files (*.dem) |

## Updating Constants

To update cached hero/item/ability data from dotaconstants:

```bash
uv run python scripts/fetch_constants.py
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENDOTA_API_KEY` | OpenDota API key for higher rate limits | None |
