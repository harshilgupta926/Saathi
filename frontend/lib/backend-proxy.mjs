import { Buffer } from "node:buffer";

const POLICIES = {
  "api/v1/agent": { method: "POST", kind: "json", maxBytes: 64 * 1024, timeoutMs: 12_000 },
  "api/v1/voice/turn": { method: "POST", kind: "multipart", maxBytes: 10 * 1024 * 1024, timeoutMs: 45_000 },
};
const READ_ROUTES = new Set(["health/ready", "health/live"]);
const buckets = new Map();
const WINDOW_MS = 60_000;
const REQUEST_LIMIT = 30;

function errorResponse(status, detail) {
  return Response.json({ detail }, { status, headers: { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" } });
}

function isRateLimited(request) {
  // Host must overwrite X-Real-IP. This is a per-instance safety net, not a shared limiter.
  const ip = request.headers.get("x-real-ip") || "unknown";
  const now = Date.now();
  let bucket = buckets.get(ip);
  if (!bucket || now - bucket.startedAt >= WINDOW_MS) { bucket = { startedAt: now, count: 0 }; buckets.set(ip, bucket); }
  bucket.count += 1;
  if (buckets.size > 2000) for (const [key, value] of buckets) if (now - value.startedAt >= WINDOW_MS) buckets.delete(key);
  return bucket.count > REQUEST_LIMIT;
}

async function readBoundedBody(request, maxBytes, timeoutMs) {
  const declared = Number(request.headers.get("content-length") || 0);
  if (declared > maxBytes) throw Object.assign(new Error("request_body_too_large"), { status: 413 });
  if (!request.body) return Buffer.alloc(0);
  const reader = request.body.getReader();
  const chunks = [];
  let total = 0;
  const deadline = Date.now() + timeoutMs;
  try {
    while (true) {
      const remaining = deadline - Date.now();
      if (remaining <= 0) throw Object.assign(new Error("request_body_timeout"), { status: 408 });
      let timer;
      const timeout = new Promise((_, reject) => { timer = setTimeout(() => reject(Object.assign(new Error("request_body_timeout"), { status: 408 })), remaining); });
      let part;
      try { part = await Promise.race([reader.read(), timeout]); } finally { clearTimeout(timer); }
      if (part.done) break;
      total += part.value.byteLength;
      if (total > maxBytes) throw Object.assign(new Error("request_body_too_large"), { status: 413 });
      chunks.push(Buffer.from(part.value));
    }
  } catch (error) {
    try { await reader.cancel(); } catch {}
    throw error;
  } finally { reader.releaseLock(); }
  return Buffer.concat(chunks, total);
}

export async function proxyRequest(request, segments = []) {
  const path = Array.isArray(segments) ? segments.join("/") : "";
  const method = request.method.toUpperCase();
  const readOnly = READ_ROUTES.has(path) && method === "GET";
  const policy = POLICIES[path];
  if (!readOnly && (!policy || policy.method !== method)) return errorResponse(404, "route_not_allowed");
  if (isRateLimited(request)) return errorResponse(429, "rate_limit_exceeded");
  if (method !== "GET") {
    const origin = request.headers.get("origin");
    if (origin) {
      try { if (new URL(origin).origin !== new URL(request.url).origin) return errorResponse(403, "origin_not_allowed"); }
      catch { return errorResponse(403, "origin_not_allowed"); }
    }
  }
  const rawBackend = process.env.BACKEND_API_URL || (process.env.NODE_ENV === "development" ? "http://localhost:8000" : "");
  const backend = rawBackend.endsWith("/") ? rawBackend.slice(0, -1) : rawBackend;
  if (!backend) return errorResponse(503, "backend_api_url_not_configured");
  const token = process.env.SAATHI_API_AUTH_TOKEN || "";
  if (process.env.NODE_ENV === "production" && token.length < 32) return errorResponse(503, "api_operator_auth_not_configured");
  const headers = new Headers({ Accept: "application/json" });
  let body;
  if (!readOnly) {
    const contentType = request.headers.get("content-type") || "";
    if (policy.kind === "json" && !contentType.toLowerCase().startsWith("application/json")) return errorResponse(415, "application_json_required");
    if (policy.kind === "multipart" && (!contentType.toLowerCase().startsWith("multipart/form-data;") || !contentType.toLowerCase().includes("boundary="))) return errorResponse(415, "multipart_form_data_required");
    try { body = await readBoundedBody(request, policy.maxBytes, policy.timeoutMs); }
    catch (error) { return errorResponse(error?.status || 400, error?.message || "invalid_request_body"); }
    if (policy.kind === "json") {
      let parsed;
      try { parsed = JSON.parse(body.toString("utf8")); } catch { return errorResponse(400, "invalid_json"); }
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return errorResponse(400, "json_object_required");
      if (Object.hasOwn(parsed, "household_id")) return errorResponse(400, "verified_household_identity_required");
      if (typeof parsed.message !== "string" || !parsed.message.trim() || parsed.message.length > 8000) return errorResponse(422, "valid_message_required");
      if (parsed.language !== undefined && (typeof parsed.language !== "string" || parsed.language.length > 20)) return errorResponse(422, "invalid_language");
      body = Buffer.from(JSON.stringify({ message: parsed.message, ...(parsed.language ? { language: parsed.language } : {}) }));
      headers.set("Content-Type", "application/json");
    } else {
      if (/name="household_id"/i.test(body.toString("latin1"))) return errorResponse(400, "verified_household_identity_required");
      headers.set("Content-Type", contentType);
    }
  }
  if (token) headers.set("X-Saathi-API-Key", token);
  const correlationId = request.headers.get("x-correlation-id");
  if (correlationId && /^[a-zA-Z0-9._:-]{1,128}$/.test(correlationId)) headers.set("X-Correlation-ID", correlationId);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), policy?.timeoutMs || 5000);
  try {
    const url = new URL(path, backend + "/");
    const response = await fetch(url, { method, headers, body: method === "GET" ? undefined : body, redirect: "manual", cache: "no-store", signal: controller.signal });
    if (response.status >= 300 && response.status < 400) return errorResponse(502, "backend_redirect_rejected");
    const payload = await response.arrayBuffer();
    if (payload.byteLength > 2 * 1024 * 1024) return errorResponse(502, "backend_response_too_large");
    const outputHeaders = new Headers({ "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" });
    const outputType = response.headers.get("content-type");
    if (outputType && outputType.toLowerCase().startsWith("application/json")) outputHeaders.set("Content-Type", outputType);
    const outputCorrelation = response.headers.get("x-correlation-id");
    if (outputCorrelation) outputHeaders.set("X-Correlation-ID", outputCorrelation);
    return new Response(payload, { status: response.status, headers: outputHeaders });
  } catch (error) {
    return errorResponse(error?.name === "AbortError" ? 504 : 502, error?.name === "AbortError" ? "backend_timeout" : "backend_unavailable");
  } finally { clearTimeout(timer); }
}

export function _resetRateLimitForTests() { buckets.clear(); }
