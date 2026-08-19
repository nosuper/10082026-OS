import { expect, test } from "@playwright/test";

import { BANK, JOB_DEAL, PETTY } from "./fixture.js";

// #115, the spec for the cash accounts screen (#101).
//
// The screen's whole claim is that **no balance is stored or hand editable** -
// every figure is the sum of the entries under it, computed on each read. A
// test that only reads a number cannot tell a derived balance from a stored
// one: both render. So the assertion that matters is the one that *moves* the
// data and looks again.
//
// Written against the fixture in scripts/e2e-seed.py rather than against
// records this file creates. A spec that builds its own fixture is testing its
// own setup; the seed is the fixture, and asserting against a shape you did not
// create is the property that makes it worth anything. The exception is the
// derivation test below, which has to write and then look - proving a number is
// derived means changing the thing it derives from.
//
// The names come from e2e/fixture.js, which is guarded against the seed. The
// first draft of this file spelled them out instead and spelled out the wrong
// ones - the *dev walkthrough* accounts, from a file the E2E stack has never
// run. The header above already claimed this dependency, in prose, correctly.
// Claiming it is not having it.
//
// Selector note, learned before running rather than after: the stat labels and
// several table cells carry `label-caps`, which is `text-transform: uppercase`
// in CSS. The DOM text is title case - "Cash on hand", not "CASH ON HAND". A
// selector copied off the rendered screen fails on every one of them.

const ACCOUNTS = "/aura-next/finance/accounts";

/** Page errors are a failure even when every assertion passes. */
function watchForCrashes(page) {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));
  return failures;
}

test("the screen states that nothing on it is typed in", async ({ page }) => {
  const failures = watchForCrashes(page);

  await page.goto(ACCOUNTS);

  // Not decoration: this sentence is the screen's own claim about itself, and
  // the tests below are what make it true rather than aspirational.
  await expect(page.getByText(/Nothing here is typed in/i)).toBeVisible();
  await expect(page.getByText(/A balance is the sum of the account's entries/i)).toBeVisible();
  expect(failures).toEqual([]);
});

test("an account with no entries reads zero rather than breaking", async ({ page }) => {
  const failures = watchForCrashes(page);

  await page.goto(ACCOUNTS);

  // The regression that would embarrass us with a new studio: a company that
  // has never posted anything opens Finance on its first day. The seed makes
  // BANK the default and every posting flow writes to the default, so PETTY is
  // exactly this case without anyone having to arrange it.
  await expect(page.getByText(PETTY).first()).toBeVisible();
  await page.getByText(PETTY).first().click();

  await expect(page.getByText("No money has moved through this account yet.")).toBeVisible();
  // "Zero, which is a fact about the account rather than a problem with it."
  await expect(page.getByText(/It holds zero/i)).toBeVisible();
  expect(failures).toEqual([]);
});

test("every account is listed with its movement count and a total across them", async ({
  page,
}) => {
  const failures = watchForCrashes(page);

  await page.goto(ACCOUNTS);

  await expect(page.getByText("Cash on hand", { exact: true })).toBeVisible();
  await expect(page.getByText("What each account holds")).toBeVisible();
  await expect(page.getByText("Total held", { exact: true })).toBeVisible();

  // Both seeded accounts, not just the one with money in it. An account is a
  // thing the company holds whether or not anything has moved through it.
  await expect(page.getByText(BANK).first()).toBeVisible();
  await expect(page.getByText(PETTY).first()).toBeVisible();
  expect(failures).toEqual([]);
});

test("an entry is listed with its date, its source and where it came from", async ({ page }) => {
  const failures = watchForCrashes(page);

  await page.goto(ACCOUNTS);
  await page.getByText(BANK).first().click();

  for (const column of ["Date", "Source", "Flow", "Amount"]) {
    await expect(page.getByText(column, { exact: true }).first()).toBeVisible();
  }
  // The seed posts through the real #99/#100 flows, so the flow names are the
  // ledger's own rather than strings this screen invented. These four are the
  // Select options on Cash Ledger Entry.flow.
  await expect(page.getByText(/Job expense|Client payment|Crew advance/).first()).toBeVisible();
  expect(failures).toEqual([]);
});

test("the balance is derived: post an entry and it moves", async ({ page }) => {
  const failures = watchForCrashes(page);

  await page.goto(ACCOUNTS);
  await page.getByText(BANK).first().click();
  const before = await readBalance(page);

  // Through the app's own endpoint rather than by inserting a ledger row.
  // #100 hangs the posting off the expense's save, so this is the same path a
  // producer takes on a phone - and an entry that only appears when the real
  // flow runs is the entry worth asserting on.
  const spend = 1_234_000;
  const posted = await postExpense(page, spend);
  expect(posted, "the expense endpoint should accept a company-paid spend").toBeTruthy();

  await page.reload();
  await page.getByText(BANK).first().click();
  const after = await readBalance(page);

  // Money out, so the balance falls by exactly what was spent. Asserting the
  // difference rather than the figure: a stored balance would not move at all,
  // and a balance that moved by the wrong amount is a different defect from one
  // that did not move.
  expect(before - after).toBe(spend);
  expect(failures).toEqual([]);
});

/** The selected account's balance, as an integer of đồng. */
async function readBalance(page) {
  const text = await page.getByRole("row").filter({ hasText: BANK }).last().innerText();
  return parseVnd(text);
}

/** `1.234.000 ₫` and friends back to a number. The screen groups đồng with dots. */
function parseVnd(text) {
  const match = text.match(/-?[\d.]+(?=\s*₫)/g);
  if (!match) throw new Error(`no đồng figure in ${JSON.stringify(text)}`);
  const last = match[match.length - 1];
  return Number(last.replace(/\./g, ""));
}

/** One record's name, or null. Filters are a JSON list, the way Frappe takes them. */
async function firstName(page, doctype, filters) {
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

/**
 * Log a company-paid expense against the seeded **open** job, through the API
 * the app itself calls. Frappe refuses a POST without the CSRF token the page
 * holds, so it is read out of the live page rather than guessed.
 *
 * Named rather than "whatever job comes back first", and that is not fussiness.
 * The seed converts the closed job last, so it is the most recently modified
 * and an unordered `limit_page_length=1` returns exactly it - and #123 refuses
 * spending against a job at its closing stage. The first draft asked for a job
 * and would have been handed the one the product forbids writing to, failing on
 * a lock working correctly.
 */
async function postExpense(page, amount) {
  const deal = await firstName(page, "Deal", [["title", "=", JOB_DEAL]]);
  if (!deal) return false;
  const job = await firstName(page, "Job", [["deal", "=", deal]]);
  if (!job) return false;

  return page.evaluate(
    async ({ job, amount }) => {
      const response = await fetch("/api/method/auraos.api.log_job_expense", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Frappe-CSRF-Token": window.csrf_token,
        },
        body: JSON.stringify({
          job,
          amount,
          paid_from: "Company",
          description: "e2e derived-balance probe",
        }),
      });
      return response.ok;
    },
    { job, amount },
  );
}
