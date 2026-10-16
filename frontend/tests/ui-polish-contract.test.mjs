import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");
const layout = await readFile(new URL("../app/layout.tsx", import.meta.url), "utf8");
const dashboard = await readFile(new URL("../app/dashboard/page.tsx", import.meta.url), "utf8");

test("Saathi UI uses visible keyboard focus and respects reduced motion", () => {
  assert.match(css, /focus-visible/);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
  assert.match(css, /--saathi-focus/);
});

test("touch targets remain usable on small screens and disabled controls communicate state", () => {
  assert.match(css, /touch-action:\s*manipulation/);
  assert.match(css, /button:disabled/);
  assert.match(css, /@media\s*\(max-width:\s*640px\)/);
  assert.match(dashboard, /disabled=\{loading \|\| !message\.trim\(\)\}/);
});

test("UI polish keeps existing response failures and provenance links", () => {
  assert.match(css, /--green:#183d32/);
  assert.match(css, /--saffron:#d9a64b/);
  assert.match(dashboard, /Request not completed\./);
  assert.match(dashboard, /View source/);
  assert.match(layout, /<nav className="site-nav"/);
});

test("motion effects are restricted to hover-capable devices and honor reduced-motion", () => {
  assert.match(css, /hover:hover/);
  assert.match(css, /prefers-reduced-motion:no-preference/);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
});
