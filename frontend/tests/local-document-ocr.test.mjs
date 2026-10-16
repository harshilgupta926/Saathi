import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const component = readFileSync(fileURLToPath(new URL("../components/LocalDocumentOCR.tsx", import.meta.url)), "utf8");
const dashboard = readFileSync(fileURLToPath(new URL("../app/dashboard/page.tsx", import.meta.url)), "utf8");
const proxy = readFileSync(fileURLToPath(new URL("../lib/backend-proxy.mjs", import.meta.url)), "utf8");

test("local OCR UI is discoverable, accessible, and capability-gated", () => {
  assert.match(dashboard, /import LocalDocumentOCR from "\.\.\/\.\.\/components\/LocalDocumentOCR"/);
  assert.match(dashboard, /<LocalDocumentOCR available=\{capabilities\.local_ocr === true\}/);
  assert.match(component, /htmlFor="local-ocr-file"/);
  assert.match(component, /htmlFor="local-ocr-language"/);
  assert.match(component, /role="alert" aria-live="assertive"/);
  assert.match(component, /role="status" aria-live="polite"/);
  assert.match(component, /disabled=\{busy \|\| !file \|\| !available\}/);
});

test("local OCR upload limits file types and size before sending", () => {
  assert.match(component, /MAX_BYTES = 8 \* 1024 \* 1024/);
  assert.match(component, /image\/png/);
  assert.match(component, /image\/jpeg/);
  assert.match(component, /image\/webp/);
  assert.match(component, /image\/tiff/);
  assert.match(component, /PDF files are not supported yet/);
  assert.match(component, /fetch\("\/backend\/api\/v1\/documents\/ocr"/);
  assert.match(component, /form\.append\("file", file, file\.name\)/);
  assert.match(component, /form\.append\("language", language\)/);
  assert.match(component, /Please review every word against the original document/);
  assert.match(component, /Network used:/);
});

test("backend proxy allowlists bounded multipart OCR without exposing server credentials", () => {
  assert.match(proxy, /"api\/v1\/documents\/ocr": \{ method: "POST", kind: "multipart", maxBytes: 9 \* 1024 \* 1024, timeoutMs: 25_000 \}/);
  assert.match(proxy, /if \(token\) headers\.set\("X-Saathi-API-Key", token\)/);
  assert.match(proxy, /request_body_too_large/);
});
