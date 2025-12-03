# Claude Code CLI

<details>
<summary><strong>🤖 AI Summary</strong></summary>

Add to `.mcp.json` (project) or `~/.claude/settings.json` (global): `{"mcpServers": {"dota2": {"command": "uv", "args": ["run", "python", "/path/to/dota_match_mcp_server.py"]}}}`. Verify with `/tools`. Ask: "Analyze match 8461956309". Can also generate scripts using real match data.

</details>

Use the Dota 2 MCP server within Claude Code for development workflows.

## Project-Level Setup

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "dota2": {
      "command": "uv",
      "args": ["run", "python", "/absolute/path/to/mcp_replay_dota2/dota_match_mcp_server.py"]
    }
  }
}
```

## Global Setup

Add to `~/.claude/settings.json` to make it available in all projects:

```json
{
  "mcpServers": {
    "dota2": {
      "command": "uv",
      "args": ["run", "python", "/absolute/path/to/mcp_replay_dota2/dota_match_mcp_server.py"]
    }
  }
}
```

## Verify

Run Claude Code and check available tools:

```bash
claude
> /tools
```

You should see the Dota 2 tools listed.

## Usage

In any Claude Code session:

```
> Analyze match 8461956309 and tell me about the first blood
```

Claude will use the MCP tools automatically.

## Use Case: Replay Analysis Scripts

You can ask Claude Code to write scripts that use match data:

```
> Write a Python script that analyzes carry farm efficiency using match 8461956309 data
```

Claude will call the tools to get real data and generate code that processes it.
