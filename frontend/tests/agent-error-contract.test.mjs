import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("../app/dashboard/page.tsx", import.meta.url), "utf8");

test("agent request has a bounded timeout and abort signal", () => {
  assert.match(source, /new AbortController\(\)/);
  assert.match(source, /setTimeout\(\(\) => controller\.abort\(\), 20_000\)/);
  assert.match(source, /signal: controller\.signal/);
  assert.match(source, /clearTimeout\(timeout\)/);
});

test("agent failures are represented as an error, never a fabricated answer", () => {
  assert.match(source, /setRequestError\(error instanceof DOMException/);
  assert.match(source, /Request not completed\./);
  assert.match(source, /role="alert" aria-live="assertive"/);
  assert.doesNotMatch(source, /setResult\(\{\s*reply: "Backend se connection nahi ho paaya/);
});

test("new requests clear stale results and expose a retry action", () => {
  assert.match(source, /setRequestError\(null\);\s*setResult\(null\);/);
  assert.match(source, /onClick=\{\(\) => void runAgent\(message\)\}/);
  assert.match(source, /disabled=\{loading \|\| !message\.trim\(\)\}>Retry/);
});

test("malformed API payloads are rejected before rendering", () => {
  assert.match(source, /const body: unknown = await response\.json\(\)/);
  assert.match(source, /typeof body\.reply !== "string"/);
  assert.match(source, /typeof body\.intent !== "string"/);
});
