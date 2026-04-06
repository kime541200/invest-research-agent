from __future__ import annotations

from invest_research_agent.models import ChannelConfig, VideoMetadata


def select_new_videos(
    channel: ChannelConfig,
    videos: list[VideoMetadata],
    initial_video_limit: int = 1,
) -> list[VideoMetadata]:
    if not videos:
        return []

    if not channel.last_checked_video_title:
        return videos[:max(initial_video_limit, 1)]

    new_videos: list[VideoMetadata] = []
    for video in videos:
        if video.title == channel.last_checked_video_title:
            break
        new_videos.append(video)
    return new_videos
