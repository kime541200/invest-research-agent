from __future__ import annotations

from pathlib import Path

from invest_research_agent.note_parser import extract_note_keywords, parse_markdown_note
from invest_research_agent.research_models import ParsedNote


def test_parse_markdown_note_reads_title_topic_and_channel(tmp_path: Path) -> None:
    note_path = tmp_path / "sample.md"
    note_path.write_text(
        """# AI 公司怎麼賺錢？

- **頻道：** inside6202
- **日期：** 2026-04-07
- **來源：** https://www.youtube.com/watch?v=video123
- **主題：** AI 商業模式
""",
        encoding="utf-8",
    )

    parsed = parse_markdown_note(note_path)

    assert parsed.title == "AI 公司怎麼賺錢？"
    assert parsed.topic == "AI 商業模式"
    assert parsed.channel == "inside6202"


def test_extract_note_keywords_uses_title_topic_and_channel() -> None:
    note = ParsedNote(
        path=Path("/tmp/virtual-note.md"),
        title="AI 公司怎麼賺錢？",
        topic="AI 商業模式",
        channel="inside6202",
    )

    keywords = extract_note_keywords(note, max_keywords=4)

    assert keywords == ["AI", "公司怎麼賺錢", "商業模式", "inside6202"]
