import { Buffer } from "node:buffer";
import { isIP } from "node:net";
import { createHmac } from "node:crypto";

const POLICIES = {
  "api/v1/agent": { method: "POST", kind: "json", maxBytes: 64 * 1024, timeoutMs: 12_000 },
  "api/v1/voice/turn": { method: "POST", kind: "multipart", maxBytes: 10 * 1024 * 1024, timeoutMs: 45_000 },
  "api/v1/documents/ocr": { method: "POST", kind: "multipart", maxBytes: 9 * 1024 * 1024, timeoutMs: 25_000 },
  "api/v1/household/consent": { method: "POST", kind: "consent", maxBytes: 4096, timeoutMs: 8_000 },
  "api/v1/household/tasks": { method: "POST", kind: "task", maxBytes: 8192, timeoutMs: 8_000 },
  "api/v1/household/tasks/status": { method: "POST", kind: "task_status", maxBytes: 4096, timeoutMs: 8_000 },
  "api/v1/household/memories": { method: "POST", kind: "memory", maxBytes: 8192, timeoutMs: 8_000 },
  "api/v1/household/memories/delete": { method: "POST", kind: "memory_delete", maxBytes: 4096, timeoutMs: 8_000 },
};
const READ_ROUTES = new Set(["health/ready", "health/live", "api/v1/household/consent", "api/v1/household/tasks", "api/v1/household/memories"]);
const buckets = new Map();
const WINDOW_MS = 60_000;
const REQUEST_LIMIT = 30;

function errorResponse(status, detail) {
  return Response.json({ detail }, { status, headers: { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" } });
}

function isRateLimited(request) {
  // Host must overwrite X-Real-IP. This is a per-instance safety net, not a shared limiter.
  const suppliedIp = request.headers.get("x-real-ip")?.trim();
  const ip = suppliedIp && isIP(suppliedIp) ? suppliedIp : "unknown";
  const now = Date.now();
  let bucket = buckets.get(ip);
  if (!bucket || now - bucket.startedAt >= WINDOW_MS) {
    bucket = { startedAt: now, count: 0 };
    buckets.delete(ip);
    buckets.set(ip, bucket);
  }
  bucket.count += 1;
  // Expire old buckets opportunistically, then evict the oldest bucket if a
  // high-cardinality request stream still exceeds the hard memory ceiling.
  if (buckets.size > 2000) {
    for (const [key, value] of buckets) {
      if (now - value.startedAt >= WINDOW_MS) buckets.delete(key);
      if (buckets.size <= 2000) break;
    }
  }
  if (buckets.size > 2000) buckets.delete(buckets.keys().next().value);
  return bucket.count > REQUEST_LIMIT;
}

function clientIp(request, env) {
  const headerName = env.SAATHI_TRUSTED_CLIENT_IP_HEADER?.trim().toLowerCase();
  if (!headerName || !["x-real-ip", "x-forwarded-for", "x-vercel-forwarded-for", "cf-connecting-ip"].includes(headerName)) return "unknown";
  const value = request.headers.get(headerName)?.trim();
  return value && !value.includes(",") && isIP(value) ? value : "unknown";
}

function sharedRateLimitConfiguration(env) {
  const rawUrl = env.UPSTASH_REDIS_REST_URL?.trim();
  const token = env.UPSTASH_REDIS_REST_TOKEN?.trim();
  if (!rawUrl || !token) return null;
  try {
    const url = new URL(rawUrl);
    if (url.protocol !== "https:" || !url.hostname.endsWith(".upstash.io") || url.port || url.username || url.password || url.pathname !== "/" || url.search || url.hash) return null;
    return { url: url.origin, token };
  } catch {
    return null;
  }
}

const RATE_LIMIT_SCRIPT = "local count = redis.call('INCR', KEYS[1]); if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]); end; return count";

async function allowSharedRequest(key, limit, env, fetchImpl) {
  const configuration = sharedRateLimitConfiguration(env);
  if (!configuration) return { error: "shared_rate_limit_not_configured" };
  const digest = createHmac("sha256", configuration.token).update(key).digest("hex");
  try {
    const response = await fetchImpl(configuration.url, {
      method: "POST",
      headers: {
        authorization: `Bearer ${configuration.token}`,
        "content-type": "application/json",
        accept: "application/json",
      },
      body: JSON.stringify(["EVAL", RATE_LIMIT_SCRIPT, "1", `saathi:rate:v1:${digest}`, String(Math.ceil(WINDOW_MS / 1000))]),
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(2_500),
    });
    if (!response.ok) return { error: "shared_rate_limit_unavailable" };
    const payload = await response.json();
    const count = payload?.result;
    if (typeof count !== "number" || !Number.isSafeInteger(count) || count < 1) return { error: "shared_rate_limit_invalid_response" };
    return { allowed: count <= limit };
  } catch {
    return { error: "shared_rate_limit_unavailable" };
  }
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

export async function proxyRequest(request, segments = [], options = {}) {
  const path = Array.isArray(segments) ? segments.join("/") : "";
  const method = request.method.toUpperCase();
  const verifiedContext = options.verifiedContext ?? null;
  const readOnly = READ_ROUTES.has(path) && method === "GET";
  const policy = POLICIES[path];
  const householdRoute = path.startsWith("api/v1/household/");
  if (householdRoute && process.env.SAATHI_HOUSEHOLD_FEATURES_ENABLED !== "true") return errorResponse(503, "household_features_disabled");
  if (!readOnly && (!policy || policy.method !== method)) return errorResponse(404, "route_not_allowed");
  if (["api/v1/household/consent", "api/v1/household/tasks", "api/v1/household/tasks/status", "api/v1/household/memories", "api/v1/household/memories/delete"].includes(path) && !verifiedContext) return errorResponse(401, "verified_phone_identity_required");
  if (verifiedContext && (!/^[0-9a-f-]{36}$/i.test(verifiedContext.identityId) || !/^[0-9a-f-]{36}$/i.test(verifiedContext.householdId))) return errorResponse(403, "invalid_verified_household_context");
  const env = process.env;
  const rateKey = `${method}:${path}:${clientIp(request, env)}`;
  if (env.NODE_ENV === "production") {
    if (clientIp(request, env) === "unknown") return errorResponse(503, "trusted_client_ip_not_configured");
    const shared = await allowSharedRequest(rateKey, REQUEST_LIMIT, env, options.rateLimitFetchImpl ?? fetch);
    if (shared.error) return errorResponse(503, shared.error);
    if (!shared.allowed) return errorResponse(429, "rate_limit_exceeded");
  } else if (isRateLimited(request)) {
    return errorResponse(429, "rate_limit_exceeded");
  }
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
  if (verifiedContext) {
    headers.set("X-Saathi-Verified-Identity", verifiedContext.identityId);
    headers.set("X-Saathi-Verified-Household", verifiedContext.householdId);
  }
  let body;
  if (!readOnly) {
    const contentType = request.headers.get("content-type") || "";
    if (["json", "consent", "task", "task_status", "memory", "memory_delete"].includes(policy.kind) && !contentType.toLowerCase().startsWith("application/json")) return errorResponse(415, "application_json_required");
    if (policy.kind === "multipart" && (!contentType.toLowerCase().startsWith("multipart/form-data;") || !contentType.toLowerCase().includes("boundary="))) return errorResponse(415, "multipart_form_data_required");
    try { body = await readBoundedBody(request, policy.maxBytes, policy.timeoutMs); }
    catch (error) { return errorResponse(error?.status || 400, error?.message || "invalid_request_body"); }
    if (["json", "consent", "task", "task_status", "memory", "memory_delete"].includes(policy.kind)) {
      let parsed;
      try { parsed = JSON.parse(body.toString("utf8")); } catch { return errorResponse(400, "invalid_json"); }
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return errorResponse(400, "json_object_required");
      if (Object.hasOwn(parsed, "household_id") || Object.hasOwn(parsed, "user_id") || Object.hasOwn(parsed, "identity_id")) return errorResponse(400, "verified_household_identity_required");
      if (policy.kind === "json") {
        if (typeof parsed.message !== "string" || !parsed.message.trim() || parsed.message.length > 8000) return errorResponse(422, "valid_message_required");
        if (parsed.language !== undefined && (typeof parsed.language !== "string" || parsed.language.length > 20)) return errorResponse(422, "invalid_language");
        body = Buffer.from(JSON.stringify({ message: parsed.message, ...(parsed.language ? { language: parsed.language } : {}) }));
      } else if (policy.kind === "consent") {
        if (!["memory", "outbound_calls"].includes(parsed.purpose) || typeof parsed.granted !== "boolean") return errorResponse(422, "valid_consent_purpose_and_boolean_required");
        body = Buffer.from(JSON.stringify({ purpose: parsed.purpose, granted: parsed.granted }));
      } else if (policy.kind === "task") {
        if (typeof parsed.title !== "string" || !parsed.title.trim() || parsed.title.trim().length > 300) return errorResponse(422, "valid_task_title_required");
        if (parsed.missing_items !== undefined && (!Array.isArray(parsed.missing_items) || parsed.missing_items.length > 20 || parsed.missing_items.some((item) => typeof item !== "string" || item.trim().length > 200))) return errorResponse(422, "invalid_task_missing_items");
        if (parsed.idempotency_key !== undefined && (typeof parsed.idempotency_key !== "string" || parsed.idempotency_key.length < 1 || parsed.idempotency_key.length > 160)) return errorResponse(422, "invalid_task_idempotency_key");
        body = Buffer.from(JSON.stringify({
          title: parsed.title.trim(),
          missing_items: (parsed.missing_items || []).map((item) => item.trim()).filter(Boolean),
          ...(parsed.idempotency_key ? { idempotency_key: parsed.idempotency_key } : {}),
        }));
      } else if (policy.kind === "task_status") {
        if (typeof parsed.task_id !== "string" || !/^[0-9a-f-]{36}$/i.test(parsed.task_id) || !["completed", "cancelled"].includes(parsed.status)) return errorResponse(422, "valid_task_status_update_required");
        body = Buffer.from(JSON.stringify({ task_id: parsed.task_id, status: parsed.status }));
      } else if (policy.kind === "memory") {
        if (typeof parsed.memory_type !== "string" || !parsed.memory_type.trim() || parsed.memory_type.trim().length > 80) return errorResponse(422, "valid_memory_type_required");
        if (typeof parsed.key_name !== "string" || !parsed.key_name.trim() || parsed.key_name.trim().length > 120) return errorResponse(422, "valid_memory_key_required");
        if (typeof parsed.value_text !== "string" || !parsed.value_text.trim() || parsed.value_text.trim().length > 2000) return errorResponse(422, "valid_memory_value_required");
        body = Buffer.from(JSON.stringify({ memory_type: parsed.memory_type.trim(), key_name: parsed.key_name.trim(), value_text: parsed.value_text.trim() }));
      } else {
        if (typeof parsed.memory_id !== "string" || !/^[0-9a-f-]{36}$/i.test(parsed.memory_id)) return errorResponse(422, "valid_memory_id_required");
        body = Buffer.from(JSON.stringify({ memory_id: parsed.memory_id }));
      }
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
export function _rateLimitBucketCountForTests() { return buckets.size; }
