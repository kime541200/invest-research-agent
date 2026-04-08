from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from invest_research_agent.external_research import ExternalResearchProvider
from invest_research_agent.note_parser import extract_note_keywords, parse_markdown_note
from invest_research_agent.research_models import ResearchEnrichmentResult


class ResearchNoteEnricher:
    def __init__(self, provider: ExternalResearchProvider) -> None:
        self.provider = provider

    def enrich_note(
        self,
        note_path: Path | str,
        keywords: list[str] | None = None,
        limit: int = 5,
    ) -> ResearchEnrichmentResult:
        parsed_note = parse_markdown_note(note_path)
        selected_keywords = keywords or extract_note_keywords(parsed_note)
        evidence = self.provider.search(selected_keywords, limit=limit)
        return ResearchEnrichmentResult(
            note_path=parsed_note.path,
            note_title=parsed_note.title,
            keywords=selected_keywords,
            evidence=evidence,
        )

    def enrich_notes(
        self,
        note_paths: list[Path],
        keywords: list[str] | None = None,
        limit: int = 5,
    ) -> list[ResearchEnrichmentResult]:
        return [
            self.enrich_note(note_path, keywords=keywords, limit=limit)
            for note_path in note_paths
        ]


def write_enrichment_result(
    result: ResearchEnrichmentResult,
    output_path: Path | str | None = None,
) -> Path:
    destination = Path(output_path) if output_path is not None else result.note_path.with_suffix(".research.json")
    payload = asdict(result)
    payload["note_path"] = str(result.note_path)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination
