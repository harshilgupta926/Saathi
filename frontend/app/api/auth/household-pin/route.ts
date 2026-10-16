import { isAuthRateLimited } from "../../../../lib/auth-rate-limit.mjs";
import { readBoundedJson } from "../../../../lib/auth-request.mjs";
import {
  createHouseholdMembership,
  findHouseholdMembership,
  getVerifiedPhoneUser,
  hashHouseholdPin,
  isStrongHouseholdPin,
  setHouseholdContextCookie,
  verifyHouseholdPin,
} from "../../../../lib/household-identity";

function validOrigin(request: Request) {
  const origin = request.headers.get("origin");
  if (!origin) return true;
  try { return new URL(origin).origin === new URL(request.url).origin; } catch { return false; }
}

export async function GET() {
  if (process.env.SAATHI_HOUSEHOLD_FEATURES_ENABLED !== "true") return Response.json({ detail: "household_features_disabled" }, { status: 503, headers: { "Cache-Control": "no-store" } });
  try {
    const user = await getVerifiedPhoneUser();
    if (!user) return Response.json({ detail: "verified_phone_identity_required" }, { status: 401, headers: { "Cache-Control": "no-store" } });
    const membership = await findHouseholdMembership(user.id);
    return Response.json({ mode: membership ? "verify" : "setup" }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return Response.json({ detail: "household_identity_not_configured" }, { status: 503, headers: { "Cache-Control": "no-store" } });
  }
}

export async function POST(request: Request) {
  if (process.env.SAATHI_HOUSEHOLD_FEATURES_ENABLED !== "true") return Response.json({ detail: "household_features_disabled" }, { status: 503, headers: { "Cache-Control": "no-store" } });
  if (!validOrigin(request)) return Response.json({ detail: "origin_not_allowed" }, { status: 403 });
  if (!(request.headers.get("content-type") || "").toLowerCase().startsWith("application/json")) return Response.json({ detail: "application_json_required" }, { status: 415, headers: { "Cache-Control": "no-store" } });
  const parsed = await readBoundedJson(request);
  if (!parsed.ok) return Response.json({ detail: parsed.detail }, { status: parsed.status, headers: { "Cache-Control": "no-store" } });
  const body = parsed.value;
  if (!["setup", "verify"].includes(String(body.mode)) || typeof body.pin !== "string" || !isStrongHouseholdPin(body.pin)) {
    return Response.json({ detail: "strong_eight_digit_household_pin_required" }, { status: 422 });
  }

  let user;
  try { user = await getVerifiedPhoneUser(); }
  catch { return Response.json({ detail: "verified_phone_identity_required" }, { status: 401 }); }
  if (!user) return Response.json({ detail: "verified_phone_identity_required" }, { status: 401 });

  let limited: boolean;
  try { limited = await isAuthRateLimited(request, user.phone, "pin"); }
  catch { return Response.json({ detail: "auth_rate_limit_unavailable" }, { status: 503, headers: { "Cache-Control": "no-store" } }); }
  if (limited) return Response.json({ detail: "household_pin_rate_limited" }, { status: 429, headers: { "Cache-Control": "no-store" } });

  try {
    const existing = await findHouseholdMembership(user.id);
    let membership;
    if (body.mode === "setup") {
      if (existing) return Response.json({ detail: "household_pin_already_set" }, { status: 409 });
      const pinHash = hashHouseholdPin(user.id, body.pin);
      membership = await createHouseholdMembership(user, pinHash);
    } else {
      if (!existing) return Response.json({ detail: "household_pin_setup_required" }, { status: 409 });
      if (!verifyHouseholdPin(user.id, body.pin, existing.pin_hash)) {
        return Response.json({ detail: "household_pin_verification_failed" }, { status: 401, headers: { "Cache-Control": "no-store" } });
      }
      membership = existing;
    }
    await setHouseholdContextCookie(user.id, membership.household_id);
    return Response.json({ status: "household_verified" }, { headers: { "Cache-Control": "no-store" } });
  } catch (cause) {
    const message = cause instanceof Error ? cause.message : "";
    if (message === "household_pin_already_set") return Response.json({ detail: message }, { status: 409 });
    return Response.json({ detail: "household_identity_not_configured" }, { status: 503, headers: { "Cache-Control": "no-store" } });
  }
}