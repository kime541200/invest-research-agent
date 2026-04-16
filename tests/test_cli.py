from __future__ import annotations

from datetime import date
import json
import sys
from pathlib import Path

from invest_research_agent import cli
from invest_research_agent.analysis_artifacts import AnalysisArtifact, AnalysisArtifactStore
from invest_research_agent.research_answers import ResearchAnswerStore
from invest_research_agent.research_artifacts import ResearchArtifactStore
from invest_research_agent.research_models import ResearchAnswer, ResearchAnswerPoint, ResearchEnrichmentResult, ResearchEvidence
from invest_research_agent.research_models import ResearchNoteSections
from invest_research_agent.stt import SttHealthStatus
from invest_research_agent.transcript_artifacts import TranscriptArtifactWriter
from invest_research_agent.models import ChannelConfig, TranscriptBundle, TranscriptSegment, VideoMetadata


def test_cli_check_stt_does_not_build_orchestrator(monkeypatch, capsys) -> None:
    def _fail_build(args):  # noqa: ANN001, ANN202
        raise AssertionError("_build_orchestrator should not be called")

    monkeypatch.setattr(cli, "_build_orchestrator", _fail_build)
    monkeypatch.setattr(cli, "load_stt_settings", lambda project_root=None: None)
    monkeypatch.setattr(
        cli,
        "check_stt_provider",
        lambda settings: SttHealthStatus(ok=False, provider="", message="STT 尚未設定。"),
    )
    monkeypatch.setattr(sys, "argv", ["invest-research-agent", "check-stt"])

    cli.main()

    output = capsys.readouterr().out
    assert "STT provider: (未設定)" in output
    assert "狀態: not_ready" in output


def test_cli_enrich_notes_outputs_json_without_orchestrator(tmp_path: Path, monkeypatch, capsys) -> None:
    note_path = tmp_path / "sample.md"
    note_path.write_text(
        """# AI 公司怎麼賺錢？

- **頻道：** inside6202
- **主題：** AI 商業模式
""",
        encoding="utf-8",
    )

    def _fail_build(args):  # noqa: ANN001, ANN202
        raise AssertionError("_build_orchestrator should not be called")

    class _FakeProvider:
        def __init__(self, feed_urls):  # noqa: ANN001
            self.feed_urls = feed_urls

    class _FakeEnricher:
        def __init__(self, provider) -> None:  # noqa: ANN001
            self.provider = provider

        def enrich_notes(self, note_paths, keywords=None, limit=5):  # noqa: ANN001
            del keywords, limit
            return [
                ResearchEnrichmentResult(
                    note_path=note_paths[0],
                    note_title="AI 公司怎麼賺錢？",
                    keywords=["AI", "商業模式"],
                    evidence=[
                        ResearchEvidence(
                            title="AI 商業模式的最新趨勢",
                            source="Example Feed",
                            url="https://example.com/ai-business",
                            score=4.0,
                        )
                    ],
                )
            ]

    monkeypatch.setattr(cli, "_build_orchestrator", _fail_build)
    monkeypatch.setattr(cli, "RssResearchProvider", _FakeProvider)
    monkeypatch.setattr(cli, "ResearchNoteEnricher", _FakeEnricher)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "invest-research-agent",
            "--notes-dir",
            str(tmp_path),
            "enrich-notes",
            "--rss-feed",
            "https://example.com/feed.xml",
            "--json",
            "--note-paths",
            str(note_path),
        ],
    )

    cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["note_title"] == "AI 公司怎麼賺錢？"
    assert payload[0]["evidence"][0]["source"] == "Example Feed"


def test_cli_prepare_analysis_initializes_pending_artifact(tmp_path: Path, monkeypatch, capsys) -> None:
    transcript_artifact = TranscriptArtifactWriter().write_artifact(
        topic="AI 商業模式",
        channel=ChannelConfig(name="inside6202", url="https://www.youtube.com/@inside6202"),
        video=VideoMetadata(
            channel_name="inside6202",
            channel_id="UC123",
            video_id="video123",
            title="AI 公司怎麼賺錢？",
            url="https://www.youtube.com/watch?v=video123",
            published_at="2026-04-06T08:00:00Z",
        ),
        transcript=TranscriptBundle(
            video_id="video123",
            language="zh-TW",
            merged_full_text="今天先談 AI 公司常見的營收模式。",
            merged_transcript=[
                TranscriptSegment(text="今天先談 AI 公司常見的營收模式。", start=0.0, duration=3.0, timestamp="00:00")
            ],
        ),
        output_root=tmp_path / "transcripts",
        output_date=date(2026, 4, 7),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "invest-research-agent",
            "--analysis-dir",
            str(tmp_path / "analysis"),
            "prepare-analysis",
            "--transcript-path",
            str(transcript_artifact.path),
        ],
    )

    cli.main()

    output = capsys.readouterr().out
    assert "已初始化 analysis artifact:" in output
    created = next((tmp_path / "analysis").glob("**/*.analysis.json"))
    payload = json.loads(created.read_text(encoding="utf-8"))
    assert payload["status"] == "pending"
    assert created == tmp_path / "analysis" / "2026-04-07" / "AI_商業模式" / "inside6202_AI_公司怎麼賺錢？.analysis.json"


def test_cli_render_note_uses_ready_analysis_artifact(tmp_path: Path, monkeypatch, capsys) -> None:
    transcript_artifact = TranscriptArtifactWriter().write_artifact(
        topic="區塊鏈資訊",
        channel=ChannelConfig(name="brainbrocrypto", url="https://www.youtube.com/@brainbrocrypto"),
        video=VideoMetadata(
            channel_name="brainbrocrypto",
            channel_id="UC999",
            video_id="video999",
            title="加密貨幣正在超車傳統金融體系",
            url="https://www.youtube.com/watch?v=video999",
            published_at="2026-04-08T08:00:00Z",
        ),
        transcript=TranscriptBundle(
            video_id="video999",
            language="zh",
            source="stt",
            merged_full_text="這是 STT fallback 逐字稿。",
            merged_transcript=[
                TranscriptSegment(text="這是 STT fallback 逐字稿。", start=0.0, duration=2.0, timestamp="00:00")
            ],
        ),
        output_root=tmp_path / "transcripts",
        output_date=date(2026, 4, 7),
    )
    analysis_path = tmp_path / "analysis" / "ready.analysis.json"
    AnalysisArtifactStore().write(
        AnalysisArtifact(
            path=analysis_path,
            transcript_path=transcript_artifact.path,
            title="加密貨幣正在超車傳統金融體系",
            channel="brainbrocrypto",
            topic="區塊鏈資訊",
            status="ready",
            summary=ResearchNoteSections(
                core_conclusion="加密資產正加速與傳統金融接軌。",
                key_points=["監管推進帶動機構接入。"],
                answered_questions=["加密貨幣是否正在超車傳統金融體系？"],
                evidence_points=["00:00：監管進展"],
                limitations=["仍需觀察市場接受度。"],
                follow_up_questions=["台灣法規進度是否跟上？"],
            ),
        )
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "invest-research-agent",
            "--notes-dir",
            str(tmp_path / "notes"),
            "render-note",
            "--transcript-path",
            str(transcript_artifact.path),
            "--analysis-path",
            str(analysis_path),
        ],
    )

    cli.main()

    output = capsys.readouterr().out
    assert "已產出筆記:" in output
    note_path = next((tmp_path / "notes").glob("**/*.md"))
    assert note_path == tmp_path / "notes" / "2026-04-07" / "區塊鏈資訊" / "brainbrocrypto_加密貨幣正在超車傳統金融體系.md"
    content = note_path.read_text(encoding="utf-8")
    assert "加密資產正加速與傳統金融接軌。" in content


def test_cli_synthesize_answer_outputs_rendered_answer(tmp_path: Path, monkeypatch, capsys) -> None:
    artifact = ResearchArtifactStore().build_from_analysis_at_path(
        analysis_artifact=AnalysisArtifact(
            path=tmp_path / "analysis" / "sample.analysis.json",
            transcript_path=tmp_path / "sample.transcript.md",
            title="股癌 EP652",
            channel="股癌 Gooaye",
            topic="股癌",
            status="ready",
            summary=ResearchNoteSections(
                key_points=["CPU 與 ASIC 成為新的市場焦點。"],
                evidence_points=["00:10：節目直接提到 CPU 與 ASIC。"],
                limitations=["尚未完成具體台股映射。"],
            ),
        ),
        transcript_artifact=TranscriptArtifactWriter().write_artifact(
            topic="股癌",
            channel=ChannelConfig(name="股癌 Gooaye", url="https://www.youtube.com/@Gooaye"),
            video=VideoMetadata(
                channel_name="股癌 Gooaye",
                channel_id="UC111",
                video_id="video111",
                title="股癌 EP652",
                url="https://www.youtube.com/watch?v=video111",
                published_at="2026-04-11T08:00:00Z",
            ),
            transcript=TranscriptBundle(
                video_id="video111",
                language="zh-TW",
                merged_full_text="CPU 與 ASIC 成為新的市場焦點。",
                merged_transcript=[TranscriptSegment(text="CPU 與 ASIC 成為新的市場焦點。", start=0.0, duration=1.0, timestamp="00:10")],
            ),
            output_root=tmp_path / "transcripts-answer",
            output_date=date(2026, 4, 11),
        ),
        note_path=tmp_path / "sample.note.md",
        path=tmp_path / "research" / "sample.research.json",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "invest-research-agent",
            "--analysis-dir",
            str(tmp_path / "analysis-output"),
            "synthesize-answer",
            "--research-artifact-path",
            str(artifact.path),
            "--question",
            "最新一集股癌有提到哪些熱門族群？",
        ],
    )

    cli.main()

    output = capsys.readouterr().out
    assert "問題：最新一集股癌有提到哪些熱門族群？" in output
    assert "結論：（無明確結論）" in output
    assert "research answer:" in output
    assert "由它負責 relevant claim selection" in output


def test_cli_analyze_prediction_market_outputs_json(tmp_path: Path, monkeypatch, capsys) -> None:
    answer = ResearchAnswer(
        path=tmp_path / "sample.answer.json",
        question="下一個值得追蹤的 prediction market 題目是什麼？",
        research_artifact_path=tmp_path / "sample.research.json",
        title="sample",
        channel="sample-channel",
        topic="sample-topic",
        summary_answer="The main signal is a rate cut probability repricing.",
        direct_mentions=[ResearchAnswerPoint(claim="Fed rate cut odds are being repriced.")],
    )
    ResearchAnswerStore().write(answer)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "invest-research-agent",
            "analyze-prediction-market",
            "--research-answer-path",
            str(answer.path),
            "--json",
        ],
    )

    cli.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["route"] == "prediction_market"
    assert payload["status"] == "ready"
    assert payload["candidates"][0]["framing"] == "Will the next Fed decision be a rate cut?"


def test_cli_analyze_prediction_market_renders_text_output(tmp_path: Path, monkeypatch, capsys) -> None:
    answer = ResearchAnswer(
        path=tmp_path / "sample.answer.json",
        question="下一個值得追蹤的 prediction market 題目是什麼？",
        research_artifact_path=tmp_path / "sample.research.json",
        title="sample",
        channel="sample-channel",
        topic="sample-topic",
        summary_answer="The main signal is a rate cut probability repricing.",
        direct_mentions=[ResearchAnswerPoint(claim="Fed rate cut odds are being repriced.")],
    )
    ResearchAnswerStore().write(answer)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "invest-research-agent",
            "analyze-prediction-market",
            "--research-answer-path",
            str(answer.path),
        ],
    )

    cli.main()

    output = capsys.readouterr().out
    assert "Route: prediction_market" in output
    assert "Candidates:" in output
    assert "Search queries:" in output
