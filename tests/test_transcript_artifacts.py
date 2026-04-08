from __future__ import annotations

from datetime import date
from pathlib import Path

from invest_research_agent.models import ChannelConfig, TranscriptBundle, TranscriptSegment, VideoMetadata
from invest_research_agent.transcript_artifacts import (
    TranscriptArtifactWriter,
    artifact_to_note_context_data,
    read_transcript_artifact,
)


def test_transcript_artifact_writer_and_reader_roundtrip(tmp_path: Path) -> None:
    writer = TranscriptArtifactWriter()
    artifact = writer.write_artifact(
        topic="AI 商業模式",
        channel=ChannelConfig(name="inside6202", url="https://www.youtube.com/@inside6202"),
        video=VideoMetadata(
            channel_name="inside6202",
            channel_id="UC123",
            video_id="video123",
            title="AI 公司怎麼賺錢？",
            url="https://www.youtube.com/watch?v=video123",
            published_at="2026-04-06T08:00:00Z",
            description="這是一段影片描述。",
        ),
        transcript=TranscriptBundle(
            video_id="video123",
            language="zh-TW",
            source="native",
            merged_full_text="今天先談 AI 公司常見的營收模式。",
            merged_transcript=[
                TranscriptSegment(text="今天先談 AI 公司常見的營收模式。", start=0.0, duration=3.0, timestamp="00:00")
            ],
        ),
        output_root=tmp_path,
        output_date=date(2026, 4, 7),
    )

    loaded = read_transcript_artifact(artifact.path)

    assert loaded.title == "AI 公司怎麼賺錢？"
    assert loaded.channel == "inside6202"
    assert loaded.topic == "AI 商業模式"
    assert loaded.collected_date == "2026-04-07"
    assert loaded.transcript_source == "原生字幕"
    assert loaded.segments[0].timestamp == "00:00"
    assert artifact.path == tmp_path / "2026-04-07" / "AI_商業模式" / "inside6202_AI_公司怎麼賺錢？.transcript.md"


def test_transcript_artifact_can_be_converted_back_to_note_context_data(tmp_path: Path) -> None:
    writer = TranscriptArtifactWriter()
    artifact = writer.write_artifact(
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
        output_root=tmp_path,
        output_date=date(2026, 4, 7),
    )

    channel, video, transcript = artifact_to_note_context_data(read_transcript_artifact(artifact.path))

    assert channel.name == "brainbrocrypto"
    assert video.video_id == "video999"
    assert transcript.source == "stt"
    assert transcript.merged_transcript[0].text == "這是 STT fallback 逐字稿。"
