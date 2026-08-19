// Finding the seeded records a spec means, by name rather than by luck.
//
// Written because of the defect in the first draft of cash-accounts.spec.js:
// it asked for `Job&limit_page_length=1` and would have been handed the
// *closed* job, because the seed converts that one last and Frappe orders by
// `modified desc`. #123 refuses spending against a closed job, so the test
// would have failed on a lock working exactly as designed - deterministically,
// which is worse than a flake, because a consistent red invites someone to
// weaken the lock.
//
// The rule that came out of it: **a fixture that deliberately holds two records
// with opposite properties turns an unnamed query into a wrong answer every
// time, not a coin flip.** So nothing here returns "one of them".
//
// cash-accounts.spec.js still carries its own copy of this lookup. That is
// deliberate for now, not an oversight: it is the subject of run 16's
// pre-registered repeat-safety claims, and editing it before that run would
// make the result unattributable to the thing it is meant to measure. Fold it
// in afterwards.

import { CLOSED_DEAL, JOB_DEAL } from "./fixture.js";

/**
 * One record's name, or null. Filters are a JSON list, the way Frappe takes them.
 *
 * **Through `page.request`, not `page.evaluate(fetch(...))`, and that is the
 * whole of run 17's eight failures.** The first version fetched a relative URL
 * from inside the page. Every caller here resolves a record *before* deciding
 * where to navigate - `openJobTab(page, await openJob(page), tab)` evaluates
 * the argument first - so the fetch ran on `about:blank`, which has no origin
 * to resolve `/api/...` against. The error is
 * `TypeError: Failed to parse URL`, which says nothing whatsoever about
 * navigation, and all eight tests died before reaching a single assertion.
 *
 * The tempting fix is a `goto` at each call site. **That documents the
 * ordering constraint instead of removing it**, and leaves the next caller to
 * rediscover it through the same unhelpful error.
 *
 * `page.request` has no such constraint: it is bound to the browser context,
 * so it carries the same signed-in cookies, and it resolves relative URLs
 * against the config's `baseURL` **without this file restating what that URL
 * is**. So do not "simplify" this back to `fetch` inside `evaluate` - the
 * relative path only looks equivalent from a page that has already navigated.
 *
 * `cash-accounts.spec.js` keeps its own inline `evaluate` version and is
 * right to: it needs `window.csrf_token` for a POST, which genuinely only
 * exists on a loaded page. It passed all five in run 15 because every test
 * there navigates first. **The same idea written twice in one afternoon, once
 * working and once not, and the only difference was where the page pointed.**
 */
export async function firstName(page, doctype, filters) {
  const response = await page.request.get("/api/method/frappe.client.get_list", {
    params: {
      doctype,
      filters: JSON.stringify(filters),
      limit_page_length: 1,
    },
    headers: { Accept: "application/json" },
  });
  if (!response.ok()) return null;
  const body = await response.json();
  return body?.message?.[0]?.name ?? null;
}

/** The job behind a seeded deal title. */
export async function jobFor(page, dealTitle) {
  const deal = await firstName(page, "Deal", [["title", "=", dealTitle]]);
  if (!deal) throw new Error(`no seeded deal titled ${JSON.stringify(dealTitle)}`);
  const job = await firstName(page, "Job", [["deal", "=", deal]]);
  if (!job) throw new Error(`deal ${deal} has not become a job`);
  return job;
}

/** The open job - the one a spec may still write to. */
export async function openJob(page) {
  return jobFor(page, JOB_DEAL);
}

/** The closed job, for the specs whose subject is the refusal. */
export async function closedJob(page) {
  return jobFor(page, CLOSED_DEAL);
}

/**
 * A job page, on the tab a spec means, scoped to that tab's panel.
 *
 * The three tabs are **shown and hidden, not mounted and unmounted** (see the
 * comment at the top of routes/jobs.$jobId.tsx - it keeps a half-typed
 * milestone plan alive across a trip to Paperwork). So every tab's markup is in
 * the DOM at once, and an unscoped `getByLabel` can match a control on a tab
 * nobody is looking at. Returning the panel rather than the page makes that
 * impossible rather than unlikely.
 */
export async function openJobTab(page, job, tab) {
  await page.goto(`/aura-next/jobs/${job}`);
  await page.getByRole("tab", { name: tab }).click();
  const panel = page.getByRole("tabpanel", { name: tab });
  await panel.waitFor({ state: "visible" });
  return panel;
}
