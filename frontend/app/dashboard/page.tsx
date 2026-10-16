"use client";

import Link from "next/link";

import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "motion/react";
import {
  AlertTriangle, ArrowLeft, ArrowUpRight, Bot, CheckCircle2,
  CloudRain, Languages, MapPin, Mic2, PhoneCall,
  ShieldCheck, Sparkles, UserRound, Volume2, Wheat, Zap, type LucideIcon
} from "lucide-react";


type Source = { name: string; url: string; retrieved_at?: string | null; freshness_note?: string | null; freshness_status?: string | null };
type Evidence = { name: string; url: string; retrieved_at?: string | null; freshness_note?: string | null; freshness_status?: string | null };
type ReadyCapabilities = { core_agent?: boolean; telephony?: boolean; telephony_realtime?: boolean; reasoning?: boolean; mandi?: boolean; speech?: boolean; weather?: boolean; documents?: boolean };
type ConsentSnapshot = { memory: { granted: boolean; recorded_at: string | null }; outbound_calls: { granted: boolean; recorded_at: string | null } };
type HouseholdTask = { task_id: string; title: string; status: "pending" | "completed" | "cancelled" | "escalated"; missing_items: string[]; scheduled_callback: string | null };
type HouseholdMemory = { memory_id: string; memory_type: string; key_name: string; value_text: string; source: "user_confirmed" | string; updated_at: string | null; expires_at: string | null };

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
  const [requestError, setRequestError] = useState<string | null>(null);
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
  const [authStatus, setAuthStatus] = useState<{ loading: boolean; configured: boolean; phoneSuffix: string | null; householdReady: boolean }>({ loading: true, configured: false, phoneSuffix: null, householdReady: false });
  const [consentStatus, setConsentStatus] = useState<ConsentSnapshot | null>(null);
  const [consentBusy, setConsentBusy] = useState(false);
  const [consentMessage, setConsentMessage] = useState<string | null>(null);
  const [consentError, setConsentError] = useState<string | null>(null);
  const [householdMemories, setHouseholdMemories] = useState<HouseholdMemory[] | null>(null);
  const [memoryType, setMemoryType] = useState("preference");
  const [memoryKey, setMemoryKey] = useState("");
  const [memoryValue, setMemoryValue] = useState("");
  const [memoryBusy, setMemoryBusy] = useState(false);
  const [memoryError, setMemoryError] = useState<string | null>(null);
  const [memoryMessage, setMemoryMessage] = useState<string | null>(null);
  const [householdTasks, setHouseholdTasks] = useState<HouseholdTask[] | null>(null);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskBusy, setTaskBusy] = useState(false);
  const [taskError, setTaskError] = useState<string | null>(null);
  const [taskMessage, setTaskMessage] = useState<string | null>(null);

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

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/auth/session", { signal: controller.signal, cache: "no-store" })
      .then(async (response) => {
        const body = await response.json();
        setAuthStatus({ loading: false, configured: body.authConfigured === true, phoneSuffix: body.phoneVerified === true ? body.phoneSuffix : null, householdReady: body.householdContextVerified === true });
      })
      .catch(() => setAuthStatus({ loading: false, configured: false, phoneSuffix: null, householdReady: false }));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!authStatus.householdReady) return;
    const controller = new AbortController();
    fetch("/backend/api/v1/household/consent", { signal: controller.signal, cache: "no-store" })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "Consent status is unavailable.");
        setConsentStatus(body);
        if (body.memory?.granted !== true) setHouseholdMemories(null);
        setConsentError(null);
      })
      .catch((cause) => {
        if (!controller.signal.aborted) setConsentError(cause instanceof Error ? cause.message : "Consent status is unavailable.");
      });
    return () => controller.abort();
  }, [authStatus.householdReady]);

  useEffect(() => {
    if (!authStatus.householdReady || consentStatus?.memory.granted !== true) return;
    const controller = new AbortController();
    fetch("/backend/api/v1/household/memories", { signal: controller.signal, cache: "no-store" })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok || !Array.isArray(body.memories)) throw new Error(body.detail || "Saved memories are unavailable.");
        setHouseholdMemories(body.memories);
        setMemoryError(null);
      })
      .catch((cause) => {
        if (!controller.signal.aborted) setMemoryError(cause instanceof Error ? cause.message : "Saved memories are unavailable.");
      });
    return () => controller.abort();
  }, [authStatus.householdReady, consentStatus?.memory.granted]);

  useEffect(() => {
    if (!authStatus.householdReady) return;
    const controller = new AbortController();
    fetch("/backend/api/v1/household/tasks", { signal: controller.signal, cache: "no-store" })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok || !Array.isArray(body.tasks)) throw new Error(body.detail || "Saved tasks are unavailable.");
        setHouseholdTasks(body.tasks);
        setTaskError(null);
      })
      .catch((cause) => {
        if (!controller.signal.aborted) setTaskError(cause instanceof Error ? cause.message : "Saved tasks are unavailable.");
      });
    return () => controller.abort();
  }, [authStatus.householdReady]);

  const updateConsent = async (purpose: "memory" | "outbound_calls", granted: boolean) => {
    setConsentBusy(true);
    setConsentError(null);
    setConsentMessage(null);
    try {
      const response = await fetch("/backend/api/v1/household/consent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ purpose, granted }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Consent could not be updated.");
      const statusResponse = await fetch("/backend/api/v1/household/consent", { cache: "no-store" });
      const statusBody = await statusResponse.json();
      if (!statusResponse.ok) throw new Error(statusBody.detail || "Consent status could not be refreshed.");
      setConsentStatus(statusBody);
      if (purpose === "memory" && !granted) setHouseholdMemories(null);
      setConsentMessage(purpose === "memory"
        ? (granted ? "Household memory consent saved." : "Household memory consent revoked; stored memory is purged by the database guard.")
        : (granted ? "Outbound-call consent saved. This does not place a call." : "Outbound-call consent revoked."));
    } catch (cause) {
      setConsentError(cause instanceof Error ? cause.message : "Consent could not be updated.");
    } finally {
      setConsentBusy(false);
    }
  };

  const signOut = async () => {
    setConsentError(null);
    try {
      const response = await fetch("/api/auth/signout", { method: "POST" });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Sign out failed.");
      setAuthStatus((current) => ({ ...current, loading: false, phoneSuffix: null, householdReady: false }));
      setConsentStatus(null);
      setConsentMessage(null);
      setHouseholdTasks(null);
      setTaskTitle("");
      setTaskMessage(null);
      setTaskError(null);
      setHouseholdMemories(null);
      setMemoryKey("");
      setMemoryValue("");
      setMemoryMessage(null);
      setMemoryError(null);
    } catch (cause) {
      setConsentError(cause instanceof Error ? cause.message : "Sign out could not be completed. Please retry.");
    }
  };

  const saveHouseholdMemory = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!authStatus.householdReady || consentStatus?.memory.granted !== true) return;
    setMemoryBusy(true);
    setMemoryError(null);
    setMemoryMessage(null);
    try {
      const response = await fetch("/backend/api/v1/household/memories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ memory_type: memoryType.trim(), key_name: memoryKey.trim(), value_text: memoryValue.trim() }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Memory could not be saved.");
      setHouseholdMemories((current) => [body as HouseholdMemory, ...(current || []).filter((item) => !(item.memory_type === body.memory_type && item.key_name === body.key_name))]);
      setMemoryKey("");
      setMemoryValue("");
      setMemoryMessage("Saved only because you explicitly confirmed it.");
    } catch (cause) {
      setMemoryError(cause instanceof Error ? cause.message : "Memory could not be saved.");
    } finally {
      setMemoryBusy(false);
    }
  };

  const deleteHouseholdMemory = async (memoryId: string) => {
    setMemoryBusy(true);
    setMemoryError(null);
    setMemoryMessage(null);
    try {
      const response = await fetch("/backend/api/v1/household/memories/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ memory_id: memoryId }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Memory could not be deleted.");
      setHouseholdMemories((current) => (current || []).filter((item) => item.memory_id !== memoryId));
      setMemoryMessage("Saved memory deleted.");
    } catch (cause) {
      setMemoryError(cause instanceof Error ? cause.message : "Memory could not be deleted.");
    } finally {
      setMemoryBusy(false);
    }
  };

  const createHouseholdTask = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const title = taskTitle.trim();
    if (!title || !authStatus.householdReady) return;
    setTaskBusy(true);
    setTaskError(null);
    setTaskMessage(null);
    try {
      const idempotencyKey = typeof crypto !== "undefined" && typeof crypto.randomUUID === "function" ? crypto.randomUUID() : undefined;
      const response = await fetch("/backend/api/v1/household/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, ...(idempotencyKey ? { idempotency_key: idempotencyKey } : {}) }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Task could not be saved.");
      setHouseholdTasks((current) => [body as HouseholdTask, ...(current || []).filter((item) => item.task_id !== body.task_id)]);
      setTaskTitle("");
      setTaskMessage("Task saved. Automatic reminders and callback delivery are not enabled yet.");
    } catch (cause) {
      setTaskError(cause instanceof Error ? cause.message : "Task could not be saved.");
    } finally {
      setTaskBusy(false);
    }
  };

  const updateHouseholdTaskStatus = async (taskId: string, status: "completed" | "cancelled") => {
    setTaskBusy(true);
    setTaskError(null);
    setTaskMessage(null);
    try {
      const response = await fetch("/backend/api/v1/household/tasks/status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_id: taskId, status }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Task status could not be updated.");
      setHouseholdTasks((current) => (current || []).filter((item) => item.task_id !== taskId));
      setTaskMessage(status === "completed" ? "Task marked complete." : "Task cancelled.");
    } catch (cause) {
      setTaskError(cause instanceof Error ? cause.message : "Task status could not be updated.");
    } finally {
      setTaskBusy(false);
    }
  };

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
    setRequestError(null);
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
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 20_000);
    setLoading(true);
    setRequestError(null);
    setResult(null);
    setVoiceState("thinking");
    try {
      const response = await fetch("/backend/api/v1/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: requestMessage, language: "hi" }),
        signal: controller.signal,
        cache: "no-store",
      });
      if (!response.ok) throw new Error(`Agent request failed: ${response.status}`);
      const body: unknown = await response.json();
      if (!body || typeof body !== "object" || !("reply" in body) || typeof body.reply !== "string" || !body.reply.trim() || !("intent" in body) || typeof body.intent !== "string") {
        throw new Error("Saathi returned an invalid response. Please retry.");
      }
      const resultBody = body as Result;
      setResult(resultBody);
      if (!capabilities.speech && typeof window !== "undefined" && "speechSynthesis" in window && resultBody.reply) {
        setVoiceState("speaking");
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(resultBody.reply);
        utterance.lang = "hi-IN";
        utterance.onend = () => setVoiceState("idle");
        window.speechSynthesis.speak(utterance);
      } else {
        setVoiceState("idle");
      }
    } catch (error) {
      setVoiceState("idle");
      setRequestError(error instanceof DOMException && error.name === "AbortError"
        ? "Saathi request timed out after 20 seconds. Check your connection and retry."
        : error instanceof Error
          ? error.message
          : "Saathi could not complete this request. Check your connection and retry.");
    } finally {
      window.clearTimeout(timeout);
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
            <p>Use voice or text to ask a question. Saathi routes the request, shows available source evidence, and makes unavailable integrations explicit.</p>
          </div>
          <div className="header-badges">
            <span role="status" aria-live="polite"><Zap size={13} /> {apiOnline ? (apiReady ? "API ready" : "API online") : "API offline"}</span>
            <span><ShieldCheck size={13} /> {consentStatus?.memory.granted ? "Memory consent granted" : "Memory consent off"}</span>
            <span><Languages size={13} /> Hindi-first</span>
            {authStatus.phoneSuffix ? (authStatus.householdReady ? <button type="button" className="auth-status-link" onClick={signOut}>Household unlocked · ••••{authStatus.phoneSuffix} · Sign out</button> : <><Link href="/login" className="auth-status-link">Verify household PIN · ••••{authStatus.phoneSuffix}</Link><button type="button" className="auth-status-link" onClick={signOut}>Sign out</button></>) : <Link href="/login" className="auth-status-link">{authStatus.loading ? "Checking sign-in…" : authStatus.configured ? "Sign in with phone" : "Phone sign-in not configured"}</Link>}
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
              <span className={`call-state ${voiceState !== "idle" ? "busy" : ""}`} role="status" aria-live="polite">{voiceState.toUpperCase()}</span>
            </div>

            <div className="scenario-tabs" role="tablist" aria-label="Question types">
              {scenarios.map(({ id, label, icon: Icon }) => (
                <button
                  type="button"
                  key={id}
                  role="tab"
                  data-scenario-tab={id}
                  tabIndex={scenario === id ? 0 : -1}
                  aria-selected={scenario === id}
                  className={scenario === id ? "selected" : ""}
                  onClick={() => selectScenario(id)}
                  onKeyDown={(event) => {
                    const current = scenarios.findIndex((item) => item.id === id);
                    let next = current;
                    if (event.key === "ArrowRight" || event.key === "ArrowDown") next = (current + 1) % scenarios.length;
                    else if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = (current - 1 + scenarios.length) % scenarios.length;
                    else if (event.key === "Home") next = 0;
                    else if (event.key === "End") next = scenarios.length - 1;
                    else return;
                    event.preventDefault();
                    const nextId = scenarios[next].id;
                    event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus();
                    selectScenario(nextId);
                  }}
                >
                  <Icon size={14} />{label}
                </button>
              ))}
            </div>

            <textarea value={message} onChange={(event) => setMessage(event.target.value)} aria-label="Caller request" />

            <div className="voice-controls">
              <button type="button" className={`voice-button ${voiceState === "listening" ? "active" : ""}`} onClick={toggleVoice} aria-label={voiceState === "listening" ? "Stop microphone recording" : "Start voice input"} aria-pressed={voiceState === "listening"} disabled={loading || voiceState === "speaking"}>
                <Mic2 size={18} /> {voiceState === "listening" ? "Stop recording" : "Start voice"}
              </button>
              <span><Volume2 size={13} /> {capabilities.speech ? "Configured provider path · live round trip still requires verification" : "Browser voice preview · provider STT/TTS not configured"}</span>
            </div>

            {voiceError && <div className="voice-error" role="alert" aria-live="assertive">{voiceError}</div>}

            <button type="button" className="run-button" onClick={run} aria-busy={loading} disabled={loading || !message.trim()}>
              <Bot size={18} />{loading ? "Saathi is thinking…" : "Run this conversation"}<ArrowUpRight size={17} />
            </button>

            {requestError && (
              <div className="voice-error" role="alert" aria-live="assertive">
                <strong>Request not completed.</strong> {requestError}
                <button type="button" onClick={() => void runAgent(message)} disabled={loading || !message.trim()}>Retry</button>
              </div>
            )}

            {result && (
              <motion.div className="answer-card" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                <div className="answer-label"><span><Bot size={15} /> SAATHI RESPONSE</span><b>{result.intent}</b></div>
                <p aria-live="polite" aria-atomic="true">{result.reply}</p>
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
          <div className="context-title"><div><span className="panel-kicker">HOUSEHOLD CONSENT</span><h3 id="consent-title">You stay in control.</h3></div><ShieldCheck size={18} /></div>
          <p className="consent-intro">Consent is separate by purpose. Sign in with a verified phone number to view and change persisted permissions. No permission is enabled by default.</p>
          {!authStatus.phoneSuffix ? (
            <div className="consent-note"><ShieldCheck size={14} /> {authStatus.configured ? "Sign in with a verified phone to manage household consent." : "Phone sign-in is not configured in this deployment. Household consent and memory remain unavailable."} {authStatus.configured && <Link href="/login">Sign in with phone</Link>}</div>
          ) : !authStatus.householdReady ? (
            <div className="consent-note"><ShieldCheck size={14} /> Verify your separate household PIN before viewing or changing consent. <Link href="/login">Verify household PIN</Link></div>
          ) : (
            <div className="consent-actions">
              <div className="consent-choice">
                <div><strong>Household memory</strong><p>Grant permission for future household-memory storage. The conversation workflow does not yet write memories automatically; revoking this permission purges any stored memory through the database guard.</p><span className="consent-state" role="status">{consentStatus ? (consentStatus.memory.granted ? "Granted" : "Not granted") : "Loading status…"}</span></div>
                <div className="consent-buttons"><button type="button" className="voice-button" onClick={() => void updateConsent("memory", true)} disabled={consentBusy || !consentStatus || consentStatus.memory.granted}>Enable memory</button><button type="button" className="voice-button" onClick={() => void updateConsent("memory", false)} disabled={consentBusy || !consentStatus || !consentStatus.memory.granted}>Revoke memory</button></div>
              </div>
              <div className="consent-choice">
                <div><strong>Outbound calls</strong><p>Allow explicitly requested follow-up calls. This permission is separate from memory and does not itself place a call.</p><span className="consent-state" role="status">{consentStatus ? (consentStatus.outbound_calls.granted ? "Granted" : "Not granted") : "Loading status…"}</span></div>
                <div className="consent-buttons"><button type="button" className="voice-button" onClick={() => void updateConsent("outbound_calls", true)} disabled={consentBusy || !consentStatus || consentStatus.outbound_calls.granted}>Allow calls</button><button type="button" className="voice-button" onClick={() => void updateConsent("outbound_calls", false)} disabled={consentBusy || !consentStatus || !consentStatus.outbound_calls.granted}>Revoke calls</button></div>
              </div>
            </div>
          )}
          {consentMessage && <p role="status" aria-live="polite">{consentMessage}</p>}
          {consentError && <p className="voice-error" role="alert" aria-live="assertive">{consentError}</p>}
        </section>

        <section className="consent-card" aria-labelledby="memories-title">
          <div className="context-title"><div><span className="panel-kicker">USER-CONTROLLED MEMORY</span><h3 id="memories-title">Choose what Saathi remembers.</h3></div><ShieldCheck size={18} /></div>
          <p className="consent-intro">Nothing is extracted from conversations automatically. Add only information you explicitly choose to save. The database also checks current memory consent when writing and purges saved memory when consent is revoked.</p>
          {!authStatus.phoneSuffix ? (
            <div className="consent-note"><ShieldCheck size={14} /> Sign in with a verified phone and household PIN to manage saved memory. <Link href="/login">Sign in</Link></div>
          ) : !authStatus.householdReady ? (
            <div className="consent-note"><ShieldCheck size={14} /> Verify your household PIN before viewing saved memory. <Link href="/login">Verify household PIN</Link></div>
          ) : consentStatus?.memory.granted !== true ? (
            <div className="consent-note"><ShieldCheck size={14} /> Memory consent is off. Enable it in the Household Consent section above before saving anything.</div>
          ) : (
            <>
              <form className="memory-form" onSubmit={saveHouseholdMemory}>
                <div className="memory-form-grid">
                  <div><label htmlFor="memory-type">Category</label><input id="memory-type" value={memoryType} onChange={(event) => setMemoryType(event.target.value)} maxLength={80} required /></div>
                  <div><label htmlFor="memory-key">What should be remembered?</label><input id="memory-key" value={memoryKey} onChange={(event) => setMemoryKey(event.target.value)} maxLength={120} placeholder="e.g. preferred crop" required /></div>
                </div>
                <label htmlFor="memory-value">Value</label>
                <textarea id="memory-value" value={memoryValue} onChange={(event) => setMemoryValue(event.target.value)} maxLength={2000} rows={3} placeholder="Write the exact information you want to save" required />
                <button type="submit" className="run-button" disabled={memoryBusy || !memoryType.trim() || !memoryKey.trim() || !memoryValue.trim()}>{memoryBusy ? "Saving…" : "Save selected memory"}</button>
              </form>
              {householdMemories === null ? <p className="consent-intro">Loading saved memory…</p> : householdMemories.length === 0 ? <div className="consent-note">No saved memories yet. Only items you add here are stored.</div> : (
                <ul className="memory-list">
                  {householdMemories.map((memory) => (
                    <li className="memory-row" key={memory.memory_id}>
                      <div><span className="consent-state">{memory.memory_type}</span><strong>{memory.key_name}</strong><p>{memory.value_text}</p><small>Explicitly saved · {memory.updated_at ? new Date(memory.updated_at).toLocaleString() : "time unavailable"}</small></div>
                      <button type="button" className="voice-button" disabled={memoryBusy} aria-label={`Delete saved memory ${memory.key_name}`} onClick={() => void deleteHouseholdMemory(memory.memory_id)}>Delete</button>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
          {memoryMessage && <p role="status" aria-live="polite">{memoryMessage}</p>}
          {memoryError && <p className="voice-error" role="alert" aria-live="assertive">{memoryError}</p>}
        </section>

        <section className="consent-card" aria-labelledby="tasks-title">
          <div className="context-title"><div><span className="panel-kicker">HOUSEHOLD TASKS</span><h3 id="tasks-title">Keep track of the next step.</h3></div><CheckCircle2 size={18} /></div>
          <p className="consent-intro">Tasks are saved to your verified household and can be marked complete or cancelled. Scheduled reminders and automatic follow-up delivery are not enabled yet.</p>
          {!authStatus.phoneSuffix ? (
            <div className="consent-note"><ShieldCheck size={14} /> {authStatus.configured ? "Sign in with a verified phone to manage household tasks." : "Phone sign-in is not configured in this deployment."} {authStatus.configured && <Link href="/login">Sign in with phone</Link>}</div>
          ) : !authStatus.householdReady ? (
            <div className="consent-note"><ShieldCheck size={14} /> Verify your household PIN before viewing or changing tasks. <Link href="/login">Verify household PIN</Link></div>
          ) : (
            <>
              <form className="task-form" onSubmit={createHouseholdTask}>
                <label htmlFor="household-task-title">New task</label>
                <div className="task-form-row">
                  <input id="household-task-title" value={taskTitle} onChange={(event) => setTaskTitle(event.target.value)} maxLength={300} placeholder="e.g. Call the agriculture office" required />
                  <button type="submit" className="run-button" disabled={taskBusy || !taskTitle.trim()}>{taskBusy ? "Saving…" : "Save task"}</button>
                </div>
              </form>
              {householdTasks === null ? <p className="consent-intro">Loading saved tasks…</p> : householdTasks.length === 0 ? <div className="consent-note">No open tasks yet. Add a task above to keep it with this household.</div> : (
                <ul className="task-list">
                  {householdTasks.map((task) => (
                    <li className="task-row" key={task.task_id}>
                      <div><strong>{task.title}</strong>{task.missing_items.length > 0 && <p>Still needed: {task.missing_items.join(", ")}</p>}</div>
                      <div className="task-row-actions"><button type="button" className="voice-button" disabled={taskBusy} onClick={() => void updateHouseholdTaskStatus(task.task_id, "completed")}>Mark complete</button><button type="button" className="voice-button" disabled={taskBusy} onClick={() => void updateHouseholdTaskStatus(task.task_id, "cancelled")}>Cancel task</button></div>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
          {taskMessage && <p role="status" aria-live="polite">{taskMessage}</p>}
          {taskError && <p className="voice-error" role="alert" aria-live="assertive">{taskError}</p>}
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
