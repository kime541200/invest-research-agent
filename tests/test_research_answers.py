from __future__ import annotations

from pathlib import Path

from invest_research_agent.research_answers import ResearchAnswerBuilder, ResearchAnswerStore, render_research_answer
from invest_research_agent.research_artifacts import ResearchArtifact, ResearchArtifactClaim
from invest_research_agent.research_models import ResearchEvidence


def test_research_answer_store_roundtrip(tmp_path: Path) -> None:
    artifact = ResearchArtifact(
        path=tmp_path / "sample.research.json",
        transcript_path=tmp_path / "sample.transcript.md",
        analysis_path=tmp_path / "sample.analysis.json",
        note_path=tmp_path / "sample.note.md",
        title="股癌 EP652",
        channel="股癌 Gooaye",
        topic="股癌",
        claims=[
            ResearchArtifactClaim(
                text="CPU 與 ASIC 成為新的市場焦點。",
                evidence_points=["00:10：節目直接提到 CPU 與 ASIC。"],
                external_evidence=[
                    ResearchEvidence(
                        title="CPU trend",
                        source="Example Feed",
                    )
                ],
            )
        ],
    )
    answer = ResearchAnswerBuilder().build_stub(
        question="最新一集股癌有提到哪些熱門族群？",
        artifact=artifact,
        output_path=tmp_path / "sample.answer.json",
    )
    store = ResearchAnswerStore()
    store.write(answer)

    loaded = store.read(answer.path)

    assert loaded.question == "最新一集股癌有提到哪些熱門族群？"
    assert loaded.direct_mentions == []
    assert loaded.inferred_points == []
    assert loaded.notes == "等待 research-answer-synthesizer 根據使用者問題完成主要 synthesis judgment。"


def test_render_research_answer_exposes_sections(tmp_path: Path) -> None:
    artifact = ResearchArtifact(
        path=tmp_path / "sample.research.json",
        transcript_path=tmp_path / "sample.transcript.md",
        analysis_path=tmp_path / "sample.analysis.json",
        note_path=tmp_path / "sample.note.md",
        title="股癌 EP652",
        channel="股癌 Gooaye",
        topic="股癌",
        claims=[
            ResearchArtifactClaim(
                text="CPU 與 ASIC 成為新的市場焦點。",
                evidence_points=["00:10：節目直接提到 CPU 與 ASIC。"],
            )
        ],
    )
    answer = ResearchAnswerBuilder().build_stub(
        question="最新一集股癌有提到哪些熱門族群？",
        artifact=artifact,
        output_path=tmp_path / "sample.answer.json",
    )

    rendered = render_research_answer(answer)

    assert "問題：最新一集股癌有提到哪些熱門族群？" in rendered
    assert "結論：（無明確結論）" in rendered
    assert "來源：" in rendered
    assert "備註：等待 research-answer-synthesizer 根據使用者問題完成主要 synthesis judgment。" in rendered
