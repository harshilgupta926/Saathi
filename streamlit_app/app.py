from __future__ import annotations

import asyncio
import html
import os
import sys
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Streamlit Cloud exposes secrets through st.secrets rather than the process
# environment. Mirror supported secrets into env before the cached Settings object
# is created so the existing backend configuration remains the single source.
_SECRET_ENV_KEYS = (
    "GEMINI_API_KEY", "OPENAI_API_KEY", "OPENAI_MODEL",
    "SARVAM_API_KEY", "SARVAM_STT_ENDPOINT", "SARVAM_STT_MODEL",
    "SARVAM_REALTIME_STT_ENDPOINT", "SARVAM_REALTIME_STT_ENABLED",
    "SARVAM_REALTIME_STREAM_TYPE", "SARVAM_TTS_ENDPOINT", "SARVAM_TTS_MODEL",
    "SARVAM_TTS_SPEAKER", "SARVAM_TTS_STREAM_ENDPOINT", "SARVAM_TTS_STREAM_SAMPLE_RATE",
    "MANDI_API_KEY", "MANDI_RESOURCE_ID", "MANDI_API_BASE",
    "EXOTEL_API_KEY", "EXOTEL_API_TOKEN", "EXOTEL_ACCOUNT_SID",
    "EXOTEL_SUBDOMAIN", "EXOTEL_VIRTUAL_NUMBER", "EXOTEL_STREAM_URL",
    "CALL_API_TOKEN", "TELEPHONY_WEBHOOK_SECRET", "DEMO_MODE",
)
try:
    _streamlit_secrets = st.secrets
except FileNotFoundError:
    _streamlit_secrets = {}

for _key in _SECRET_ENV_KEYS:
    if _key in _streamlit_secrets and str(_streamlit_secrets[_key]).strip():
        os.environ.setdefault(_key, str(_streamlit_secrets[_key]))

from app.config import get_settings
from app.orchestrator import AgentContext, Orchestrator
from app.schemas import LocationContext

try:
    from app.voice import VoiceGateway
except Exception:
    VoiceGateway = None

st.set_page_config(
    page_title="Saathi — Voice-first assistance",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root{--ink:#17211b;--muted:#6d776f;--paper:#f6f4ee;--card:rgba(255,255,255,.78);--line:rgba(23,33,27,.09);--green:#176b4d;--green2:#2b8a67}
html,body,[class*="css"]{font-family:"DM Sans",sans-serif;color:var(--ink)}
.stApp{background:radial-gradient(circle at 8% 4%,rgba(42,138,103,.13),transparent 28%),radial-gradient(circle at 92% 8%,rgba(231,184,75,.12),transparent 25%),linear-gradient(180deg,#fbfaf7 0%,var(--paper) 100%)}
.block-container{max-width:1280px;padding-top:1.5rem;padding-bottom:4rem}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:1.2rem}.brand-mark{width:42px;height:42px;border-radius:14px;display:grid;place-items:center;color:white;font-weight:800;background:linear-gradient(135deg,#176b4d,#3a9b77);box-shadow:0 10px 28px rgba(23,107,77,.20)}.brand-name{font:800 1.15rem Manrope,sans-serif;letter-spacing:-.03em}.brand-sub{color:var(--muted);font-size:.78rem}
.hero{position:relative;overflow:hidden;padding:42px;border-radius:30px;background:linear-gradient(135deg,rgba(255,255,255,.88),rgba(237,248,241,.78));border:1px solid var(--line);box-shadow:0 22px 70px rgba(31,48,39,.08)}.hero:after{content:"";position:absolute;width:280px;height:280px;right:-100px;top:-120px;border-radius:50%;background:rgba(43,138,103,.11)}.eyebrow{color:var(--green);font-size:.74rem;font-weight:800;letter-spacing:.14em;text-transform:uppercase;margin-bottom:10px}.hero h1{font:800 clamp(2.1rem,5vw,4.5rem)/.98 Manrope,sans-serif;letter-spacing:-.065em;max-width:820px;margin:0}.hero p{max-width:690px;color:#647067;font-size:1.05rem;line-height:1.65;margin:18px 0 0}
.panel{background:var(--card);border:1px solid var(--line);border-radius:24px;padding:22px;box-shadow:0 12px 40px rgba(31,48,39,.055)}.panel-title{font:700 1rem Manrope,sans-serif;margin-bottom:4px}.panel-sub{color:var(--muted);font-size:.82rem;margin-bottom:16px}
.metric{background:#fff;border:1px solid var(--line);border-radius:18px;padding:15px}.metric-label{color:var(--muted);font-size:.73rem;text-transform:uppercase;letter-spacing:.08em}.metric-value{font:800 1.15rem Manrope,sans-serif;margin-top:4px}
.chat{background:#fff;border:1px solid var(--line);border-radius:22px;padding:18px;margin-top:12px}.chat-user{color:#5e6a62;font-size:.78rem;font-weight:700;margin-bottom:6px}.chat-saathi{font:600 1.02rem/1.55 Manrope,sans-serif}.source{margin-top:14px;padding:12px 14px;border-radius:14px;background:#f1f7f3;border:1px solid rgba(23,107,77,.11)}.source b{color:var(--green)}.badge{display:inline-flex;align-items:center;gap:7px;border-radius:999px;padding:6px 10px;background:#edf7f1;color:var(--green);font-size:.72rem;font-weight:800}.dot{width:7px;height:7px;border-radius:50%;background:#3a9b77;display:inline-block}
div.stButton>button{border-radius:14px;border:1px solid var(--line);min-height:44px;font-weight:700;transition:all .18s ease}div.stButton>button:hover{transform:translateY(-1px);border-color:rgba(23,107,77,.25)}
button[kind="primary"]{background:linear-gradient(135deg,#176b4d,#2b8a67)!important;color:#fff!important;border:0!important;box-shadow:0 10px 24px rgba(23,107,77,.18)}
[data-testid="stSidebar"]{background:rgba(249,248,243,.94);border-right:1px solid var(--line)}[data-testid="stSidebar"] .block-container{padding-top:1.5rem}
.stTextInput input,.stTextArea textarea,.stSelectbox div[data-baseweb="select"]{border-radius:14px!important}
.muted{color:var(--muted)}
</style>
""",
    unsafe_allow_html=True,
)

settings = get_settings()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_outcome" not in st.session_state:
    st.session_state.last_outcome = None
if "last_audio" not in st.session_state:
    st.session_state.last_audio = None

with st.sidebar:
    st.markdown('<div class="brand"><div class="brand-mark">S</div><div><div class="brand-name">Saathi</div><div class="brand-sub">Voice-first assistance</div></div></div>', unsafe_allow_html=True)
    st.markdown("### Demo controls")
    mode = st.radio("Experience", ["Talk to Saathi", "Operator view"], index=0)
    language = st.selectbox("Language", ["Hindi / Hinglish", "English"], index=0)
    st.markdown("### Location")
    location_label = st.text_input("City / district", value="Sonipat, Haryana").strip() or "Unknown location"
    latitude = st.number_input("Latitude", value=28.9931, format="%.4f")
    longitude = st.number_input("Longitude", value=77.0151, format="%.4f")
    st.divider()
    live = not settings.demo_mode
    st.markdown(f'<span class="badge"><span class="dot"></span>{"Live providers" if live else "Demo-safe mode"}</span>', unsafe_allow_html=True)
    st.caption("Demo data is explicitly labelled. Provider keys belong in Streamlit Secrets, never in GitHub.")
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_outcome = None
        st.session_state.last_audio = None
        st.rerun()

st.markdown(
    '<div class="hero"><div class="eyebrow">Saathi · field-ready AI companion</div><h1>Apni baat kahiye.<br>Saathi samjhega.</h1><p>Hindi-first assistance for farming, schemes, documents and everyday help — with clear sources, human escalation and a safe fallback when live providers are unavailable.</p></div>',
    unsafe_allow_html=True,
)
st.write("")

if mode == "Operator view":
    st.markdown('<div class="panel"><div class="panel-title">Operator command center</div><div class="panel-sub">See exactly how Saathi interpreted the request and which capability handled it.</div></div>', unsafe_allow_html=True)
    cols = st.columns(5)
    vals = [
        ("Core agent", "Ready"),
        ("Weather", "Live" if not settings.demo_mode else "Demo"),
        ("Mandi", "Live" if (not settings.demo_mode and settings.mandi_api_key and settings.mandi_resource_id) else "Demo / gated"),
        ("Speech", "Live" if (not settings.demo_mode and settings.sarvam_api_key) else ("Configured / demo" if settings.sarvam_api_key else "Not configured")),
        ("Telephony", "Live" if (not settings.demo_mode and settings.exotel_stream_url) else ("Configured / demo" if settings.exotel_stream_url else "Not configured")),
    ]
    for c,(label,value) in zip(cols,vals):
        with c:
            st.markdown(f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>', unsafe_allow_html=True)
    st.write("")
    out = st.session_state.last_outcome
    if out:
        c1,c2 = st.columns([1,1])
        with c1:
            st.markdown("#### Request trace")
            st.json({"intent":str(out.intent),"tool":out.tool_name,"confidence":round(out.confidence,3),"latency_ms":out.latency_ms,"demo":out.demo})
        with c2:
            st.markdown("#### Provenance")
            sources = getattr(out,"sources",[])
            if sources:
                for src in sources:
                    st.markdown(
                        f'<div class="source"><b>{html.escape(str(src["name"]))}</b><br>'
                        f'<span class="muted">Retrieved: {html.escape(str(src["retrieved_at"]))}</span><br>'
                        f'<span class="muted">{html.escape(str(src.get("freshness_note", "")))}</span></div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No external source was required for this response.")
    else:
        st.info("Run a conversation from the user view to populate the operator trace.")
    st.stop()

left,right = st.columns([1.35,.75],gap="large")

with left:
    st.markdown('<div class="panel"><div class="panel-title">Baat shuru karein</div><div class="panel-sub">Type a request, or record a voice turn when a speech provider is configured.</div></div>', unsafe_allow_html=True)

    audio = st.audio_input("Voice message", key="voice_input")
    if audio:
        st.audio(audio)
        if settings.sarvam_api_key and VoiceGateway is not None:
            if st.button("Process voice", type="primary", use_container_width=True):
                with st.spinner("Saathi is listening and finding the right answer…"):
                    try:
                        gateway = VoiceGateway(settings, Orchestrator())
                        async def run_voice():
                            return await gateway.handle(
                                audio.getvalue(),
                                language="hi" if language.startswith("Hindi") else "en",
                                household_id=None,
                                location=LocationContext(latitude=latitude, longitude=longitude, label=location_label),
                            )
                        started=time.perf_counter()
                        turn=asyncio.run(run_voice())
                        elapsed=(time.perf_counter()-started)*1000
                        class UIOutcome: pass
                        ui=UIOutcome()
                        ui.reply=turn.outcome.reply; ui.intent=turn.outcome.intent; ui.tool_name=turn.outcome.tool_name
                        ui.confidence=turn.outcome.confidence; ui.latency_ms=round(elapsed,1); ui.demo=settings.demo_mode
                        ui.correlation_id="streamlit-voice"; ui.escalated=turn.outcome.escalated; ui.source=None; ui.sources=[]
                        for item in turn.outcome.results:
                            if item.source:
                                src=item.source
                                ui.sources.append({"name":src.name,"retrieved_at":src.retrieved_at.isoformat(),"freshness_note":src.freshness_note,"url":src.url})
                        if ui.sources: ui.source=ui.sources[0]
                        st.session_state.last_outcome=ui
                        st.session_state.messages.append(("user",turn.transcript))
                        st.session_state.messages.append(("saathi",turn.outcome.reply))
                        st.session_state.last_audio = turn.audio
                        st.rerun()
                    except Exception:
                        st.error("Voice provider could not process this turn. Check the provider configuration and try again.")
        else:
            st.caption("Voice processing is ready for Sarvam credentials. Until then, use the text box for the complete deterministic demo.")

    prompt=st.chat_input("Jaise: Sonipat mein gehun ka mandi bhav kya hai?")
    if prompt:
        with st.spinner("Saathi samajh raha hai…"):
            started=time.perf_counter()
            outcome=asyncio.run(Orchestrator().handle(
                prompt,
                AgentContext(
                    household_id=None,
                    language="hi" if language.startswith("Hindi") else "en",
                    location=LocationContext(latitude=latitude,longitude=longitude,label=location_label),
                ),
            ))
            elapsed=(time.perf_counter()-started)*1000
        class UIOutcome: pass
        ui=UIOutcome()
        ui.reply=outcome.reply; ui.intent=outcome.intent; ui.tool_name=outcome.tool_name; ui.confidence=outcome.confidence
        ui.latency_ms=round(elapsed,1); ui.demo=settings.demo_mode; ui.correlation_id="streamlit-text"; ui.escalated=outcome.escalated
        ui.sources=[]
        for item in outcome.results:
            if item.source:
                src=item.source
                ui.sources.append({"name":src.name,"retrieved_at":src.retrieved_at.isoformat(),"freshness_note":src.freshness_note,"url":src.url})
        ui.source=ui.sources[0] if ui.sources else None
        st.session_state.messages.append(("user",prompt))
        st.session_state.messages.append(("saathi",outcome.reply))
        st.session_state.last_outcome=ui

    if st.session_state.last_audio:
        st.markdown("#### Saathi voice reply")
        st.audio(st.session_state.last_audio, format="audio/wav")
        st.write("")

    if st.session_state.messages:
        for role,message in st.session_state.messages[-10:]:
            safe_message = html.escape(str(message))
            if role=="user":
                st.markdown(f'<div class="chat"><div class="chat-user">YOU</div><div>{safe_message}</div></div>',unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat"><div class="chat-user">SAATHI</div><div class="chat-saathi">{safe_message}</div></div>',unsafe_allow_html=True)
    else:
        st.markdown('<div class="chat"><div class="chat-user">TRY A REAL REQUEST</div><div class="chat-saathi">“Mere Sonipat mein kal baarish hogi?”<br>“Sonipat mein gehun ka mandi bhav batao.”<br>“PM Kisan ke liye kya chahiye?”</div></div>',unsafe_allow_html=True)

with right:
    st.markdown('<div class="panel"><div class="panel-title">What Saathi understood</div><div class="panel-sub">The reasoning trace stays visible instead of hiding behind a chatbot.</div></div>', unsafe_allow_html=True)
    out=st.session_state.last_outcome
    if out:
        st.markdown(f'<div class="metric"><div class="metric-label">Intent</div><div class="metric-value">{html.escape(str(out.intent))}</div></div>',unsafe_allow_html=True)
        st.write("")
        c1,c2=st.columns(2)
        with c1:
            st.markdown(f'<div class="metric"><div class="metric-label">Capability</div><div class="metric-value">{html.escape(str(out.tool_name or "conversation"))}</div></div>',unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric"><div class="metric-label">Confidence</div><div class="metric-value">{out.confidence:.0%}</div></div>',unsafe_allow_html=True)
        st.write("")
        st.markdown(f'<div class="metric"><div class="metric-label">Turn latency</div><div class="metric-value">{out.latency_ms:.0f} ms</div></div>',unsafe_allow_html=True)
        if out.source:
            src=out.source
            st.markdown(
                f'<div class="source"><b>Source-backed answer</b><br>{html.escape(str(src["name"]))}'
                f'<br><span class="muted">Retrieved {html.escape(str(src["retrieved_at"]))}</span></div>',
                unsafe_allow_html=True,
            )
        if out.escalated:
            st.warning("Saathi recommends human support for this request.")
    else:
        st.markdown('<div class="metric"><div class="metric-label">Safe by design</div><div class="metric-value">Source → answer → escalation</div></div>',unsafe_allow_html=True)
        st.write("")
        st.caption("Saathi does not invent live prices, weather, eligibility or application status. Provider failures remain visible.")
