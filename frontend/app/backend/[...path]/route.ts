import { proxyRequest } from "../../../lib/backend-proxy.mjs";
import { resolveVerifiedHouseholdContext } from "../../../lib/household-identity";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
type RouteContext = { params: Promise<{ path: string[] }> };

async function handle(request: Request, context: RouteContext) {
  const { path = [] } = await context.params;
  const routePath = path.join("/");
  if (routePath.startsWith("api/v1/household/") && process.env.SAATHI_HOUSEHOLD_FEATURES_ENABLED !== "true") return Response.json({ detail: "household_features_disabled" }, { status: 503, headers: { "Cache-Control": "no-store" } });
  const householdRoutes = new Set(["api/v1/household/consent", "api/v1/household/tasks", "api/v1/household/tasks/status", "api/v1/household/memories", "api/v1/household/memories/delete"]);
  let verifiedContext = null;
  if (householdRoutes.has(routePath)) {
    try {
      verifiedContext = await resolveVerifiedHouseholdContext();
    } catch (cause) {
      const reason = cause instanceof Error ? cause.message : "";
      const requiresUserAction = [
        "verified_phone_identity_required",
        "household_pin_verification_required",
        "household_context_mismatch",
      ].includes(reason);
      return Response.json(
        { detail: requiresUserAction ? reason : "household_identity_unavailable" },
        { status: requiresUserAction ? 401 : 503, headers: { "Cache-Control": "no-store" } },
      );
    }
  } else if (routePath === "api/v1/agent" || routePath === "api/v1/voice/turn") {
    // General conversation and voice should remain usable without an account.
    // Only attach household context when the current user has completed OTP + PIN.
    // Missing identity must never block anonymous, non-persistent assistance.
    try { verifiedContext = await resolveVerifiedHouseholdContext(); } catch { verifiedContext = null; }
  }
  if (routePath === "api/v1/household/consent" && !verifiedContext) {
    return Response.json(
      { detail: "verified_phone_identity_required" },
      { status: 401, headers: { "Cache-Control": "no-store" } },
    );
  }
  return proxyRequest(request, path, { verifiedContext });
}

export const GET = handle;
export const POST = handle;
