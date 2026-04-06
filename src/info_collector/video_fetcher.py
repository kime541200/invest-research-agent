from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from info_collector.mcp_client import McpHttpClient
from info_collector.models import ChannelConfig, TranscriptBundle, TranscriptSegment, VideoMetadata


class YouTubeMcpGateway:
    def __init__(self, client: McpHttpClient) -> None:
        self.client = client

    def resolve_channel_id(self, channel: ChannelConfig) -> str:
        if channel.channel_id:
            return channel.channel_id

        for query in _build_channel_queries(channel):
            result = self.client.call_tool(
                "channels_searchChannels",
                {
                    "query": query,
                    "max_results": 5,
                },
            )
            channel_id = _pick_channel_id(result, channel)
            if channel_id:
                return channel_id

        raise RuntimeError(f"無法解析頻道 ID: {channel.name}")

    def list_recent_videos(self, channel: ChannelConfig, max_results: int = 5) -> tuple[str, list[VideoMetadata]]:
        channel_id = self.resolve_channel_id(channel)
        result = self.client.call_tool(
            "channels_listVideos",
            {
                "channel_id": channel_id,
                "max_results": max_results,
            },
        )
        videos = [
            _to_video_metadata(channel.name, channel_id, item)
            for item in result or []
            if _extract_video_id(item)
        ]
        return channel_id, videos

    def get_transcript(self, video_id: str, language: str | None = None) -> TranscriptBundle:
        payload: dict[str, Any] = {"video_id": video_id}
        if language:
            payload["language"] = language

        result = self.client.call_tool("transcripts_getTranscript", payload)
        transcript = _to_transcript_segments((result or {}).get("transcript", []))
        merged_transcript = _to_transcript_segments((result or {}).get("merged_transcript", []))
        return TranscriptBundle(
            video_id=video_id,
            language=(result or {}).get("language"),
            status=str((result or {}).get("status", "ok")),
            reason=(result or {}).get("reason"),
            full_text=str((result or {}).get("full_text", "")),
            merged_full_text=str((result or {}).get("merged_full_text", "")),
            transcript=transcript,
            merged_transcript=merged_transcript,
        )


def _build_channel_queries(channel: ChannelConfig) -> list[str]:
    queries: list[str] = []
    handle = _extract_handle_from_url(channel.url)
    if handle:
        queries.extend([handle, f"@{handle}"])
    queries.extend(channel.alias)
    queries.append(channel.name)

    seen: set[str] = set()
    deduped: list[str] = []
    for query in queries:
        normalized = query.strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


def _extract_handle_from_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return ""
    if path.startswith("@"):
        return path[1:]
    return path.rsplit("/", maxsplit=1)[-1]


def _pick_channel_id(result: Any, channel: ChannelConfig) -> str | None:
    if not isinstance(result, list):
        return None

    desired_names = {channel.name.casefold(), *(alias.casefold() for alias in channel.alias)}
    for item in result:
        snippet = item.get("snippet", {})
        title = str(snippet.get("channelTitle", "")).casefold()
        if title in desired_names:
            return str(item.get("id", {}).get("channelId", ""))

    first = result[0] if result else {}
    return str(first.get("id", {}).get("channelId", "")) or None


def _extract_video_id(item: dict[str, Any]) -> str:
    return str(item.get("id", {}).get("videoId", ""))


def _to_video_metadata(channel_name: str, channel_id: str, item: dict[str, Any]) -> VideoMetadata:
    snippet = item.get("snippet", {})
    video_id = _extract_video_id(item)
    return VideoMetadata(
        channel_name=channel_name,
        channel_id=channel_id,
        video_id=video_id,
        title=str(snippet.get("title", "")).strip(),
        url=f"https://www.youtube.com/watch?v={video_id}",
        published_at=str(snippet.get("publishedAt", "")),
        description=str(snippet.get("description", "")),
        raw=item,
    )


def _to_transcript_segments(items: list[dict[str, Any]]) -> list[TranscriptSegment]:
    return [
        TranscriptSegment(
            text=str(item.get("text", "")).strip(),
            start=float(item.get("start", 0.0)),
            duration=float(item.get("duration", 0.0)),
            timestamp=str(item.get("timestamp", "")),
        )
        for item in items
        if str(item.get("text", "")).strip()
    ]
