from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re

from invest_research_agent.models import ChannelConfig, GeneratedNote, TranscriptBundle, VideoMetadata


@dataclass(frozen=True)
class NoteContext:
    topic: str
    channel: ChannelConfig
    video: VideoMetadata
    transcript: TranscriptBundle | None = None


class MarkdownNoteGenerator:
    def build_note(self, context: NoteContext) -> str:
        transcript_text = _get_preferred_transcript_text(context.transcript)
        transcript_lines = _build_full_transcript_lines(context.transcript)

        lines = [
            f"# {context.video.title}",
            "",
            f"- **頻道：** {context.channel.name}",
            f"- **日期：** {_date_from_video(context.video)}",
            f"- **來源：** {context.video.url}",
            f"- **主題：** {context.topic}",
            f"- **字幕狀態：** {_get_transcript_status_label(context.transcript)}",
            f"- **字幕來源：** {_get_transcript_source_label(context.transcript)}",
            f"- **字幕語言：** {_get_transcript_language_label(context.transcript)}",
            "",
        ]

        if context.video.description.strip():
            lines.extend(
                [
                    "",
                    "## 🗒️ 影片描述",
                    context.video.description.strip(),
                ]
            )

        if transcript_text:
            lines.extend(
                [
                    "",
                    "## 📚 完整逐字稿",
                    *transcript_lines,
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "## ⚠️ 逐字稿狀態",
                    _build_transcript_unavailable_message(context.transcript),
                ]
            )

        return "\n".join(lines).rstrip() + "\n"

    def write_note(
        self,
        context: NoteContext,
        output_root: Path | str,
        output_date: date | None = None,
    ) -> GeneratedNote:
        target_date = output_date or date.today()
        note_dir = Path(output_root) / target_date.isoformat()
        note_dir.mkdir(parents=True, exist_ok=True)
        path = note_dir / _sanitize_filename(f"{context.channel.name}_{context.video.title}.md")
        content = self.build_note(context)
        path.write_text(content, encoding="utf-8")
        return GeneratedNote(path=path, content=content)


def _build_full_transcript_lines(transcript: TranscriptBundle | None) -> list[str]:
    preferred_transcript = _get_preferred_transcript(transcript)
    if preferred_transcript:
        return [
            f"- **{segment.timestamp or '片段'}**：{_normalize_text(segment.text)}"
            for segment in preferred_transcript
            if _normalize_text(segment.text)
        ]

    transcript_text = _get_preferred_transcript_text(transcript)
    if not transcript_text:
        return []
    return [_normalize_text(transcript_text)]


def _date_from_video(video: VideoMetadata) -> str:
    return video.published_at[:10] if video.published_at else date.today().isoformat()


def _sanitize_filename(filename: str) -> str:
    sanitized = re.sub(r'[\\/:*?"<>|]+', "_", filename)
    sanitized = re.sub(r"\s+", "_", sanitized).strip("._")
    return sanitized or "note.md"


def _get_preferred_transcript(transcript: TranscriptBundle | None) -> list:
    if transcript is None:
        return []
    if transcript.merged_transcript:
        return transcript.merged_transcript
    return transcript.transcript


def _get_preferred_transcript_text(transcript: TranscriptBundle | None) -> str:
    if transcript is None:
        return ""
    if transcript.merged_full_text:
        return _normalize_text(transcript.merged_full_text)
    if transcript.full_text:
        return _normalize_text(transcript.full_text)
    preferred_segments = _get_preferred_transcript(transcript)
    return _normalize_text(" ".join(segment.text for segment in preferred_segments if segment.text))


def _get_transcript_status_label(transcript: TranscriptBundle | None) -> str:
    if transcript is None:
        return "未提供"
    if transcript.status == "ok":
        return "可用"
    return f"不可用 ({_get_transcript_reason_text(transcript)})"


def _get_transcript_source_label(transcript: TranscriptBundle | None) -> str:
    if transcript is None:
        return "未提供"
    if transcript.status != "ok" and transcript.reason and "stt_fallback_failed" in transcript.reason:
        return "原生字幕不可用，STT fallback 失敗"
    if transcript.source == "stt":
        return "STT fallback"
    if transcript.source == "native":
        return "原生字幕"
    return transcript.source


def _get_transcript_language_label(transcript: TranscriptBundle | None) -> str:
    if transcript is None or not transcript.language:
        return "未知"
    return transcript.language


def _build_transcript_unavailable_message(transcript: TranscriptBundle | None) -> str:
    if transcript is None:
        return "目前沒有可用逐字稿。"
    reason = _get_transcript_reason_text(transcript)
    return f"目前沒有可用逐字稿，原因：{reason}"


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _get_transcript_reason_text(transcript: TranscriptBundle) -> str:
    return _normalize_text(transcript.reason or "unknown")
