"""Offline Hindi speech adapters using a local Vosk model and eSpeak NG.

No network calls or hosted speech credentials are used. The Vosk model is an
operator-installed artifact and is not downloaded at runtime.
"""
import asyncio
import json
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path


MAX_AUDIO_BYTES = 8_000_000
MAX_AUDIO_SECONDS = 60
SAMPLE_RATE = 16_000


class LocalSpeechError(RuntimeError):
    """Safe, non-sensitive local speech failure."""


@lru_cache(maxsize=2)
def _load_vosk_model(model_path: str):
    from vosk import Model

    path = Path(model_path)
    if not path.is_dir() or not (path / "am").exists():
        raise LocalSpeechError("local_stt_model_unavailable")
    try:
        return Model(str(path))
    except Exception as exc:
        raise LocalSpeechError("local_stt_model_load_failed") from exc


def _decode_audio(audio: bytes, *, ffmpeg_binary: str, timeout_seconds: float) -> bytes:
    if not audio:
        raise ValueError("empty_audio")
    if len(audio) > MAX_AUDIO_BYTES:
        raise ValueError("audio_too_large")
    executable = shutil.which(ffmpeg_binary)
    if not executable:
        raise LocalSpeechError("local_audio_decoder_unavailable")
    try:
        result = subprocess.run(
            [
                executable, "-nostdin", "-hide_banner", "-loglevel", "error",
                "-i", "pipe:0", "-t", str(MAX_AUDIO_SECONDS + 1),
                "-ar", str(SAMPLE_RATE), "-ac", "1", "-f", "s16le", "pipe:1",
            ],
            input=audio,
            capture_output=True,
            timeout=max(1.0, min(float(timeout_seconds), 25.0)),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise LocalSpeechError("local_audio_decode_timeout") from exc
    except OSError as exc:
        raise LocalSpeechError("local_audio_decoder_failed") from exc
    if result.returncode != 0 or not result.stdout:
        raise LocalSpeechError("local_audio_decode_failed")
    max_pcm_bytes = SAMPLE_RATE * 2 * MAX_AUDIO_SECONDS
    if len(result.stdout) > max_pcm_bytes:
        raise ValueError("audio_too_long")
    return result.stdout


def _transcribe_sync(audio: bytes, *, model_path: str, ffmpeg_binary: str, timeout_seconds: float) -> str:
    pcm = _decode_audio(audio, ffmpeg_binary=ffmpeg_binary, timeout_seconds=timeout_seconds)
    try:
        from vosk import KaldiRecognizer
        model = _load_vosk_model(model_path)
        recognizer = KaldiRecognizer(model, SAMPLE_RATE)
        for offset in range(0, len(pcm), 4000):
            recognizer.AcceptWaveform(pcm[offset : offset + 4000])
        payload = json.loads(recognizer.FinalResult())
    except LocalSpeechError:
        raise
    except Exception as exc:
        raise LocalSpeechError("local_stt_failed") from exc
    transcript = str(payload.get("text") or "").strip()
    return transcript


class VoskHindiSpeechToTextProvider:
    """Offline STT for Hindi audio using the operator-installed Vosk Hindi model."""

    def __init__(
        self,
        model_path: str,
        *,
        ffmpeg_binary: str = "ffmpeg",
        timeout_seconds: float = 15.0,
    ) -> None:
        self.model_path = model_path
        self.ffmpeg_binary = ffmpeg_binary
        self.timeout_seconds = max(1.0, min(float(timeout_seconds), 25.0))

    async def transcribe(self, audio: bytes, *, language: str) -> str:
        if language and language.casefold() not in {"hi", "hi-in", "unknown", "hinglish"}:
            raise ValueError("local_stt_language_not_supported")
        return await asyncio.to_thread(
            _transcribe_sync,
            audio,
            model_path=self.model_path,
            ffmpeg_binary=self.ffmpeg_binary,
            timeout_seconds=self.timeout_seconds,
        )


class EspeakHindiTextToSpeechProvider:
    """Offline speech synthesis through the local eSpeak NG executable."""

    def __init__(self, *, binary: str = "espeak-ng", timeout_seconds: float = 10.0) -> None:
        self.binary = binary
        self.timeout_seconds = max(1.0, min(float(timeout_seconds), 20.0))

    async def synthesize(self, text: str, *, language: str) -> bytes:
        clean_text = " ".join(str(text).split())[:2500]
        if not clean_text:
            raise ValueError("empty_speech_text")
        lang = (language or "hi").casefold()
        if lang not in {"hi", "hi-in", "unknown", "hinglish", "en", "en-in", "en-us"}:
            raise ValueError("local_tts_language_not_supported")
        voice = "en" if lang in {"en", "en-in", "en-us"} else "hi"
        executable = shutil.which(self.binary)
        if not executable:
            raise LocalSpeechError("local_tts_engine_unavailable")
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [executable, "--stdout", "-v", voice, "--", clean_text],
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise LocalSpeechError("local_tts_timeout") from exc
        except OSError as exc:
            raise LocalSpeechError("local_tts_execution_failed") from exc
        if result.returncode != 0 or not result.stdout:
            raise LocalSpeechError("local_tts_execution_failed")
        return result.stdout
