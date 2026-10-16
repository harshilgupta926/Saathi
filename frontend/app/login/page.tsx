"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

type PinMode = "setup" | "verify" | null;

export default function LoginPage() {
  const router = useRouter();
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [pin, setPin] = useState("");
  const [sent, setSent] = useState(false);
  const [phoneVerified, setPhoneVerified] = useState(false);
  const [pinMode, setPinMode] = useState<PinMode>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function checkPinMode() {
    setError(null);
    const response = await fetch("/api/auth/household-pin", { cache: "no-store" });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "Household identity setup is unavailable.");
    if (body.mode !== "setup" && body.mode !== "verify") throw new Error("Household identity setup is unavailable.");
    setPinMode(body.mode);
    setNotice(body.mode === "setup"
      ? "Create an eight-digit household PIN. Avoid repeated digits and sequential numbers; phone OTP alone is not enough to access household data."
      : "Enter your household PIN to unlock this household on this device.");
  }

  async function sendOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const response = await fetch("/api/auth/otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phone.trim() }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "OTP could not be sent.");
      setSent(true);
      setNotice("If phone sign-in is enabled for this project, a verification code has been sent.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "OTP delivery is unavailable.");
    } finally {
      setBusy(false);
    }
  }

  async function verifyOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const response = await fetch("/api/auth/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phone.trim(), token: code.trim() }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Verification failed.");
      setPhoneVerified(true);
      await checkPinMode();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Phone verification failed.");
    } finally {
      setBusy(false);
    }
  }

  async function submitPin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!pinMode) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const response = await fetch("/api/auth/household-pin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: pinMode, pin }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Household verification failed.");
      router.replace("/dashboard");
      router.refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Household verification failed.");
    } finally {
      setBusy(false);
    }
  }

  function resetPhone() {
    setSent(false);
    setPhoneVerified(false);
    setPinMode(null);
    setCode("");
    setPin("");
    setNotice(null);
    setError(null);
  }

  return (
    <main className="command-shell">
      <div className="command-wrap">
        <header className="command-header">
          <div>
            <div className="eyebrow"><span className="eyebrow-line" /> SAATHI</div>
            <h1>Sign in with <em>your phone.</em></h1>
            <p>Verify your phone, then unlock your household with a separate PIN. This protects household data if a phone number is later recycled.</p>
          </div>
          <Link href="/dashboard" className="site-nav-cta">Back to dashboard</Link>
        </header>

        <section className="consent-card" aria-labelledby="phone-login-title">
          <div className="context-title">
            <div><span className="panel-kicker">VERIFIED IDENTITY</span><h2 id="phone-login-title">Phone and household verification</h2></div>
          </div>
          <p className="consent-intro">Enter your phone in international format, for example +919876543210. SMS sign-in must be enabled in Supabase Auth before this can work.</p>

          {!sent ? (
            <form onSubmit={sendOtp} className="auth-form">
              <label htmlFor="phone-number">Phone number</label>
              <input id="phone-number" type="tel" inputMode="tel" autoComplete="tel" placeholder="+919876543210" pattern="\+[1-9][0-9]{7,14}" value={phone} onChange={(event) => setPhone(event.target.value)} required maxLength={16} />
              <button type="submit" className="run-button" disabled={busy || !phone.trim()}>{busy ? "Sending code…" : "Send verification code"}</button>
            </form>
          ) : !phoneVerified ? (
            <form onSubmit={verifyOtp} className="auth-form">
              <label htmlFor="phone-code">Six-digit SMS verification code</label>
              <input id="phone-code" type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))} required />
              <button type="submit" className="run-button" disabled={busy || code.length !== 6}>{busy ? "Verifying…" : "Verify phone"}</button>
              <button type="button" className="voice-button" onClick={resetPhone} disabled={busy}>Change phone number</button>
            </form>
          ) : pinMode ? (
            <form onSubmit={submitPin} className="auth-form">
              <label htmlFor="household-pin">{pinMode === "setup" ? "Create an eight-digit household PIN" : "Enter your eight-digit household PIN"}</label>
              <input id="household-pin" type="password" inputMode="numeric" autoComplete="off" pattern="[0-9]{8}" maxLength={8} value={pin} onChange={(event) => setPin(event.target.value.replace(/\D/g, "").slice(0, 8))} required />
              <button type="submit" className="run-button" disabled={busy || pin.length !== 8}>{busy ? "Verifying…" : pinMode === "setup" ? "Create PIN and continue" : "Unlock household"}</button>
              <button type="button" className="voice-button" onClick={resetPhone} disabled={busy}>Use another phone</button>
            </form>
          ) : (
            <div className="auth-form">
              <p>Phone verified, but household identity setup is unavailable. The membership migration and server configuration must be completed before household data can be accessed.</p>
              <button type="button" className="run-button" disabled={busy} onClick={async () => { setBusy(true); try { await checkPinMode(); } catch (cause) { setError(cause instanceof Error ? cause.message : "Household setup unavailable."); } finally { setBusy(false); } }}>Retry household setup</button>
              <button type="button" className="voice-button" onClick={resetPhone} disabled={busy}>Use another phone</button>
            </div>
          )}

          {notice && <p role="status" aria-live="polite">{notice}</p>}
          {error && <p className="voice-error" role="alert" aria-live="assertive">{error}</p>}
          <p className="consent-intro">The household PIN is separate from the SMS code. It is stored only as a server-keyed hash, rate-limited, and never sent to the backend agent. Household memory and outbound-call consent start disabled.</p>
        </section>
      </div>
    </main>
  );
}