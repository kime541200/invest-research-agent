from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from typing import Any

WatchTier = Literal["core", "normal", "optional", "paused"]


@dataclass(frozen=True)
class ChannelState:
    last_checked_video_title: str = ""
    channel_id: str | None = None


@dataclass(frozen=True)
class ChannelConfig:
    name: str
    url: str
    alias: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    watch_tier: WatchTier = "normal"
    description: str = ""
    topic_keywords: list[str] = field(default_factory=list)
    priority: int = 0
    last_checked_video_title: str = ""
    channel_id: str | None = None


@dataclass(frozen=True)
class RoutedChannel:
    channel: ChannelConfig
    score: float
    matched_terms: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass(frozen=True)
class VideoMetadata:
    channel_name: str
    channel_id: str
    video_id: str
    title: str
    url: str
    published_at: str = ""
    description: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TranscriptSegment:
    text: str
    start: float
    duration: float
    timestamp: str


@dataclass(frozen=True)
class TranscriptBundle:
    video_id: str
    language: str | None
    status: str = "ok"
    source: str = "native"
    reason: str | None = None
    full_text: str = ""
    merged_full_text: str = ""
    transcript: list[TranscriptSegment] = field(default_factory=list)
    merged_transcript: list[TranscriptSegment] = field(default_factory=list)


@dataclass(frozen=True)
class GeneratedNote:
    path: Path
    content: str


@dataclass(frozen=True)
class ChannelCollectionResult:
    channel: ChannelConfig
    resolved_channel_id: str | None
    route_score: float
    matched_terms: list[str]
    fetched_videos: list[VideoMetadata] = field(default_factory=list)
    new_videos: list[VideoMetadata] = field(default_factory=list)
    note_paths: list[Path] = field(default_factory=list)
    status: str = "pending"
    message: str = ""


@dataclass(frozen=True)
class CollectionResult:
    topic: str
    routed_channels: list[RoutedChannel]
    channel_results: list[ChannelCollectionResult]
    output_dir: Path
