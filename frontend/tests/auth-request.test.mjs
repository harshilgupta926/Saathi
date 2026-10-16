import test from "node:test";
import assert from "node:assert/strict";
import { readBoundedJson } from "../lib/auth-request.mjs";

test("reads a valid bounded JSON object", async () => {
  const request = new Request("https://saathi.example.test/api/auth/otp", {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ phone: "+919876543210" }),
  });
  const result = await readBoundedJson(request);
  assert.equal(result.ok, true);
  if (result.ok) assert.deepEqual(result.value, { phone: "+919876543210" });
});

test("rejects a declared oversized body before reading", async () => {
  const request = new Request("https://saathi.example.test/api/auth/otp", {
    method: "POST", headers: { "content-length": "5000" }, body: "{}",
  });
  const result = await readBoundedJson(request);
  assert.deepEqual(result, { ok: false, status: 413, detail: "request_body_too_large" });
});

test("rejects streamed bodies that exceed the byte limit without Content-Length", async () => {
  const body = new ReadableStream({
    start(controller) { controller.enqueue(new TextEncoder().encode(JSON.stringify({ value: "x".repeat(5000) }))); controller.close(); },
  });
  const request = new Request("https://saathi.example.test/api/auth/otp", { method: "POST", body, duplex: "half" });
  const result = await readBoundedJson(request);
  assert.deepEqual(result, { ok: false, status: 413, detail: "request_body_too_large" });
});

test("rejects malformed JSON, arrays, primitives and invalid UTF-8", async () => {
  for (const raw of ["{", "[]", "42", "null"]) {
    const result = await readBoundedJson(new Request("https://saathi.example.test", { method: "POST", body: raw }));
    assert.equal(result.ok, false);
  }
  const body = new ReadableStream({ start(controller) { controller.enqueue(new Uint8Array([0xff, 0xfe])); controller.close(); } });
  const request = new Request("https://saathi.example.test", { method: "POST", body, duplex: "half" });
  assert.equal((await readBoundedJson(request)).ok, false);
});

test("times out a stalled streamed request body", async () => {
  const body = new ReadableStream({ start() {} });
  const request = new Request("https://saathi.example.test/api/auth/otp", { method: "POST", body, duplex: "half" });
  const result = await readBoundedJson(request, 4096, 10);
  assert.deepEqual(result, { ok: false, status: 408, detail: "request_body_timeout" });
});