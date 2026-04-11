from __future__ import annotations

from pathlib import Path

from invest_research_agent.analysis_artifacts import (
    AnalysisArtifact,
    AnalysisArtifactStore,
    build_unavailable_analysis_sections,
)
from invest_research_agent.research_models import ResearchNoteSections


def test_analysis_artifact_store_roundtrip_preserves_source_of_truth(tmp_path: Path) -> None:
    store = AnalysisArtifactStore()
    artifact = AnalysisArtifact(
        path=tmp_path / "sample.analysis.json",
        transcript_path=tmp_path / "sample.transcript.md",
        title="Sample Title",
        channel="sample-channel",
        topic="sample-topic",
        status="ready",
        agent="transcript-analyst",
        source_of_truth="transcript_artifact",
        summary=ResearchNoteSections(
            core_conclusion="影片主張 AI 公司的商業模式應以可重複收入為核心。",
            key_points=["訂閱收入提升可預測性。"],
            answered_questions=["AI 公司如何建立穩定收入？"],
            evidence_points=["00:42：影片直接比較一次性專案與訂閱收入。"],
            limitations=["內容未涵蓋不同市場週期下的變化。"],
            follow_up_questions=["哪些指標最能驗證收入品質？"],
        ),
        notes="analysis artifact 僅代表 transcript-derived analysis，尚非外部驗證結論。",
    )

    store.write(artifact)
    loaded = store.read(artifact.path)

    assert loaded.path == artifact.path
    assert loaded.transcript_path == artifact.transcript_path
    assert loaded.source_of_truth == "transcript_artifact"
    assert loaded.summary.core_conclusion == "影片主張 AI 公司的商業模式應以可重複收入為核心。"
    assert loaded.notes == "analysis artifact 僅代表 transcript-derived analysis，尚非外部驗證結論。"


def test_build_unavailable_analysis_sections_surfaces_non_final_research_warning() -> None:
    artifact = AnalysisArtifact(
        path=Path("analysis.json"),
        transcript_path=Path("transcript.md"),
        title="Title",
        channel="channel",
        topic="topic",
        status="pending",
        notes="等待 transcript-analyst 子 Agent 根據逐字稿完成分析；analysis artifact 僅代表 transcript-derived analysis，尚非外部驗證結論。",
    )

    sections = build_unavailable_analysis_sections(artifact)

    assert "尚非外部驗證結論" in sections.core_conclusion
    assert sections.key_points == []
    assert sections.evidence_points == []
    assert sections.limitations == ["分析結果尚未可用，當前 note 不應被視為已完成的研究結論。"]
