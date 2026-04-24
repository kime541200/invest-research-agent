from __future__ import annotations

from pathlib import Path

import pytest

from invest_research_agent.notebooklm_enricher import NotebookLMNoteEnricher
from invest_research_agent.notebooklm_gateway import NotebookLMAnswer, NotebookLMCitation, NotebookLMNotebook, NotebookLMSource


class FakeNotebookLMGateway:
    def __init__(self, *, notebooks=None, sources=None, answer=None) -> None:  # noqa: ANN001
        self.notebooks = notebooks or []
        self.sources = sources or {}
        self.answer = answer or NotebookLMAnswer(answer="", conversation_id=None, citations=[])
        self.created_titles: list[str] = []
        self.added_sources: list[tuple[str, str, bool]] = []
        self.asked_queries: list[tuple[str, str]] = []

    def list_notebooks(self) -> list[NotebookLMNotebook]:
        return list(self.notebooks)

    def create_notebook(self, title: str) -> NotebookLMNotebook:
        self.created_titles.append(title)
        notebook = NotebookLMNotebook(id=f"nb-{len(self.created_titles)}", title=title)
        self.notebooks.append(notebook)
        self.sources.setdefault(notebook.id, [])
        return notebook

    def list_sources(self, notebook_id: str) -> list[NotebookLMSource]:
        return list(self.sources.get(notebook_id, []))

    def add_youtube_source(self, notebook_id: str, youtube_url: str, wait: bool = True) -> NotebookLMSource:
        self.added_sources.append((notebook_id, youtube_url, wait))
        source = NotebookLMSource(id=f"src-{len(self.added_sources)}", title="影片來源", url=youtube_url, status="ready")
        self.sources.setdefault(notebook_id, []).append(source)
        return source

    def ask_notebook(self, notebook_id: str, query: str, conversation_id: str | None = None) -> NotebookLMAnswer:
        del conversation_id
        self.asked_queries.append((notebook_id, query))
        return self.answer


def test_notebooklm_enricher_reuses_existing_notebook_and_source(tmp_path: Path) -> None:
    note_path = tmp_path / "sample.md"
    note_path.write_text(
        """# GPT-5.5 測試\n\n- **頻道：** inside6202\n- **主題：** AI 工具\n- **來源：** https://youtu.be/abc123\n""",
        encoding="utf-8",
    )
    gateway = FakeNotebookLMGateway(
        notebooks=[NotebookLMNotebook(id="nb-1", title="invest-research-agent | AI 工具")],
        sources={
            "nb-1": [NotebookLMSource(id="src-existing", title="GPT-5.5 測試", url="https://youtu.be/abc123", status="ready")]
        },
        answer=NotebookLMAnswer(
            answer="整理完成",
            conversation_id="conv-1",
            citations=[
                NotebookLMCitation(
                    citation_number=1,
                    source_id="src-existing",
                    title="",
                    url="",
                    cited_text="影片展示 GPT-5.5 的 computer use 能力。",
                )
            ],
        ),
    )

    result = NotebookLMNoteEnricher(gateway).enrich_note(note_path)

    assert gateway.created_titles == []
    assert gateway.added_sources == []
    assert result.evidence[0].source == "NotebookLM"
    assert result.evidence[0].url == "https://youtu.be/abc123"
    assert "computer use" in result.evidence[0].summary


def test_notebooklm_enricher_creates_notebook_and_adds_source(tmp_path: Path) -> None:
    note_path = tmp_path / "sample.md"
    note_path.write_text(
        """# AI 商業模式\n\n- **頻道：** inside6202\n- **主題：** AI 商業模式\n- **來源：** https://youtu.be/xyz789\n""",
        encoding="utf-8",
    )
    gateway = FakeNotebookLMGateway(
        answer=NotebookLMAnswer(
            answer="整理完成",
            conversation_id="conv-2",
            citations=[
                NotebookLMCitation(
                    citation_number=1,
                    source_id="src-1",
                    title="",
                    url="",
                    cited_text="影片提到 AI 公司的主要營收模式。",
                )
            ],
        )
    )

    result = NotebookLMNoteEnricher(gateway).enrich_note(note_path, notebook_title="Custom Notebook")

    assert gateway.created_titles == ["Custom Notebook"]
    assert gateway.added_sources == [("nb-1", "https://youtu.be/xyz789", True)]
    assert result.note_title == "AI 商業模式"
    assert result.evidence[0].title == "影片來源"


def test_notebooklm_enricher_requires_source_url(tmp_path: Path) -> None:
    note_path = tmp_path / "sample.md"
    note_path.write_text(
        """# AI 商業模式\n\n- **頻道：** inside6202\n- **主題：** AI 商業模式\n""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="note 缺少來源 URL"):
        NotebookLMNoteEnricher(FakeNotebookLMGateway()).enrich_note(note_path)
