import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const dashboard = readFileSync(fileURLToPath(new URL("../app/dashboard/page.tsx", import.meta.url)), "utf8");
const proxyRoute = readFileSync(fileURLToPath(new URL("../app/backend/[...path]/route.ts", import.meta.url)), "utf8");

test("household memory is explicit, user-entered and not auto-extracted", () => {
  assert.match(dashboard, /Nothing is extracted from conversations automatically/);
  assert.match(dashboard, /Save selected memory/);
  assert.match(dashboard, /deleteHouseholdMemory/);
  assert.match(dashboard, /consentStatus\?\.memory\.granted !== true/);
});

test("memory routes require verified household context in the server proxy", () => {
  assert.match(proxyRoute, /api\/v1\/household\/memories/);
  assert.match(proxyRoute, /resolveVerifiedHouseholdContext/);
});