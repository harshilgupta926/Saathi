import test from "node:test";
import assert from "node:assert/strict";
import { proxyRequest as rawProxyRequest, _resetRateLimitForTests, _rateLimitBucketCountForTests } from "../lib/backend-proxy.mjs";

function proxyRequest(request, segments, options = {}) {
  return rawProxyRequest(request, segments, {
    rateLimitFetchImpl: async () => Response.json({ result: 1 }),
    ...options,
  });
}

const originalFetch = globalThis.fetch;
const originalEnv = { ...process.env };
function setup() { _resetRateLimitForTests(); process.env.NODE_ENV = "production"; process.env.BACKEND_API_URL = "https://api.example.test"; process.env.SAATHI_API_AUTH_TOKEN = "x".repeat(40); process.env.UPSTASH_REDIS_REST_URL = "https://saathi-test.upstash.io"; process.env.UPSTASH_REDIS_REST_TOKEN = "test-only-token-not-a-secret"; process.env.SAATHI_TRUSTED_CLIENT_IP_HEADER = "x-real-ip"; }
function req(path, init = {}, ip = "192.0.2.10") { return new Request("https://web.example.test/backend/" + path, { ...init, headers: { "x-real-ip": ip, ...(init.headers || {}) } }); }
test.afterEach(() => {
  globalThis.fetch = originalFetch;
  for (const key of ["NODE_ENV", "BACKEND_API_URL", "SAATHI_API_AUTH_TOKEN", "UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN", "SAATHI_TRUSTED_CLIENT_IP_HEADER"]) { if (originalEnv[key] === undefined) delete process.env[key]; else process.env[key] = originalEnv[key]; }
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
test("enforces a per-instance request limit in development", async () => { setup(); process.env.NODE_ENV = "development"; globalThis.fetch = async () => Response.json({ status: "alive" }); let r; for (let i=0;i<31;i++) r = await proxyRequest(req("health/live", {}, "198.51.100.77"), ["health","live"]); assert.equal(r.status, 429); });


test("rate-limit bucket storage stays bounded under high-cardinality IP input", async () => {
  setup();
  process.env.NODE_ENV = "development";
  globalThis.fetch = async () => Response.json({ status: "alive" });
  for (let i = 0; i < 2_500; i += 1) {
    const ip = `198.18.${Math.floor(i / 256)}.${i % 256}`;
    const response = await proxyRequest(req("health/live", {}, ip), ["health", "live"]);
    assert.equal(response.status, 200);
  }
  assert.ok(_rateLimitBucketCountForTests() <= 2_000);
});


test("malformed X-Real-IP values cannot create unbounded distinct buckets", async () => {
  setup();
  process.env.NODE_ENV = "development";
  globalThis.fetch = async () => Response.json({ status: "alive" });
  let response;
  for (let i = 0; i < 31; i += 1) {
    response = await proxyRequest(req("health/live", {}, `not-an-ip-${i}`), ["health", "live"]);
  }
  assert.equal(response.status, 429);
  assert.equal(_rateLimitBucketCountForTests(), 1);
});


test("production fails closed when shared rate-limit configuration is missing", async () => {
  setup();
  delete process.env.UPSTASH_REDIS_REST_URL;
  let upstreamCalled = false;
  globalThis.fetch = async () => { upstreamCalled = true; return Response.json({ status: "alive" }); };
  const response = await proxyRequest(req("health/live"), ["health", "live"], { rateLimitFetchImpl: async () => { throw new Error("must not call limiter"); } });
  assert.equal(response.status, 503);
  assert.equal((await response.json()).detail, "shared_rate_limit_not_configured");
  assert.equal(upstreamCalled, false);
});

test("production rejects non-Upstash hosts and non-default ports", async () => {
  for (const url of ["https://redis.attacker.example", "https://saathi-test.upstash.io:8443"]) {
    setup(); process.env.UPSTASH_REDIS_REST_URL = url;
    let upstreamCalled = false;
    globalThis.fetch = async () => { upstreamCalled = true; return Response.json({ status: "alive" }); };
    const response = await proxyRequest(req("health/live"), ["health", "live"], { rateLimitFetchImpl: async () => { throw new Error("must not call limiter"); } });
    assert.equal(response.status, 503);
    assert.equal((await response.json()).detail, "shared_rate_limit_not_configured");
    assert.equal(upstreamCalled, false);
  }
});

test("production fails closed on malformed trusted client IP", async () => {
  setup();
  const response = await proxyRequest(req("health/live", {}, "spoofed, 198.51.100.1"), ["health", "live"]);
  assert.equal(response.status, 503);
  assert.equal((await response.json()).detail, "trusted_client_ip_not_configured");
});

test("shared rate limiter outage fails closed before backend call", async () => {
  setup();
  let upstreamCalled = false;
  globalThis.fetch = async () => { upstreamCalled = true; return Response.json({ status: "alive" }); };
  const response = await proxyRequest(req("health/live"), ["health", "live"], { rateLimitFetchImpl: async () => new Response("unavailable", { status: 503 }) });
  assert.equal(response.status, 503);
  assert.equal((await response.json()).detail, "shared_rate_limit_unavailable");
  assert.equal(upstreamCalled, false);
});

test("shared rate limiter rejects numeric-string counter values", async () => {
  setup();
  const response = await proxyRequest(req("health/live"), ["health", "live"], { rateLimitFetchImpl: async () => Response.json({ result: "1" }) });
  assert.equal(response.status, 503);
  assert.equal((await response.json()).detail, "shared_rate_limit_invalid_response");
});

test("shared rate limiter returns 429 when the atomic counter exceeds the limit", async () => {
  setup();
  const response = await proxyRequest(req("health/live"), ["health", "live"], { rateLimitFetchImpl: async () => Response.json({ result: 31 }) });
  assert.equal(response.status, 429);
  assert.equal((await response.json()).detail, "rate_limit_exceeded");
});


test("production uses an atomic shared counter with a pseudonymous Redis key", async () => {
  setup();
  let limiterUrl;
  let limiterInit;
  globalThis.fetch = async () => Response.json({ status: "alive" });
  const response = await proxyRequest(req("health/live", {}, "198.51.100.23"), ["health", "live"], {
    rateLimitFetchImpl: async (url, init) => {
      limiterUrl = url;
      limiterInit = init;
      return Response.json({ result: 1 });
    },
  });
  assert.equal(response.status, 200);
  assert.equal(limiterUrl, process.env.UPSTASH_REDIS_REST_URL);
  assert.equal(limiterInit.method, "POST");
  assert.equal(new Headers(limiterInit.headers).get("authorization"), `Bearer ${process.env.UPSTASH_REDIS_REST_TOKEN}`);
  const command = JSON.parse(limiterInit.body);
  assert.equal(command[0], "EVAL");
  assert.match(command[1], /redis\.call\('INCR'/);
  assert.match(command[3], /^saathi:rate:v1:[a-f0-9]{64}$/);
  assert.doesNotMatch(command[3], /198\.51\.100\.23/);
  assert.equal(command[4], "60");
});
