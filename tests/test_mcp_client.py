from __future__ import annotations

import json
from urllib import request

from invest_research_agent.mcp_client import McpHttpClient


class _FakeResponse:
    def __init__(self, payload: dict, session_id: str | None = None) -> None:
        self._payload = payload
        self.headers = {"mcp-session-id": session_id} if session_id else {}

    def read(self) -> bytes:
        body = f"event: message\ndata: {json.dumps(self._payload)}\n\n"
        return body.encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None


def test_mcp_client_reuses_session_header(monkeypatch) -> None:
    seen_headers: list[dict[str, str]] = []
    responses = iter(
        [
            _FakeResponse(
                {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05"}},
                session_id="session-123",
            ),
            _FakeResponse({}, session_id="session-123"),
            _FakeResponse(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps([{"id": {"channelId": "UC123"}}]),
                            }
                        ]
                    },
                },
                session_id="session-123",
            ),
        ]
    )

    def _fake_urlopen(req: request.Request, timeout: float):  # noqa: ANN202
        del timeout
        seen_headers.append(dict(req.header_items()))
        return next(responses)

    monkeypatch.setattr(request, "urlopen", _fake_urlopen)

    client = McpHttpClient("http://localhost:8088/mcp")
    result = client.call_tool("channels_searchChannels", {"query": "inside6202"})

    assert result == [{"id": {"channelId": "UC123"}}]
    assert any(header.get("Mcp-session-id") == "session-123" for header in seen_headers[1:])
