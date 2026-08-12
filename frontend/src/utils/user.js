// Who is signed in, read off Frappe's cookie — API-free on purpose: a
// failed call here would break pages that only need a preference key.
export function currentUser() {
  const cookie = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith("user_id="))
  return cookie ? decodeURIComponent(cookie.slice("user_id=".length)) : "unknown"
}
