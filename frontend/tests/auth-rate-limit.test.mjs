import test from "node:test";
import assert from "node:assert/strict";
import { isAuthRateLimited, _resetAuthRateLimitForTests, _authRateLimitBucketCountForTests } from "../lib/auth-rate-limit.mjs";

const originalEnv = { ...process.env };
const originalFetch = globalThis.fetch;
test.beforeEach(() => {
  process.env.NODE_ENV = "test";
  process.env.SAATHI_TRUSTED_CLIENT_IP_HEADER = "x-real-ip";
  _resetAuthRateLimitForTests();
});
test.afterEach(() => {
  for (const key of ["NODE_ENV", "SAATHI_TRUSTED_CLIENT_IP_HEADER", "UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"]) {
    if (originalEnv[key] === undefined) delete process.env[key];
    else process.env[key] = originalEnv[key];
  }
  globalThis.fetch = originalFetch;
  _resetAuthRateLimitForTests();
});

test("OTP sends are limited per phone and per host IP", async () => {
  const request = new Request("https://saathi.example.com/api/auth/otp", { headers: { "x-real-ip": "192.0.2.15" } });
  assert.equal(await isAuthRateLimited(request, "+919876543210", "otp"), false);
  assert.equal(await isAuthRateLimited(request, "+919876543210", "otp"), false);
  assert.equal(await isAuthRateLimited(request, "+919876543210", "otp"), false);
  assert.equal(await isAuthRateLimited(request, "+919876543210", "otp"), true);
});

test("OTP verification has a separate attempt budget", async () => {
  const request = new Request("https://saathi.example.com/api/auth/verify", { headers: { "x-real-ip": "192.0.2.16" } });
  for (let i = 0; i < 10; i++) assert.equal(await isAuthRateLimited(request, "+919876543211", "verify"), false);
  assert.equal(await isAuthRateLimited(request, "+919876543211", "verify"), true);
});


test("production OTP limits fail closed without shared Redis configuration", async () => {
  process.env.NODE_ENV = "production";
  process.env.SAATHI_TRUSTED_CLIENT_IP_HEADER = "x-real-ip";
  delete process.env.UPSTASH_REDIS_REST_URL;
  delete process.env.UPSTASH_REDIS_REST_TOKEN;
  const request = new Request("https://saathi.example.com/api/auth/otp", { headers: { "x-real-ip": "192.0.2.25" } });
  await assert.rejects(isAuthRateLimited(request, "+919876543212", "otp"), /shared_rate_limit_not_configured/);
});

test("production OTP limits use atomic shared counters and hash identity keys", async () => {
  process.env.NODE_ENV = "production";
  process.env.SAATHI_TRUSTED_CLIENT_IP_HEADER = "x-real-ip";
  process.env.UPSTASH_REDIS_REST_URL = "https://saathi-test.upstash.io";
  process.env.UPSTASH_REDIS_REST_TOKEN = "test-only-token-never-used-outside-this-unit-test";
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options, command: JSON.parse(options.body) });
    return Response.json({ result: calls.length === 1 ? 4 : 1 });
  };
  const request = new Request("https://saathi.example.com/api/auth/otp", { headers: { "x-real-ip": "192.0.2.26" } });
  assert.equal(await isAuthRateLimited(request, "+919876543213", "otp"), true);
  assert.equal(calls.length, 2);
  assert.ok(calls.every((call) => call.url === "https://saathi-test.upstash.io"));
  assert.ok(calls.every((call) => String(call.command[3]).startsWith("saathi:auth:v1:")));
  assert.ok(calls.every((call) => !JSON.stringify(call.command).includes("+919876543213")));
});


test("production rejects missing trusted client IP before any Upstash request", async () => {
  process.env.NODE_ENV = "production";
  process.env.SAATHI_TRUSTED_CLIENT_IP_HEADER = "x-real-ip";
  process.env.UPSTASH_REDIS_REST_URL = "https://saathi-test.upstash.io";
  process.env.UPSTASH_REDIS_REST_TOKEN = "test-only-token";
  let calls = 0;
  globalThis.fetch = async () => { calls += 1; return Response.json({ result: 1 }); };
  const request = new Request("https://saathi.example.com/api/auth/otp");
  await assert.rejects(isAuthRateLimited(request, "+919876543214", "otp"), /trusted_client_ip_invalid/);
  assert.equal(calls, 0);
});

test("production rejects malformed and comma-separated trusted client IP before any Upstash request", async () => {
  process.env.NODE_ENV = "production";
  process.env.SAATHI_TRUSTED_CLIENT_IP_HEADER = "x-real-ip";
  process.env.UPSTASH_REDIS_REST_URL = "https://saathi-test.upstash.io";
  process.env.UPSTASH_REDIS_REST_TOKEN = "test-only-token";
  let calls = 0;
  globalThis.fetch = async () => { calls += 1; return Response.json({ result: 1 }); };
  for (const ip of ["not-an-ip", "192.0.2.1, 192.0.2.2", "192.0.2.1:443", "[2001:db8::1], 2001:db8::2"]) {
    const request = new Request("https://saathi.example.com/api/auth/otp", { headers: { "x-real-ip": ip } });
    await assert.rejects(isAuthRateLimited(request, "+919876543215", "otp"), /trusted_client_ip_invalid/);
  }
  assert.equal(calls, 0);
});

test("production rejects unconfigured trusted IP header before any Upstash request", async () => {
  process.env.NODE_ENV = "production";
  delete process.env.SAATHI_TRUSTED_CLIENT_IP_HEADER;
  process.env.UPSTASH_REDIS_REST_URL = "https://saathi-test.upstash.io";
  process.env.UPSTASH_REDIS_REST_TOKEN = "test-only-token";
  let calls = 0;
  globalThis.fetch = async () => { calls += 1; return Response.json({ result: 1 }); };
  const request = new Request("https://saathi.example.com/api/auth/otp", { headers: { "x-real-ip": "192.0.2.27" } });
  await assert.rejects(isAuthRateLimited(request, "+919876543216", "otp"), /trusted_client_ip_not_configured/);
  assert.equal(calls, 0);
});


test("development rate-limit bucket storage remains bounded under high-cardinality traffic", async () => {
  process.env.NODE_ENV = "development";
  for (let i = 0; i < 5_100; i += 1) {
    const ip = `198.18.${Math.floor(i / 256)}.${i % 256}`;
    const request = new Request("https://saathi.example.com/api/auth/otp", { headers: { "x-real-ip": ip } });
    await isAuthRateLimited(request, "+919876543217", "test");
  }
  assert.ok(_authRateLimitBucketCountForTests() <= 5_000);
});