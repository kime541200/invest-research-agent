from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from invest_research_agent.analysis_artifacts import AnalysisArtifactStore
from invest_research_agent.audio_downloader import AudioDownloader
from invest_research_agent.dedupe import select_new_videos
from invest_research_agent.models import ChannelCollectionResult, CollectionResult, NotebookLMWorkflowResult
from invest_research_agent.note_generator import MarkdownNoteGenerator, NoteContext
from invest_research_agent.notebooklm_enricher import NotebookLMCollectedResearch, NotebookLMNoteEnricher
from invest_research_agent.notebooklm_gateway import NotebookLMGatewayError
from invest_research_agent.research_artifacts import ResearchArtifactStore
from invest_research_agent.research_models import ResearchEnrichmentResult
from invest_research_agent.research_pipeline import write_enrichment_result
from invest_research_agent.transcript_artifacts import TranscriptArtifactWriter
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
        transcripts_root: Path | str | None = None,
        analysis_root: Path | str | None = None,
        audio_downloader: AudioDownloader | None = None,
        stt_client: SttClient | None = None,
        notebooklm_enricher: NotebookLMNoteEnricher | None = None,
    ) -> None:
        self.state_store = state_store
        self.topic_router = topic_router
        self.video_gateway = video_gateway
        self.note_generator = note_generator
        self.notes_root = Path(notes_root)
        self.transcripts_root = Path(transcripts_root) if transcripts_root is not None else self.notes_root.parent / "transcripts"
        self.analysis_root = Path(analysis_root) if analysis_root is not None else self.notes_root.parent / "analysis"
        self.audio_downloader = audio_downloader
        self.stt_client = stt_client
        self.notebooklm_enricher = notebooklm_enricher
        self.transcript_writer = TranscriptArtifactWriter()
        self.analysis_store = AnalysisArtifactStore()
        self.research_store = ResearchArtifactStore()

    def collect_from_topic(
        self,
        topic: str,
        max_channels: int = 3,
        max_videos_per_channel: int = 5,
        initial_video_limit: int = 1,
        transcript_language: str | None = None,
        write_transcripts: bool = True,
        initialize_analysis: bool = True,
        write_notes: bool = True,
        update_state: bool = True,
        notebooklm_first: bool = True,
    ) -> CollectionResult:
        channels = self.state_store.get_channels()
        routed_channels = self.topic_router.route(topic, channels, limit=max_channels)
        channel_results: list[ChannelCollectionResult] = []
        collected_date = date.today()

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
                transcript_paths = []
                analysis_paths = []
                research_paths = []
                notebooklm_results = []

                for video in new_videos:
                    notebooklm_research, notebooklm_result = self._try_collect_with_notebooklm(
                        topic=topic,
                        channel=channel,
                        video=video,
                    ) if notebooklm_first else (None, NotebookLMWorkflowResult(status="not_attempted", reason="notebooklm_disabled"))
                    notebooklm_results.append(notebooklm_result)
                    if notebooklm_research is not None:
                        note = None
                        if write_notes:
                            note = self.note_generator.write_note(
                                NoteContext(
                                    topic=topic,
                                    channel=channel,
                                    video=video,
                                    transcript=None,
                                    research_sections=notebooklm_research.research_sections,
                                    analysis_artifact=None,
                                ),
                                output_root=self.notes_root,
                                output_date=collected_date,
                            )
                            note_paths.append(note.path)
                        if note is not None:
                            enrichment = ResearchEnrichmentResult(
                                note_path=note.path,
                                note_title=video.title,
                                keywords=[],
                                evidence=notebooklm_research.evidence,
                                answer=notebooklm_research.answer,
                                conversation_id=notebooklm_research.conversation_id,
                                notebook_id=notebooklm_research.notebook_id,
                                source_of_truth="notebooklm",
                            )
                            sidecar_path = write_enrichment_result(
                                enrichment,
                                note.path.with_suffix(".notebooklm.research.json"),
                            )
                            research_artifact = self.research_store.build_from_notebooklm(
                                enrichment=enrichment,
                                channel=channel.name,
                                topic=topic,
                                output_root=self.analysis_root.parent / "research",
                                output_date=collected_date.isoformat(),
                            )
                            research_paths.extend([sidecar_path, research_artifact.path])
                        continue

                    transcript = self.video_gateway.get_transcript(
                        video.video_id,
                        language=transcript_language,
                    )
                    transcript = self._get_best_available_transcript(
                        video=video,
                        transcript=transcript,
                        language=transcript_language,
                    )
                    analysis_artifact = None
                    transcript_artifact = None

                    if write_transcripts:
                        transcript_artifact = self.transcript_writer.write_artifact(
                            topic=topic,
                            channel=channel,
                            video=video,
                            transcript=transcript,
                            output_root=self.transcripts_root,
                            output_date=collected_date,
                        )
                        transcript_paths.append(transcript_artifact.path)

                    if initialize_analysis and transcript_artifact is not None:
                        analysis_artifact = self.analysis_store.initialize_pending(
                            transcript_artifact=transcript_artifact,
                            output_root=self.analysis_root,
                        )
                        analysis_paths.append(analysis_artifact.path)

                    if write_notes:
                        note = self.note_generator.write_note(
                            NoteContext(
                                topic=topic,
                                channel=channel,
                                video=video,
                                transcript=transcript,
                                analysis_artifact=analysis_artifact,
                            ),
                            output_root=self.notes_root,
                            output_date=collected_date,
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
                        transcript_paths=transcript_paths,
                        analysis_paths=analysis_paths,
                        research_paths=research_paths,
                        note_paths=note_paths,
                        notebooklm_results=notebooklm_results,
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
            channel_result["transcript_paths"] = [str(path) for path in channel_result["transcript_paths"]]
            channel_result["analysis_paths"] = [str(path) for path in channel_result["analysis_paths"]]
            channel_result["research_paths"] = [str(path) for path in channel_result.get("research_paths", [])]
            channel_result["note_paths"] = [str(path) for path in channel_result["note_paths"]]
        data["output_dir"] = str(result.output_dir)
        return data

    def _try_collect_with_notebooklm(
        self,
        *,
        topic: str,
        channel: Any,
        video: Any,
    ) -> tuple[NotebookLMCollectedResearch | None, NotebookLMWorkflowResult]:
        if self.notebooklm_enricher is None:
            return None, NotebookLMWorkflowResult(status="not_attempted", reason="notebooklm_unconfigured")
        try:
            research = self.notebooklm_enricher.collect_video_research(
                topic=topic,
                channel=channel,
                video=video,
            )
            return research, _collected_research_to_result(research)
        except NotebookLMGatewayError as exc:
            return None, NotebookLMWorkflowResult(
                status="fallback",
                reason=str(exc),
                source_of_truth="transcript_artifact",
            )
        except Exception as exc:
            return None, NotebookLMWorkflowResult(
                status="fallback",
                reason=str(exc),
                source_of_truth="transcript_artifact",
            )

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
                source=getattr(transcript, "source", "native"),
                reason=f"{reason}; stt_fallback_failed: {exc}",
                full_text=transcript.full_text,
                merged_full_text=transcript.merged_full_text,
                transcript=transcript.transcript,
                merged_transcript=transcript.merged_transcript,
            )


def _collected_research_to_result(research: NotebookLMCollectedResearch) -> NotebookLMWorkflowResult:
    return NotebookLMWorkflowResult(
        notebook_id=research.notebook_id,
        source_id=research.source_id,
        source_status=research.source_status,
        answer=research.answer,
        conversation_id=research.conversation_id,
        citations=[
            {
                "citation_number": item.citation_number,
                "source_id": item.source_id,
                "title": item.title,
                "url": item.url,
                "cited_text": item.cited_text,
            }
            for item in research.citations
        ],
        status="success",
        reason="",
        source_of_truth=research.source_of_truth,
    )
