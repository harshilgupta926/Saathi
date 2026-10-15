import test from "node:test";
import assert from "node:assert/strict";
import { proxyRequest, _resetRateLimitForTests } from "../lib/backend-proxy.mjs";

const originalFetch = globalThis.fetch;
const originalEnv = { ...process.env };
function setup() { _resetRateLimitForTests(); process.env.NODE_ENV = "production"; process.env.BACKEND_API_URL = "https://api.example.test"; process.env.SAATHI_API_AUTH_TOKEN = "x".repeat(40); }
function req(path, init = {}, ip = "192.0.2.10") { return new Request("https://web.example.test/backend/" + path, { ...init, headers: { "x-real-ip": ip, ...(init.headers || {}) } }); }
test.afterEach(() => {
  globalThis.fetch = originalFetch;
  for (const key of ["NODE_ENV", "BACKEND_API_URL", "SAATHI_API_AUTH_TOKEN"]) { if (originalEnv[key] === undefined) delete process.env[key]; else process.env[key] = originalEnv[key]; }
  _resetRateLimitForTests();
});
test("rejects unlisted routes without contacting upstream", async () => { setup(); let called = false; globalThis.fetch = async () => { called = true; }; const r = await proxyRequest(req("api/v1/telephony/call", { method: "POST" }), ["api","v1","telephony","call"]); assert.equal(r.status, 404); assert.equal(called, false); });
test("rejects wrong methods", async () => { setup(); const r = await proxyRequest(req("api/v1/agent", { method: "GET" }), ["api","v1","agent"]); assert.equal(r.status, 404); });
test("fails closed when production token is missing", async () => { setup(); delete process.env.SAATHI_API_AUTH_TOKEN; const r = await proxyRequest(req("health/ready"), ["health","ready"]); assert.equal(r.status, 503); });
test("fails closed when production backend URL is missing", async () => { setup(); delete process.env.BACKEND_API_URL; const r = await proxyRequest(req("health/live"), ["health","live"]); assert.equal(r.status, 503); });
test("injects server token and strips caller authorization", async () => { setup(); let init; globalThis.fetch = async (_url, options) => { init = options; return Response.json({ reply: "ok" }); }; const r = await proxyRequest(req("api/v1/agent", { method: "POST", headers: { "content-type": "application/json", authorization: "Bearer attacker" }, body: JSON.stringify({ message: "नमस्ते", language: "hi" }) }), ["api","v1","agent"]); assert.equal(r.status, 200); assert.equal(new Headers(init.headers).get("X-Saathi-API-Key"), "x".repeat(40)); assert.equal(new Headers(init.headers).get("authorization"), null); assert.equal(init.redirect, "manual"); });
test("rejects client-supplied household id", async () => { setup(); globalThis.fetch = async () => { throw Error("must not fetch"); }; const r = await proxyRequest(req("api/v1/agent", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ message: "hi", household_id: "other" }) }), ["api","v1","agent"]); assert.equal(r.status, 400); });
test("rejects malformed JSON and unsupported content types", async () => { setup(); let r = await proxyRequest(req("api/v1/agent", { method: "POST", headers: { "content-type": "application/json" }, body: "{" }), ["api","v1","agent"]); assert.equal(r.status, 400); r = await proxyRequest(req("api/v1/agent", { method: "POST", headers: { "content-type": "text/plain" }, body: "hi" }), ["api","v1","agent"]); assert.equal(r.status, 415); });
test("rejects oversized declared body", async () => { setup(); globalThis.fetch = async () => { throw Error("must not fetch"); }; const r = await proxyRequest(req("api/v1/agent", { method: "POST", headers: { "content-type": "application/json", "content-length": "999999" }, body: JSON.stringify({ message: "hi" }) }), ["api","v1","agent"]); assert.equal(r.status, 413); });
test("rejects cross-origin mutation", async () => { setup(); const r = await proxyRequest(req("api/v1/agent", { method: "POST", headers: { "content-type": "application/json", origin: "https://evil.example" }, body: JSON.stringify({ message: "hi" }) }), ["api","v1","agent"]); assert.equal(r.status, 403); });
test("does not follow backend redirects", async () => { setup(); globalThis.fetch = async () => new Response(null, { status: 302, headers: { location: "https://evil.example" } }); const r = await proxyRequest(req("health/live"), ["health","live"]); assert.equal(r.status, 502); });
test("preserves upstream status and disables caching", async () => { setup(); globalThis.fetch = async () => Response.json({ detail: "offline" }, { status: 503 }); const r = await proxyRequest(req("health/ready"), ["health","ready"]); assert.equal(r.status, 503); assert.equal(r.headers.get("cache-control"), "no-store"); });
test("enforces a per-instance request limit", async () => { setup(); globalThis.fetch = async () => Response.json({ status: "alive" }); let r; for (let i=0;i<31;i++) r = await proxyRequest(req("health/live", {}, "198.51.100.77"), ["health","live"]); assert.equal(r.status, 429); });
