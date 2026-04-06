from __future__ import annotations

from pathlib import Path

from info_collector.models import ChannelConfig, TranscriptBundle, TranscriptSegment, VideoMetadata
from info_collector.note_generator import MarkdownNoteGenerator, NoteContext


def test_note_generator_writes_markdown_note(tmp_path: Path) -> None:
    generator = MarkdownNoteGenerator()
    context = NoteContext(
        topic="AI 商業模式",
        channel=ChannelConfig(
            name="inside6202",
            url="https://www.youtube.com/@inside6202",
            tags=["科技", "AI"],
        ),
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
            full_text="今天先談 AI 公司常見的營收模式。 接著會比較訂閱制與服務制的差異。 最後整理投資人應該追蹤的指標。",
            merged_full_text="今天先談 AI 公司常見的營收模式，接著會比較訂閱制與服務制的差異。\n\n最後整理投資人應該追蹤的指標。",
            transcript=[
                TranscriptSegment(text="今天先談 AI 公司常見的營收模式。", start=0.0, duration=3.0, timestamp="0:00"),
                TranscriptSegment(text="接著會比較訂閱制與服務制的差異。", start=30.0, duration=4.0, timestamp="0:30"),
                TranscriptSegment(text="最後整理投資人應該追蹤的指標。", start=120.0, duration=5.0, timestamp="2:00"),
            ],
            merged_transcript=[
                TranscriptSegment(
                    text="今天先談 AI 公司常見的營收模式，接著會比較訂閱制與服務制的差異。",
                    start=0.0,
                    duration=34.0,
                    timestamp="0:00",
                ),
                TranscriptSegment(
                    text="最後整理投資人應該追蹤的指標。",
                    start=120.0,
                    duration=5.0,
                    timestamp="2:00",
                ),
            ],
        ),
    )

    note = generator.write_note(context, output_root=tmp_path)

    assert note.path.exists()
    content = note.path.read_text(encoding="utf-8")
    assert "# AI 公司怎麼賺錢？" in content
    assert "## 📝 核心總結" in content
    assert "## 📚 逐字稿摘錄" in content
    assert "重點聚焦在：今天先談 AI 公司常見的營收模式，接著會比較訂閱制與服務制的差異。 最後整理投資人應該追蹤的指標。" in content
    assert "今天先談 AI 公司常見的營收模式，接著會比較訂閱制與服務制的差異。" in content
    assert "**0:00**" in content
    assert "**2:00**" in content
