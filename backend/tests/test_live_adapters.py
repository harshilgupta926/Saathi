import asyncio
import base64

from app import http_tools, provider_adapters


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    response = FakeResponse({})

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, *args, **kwargs):
        return self.response

    async def request(self, method, *args, **kwargs):
        return self.response

    async def post(self, *args, **kwargs):
        return self.response


def test_open_meteo_adapter_preserves_coordinates(monkeypatch):
    FakeClient.response = FakeResponse({
        "current": {"temperature_2m": 31, "precipitation": 0.2},
        "hourly": {"precipitation_probability": [10, 35, 20]},
    })
    monkeypatch.setattr(http_tools.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(http_tools.OpenMeteoWeatherTool().forecast(latitude=28.61, longitude=77.21))
    assert result.ok is True
    assert result.data["latitude"] == 28.61
    assert result.data["longitude"] == 77.21
    assert result.data["rain_probability_pct"] == 35
    assert result.source.name == "Open-Meteo"


def test_mandi_adapter_maps_government_record(monkeypatch):
    FakeClient.response = FakeResponse({
        "records": [{
            "state": "Haryana",
            "district": "Sonipat",
            "market": "Sonipat",
            "commodity": "Wheat",
            "arrival_date": "14/10/2026",
            "min_price": "2100",
            "modal_price": "2250",
            "max_price": "2325",
        }]
    })
    monkeypatch.setattr(http_tools.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(http_tools.DataGovMandiTool(api_key="key", resource_id="resource").price(
        commodity="Wheat", state="Haryana", district="Sonipat"
    ))
    assert result.ok is True
    assert result.data["modal_price"] == 2250
    assert result.data["arrival_date"] == "14/10/2026"
    assert result.data["market"] == "Sonipat"
    assert result.source.name == "Government OGD / AGMARKNET"


def test_sarvam_stt_maps_transcript(monkeypatch):
    FakeClient.response = FakeResponse({"transcript": "सोनीपत मंडी का भाव बताओ"})
    monkeypatch.setattr(provider_adapters.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(provider_adapters.SarvamSpeechToTextProvider("key", "https://example.test").transcribe(
        b"audio", language="hi"
    ))
    assert result.startswith("सोनीपत")


def test_sarvam_tts_decodes_audio(monkeypatch):
    expected = b"RIFF-demo"
    FakeClient.response = FakeResponse({"audios": [base64.b64encode(expected).decode()]})
    monkeypatch.setattr(provider_adapters.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(provider_adapters.SarvamTextToSpeechProvider("key", "https://example.test").synthesize(
        "नमस्ते", language="hi"
    ))
    assert result == expected

def test_exotel_voice_ai_call_sends_destination_and_stream(monkeypatch):
    class ExotelResponse(FakeResponse):
        def __init__(self):
            super().__init__({"Call": {"Sid": "call-123"}})

    captured = {}

    class ExotelClient(FakeClient):
        response = ExotelResponse()

        async def post(self, *args, **kwargs):
            captured["url"] = args[0]
            captured["data"] = kwargs["data"]
            captured["auth"] = kwargs["auth"]
            return self.response

    monkeypatch.setattr(provider_adapters.httpx, "AsyncClient", ExotelClient)
    provider = provider_adapters.ExotelTelephonyProvider(
        account_sid="sid",
        api_key="key",
        api_token="token",
        caller_id="18001234567",
    )
    result = asyncio.run(provider.place_voice_ai_call(
        to="+919999999999",
        stream_url="wss://voice.example.test/stream",
    ))
    assert result == "call-123"
    assert captured["data"]["From"] == "18001234567"
    assert captured["data"]["To"] == "+919999999999"
    assert captured["data"]["StreamUrl"] == "wss://voice.example.test/stream"
    assert captured["data"]["StreamType"] == "bidirectional"

def test_gemini_tool_router_reads_function_call_steps(monkeypatch):
    class GeminiResponse(FakeResponse):
        def __init__(self):
            super().__init__({"steps": [{"type": "function_call", "id": "fc-1", "name": "get_mandi_price", "arguments": {"commodity": "Wheat", "state": "Haryana"}}]})

    class GeminiClient(FakeClient):
        response = GeminiResponse()

    monkeypatch.setattr(provider_adapters.httpx, "AsyncClient", GeminiClient)
    call = asyncio.run(provider_adapters.GeminiToolRouter("key").choose("Sonipat mandi wheat price"))
    assert call is not None
    assert call.name == "get_mandi_price"
    assert call.arguments["commodity"] == "Wheat"
    assert call.call_id == "fc-1"


def test_sarvam_stt_sends_keyterms(monkeypatch):
    captured = {}
    class STTClient(FakeClient):
        async def request(self, method, *args, **kwargs):
            captured["data"] = kwargs.get("data")
            return FakeResponse({"transcript": "गेहूं"})
    monkeypatch.setattr(provider_adapters.httpx, "AsyncClient", STTClient)
    asyncio.run(provider_adapters.SarvamSpeechToTextProvider(
        "key", "https://example.test", keyterms=["Sonipat", "गेहूं"]
    ).transcribe(b"audio", language="hi"))
    import json
    keyterms = json.loads(captured["data"]["keyterms"])
    assert keyterms == ["Sonipat", "गेहूं"]


def test_realtime_tts_accepts_only_supported_telephony_rates():
    from app.provider_adapters import SarvamRealtimeTTSProvider
    provider = SarvamRealtimeTTSProvider(api_key="key", sample_rate=8000)
    assert provider.sample_rate == 8000
    try:
        SarvamRealtimeTTSProvider(api_key="key", sample_rate=11025)
    except ValueError as exc:
        assert str(exc) == "sarvam_tts_unsupported_sample_rate"
    else:
        raise AssertionError("unsupported sample rate was accepted")


def test_exotel_voice_ai_requires_secure_stream_url():
    provider = provider_adapters.ExotelTelephonyProvider(
        account_sid="sid", api_key="key", api_token="token", caller_id="number"
    )
    try:
        asyncio.run(provider.place_voice_ai_call(to="+911234567890", stream_url="ws://unsafe.example"))
    except ValueError as exc:
        assert str(exc) == "Exotel Voice AI StreamUrl must use wss://"
    else:
        raise AssertionError("insecure stream URL was accepted")


def test_mandi_adapter_rejects_stale_observation(monkeypatch):
    FakeClient.response = FakeResponse({
        "records": [{
            "state": "Haryana",
            "district": "Sonipat",
            "market": "Sonipat",
            "commodity": "Wheat",
            "arrival_date": "01/10/2026",
            "modal_price": "2250",
        }]
    })
    monkeypatch.setattr(http_tools.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(http_tools.DataGovMandiTool(api_key="key", resource_id="resource").price(
        commodity="Wheat", state="Haryana", district="Sonipat"
    ))
    assert result.ok is False
    assert result.error_code == "MANDI_STALE_RECORD"
    assert result.source is not None
    assert result.source.freshness_status == "stale"
