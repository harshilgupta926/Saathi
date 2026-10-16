import asyncio
import base64
import json
from urllib.parse import quote

import httpx
from websockets.asyncio.client import connect as websocket_connect

from .providers import ReasoningProvider, SpeechToTextProvider, TelephonyProvider, TextToSpeechProvider


class GeminiInteractionsProvider:
    def __init__(self, api_key: str, model: str = "gemini-3.8-flash", timeout_seconds: float = 15.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def respond(self, messages: list[dict[str, str]]) -> str:
        prompt = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages)
        body = {"model": self.model, "input": prompt}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                "https://generativelanguage.googleapis.com/v1beta/interactions",
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json=body,
            )
            response.raise_for_status()
            data = response.json()
        return str(data.get("output_text") or "")


async def _request_with_retry(client, method: str, url: str, *, attempts: int = 3, **kwargs):
    for attempt in range(attempts):
        try:
            response = await client.request(method, url, **kwargs)
            status_code = getattr(response, "status_code", 200)
            if status_code not in {429, 500, 502, 503, 504} or attempt == attempts - 1:
                return response
        except httpx.RequestError:
            if attempt == attempts - 1:
                raise
        await asyncio.sleep(min(2 ** attempt, 4))
    raise RuntimeError("provider_request_failed")


class SarvamSpeechToTextProvider:
    def __init__(self, api_key: str, endpoint: str, model: str = "saaras:v4", mode: str = "transcribe", timeout_seconds: float = 20.0, keyterms: list[str] | None = None) -> None:
        self.api_key, self.endpoint, self.model, self.mode, self.timeout_seconds = api_key, endpoint, model, mode, timeout_seconds
        self.keyterms = tuple(keyterms or ())[:50]

    async def transcribe(self, audio: bytes, *, language: str) -> str:
        language_code = language if language == "unknown" or "-" in language else f"{language}-IN"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await _request_with_retry(
                client, "POST", self.endpoint,
                headers={"api-subscription-key": self.api_key},
                files={"file": ("caller.webm", audio, "audio/webm")},
                data={"model": self.model, "mode": "codemix", "language_code": language_code, "keyterms": json.dumps(list(self.keyterms)) if self.keyterms else None},
            )
            response.raise_for_status()
            payload = response.json()
        return str(payload.get("transcript") or "").strip()


class SarvamTextToSpeechProvider:
    def __init__(self, api_key: str, endpoint: str, model: str = "bulbul:v3", speaker: str = "shubh", timeout_seconds: float = 20.0) -> None:
        self.api_key, self.endpoint, self.model, self.speaker, self.timeout_seconds = api_key, endpoint, model, speaker, timeout_seconds

    async def synthesize(self, text: str, *, language: str) -> bytes:
        language_code = language if language == "unknown" or "-" in language else f"{language}-IN"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await _request_with_retry(
                client, "POST", self.endpoint,
                headers={"api-subscription-key": self.api_key, "Content-Type": "application/json"},
                json={"text": text[:2500], "model": self.model, "speaker": self.speaker, "language_code": language_code, "output_audio_codec": "wav"},
            )
            response.raise_for_status()
            body = response.json()
        audios = body.get("audios") or []
        if not audios:
            raise ValueError("sarvam_tts_returned_no_audio")
        return base64.b64decode(audios[0])


class ConfiguredSpeechToTextProvider:
    def __init__(self, endpoint: str, api_key: str, user_id: str | None = None, timeout_seconds: float = 15.0) -> None:
        self.endpoint, self.api_key, self.user_id, self.timeout_seconds = endpoint, api_key, user_id, timeout_seconds

    async def transcribe(self, audio: bytes, *, language: str) -> str:
        headers = {"Authorization": self.api_key}
        if self.user_id:
            headers["userId"] = self.user_id
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(self.endpoint, headers=headers, files={"audio": ("audio.wav", audio, "audio/wav")}, data={"language": language})
            response.raise_for_status()
            payload = response.json()
        return str(payload.get("text") or payload.get("transcript") or "")


class ConfiguredTextToSpeechProvider:
    def __init__(self, endpoint: str, api_key: str, user_id: str | None = None, timeout_seconds: float = 15.0) -> None:
        self.endpoint, self.api_key, self.user_id, self.timeout_seconds = endpoint, api_key, user_id, timeout_seconds

    async def synthesize(self, text: str, *, language: str) -> bytes:
        headers = {"Authorization": self.api_key, "Content-Type": "application/json"}
        if self.user_id:
            headers["userId"] = self.user_id
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(self.endpoint, headers=headers, json={"text": text, "language": language})
            response.raise_for_status()
        return response.content


class ExotelTelephonyProvider:
    def __init__(self, account_sid: str, api_key: str, api_token: str, caller_id: str, host: str = "api.in.exotel.com", timeout_seconds: float = 10.0) -> None:
        self.account_sid, self.api_key, self.api_token, self.caller_id, self.host, self.timeout_seconds = account_sid, api_key, api_token, caller_id, host, timeout_seconds

    async def place_call(self, *, to: str, callback_url: str) -> str:
        url = f"https://{self.host}/v1/Accounts/{self.account_sid}/Calls/connect"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                url,
                data={"From": self.caller_id, "To": to, "CallerId": self.caller_id, "StatusCallback": callback_url},
                auth=(self.api_key, self.api_token),
            )
            response.raise_for_status()
            payload = response.json()
        return str(payload.get("Call", {}).get("Sid") or "")

    async def place_voice_ai_call(self, *, to: str, stream_url: str, callback_url: str | None = None) -> str:
        if not stream_url.startswith("wss://"):
            raise ValueError("Exotel Voice AI StreamUrl must use wss://")
        url = f"https://{self.host}/v1/Accounts/{self.account_sid}/Calls/connect"
        data = {
            "From": self.caller_id,
            "To": to,
            "CallerId": self.caller_id,
            "StreamUrl": stream_url,
            "StreamType": "bidirectional",
        }
        if callback_url:
            data["StatusCallback"] = callback_url
            data["StatusCallbackEvents[]"] = "terminal"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(url, data=data, auth=(self.api_key, self.api_token))
            response.raise_for_status()
            payload = response.json()
        return str(payload.get("Call", {}).get("Sid") or "")


class SafeProviderFactory:
    @staticmethod
    def gemini(api_key: str | None, model: str) -> ReasoningProvider | None:
        return GeminiInteractionsProvider(api_key, model) if api_key else None

    @staticmethod
    def sarvam_stt(api_key: str | None, endpoint: str, model: str, keyterms: list[str] | None = None) -> SpeechToTextProvider | None:
        return SarvamSpeechToTextProvider(api_key, endpoint, model, keyterms=keyterms) if api_key else None

    @staticmethod
    def sarvam_tts(api_key: str | None, endpoint: str, model: str, speaker: str) -> TextToSpeechProvider | None:
        return SarvamTextToSpeechProvider(api_key, endpoint, model, speaker) if api_key else None


from dataclasses import dataclass

@dataclass(frozen=True)
class GeminiToolCall:
    name: str
    arguments: dict
    call_id: str


class GeminiToolRouter:
    """Stateless Gemini Interactions function-calling boundary.

    The router only chooses a declared tool. Tool execution remains in Saathi,
    so factual authority stays with our adapters.
    """

    TOOLS = [
        {
            "type": "function",
            "name": "get_weather",
            "description": "Retrieve verified weather for caller context.",
            "parameters": {
                "type": "object",
                "properties": {"latitude": {"type": "number"}, "longitude": {"type": "number"}},
                "required": ["latitude", "longitude"],
            },
        },
        {
            "type": "function",
            "name": "get_mandi_price",
            "description": "Retrieve verified daily mandi price data.",
            "parameters": {
                "type": "object",
                "properties": {"commodity": {"type": "string"}, "state": {"type": "string"}, "district": {"type": "string"}},
                "required": ["commodity", "state"],
            },
        },
        {
            "type": "function",
            "name": "request_human",
            "description": "Escalate when the caller asks for a person or automation is unsafe/uncertain.",
            "parameters": {"type": "object", "properties": {"reason": {"type": "string"}}, "required": ["reason"]},
        },
    ]

    def __init__(self, api_key: str, model: str = "gemini-3.8-flash", timeout_seconds: float = 15.0) -> None:
        self.api_key, self.model, self.timeout_seconds = api_key, model, timeout_seconds

    async def choose(self, user_text: str) -> GeminiToolCall | None:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await _request_with_retry(
                client, "POST",
                "https://generativelanguage.googleapis.com/v1beta/interactions",
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "store": False,
                    "input": user_text,
                    "tools": self.TOOLS,
                },
            )
            response.raise_for_status()
            payload = response.json()

        for step in payload.get("steps", []):
            if step.get("type") != "function_call":
                continue
            name = str(step.get("name") or "")
            if name not in {tool["name"] for tool in self.TOOLS}:
                continue
            arguments = step.get("arguments") or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    continue
            if not isinstance(arguments, dict):
                continue
            return GeminiToolCall(
                name=name,
                arguments=arguments,
                call_id=str(step.get("id") or ""),
            )
        return None


class SarvamRealtimeSTTSession:
    """Raw WebSocket transport for Sarvam Realtime STT.

    The session keeps audio streaming independent from turn processing so
    Exotel media can continue arriving while Saathi decides and speaks.
    """

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str = "wss://api.sarvam.ai/speech-to-text-realtime/ws",
        model: str = "saaras:v4",
        language_code: str = "hi-IN",
        stream_type: str = "fast",
        keyterms: list[str] | None = None,
    ) -> None:
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = model
        self.language_code = language_code
        self.stream_type = stream_type
        self.keyterms = tuple(keyterms or ())[:50]
        self._ws = None

    def _url(self, sample_rate: int) -> str:
        if sample_rate not in {8000, 16000}:
            raise ValueError("sarvam_realtime_unsupported_sample_rate")
        params = {
            "model": self.model,
            "language_code": self.language_code,
            "stream_type": self.stream_type,
            "endpointing": "vad",
            "encoding": "linear16",
            "sample_rate": str(sample_rate),
            "mode": "codemix",
        }
        if self.keyterms:
            params["keyterms"] = json.dumps(list(self.keyterms), ensure_ascii=False)
        query = "&".join(f"{quote(str(k))}={quote(str(v))}" for k, v in params.items())
        return f"{self.endpoint}?{query}"

    async def connect(self, *, sample_rate: int) -> None:
        self._ws = await websocket_connect(
            self._url(sample_rate),
            additional_headers={"api-subscription-key": self.api_key},
            ping_interval=20,
            ping_timeout=10,
            max_size=2**20,
        )

    async def send_audio(self, pcm: bytes) -> None:
        if not self._ws:
            raise RuntimeError("sarvam_realtime_not_connected")
        await self._ws.send(json.dumps({
            "event": "audio_input",
            "audio": base64.b64encode(pcm).decode("ascii"),
        }))

    async def receive(self) -> dict:
        if not self._ws:
            raise RuntimeError("sarvam_realtime_not_connected")
        message = await self._ws.recv()
        if isinstance(message, bytes):
            raise ValueError("sarvam_realtime_unexpected_binary_event")
        payload = json.loads(message)
        if not isinstance(payload, dict):
            raise ValueError("sarvam_realtime_invalid_event")
        return payload

    async def end(self) -> None:
        if self._ws is not None:
            await self._ws.send(json.dumps({"event": "end"}))

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None


class SarvamRealtimeTTSProvider:
    """Per-response streaming TTS transport.

    A fresh socket per response makes barge-in cancellation deterministic:
    cancelling the response task closes the socket and discards in-flight audio.
    """

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str = "wss://api.sarvam.ai/text-to-speech/ws",
        model: str = "bulbul:v3",
        speaker: str = "shubh",
        sample_rate: int = 8000,
    ) -> None:
        if sample_rate not in {8000, 16000, 22050, 24000}:
            raise ValueError("sarvam_tts_unsupported_sample_rate")
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = model
        self.speaker = speaker
        self.sample_rate = sample_rate

    async def stream(self, text: str, *, language: str, sample_rate: int | None = None):
        target_rate = sample_rate or self.sample_rate
        if target_rate not in {8000, 16000, 22050, 24000}:
            raise ValueError("sarvam_tts_unsupported_sample_rate")
        uri = (
            f"{self.endpoint}?model={quote(self.model)}&send_completion_event=true"
        )
        ws = await websocket_connect(
            uri,
            additional_headers={"api-subscription-key": self.api_key},
            ping_interval=20,
            ping_timeout=10,
            max_size=2**22,
        )
        try:
            await ws.send(json.dumps({
                "type": "config",
                "data": {
                    "language_code": language if "-" in language else f"{language}-IN",
                    "speaker": self.speaker,
                    "output_audio_codec": "linear16",
                    "speech_sample_rate": target_rate,
                    "min_buffer_size": 40,
                    "max_chunk_length": 200,
                },
            }))
            await ws.send(json.dumps({"type": "text", "data": {"text": text[:2500]}}))
            await ws.send(json.dumps({"type": "flush"}))

            while True:
                raw = await ws.recv()
                if isinstance(raw, bytes):
                    continue
                payload = json.loads(raw)
                if payload.get("type") == "audio":
                    data = payload.get("data") or {}
                    audio = data.get("audio")
                    if audio:
                        yield base64.b64decode(audio)
                elif payload.get("type") == "event":
                    data = payload.get("data") or {}
                    if data.get("event_type") == "final":
                        break
                elif payload.get("type") == "error":
                    raise RuntimeError("sarvam_tts_stream_error")
        finally:
            await ws.close()


class OllamaToolRouter:
    """Local, API-key-free tool selection using Ollama's /api/chat endpoint."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "qwen2.5:3b", timeout_seconds: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = max(1.0, min(float(timeout_seconds), 60.0))

    async def choose(self, message: str):
        tools = [
            {"type": "function", "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            }}
            for tool in GeminiToolRouter.TOOLS
        ]
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "Choose at most one listed tool only when appropriate. Never answer factual questions yourself. If uncertain, return no tool call."},
                        {"role": "user", "content": message[:4000]},
                    ],
                    "tools": tools,
                    "stream": False,
                    "options": {"temperature": 0},
                },
            )
            response.raise_for_status()
            payload = response.json()
        calls = (payload.get("message") or {}).get("tool_calls") or []
        if not calls:
            return None
        function = calls[0].get("function") or {}
        name = function.get("name")
        if name not in {tool["name"] for tool in GeminiToolRouter.TOOLS}:
            return None
        arguments = function.get("arguments") or {}
        if not isinstance(arguments, dict):
            return None
        return GeminiToolCall(name=name, arguments=arguments, call_id="ollama-local")
