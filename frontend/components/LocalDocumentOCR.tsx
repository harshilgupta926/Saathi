"use client";

import { type FormEvent, useState } from "react";
import { FileText, ShieldCheck, Upload } from "lucide-react";

type OCRResult = {
  text: string;
  engine: string;
  language: string;
  average_confidence: number | null;
  needs_human_review: boolean;
  network_used: boolean;
};

const MAX_BYTES = 8 * 1024 * 1024;
const ACCEPTED_TYPES = new Set(["image/png", "image/jpeg", "image/webp", "image/tiff"]);

export default function LocalDocumentOCR({ available = false }: { available?: boolean }) {
  const [file, setFile] = useState<File | null>(null);
  const [language, setLanguage] = useState("hin+eng");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OCRResult | null>(null);

  const chooseFile = (candidate: File | null) => {
    setError(null);
    setResult(null);
    if (!candidate) {
      setFile(null);
      return;
    }
    if (!ACCEPTED_TYPES.has(candidate.type)) {
      setFile(null);
      setError("Choose a PNG, JPEG, WebP or TIFF image. PDF files are not supported yet.");
      return;
    }
    if (candidate.size > MAX_BYTES) {
      setFile(null);
      setError("This image is larger than 8 MB. Choose a smaller image.");
      return;
    }
    setFile(candidate);
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file || busy) return;
    setBusy(true);
    setError(null);
    setResult(null);
    const form = new FormData();
    form.append("file", file, file.name);
    form.append("language", language);
    try {
      const response = await fetch("/backend/api/v1/documents/ocr", {
        method: "POST",
        body: form,
        cache: "no-store",
        signal: AbortSignal.timeout(30_000),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof payload?.detail === "string" ? payload.detail : "";
        const messages: Record<string, string> = {
          local_ocr_engine_unavailable: "Local OCR is not installed on this server yet.",
          local_ocr_disabled: "Local OCR is disabled in this deployment.",
          local_ocr_timeout: "OCR took too long. Try a clearer or smaller image.",
          document_too_large: "The image is larger than the server limit.",
          unsupported_or_invalid_image: "The image type or file signature is not supported.",
          rate_limited: "Too many document requests. Wait a moment and try again.",
          backend_api_url_not_configured: "The Saathi backend is not connected.",
        };
        throw new Error(messages[detail] || "Saathi could not process this image. Try another image or type the information instead.");
      }
      setResult(payload as OCRResult);
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === "TimeoutError") {
        setError("The request timed out. Try a smaller image or type the information instead.");
      } else {
        setError(cause instanceof Error ? cause.message : "Document processing failed.");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="consent-card local-ocr-card" aria-labelledby="local-ocr-title">
      <div className="context-title">
        <div><span className="panel-kicker">LOCAL DOCUMENT HELPER</span><h3 id="local-ocr-title">Read a document with Saathi.</h3></div>
        <FileText size={19} aria-hidden="true" />
      </div>
      <p className="consent-intro">Extract text from a photo of a form or card using local OCR. The image is processed in memory and is not saved by this endpoint. This tool reads text; it does not verify eligibility or confirm that a document is genuine.</p>
      <form className="local-ocr-form" onSubmit={submit}>
        <div className="local-ocr-fields">
          <div>
            <label htmlFor="local-ocr-file">Choose an image (max 8 MB)</label>
            <input
              id="local-ocr-file"
              type="file"
              accept="image/png,image/jpeg,image/webp,image/tiff"
              onChange={(event) => chooseFile(event.target.files?.[0] || null)}
              disabled={busy}
              required
            />
            {file && <span className="local-ocr-file-name">{file.name} · {(file.size / 1024).toFixed(0)} KB</span>}
          </div>
          <div>
            <label htmlFor="local-ocr-language">Text language</label>
            <select id="local-ocr-language" value={language} onChange={(event) => setLanguage(event.target.value)} disabled={busy}>
              <option value="hin+eng">Hindi + English</option>
              <option value="hin">Hindi</option>
              <option value="eng">English</option>
            </select>
          </div>
        </div>
        <button type="submit" className="run-button local-ocr-submit" disabled={busy || !file || !available}>
          <Upload size={16} aria-hidden="true" /> {busy ? "Reading image…" : "Extract text locally"}
        </button>
      </form>
      {!available && <p className="consent-note" role="status">Local OCR is unavailable on this server. Install Tesseract with Hindi/English language data and enable local OCR to use this feature.</p>}
      {busy && <p className="local-ocr-status" role="status" aria-live="polite">Processing on the Saathi server. Keep this page open.</p>}
      {error && <p className="voice-error" role="alert" aria-live="assertive">{error}</p>}
      {result && (
        <div className="local-ocr-result" aria-labelledby="local-ocr-result-title">
          <div className="local-ocr-result-head">
            <strong id="local-ocr-result-title"><FileText size={15} aria-hidden="true" /> Extracted text</strong>
            <span>{result.average_confidence === null ? "Confidence unavailable" : String(Math.round(result.average_confidence)) + "% average confidence"}</span>
          </div>
          {result.text ? <pre>{result.text}</pre> : <p>No text was detected. Try a clearer, well-lit photo.</p>}
          {result.needs_human_review && <p className="local-ocr-review"><ShieldCheck size={15} aria-hidden="true" /> Please review every word against the original document before using this text.</p>}
          <small>Engine: {result.engine} · Language: {result.language} · Network used: {result.network_used ? "yes" : "no"}</small>
          <button type="button" className="voice-button" onClick={() => { void navigator.clipboard?.writeText(result.text).catch(() => setError("Clipboard access was denied. Select and copy the text manually.")); }}>Copy extracted text</button>
        </div>
      )}
      <p className="local-ocr-privacy"><ShieldCheck size={14} aria-hidden="true" /> Do not upload a document unless you have permission. Review extracted text yourself; OCR can make mistakes.</p>
    </section>
  );
}
