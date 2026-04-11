from __future__ import annotations

import json
from pathlib import Path

import httpx

from invest_research_agent.analysis_artifacts import AnalysisArtifact
from invest_research_agent.external_research import ExternalResearchProvider, RssResearchProvider
from invest_research_agent.research_pipeline import (
    ClaimEnrichmentBuilder,
    ResearchArtifactBuilder,
    ResearchNoteEnricher,
    generate_claim_keywords,
    write_enrichment_result,
)
from invest_research_agent.research_models import ResearchEvidence, ResearchNoteSections
from invest_research_agent.transcript_artifacts import TranscriptArtifactWriter
from invest_research_agent.models import ChannelConfig, TranscriptBundle, TranscriptSegment, VideoMetadata


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class _FakeClaimProvider(ExternalResearchProvider):
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def search(self, keywords: list[str], limit: int = 5) -> list[ResearchEvidence]:
        self.calls.append(list(keywords))
        return [
            ResearchEvidence(
                title="Claim evidence",
                source="Example Feed",
                summary="Supports the claim.",
                url="https://example.com/claim-evidence",
                published_at="2026-04-11",
                score=4.0,
            )
        ][:limit]


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
    assert artifact.claims[0].keywords == []
    assert artifact.overall_risks == ["未比較不同產業差異。"]


def test_generate_claim_keywords_prefers_claim_then_artifact_metadata(tmp_path: Path) -> None:
    artifact = AnalysisArtifact(
        path=tmp_path / "sample.analysis.json",
        transcript_path=tmp_path / "sample.transcript.md",
        title="AI 公司怎麼賺錢？",
        channel="inside6202",
        topic="AI 商業模式",
        summary=ResearchNoteSections(),
    )
    research_artifact = ResearchArtifactBuilder().store.build_from_analysis_at_path(
        analysis_artifact=artifact,
        transcript_artifact=TranscriptArtifactWriter().write_artifact(
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
                merged_full_text="內容",
                merged_transcript=[TranscriptSegment(text="內容", start=0.0, duration=1.0, timestamp="00:00")],
            ),
            output_root=tmp_path / "transcripts-keywords",
        ),
        note_path=tmp_path / "sample.note.md",
        path=tmp_path / "sample.research.json",
    )

    keywords = generate_claim_keywords("訂閱收入提高可預測性。", artifact=research_artifact)

    assert keywords == ["訂閱收入提高可預測性。", "AI 商業模式", "inside6202", "AI 公司怎麼賺錢？"]


def test_claim_enrichment_builder_enriches_each_claim_from_claim_keywords(tmp_path: Path) -> None:
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
        output_root=tmp_path / "transcripts-enrichment",
    )
    analysis_artifact = AnalysisArtifact(
        path=tmp_path / "analysis" / "sample.analysis.json",
        transcript_path=transcript_artifact.path,
        title="AI 公司怎麼賺錢？",
        channel="inside6202",
        topic="AI 商業模式",
        status="ready",
        summary=ResearchNoteSections(
            key_points=["訂閱收入提高可預測性。"],
            evidence_points=["00:00：影片直接比較訂閱與服務收入。"],
            limitations=["未比較不同產業差異。"],
        ),
    )
    note_path = tmp_path / "notes" / "sample.note.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text("# AI 公司怎麼賺錢？\n", encoding="utf-8")

    artifact = ResearchArtifactBuilder().build_from_paths(
        analysis_artifact=analysis_artifact,
        note_path=note_path,
        output_root=tmp_path / "research-enrichment",
    )
    provider = _FakeClaimProvider()
    enriched = ClaimEnrichmentBuilder(provider).enrich_artifact(artifact, limit=1)

    assert provider.calls == [["訂閱收入提高可預測性。", "AI 商業模式", "inside6202", "AI 公司怎麼賺錢？"]]
    assert enriched.claims[0].keywords == ["訂閱收入提高可預測性。", "AI 商業模式", "inside6202", "AI 公司怎麼賺錢？"]
    assert enriched.claims[0].external_evidence[0].title == "Claim evidence"
