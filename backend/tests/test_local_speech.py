import asyncio
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from app import local_speech


def test_local_stt_decodes_audio_and_uses_vosk_model(monkeypatch, tmp_path):
    model_path = tmp_path / "vosk-model-small-hi-0.22"
    (model_path / "am").mkdir(parents=True)
    observed = {"chunks": 0}

    class FakeModel:
        def __init__(self, path):
            observed["model_path"] = path

    class FakeRecognizer:
        def __init__(self, model, sample_rate):
            observed["sample_rate"] = sample_rate

        def AcceptWaveform(self, chunk):
            observed["chunks"] += 1
            return False

        def FinalResult(self):
            return json.dumps({"text": "namaste kisan"})

    monkeypatch.setitem(sys.modules, "vosk", SimpleNamespace(Model=FakeModel, KaldiRecognizer=FakeRecognizer))
    monkeypatch.setattr(local_speech, "_decode_audio", lambda audio, **kwargs: b"\x00\x00" * 5000)
    local_speech._load_vosk_model.cache_clear()
    provider = local_speech.VoskHindiSpeechToTextProvider(str(model_path))
    transcript = asyncio.run(provider.transcribe(b"audio bytes", language="hi-IN"))
    assert transcript == "namaste kisan"
    assert observed["model_path"] == str(model_path)
    assert observed["sample_rate"] == 16000
    assert observed["chunks"] >= 2


def test_local_stt_rejects_unsupported_language_before_decode():
    provider = local_speech.VoskHindiSpeechToTextProvider("/missing/model")
    with pytest.raises(ValueError, match="local_stt_language_not_supported"):
        asyncio.run(provider.transcribe(b"audio", language="fr"))


def test_audio_decoder_bounds_input_and_timeout(monkeypatch):
    provider_error = local_speech.LocalSpeechError
    with pytest.raises(ValueError, match="audio_too_large"):
        local_speech._decode_audio(b"x" * (local_speech.MAX_AUDIO_BYTES + 1), ffmpeg_binary="ffmpeg", timeout_seconds=15)

    monkeypatch.setattr(local_speech.shutil, "which", lambda name: "/usr/bin/ffmpeg")

    def timeout_run(command, **kwargs):
        assert kwargs["timeout"] == 25.0
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(local_speech.subprocess, "run", timeout_run)
    with pytest.raises(provider_error, match="local_audio_decode_timeout"):
        local_speech._decode_audio(b"audio", ffmpeg_binary="ffmpeg", timeout_seconds=100)


def test_local_tts_returns_wav_without_network(monkeypatch):
    monkeypatch.setattr(local_speech.shutil, "which", lambda name: "/usr/bin/espeak-ng")
    seen = {}

    def fake_run(command, **kwargs):
        seen["command"] = command
        return subprocess.CompletedProcess(command, 0, stdout=b"RIFFfake-wav", stderr=b"")

    monkeypatch.setattr(local_speech.subprocess, "run", fake_run)
    provider = local_speech.EspeakHindiTextToSpeechProvider()
    result = asyncio.run(provider.synthesize("नमस्ते किसान", language="hi"))
    assert result.startswith(b"RIFF")
    assert seen["command"][0] == "/usr/bin/espeak-ng"
    assert seen["command"][seen["command"].index("-v") + 1] == "hi"
    assert "नमस्ते किसान" in seen["command"]


def test_local_tts_reports_missing_binary(monkeypatch):
    monkeypatch.setattr(local_speech.shutil, "which", lambda name: None)
    provider = local_speech.EspeakHindiTextToSpeechProvider()
    with pytest.raises(local_speech.LocalSpeechError, match="local_tts_engine_unavailable"):
        asyncio.run(provider.synthesize("नमस्ते", language="hi"))


def test_voice_gateway_uses_local_providers_without_hosted_credentials():
    from app.config import Settings
    from app.local_speech import EspeakHindiTextToSpeechProvider, VoskHindiSpeechToTextProvider
    from app.voice import VoiceGateway

    settings = Settings(
        speech_provider="local",
        vosk_model_path="/models/vosk-model-small-hi-0.22",
        ffmpeg_binary="ffmpeg",
        espeak_ng_binary="espeak-ng",
        sarvam_api_key=None,
    )
    gateway = VoiceGateway(settings, orchestrator=object())
    assert isinstance(gateway.stt, VoskHindiSpeechToTextProvider)
    assert isinstance(gateway.tts, EspeakHindiTextToSpeechProvider)


def test_readiness_only_marks_local_speech_available_when_model_and_binaries_exist(monkeypatch):
    import app.main as main
    from fastapi.testclient import TestClient

    monkeypatch.setattr(main.settings, "speech_provider", "local")
    monkeypatch.setattr(main.settings, "vosk_model_path", "/models/vosk-model-small-hi-0.22")
    monkeypatch.setattr(main.settings, "ffmpeg_binary", "ffmpeg")
    monkeypatch.setattr(main.settings, "espeak_ng_binary", "espeak-ng")
    monkeypatch.setattr(main.os.path, "isdir", lambda path: path == "/models/vosk-model-small-hi-0.22")
    monkeypatch.setattr(main.shutil, "which", lambda binary: f"/usr/bin/{binary}" if binary in {"ffmpeg", "espeak-ng"} else None)

    body = TestClient(main.app).get("/health/ready").json()
    assert body["speech_provider"] == "local"
    assert body["provider_contracts"]["speech"] is True
    assert body["provider_contracts"]["offline_stt"] is True
    assert body["provider_contracts"]["offline_tts"] is True
