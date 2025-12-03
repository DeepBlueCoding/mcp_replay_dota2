# Claude Desktop

<details>
<summary><strong>🤖 AI Summary</strong></summary>

Add to `claude_desktop_config.json`: `{"mcpServers": {"dota2": {"command": "uv", "args": ["run", "python", "dota_match_mcp_server.py"], "cwd": "/path/to/repo"}}}`. Restart Claude Desktop. Look for hammer icon (🔨) to verify. Ask naturally: "Analyze match 8461956309".

</details>

The simplest way to use this MCP server - just configure and chat.

## Setup

Add to your Claude Desktop config file:

**Linux:** `~/.config/claude/claude_desktop_config.json`
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "dota2": {
      "command": "uv",
      "args": ["run", "python", "dota_match_mcp_server.py"],
      "cwd": "/path/to/mcp_replay_dota2"
    }
  }
}
```

## Restart Claude Desktop

After saving the config, restart Claude Desktop completely (quit and reopen).

## Verify Connection

You should see a hammer icon (🔨) in the chat input area. Click it to see available tools:

- `get_hero_deaths`
- `get_combat_log`
- `get_fight_combat_log`
- `get_item_purchases`
- `get_objective_kills`
- `get_match_timeline`
- `get_stats_at_minute`
- `get_courier_kills`

## Usage

Just ask naturally:

> "Analyze match 8461956309. Why did Radiant lose the fight at 25 minutes?"

Claude will automatically:
1. Call `get_hero_deaths` to find deaths around that time
2. Call `get_fight_combat_log` to get fight details
3. Synthesize an analysis

## Troubleshooting

**No hammer icon?**
- Check the config file path is correct
- Ensure `uv` is in your PATH
- Check Claude Desktop logs for errors

**Tools not working?**
- Verify the `cwd` path is correct
- Try running `uv run python dota_match_mcp_server.py` manually to check for errors
