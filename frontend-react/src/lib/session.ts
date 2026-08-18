import { callMethod } from "./frappe";

// Identity comes from the Frappe session, never from a hardcoded value.
// This mirrors the pattern the Vue app has been running (frontend/src/App.vue):
// read the cookies Frappe sets at login for the name, probe a founder-only
// endpoint for the role, bounce guests to Frappe's own login page.

/** Where log-out lands the user afterwards, so re-login returns to this app. */
export const HOME_PATH = "/aura-next/deals";

function readCookie(name: string): string {
  const raw = document.cookie
    .split("; ")
    .find((c) => c.startsWith(`${name}=`))
    ?.slice(name.length + 1);
  if (!raw) return "";
  try {
    return decodeURIComponent(raw).replace(/^"|"$/g, "");
  } catch {
    return "";
  }
}

export function sessionUserId(): string {
  return readCookie("user_id");
}

export function isGuestSession(): boolean {
  const userId = sessionUserId();
  return !userId || userId === "Guest";
}

export function loginUrl(target: string): string {
  return `/login?redirect-to=${encodeURIComponent(target)}`;
}

/**
 * Send a guest to Frappe's login page, returning here once signed in.
 *
 * Deliberately driven by the cookie rather than by an API call: a failed call
 * (a stale CSRF token, say) would bounce a signed-in user to /login, which
 * bounces straight back - an endless reload.
 */
export function requireSession(): boolean {
  if (!isGuestSession()) return true;
  window.location.replace(loginUrl(window.location.pathname));
  return false;
}

export function sessionUserName(): string {
  // full_name is set by Frappe at login; fall back to the account's local part.
  const fullName = readCookie("full_name");
  if (fullName) return fullName;
  const local = sessionUserId().split("@")[0];
  return local || "Signed in";
}

export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  const first = words[0] ?? "";
  const last = words.length > 1 ? (words[words.length - 1] ?? "") : "";
  return ((first.charAt(0) ?? "") + (last.charAt(0) ?? "")).toUpperCase();
}

/**
 * Is this session the founder?
 *
 * Decided by the server, not guessed in the browser: settings are readable only
 * by the founder, so a successful read of the margin floor is the role check.
 * The UI is never the permission boundary - the server refuses the data either
 * way, this only decides what is worth showing.
 */
export async function probeFounder(): Promise<boolean> {
  try {
    await callMethod<number>("auraos.api.get_margin_floor");
    return true;
  } catch {
    return false;
  }
}

/** End the Frappe session, then land on a login page that returns here. */
export async function logout(): Promise<void> {
  try {
    await callMethod("logout");
  } finally {
    window.location.replace(loginUrl(HOME_PATH));
  }
}
