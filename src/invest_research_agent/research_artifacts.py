from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path

from invest_research_agent.analysis_artifacts import AnalysisArtifact
from invest_research_agent.research_models import ResearchEvidence, ResearchNoteSections
from invest_research_agent.transcript_artifacts import TranscriptArtifact


@dataclass(frozen=True)
class ResearchArtifactClaim:
    text: str
    keywords: list[str] = field(default_factory=list)
    evidence_points: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    external_evidence: list[ResearchEvidence] = field(default_factory=list)


@dataclass(frozen=True)
class ResearchArtifact:
    path: Path
    transcript_path: Path
    analysis_path: Path
    note_path: Path
    title: str
    channel: str
    topic: str
    source_of_truth: str = "analysis_artifact"
    claims: list[ResearchArtifactClaim] = field(default_factory=list)
    overall_risks: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)


class ResearchArtifactStore:
    def build_from_analysis(
        self,
        *,
        analysis_artifact: AnalysisArtifact,
        transcript_artifact: TranscriptArtifact,
        note_path: Path | str,
        output_root: Path | str,
    ) -> ResearchArtifact:
        output_dir = Path(output_root) / transcript_artifact.collected_date / _sanitize_path_segment(transcript_artifact.topic)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / transcript_artifact.path.name.replace(".transcript.md", ".research.json")
        return self.build_from_analysis_at_path(
            analysis_artifact=analysis_artifact,
            transcript_artifact=transcript_artifact,
            note_path=note_path,
            path=path,
        )

    def build_from_analysis_at_path(
        self,
        *,
        analysis_artifact: AnalysisArtifact,
        transcript_artifact: TranscriptArtifact,
        note_path: Path | str,
        path: Path | str,
    ) -> ResearchArtifact:
        note_path = Path(note_path)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        summary: ResearchNoteSections = analysis_artifact.summary
        artifact = ResearchArtifact(
            path=path,
            transcript_path=transcript_artifact.path,
            analysis_path=analysis_artifact.path,
            note_path=note_path,
            title=analysis_artifact.title,
            channel=analysis_artifact.channel,
            topic=analysis_artifact.topic,
            source_of_truth="analysis_artifact",
            claims=[
                ResearchArtifactClaim(
                    text=claim,
                    evidence_points=list(summary.evidence_points),
                    limitations=list(summary.limitations),
                )
                for claim in summary.key_points
            ],
            overall_risks=list(summary.limitations),
            next_actions=list(summary.follow_up_questions),
        )
        self.write(artifact)
        return artifact

    def write(self, artifact: ResearchArtifact) -> Path:
        payload = asdict(artifact)
        payload["path"] = str(artifact.path)
        payload["transcript_path"] = str(artifact.transcript_path)
        payload["analysis_path"] = str(artifact.analysis_path)
        payload["note_path"] = str(artifact.note_path)
        artifact.path.parent.mkdir(parents=True, exist_ok=True)
        artifact.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return artifact.path

    def read(self, path: Path | str) -> ResearchArtifact:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        claims = [
            ResearchArtifactClaim(
                text=item.get("text", ""),
                keywords=item.get("keywords", []),
                evidence_points=item.get("evidence_points", []),
                limitations=item.get("limitations", []),
                external_evidence=[ResearchEvidence(**evidence) for evidence in item.get("external_evidence", [])],
            )
            for item in payload.get("claims", [])
        ]
        return ResearchArtifact(
            path=Path(payload["path"]),
            transcript_path=Path(payload["transcript_path"]),
            analysis_path=Path(payload["analysis_path"]),
            note_path=Path(payload["note_path"]),
            title=payload.get("title", ""),
            channel=payload.get("channel", ""),
            topic=payload.get("topic", ""),
            source_of_truth=payload.get("source_of_truth", "analysis_artifact"),
            claims=claims,
            overall_risks=payload.get("overall_risks", []),
            next_actions=payload.get("next_actions", []),
        )


def _sanitize_path_segment(value: str) -> str:
    sanitized = "".join("_" if char in '\\/:*?\"<>|' else char for char in value)
    sanitized = "_".join(sanitized.split()).strip("._")
    return sanitized or "untitled-topic"
