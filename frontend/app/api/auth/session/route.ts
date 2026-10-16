import { createSupabaseServerClient } from "../../../../lib/supabase/server";
import { resolveVerifiedHouseholdContext } from "../../../../lib/household-identity";

export async function GET() {
  const supabase = await createSupabaseServerClient();
  if (!supabase) return Response.json({ authenticated: false, authConfigured: false }, { headers: { "Cache-Control": "no-store" } });
  const { data, error } = await supabase.auth.getUser();
  const user = !error ? data.user : null;
  const phone = user?.phone_confirmed_at && user.phone ? user.phone : null;
  let householdContextVerified = false;
  if (phone && process.env.SAATHI_HOUSEHOLD_FEATURES_ENABLED === "true") {
    try { householdContextVerified = Boolean(await resolveVerifiedHouseholdContext()); } catch { householdContextVerified = false; }
  }
  return Response.json({
    authConfigured: true,
    authenticated: Boolean(user),
    phoneVerified: Boolean(phone),
    phoneSuffix: phone ? phone.slice(-4) : null,
    householdContextVerified,
  }, { headers: { "Cache-Control": "no-store" } });
}