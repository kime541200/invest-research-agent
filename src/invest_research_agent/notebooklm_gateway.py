from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invest_research_agent.mcp_client import McpHttpClient


class NotebookLMGatewayError(RuntimeError):
    def __init__(self, message: str, *, category: str) -> None:
        super().__init__(message)
        self.category = category


@dataclass(frozen=True)
class NotebookLMNotebook:
    id: str
    title: str


@dataclass(frozen=True)
class NotebookLMSource:
    id: str
    title: str
    url: str
    status: str


@dataclass(frozen=True)
class NotebookLMCitation:
    citation_number: int
    source_id: str
    title: str
    url: str
    cited_text: str


@dataclass(frozen=True)
class NotebookLMAnswer:
    answer: str
    conversation_id: str | None
    citations: list[NotebookLMCitation]


class NotebookLMMcpGateway:
    def __init__(self, client: McpHttpClient) -> None:
        self.client = client

    def list_notebooks(self) -> list[NotebookLMNotebook]:
        try:
            result = self.client.call_tool("list_notebooks")
        except Exception as exc:
            raise NotebookLMGatewayError(str(exc), category="server") from exc
        if not isinstance(result, list):
            return []
        return [
            NotebookLMNotebook(
                id=str(item.get("id", "")).strip(),
                title=str(item.get("title", "")).strip(),
            )
            for item in result
            if isinstance(item, dict) and str(item.get("id", "")).strip()
        ]

    def create_notebook(self, title: str) -> NotebookLMNotebook:
        try:
            result = self.client.call_tool("create_notebook", {"title": title})
        except Exception as exc:
            raise NotebookLMGatewayError(str(exc), category="auth") from exc
        if not isinstance(result, dict):
            raise NotebookLMGatewayError("NotebookLM create_notebook 回傳格式不正確", category="auth")
        notebook_id = str(result.get("id", "")).strip()
        if not notebook_id:
            raise NotebookLMGatewayError("NotebookLM create_notebook 缺少 notebook id", category="auth")
        return NotebookLMNotebook(id=notebook_id, title=str(result.get("title", title)).strip())

    def list_sources(self, notebook_id: str) -> list[NotebookLMSource]:
        try:
            result = self.client.call_tool("list_sources", {"notebook_id": notebook_id})
        except Exception as exc:
            raise NotebookLMGatewayError(str(exc), category="ingestion") from exc
        if not isinstance(result, list):
            return []
        sources: list[NotebookLMSource] = []
        for item in result:
            if not isinstance(item, dict):
                continue
            source_id = str(item.get("id", "")).strip()
            if not source_id:
                continue
            try:
                status_payload = self.client.call_tool(
                    "get_source_status",
                    {"notebook_id": notebook_id, "source_id": source_id},
                )
            except Exception as exc:
                raise NotebookLMGatewayError(str(exc), category="ingestion") from exc
            if not isinstance(status_payload, dict):
                status_payload = {}
            sources.append(
                NotebookLMSource(
                    id=source_id,
                    title=str(item.get("title", status_payload.get("title", ""))).strip(),
                    url=str(status_payload.get("url", "")).strip(),
                    status=str(status_payload.get("status", item.get("status", ""))).strip(),
                )
            )
        return sources

    def add_youtube_source(self, notebook_id: str, youtube_url: str, wait: bool = True) -> NotebookLMSource:
        try:
            result = self.client.call_tool(
                "add_youtube_source",
                {
                    "notebook_id": notebook_id,
                    "youtube_url": youtube_url,
                    "wait": wait,
                },
            )
        except Exception as exc:
            raise NotebookLMGatewayError(str(exc), category="ingestion") from exc
        if not isinstance(result, dict):
            raise NotebookLMGatewayError("NotebookLM add_youtube_source 回傳格式不正確", category="ingestion")
        source_id = str(result.get("id", "")).strip()
        if not source_id:
            raise NotebookLMGatewayError("NotebookLM add_youtube_source 缺少 source id", category="ingestion")
        return NotebookLMSource(
            id=source_id,
            title=str(result.get("title", "")).strip(),
            url=str(result.get("url", youtube_url)).strip(),
            status=str(result.get("status", "")).strip(),
        )

    def ask_notebook(
        self,
        notebook_id: str,
        query: str,
        conversation_id: str | None = None,
    ) -> NotebookLMAnswer:
        payload: dict[str, Any] = {
            "notebook_id": notebook_id,
            "query": query,
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id
        try:
            result = self.client.call_tool("ask_notebook", payload)
        except Exception as exc:
            raise NotebookLMGatewayError(str(exc), category="ask") from exc
        if not isinstance(result, dict):
            raise NotebookLMGatewayError("NotebookLM ask_notebook 回傳格式不正確", category="ask")
        citations = [
            self._to_citation(item)
            for item in result.get("citations", []) or []
            if isinstance(item, dict)
        ]
        return NotebookLMAnswer(
            answer=str(result.get("answer", "")).strip(),
            conversation_id=_optional_str(result.get("conversation_id")),
            citations=citations,
        )

    def _to_citation(self, item: dict[str, Any]) -> NotebookLMCitation:
        source_id = str(item.get("source_id", "")).strip()
        title = str(item.get("title", "")).strip() or f"NotebookLM citation #{item.get('citation_number', '')}".strip()
        return NotebookLMCitation(
            citation_number=_to_int(item.get("citation_number")),
            source_id=source_id,
            title=title,
            url=str(item.get("url", "")).strip(),
            cited_text=str(item.get("cited_text", "")).strip(),
        )


def _optional_str(value: Any) -> str | None:
    normalized = str(value).strip() if value is not None else ""
    return normalized or None


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
