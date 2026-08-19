// Asking the server a question from inside a signed-in page.
//
// Two specs need this and both need it for the same reason: what a screen
// shows is not what the server would hand over, and the assertions worth
// writing are about the second one. A permission spec that only checks a tile
// is missing goes green on the day the endpoint starts answering.
//
// The request is made with page.evaluate rather than with page.request,
// because page.request carries the session cookie but not the CSRF token the
// Frappe shell injects into the page. Frappe refuses a tokenless POST outright
// - so a spec built on page.request would see a refusal whoever was asking,
// which looks exactly like a passing permission test and would still look like
// one on the day the permission check was deleted.
//
// This is the same transport src/lib/frappe.ts uses: same path, same POST,
// same header, same credentials mode.

/**
 * Call a whitelisted method as whoever the page is signed in as.
 *
 * Returns the HTTP status, Frappe's own exception class name when it sent one,
 * and the parsed body - the refusal as well as the answer, because the refusal
 * is the thing being asserted about half the time.
 *
 * The page must already be loaded: window.csrf_token is on the document Frappe
 * served, not in the bundle.
 */
export async function callAs(page, method, args = {}) {
  return await page.evaluate(
    async ({ method, args }) => {
      const response = await fetch(`/api/method/${method}`, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-Frappe-CSRF-Token": window.csrf_token || "",
        },
        body: JSON.stringify(args),
      });
      const text = await response.text();
      let body = null;
      try {
        body = JSON.parse(text);
      } catch {
        body = null;
      }
      return { status: response.status, excType: String((body && body.exc_type) || ""), body };
    },
    { method, args },
  );
}

/** Every key anywhere in a JSON body, however deeply it is nested. */
export function keysDeep(value, found = new Set()) {
  if (Array.isArray(value)) {
    for (const entry of value) keysDeep(entry, found);
  } else if (value && typeof value === "object") {
    for (const [key, entry] of Object.entries(value)) {
      found.add(key);
      keysDeep(entry, found);
    }
  }
  return found;
}

// Money and percentages the way src/lib/format.ts writes them, so a figure on
// screen can be compared against the number the server sent rather than
// against one typed into a spec. The duplication is deliberate: if a screen
// ever starts working a figure out for itself, this is what stops agreeing
// with it. Both mirror lib/format.ts exactly, including the short dash for a
// figure that is absent rather than zero.
const GROUPED = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 });
const PERCENT = new Intl.NumberFormat("vi-VN", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export function vnd(amount, blank = "-") {
  if (amount === null || amount === undefined || Number.isNaN(amount)) return blank;
  return GROUPED.format(Math.round(amount));
}

/** `+1.000.000` for a figure the screen prints with its sign. */
export function vndSigned(amount) {
  return `${amount > 0 ? "+" : ""}${vnd(amount)}`;
}

export function percent(value, blank = "-") {
  if (value === null || value === undefined || Number.isNaN(value)) return blank;
  return `${PERCENT.format(value)}%`;
}

/** Cell text as a person reads it, with the đồng sign and spacing stripped. */
export function figureIn(text) {
  return String(text ?? "").replace(/[₫\s]/g, "");
}
