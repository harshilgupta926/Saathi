"use client";

import Link from "next/link";

import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "motion/react";
import {
  AlertTriangle, ArrowLeft, ArrowUpRight, Bot, CheckCircle2,
  CloudRain, Languages, MapPin, Mic2, PhoneCall,
  ShieldCheck, Sparkles, UserRound, Volume2, Wheat, Zap, type LucideIcon
} from "lucide-react";


type Source = { name: string; url: string; retrieved_at?: string | null; freshness_note?: string | null; freshness_status?: string | null };
type Evidence = { name: string; url: string; retrieved_at?: string | null; freshness_note?: string | null; freshness_status?: string | null };
type ReadyCapabilities = { core_agent?: boolean; telephony?: boolean; telephony_realtime?: boolean; reasoning?: boolean; mandi?: boolean; speech?: boolean; weather?: boolean; documents?: boolean };

type BrowserSpeechRecognition = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((event: { results: { [index: number]: { [index: number]: { transcript: string } } } }) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type BrowserSpeechRecognitionConstructor = new () => BrowserSpeechRecognition;

type BrowserSpeechWindow = Window & {
  SpeechRecognition?: BrowserSpeechRecognitionConstructor;
  webkitSpeechRecognition?: BrowserSpeechRecognitionConstructor;
};

type Result = {
  reply: string;
  intent: string;
  demo: boolean;
  correlation_id?: string;
  source?: Source;
  sources?: Evidence[];
  escalated?: boolean;
  escalation_reason?: string | null;
  confidence?: number | null;
  tool_name?: string | null;
  latency_ms?: number | null;
};

const scenarios = [
  { id: "mandi", label: "Mandi bhav", text: "सोनीपत मंडी में गेहूं का आज क्या भाव है?", icon: Wheat },
  { id: "weather", label: "Weather", text: "अगले 24 घंटे में बारिश की संभावना कितनी है?", icon: CloudRain },
  { id: "scheme", label: "Yojana", text: "मेरे लिए किसान की सरकारी योजना बताओ", icon: ShieldCheck },
  { id: "human", label: "Human help", text: "मुझे किसी इंसान से बात करनी है", icon: UserRound },
] as const;

const flowSteps: [string, string, string, LucideIcon][] = [
  ["01", "Listen", "Voice / missed call", Mic2],
  ["02", "Understand", "Language + intent", Languages],
  ["03", "Act", "Specialist + tools", Bot],
  ["04", "Protect", "Consent boundary", ShieldCheck],
  ["05", "Escalate", "Human when needed", UserRound],
];

export default function Dashboard() {
  const [message, setMessage] = useState<string>(scenarios[0].text);
  const [scenario, setScenario] = useState("mandi");
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [voiceState, setVoiceState] = useState<"idle" | "listening" | "thinking" | "speaking">("idle");
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const [apiOnline, setApiOnline] = useState(false);
  const [apiReady, setApiReady] = useState(false);
  const [capabilities, setCapabilities] = useState<ReadyCapabilities>({});
  const [demoMode, setDemoMode] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/backend/health/ready", { signal: controller.signal, cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("health check failed");
        const body = await response.json();
        setApiOnline(true);
        setApiReady(body.status === "ready");
        setCapabilities(body.provider_contracts || {});
        setDemoMode(body.demo_mode !== false);
      })
      .catch(() => {
        setApiOnline(false);
        setApiReady(false);
      });
    return () => controller.abort();
  }, []);

  const trace = useMemo(() => {
    const tool = result?.tool_name || "pending";
    const hasEvidence = !!result?.source || !!result?.sources?.length;
    const providerState = hasEvidence ? "Evidence + provenance attached" : result ? "No live evidence attached" : "Waiting for request";
    return [
      ["01", "Request received", true],
      ["02", result ? `Intent · ${result.intent}` : "Language + intent", !!result],
      ["03", result ? `Capability · ${tool}` : "Specialist capability", !!result],
      ["04", result ? "Policy boundary checked" : "Policy boundary", !!result],
      ["05", providerState, hasEvidence],
      ["06", result?.escalated ? "Human escalation selected" : result ? "Grounded response selected" : "Response policy", !!result],
      ["07", result ? `Sources · ${result.sources?.length || (result.source ? 1 : 0)}` : "Source count", hasEvidence],
      ["08", typeof result?.latency_ms === "number" ? `Turn latency · ${result.latency_ms} ms` : "Turn latency", !!result],
    ] as const;
  }, [result]);

  const selectScenario = (id: string) => {
    const item = scenarios.find((entry) => entry.id === id) ?? scenarios[0];
    setScenario(id);
    setMessage(item.text);
    setResult(null);
    setVoiceState("idle");
  };

  const toggleVoice = async () => {
    setVoiceError(null);

    // Demo-mode fallback: use the browser's native speech stack when Sarvam
    // is not configured. This is explicitly local/browser voice, not provider STT/TTS.
    if (!capabilities.speech) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
        return;
      }
      const SpeechRecognition = (window as BrowserSpeechWindow).SpeechRecognition || (window as BrowserSpeechWindow).webkitSpeechRecognition;
      if (!SpeechRecognition) {
        setVoiceError("Live speech is not configured, and this browser does not provide local speech recognition.");
        return;
      }
      const recognition = new SpeechRecognition();
      recognition.lang = "hi-IN";
      recognition.interimResults = false;
      recognition.continuous = false;
      recognition.onresult = (event) => {
        const transcript = event.results[0]?.[0]?.transcript?.trim();
        if (transcript) {
          setMessage(transcript);
          void runAgent(transcript);
        }
      };
      recognition.onerror = (event) => {
        recognitionRef.current = null;
        setVoiceState("idle");
        setVoiceError(event.error ? `Browser speech error: ${event.error}` : "Browser speech recognition failed.");
      };
      recognition.onend = () => {
        recognitionRef.current = null;
        setVoiceState("idle");
      };
      recognitionRef.current = recognition;
      setVoiceState("listening");
      recognition.start();
      return;
    }

    if (recorderRef.current) {
      recorderRef.current.stop();
      setVoiceState("thinking");
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setVoiceError("Browser microphone recording is not available here.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorderRef.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        recorderRef.current = null;
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        if (!blob.size) {
          setVoiceState("idle");
          setVoiceError("No voice was captured.");
          return;
        }

        setLoading(true);
        setVoiceState("thinking");
        try {
          const form = new FormData();
          form.append("audio", blob, "caller.webm");
          form.append("language", "hi");
          const response = await fetch("/backend/api/v1/voice/turn", { method: "POST", body: form });
          const body = await response.json();
          if (!response.ok) throw new Error(body.detail || `Voice request failed: ${response.status}`);
          setMessage(body.transcript || message);
          setResult(body);
          setVoiceState(body.audio_base64 ? "speaking" : "idle");

          if (body.audio_base64) {
            const bytes = Uint8Array.from(atob(body.audio_base64), (char) => char.charCodeAt(0));
            const audio = new Audio(URL.createObjectURL(new Blob([bytes], { type: body.audio_mime_type || "audio/wav" })));
            audio.onended = () => { URL.revokeObjectURL(audio.src); setVoiceState("idle"); };
            await audio.play();
          }
        } catch (error) {
          setVoiceState("idle");
          setVoiceError(error instanceof Error ? error.message : "Voice provider is not configured.");
        } finally {
          setLoading(false);
        }
      };
      recorder.start();
      setVoiceState("listening");
    } catch {
      setVoiceError("Microphone permission was denied or unavailable.");
      setVoiceState("idle");
    }
  };

  const runAgent = async (requestMessage = message) => {
    setLoading(true);
    setVoiceState("thinking");
    try {
      const response = await fetch("/backend/api/v1/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: requestMessage, language: "hi" }),
      });
      if (!response.ok) throw new Error(`Agent request failed: ${response.status}`);
      const body = await response.json();
      setResult(body);
      if (!capabilities.speech && typeof window !== "undefined" && "speechSynthesis" in window && body.reply) {
        setVoiceState("speaking");
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(body.reply);
        utterance.lang = "hi-IN";
        utterance.onend = () => setVoiceState("idle");
        window.speechSynthesis.speak(utterance);
      } else {
        setVoiceState("idle");
      }
    } catch {
      setResult({
        reply: "Backend se connection nahi ho paaya. Saathi live result invent nahi karega — provider status check karein.",
        intent: "general",
        demo: true,
      });
      setVoiceState("idle");
    } finally {
      setLoading(false);
    }
  };

  const run = () => runAgent();

  return (
    <main className="command-shell">
      <div className="command-wrap">
        <header className="command-header">
          <div>
            <div className="eyebrow"><span className="eyebrow-line" /> SAATHI</div>
            <h1>Ask Saathi. <em>Get grounded help.</em></h1>
            <p>Use voice or text to ask a real question. Saathi interprets it, checks the right specialist source, and shows the evidence behind the response.</p>
          </div>
          <div className="header-badges">
            <span><Zap size={13} /> {apiOnline ? (apiReady ? "API ready" : "API online") : "API offline"}</span>
            <span><ShieldCheck size={13} /> Consent-led</span>
            <span><Languages size={13} /> Hindi-first</span>
          </div>
        </header>

        <section className="status-grid">
          <article className="metric-card accent">
            <div className="metric-icon"><PhoneCall size={18} /></div>
            <div><small>VOICE CHANNEL</small><strong>Phone channel</strong><p>Exotel adapter present · live call not verified</p></div>
          </article>
          <article className="metric-card">
            <div className="metric-icon"><Bot size={18} /></div>
            <div><small>ORCHESTRATOR</small><strong>Specialist routing</strong><p>Deterministic intent + tool boundary</p></div>
          </article>
          <article className="metric-card">
            <div className="metric-icon"><Sparkles size={18} /></div>
            <div><small>VOICE STATE</small><strong>{voiceState === "idle" ? "Ready" : voiceState === "listening" ? "Listening" : voiceState === "thinking" ? "Thinking" : "Speaking"}</strong><p>Live browser voice state</p></div>
          </article>
        </section>

        <section className="workspace">
          <div className="caller-panel">
            <div className="panel-head">
              <div><span className="panel-kicker">ASK SAATHI</span><h2>What would you like to know?</h2></div>
              <span className="demo-tag"><i /> BROWSER PROTOTYPE</span>
            </div>

            <div className="caller-context">
              <div className={`caller-avatar ${voiceState !== "idle" ? "pulse" : ""}`}><Mic2 size={23} /></div>
              <div><strong>Demo session</strong><span>Hindi · location not provided</span></div>
              <span className={`call-state ${voiceState !== "idle" ? "busy" : ""}`}>{voiceState.toUpperCase()}</span>
            </div>

            <div className="scenario-tabs" role="tablist" aria-label="Question types">
              {scenarios.map(({ id, label, icon: Icon }) => (
                <button type="button" key={id} role="tab" aria-selected={scenario === id} className={scenario === id ? "selected" : ""} onClick={() => selectScenario(id)}>
                  <Icon size={14} />{label}
                </button>
              ))}
            </div>

            <textarea value={message} onChange={(event) => setMessage(event.target.value)} aria-label="Caller request" />

            <div className="voice-controls">
              <button type="button" className={`voice-button ${voiceState === "listening" ? "active" : ""}`} onClick={toggleVoice} aria-label="Toggle microphone" disabled={loading || voiceState === "speaking"}>
                <Mic2 size={18} /> {voiceState === "listening" ? "Stop recording" : "Start voice"}
              </button>
              <span><Volume2 size={13} /> {capabilities.speech ? "Configured provider path · live round trip still requires verification" : "Browser voice preview · provider STT/TTS not configured"}</span>
            </div>

            {voiceError && <div className="voice-error" role="alert" aria-live="assertive">{voiceError}</div>}

            <button type="button" className="run-button" onClick={run} disabled={loading || !message.trim()}>
              <Bot size={18} />{loading ? "Saathi is thinking…" : "Run this conversation"}<ArrowUpRight size={17} />
            </button>

            {result && (
              <motion.div className="answer-card" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                <div className="answer-label"><span><Bot size={15} /> SAATHI RESPONSE</span><b>{result.intent}</b></div>
                <p>{result.reply}</p>
                {(result.sources?.length ? result.sources : result.source ? [result.source] : []).map((source, index) => (
                  <div className="source-row" key={`${source.name}-${source.retrieved_at || source.freshness_status || index}-${index}`}>{source.freshness_status === "stale" || source.freshness_status === "unknown" || source.freshness_status === "future" ? <AlertTriangle size={15} /> : <CheckCircle2 size={15} />}<div><strong>{source.name}</strong><span>{source.freshness_note || "Provider result retrieved with timestamp."}</span><small>{source.retrieved_at ? `Retrieved · ${new Date(source.retrieved_at).toLocaleString()}` : `No live retrieval timestamp · catalogue review status: ${source.freshness_status || "unknown"}`}</small>{source.url && <a href={source.url} target="_blank" rel="noreferrer">View source ↗</a>}</div></div>
                ))}
                {!result.sources?.length && !result.source && (
                  <div className="source-row warning"><ShieldCheck size={15} /><div><strong>No live source attached</strong><span>Saathi will not present an unverified answer as live fact.</span></div></div>
                )}
                {result.correlation_id && <div className="correlation-line">Correlation ID · <code>{result.correlation_id}</code>{result.tool_name && <> · Tool · <strong>{result.tool_name}</strong></>}{typeof result.latency_ms === "number" && <> · Turn · <strong>{result.latency_ms} ms</strong></>}</div>}
              </motion.div>
            )}
          </div>

          <aside className="trace-panel">
            <div className="panel-head dark-head">
              <div><span className="panel-kicker">AGENT TRACE</span><h2>Every step is inspectable.</h2></div>
              <Sparkles size={19} />
            </div>
            <div className="trace-list">
              {trace.map(([num, label, active]) => (
                <div className={`trace-item ${active ? "active" : ""}`} key={num}>
                  <span className="trace-num">{num}</span><span className="trace-line" /><span className="trace-label">{label}</span>
                  {active ? <CheckCircle2 size={15} /> : <span className="pending-dot" />}
                </div>
              ))}
            </div>
            <div className="privacy-box"><ShieldCheck size={17} /><div><strong>No invented facts.</strong><p>Tool-backed answers carry provenance. Demo data stays visibly marked.</p></div></div>
          </aside>
        </section>

        <section className="context-grid">
          <article className="context-card">
            <div className="context-title"><div><span className="panel-kicker">FIELD CONTEXT</span><h3>Where should Saathi look?</h3></div><MapPin size={18} /></div>
            <div className="location-row"><div className="map-placeholder"><MapPin size={23} /><span>FIELD CONTEXT</span></div><div><strong>Location not set</strong><p>Location-specific answers require a verified location context. Saathi does not infer your location.</p><span className="source-status"><i /> Location source · not provided</span></div></div>
          </article>

          <article className="context-card">
            <div className="context-title"><div><span className="panel-kicker">SOURCE HEALTH</span><h3>What can we trust?</h3></div><CheckCircle2 size={18} /></div>
            <div className="health-list">
              <div><span><Wheat size={14} /> Mandi tool</span><b className={capabilities.mandi ? "live-badge" : "demo-badge"}>{demoMode ? "DEMO MODE" : capabilities.mandi ? "LIVE OGD" : "NOT CONFIGURED"}</b></div>
              <div><span><CloudRain size={14} /> Weather tool</span><b className={demoMode ? "demo-badge" : "live-badge"}>{demoMode ? "DEMO MODE" : "Open-Meteo configured"}</b></div>
              <div><span><ShieldCheck size={14} /> Scheme rules</span><b className="demo-badge">STATIC CATALOGUE</b></div>
            </div>
          </article>
        </section>

        <section className="consent-card" aria-labelledby="consent-title">
          <div className="context-title"><div><span className="panel-kicker">HOUSEHOLD MEMORY</span><h3 id="consent-title">Remember only with permission.</h3></div><ShieldCheck size={18} /></div>
          <p className="consent-intro">Saathi separates useful continuity from silent surveillance. Household memory remains a prototype-only capability until server-side consent persistence is enabled.</p>
          <div className="consent-note"><ShieldCheck size={14} /> Household memory is disabled in this prototype. No consent is being collected or stored here; persistent memory remains unavailable until authenticated identity, server-side consent and deletion workflows are verified.</div>
        </section>

        <section className="fallback-card" aria-labelledby="fallback-title">
          <div className="fallback-icon"><UserRound size={22} /></div>
          <div className="fallback-copy"><span className="panel-kicker">HUMAN FALLBACK</span><h3 id="fallback-title">Human escalation policy</h3><p>Explicit requests and low-confidence/provider failures can be flagged in the response. A persistent volunteer queue, assignment and delivery workflow is not connected in this prototype.</p></div>
          <div className="fallback-status"><span><i /> Policy only</span><small>Volunteer queue · not connected</small></div>
        </section>

        <section className="flow-strip">
          {flowSteps.map(([num, title, sub, Icon], i) => (
            <div className="flow-step" key={num}><span>{num}</span><Icon size={17} /><div><strong>{title}</strong><small>{sub}</small></div>{i < 4 && <ArrowUpRight size={14} />}</div>
          ))}
        </section>

        <footer className="command-footer" aria-label="Saathi footer">
          <span>SAATHI · VOICE-FIRST ACCESS</span><span>Product prototype · 2026</span>
          <Link href="/"><ArrowLeft size={14} /> Back to product</Link>
        </footer>
      </div>
    </main>
  );
}
