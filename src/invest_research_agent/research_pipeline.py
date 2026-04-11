from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from invest_research_agent.analysis_artifacts import AnalysisArtifact
from invest_research_agent.external_research import ExternalResearchProvider
from invest_research_agent.note_parser import extract_note_keywords, parse_markdown_note
from invest_research_agent.research_artifacts import ResearchArtifact, ResearchArtifactClaim, ResearchArtifactStore
from invest_research_agent.research_models import ResearchEnrichmentResult
from invest_research_agent.transcript_artifacts import read_transcript_artifact_for_analysis


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


class ResearchArtifactBuilder:
    def __init__(self, store: ResearchArtifactStore | None = None) -> None:
        self.store = store or ResearchArtifactStore()

    def build_from_paths(
        self,
        *,
        analysis_artifact: AnalysisArtifact,
        note_path: Path | str,
        output_root: Path | str,
    ) -> ResearchArtifact:
        transcript_artifact = read_transcript_artifact_for_analysis(analysis_artifact.transcript_path)
        return self.store.build_from_analysis(
            analysis_artifact=analysis_artifact,
            transcript_artifact=transcript_artifact,
            note_path=note_path,
            output_root=output_root,
        )


class ClaimEnrichmentBuilder:
    def __init__(self, provider: ExternalResearchProvider, store: ResearchArtifactStore | None = None) -> None:
        self.provider = provider
        self.store = store or ResearchArtifactStore()

    def enrich_artifact(self, artifact: ResearchArtifact, limit: int = 5) -> ResearchArtifact:
        claims = [self._enrich_claim(claim=claim, artifact=artifact, limit=limit) for claim in artifact.claims]
        enriched = ResearchArtifact(
            path=artifact.path,
            transcript_path=artifact.transcript_path,
            analysis_path=artifact.analysis_path,
            note_path=artifact.note_path,
            title=artifact.title,
            channel=artifact.channel,
            topic=artifact.topic,
            source_of_truth=artifact.source_of_truth,
            claims=claims,
            overall_risks=list(artifact.overall_risks),
            next_actions=list(artifact.next_actions),
        )
        self.store.write(enriched)
        return enriched

    def _enrich_claim(self, *, claim: ResearchArtifactClaim, artifact: ResearchArtifact, limit: int) -> ResearchArtifactClaim:
        keywords = claim.keywords or generate_claim_keywords(claim.text, artifact=artifact)
        evidence = self.provider.search(keywords, limit=limit)
        return ResearchArtifactClaim(
            text=claim.text,
            keywords=keywords,
            evidence_points=list(claim.evidence_points),
            limitations=list(claim.limitations),
            external_evidence=evidence,
        )


def generate_claim_keywords(claim_text: str, *, artifact: ResearchArtifact, max_keywords: int = 6) -> list[str]:
    candidates = [claim_text.strip(), artifact.topic.strip(), artifact.channel.strip(), artifact.title.strip()]
    seen: set[str] = set()
    keywords: list[str] = []
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


def write_enrichment_result(
    result: ResearchEnrichmentResult,
    output_path: Path | str | None = None,
) -> Path:
    destination = Path(output_path) if output_path is not None else result.note_path.with_suffix(".research.json")
    payload = asdict(result)
    payload["note_path"] = str(result.note_path)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination
