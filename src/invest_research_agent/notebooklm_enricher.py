from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from invest_research_agent.models import ChannelConfig, VideoMetadata
from invest_research_agent.note_parser import extract_note_keywords, parse_markdown_note
from invest_research_agent.notebooklm_gateway import NotebookLMAnswer, NotebookLMCitation, NotebookLMNotebook, NotebookLMSource, NotebookLMMcpGateway
from invest_research_agent.research_models import ResearchEnrichmentResult, ResearchEvidence, ResearchNoteSections


@dataclass(frozen=True)
class NotebookLMCollectedResearch:
    notebook_id: str
    source_id: str
    source_status: str
    answer: str
    conversation_id: str | None
    citations: list[NotebookLMCitation]
    evidence: list[ResearchEvidence]
    research_sections: ResearchNoteSections
    source_of_truth: str = "notebooklm"


class NotebookLMNoteEnricher:
    def __init__(self, gateway: NotebookLMMcpGateway) -> None:
        self.gateway = gateway

    def enrich_note(
        self,
        note_path: Path | str,
        keywords: list[str] | None = None,
        limit: int = 5,
        notebook_title: str | None = None,
    ) -> ResearchEnrichmentResult:
        parsed_note = parse_markdown_note(note_path)
        if not parsed_note.source_url:
            raise ValueError(f"note 缺少來源 URL: {parsed_note.path}")

        selected_keywords = keywords or extract_note_keywords(parsed_note)
        resolved_notebook = self._ensure_notebook(notebook_title or _default_notebook_title(parsed_note))
        sources = self.gateway.list_sources(resolved_notebook.id)
        matched_source = _find_matching_source(sources, parsed_note.source_url, parsed_note.title)
        if matched_source is None:
            matched_source = self.gateway.add_youtube_source(
                notebook_id=resolved_notebook.id,
                youtube_url=parsed_note.source_url,
                wait=True,
            )
            sources = [*sources, matched_source]

        answer = self.gateway.ask_notebook(
            notebook_id=resolved_notebook.id,
            query=_build_query(parsed_note.title, selected_keywords),
        )
        source_title_by_id = {source.id: source.title for source in sources if source.id}
        evidence = _citations_to_evidence(
            citations=answer.citations,
            source_title_by_id=source_title_by_id,
            primary_source_id=matched_source.id,
            primary_source_url=parsed_note.source_url,
            limit=limit,
        )
        return ResearchEnrichmentResult(
            note_path=parsed_note.path,
            note_title=parsed_note.title,
            keywords=selected_keywords,
            evidence=evidence,
            answer=answer.answer,
            conversation_id=answer.conversation_id,
            notebook_id=resolved_notebook.id,
            source_of_truth="notebooklm",
        )

    def enrich_notes(
        self,
        note_paths: list[Path],
        keywords: list[str] | None = None,
        limit: int = 5,
        notebook_title: str | None = None,
    ) -> list[ResearchEnrichmentResult]:
        return [
            self.enrich_note(
                note_path=note_path,
                keywords=keywords,
                limit=limit,
                notebook_title=notebook_title,
            )
            for note_path in note_paths
        ]

    def collect_video_research(
        self,
        *,
        topic: str,
        channel: ChannelConfig,
        video: VideoMetadata,
        keywords: list[str] | None = None,
        limit: int = 5,
        notebook_title: str | None = None,
    ) -> NotebookLMCollectedResearch:
        selected_keywords = keywords or _build_video_keywords(topic=topic, channel_name=channel.name, video_title=video.title)
        resolved_notebook = self._ensure_notebook(notebook_title or _default_video_notebook_title(topic, video.title))
        sources = self.gateway.list_sources(resolved_notebook.id)
        matched_source = _find_matching_source(sources, video.url, video.title)
        if matched_source is None:
            matched_source = self.gateway.add_youtube_source(
                notebook_id=resolved_notebook.id,
                youtube_url=video.url,
                wait=True,
            )
            sources = [*sources, matched_source]

        answer = self.gateway.ask_notebook(
            notebook_id=resolved_notebook.id,
            query=_build_query(video.title, selected_keywords),
        )
        source_title_by_id = {source.id: source.title for source in sources if source.id}
        evidence = _citations_to_evidence(
            citations=answer.citations,
            source_title_by_id=source_title_by_id,
            primary_source_id=matched_source.id,
            primary_source_url=video.url,
            limit=limit,
        )
        sections = _answer_to_research_sections(answer.answer, evidence)
        return NotebookLMCollectedResearch(
            notebook_id=resolved_notebook.id,
            source_id=matched_source.id,
            source_status=matched_source.status,
            answer=answer.answer,
            conversation_id=answer.conversation_id,
            citations=answer.citations,
            evidence=evidence,
            research_sections=sections,
        )

    def _ensure_notebook(self, title: str) -> NotebookLMNotebook:
        for notebook in self.gateway.list_notebooks():
            if notebook.title == title:
                return notebook
        return self.gateway.create_notebook(title)


def _default_notebook_title(parsed_note) -> str:  # noqa: ANN001
    scope = parsed_note.topic or parsed_note.title or "untitled"
    return f"invest-research-agent | {scope}"


def _default_video_notebook_title(topic: str, video_title: str) -> str:
    scope = topic or video_title or "untitled"
    return f"invest-research-agent | {scope}"


def _find_matching_source(sources: list[NotebookLMSource], source_url: str, note_title: str) -> NotebookLMSource | None:
    normalized_url = source_url.strip()
    normalized_title = note_title.strip().casefold()
    for source in sources:
        if normalized_url and source.url.strip() == normalized_url:
            return source
    for source in sources:
        if normalized_title and source.title.strip().casefold() == normalized_title:
            return source
    return None


def _build_query(note_title: str, keywords: list[str]) -> str:
    keyword_text = "、".join(keyword for keyword in keywords if keyword.strip())
    if keyword_text:
        return (
            f"請整理影片《{note_title}》中與以下主題最相關的重點：{keyword_text}。"
            "請盡量引用來源內容作為依據。"
        )
    return f"請整理影片《{note_title}》的重點，並盡量引用來源內容作為依據。"


def _build_video_keywords(*, topic: str, channel_name: str, video_title: str, max_keywords: int = 5) -> list[str]:
    candidates = [video_title.strip(), topic.strip(), channel_name.strip()]
    keywords: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate:
            continue
        normalized = candidate.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        keywords.append(candidate)
        if len(keywords) >= max_keywords:
            break
    return keywords


def _answer_to_research_sections(answer: str, evidence: list[ResearchEvidence]) -> ResearchNoteSections:
    key_points = [item.summary for item in evidence if item.summary][:5]
    evidence_points = [item.summary for item in evidence if item.summary][:5]
    conclusion = answer.strip() or (key_points[0] if key_points else "NotebookLM 未提供足夠摘要。")
    return ResearchNoteSections(
        core_conclusion=conclusion,
        key_points=key_points,
        answered_questions=["這支影片的核心重點是什麼？"] if conclusion else [],
        evidence_points=evidence_points,
        limitations=[] if evidence else ["NotebookLM 未提供 citation-backed evidence。"],
        follow_up_questions=[],
    )


def _citations_to_evidence(
    *,
    citations,
    source_title_by_id: dict[str, str],
    primary_source_id: str,
    primary_source_url: str,
    limit: int,
) -> list[ResearchEvidence]:
    evidence: list[ResearchEvidence] = []
    seen: set[tuple[str, str]] = set()
    score = float(limit)
    for citation in citations:
        title = source_title_by_id.get(citation.source_id) or citation.title or f"NotebookLM citation #{citation.citation_number}"
        url = primary_source_url if citation.source_id == primary_source_id else ""
        summary = citation.cited_text.strip()
        dedupe_key = (title.casefold(), summary.casefold())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        evidence.append(
            ResearchEvidence(
                title=title,
                source="NotebookLM",
                summary=summary,
                url=url,
                score=max(score, 0.0),
            )
        )
        score -= 1.0
        if len(evidence) >= limit:
            break
    return evidence
