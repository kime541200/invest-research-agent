#!/usr/bin/env bash
# Test an MCP server using fastmcp CLI.
# Usage: test_mcp_server.sh <mcp_url> [tool_name] [tool_args_json]
#
# Examples:
#   ./test_mcp_server.sh http://localhost:8004/mcp
#   ./test_mcp_server.sh http://localhost:8004/mcp firecrawl_scrape '{"url":"https://example.com","formats":["markdown"]}'

set -euo pipefail

MCP_URL="${1:-}"
TOOL_NAME="${2:-}"
TOOL_ARGS="${3:-}"

if [[ -z "$MCP_URL" ]]; then
  echo "Usage: $0 <mcp_url> [tool_name] [tool_args_json]" >&2
  exit 1
fi

PROJECT_ROOT="$(pwd)"

# ── Step 1: Ensure virtual environment exists ─────────────────────────────────
VENV_DIR="$PROJECT_ROOT/.venv"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "📦  No .venv found. Creating with uv..."
  if ! command -v uv &>/dev/null; then
    echo "❌  uv not found. Install it: https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
  fi
  uv venv "$VENV_DIR"
  echo "✅  .venv created"
fi

# ── Step 2: Ensure fastmcp is installed ──────────────────────────────────────
FASTMCP_BIN="$VENV_DIR/bin/fastmcp"

if [[ ! -f "$FASTMCP_BIN" ]]; then
  echo "📦  Installing fastmcp into .venv..."
  if command -v uv &>/dev/null; then
    uv pip install fastmcp --python "$VENV_DIR/bin/python"
  else
    "$VENV_DIR/bin/pip" install fastmcp
  fi
  echo "✅  fastmcp installed"
fi

# ── Step 3: Health check ──────────────────────────────────────────────────────
# Strategy A: /health endpoint (FastMCP built-in, not always present)
# Strategy B: MCP initialize handshake (universal, works on any HTTP MCP server)

BASE_URL="${MCP_URL%/mcp}"
HEALTH_OK=false

echo ""
echo "🔍  Health check..."

# Try /health first
if curl -sf --max-time 5 "$BASE_URL/health" -o /dev/null 2>/dev/null; then
  HEALTH_BODY="$(curl -sf --max-time 5 "$BASE_URL/health")"
  echo "✅  /health OK — response: $HEALTH_BODY"
  HEALTH_OK=true
else
  echo "ℹ️   /health not available — trying MCP initialize handshake..."

  # MCP initialize handshake (standard JSON-RPC over HTTP)
  MCP_INIT_PAYLOAD='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"healthcheck","version":"1.0"}}}'

  INIT_RESPONSE="$(curl -sf --max-time 10 \
    -X POST \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d "$MCP_INIT_PAYLOAD" \
    "$MCP_URL" 2>/dev/null || true)"

  if [[ -n "$INIT_RESPONSE" ]] && echo "$INIT_RESPONSE" | grep -q '"protocolVersion"'; then
    PROTOCOL_VERSION="$(echo "$INIT_RESPONSE" | grep -o '"protocolVersion":"[^"]*"' | head -1 | cut -d'"' -f4)"
    echo "✅  MCP initialize handshake OK — protocolVersion: $PROTOCOL_VERSION"
    HEALTH_OK=true
  else
    echo "⚠️   Both /health and MCP initialize failed. Server may not be ready yet."
    echo "    Response: $INIT_RESPONSE"
  fi
fi

if [[ "$HEALTH_OK" == "false" ]]; then
  echo "❌  Health check failed. Check that the server is running and the URL is correct." >&2
  exit 1
fi

# ── Step 4: List tools ────────────────────────────────────────────────────────
echo ""
echo "🔧  Listing tools at $MCP_URL ..."
"$FASTMCP_BIN" list "$MCP_URL" --auth none

# ── Step 5: Optional tool call ───────────────────────────────────────────────
if [[ -n "$TOOL_NAME" ]]; then
  echo ""
  echo "🚀  Calling tool: $TOOL_NAME"
  if [[ -n "$TOOL_ARGS" ]]; then
    "$FASTMCP_BIN" call "$MCP_URL" "$TOOL_NAME" --auth none "$TOOL_ARGS"
  else
    "$FASTMCP_BIN" call "$MCP_URL" "$TOOL_NAME" --auth none
  fi
fi

echo ""
echo "✅  MCP server test complete."
