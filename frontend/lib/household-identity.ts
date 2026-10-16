import { createHmac, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";
import { createSupabaseServerClient } from "./supabase/server";

export type VerifiedHouseholdContext = { identityId: string; householdId: string };
type VerifiedPhoneUser = { id: string; phone: string; phone_confirmed_at: string };
type HouseholdMembership = { id: string; household_id: string; pin_hash: string; verified_phone: string };

const E164 = /^\+[1-9]\d{7,14}$/;
const CONTEXT_COOKIE = "saathi_household_context";
const CONTEXT_TTL_SECONDS = 60 * 60;

function getStoreConfig() {
  const supabaseUrl = (process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL || "").replace(/\/$/, "");
  const secret = process.env.SUPABASE_SECRET_KEY;
  if (!supabaseUrl || !secret) throw new Error("household_store_not_configured");
  return { supabaseUrl, secret, headers: { apikey: secret, Authorization: `Bearer ${secret}`, Accept: "application/json", "Content-Type": "application/json" } };
}
function getSigningSecret() {
  const value = process.env.HOUSEHOLD_CONTEXT_SIGNING_SECRET || "";
  if (value.length < 32) throw new Error("household_context_signing_secret_not_configured");
  return value;
}
function getPinPepper() {
  const value = process.env.HOUSEHOLD_PIN_PEPPER || "";
  if (value.length < 32) throw new Error("household_pin_pepper_not_configured");
  return value;
}
export function assertHouseholdIdentitySecretsConfigured() {
  getPinPepper();
  getSigningSecret();
}
export async function getVerifiedPhoneUser(): Promise<VerifiedPhoneUser | null> {
  const auth = await createSupabaseServerClient();
  if (!auth) return null;
  const { data, error } = await auth.auth.getUser();
  if (error || !data.user) return null;
  const user = data.user;
  if (!user.phone || !user.phone_confirmed_at || !E164.test(user.phone)) throw new Error("verified_phone_identity_required");
  return { id: user.id, phone: user.phone, phone_confirmed_at: user.phone_confirmed_at };
}
export async function findHouseholdMembership(userId: string): Promise<HouseholdMembership | null> {
  const { supabaseUrl, headers } = getStoreConfig();
  const url = new URL(`${supabaseUrl}/rest/v1/saathi_household_memberships`);
  url.searchParams.set("auth_user_id", `eq.${userId}`);
  url.searchParams.set("select", "id,household_id,pin_hash,verified_phone");
  url.searchParams.set("limit", "1");
  const response = await fetch(url, { headers, cache: "no-store", signal: AbortSignal.timeout(4000) });
  if (!response.ok) throw new Error("household_membership_store_not_configured");
  const rows = await response.json() as HouseholdMembership[];
  return rows[0] ?? null;
}
export function isStrongHouseholdPin(pin: string): boolean {
  if (!/^\d{8}$/.test(pin)) return false;
  if (/^(\d)\1{7}$/.test(pin)) return false;
  if (/^(\d{2})\1{3}$/.test(pin)) return false;
  const digits = pin.split("").map(Number);
  const ascending = digits.every((digit, index) => index === 0 || digit === digits[index - 1] + 1);
  const descending = digits.every((digit, index) => index === 0 || digit === digits[index - 1] - 1);
  return !ascending && !descending;
}

export function hashHouseholdPin(userId: string, pin: string): string {
  return createHmac("sha256", getPinPepper()).update(`${userId}:${pin}`).digest("hex");
}
export function verifyHouseholdPin(userId: string, pin: string, expectedHex: string): boolean {
  if (!/^[0-9a-f]{64}$/i.test(expectedHex)) return false;
  const expected = Buffer.from(expectedHex, "hex");
  const actual = Buffer.from(hashHouseholdPin(userId, pin), "hex");
  return expected.length === actual.length && timingSafeEqual(expected, actual);
}
export async function createHouseholdMembership(user: VerifiedPhoneUser, pinHash: string): Promise<HouseholdMembership> {
  const { supabaseUrl, headers } = getStoreConfig();
  const response = await fetch(`${supabaseUrl}/rest/v1/rpc/saathi_enroll_household`, {
    method: "POST",
    headers: { ...headers, Prefer: "return=representation" },
    body: JSON.stringify({
      p_auth_user_id: user.id,
      p_verified_phone: user.phone,
      p_pin_hash: pinHash,
    }),
    cache: "no-store",
    signal: AbortSignal.timeout(4000),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null) as { message?: unknown } | null;
    if (errorBody?.message === "household_pin_already_set") {
      throw new Error("household_pin_already_set");
    }
    throw new Error("household_membership_enrollment_failed");
  }
  const rows = await response.json() as HouseholdMembership[];
  const membership = rows[0] ?? await findHouseholdMembership(user.id);
  if (!membership || membership.pin_hash !== pinHash) throw new Error("household_membership_conflict");
  return membership;
}
export async function setHouseholdContextCookie(userId: string, householdId: string) {
  const signingSecret = getSigningSecret();
  const payload = Buffer.from(JSON.stringify({ userId, householdId, exp: Math.floor(Date.now() / 1000) + CONTEXT_TTL_SECONDS })).toString("base64url");
  const signature = createHmac("sha256", signingSecret).update(payload).digest("base64url");
  const cookieStore = await cookies();
  cookieStore.set(CONTEXT_COOKIE, `${payload}.${signature}`, {
    httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/", maxAge: CONTEXT_TTL_SECONDS,
  });
}
export async function clearHouseholdContextCookie() {
  const cookieStore = await cookies();
  cookieStore.set(CONTEXT_COOKIE, "", { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/", maxAge: 0 });
}
async function readHouseholdContextCookie(userId: string): Promise<string | null> {
  const signingSecret = getSigningSecret();
  const cookieStore = await cookies();
  const raw = cookieStore.get(CONTEXT_COOKIE)?.value;
  if (!raw) return null;
  const [payload, signature] = raw.split(".");
  if (!payload || !signature) return null;
  const expected = createHmac("sha256", signingSecret).update(payload).digest();
  const supplied = Buffer.from(signature, "base64url");
  if (supplied.length !== expected.length || !timingSafeEqual(supplied, expected)) return null;
  try {
    const value = JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as { userId?: string; householdId?: string; exp?: number };
    if (value.userId !== userId || typeof value.householdId !== "string" || typeof value.exp !== "number" || value.exp <= Math.floor(Date.now() / 1000)) return null;
    return value.householdId;
  } catch { return null; }
}
export async function resolveVerifiedHouseholdContext(): Promise<VerifiedHouseholdContext | null> {
  const user = await getVerifiedPhoneUser();
  if (!user) return null;
  const cookieHouseholdId = await readHouseholdContextCookie(user.id);
  if (!cookieHouseholdId) throw new Error("household_pin_verification_required");
  const membership = await findHouseholdMembership(user.id);
  if (!membership || membership.household_id !== cookieHouseholdId) throw new Error("household_context_mismatch");
  return { identityId: user.id, householdId: membership.household_id };
}