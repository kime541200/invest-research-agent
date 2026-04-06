from __future__ import annotations

import json
from itertools import count
from typing import Any
from urllib import error, request


class McpClientError(RuntimeError):
    """Raised when the MCP server returns an invalid response."""


class McpHttpClient:
    def __init__(self, endpoint: str, timeout: float = 30.0) -> None:
        self.endpoint = endpoint
        self.timeout = timeout
        self._request_ids = count(1)
        self._initialized = False
        self._session_id: str | None = None

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        self._ensure_initialized()
        response = self._post(
            {
                "jsonrpc": "2.0",
                "id": next(self._request_ids),
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": arguments or {},
                },
            }
        )
        if "error" in response:
            raise McpClientError(f"{name} 呼叫失敗: {response['error']}")
        return _extract_tool_result(response.get("result"))

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return

        response = self._post(
            {
                "jsonrpc": "2.0",
                "id": next(self._request_ids),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "info-collector",
                        "version": "0.1.0",
                    },
                },
            }
        )
        if "error" in response:
            raise McpClientError(f"MCP initialize 失敗: {response['error']}")

        try:
            self._post(
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                },
                expect_response=False,
            )
        except McpClientError:
            # Some servers ignore HTTP notifications. The initialization result is enough.
            pass

        self._initialized = True

    def _post(self, payload: dict[str, Any], expect_response: bool = True) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
        req = request.Request(
            self.endpoint,
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                self._session_id = response.headers.get("mcp-session-id", self._session_id)
                raw = response.read().decode("utf-8").strip()
        except error.URLError as exc:
            raise McpClientError(f"無法連線到 MCP server: {exc}") from exc

        if not expect_response and not raw:
            return {}
        if not raw:
            raise McpClientError("MCP server 回傳空內容")

        parsed = _parse_json_response(raw)
        if not isinstance(parsed, dict):
            raise McpClientError(f"無法解析 MCP 回應: {raw}")
        return parsed


def _parse_json_response(raw: str) -> Any:
    stripped = raw.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)

    sse_payloads: list[str] = []
    for line in stripped.splitlines():
        if line.startswith("data:"):
            sse_payloads.append(line[5:].strip())

    for payload in reversed(sse_payloads):
        if not payload:
            continue
        return json.loads(payload)

    raise McpClientError(f"不支援的 MCP 回應格式: {raw}")


def _extract_tool_result(result: Any) -> Any:
    if isinstance(result, dict) and "content" in result:
        content = result["content"]
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "text":
                    return _try_json_loads(item.get("text", ""))
                if item.get("type") == "json":
                    return item.get("json")
        return result
    return result


def _try_json_loads(value: str) -> Any:
    value = value.strip()
    if not value:
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value
