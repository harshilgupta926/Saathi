import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const root = new URL("../../", import.meta.url);
const compose = readFileSync(fileURLToPath(new URL("docker-compose.yml", root)), "utf8");
const localAi = readFileSync(fileURLToPath(new URL("docker-compose.local-ai.yml", root)), "utf8");
const proxy = readFileSync(fileURLToPath(new URL("../lib/backend-proxy.mjs", import.meta.url)), "utf8");

test("base Compose frontend targets backend through an explicit local-only limiter", () => {
  assert.match(compose, /BACKEND_API_URL: http:\/\/backend:8000/);
  assert.match(compose, /APP_ENV: development/);
  assert.match(compose, /SAATHI_LOCAL_RATE_LIMITER_ENABLED: "true"/);
});

test("full local AI overlay really disables demo routing and selects Ollama", () => {
  assert.match(localAi, /DEMO_MODE: "false"/);
  assert.match(localAi, /LLM_PROVIDER: ollama/);
  assert.match(localAi, /LLM_MODEL: qwen2\.5:7b/);
  assert.match(localAi, /OLLAMA_BASE_URL: http:\/\/ollama:11434/);
  assert.match(localAi, /API_AUTH_TOKEN: \$\{SAATHI_API_AUTH_TOKEN:\?/);
  assert.match(localAi, /SAATHI_API_AUTH_TOKEN: \$\{SAATHI_API_AUTH_TOKEN:\?/);
  assert.match(localAi, /condition: service_completed_successfully/);
});

test("local rate limiter requires both explicit local flags and production still uses shared limiter", () => {
  assert.match(proxy, /env\.APP_ENV\?\.trim\(\)\.toLowerCase\(\) === "development"/);
  assert.match(proxy, /env\.SAATHI_LOCAL_RATE_LIMITER_ENABLED === "true"/);
  assert.match(proxy, /if \(env\.NODE_ENV === "production" && !explicitLocalDevelopment\)/);
  assert.match(proxy, /shared_rate_limit_not_configured/);
});
