from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re

from info_collector.models import ChannelConfig, GeneratedNote, TranscriptBundle, VideoMetadata


@dataclass(frozen=True)
class NoteContext:
    topic: str
    channel: ChannelConfig
    video: VideoMetadata
    transcript: TranscriptBundle | None = None


class MarkdownNoteGenerator:
    def build_note(self, context: NoteContext) -> str:
        summary = _build_summary(context)
        highlights = _build_highlights(context)
        actions = _build_actions(context)
        transcript_excerpt = _build_transcript_excerpt(context.transcript)

        lines = [
            f"# {context.video.title}",
            "",
            f"- **頻道：** {context.channel.name}",
            f"- **日期：** {_date_from_video(context.video)}",
            f"- **來源：** {context.video.url}",
            f"- **主題：** {context.topic}",
            "",
            "## 📝 核心總結",
            f"> {summary}",
            "",
            "## 📌 重點摘要",
            *[f"- {item}" for item in highlights],
            "",
            "## 💡 行動建議 (Actionable Insights)",
            *[f"- {item}" for item in actions],
        ]

        if transcript_excerpt:
            lines.extend(
                [
                    "",
                    "## 📚 逐字稿摘錄",
                    *[f"- {item}" for item in transcript_excerpt],
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


def _build_summary(context: NoteContext) -> str:
    transcript = _get_preferred_transcript(context.transcript)
    transcript_text = _get_preferred_transcript_text(context.transcript)
    if transcript_text:
        summary_body = _summarize_transcript_text(transcript_text)
        if summary_body:
            return _trim_text(
                f"這支影片圍繞「{context.topic}」展開，重點聚焦在：{summary_body}",
                limit=220,
            )
    if transcript:
        combined = " ".join(segment.text for segment in transcript[:2] if segment.text).strip()
        if combined:
            return _trim_text(
                f"這支影片圍繞「{context.topic}」展開，重點聚焦在：{combined}",
                limit=220,
            )

    if context.video.description.strip():
        return _trim_text(
            f"這支影片與「{context.topic}」相關，影片描述提到：{context.video.description.strip()}",
            limit=180,
        )

    tags = "、".join(context.channel.tags[:3]) or context.topic
    return f"這支影片可作為「{context.topic}」的初步觀察材料，建議搭配頻道既有關注領域 {tags} 一起閱讀。"


def _build_highlights(context: NoteContext) -> list[str]:
    transcript = _get_preferred_transcript(context.transcript)
    if transcript:
        candidates = _sample_segments(transcript, sample_size=3)
        return [
            f"**{segment.timestamp or '重點'}**：{_trim_text(segment.text, limit=90)}"
            for segment in candidates
        ]

    highlights: list[str] = []
    if context.video.description.strip():
        for piece in _split_sentences(context.video.description)[:3]:
            highlights.append(f"**影片描述**：{_trim_text(piece, limit=90)}")
    if not highlights:
        highlights.append("**待補逐字稿**：目前沒有可用字幕，建議回看影片描述與標題補齊摘要。")
    return highlights


def _build_actions(context: NoteContext) -> list[str]:
    actions = [
        f"把這支影片與主題「{context.topic}」一起比對，確認是否出現新的市場敘事或觀點轉向。",
    ]
    if context.channel.tags:
        actions.append(
            f"延伸追蹤頻道常見標籤：{'、'.join(context.channel.tags[:4])}，觀察後續是否持續提及。"
        )
    else:
        actions.append("若後續要深入討論，建議再抓取同頻道下一支相關影片做交叉比對。")
    return actions


def _build_transcript_excerpt(transcript: TranscriptBundle | None) -> list[str]:
    preferred_transcript = _get_preferred_transcript(transcript)
    if not preferred_transcript:
        return []
    return [
        f"**{segment.timestamp or '片段'}**：{_trim_text(segment.text, limit=110)}"
        for segment in _sample_segments(preferred_transcript, sample_size=5)
    ]


def _sample_segments(segments: list, sample_size: int) -> list:
    if len(segments) <= sample_size:
        return segments
    indexes = _pick_sample_indexes(len(segments), sample_size)
    return [segments[idx] for idx in indexes]


def _split_sentences(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"[。！？\n]+", text) if item.strip()]


def _date_from_video(video: VideoMetadata) -> str:
    return video.published_at[:10] if video.published_at else date.today().isoformat()


def _trim_text(text: str, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


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
        return transcript.merged_full_text
    if transcript.full_text:
        return transcript.full_text
    preferred_segments = _get_preferred_transcript(transcript)
    return " ".join(segment.text for segment in preferred_segments if segment.text).strip()


def _summarize_transcript_text(text: str) -> str:
    paragraphs = [item.strip() for item in text.split("\n\n") if item.strip()]
    if paragraphs:
        return _trim_text(" ".join(paragraphs[:2]), limit=180)

    sentences = _split_sentences(text)
    if sentences:
        return _trim_text("；".join(sentences[:2]), limit=180)

    return _trim_text(text, limit=180)


def _pick_sample_indexes(segment_count: int, sample_size: int) -> list[int]:
    if segment_count <= sample_size:
        return list(range(segment_count))
    if sample_size <= 1:
        return [0]

    last_index = segment_count - 1
    indexes = {0, last_index}
    if sample_size >= 3:
        indexes.add(segment_count // 2)

    if len(indexes) < sample_size:
        step = max(last_index // max(sample_size - 1, 1), 1)
        for idx in range(step, last_index, step):
            indexes.add(idx)
            if len(indexes) >= sample_size:
                break

    return sorted(indexes)[:sample_size]
