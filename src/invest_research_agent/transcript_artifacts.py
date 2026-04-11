from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re

from invest_research_agent.models import ChannelConfig, TranscriptBundle, TranscriptSegment, VideoMetadata


@dataclass(frozen=True)
class TranscriptArtifact:
    path: Path
    title: str
    channel: str
    video_id: str
    video_url: str
    collected_date: str
    published_date: str
    topic: str
    transcript_status: str
    transcript_source: str
    transcript_language: str
    description: str
    full_text: str
    segments: list[TranscriptSegment]


class TranscriptArtifactWriter:
    def write_artifact(
        self,
        *,
        topic: str,
        channel: ChannelConfig,
        video: VideoMetadata,
        transcript: TranscriptBundle,
        output_root: Path | str,
        output_date: date | None = None,
    ) -> TranscriptArtifact:
        target_date = output_date or date.today()
        output_dir = Path(output_root) / target_date.isoformat() / _sanitize_path_segment(topic)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / _sanitize_filename(f"{channel.name}_{video.title}.transcript.md")

        segments = _get_preferred_segments(transcript)
        full_text = _get_preferred_full_text(transcript)
        artifact = TranscriptArtifact(
            path=path,
            title=video.title,
            channel=channel.name,
            video_id=video.video_id,
            video_url=video.url,
            collected_date=target_date.isoformat(),
            published_date=_get_video_date(video).isoformat(),
            topic=topic,
            transcript_status=_get_transcript_status_label(transcript),
            transcript_source=_get_transcript_source_label(transcript),
            transcript_language=transcript.language or "未知",
            description=video.description.strip(),
            full_text=full_text,
            segments=segments,
        )
        path.write_text(_build_markdown_artifact(artifact), encoding="utf-8")
        return artifact


def read_transcript_artifact(path: Path | str) -> TranscriptArtifact:
    artifact_path = Path(path)
    lines = artifact_path.read_text(encoding="utf-8").splitlines()
    metadata: dict[str, str] = {}
    title = ""
    description_lines: list[str] = []
    transcript_lines: list[str] = []
    segments: list[TranscriptSegment] = []
    section = ""

    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            continue
        if line.startswith("- **") and "：** " in line:
            key, value = line[4:].split("：** ", maxsplit=1)
            metadata[key] = value.strip()
            continue
        if line.startswith("## "):
            if "影片描述" in line:
                section = "description"
            elif "完整逐字稿" in line:
                section = "transcript"
            else:
                section = ""
            continue
        if section == "description" and line.strip():
            description_lines.append(line)
        elif section == "transcript" and line.strip():
            transcript_lines.append(line)
            segment_match = re.match(r"- \*\*(.+?)\*\*：(.*)", line)
            if segment_match:
                segments.append(
                    TranscriptSegment(
                        text=segment_match.group(2).strip(),
                        start=0.0,
                        duration=0.0,
                        timestamp=segment_match.group(1).strip(),
                    )
                )

    if not segments and transcript_lines:
        segments = [TranscriptSegment(text=" ".join(transcript_lines).strip(), start=0.0, duration=0.0, timestamp="")]

    full_text = " ".join(segment.text for segment in segments if segment.text).strip()
    return TranscriptArtifact(
        path=artifact_path,
        title=title,
        channel=metadata.get("頻道", ""),
        video_id=metadata.get("影片 ID", ""),
        video_url=metadata.get("來源", ""),
        collected_date=metadata.get("收集日期", _infer_collected_date_from_path(artifact_path)),
        published_date=metadata.get("日期", ""),
        topic=metadata.get("主題", ""),
        transcript_status=metadata.get("字幕狀態", ""),
        transcript_source=metadata.get("字幕來源", ""),
        transcript_language=metadata.get("字幕語言", ""),
        description="\n".join(description_lines).strip(),
        full_text=full_text,
        segments=segments,
    )


def artifact_to_note_context_data(artifact: TranscriptArtifact) -> tuple[ChannelConfig, VideoMetadata, TranscriptBundle]:
    channel = ChannelConfig(name=artifact.channel, url=artifact.video_url, last_checked_video_title="")
    video = VideoMetadata(
        channel_name=artifact.channel,
        channel_id="",
        video_id=artifact.video_id,
        title=artifact.title,
        url=artifact.video_url,
        published_at=artifact.published_date,
        description=artifact.description,
    )
    transcript = TranscriptBundle(
        video_id=artifact.video_id,
        language=None if artifact.transcript_language == "未知" else artifact.transcript_language,
        status="ok" if artifact.transcript_status == "可用" else "unavailable",
        source="stt" if artifact.transcript_source == "STT fallback" else "native",
        full_text=artifact.full_text,
        merged_full_text=artifact.full_text,
        transcript=artifact.segments,
        merged_transcript=artifact.segments,
    )
    return channel, video, transcript


def read_transcript_artifact_for_analysis(path: Path | str) -> TranscriptArtifact:
    return read_transcript_artifact(path)


def _build_markdown_artifact(artifact: TranscriptArtifact) -> str:
    lines = [
        f"# {artifact.title}",
        "",
        f"- **頻道：** {artifact.channel}",
        f"- **日期：** {artifact.published_date}",
        f"- **收集日期：** {artifact.collected_date}",
        f"- **來源：** {artifact.video_url}",
        f"- **影片 ID：** {artifact.video_id}",
        f"- **主題：** {artifact.topic}",
        f"- **字幕狀態：** {artifact.transcript_status}",
        f"- **字幕來源：** {artifact.transcript_source}",
        f"- **字幕語言：** {artifact.transcript_language}",
    ]

    if artifact.description:
        lines.extend(["", "## 🗒️ 影片描述", artifact.description])

    lines.extend(["", "## 📚 完整逐字稿"])
    if artifact.segments:
        lines.extend(
            [f"- **{segment.timestamp or '片段'}**：{_normalize_text(segment.text)}" for segment in artifact.segments if _normalize_text(segment.text)]
        )
    elif artifact.full_text:
        lines.append(_normalize_text(artifact.full_text))
    else:
        lines.append("目前沒有可用逐字稿。")

    return "\n".join(lines).rstrip() + "\n"


def _get_preferred_segments(transcript: TranscriptBundle) -> list[TranscriptSegment]:
    if transcript.merged_transcript:
        return transcript.merged_transcript
    return transcript.transcript


def _get_preferred_full_text(transcript: TranscriptBundle) -> str:
    if transcript.merged_full_text.strip():
        return _normalize_text(transcript.merged_full_text)
    if transcript.full_text.strip():
        return _normalize_text(transcript.full_text)
    return _normalize_text(" ".join(segment.text for segment in _get_preferred_segments(transcript) if segment.text))


def _get_transcript_status_label(transcript: TranscriptBundle) -> str:
    if transcript.status == "ok":
        return "可用"
    reason = transcript.reason or "unknown"
    return f"不可用 ({_normalize_text(reason)})"


def _get_transcript_source_label(transcript: TranscriptBundle) -> str:
    if transcript.source == "stt":
        return "STT fallback"
    if transcript.source == "native":
        return "原生字幕"
    return transcript.source


def _get_video_date(video: VideoMetadata) -> date:
    if video.published_at:
        return date.fromisoformat(video.published_at[:10])
    return date.today()


def _sanitize_filename(filename: str) -> str:
    sanitized = re.sub(r'[\\/:*?"<>|]+', "_", filename)
    sanitized = re.sub(r"\s+", "_", sanitized).strip("._")
    return sanitized or "transcript.md"


def _sanitize_path_segment(value: str) -> str:
    sanitized = re.sub(r'[\\/:*?"<>|]+', "_", value)
    sanitized = re.sub(r"\s+", "_", sanitized).strip("._")
    return sanitized or "untitled-topic"


def _infer_collected_date_from_path(path: Path) -> str:
    parent = path.parent
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", parent.name):
        return parent.name
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", parent.parent.name):
        return parent.parent.name
    return ""


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
