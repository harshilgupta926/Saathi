import { isAuthRateLimited } from "../../../../lib/auth-rate-limit.mjs";
import { createSupabaseServerClient } from "../../../../lib/supabase/server";
import { readBoundedJson } from "../../../../lib/auth-request.mjs";

function validOrigin(request: Request) {
  const origin = request.headers.get("origin");
  if (!origin) return true;
  try { return new URL(origin).origin === new URL(request.url).origin; } catch { return false; }
}

export async function POST(request: Request) {
  if (process.env.SAATHI_HOUSEHOLD_FEATURES_ENABLED !== "true") return Response.json({ detail: "household_features_disabled" }, { status: 503, headers: { "Cache-Control": "no-store" } });
  if (!validOrigin(request)) return Response.json({ detail: "origin_not_allowed" }, { status: 403 });
  if (!(request.headers.get("content-type") || "").toLowerCase().startsWith("application/json")) return Response.json({ detail: "application_json_required" }, { status: 415, headers: { "Cache-Control": "no-store" } });
  const parsed = await readBoundedJson(request);
  if (!parsed.ok) return Response.json({ detail: parsed.detail }, { status: parsed.status, headers: { "Cache-Control": "no-store" } });
  const body = parsed.value;
  if (typeof body.phone !== "string" || !/^\+[1-9]\d{7,14}$/.test(body.phone)) {
    return Response.json({ detail: "valid_e164_phone_required" }, { status: 422 });
  }

  let rateLimited: boolean;
  try {
    rateLimited = await isAuthRateLimited(request, body.phone, "otp");
  } catch {
    return Response.json({ detail: "auth_rate_limit_unavailable" }, { status: 503, headers: { "Cache-Control": "no-store" } });
  }
  if (rateLimited) return Response.json({ detail: "auth_rate_limited" }, { status: 429, headers: { "Cache-Control": "no-store" } });

  const supabase = await createSupabaseServerClient();
  if (!supabase) return Response.json({ detail: "supabase_auth_not_configured" }, { status: 503 });
  const { error } = await supabase.auth.signInWithOtp({ phone: body.phone, options: { shouldCreateUser: true } });
  if (error) {
    const status = error.status === 429 ? 429 : 503;
    return Response.json({ detail: status === 429 ? "otp_rate_limited" : "otp_delivery_unavailable" }, { status });
  }
  return Response.json({ status: "otp_requested" }, { headers: { "Cache-Control": "no-store" } });
}