# Installation

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/) package manager

## Clone the Repository

```bash
git clone https://github.com/DeepBlueCoding/mcp_replay_dota2.git
cd mcp_replay_dota2
```

## Install Dependencies

```bash
uv sync
```

This will install all required dependencies including:

- `fastmcp` - MCP server framework
- `python-opendota-sdk` - OpenDota API client
- `python-manta` - Dota 2 replay parser

## Development Dependencies

For development (testing, linting):

```bash
uv sync --group dev
```

## Verify Installation

```bash
uv run python dota_match_mcp_server.py --version
```

## Running the Server

```bash
uv run python dota_match_mcp_server.py
```

The server will start and expose MCP resources and tools via stdin/stdout.
