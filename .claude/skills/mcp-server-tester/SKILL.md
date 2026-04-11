---
name: mcp-server-tester
description: >
  Test and verify that an MCP server is correctly running and exposing its tools.
  Use this skill when: (1) setting up a new MCP server (Docker, npx, or any transport),
  (2) verifying a Streamable HTTP or SSE MCP server after deployment or config changes,
  (3) debugging connection issues or checking which tools are registered,
  (4) the user asks to "test", "verify", "check", or "validate" an MCP server.
  Handles virtual environment setup automatically using uv if .venv is missing.
---

# MCP Server Tester

## Overview

Test any HTTP-based MCP server (Streamable HTTP or SSE transport) using the `fastmcp` CLI.
The workflow covers: environment setup → health check → tool listing → optional tool call.

## Workflow

### Step 1 — Ensure Python environment

Check if `.venv` exists in the current project directory:

```bash
ls .venv/bin/fastmcp 2>/dev/null || echo "missing"
```

**If missing**, create and set up with `uv`:

```bash
uv venv .venv
uv pip install fastmcp --python .venv/bin/python
```

**If `uv` is not installed**, tell the user to install it:
```
https://docs.astral.sh/uv/getting-started/installation/
```

Activate with:
```bash
source .venv/bin/activate
```

### Step 2 — Health check

不同的 MCP server 健康檢查方式不同，按以下順序嘗試：

**Strategy A：`/health` 端點**（FastMCP 內建，非所有 server 都有）

```bash
curl -sf http://localhost:PORT/health
```

Expected response: `ok` with HTTP 200.

**Strategy B：MCP initialize 握手**（通用，任何 HTTP MCP server 都適用）

當 `/health` 不存在時，改用標準 MCP 協議的 `initialize` 請求：

```bash
curl -sf --max-time 10 \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"healthcheck","version":"1.0"}}}' \
  http://localhost:PORT/mcp
```

回應中包含 `"protocolVersion"` 即代表 server 正常運作。

這個方式同時驗證了 HTTP 層 + MCP 協議層，比單純 ping `/health` 更完整。

**Docker Compose 健康檢查建議**：

> ⚠️ Docker healthcheck 是在**容器內部**執行的，URL 中的 PORT 必須填**容器內部 port**（即 `EXPOSE` 的那個 port），而不是對外 mapping 的 host port。
>
> 例如 `ports: "8004:3000"` → healthcheck URL 應用 `3000`，不是 `8004`。

若 server 有 `/health`：
```yaml
test: ["CMD", "wget", "-qO", "/dev/null", "http://localhost:3000/health"]
```

若 server 沒有 `/health`，改用 MCP initialize（PORT 同樣填容器內部 port）：
```yaml
test: ["CMD-SHELL", "curl -sf --max-time 10 -X POST -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2024-11-05\",\"capabilities\":{},\"clientInfo\":{\"name\":\"healthcheck\",\"version\":\"1.0\"}}}' http://127.0.0.1:3000/mcp"]
interval: 30s
timeout: 15s
retries: 3
start_period: 120s
```

至於 MCP path（`/mcp`、`/sse` 等），視各 server 實作而定，查看 server 文件或啟動 log 確認。

### Step 3 — List tools

```bash
fastmcp list http://localhost:PORT/mcp --auth none
```

Use `--auth none` for local servers without authentication.
Add `--json` for machine-readable output.

A healthy server should return a numbered tool list. If connection fails, check:
- Is the server/container running?
- Is the port mapping correct?
- For Docker: is `HOST=0.0.0.0` set? (not `localhost`)

### Step 4 — Call a tool (functional test)

Pick a lightweight, read-only tool and call it with `--input-json`:

```bash
fastmcp call http://localhost:PORT/mcp <tool_name> --auth none '{"param": "value"}'
```

**Tip:** For servers without obvious lightweight tools, use the first tool returned by `fastmcp list`
and construct minimal valid arguments based on its schema.

## Using the Bundled Script

`scripts/test_mcp_server.sh` automates all four steps. Run it from the project root:

```bash
# List tools only
bash /path/to/skill/scripts/test_mcp_server.sh http://localhost:8004/mcp

# List tools + call one tool
bash /path/to/skill/scripts/test_mcp_server.sh \
  http://localhost:8004/mcp \
  tool_name \
  '{"param": "value"}'
```

The script will auto-create `.venv` and install `fastmcp` if not already set up.

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `All connection attempts failed` | Server not running | Start the server first |
| `All connection attempts failed` | Wrong port | Check port mapping in docker-compose |
| Connection ok but tools empty | Server starting up | Wait a few seconds and retry |
| Docker container reachable but tools fail | `HOST` not set to `0.0.0.0` | Add `HOST=0.0.0.0` to environment |
| `uv: command not found` | uv not installed | Install uv from https://docs.astral.sh/uv/getting-started/installation/ |

## MCP URL Patterns

| Transport | URL format |
|-----------|-----------|
| Streamable HTTP (FastMCP) | `http://localhost:PORT/mcp` |
| SSE (older FastMCP) | `http://localhost:PORT/sse` |
| Custom path | Check server docs for the exact path |
