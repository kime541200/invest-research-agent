from __future__ import annotations

import os
from pathlib import Path
import time

import invest_research_agent.audio_downloader as audio_downloader_module
from invest_research_agent.audio_downloader import AudioCacheSettings, AudioDownloader, load_audio_cache_settings
from invest_research_agent.models import VideoMetadata


def test_audio_downloader_reuses_cached_file(tmp_path: Path) -> None:
    cached_file = tmp_path / "video-1.webm"
    cached_file.write_bytes(b"audio")

    downloader = AudioDownloader(tmp_path)
    video = VideoMetadata(
        channel_name="inside6202",
        channel_id="UC123",
        video_id="video-1",
        title="新影片",
        url="https://www.youtube.com/watch?v=video-1",
    )

    path = downloader.download_audio(video)

    assert path == cached_file


def test_audio_downloader_downloads_when_cache_missing(monkeypatch, tmp_path: Path) -> None:
    downloaded_path = tmp_path / "video-2.m4a"

    class _FakeYoutubeDL:
        def __init__(self, options: dict) -> None:
            self.options = options

        def __enter__(self) -> "_FakeYoutubeDL":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
            return None

        def extract_info(self, url: str, download: bool) -> dict[str, str]:
            assert download is True
            assert url == "https://www.youtube.com/watch?v=video-2"
            downloaded_path.write_bytes(b"audio")
            return {"id": "video-2", "ext": "m4a"}

        def prepare_filename(self, info: dict[str, str]) -> str:
            assert info["id"] == "video-2"
            return str(downloaded_path)

    monkeypatch.setattr(audio_downloader_module, "YoutubeDL", _FakeYoutubeDL)

    downloader = AudioDownloader(tmp_path)
    video = VideoMetadata(
        channel_name="inside6202",
        channel_id="UC123",
        video_id="video-2",
        title="新影片",
        url="https://www.youtube.com/watch?v=video-2",
    )

    path = downloader.download_audio(video)

    assert path == downloaded_path


def test_audio_downloader_prunes_expired_files_for_ttl_policy(tmp_path: Path) -> None:
    expired_file = tmp_path / "old-video.m4a"
    expired_file.write_bytes(b"audio")
    fresh_file = tmp_path / "new-video.m4a"
    fresh_file.write_bytes(b"audio")

    now = time.time()
    ten_days_ago = now - (10 * 24 * 60 * 60)
    os.utime(expired_file, (ten_days_ago, ten_days_ago))

    AudioDownloader(tmp_path, cache_settings=AudioCacheSettings(policy="ttl", ttl_days=7))

    assert not expired_file.exists()
    assert fresh_file.exists()


def test_audio_downloader_deletes_audio_on_success_when_requested(tmp_path: Path) -> None:
    audio_path = tmp_path / "video-3.m4a"
    audio_path.write_bytes(b"audio")
    downloader = AudioDownloader(
        tmp_path,
        cache_settings=AudioCacheSettings(policy="delete-on-success", ttl_days=7),
    )

    downloader.handle_success(audio_path)

    assert not audio_path.exists()


def test_load_audio_cache_settings_defaults_to_ttl(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("AUDIO_CACHE_POLICY", raising=False)
    monkeypatch.delenv("AUDIO_CACHE_TTL_DAYS", raising=False)

    settings = load_audio_cache_settings(tmp_path)

    assert settings.policy == "ttl"
    assert settings.ttl_days == 7
