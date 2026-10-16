from dataclasses import dataclass

from .config import Settings
from .orchestrator import AgentContext, AgentOutcome, Orchestrator
from .provider_adapters import SafeProviderFactory
from .local_speech import EspeakHindiTextToSpeechProvider, VoskHindiSpeechToTextProvider
from .schemas import LocationContext


@dataclass(frozen=True)
class VoiceTurn:
    transcript: str
    outcome: AgentOutcome
    audio: bytes | None


class VoiceGateway:
    def __init__(self, settings: Settings, orchestrator: Orchestrator) -> None:
        self.orchestrator = orchestrator
        provider = (settings.speech_provider or "local").casefold()
        if provider == "local":
            self.stt = VoskHindiSpeechToTextProvider(
                settings.vosk_model_path,
                ffmpeg_binary=settings.ffmpeg_binary,
                timeout_seconds=settings.local_speech_timeout_seconds,
            )
            self.tts = EspeakHindiTextToSpeechProvider(
                binary=settings.espeak_ng_binary,
                timeout_seconds=settings.local_speech_timeout_seconds,
            )
        elif provider == "sarvam":
            self.stt = SafeProviderFactory.sarvam_stt(
                settings.sarvam_api_key,
                settings.sarvam_stt_endpoint,
                settings.sarvam_stt_model,
                keyterms=["Sonipat", "सोनीपत", "Haryana", "हरियाणा", "Wheat", "गेहूं", "Mandi", "मंडी"],
            )
            self.tts = SafeProviderFactory.sarvam_tts(
                settings.sarvam_api_key,
                settings.sarvam_tts_endpoint,
                settings.sarvam_tts_model,
                settings.sarvam_tts_speaker,
            )
        else:
            # Unknown provider names disable speech rather than silently choosing a hosted service.
            self.stt = None
            self.tts = None

    async def handle(self, audio: bytes, *, language: str, household_id: str | None, location: LocationContext | None = None) -> VoiceTurn:
        if self.stt is None:
            raise RuntimeError("speech_to_text_provider_not_configured")
        transcript = await self.stt.transcribe(audio, language=language)
        if not transcript:
            raise ValueError("empty_transcript")
        outcome = await self.orchestrator.handle(
            transcript,
            AgentContext(household_id=household_id, language=language, location=location),
        )
        audio_out = await self.tts.synthesize(outcome.reply, language=language) if self.tts else None
        return VoiceTurn(transcript=transcript, outcome=outcome, audio=audio_out)
