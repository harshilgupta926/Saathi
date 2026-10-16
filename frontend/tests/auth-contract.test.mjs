import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const read = (path) => readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8");
const server = read("../lib/supabase/server.ts");
const identity = read("../lib/household-identity.ts");
const login = read("../app/login/page.tsx");
const proxyRoute = read("../app/backend/[...path]/route.ts");
const consentRoute = read("../app/api/auth/verify/route.ts");
const pinRoute = read("../app/api/auth/household-pin/route.ts");
const signoutRoute = read("../app/api/auth/signout/route.ts");
const membershipMigration = read("../../docs/proposed-migrations/20261015080000_saathi_household_memberships.sql.proposed");
const backendProxyRoute = read("../app/backend/[...path]/route.ts");

test("Supabase SSR auth uses cookie sessions and publishable key only", () => {
  assert.match(server, /createServerClient/);
  assert.match(server, /cookieStore\.getAll\(\)/);
  assert.match(server, /NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY/);
  assert.doesNotMatch(server, /SUPABASE_SECRET_KEY/);
});

test("household binding requires confirmed E.164 phone and server-only secret", () => {
  assert.match(identity, /phone_confirmed_at/);
  assert.match(identity, /E164/);
  assert.match(identity, /SUPABASE_SECRET_KEY/);
  assert.match(identity, /saathi_household_memberships/);
  assert.match(identity, /auth_user_id/);
  assert.match(identity, /saathi_enroll_household/);
  assert.match(identity, /p_auth_user_id: user\.id/);
  assert.match(identity, /p_verified_phone: user\.phone/);
  assert.match(identity, /p_pin_hash: pinHash/);
  assert.doesNotMatch(identity, /NEXT_PUBLIC_SUPABASE_SECRET_KEY/);
});

test("OTP flow requires a verified six-digit SMS code", () => {
  assert.match(login, /\/api\/auth\/otp/);
  assert.match(login, /\/api\/auth\/verify/);
  assert.match(login, /autoComplete="one-time-code"/);
  assert.match(consentRoute, /verifyOtp/);
  assert.match(consentRoute, /phone_confirmed_at/);
});

test("proxy resolves household context server-side and protects consent routes", () => {
  assert.match(proxyRoute, /resolveVerifiedHouseholdContext/);
  assert.match(proxyRoute, /api\/v1\/household\/consent/);
  assert.match(proxyRoute, /household_identity_unavailable/);
  assert.match(proxyRoute, /household_pin_verification_required/);
  assert.match(proxyRoute, /api\/v1\/household\/tasks/);
  assert.match(proxyRoute, /api\/v1\/household\/memories/);
  assert.match(proxyRoute, /requiresUserAction \? 401 : 503/);
});

test("household PIN is separate, rate-limited and server-keyed", () => {
  assert.match(pinRoute, /isAuthRateLimited\(request, user\.phone, "pin"\)/);
  assert.match(pinRoute, /isStrongHouseholdPin\(body\.pin\)/);
  assert.match(identity, /const ascending = digits\.every/);
  assert.match(identity, /const descending = digits\.every/);
  assert.match(pinRoute, /verifyHouseholdPin\(user\.id, body\.pin, existing\.pin_hash\)/);
  assert.match(pinRoute, /setHouseholdContextCookie\(user\.id, membership\.household_id\)/);
  assert.match(identity, /HOUSEHOLD_PIN_PEPPER/);
  assert.match(identity, /HOUSEHOLD_CONTEXT_SIGNING_SECRET/);
  assert.match(identity, /httpOnly: true/);
  assert.match(signoutRoute, /clearHouseholdContextCookie/);
});

test("proposed membership migration denies browser access and remains syntactically complete", () => {
  assert.match(membershipMigration, /auth_user_id uuid NOT NULL UNIQUE REFERENCES auth\.users\(id\)/);
  assert.ok(membershipMigration.includes("pin_hash text NOT NULL CHECK (pin_hash ~ '^[0-9a-f]{64}$')"));
  assert.ok(membershipMigration.includes("verified_phone text NOT NULL CHECK"));
  assert.ok(membershipMigration.includes("[0-9]{7,14}$')"));
  assert.match(membershipMigration, /ENABLE ROW LEVEL SECURITY/);
  assert.match(membershipMigration, /REVOKE ALL ON TABLE public\.saathi_household_memberships FROM PUBLIC, anon, authenticated/);
  assert.match(membershipMigration, /REVOKE ALL ON TABLE public\.saathi_household_memberships FROM service_role/);
  assert.match(membershipMigration, /GRANT SELECT ON TABLE public\.saathi_household_memberships TO service_role/);
  assert.match(membershipMigration, /REVOKE ALL ON FUNCTION public\.saathi_enroll_household\(uuid, text, text\)\s+FROM PUBLIC, anon, authenticated/);
  assert.match(membershipMigration, /GRANT EXECUTE ON FUNCTION public\.saathi_enroll_household\(uuid, text, text\)\s+TO service_role/);
  assert.match(membershipMigration, /PROPOSED ONLY/);
  assert.equal(membershipMigration.trim().endsWith(";"), true);
  assert.equal((membershipMigration.match(/CREATE INDEX/g) || []).length, 1);
  assert.match(membershipMigration, /CREATE OR REPLACE FUNCTION public\.saathi_enroll_household/);
  assert.match(membershipMigration, /LANGUAGE plpgsql\s+SECURITY DEFINER\s+SET search_path = pg_catalog\s+AS \$saathi\$/);
  assert.match(membershipMigration, /PERFORM pg_catalog\.pg_advisory_xact_lock\(/);
  assert.match(membershipMigration, /pg_catalog\.hashtextextended\(p_auth_user_id::text, 0\)/);
  assert.match(membershipMigration, /REVOKE ALL ON FUNCTION public\.saathi_enroll_household\(uuid, text, text\)\s+FROM PUBLIC, anon, authenticated/);
  assert.match(membershipMigration, /GRANT EXECUTE ON FUNCTION public\.saathi_enroll_household\(uuid, text, text\)\s+TO service_role/);
});


test("household enrollment is atomic and serialized per Auth identity", () => {
  assert.match(identity, /\/rest\/v1\/rpc\/saathi_enroll_household/);
  assert.match(identity, /p_auth_user_id: user\.id/);
  assert.match(membershipMigration, /pg_advisory_xact_lock/);
  assert.match(membershipMigration, /hashtextextended\(p_auth_user_id::text, 0\)/);
  assert.match(membershipMigration, /ON CONFLICT \(phone_number\) DO NOTHING/);
  assert.match(membershipMigration, /VALUES \(NULL, FALSE, FALSE\)/);
});


test("anonymous conversation remains available while household data requires verified identity", () => {
  assert.match(backendProxyRoute, /householdRoutes\.has\(routePath\)/);
  assert.match(backendProxyRoute, /routePath === "api\/v1\/agent" \|\| routePath === "api\/v1\/voice\/turn"/);
  assert.match(backendProxyRoute, /try \{ verifiedContext = await resolveVerifiedHouseholdContext\(\); \} catch \{ verifiedContext = null; \}/);
  assert.match(backendProxyRoute, /if \(routePath === "api\/v1\/household\/consent" && !verifiedContext\)/);
});


test("atomic enrollment validates inputs, keeps consent off and never adopts by phone", () => {
  assert.match(membershipMigration, /p_verified_phone !~/);
  assert.match(membershipMigration, /p_pin_hash !~/);
  assert.match(membershipMigration, /WHERE h\.phone_number = p_verified_phone/);
  assert.match(membershipMigration, /phone_for_household := NULL/);
  assert.match(membershipMigration, /VALUES \(phone_for_household, FALSE, FALSE\)/);
  assert.match(membershipMigration, /INSERT INTO public\.saathi_household_memberships AS m/);
  assert.match(membershipMigration, /IF existing\.pin_hash <> p_pin_hash THEN/);
  assert.doesNotMatch(membershipMigration, /SELECT h\.id INTO household_uuid FROM public\.saathi_households AS h WHERE h\.phone_number = p_verified_phone/);
});

test("auth mutations require JSON and use a bounded streaming parser", () => {
  const requestReader = read("../lib/auth-request.mjs");
  for (const route of [read("../app/api/auth/otp/route.ts"), read("../app/api/auth/verify/route.ts"), pinRoute]) {
    assert.match(route, /application_json_required/);
    assert.match(route, /readBoundedJson\(request\)/);
    assert.doesNotMatch(route, /await request\.text\(\)/);
  }
  assert.match(requestReader, /request_body_too_large/);
  assert.match(requestReader, /request_body_timeout/);
  assert.match(requestReader, /new TextDecoder\("utf-8", \{ fatal: true \}\)/);
});

test("OTP and household PIN entry points require the explicit household feature flag", () => {
  for (const route of [read("../app/api/auth/otp/route.ts"), read("../app/api/auth/verify/route.ts"), read("../app/api/auth/household-pin/route.ts")]) {
    assert.match(route, /SAATHI_HOUSEHOLD_FEATURES_ENABLED !== "true"/);
    assert.match(route, /household_features_disabled/);
  }
  assert.match(backendProxyRoute, /SAATHI_HOUSEHOLD_FEATURES_ENABLED !== "true"/);
});
