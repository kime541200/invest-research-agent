from __future__ import annotations

from datetime import date
from pathlib import Path

from invest_research_agent.analysis_artifacts import AnalysisArtifact
from invest_research_agent.models import ChannelConfig, TranscriptBundle, TranscriptSegment, VideoMetadata
from invest_research_agent.note_generator import MarkdownNoteGenerator, NoteContext
from invest_research_agent.research_models import ResearchNoteSections


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
        analysis_artifact=AnalysisArtifact(
            path=tmp_path / "analysis.json",
            transcript_path=tmp_path / "transcript.md",
            title="AI 公司怎麼賺錢？",
            channel="inside6202",
            topic="AI 商業模式",
            status="ready",
            summary=ResearchNoteSections(
                core_conclusion="AI 公司常見營收模式可分為訂閱制、服務制與混合型模式。",
                key_points=["訂閱制可提高收入可預測性。", "服務制更依賴顧問與導入能力。"],
                answered_questions=["AI 公司怎麼賺錢？"],
                evidence_points=["00:00：先談營收模式", "02:00：整理投資人應追蹤的指標"],
                limitations=["不同公司階段會影響最適商業模式。"],
                follow_up_questions=["哪些指標最能驗證訂閱制的健康度？"],
            ),
        ),
    )

    note = generator.write_note(context, output_root=tmp_path, output_date=date(2026, 4, 7))

    assert note.path.exists()
    assert note.path == tmp_path / "2026-04-07" / "AI_商業模式" / "inside6202_AI_公司怎麼賺錢？.md"
    content = note.path.read_text(encoding="utf-8")
    assert "# AI 公司怎麼賺錢？" in content
    assert "- **字幕狀態：** 可用" in content
    assert "- **字幕來源：** 原生字幕" in content
    assert "- **字幕語言：** zh-TW" in content
    assert "## 📝 核心結論" in content
    assert "AI 公司常見營收模式可分為訂閱制、服務制與混合型模式。" in content
    assert "## 📌 重點拆解" in content
    assert "## ❓ 本片回答的問題" in content
    assert "- AI 公司怎麼賺錢？" in content
    assert "## 📎 重要依據 / 數據 / 例子" in content
    assert "- 00:00：先談營收模式" in content
    assert "## ⚠️ 限制條件 / 前提" in content
    assert "- 不同公司階段會影響最適商業模式。" in content
    assert "## 🔭 後續追蹤方向" in content
    assert "- 哪些指標最能驗證訂閱制的健康度？" in content
    assert "## 📚 完整逐字稿" in content
    assert "- **0:00**：今天先談 AI 公司常見的營收模式，接著會比較訂閱制與服務制的差異。" in content
    assert "- **2:00**：最後整理投資人應該追蹤的指標。" in content


def test_note_generator_surfaces_unavailable_analysis_instead_of_transcript_opening(tmp_path: Path) -> None:
    generator = MarkdownNoteGenerator()
    context = NoteContext(
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
            full_text="哈囉大家好我是腦哥 歡迎收看本週的幣圈週報。",
            merged_full_text="哈囉大家好我是腦哥 歡迎收看本週的幣圈週報。",
            merged_transcript=[
                TranscriptSegment(text="哈囉大家好我是腦哥", start=0.0, duration=1.0, timestamp="00:00"),
                TranscriptSegment(text="歡迎收看本週的幣圈週報。", start=1.0, duration=1.0, timestamp="00:01"),
            ],
        ),
        analysis_artifact=AnalysisArtifact(
            path=tmp_path / "analysis.json",
            transcript_path=tmp_path / "transcript.md",
            title="加密貨幣正在超車傳統金融體系",
            channel="brainbrocrypto",
            topic="區塊鏈資訊",
            status="pending",
            notes="等待 transcript-analyst 子 Agent 根據逐字稿完成分析。",
        ),
    )

    note = generator.write_note(context, output_root=tmp_path, output_date=date(2026, 4, 7))
    content = note.path.read_text(encoding="utf-8")

    assert "等待 transcript-analyst 子 Agent 根據逐字稿完成分析。" in content
    assert "## 📌 重點拆解\n- 待補" in content
