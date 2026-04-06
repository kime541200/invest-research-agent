from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from invest_research_agent.audio_downloader import AudioDownloader
from invest_research_agent.dedupe import select_new_videos
from invest_research_agent.models import ChannelCollectionResult, CollectionResult
from invest_research_agent.note_generator import MarkdownNoteGenerator, NoteContext
from invest_research_agent.state_store import ResourceStateStore
from invest_research_agent.stt import SttClient
from invest_research_agent.topic_router import TopicRouter
from invest_research_agent.video_fetcher import YouTubeMcpGateway


class CollectorOrchestrator:
    def __init__(
        self,
        state_store: ResourceStateStore,
        topic_router: TopicRouter,
        video_gateway: YouTubeMcpGateway,
        note_generator: MarkdownNoteGenerator,
        notes_root: Path | str,
        audio_downloader: AudioDownloader | None = None,
        stt_client: SttClient | None = None,
    ) -> None:
        self.state_store = state_store
        self.topic_router = topic_router
        self.video_gateway = video_gateway
        self.note_generator = note_generator
        self.notes_root = Path(notes_root)
        self.audio_downloader = audio_downloader
        self.stt_client = stt_client

    def collect_from_topic(
        self,
        topic: str,
        max_channels: int = 3,
        max_videos_per_channel: int = 5,
        initial_video_limit: int = 1,
        transcript_language: str | None = None,
        write_notes: bool = True,
        update_state: bool = True,
    ) -> CollectionResult:
        channels = self.state_store.get_channels()
        routed_channels = self.topic_router.route(topic, channels, limit=max_channels)
        channel_results: list[ChannelCollectionResult] = []

        for routed_channel in routed_channels:
            channel = routed_channel.channel
            try:
                resolved_channel_id, videos = self.video_gateway.list_recent_videos(
                    channel=channel,
                    max_results=max_videos_per_channel,
                )
                new_videos = select_new_videos(
                    channel=channel,
                    videos=videos,
                    initial_video_limit=initial_video_limit,
                )
                note_paths = []

                if write_notes:
                    for video in new_videos:
                        transcript = self.video_gateway.get_transcript(
                            video.video_id,
                            language=transcript_language,
                        )
                        transcript = self._get_best_available_transcript(
                            video=video,
                            transcript=transcript,
                            language=transcript_language,
                        )
                        note = self.note_generator.write_note(
                            NoteContext(
                                topic=topic,
                                channel=channel,
                                video=video,
                                transcript=transcript,
                            ),
                            output_root=self.notes_root,
                        )
                        note_paths.append(note.path)

                if update_state and new_videos:
                    self.state_store.update_last_checked_title(channel.name, new_videos[0].title)

                status = "processed" if new_videos else "skipped"
                message = "已處理新影片" if new_videos else "沒有新影片"
                channel_results.append(
                    ChannelCollectionResult(
                        channel=channel,
                        resolved_channel_id=resolved_channel_id,
                        route_score=routed_channel.score,
                        matched_terms=routed_channel.matched_terms,
                        fetched_videos=videos,
                        new_videos=new_videos,
                        note_paths=note_paths,
                        status=status,
                        message=message,
                    )
                )
            except Exception as exc:
                channel_results.append(
                    ChannelCollectionResult(
                        channel=channel,
                        resolved_channel_id=None,
                        route_score=routed_channel.score,
                        matched_terms=routed_channel.matched_terms,
                        status="error",
                        message=str(exc),
                    )
                )

        return CollectionResult(
            topic=topic,
            routed_channels=routed_channels,
            channel_results=channel_results,
            output_dir=self.notes_root,
        )

    def route_topic(self, topic: str, limit: int = 5) -> list[dict[str, Any]]:
        channels = self.state_store.get_channels()
        routed_channels = self.topic_router.route(topic, channels, limit=limit)
        return [
            {
                "channel": item.channel.name,
                "score": item.score,
                "matched_terms": item.matched_terms,
                "reason": item.reason,
            }
            for item in routed_channels
        ]

    def list_tags(self) -> list[str]:
        return self.state_store.get_all_tags()

    def list_channels(
        self,
        watch_tier: str | None = None,
        include_paused: bool = False,
    ) -> list[dict[str, Any]]:
        channels = self.state_store.get_channels()
        if not include_paused:
            channels = [channel for channel in channels if channel.watch_tier != "paused"]
        if watch_tier is not None:
            channels = [channel for channel in channels if channel.watch_tier == watch_tier]
        return [
            {
                "channel": channel.name,
                "url": channel.url,
                "watch_tier": channel.watch_tier,
                "priority": channel.priority,
            }
            for channel in channels
        ]

    def get_channel_tags(self, channel_name: str) -> list[str] | None:
        channel = self.state_store.get_channel(channel_name)
        if channel is None:
            return None
        return channel.tags

    def get_channels_by_tags(self, tags: list[str], include_paused: bool = False) -> dict[str, list[dict[str, str]]]:
        grouped = self.state_store.get_channels_by_tags(tags, include_paused=include_paused)
        return {
            tier: [{"channel": channel.name, "url": channel.url} for channel in channels]
            for tier, channels in grouped.items()
        }

    def get_last_checked_title(self, channel_name: str) -> str | None:
        channel = self.state_store.get_channel(channel_name)
        if channel is None:
            return None
        return channel.last_checked_video_title

    def update_last_checked_title(self, channel_name: str, title: str) -> None:
        self.state_store.update_last_checked_title(channel_name, title)

    def to_dict(self, result: CollectionResult) -> dict[str, Any]:
        data = asdict(result)
        for channel_result in data["channel_results"]:
            channel_result["note_paths"] = [str(path) for path in channel_result["note_paths"]]
        data["output_dir"] = str(result.output_dir)
        return data

    def _get_best_available_transcript(
        self,
        video: Any,
        transcript: Any,
        language: str | None = None,
    ) -> Any:
        if getattr(transcript, "status", "ok") != "unavailable":
            return transcript
        if self.audio_downloader is None or self.stt_client is None:
            return transcript

        try:
            audio_path = self.audio_downloader.download_audio(video)
            stt_transcript = self.stt_client.transcribe(
                audio_path=audio_path,
                video_id=video.video_id,
                language=language,
            )
            self.audio_downloader.handle_success(audio_path)
            return stt_transcript
        except Exception as exc:
            reason = transcript.reason or "native_transcript_unavailable"
            return transcript.__class__(
                video_id=transcript.video_id,
                language=transcript.language,
                status="unavailable",
                reason=f"{reason}; stt_fallback_failed: {exc}",
                full_text=transcript.full_text,
                merged_full_text=transcript.merged_full_text,
                transcript=transcript.transcript,
                merged_transcript=transcript.merged_transcript,
            )
