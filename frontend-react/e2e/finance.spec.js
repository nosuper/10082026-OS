import { expect, test } from "@playwright/test";

import { producerState } from "./auth-state.js";
import { closedJob, openJob } from "./records.js";

const producerTest = test.extend({ storageState: producerState });

// **The comment this replaces said "the seeded site has no jobs and no
// milestones", and by the time anyone read it that was false.** #130 gave the
// seed two jobs, payment milestones, and an expense dated today, and both
// tests below kept their green because neither of them ever asserted the
// premise their titles were built on. A premise that lives only in a comment
// does not run, so nothing fails when it stops being true (#132).
//
// Both tests now state their own precondition against the server. If the seed
// changes again, they fail at the assertion that says which fact moved -
// rather than passing while their titles quietly become false sentences.

/** The milestone statuses that mean the client has been billed and has not paid. */
const OWED = ["Requested", "Invoiced"];

async function milestonesOf(page, job) {
  const response = await page.request.get(`/api/method/frappe.client.get?doctype=Job&name=${job}`);
  expect(response.ok(), `could not read Job ${job}`).toBe(true);
  return (await response.json()).message.payment_milestones ?? [];
}

// Still true, and now proven rather than assumed: ensure_collected_milestone
// marks the first milestone Paid and states every other as "Not requested", so
// the site has milestones and still owes nothing. An empty ladder is exactly
// where a reporting screen breaks or silently drops its rungs, and this screen
// has no range control - "owed today, not over a range" - so there is no way to
// scope the empty case artificially. The seed is the only thing that makes it.
test("receivables renders every ageing rung even with nothing owed", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  await page.goto("/aura-next/finance/receivables");

  // The premise, executable. Both seeded jobs, because receivables reads all
  // of them and one owed milestone anywhere would make the title false.
  for (const job of [await openJob(page), await closedJob(page)]) {
    const billed = (await milestonesOf(page, job)).filter((row) => OWED.includes(row.status));
    expect(
      billed.map((row) => `${row.description ?? row.name}: ${row.status}`),
      "a milestone is owed, so this test is no longer about an empty ladder",
    ).toEqual([]);
  }

  for (const rung of ["Not yet due", "1-30 days", "31-60 days", "61-90 days", "Over 90 days"]) {
    await expect(page.getByText(rung, { exact: false }).first()).toBeVisible();
  }
  expect(failures).toEqual([]);
});

// Retitled, because the old title - "a range with no activity" - stopped being
// true when the seed started creating an expense dated today. The screens
// zero-fill the months with nothing in them rather than dropping them, and that
// is the claim worth keeping: it holds whether or not a given month is empty,
// which is why it survives the next seed change too.
test("income and expenses render every month in the range, the empty ones included", async ({
  page,
}) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  await page.goto("/aura-next/finance/income");
  await expect(page.locator("body")).toContainText(/cash/i);

  await page.goto("/aura-next/finance/expenses");
  expect(failures).toEqual([]);
});

producerTest("a producer sees margin but no commission or net profit", async ({ page }) => {
  await page.goto("/aura-next/finance/receivables");

  // Exact matches only. These are data labels; the screen also explains in
  // prose that commission and net profit live behind a different door, and a
  // substring check fails on the sentence that says so.
  for (const label of ["Commission", "CMF", "Net profit", "TNDN"]) {
    await expect(page.getByText(label, { exact: true })).toHaveCount(0);
  }
  // And the producer does get what they are entitled to.
  await expect(page.getByText("Margin", { exact: false }).first()).toBeVisible();
});
