from __future__ import annotations

from pathlib import Path

import httpx

from info_collector.stt import SttClient, SttSettings, check_stt_provider, load_stt_settings


class _FakeGetResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code


class _FakePostResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_load_stt_settings_from_environment(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("STT_PROVIDER", "speaches")
    monkeypatch.setenv("STT_BASE_URL", "http://localhost:8089/v1")
    monkeypatch.setenv("STT_MODEL", "Systran/faster-whisper-small")
    monkeypatch.setenv("STT_API_KEY", "")
    monkeypatch.setenv("STT_TIMEOUT", "123")
    monkeypatch.setenv("STT_LANGUAGE", "zh")

    settings = load_stt_settings(tmp_path)

    assert settings is not None
    assert settings.provider == "speaches"
    assert settings.base_url == "http://localhost:8089/v1"
    assert settings.model == "Systran/faster-whisper-small"
    assert settings.timeout == 123.0
    assert settings.language == "zh"


def test_check_stt_provider_for_local_speaches(monkeypatch) -> None:
    settings = SttSettings(
        provider="speaches",
        base_url="http://localhost:8089/v1",
        model="Systran/faster-whisper-small",
    )

    monkeypatch.setattr(httpx, "get", lambda url, timeout: _FakeGetResponse())  # noqa: ARG005

    health = check_stt_provider(settings)

    assert health.ok is True
    assert "模型已就緒" in health.message


def test_check_stt_provider_for_local_speaches_detects_missing_model(monkeypatch) -> None:
    settings = SttSettings(
        provider="speaches",
        base_url="http://localhost:8089/v1",
        model="Systran/faster-whisper-small",
    )

    responses = iter([_FakeGetResponse(200), _FakeGetResponse(404)])
    monkeypatch.setattr(httpx, "get", lambda url, timeout: next(responses))  # noqa: ARG005

    health = check_stt_provider(settings)

    assert health.ok is False
    assert "模型尚未安裝" in health.message


def test_check_stt_provider_for_cloud_requires_api_key() -> None:
    settings = SttSettings(
        provider="groq",
        base_url="https://api.groq.com/openai/v1",
        model="whisper-large-v3",
    )

    health = check_stt_provider(settings)

    assert health.ok is False
    assert "STT_API_KEY" in health.message


def test_stt_client_transcribe_normalizes_segments(monkeypatch, tmp_path: Path) -> None:
    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"fake")

    settings = SttSettings(
        provider="speaches",
        base_url="http://localhost:8089/v1",
        model="Systran/faster-whisper-small",
        language="zh",
    )

    monkeypatch.setattr(
        httpx,
        "post",
        lambda *args, **kwargs: _FakePostResponse(  # noqa: ARG005
            {
                "text": "第一句 第二句",
                "segments": [
                    {"start": 0.0, "end": 1.5, "text": "第一句"},
                    {"start": 2.0, "end": 4.0, "text": "第二句"},
                ],
            }
        ),
    )

    transcript = SttClient(settings).transcribe(audio_path=audio_path, video_id="video-1")

    assert transcript.status == "ok"
    assert transcript.full_text == "第一句 第二句"
    assert len(transcript.transcript) == 2
    assert transcript.transcript[0].timestamp == "00:00"
