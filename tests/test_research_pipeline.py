from __future__ import annotations

import json
from pathlib import Path

import httpx

from invest_research_agent.external_research import RssResearchProvider
from invest_research_agent.research_pipeline import ResearchNoteEnricher, write_enrichment_result


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
