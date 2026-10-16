import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const notFound = readFileSync(new URL("../app/not-found.tsx", import.meta.url), "utf8");
const errorPage = readFileSync(new URL("../app/error.tsx", import.meta.url), "utf8");
const globalError = readFileSync(new URL("../app/global-error.tsx", import.meta.url), "utf8");
const dashboardLayout = readFileSync(new URL("../app/dashboard/layout.tsx", import.meta.url), "utf8");

test("404 page offers accessible recovery links", () => {
  assert.match(notFound, /aria-labelledby="not-found-title"/);
  assert.match(notFound, /href="\/"|href=\{?"\/"\}?/);
  assert.match(notFound, /href="\/dashboard"/);
});

test("route error boundary offers retry and hides internal error details", () => {
  assert.match(errorPage, /onClick=\{reset\}/);
  assert.match(errorPage, /role="alert"/);
  assert.match(errorPage, /Internal error details are hidden/);
  assert.doesNotMatch(errorPage, /error\.stack|error\.message/);
});

test("global error boundary renders a complete document and recovery actions", () => {
  assert.match(globalError, /<html lang="en">/);
  assert.match(globalError, /<body/);
  assert.match(globalError, /onClick=\{reset\}/);
  assert.match(globalError, /href="\/"/);
  assert.doesNotMatch(globalError, /error\.stack|error\.message/);
});

test("dashboard has route-specific metadata that truthfully labels demo limitations", () => {
  assert.match(dashboardLayout, /title: "Household demo \| Saathi"/);
  assert.match(dashboardLayout, /automatic reminders and volunteer assignment require separate configuration and verification/);
  assert.match(dashboardLayout, /robots: \{ index: false, follow: false \}/);
});