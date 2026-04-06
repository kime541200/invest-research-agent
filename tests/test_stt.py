from __future__ import annotations

from pathlib import Path

import httpx

from invest_research_agent.stt import (
    PreparedAudioChunk,
    SttClient,
    SttSettings,
    _calculate_segment_seconds,
    _get_default_target_chunk_mb,
    _get_default_response_format,
    _to_transcript_bundle,
    check_stt_provider,
    load_stt_settings,
)


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
    monkeypatch.setenv("STT_MAX_UPLOAD_MB", "12")
    monkeypatch.setenv("STT_TRANSCODE_BITRATE", "24k")
    monkeypatch.setenv("STT_TRANSCODE_SAMPLE_RATE", "22050")
    monkeypatch.setenv("STT_SEGMENT_SECONDS", "900")

    settings = load_stt_settings(tmp_path)

    assert settings is not None
    assert settings.provider == "speaches"
    assert settings.base_url == "http://localhost:8089/v1"
    assert settings.model == "Systran/faster-whisper-small"
    assert settings.timeout == 123.0
    assert settings.language == "zh"
    assert settings.max_upload_bytes == 12 * 1024 * 1024
    assert settings.target_chunk_bytes == 8 * 1024 * 1024
    assert settings.transcode_bitrate == "24k"
    assert settings.transcode_sample_rate == 22050
    assert settings.segment_seconds == 900
    assert settings.always_preprocess is True
    assert settings.response_format == "verbose_json"


def test_get_default_target_chunk_mb_uses_smaller_default_for_speaches() -> None:
    assert _get_default_target_chunk_mb("speaches", 24) == 8.0
    assert _get_default_target_chunk_mb("groq", 24) == 24


def test_get_default_response_format_uses_json_for_vllm_qwen3_asr() -> None:
    assert _get_default_response_format("vllm-qwen3-asr") == "json"
    assert _get_default_response_format("speaches") == "verbose_json"


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
        "invest_research_agent.stt._prepare_audio_chunks",
        lambda audio_path, settings, temp_dir: [PreparedAudioChunk(path=audio_path)],
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


def test_to_transcript_bundle_applies_chunk_offset() -> None:
    bundle = _to_transcript_bundle(
        video_id="video-1",
        payload={
            "text": "第二段字幕",
            "segments": [
                {"text": "第二段字幕", "start": 5.0, "end": 8.0},
            ],
        },
        language="zh",
        start_offset=120.0,
    )

    assert bundle.transcript[0].start == 125.0
    assert bundle.transcript[0].duration == 3.0
    assert bundle.transcript[0].timestamp == "02:05"


def test_calculate_segment_seconds_scales_down_for_large_files() -> None:
    segment_seconds = _calculate_segment_seconds(
        file_size=90 * 1024 * 1024,
        max_upload_bytes=24 * 1024 * 1024,
        fallback_segment_seconds=1800,
    )

    assert segment_seconds == 450


def test_stt_client_merges_multiple_audio_chunks(monkeypatch, tmp_path: Path) -> None:
    source_audio = tmp_path / "input.webm"
    source_audio.write_bytes(b"source-audio")
    chunk_1 = tmp_path / "chunk_001.mp3"
    chunk_2 = tmp_path / "chunk_002.mp3"
    chunk_1.write_bytes(b"chunk-1")
    chunk_2.write_bytes(b"chunk-2")

    monkeypatch.setattr(
        "invest_research_agent.stt._prepare_audio_chunks",
        lambda audio_path, settings, temp_dir: [
            PreparedAudioChunk(path=chunk_1, start_offset=0.0),
            PreparedAudioChunk(path=chunk_2, start_offset=120.0),
        ],
    )

    payloads = iter(
        [
            {
                "text": "第一段",
                "segments": [
                    {"text": "第一段", "start": 0.0, "end": 3.0},
                ],
            },
            {
                "text": "第二段",
                "segments": [
                    {"text": "第二段", "start": 5.0, "end": 9.0},
                ],
            },
        ]
    )
    monkeypatch.setattr(
        "invest_research_agent.stt._post_transcription_request",
        lambda settings, audio_path, language: next(payloads),
    )

    client = SttClient(
        SttSettings(
            provider="groq",
            base_url="https://api.groq.com/openai/v1",
            model="whisper-large-v3-turbo",
            api_key="test-key",
            language="zh",
        )
    )

    bundle = client.transcribe(source_audio, video_id="video-1", language="zh")

    assert bundle.full_text == "第一段 第二段"
    assert len(bundle.transcript) == 2
    assert bundle.transcript[1].start == 125.0
    assert bundle.transcript[1].timestamp == "02:05"
