from __future__ import annotations

from pathlib import Path

from invest_research_agent.analysis_artifacts import AnalysisArtifact
from invest_research_agent.research_artifacts import (
    ResearchArtifact,
    ResearchArtifactClaim,
    ResearchArtifactStore,
)
from invest_research_agent.research_models import ResearchNoteSections
from invest_research_agent.transcript_artifacts import TranscriptArtifact
from invest_research_agent.models import TranscriptSegment


def test_research_artifact_store_roundtrip_preserves_upstream_references(tmp_path: Path) -> None:
    store = ResearchArtifactStore()
    artifact = ResearchArtifact(
        path=tmp_path / "sample.research.json",
        transcript_path=tmp_path / "sample.transcript.md",
        analysis_path=tmp_path / "sample.analysis.json",
        note_path=tmp_path / "sample.note.md",
        title="Sample Title",
        channel="sample-channel",
        topic="sample-topic",
        claims=[
            ResearchArtifactClaim(
                text="AI 公司更適合可重複收入模式。",
                evidence_points=["00:42：影片直接比較一次性專案與訂閱收入。"],
                limitations=["未涵蓋市場逆風時期。"],
            )
        ],
        overall_risks=["影片只聚焦單一商業模式。"],
        next_actions=["補充查驗 SaaS retention 指標。"],
    )

    store.write(artifact)
    loaded = store.read(artifact.path)

    assert loaded.transcript_path == artifact.transcript_path
    assert loaded.analysis_path == artifact.analysis_path
    assert loaded.note_path == artifact.note_path
    assert loaded.source_of_truth == "analysis_artifact"
    assert loaded.claims[0].text == "AI 公司更適合可重複收入模式。"
    assert loaded.overall_risks == ["影片只聚焦單一商業模式。"]


def test_research_artifact_store_builds_from_analysis_without_duplication(tmp_path: Path) -> None:
    store = ResearchArtifactStore()
    analysis = AnalysisArtifact(
        path=tmp_path / "sample.analysis.json",
        transcript_path=tmp_path / "sample.transcript.md",
        title="AI 公司怎麼賺錢？",
        channel="inside6202",
        topic="AI 商業模式",
        status="ready",
        summary=ResearchNoteSections(
            core_conclusion="AI 公司若要建立穩定收入，應優先追求可重複收入模型。",
            key_points=["訂閱收入提高可預測性。", "服務收入更依賴交付能力。"],
            evidence_points=["00:42：影片直接比較一次性專案與訂閱收入。"],
            limitations=["未比較不同產業別的差異。"],
            follow_up_questions=["哪些 retention 指標最能驗證收入品質？"],
        ),
    )
    transcript = TranscriptArtifact(
        path=tmp_path / "sample.transcript.md",
        title="AI 公司怎麼賺錢？",
        channel="inside6202",
        video_id="video123",
        video_url="https://www.youtube.com/watch?v=video123",
        collected_date="2026-04-11",
        published_date="2026-04-10",
        topic="AI 商業模式",
        transcript_status="可用",
        transcript_source="原生字幕",
        transcript_language="zh-TW",
        description="影片討論 AI 公司收入模型。",
        full_text="完整逐字稿",
        segments=[TranscriptSegment(text="完整逐字稿", start=0.0, duration=1.0, timestamp="00:00")],
    )

    artifact = store.build_from_analysis(
        analysis_artifact=analysis,
        transcript_artifact=transcript,
        note_path=tmp_path / "sample.note.md",
        output_root=tmp_path,
    )

    assert artifact.transcript_path == transcript.path
    assert artifact.analysis_path == analysis.path
    assert artifact.note_path == tmp_path / "sample.note.md"
    assert [claim.text for claim in artifact.claims] == ["訂閱收入提高可預測性。", "服務收入更依賴交付能力。"]
    assert artifact.overall_risks == ["未比較不同產業別的差異。"]
    assert artifact.next_actions == ["哪些 retention 指標最能驗證收入品質？"]
