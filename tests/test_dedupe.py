from __future__ import annotations

from invest_research_agent.dedupe import select_new_videos
from invest_research_agent.models import ChannelConfig, VideoMetadata


def _make_video(title: str, video_id: str) -> VideoMetadata:
    return VideoMetadata(
        channel_name="inside6202",
        channel_id="UC123",
        video_id=video_id,
        title=title,
        url=f"https://www.youtube.com/watch?v={video_id}",
    )


def test_select_new_videos_returns_initial_limit_for_first_time_channel() -> None:
    channel = ChannelConfig(name="inside6202", url="https://www.youtube.com/@inside6202")
    videos = [
        _make_video("最新影片", "video-new"),
        _make_video("次新影片", "video-second"),
    ]

    selected = select_new_videos(channel, videos, initial_video_limit=2)

    assert [video.title for video in selected] == ["最新影片", "次新影片"]


def test_select_new_videos_still_returns_at_least_one_for_initial_limit_zero() -> None:
    channel = ChannelConfig(name="inside6202", url="https://www.youtube.com/@inside6202")
    videos = [
        _make_video("最新影片", "video-new"),
        _make_video("次新影片", "video-second"),
    ]

    selected = select_new_videos(channel, videos, initial_video_limit=0)

    assert [video.title for video in selected] == ["最新影片"]


def test_select_new_videos_stops_at_last_checked_title() -> None:
    channel = ChannelConfig(
        name="inside6202",
        url="https://www.youtube.com/@inside6202",
        last_checked_video_title="舊影片",
    )
    videos = [
        _make_video("最新影片", "video-new"),
        _make_video("次新影片", "video-second"),
        _make_video("舊影片", "video-old"),
    ]

    selected = select_new_videos(channel, videos)

    assert [video.title for video in selected] == ["最新影片", "次新影片"]


def test_select_new_videos_returns_all_when_last_checked_title_not_found() -> None:
    channel = ChannelConfig(
        name="inside6202",
        url="https://www.youtube.com/@inside6202",
        last_checked_video_title="不存在的影片",
    )
    videos = [
        _make_video("最新影片", "video-new"),
        _make_video("次新影片", "video-second"),
    ]

    selected = select_new_videos(channel, videos)

    assert [video.title for video in selected] == ["最新影片", "次新影片"]
