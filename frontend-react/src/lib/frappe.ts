// Same-origin talk to Frappe. The app is served by Frappe itself (see
// auraos/www/aura_next.py), so the session cookie rides along automatically and
// there is no token auth, no CORS and no second backend.
//
// The Jinja shell injects window.csrf_token; Frappe rejects authenticated POSTs
// without it.

declare global {
  interface Window {
    csrf_token?: string;
  }
}

export function csrfToken(): string {
  const token = typeof window === "undefined" ? undefined : window.csrf_token;
  // The dev server serves index.html untouched, so the tag is absent there.
  return token && !token.startsWith("{{") ? token : "";
}

export class FrappeError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "FrappeError";
    this.status = status;
  }
}

/** POST a whitelisted method and return its `message` payload. */
export async function callMethod<T>(method: string, args: unknown = {}): Promise<T> {
  const response = await fetch(`/api/method/${method}`, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-Frappe-CSRF-Token": csrfToken(),
    },
    body: JSON.stringify(args),
  });

  if (!response.ok) {
    throw new FrappeError(response.status, `${method} failed with ${response.status}`);
  }

  const payload = (await response.json()) as { message?: T };
  return payload.message as T;
}
