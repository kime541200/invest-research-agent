from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Any
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

from info_collector.models import TranscriptBundle, TranscriptSegment


@dataclass(frozen=True)
class SttSettings:
    provider: str
    base_url: str
    model: str
    api_key: str | None = None
    timeout: float = 300.0
    language: str | None = None

    @property
    def is_enabled(self) -> bool:
        return bool(self.provider and self.base_url and self.model)


@dataclass(frozen=True)
class SttHealthStatus:
    ok: bool
    provider: str
    message: str


def load_stt_settings(project_root: Path | str | None = None) -> SttSettings | None:
    root = Path(project_root or Path.cwd())
    load_dotenv(root / ".env", override=False)

    provider = os.getenv("STT_PROVIDER", "").strip()
    base_url = os.getenv("STT_BASE_URL", "").strip()
    model = os.getenv("STT_MODEL", "").strip()
    api_key = os.getenv("STT_API_KEY", "").strip() or None
    timeout = float(os.getenv("STT_TIMEOUT", "300") or 300)
    language = os.getenv("STT_LANGUAGE", "").strip() or None

    settings = SttSettings(
        provider=provider,
        base_url=base_url,
        model=model,
        api_key=api_key,
        timeout=timeout,
        language=language,
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
        headers = {}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"

        request_data: dict[str, Any] = {
            "model": self.settings.model,
            "response_format": "verbose_json",
            "timestamp_granularities[]": "segment",
        }
        selected_language = language or self.settings.language
        if selected_language:
            request_data["language"] = selected_language

        with audio_path.open("rb") as audio_file:
            files = {"file": (audio_path.name, audio_file)}
            response = httpx.post(
                _build_transcriptions_url(self.settings.base_url),
                data=request_data,
                files=files,
                headers=headers,
                timeout=self.settings.timeout,
            )
        response.raise_for_status()

        try:
            payload = response.json()
        except ValueError:
            payload = {"text": response.text}

        return _to_transcript_bundle(video_id=video_id, payload=payload, language=selected_language)


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


def _to_transcript_bundle(video_id: str, payload: dict[str, Any], language: str | None) -> TranscriptBundle:
    segments = _to_transcript_segments(payload.get("segments", []))
    full_text = str(payload.get("text", "")).strip()
    if not full_text and segments:
        full_text = " ".join(segment.text for segment in segments if segment.text).strip()

    return TranscriptBundle(
        video_id=video_id,
        language=language,
        status="ok",
        reason=None,
        full_text=full_text,
        merged_full_text=full_text,
        transcript=segments,
        merged_transcript=segments,
    )


def _to_transcript_segments(items: Any) -> list[TranscriptSegment]:
    if not isinstance(items, list):
        return []

    segments: list[TranscriptSegment] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        start = float(item.get("start", 0.0) or 0.0)
        end = float(item.get("end", start) or start)
        segments.append(
            TranscriptSegment(
                text=text,
                start=start,
                duration=max(end - start, 0.0),
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
