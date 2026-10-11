from base64 import b64encode
from hmac import compare_digest
from time import perf_counter

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .schemas import AgentRequest, CallRequest, ConversationRequest, ConversationResponse, LocationContext, VoiceTurnResponse
from .orchestrator import AgentContext, Orchestrator
from .rate_limit import InMemoryRateLimiter
from .telephony import HmacWebhookVerifier
from .observability import emit_event, get_correlation_id, metrics_snapshot, record_request, set_correlation_id
from .telephony_voice import SarvamTelephonySpeechProvider
from .provider_adapters import ExotelTelephonyProvider, SarvamRealtimeSTTSession, SarvamRealtimeTTSProvider
from .voice import VoiceGateway
from .voice_bridge import run_exotel_realtime_session, run_exotel_session
from .webhook_events import InMemoryWebhookEventStore, derive_event_id, record_supabase_webhook_event
from .supabase_store import record_conversation_metadata


settings = get_settings()
app = FastAPI(title="Saathi API", version="0.7.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-Saathi-Signature", "X-Provider-Event-ID", "X-Correlation-ID"],
    expose_headers=["X-Correlation-ID"],
)
limiter = InMemoryRateLimiter()
orchestrator = Orchestrator()
webhook_events = InMemoryWebhookEventStore()
voice_gateway = VoiceGateway(settings, orchestrator)


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    incoming = request.headers.get("X-Correlation-ID")
    correlation_id = set_correlation_id(incoming)
    started = perf_counter()
    emit_event("request.started", method=request.method, route=request.url.path)
    try:
        response = await call_next(request)
    except Exception as exc:
        latency_ms = (perf_counter() - started) * 1000
        record_request(request.url.path, 500, latency_ms)
        emit_event("request.failed", method=request.method, route=request.url.path, status_code=500, latency_ms=round(latency_ms, 2), error_type=type(exc).__name__)
        raise
    latency_ms = (perf_counter() - started) * 1000
    record_request(request.url.path, response.status_code, latency_ms)
    emit_event("request.completed", method=request.method, route=request.url.path, status_code=response.status_code, latency_ms=round(latency_ms, 2))
    response.headers["X-Correlation-ID"] = correlation_id
    # API responses should not be MIME-sniffed or embedded by other sites.
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").lower() == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {"status": "ok", "service": "saathi-api", "version": app.version, "demo_mode": settings.demo_mode}


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/metrics")
def metrics() -> dict[str, object]:
    return metrics_snapshot()


@app.get("/health/ready")
def readiness() -> dict[str, object]:
    telephony = bool(
        settings.telephony_webhook_secret
        and settings.exotel_api_key
        and settings.exotel_api_token
        and settings.exotel_account_sid
        and settings.exotel_virtual_number
        and settings.exotel_stream_url
    )
    reasoning = bool(getattr(settings, "gemini_api_key", None) or getattr(settings, "openai_api_key", None))
    mandi = bool(settings.mandi_api_key and settings.mandi_resource_id)
    speech = bool(
        (settings.bhashini_api_key and settings.bhashini_stt_endpoint and settings.bhashini_tts_endpoint)
        or settings.sarvam_api_key
    )
    # The deterministic text agent and Open-Meteo path do not depend on
    # optional LLM/telephony/mandi providers. Readiness therefore reflects
    # actual capability availability instead of requiring every integration.
    return {
        "status": "ready",
        "demo_mode": settings.demo_mode,
        "provider_contracts": {
            "core_agent": True,
            "telephony": telephony,
            "telephony_realtime": bool(telephony and settings.sarvam_realtime_stt_enabled and settings.sarvam_api_key),
            "reasoning": reasoning,
            "mandi": mandi,
            "speech": speech,
            "weather": True,
            "documents": bool(settings.sarvam_api_key),
        },
    }


def _source(outcome):
    if outcome.result and outcome.result.source:
        return {
            "name": outcome.result.source.name,
            "url": outcome.result.source.url,
            "retrieved_at": outcome.result.source.retrieved_at.isoformat(),
            "freshness_note": outcome.result.source.freshness_note,
        }
    return None

def _sources(outcome):
    items = []
    for result in outcome.results:
        if result.source:
            items.append({
                "name": result.source.name,
                "url": result.source.url,
                "retrieved_at": result.source.retrieved_at.isoformat(),
                "freshness_note": result.source.freshness_note,
            })
    return items


@app.post("/api/v1/conversation", response_model=ConversationResponse)
async def conversation(payload: ConversationRequest, request: Request) -> ConversationResponse:
    key = request.client.host if request.client else "unknown"
    if not limiter.allow(key):
        raise HTTPException(status_code=429, detail="rate_limited")
    started = perf_counter()
    outcome = await orchestrator.handle(
        payload.message,
        AgentContext(household_id=payload.household_id, language=payload.language, location=payload.location),
    )
    failed = bool(outcome.result and not outcome.result.ok)
    await record_conversation_metadata(
        household_id=payload.household_id,
        agent_used=outcome.intent,
        tools_called=[outcome.tool_name] if outcome.tool_name else [],
        confidence_score=outcome.confidence,
        language_code=payload.language,
        correlation_id=get_correlation_id(),
        response_class="error" if failed else ("escalated" if outcome.escalated else "answered"),
    )
    return ConversationResponse(
        status="error" if failed else "ok",
        reply=outcome.reply,
        intent=outcome.intent,
        source=_source(outcome),
        sources=_sources(outcome),
        demo=settings.demo_mode,
        correlation_id=get_correlation_id(),
        escalated=outcome.escalated,
        escalation_reason=outcome.escalation_reason,
        confidence=outcome.confidence,
        tool_name=outcome.tool_name,
        latency_ms=round((perf_counter() - started) * 1000, 2),
    )


@app.post("/api/v1/agent", response_model=ConversationResponse)
async def agent(payload: AgentRequest, request: Request) -> ConversationResponse:
    key = request.client.host if request.client else "unknown"
    if not limiter.allow(f"agent:{key}"):
        raise HTTPException(status_code=429, detail="rate_limited")
    started = perf_counter()
    outcome = await orchestrator.handle(
        payload.message,
        AgentContext(household_id=payload.household_id, language=payload.language, location=payload.location),
    )
    failed = bool(outcome.result and not outcome.result.ok)
    await record_conversation_metadata(
        household_id=payload.household_id,
        agent_used=outcome.intent,
        tools_called=[outcome.tool_name] if outcome.tool_name else [],
        confidence_score=outcome.confidence,
        language_code=payload.language,
        correlation_id=get_correlation_id(),
        response_class="error" if failed else ("escalated" if outcome.escalated else "answered"),
    )
    return ConversationResponse(
        status="error" if failed else "ok",
        reply=outcome.reply,
        intent=outcome.intent,
        source=_source(outcome),
        sources=_sources(outcome),
        demo=settings.demo_mode,
        correlation_id=get_correlation_id(),
        escalated=outcome.escalated,
        escalation_reason=outcome.escalation_reason,
        confidence=outcome.confidence,
        tool_name=outcome.tool_name,
        latency_ms=round((perf_counter() - started) * 1000, 2),
    )


@app.post("/api/v1/voice/turn", response_model=VoiceTurnResponse)
async def voice_turn(
    request: Request,
    audio: UploadFile = File(...),
    language: str = Form("hi"),
    household_id: str | None = Form(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    location_label: str | None = Form(None),
) -> VoiceTurnResponse:
    key = request.client.host if request.client else "unknown"
    if not limiter.allow(f"voice:{key}"):
        raise HTTPException(status_code=429, detail="rate_limited")
    allowed_audio_types = {"audio/webm", "audio/wav", "audio/x-wav"}
    if audio.content_type and audio.content_type not in allowed_audio_types:
        raise HTTPException(status_code=415, detail="unsupported_audio_type")
    if len(language) < 2 or len(language) > 20:
        raise HTTPException(status_code=422, detail="invalid_language")
    if household_id is not None and (len(household_id) < 1 or len(household_id) > 120):
        raise HTTPException(status_code=422, detail="invalid_household_id")
    max_audio_bytes = 8_000_000
    raw = await audio.read(max_audio_bytes + 1)
    if not raw:
        raise HTTPException(status_code=422, detail="empty_audio")
    if len(raw) > max_audio_bytes:
        raise HTTPException(status_code=413, detail="audio_too_large")
    location = None
    if latitude is not None or longitude is not None:
        if latitude is None or longitude is None:
            raise HTTPException(status_code=422, detail="location_requires_latitude_and_longitude")
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise HTTPException(status_code=422, detail="invalid_location_coordinates")
        location = LocationContext(latitude=latitude, longitude=longitude, label=location_label)
    started = perf_counter()
    try:
        turn = await voice_gateway.handle(raw, language=language, household_id=household_id, location=location)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="voice_provider_error") from exc

    return VoiceTurnResponse(
        status="ok",
        transcript=turn.transcript,
        reply=turn.outcome.reply,
        intent=turn.outcome.intent,
        audio_base64=b64encode(turn.audio).decode("ascii") if turn.audio else None,
        audio_mime_type="audio/wav" if turn.audio else None,
        source=_source(turn.outcome),
        sources=_sources(turn.outcome),
        demo=settings.demo_mode,
        correlation_id=get_correlation_id(),
        escalated=turn.outcome.escalated,
        escalation_reason=turn.outcome.escalation_reason,
        confidence=turn.outcome.confidence,
        tool_name=turn.outcome.tool_name,
        latency_ms=round((perf_counter() - started) * 1000, 2),
    )


@app.post("/api/v1/calls")
async def place_outbound_call(
    payload: CallRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    if not payload.consent:
        raise HTTPException(status_code=400, detail="explicit_outbound_call_consent_required")
    if not payload.to.replace("+", "").isdigit():
        raise HTTPException(status_code=422, detail="invalid_phone_number")
    if settings.demo_mode and settings.app_env.lower() != "production":
        emit_event("call.demo", channel="exotel", realtime=payload.realtime_voice_ai)
        return {"status": "demo", "call_id": "demo-call-accepted", "provider": "exotel", "realtime": payload.realtime_voice_ai}
    token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    if not settings.call_api_token or not compare_digest(token, settings.call_api_token):
        raise HTTPException(status_code=401, detail="call_api_unauthorized")
    required = (settings.exotel_account_sid, settings.exotel_api_key, settings.exotel_api_token, settings.exotel_virtual_number)
    if not all(required):
        raise HTTPException(status_code=503, detail="telephony_provider_not_configured")
    provider = ExotelTelephonyProvider(
        account_sid=settings.exotel_account_sid,
        api_key=settings.exotel_api_key,
        api_token=settings.exotel_api_token,
        caller_id=settings.exotel_virtual_number,
        host=settings.exotel_subdomain,
    )
    if payload.realtime_voice_ai:
        if not settings.exotel_stream_url:
            raise HTTPException(status_code=503, detail="realtime_stream_not_configured")
        call_id = await provider.place_voice_ai_call(
            to=payload.to,
            stream_url=settings.exotel_stream_url,
            callback_url=payload.callback_url,
        )
    else:
        call_id = await provider.place_call(to=payload.to, callback_url=payload.callback_url)
    emit_event("call.placed", channel="exotel", call_id=call_id, realtime=payload.realtime_voice_ai)
    return {"status": "accepted", "call_id": call_id, "provider": "exotel", "realtime": payload.realtime_voice_ai}


@app.websocket("/api/v1/telephony/stream")
async def telephony_stream(websocket: WebSocket) -> None:
    """Exotel AgentStream endpoint.

    With SARVAM_REALTIME_STT_ENABLED=true this uses Sarvam Realtime STT,
    streaming TTS, server VAD and cancellation-aware barge-in. Otherwise it
    retains the bounded-turn adapter as a safe fallback.
    """
    if not settings.exotel_stream_url or not settings.sarvam_api_key:
        await websocket.close(code=1013, reason="telephony_provider_not_configured")
        return

    await websocket.accept()
    try:
        if settings.sarvam_realtime_stt_enabled:
            realtime_stt = SarvamRealtimeSTTSession(
                api_key=settings.sarvam_api_key,
                endpoint=settings.sarvam_realtime_stt_endpoint,
                model=settings.sarvam_stt_model,
                stream_type=settings.sarvam_realtime_stream_type,
                keyterms=["Sonipat", "सोनीपत", "Haryana", "हरियाणा", "Wheat", "गेहूं", "mandi", "मंडी"],
            )
            realtime_tts = SarvamRealtimeTTSProvider(
                api_key=settings.sarvam_api_key,
                endpoint=settings.sarvam_tts_stream_endpoint,
                model=settings.sarvam_tts_model,
                speaker=settings.sarvam_tts_speaker,
                sample_rate=settings.sarvam_tts_stream_sample_rate,
            )

            async def respond(text: str) -> str:
                outcome = await orchestrator.handle(text, AgentContext(household_id=None, language="hi"))
                return outcome.reply

            async def synthesize_stream(text: str, sample_rate: int):
                async for chunk in realtime_tts.stream(text, language="hi-IN", sample_rate=sample_rate):
                    yield chunk

            await run_exotel_realtime_session(
                websocket,
                stt_session=realtime_stt,
                respond=respond,
                synthesize_stream=synthesize_stream,
            )
            return

        speech = SarvamTelephonySpeechProvider(settings)

        async def transcribe(pcm: bytes, sample_rate: int) -> str:
            return await speech.transcribe(pcm, sample_rate=sample_rate, language="hi-IN")

        async def respond(text: str) -> str:
            outcome = await orchestrator.handle(text, AgentContext(household_id=None, language="hi"))
            return outcome.reply

        async def synthesize(text: str, sample_rate: int) -> bytes:
            return await speech.synthesize(text, sample_rate=sample_rate, language="hi-IN")

        await run_exotel_session(
            websocket,
            transcribe=transcribe,
            respond=respond,
            synthesize=synthesize,
        )
    except WebSocketDisconnect:
        return
    except Exception:
        if websocket.client_state.name == "CONNECTED":
            await websocket.close(code=1011, reason="telephony_session_error")


@app.post("/api/v1/webhooks/telephony")
async def telephony_webhook(
    request: Request,
    x_saathi_signature: str | None = Header(default=None),
    x_provider_event_id: str | None = Header(default=None),
) -> dict[str, str | bool]:
    body = await request.body()
    if not settings.telephony_webhook_secret:
        raise HTTPException(status_code=503, detail="telephony_webhook_not_configured")
    if not x_saathi_signature or not HmacWebhookVerifier(settings.telephony_webhook_secret).verify(body, x_saathi_signature):
        raise HTTPException(status_code=401, detail="invalid_signature")
    event_id = derive_event_id(body, x_provider_event_id)
    event_type = None
    try:
        parsed_body = await request.json()
        if isinstance(parsed_body, dict) and isinstance(parsed_body.get("event"), str):
            event_type = parsed_body["event"]
        elif isinstance(parsed_body, dict) and isinstance(parsed_body.get("event_type"), str):
            event_type = parsed_body["event_type"]
    except (ValueError, UnicodeDecodeError):
        # The signed raw body remains authoritative; event-type metadata is optional.
        event_type = None

    if settings.supabase_url and settings.supabase_secret_key:
        try:
            duplicate = await record_supabase_webhook_event(
                base_url=settings.supabase_url,
                secret_key=settings.supabase_secret_key,
                event_id=event_id,
                event_type=event_type,
            )
        except (RuntimeError, ValueError):
            raise HTTPException(status_code=503, detail="durable_webhook_store_unavailable")
        except Exception:
            raise HTTPException(status_code=503, detail="durable_webhook_store_unavailable")
    elif settings.app_env.lower() == "production":
        raise HTTPException(status_code=503, detail="durable_webhook_store_not_configured")
    else:
        duplicate = webhook_events.seen_or_record(event_id)
    return {"status": "duplicate" if duplicate else "accepted", "event_id": event_id}
