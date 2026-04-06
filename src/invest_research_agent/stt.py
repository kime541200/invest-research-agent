from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import os
import subprocess
import tempfile
from typing import Any
from urllib.parse import quote

import httpx
from dotenv import load_dotenv
from imageio_ffmpeg import get_ffmpeg_exe

from invest_research_agent.models import TranscriptBundle, TranscriptSegment


@dataclass(frozen=True)
class SttSettings:
    provider: str
    base_url: str
    model: str
    api_key: str | None = None
    timeout: float = 300.0
    language: str | None = None
    max_upload_bytes: int = 24 * 1024 * 1024
    target_chunk_bytes: int = 24 * 1024 * 1024
    transcode_bitrate: str = "32k"
    transcode_sample_rate: int = 16000
    segment_seconds: int = 1800
    always_preprocess: bool = False
    response_format: str = "verbose_json"

    @property
    def is_enabled(self) -> bool:
        return bool(self.provider and self.base_url and self.model)


@dataclass(frozen=True)
class SttHealthStatus:
    ok: bool
    provider: str
    message: str


@dataclass(frozen=True)
class PreparedAudioChunk:
    path: Path
    start_offset: float = 0.0


def load_stt_settings(project_root: Path | str | None = None) -> SttSettings | None:
    root = Path(project_root or Path.cwd())
    load_dotenv(root / ".env", override=False)

    provider = os.getenv("STT_PROVIDER", "").strip()
    base_url = os.getenv("STT_BASE_URL", "").strip()
    model = os.getenv("STT_MODEL", "").strip()
    api_key = os.getenv("STT_API_KEY", "").strip() or None
    timeout = float(os.getenv("STT_TIMEOUT", "300") or 300)
    language = os.getenv("STT_LANGUAGE", "").strip() or None
    max_upload_mb = float(os.getenv("STT_MAX_UPLOAD_MB", "24") or 24)
    target_chunk_mb = float(
        os.getenv("STT_TARGET_CHUNK_MB", str(_get_default_target_chunk_mb(provider, max_upload_mb))) or max_upload_mb
    )
    transcode_bitrate = os.getenv("STT_TRANSCODE_BITRATE", "32k").strip() or "32k"
    transcode_sample_rate = int(os.getenv("STT_TRANSCODE_SAMPLE_RATE", "16000") or 16000)
    segment_seconds = int(os.getenv("STT_SEGMENT_SECONDS", "1800") or 1800)
    always_preprocess = os.getenv("STT_ALWAYS_PREPROCESS", "").strip().casefold() in {"1", "true", "yes", "on"}
    response_format = os.getenv("STT_RESPONSE_FORMAT", _get_default_response_format(provider)).strip() or "verbose_json"
    if provider.casefold() == "speaches":
        always_preprocess = True

    settings = SttSettings(
        provider=provider,
        base_url=base_url,
        model=model,
        api_key=api_key,
        timeout=timeout,
        language=language,
        max_upload_bytes=max(int(max_upload_mb * 1024 * 1024), 1),
        target_chunk_bytes=max(int(target_chunk_mb * 1024 * 1024), 1),
        transcode_bitrate=transcode_bitrate,
        transcode_sample_rate=max(transcode_sample_rate, 8000),
        segment_seconds=max(segment_seconds, 60),
        always_preprocess=always_preprocess,
        response_format=response_format,
    )
    return settings if settings.is_enabled else None


def check_stt_provider(settings: SttSettings | None) -> SttHealthStatus:
    if settings is None:
        return SttHealthStatus(ok=False, provider="", message="STT 尚未設定。")

    provider = settings.provider.casefold()
    if provider == "speaches":
        health_url = _build_health_url(settings.base_url)
        try:
            response = httpx.get(health_url, timeout=min(settings.timeout, 10.0))
            if response.status_code != 200:
                return SttHealthStatus(
                    ok=False,
                    provider=settings.provider,
                    message=f"STT 服務健康檢查失敗：{health_url} -> HTTP {response.status_code}",
                )

            model_response = httpx.get(_build_model_url(settings.base_url, settings.model), timeout=min(settings.timeout, 10.0))
            if model_response.status_code == 200:
                return SttHealthStatus(ok=True, provider=settings.provider, message=f"STT 服務與模型已就緒：{settings.model}")
            if model_response.status_code == 404:
                return SttHealthStatus(
                    ok=False,
                    provider=settings.provider,
                    message=f"STT 服務已啟動，但模型尚未安裝：{settings.model}",
                )
            return SttHealthStatus(
                ok=False,
                provider=settings.provider,
                message=f"STT 服務已啟動，但模型檢查失敗：{settings.model} -> HTTP {model_response.status_code}",
            )
        except httpx.HTTPError as exc:
            return SttHealthStatus(ok=False, provider=settings.provider, message=f"無法連線 STT 服務：{exc}")

    missing_fields = _get_missing_cloud_fields(settings)
    if missing_fields:
        joined = ", ".join(missing_fields)
        return SttHealthStatus(
            ok=False,
            provider=settings.provider,
            message=f"雲端 STT 設定不完整，缺少：{joined}",
        )

    return SttHealthStatus(
        ok=True,
        provider=settings.provider,
        message="雲端 STT 設定已齊備；如需進一步驗證，可使用實際音檔進行 smoke test。",
    )


class SttClient:
    def __init__(self, settings: SttSettings) -> None:
        self.settings = settings

    def transcribe(self, audio_path: Path, video_id: str, language: str | None = None) -> TranscriptBundle:
        selected_language = language or self.settings.language
        with tempfile.TemporaryDirectory(prefix="stt-audio-") as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            chunks = _prepare_audio_chunks(audio_path=audio_path, settings=self.settings, temp_dir=temp_dir)
            bundles = [
                _to_transcript_bundle(
                    video_id=video_id,
                    payload=_post_transcription_request(
                        settings=self.settings,
                        audio_path=chunk.path,
                        language=selected_language,
                    ),
                    language=selected_language,
                    start_offset=chunk.start_offset,
                )
                for chunk in chunks
            ]
        return _merge_transcript_bundles(video_id=video_id, language=selected_language, bundles=bundles)


def _build_health_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        normalized = normalized[: -len("/v1")]
    return f"{normalized}/health"


def _build_transcriptions_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/audio/transcriptions"


def _build_model_url(base_url: str, model: str) -> str:
    return f"{base_url.rstrip('/')}/models/{quote(model, safe='')}"


def _get_missing_cloud_fields(settings: SttSettings) -> list[str]:
    missing = []
    if not settings.base_url:
        missing.append("STT_BASE_URL")
    if not settings.model:
        missing.append("STT_MODEL")
    if not settings.api_key:
        missing.append("STT_API_KEY")
    return missing


def _get_default_target_chunk_mb(provider: str, max_upload_mb: float) -> float:
    if provider.casefold() == "speaches":
        return min(max_upload_mb, 8.0)
    return max_upload_mb


def _get_default_response_format(provider: str) -> str:
    if provider.casefold() == "vllm-qwen3-asr":
        return "json"
    return "verbose_json"


def _post_transcription_request(
    settings: SttSettings,
    audio_path: Path,
    language: str | None,
) -> dict[str, Any]:
    headers = {}
    if settings.api_key:
        headers["Authorization"] = f"Bearer {settings.api_key}"

    request_data: dict[str, Any] = {
        "model": settings.model,
        "response_format": settings.response_format,
    }
    if settings.response_format == "verbose_json":
        request_data["timestamp_granularities[]"] = "segment"
    if language:
        request_data["language"] = language

    with audio_path.open("rb") as audio_file:
        files = {"file": (audio_path.name, audio_file)}
        response = httpx.post(
            _build_transcriptions_url(settings.base_url),
            data=request_data,
            files=files,
            headers=headers,
            timeout=settings.timeout,
        )
    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError:
        payload = {"text": response.text}
    return payload


def _prepare_audio_chunks(audio_path: Path, settings: SttSettings, temp_dir: Path) -> list[PreparedAudioChunk]:
    target_chunk_bytes = min(settings.target_chunk_bytes, settings.max_upload_bytes)
    should_preprocess = settings.always_preprocess or audio_path.stat().st_size > target_chunk_bytes
    if not should_preprocess and audio_path.stat().st_size <= settings.max_upload_bytes:
        return [PreparedAudioChunk(path=audio_path)]

    normalized_path = temp_dir / f"{audio_path.stem}.stt.mp3"
    _transcode_audio(
        input_path=audio_path,
        output_path=normalized_path,
        bitrate=settings.transcode_bitrate,
        sample_rate=settings.transcode_sample_rate,
    )
    if not settings.always_preprocess and normalized_path.stat().st_size <= target_chunk_bytes:
        return [PreparedAudioChunk(path=normalized_path)]

    segment_seconds = _calculate_segment_seconds(
        file_size=normalized_path.stat().st_size,
        max_upload_bytes=target_chunk_bytes,
        fallback_segment_seconds=settings.segment_seconds,
    )
    segment_pattern = temp_dir / "chunk_%03d.mp3"
    _segment_audio(
        input_path=normalized_path,
        output_pattern=segment_pattern,
        segment_seconds=segment_seconds,
    )

    chunk_paths = sorted(temp_dir.glob("chunk_*.mp3"))
    if not chunk_paths:
        raise RuntimeError(f"切分音檔失敗：{normalized_path}")
    return [
        PreparedAudioChunk(
            path=chunk_path,
            start_offset=index * float(segment_seconds),
        )
        for index, chunk_path in enumerate(chunk_paths)
    ]


def _transcode_audio(
    input_path: Path,
    output_path: Path,
    bitrate: str,
    sample_rate: int,
) -> None:
    _run_ffmpeg(
        [
            "-y",
            "-i",
            str(input_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-b:a",
            bitrate,
            str(output_path),
        ]
    )
    if not output_path.exists():
        raise RuntimeError(f"轉碼後找不到音檔：{output_path}")


def _segment_audio(input_path: Path, output_pattern: Path, segment_seconds: int) -> None:
    _run_ffmpeg(
        [
            "-y",
            "-i",
            str(input_path),
            "-f",
            "segment",
            "-segment_time",
            str(segment_seconds),
            "-reset_timestamps",
            "1",
            "-c",
            "copy",
            str(output_pattern),
        ]
    )


def _run_ffmpeg(arguments: list[str]) -> None:
    command = [get_ffmpeg_exe(), *arguments]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode == 0:
        return
    stderr = completed.stderr.strip() or completed.stdout.strip() or "未知錯誤"
    raise RuntimeError(f"ffmpeg 執行失敗：{stderr}")


def _calculate_segment_seconds(file_size: int, max_upload_bytes: int, fallback_segment_seconds: int) -> int:
    if file_size <= 0 or max_upload_bytes <= 0:
        return fallback_segment_seconds
    estimated_segments = max(math.ceil(file_size / max_upload_bytes), 1)
    return max(math.ceil(fallback_segment_seconds / estimated_segments), 60)


def _merge_transcript_bundles(
    video_id: str,
    language: str | None,
    bundles: list[TranscriptBundle],
) -> TranscriptBundle:
    if not bundles:
        return TranscriptBundle(video_id=video_id, language=language, status="ok")
    full_text = " ".join(bundle.full_text for bundle in bundles if bundle.full_text).strip()
    segments = [segment for bundle in bundles for segment in bundle.transcript]
    return TranscriptBundle(
        video_id=video_id,
        language=language,
        status="ok",
        source="stt",
        reason=None,
        full_text=full_text,
        merged_full_text=full_text,
        transcript=segments,
        merged_transcript=segments,
    )


def _to_transcript_bundle(
    video_id: str,
    payload: dict[str, Any],
    language: str | None,
    start_offset: float = 0.0,
) -> TranscriptBundle:
    segments = _to_transcript_segments(payload.get("segments", []), start_offset=start_offset)
    full_text = str(payload.get("text", "")).strip()
    if not full_text and segments:
        full_text = " ".join(segment.text for segment in segments if segment.text).strip()

    return TranscriptBundle(
        video_id=video_id,
        language=language,
        status="ok",
        source="stt",
        reason=None,
        full_text=full_text,
        merged_full_text=full_text,
        transcript=segments,
        merged_transcript=segments,
    )


def _to_transcript_segments(items: Any, start_offset: float = 0.0) -> list[TranscriptSegment]:
    if not isinstance(items, list):
        return []

    segments: list[TranscriptSegment] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        raw_start = float(item.get("start", 0.0) or 0.0)
        raw_end = float(item.get("end", raw_start) or raw_start)
        start = raw_start + start_offset
        segments.append(
            TranscriptSegment(
                text=text,
                start=start,
                duration=max(raw_end - raw_start, 0.0),
                timestamp=_format_timestamp(start),
            )
        )
    return segments


def _format_timestamp(seconds: float) -> str:
    total_seconds = max(int(seconds), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
