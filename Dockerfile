# Dota 2 Match MCP Server - Docker Image
# Optimized for fast startup with pre-compiled bytecode

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install dependencies first (cached layer)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Copy source code
COPY src/ /app/src/
COPY data/ /app/data/
COPY dota_match_mcp_server.py /app/
COPY pyproject.toml uv.lock README.md /app/

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Runtime stage - smaller image
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/data /app/data
COPY --from=builder /app/dota_match_mcp_server.py /app/
COPY --from=builder /app/pyproject.toml /app/

# Set up environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=0

# Create cache directories
RUN mkdir -p /app/.cache/mcp_dota2/replays \
    && mkdir -p /app/.cache/mcp_dota2/parsed_replays

# For HTTP/SSE transport (optional)
ENV PORT=8081
EXPOSE 8081

# Default: STDIO transport for MCP
# Override with --transport sse for HTTP/SSE mode
ENTRYPOINT ["python", "dota_match_mcp_server.py"]
