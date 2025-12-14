# Docker Deployment

The Dota 2 Match MCP Server can be run in Docker for faster startup times and consistent deployment.

## Quick Start

### Build the Image

```bash
docker build -t dota2-mcp-server .
```

### Run with SSE Transport (Recommended for Docker)

```bash
docker run -p 8081:8081 dota2-mcp-server --transport sse
```

The server will be available at `http://localhost:8081/sse`.

### Run with Docker Compose

```bash
# SSE transport (default)
docker compose up mcp-server

# STDIO transport
docker compose --profile stdio run --rm mcp-server-stdio
```

## Transport Modes

### SSE (Server-Sent Events) - Recommended for Docker

SSE transport runs an HTTP server, which is ideal for Docker deployments:

```bash
docker run -p 8081:8081 dota2-mcp-server --transport sse --port 8081
```

Configure your MCP client to connect to `http://localhost:8081/sse`.

### STDIO (Standard I/O)

STDIO transport is the default for local development but requires interactive mode in Docker:

```bash
docker run -i dota2-mcp-server
```

## Persistent Cache

Replay files are large (50-400MB) and take time to download and parse. Mount a volume to persist the cache:

```bash
docker run -p 8081:8081 \
  -v dota2-replay-cache:/app/.cache/mcp_dota2 \
  dota2-mcp-server --transport sse
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8081` | Port for SSE transport |

## Claude Desktop Configuration

### SSE Transport (Recommended)

```json
{
  "mcpServers": {
    "dota2": {
      "url": "http://localhost:8081/sse"
    }
  }
}
```

### STDIO Transport

```json
{
  "mcpServers": {
    "dota2": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-v", "dota2-replay-cache:/app/.cache/mcp_dota2", "dota2-mcp-server"]
    }
  }
}
```

## Startup Optimization

The Docker image uses several optimizations for fast startup:

1. **Pre-compiled bytecode** (`UV_COMPILE_BYTECODE=1`) - Python bytecode is compiled at build time
2. **Slim base image** - Uses `python:3.12-slim-bookworm` for minimal size
3. **Layer caching** - Dependencies are installed in a separate layer for faster rebuilds
4. **No runtime dependency resolution** - Uses locked dependencies from `uv.lock`

## Building for Production

For production deployments, consider:

1. **Use a specific tag** instead of `latest`:
   ```bash
   docker build -t dota2-mcp-server:1.0.0 .
   ```

2. **Set resource limits**:
   ```bash
   docker run -p 8081:8081 \
     --memory=2g \
     --cpus=2 \
     dota2-mcp-server --transport sse
   ```

3. **Health checks** are included in `docker-compose.yml`

## Troubleshooting

### Slow Startup

If startup is slow, ensure:
- The Docker image has been built (not building on first run)
- The cache volume is mounted (avoids re-downloading replays)
- Sufficient memory is allocated (at least 1GB recommended)

### Connection Refused

If you get "connection refused" when connecting to SSE:
- Ensure the container is running: `docker ps`
- Check the port mapping: `docker run -p 8081:8081 ...`
- Verify the transport mode: `--transport sse`
