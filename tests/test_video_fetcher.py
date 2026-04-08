from __future__ import annotations

from invest_research_agent.models import ChannelConfig
from invest_research_agent.video_fetcher import YouTubeMcpGateway


class FakeMcpClient:
    def __init__(self, responses: dict[tuple[str, str], object]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, object]]] = []

    def call_tool(self, name: str, arguments: dict[str, object] | None = None) -> object:
        payload = arguments or {}
        self.calls.append((name, payload))
        if name == "channels_searchChannels":
            return self.responses.get((name, str(payload.get("query", ""))), [])
        if name == "channels_listVideos":
            return self.responses.get((name, str(payload.get("channel_id", ""))), [])
        if name == "transcripts_getTranscript":
            return self.responses.get((name, str(payload.get("video_id", ""))), {})
        raise AssertionError(f"unexpected call: {name}")


def test_resolve_channel_id_uses_cached_channel_id() -> None:
    client = FakeMcpClient({})
    gateway = YouTubeMcpGateway(client)
    channel = ChannelConfig(
        name="inside6202",
        url="https://www.youtube.com/@inside6202",
        channel_id="UC_CACHED",
    )

    channel_id = gateway.resolve_channel_id(channel)

    assert channel_id == "UC_CACHED"
    assert client.calls == []


def test_resolve_channel_id_prefers_matching_alias_title() -> None:
    client = FakeMcpClient(
        {
            ("channels_searchChannels", "inside6202"): [
                {
                    "id": {"channelId": "UC_MATCH"},
                    "snippet": {"channelTitle": "Inside6202"},
                },
                {
                    "id": {"channelId": "UC_OTHER"},
                    "snippet": {"channelTitle": "Other"},
                },
            ]
        }
    )
    gateway = YouTubeMcpGateway(client)
    channel = ChannelConfig(
        name="inside6202",
        url="https://www.youtube.com/@inside6202",
        alias=["Inside"],
    )

    channel_id = gateway.resolve_channel_id(channel)

    assert channel_id == "UC_MATCH"


def test_list_recent_videos_filters_entries_without_video_id() -> None:
    client = FakeMcpClient(
        {
            ("channels_searchChannels", "inside6202"): [
                {
                    "id": {"channelId": "UC123"},
                    "snippet": {"channelTitle": "inside6202"},
                }
            ],
            ("channels_listVideos", "UC123"): [
                {
                    "id": {"videoId": "video-123"},
                    "snippet": {
                        "title": "有效影片",
                        "publishedAt": "2026-04-07T08:00:00Z",
                        "description": "影片描述",
                    },
                },
                {
                    "id": {},
                    "snippet": {"title": "無效影片"},
                },
            ],
        }
    )
    gateway = YouTubeMcpGateway(client)
    channel = ChannelConfig(name="inside6202", url="https://www.youtube.com/@inside6202")

    channel_id, videos = gateway.list_recent_videos(channel)

    assert channel_id == "UC123"
    assert len(videos) == 1
    assert videos[0].title == "有效影片"
    assert videos[0].url == "https://www.youtube.com/watch?v=video-123"


def test_get_transcript_maps_metadata_and_segments() -> None:
    client = FakeMcpClient(
        {
            ("transcripts_getTranscript", "video-123"): {
                "language": "zh-TW",
                "status": "ok",
                "reason": None,
                "full_text": "第一段 第二段",
                "merged_full_text": "第一段，第二段",
                "transcript": [
                    {"text": "第一段", "start": 0.0, "duration": 2.0, "timestamp": "0:00"},
                    {"text": "第二段", "start": 5.0, "duration": 3.0, "timestamp": "0:05"},
                ],
                "merged_transcript": [
                    {"text": "第一段，第二段", "start": 0.0, "duration": 8.0, "timestamp": "0:00"},
                ],
            }
        }
    )
    gateway = YouTubeMcpGateway(client)

    transcript = gateway.get_transcript("video-123", language="zh-TW")

    assert transcript.language == "zh-TW"
    assert transcript.status == "ok"
    assert transcript.full_text == "第一段 第二段"
    assert transcript.merged_transcript[0].text == "第一段，第二段"
