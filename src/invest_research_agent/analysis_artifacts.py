from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path

from invest_research_agent.research_models import ResearchNoteSections
from invest_research_agent.transcript_artifacts import TranscriptArtifact


@dataclass(frozen=True)
class AnalysisArtifact:
    path: Path
    transcript_path: Path
    title: str
    channel: str
    topic: str
    status: str = "pending"
    agent: str = ""
    summary: ResearchNoteSections = field(default_factory=ResearchNoteSections)
    notes: str = ""


class AnalysisArtifactStore:
    def initialize_pending(
        self,
        transcript_artifact: TranscriptArtifact,
        output_root: Path | str,
    ) -> AnalysisArtifact:
        output_dir = Path(output_root) / transcript_artifact.published_date
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / transcript_artifact.path.name.replace(".transcript.md", ".analysis.json")
        return self.initialize_pending_at_path(transcript_artifact, path)

    def initialize_pending_at_path(
        self,
        transcript_artifact: TranscriptArtifact,
        path: Path | str,
    ) -> AnalysisArtifact:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        artifact = AnalysisArtifact(
            path=path,
            transcript_path=transcript_artifact.path,
            title=transcript_artifact.title,
            channel=transcript_artifact.channel,
            topic=transcript_artifact.topic,
            status="pending",
            agent="transcript-analyst",
            notes="等待 transcript-analyst 子 Agent 根據逐字稿完成分析。",
        )
        self.write(artifact)
        return artifact

    def write(self, artifact: AnalysisArtifact) -> Path:
        payload = asdict(artifact)
        payload["path"] = str(artifact.path)
        payload["transcript_path"] = str(artifact.transcript_path)
        artifact.path.parent.mkdir(parents=True, exist_ok=True)
        artifact.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return artifact.path

    def read(self, path: Path | str) -> AnalysisArtifact:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        summary = ResearchNoteSections(**payload.get("summary", {}))
        return AnalysisArtifact(
            path=Path(payload["path"]),
            transcript_path=Path(payload["transcript_path"]),
            title=payload.get("title", ""),
            channel=payload.get("channel", ""),
            topic=payload.get("topic", ""),
            status=payload.get("status", "pending"),
            agent=payload.get("agent", ""),
            summary=summary,
            notes=payload.get("notes", ""),
        )


def build_unavailable_analysis_sections(analysis_artifact: AnalysisArtifact | None) -> ResearchNoteSections:
    message = "分析 artifact 尚未產出。請先使用 transcript-analyst 子 Agent 完成逐字稿分析。"
    if analysis_artifact is not None and analysis_artifact.notes:
        message = analysis_artifact.notes
    return ResearchNoteSections(
        core_conclusion=message,
        key_points=[],
        answered_questions=[],
        evidence_points=[],
        limitations=["分析結果尚未可用。"],
        follow_up_questions=["完成 analysis artifact 後再產出正式研究重點。"],
    )
