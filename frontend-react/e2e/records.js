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

/** One record's name, or null. Filters are a JSON list, the way Frappe takes them. */
export async function firstName(page, doctype, filters) {
  return page.evaluate(
    async ({ doctype, filters }) => {
      const query = new URLSearchParams({
        doctype,
        filters: JSON.stringify(filters),
        limit_page_length: "1",
      });
      const response = await fetch(`/api/method/frappe.client.get_list?${query}`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) return null;
      const body = await response.json();
      return body?.message?.[0]?.name ?? null;
    },
    { doctype, filters },
  );
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
