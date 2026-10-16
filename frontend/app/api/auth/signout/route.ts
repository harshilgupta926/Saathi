import { createSupabaseServerClient } from "../../../../lib/supabase/server";
import { clearHouseholdContextCookie } from "../../../../lib/household-identity";

export async function POST(request: Request) {
  const origin = request.headers.get("origin");
  if (origin) {
    try { if (new URL(origin).origin !== new URL(request.url).origin) return Response.json({ detail: "origin_not_allowed" }, { status: 403 }); }
    catch { return Response.json({ detail: "origin_not_allowed" }, { status: 403 }); }
  }
  const supabase = await createSupabaseServerClient();
  if (!supabase) return Response.json({ detail: "supabase_auth_not_configured" }, { status: 503 });
  const { error } = await supabase.auth.signOut();
  if (error) return Response.json({ detail: "signout_failed" }, { status: 503 });
  await clearHouseholdContextCookie();
  return Response.json({ status: "signed_out" }, { headers: { "Cache-Control": "no-store" } });
}