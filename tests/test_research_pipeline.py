from __future__ import annotations

import json
from pathlib import Path

import httpx

from invest_research_agent.analysis_artifacts import AnalysisArtifact
from invest_research_agent.external_research import RssResearchProvider
from invest_research_agent.research_pipeline import ResearchArtifactBuilder, ResearchNoteEnricher, write_enrichment_result
from invest_research_agent.research_models import ResearchNoteSections
from invest_research_agent.transcript_artifacts import TranscriptArtifactWriter
from invest_research_agent.models import ChannelConfig, TranscriptBundle, TranscriptSegment, VideoMetadata


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_research_enricher_uses_rss_provider_and_writes_sidecar(tmp_path: Path, monkeypatch) -> None:
    rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example Feed</title>
    <item>
      <title>AI 商業模式的最新趨勢</title>
      <link>https://example.com/ai-business</link>
      <description>討論 AI 公司怎麼賺錢與 SaaS 模式。</description>
      <pubDate>Tue, 08 Apr 2026 09:00:00 GMT</pubDate>
    </item>
    <item>
      <title>無關主題</title>
      <link>https://example.com/other</link>
      <description>這篇文章和 AI 商業模式無關。</description>
      <pubDate>Tue, 08 Apr 2026 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

    def _fake_get(url: str, timeout: float) -> _FakeResponse:
        del url, timeout
        return _FakeResponse(rss_xml)

    monkeypatch.setattr(httpx, "get", _fake_get)

    note_path = tmp_path / "note.md"
    note_path.write_text(
        """# AI 公司怎麼賺錢？

- **頻道：** inside6202
- **主題：** AI 商業模式
""",
        encoding="utf-8",
    )

    provider = RssResearchProvider(["https://example.com/feed.xml"])
    enricher = ResearchNoteEnricher(provider)

    result = enricher.enrich_note(note_path, limit=2)
    output_path = write_enrichment_result(result)

    assert result.note_title == "AI 公司怎麼賺錢？"
    assert "AI" in result.keywords
    assert len(result.evidence) == 2
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["note_title"] == "AI 公司怎麼賺錢？"
    assert payload["evidence"][0]["source"] == "Example Feed"


def test_research_artifact_builder_generates_from_analysis_and_transcript(tmp_path: Path) -> None:
    writer = TranscriptArtifactWriter()
    transcript_artifact = writer.write_artifact(
        topic="AI 商業模式",
        channel=ChannelConfig(name="inside6202", url="https://www.youtube.com/@inside6202"),
        video=VideoMetadata(
            channel_name="inside6202",
            channel_id="UC123",
            video_id="video123",
            title="AI 公司怎麼賺錢？",
            url="https://www.youtube.com/watch?v=video123",
            published_at="2026-04-10T08:00:00Z",
            description="影片討論 AI 公司收入模型。",
        ),
        transcript=TranscriptBundle(
            video_id="video123",
            language="zh-TW",
            source="native",
            merged_full_text="影片說明訂閱收入與服務收入的差異。",
            merged_transcript=[
                TranscriptSegment(text="影片說明訂閱收入與服務收入的差異。", start=0.0, duration=3.0, timestamp="00:00")
            ],
        ),
        output_root=tmp_path / "transcripts",
    )
    analysis_artifact = AnalysisArtifact(
        path=tmp_path / "analysis" / "sample.analysis.json",
        transcript_path=transcript_artifact.path,
        title="AI 公司怎麼賺錢？",
        channel="inside6202",
        topic="AI 商業模式",
        status="ready",
        summary=ResearchNoteSections(
            core_conclusion="AI 公司應優先建立可重複收入模式。",
            key_points=["訂閱收入提高可預測性。"],
            evidence_points=["00:00：影片直接比較訂閱與服務收入。"],
            limitations=["未比較不同產業差異。"],
            follow_up_questions=["哪些 retention 指標最重要？"],
        ),
    )
    note_path = tmp_path / "notes" / "sample.note.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text("# AI 公司怎麼賺錢？\n", encoding="utf-8")

    builder = ResearchArtifactBuilder()
    artifact = builder.build_from_paths(
        analysis_artifact=analysis_artifact,
        note_path=note_path,
        output_root=tmp_path / "research",
    )

    assert artifact.transcript_path == transcript_artifact.path
    assert artifact.analysis_path == analysis_artifact.path
    assert artifact.note_path == note_path
    assert artifact.claims[0].text == "訂閱收入提高可預測性。"
    assert artifact.overall_risks == ["未比較不同產業差異。"]
