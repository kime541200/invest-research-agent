from __future__ import annotations

from pathlib import Path

from invest_research_agent.audio_downloader import AudioDownloader
from invest_research_agent.models import ChannelConfig, TranscriptBundle, TranscriptSegment, VideoMetadata
from invest_research_agent.note_generator import MarkdownNoteGenerator
from invest_research_agent.notebooklm_enricher import NotebookLMCollectedResearch
from invest_research_agent.notebooklm_gateway import NotebookLMCitation
from invest_research_agent.orchestrator import CollectorOrchestrator
from invest_research_agent.research_models import ResearchEvidence, ResearchNoteSections
from invest_research_agent.state_store import ResourceStateStore
from invest_research_agent.stt import SttClient, SttSettings
from invest_research_agent.topic_router import TopicRouter


class FakeYouTubeGateway:
    def list_recent_videos(self, channel, max_results: int = 5):  # noqa: ANN001
        videos = [
            VideoMetadata(
                channel_name=channel.name,
                channel_id="UC123",
                video_id="video-new",
                title="新影片",
                url="https://www.youtube.com/watch?v=video-new",
                published_at="2026-04-06T08:00:00Z",
            ),
            VideoMetadata(
                channel_name=channel.name,
                channel_id="UC123",
                video_id="video-old",
                title="舊影片",
                url="https://www.youtube.com/watch?v=video-old",
                published_at="2026-04-05T08:00:00Z",
            ),
        ]
        return "UC123", videos[:max_results]

    def get_transcript(self, video_id: str, language: str | None = None) -> TranscriptBundle:
        return TranscriptBundle(
            video_id=video_id,
            language=language or "zh-TW",
            full_text="這是逐字稿摘要。 補充第二個重點。",
            merged_full_text="這是逐字稿摘要，補充第二個重點。",
            transcript=[
                TranscriptSegment(text="這是逐字稿摘要。", start=0.0, duration=2.0, timestamp="0:00"),
                TranscriptSegment(text="補充第二個重點。", start=10.0, duration=2.0, timestamp="0:10"),
            ],
            merged_transcript=[
                TranscriptSegment(text="這是逐字稿摘要，補充第二個重點。", start=0.0, duration=12.0, timestamp="0:00"),
            ],
        )


class FakeUnavailableYouTubeGateway(FakeYouTubeGateway):
    def get_transcript(self, video_id: str, language: str | None = None) -> TranscriptBundle:
        del language
        return TranscriptBundle(
            video_id=video_id,
            language=None,
            status="unavailable",
            reason="transcripts_disabled",
        )


class FakeNotebookLMEnricher:
    def collect_video_research(self, *, topic: str, channel: ChannelConfig, video: VideoMetadata):  # noqa: ANN001
        del topic, channel
        return NotebookLMCollectedResearch(
            notebook_id="nb-1",
            source_id="src-1",
            source_status="ready",
            answer="影片主要談 AI 與新創的最新觀察。",
            conversation_id="conv-1",
            citations=[
                NotebookLMCitation(
                    citation_number=1,
                    source_id="src-1",
                    title=video.title,
                    url=video.url,
                    cited_text="影片提到 AI 新創與商業模式的最新變化。",
                )
            ],
            evidence=[
                ResearchEvidence(
                    title=video.title,
                    source="NotebookLM",
                    summary="影片提到 AI 新創與商業模式的最新變化。",
                    url=video.url,
                    score=5.0,
                )
            ],
            research_sections=ResearchNoteSections(
                core_conclusion="影片主要談 AI 與新創的最新觀察。",
                key_points=["影片提到 AI 新創與商業模式的最新變化。"],
                answered_questions=["這支影片的核心重點是什麼？"],
                evidence_points=["影片提到 AI 新創與商業模式的最新變化。"],
                limitations=[],
                follow_up_questions=[],
            ),
        )


class FakeFailingNotebookLMEnricher:
    def collect_video_research(self, *, topic: str, channel: ChannelConfig, video: VideoMetadata):  # noqa: ANN001
        del topic, channel, video
        raise RuntimeError("NotebookLM unavailable")


class FakeAudioDownloader(AudioDownloader):
    def __init__(self, audio_path: Path) -> None:
        self.audio_path = audio_path
        self.success_paths: list[Path] = []

    def download_audio(self, video: VideoMetadata) -> Path:
        del video
        return self.audio_path

    def handle_success(self, audio_path: Path) -> None:
        self.success_paths.append(audio_path)


class FakeSttClient(SttClient):
    def __init__(self) -> None:
        super().__init__(
            SttSettings(
                provider="speaches",
                base_url="http://localhost:8089/v1",
                model="Systran/faster-whisper-small",
                language="zh",
            )
        )

    def transcribe(self, audio_path: Path, video_id: str, language: str | None = None) -> TranscriptBundle:
        del audio_path, language
        return TranscriptBundle(
            video_id=video_id,
            language="zh",
            status="ok",
            source="stt",
            full_text="這是 STT fallback 逐字稿。",
            merged_full_text="這是 STT fallback 逐字稿。",
            transcript=[
                TranscriptSegment(text="這是 STT fallback 逐字稿。", start=0.0, duration=3.0, timestamp="0:00"),
            ],
            merged_transcript=[
                TranscriptSegment(text="這是 STT fallback 逐字稿。", start=0.0, duration=3.0, timestamp="0:00"),
            ],
        )


def test_orchestrator_collects_and_updates_state(tmp_path: Path) -> None:
    resource_file = tmp_path / "resources.yaml"
    resource_file.write_text(
        """
yt_channels:
  inside6202:
    url: https://www.youtube.com/@inside6202
    alias:
      - Inside
    tags:
      - 科技
      - AI
    topic_keywords:
      - 新創
    watch_tier: normal
channel_state:
  inside6202:
    last_checked_video_title: 舊影片
""".strip()
        + "\n",
        encoding="utf-8",
    )

    orchestrator = CollectorOrchestrator(
        state_store=ResourceStateStore(resource_file),
        topic_router=TopicRouter(),
        video_gateway=FakeYouTubeGateway(),
        note_generator=MarkdownNoteGenerator(),
        notes_root=tmp_path / "notes",
        notebooklm_enricher=FakeNotebookLMEnricher(),
    )

    result = orchestrator.collect_from_topic("我想看 AI 與新創", max_channels=1)

    assert len(result.channel_results) == 1
    channel_result = result.channel_results[0]
    assert channel_result.status == "processed"
    assert channel_result.new_videos[0].title == "新影片"
    assert channel_result.transcript_paths == []
    assert channel_result.analysis_paths == []
    assert channel_result.research_paths[0].suffix == ".json"
    assert channel_result.note_paths[0].exists()
    assert channel_result.note_paths[0].parent.name == "我想看_AI_與新創"
    note_content = channel_result.note_paths[0].read_text(encoding="utf-8")
    assert "影片主要談 AI 與新創的最新觀察。" in note_content
    assert channel_result.notebooklm_results[0].status == "success"
    assert channel_result.notebooklm_results[0].source_of_truth == "notebooklm"

    reloaded = ResourceStateStore(resource_file).get_channel("inside6202")
    assert reloaded is not None
    assert reloaded.last_checked_video_title == "新影片"


def test_orchestrator_uses_stt_fallback_when_native_transcript_unavailable(tmp_path: Path) -> None:
    resource_file = tmp_path / "resources.yaml"
    resource_file.write_text(
        """
yt_channels:
  inside6202:
    url: https://www.youtube.com/@inside6202
    tags:
      - AI
channel_state:
  inside6202:
    last_checked_video_title: 舊影片
""".strip()
        + "\n",
        encoding="utf-8",
    )
    fake_audio_path = tmp_path / "video-new.m4a"
    fake_audio_path.write_bytes(b"audio")
    fake_downloader = FakeAudioDownloader(fake_audio_path)

    orchestrator = CollectorOrchestrator(
        state_store=ResourceStateStore(resource_file),
        topic_router=TopicRouter(),
        video_gateway=FakeUnavailableYouTubeGateway(),
        note_generator=MarkdownNoteGenerator(),
        notes_root=tmp_path / "notes",
        audio_downloader=fake_downloader,
        stt_client=FakeSttClient(),
        notebooklm_enricher=FakeFailingNotebookLMEnricher(),
    )

    result = orchestrator.collect_from_topic("AI", max_channels=1)

    note_content = result.channel_results[0].note_paths[0].read_text(encoding="utf-8")
    assert "STT fallback 逐字稿" in note_content
    assert "- **字幕來源：** STT fallback" in note_content
    assert result.channel_results[0].transcript_paths[0].exists()
    assert result.channel_results[0].analysis_paths[0].exists()
    assert result.channel_results[0].notebooklm_results[0].status == "fallback"
    assert fake_downloader.success_paths == [fake_audio_path]
