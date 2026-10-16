from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    cors_origins: str = "http://localhost:3000"
    supabase_url: str | None = None
    supabase_publishable_key: str | None = None
    supabase_secret_key: str | None = None
    llm_provider: str = "ollama"
    llm_model: str = "qwen2.5:7b"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_timeout_seconds: float = 20.0
    local_ocr_enabled: bool = True
    local_ocr_binary: str = "tesseract"
    local_ocr_timeout_seconds: float = 15.0
    local_ocr_max_bytes: int = 8388608
    gemini_api_key: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    speech_provider: str = "local"
    vosk_model_path: str = "/models/vosk-model-small-hi-0.22"
    ffmpeg_binary: str = "ffmpeg"
    espeak_ng_binary: str = "espeak-ng"
    local_speech_timeout_seconds: float = 15.0
    bhashini_user_id: str | None = None
    bhashini_api_key: str | None = None
    bhashini_stt_endpoint: str | None = None
    bhashini_tts_endpoint: str | None = None
    sarvam_api_key: str | None = None
    sarvam_stt_endpoint: str = "https://api.sarvam.ai/speech-to-text"
    sarvam_stt_model: str = "saaras:v4"
    sarvam_realtime_stt_endpoint: str = "wss://api.sarvam.ai/speech-to-text-realtime/ws"
    sarvam_realtime_stt_enabled: bool = False
    sarvam_realtime_stream_type: str = "fast"
    sarvam_tts_endpoint: str = "https://api.sarvam.ai/text-to-speech"
    sarvam_tts_model: str = "bulbul:v3"
    sarvam_tts_speaker: str = "shubh"
    sarvam_tts_stream_endpoint: str = "wss://api.sarvam.ai/text-to-speech/ws"
    sarvam_tts_stream_sample_rate: int = 8000
    mandi_api_key: str | None = None
    mandi_resource_id: str | None = "9ef84268-d588-465a-a308-a864a43d0070"
    mandi_api_base: str = "https://api.data.gov.in/resource"
    exotel_api_key: str | None = None
    exotel_api_token: str | None = None
    exotel_account_sid: str | None = None
    exotel_subdomain: str = "api.in.exotel.com"
    exotel_virtual_number: str | None = None
    exotel_stream_url: str | None = None
    telephony_callback_url: str | None = None
    telephony_callback_signature_verified: bool = False
    telephony_webhook_secret: str | None = None
    call_api_token: str | None = None
    api_auth_token: str | None = None
    telephony_stream_token: str | None = None
    demo_mode: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
