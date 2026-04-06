from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import os
from pathlib import Path

from dotenv import load_dotenv
from yt_dlp import YoutubeDL

from info_collector.models import VideoMetadata


@dataclass(frozen=True)
class AudioCacheSettings:
    policy: str = "ttl"
    ttl_days: int = 7


class AudioDownloader:
    def __init__(self, cache_root: Path | str, cache_settings: AudioCacheSettings | None = None) -> None:
        self.cache_root = Path(cache_root)
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self.cache_settings = cache_settings or AudioCacheSettings()
        self.prune_cache()

    def download_audio(self, video: VideoMetadata) -> Path:
        cached_file = _get_cached_audio_path(self.cache_root, video.video_id)
        if cached_file is not None:
            return cached_file

        outtmpl = str(self.cache_root / f"{video.video_id}.%(ext)s")
        options = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "restrictfilenames": True,
        }

        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(video.url, download=True)
            filename = Path(ydl.prepare_filename(info))

        if filename.exists():
            return filename

        cached_file = _get_cached_audio_path(self.cache_root, video.video_id)
        if cached_file is not None:
            return cached_file

        raise RuntimeError(f"找不到已下載的音訊檔：{video.video_id}")

    def handle_success(self, audio_path: Path) -> None:
        if self.cache_settings.policy == "delete-on-success" and audio_path.exists():
            audio_path.unlink()

    def prune_cache(self) -> None:
        if self.cache_settings.policy != "ttl":
            return

        expiration = datetime.now() - timedelta(days=self.cache_settings.ttl_days)
        for candidate in self.cache_root.glob("*"):
            if not candidate.is_file():
                continue
            modified_at = datetime.fromtimestamp(candidate.stat().st_mtime)
            if modified_at < expiration:
                candidate.unlink()


def load_audio_cache_settings(project_root: Path | str | None = None) -> AudioCacheSettings:
    root = Path(project_root or Path.cwd())
    load_dotenv(root / ".env", override=False)

    policy = os.getenv("AUDIO_CACHE_POLICY", "ttl").strip().casefold() or "ttl"
    if policy not in {"keep", "delete-on-success", "ttl"}:
        policy = "ttl"

    ttl_raw = os.getenv("AUDIO_CACHE_TTL_DAYS", "7").strip() or "7"
    try:
        ttl_days = int(ttl_raw)
    except ValueError:
        ttl_days = 7
    if ttl_days < 0:
        ttl_days = 7

    return AudioCacheSettings(policy=policy, ttl_days=ttl_days)


def _get_cached_audio_path(cache_root: Path, video_id: str) -> Path | None:
    for candidate in sorted(cache_root.glob(f"{video_id}.*")):
        if candidate.is_file():
            return candidate
    return None
