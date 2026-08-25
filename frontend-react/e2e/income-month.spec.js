import { expect, test } from "@playwright/test";

import { BANK, COMPANY } from "./fixture.js";

// #116, the month a collection lands in.
//
// **No spec has asserted a month until now, and rule 32 is why it was left.**
// The seed dates its collection `add_months(today(), -2)`. The obvious spec
// computes the same instant a second time in JS and compares - and two
// independent derivations of one instant is the defect, not the arithmetic.
// Two ways it breaks and neither is fixed by a safer date library: **a run
// crossing midnight on the 1st** between seed time and assertion time, where
// the seed wrote June and the spec derives July and pinning the day does not
// help because it is `today()` that moved; and **timezone**, a Python container
// clock against a JS browser one.
//
// **So this spec derives nothing.** It reads the month off one screen and
// checks the other screen agrees. Rule 32 offered two exits - the seed
// publishes what it wrote, or the spec asserts the label already on screen.
// This is the second, and it needs no change to `scripts/e2e-seed.py`, which
// belongs to another lane and is held.
//
// **And the comparison is not circular, which is the part worth checking
// before trusting it.** Rule 33: a second view fed by the same source is not a
// second witness. These two are not:
//
//   - `/finance/income` reads **Job Payment Milestone.paid_on** directly
//     (`api.finance_income`), bucketed by `finance.month_key`.
//   - `/finance/accounts` reads **Cash Ledger Entry.entry_date**, written by
//     `post_collections` when the Job was saved.
//
// Different tables, written at different moments by different code. **The
// disagreement this catches has already happened once**: backdating `paid_on`
// with `db.set_value`, without letting the posting re-derive, put the same
// money in July on one screen and August on the other. That is the regression
// under test.
//
// Selector notes: the finance range is remembered in `sessionStorage`, which a
// fresh context does not carry, so every test starts at the default "This
// year" window and clicks its own preset. `label-caps` uppercases the column
// headers on screen while the DOM keeps title case.

const ACCOUNTS = "/aura-next/finance/accounts";
const INCOME = "/aura-next/finance/income";

/** `dd/MM/yyyy` as the screen prints it, to the `yyyy-MM` the server buckets by. */
function monthOf(printed) {
  const match = printed.match(/(\d{2})\/(\d{2})\/(\d{4})/);
  if (!match) throw new Error(`no dd/MM/yyyy date in ${JSON.stringify(printed)}`);
  return `${match[3]}-${match[2]}`;
}

/** `1.234.000 ₫` and friends back to a number. The screen groups đồng with dots. */
function parseVnd(text) {
  const match = text.match(/-?[\d.]+(?=\s*₫)/g);
  if (!match) throw new Error(`no đồng figure in ${JSON.stringify(text)}`);
  return Number(match[match.length - 1].replace(/\./g, ""));
}

/** The seeded collection, as the cash ledger recorded it. */
async function collectionFromLedger(page) {
  await page.goto(ACCOUNTS);
  await page.getByText(BANK).first().click();

  const row = page.getByRole("row").filter({ hasText: "Client payment" });
  await expect(row).toHaveCount(1);
  const text = await row.innerText();
  return { month: monthOf(text), amount: parseVnd(text) };
}

test("income is bucketed by calendar month, on the basis it states", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  await page.goto(INCOME);

  // The basis is on the screen's face because it decides what the number
  // means: a milestone counts on the day it was recorded paid, not the day it
  // fell due and not the day the invoice was issued. Asserted on the rendered
  // copy, not on the page description - the sentence about calendar months
  // lives in a <meta> tag and getByText would never have found it.
  await expect(page.getByText("Cash basis.", { exact: true })).toBeVisible();
  await expect(page.getByText(/dated by the day it was received/i)).toBeVisible();
  await expect(page.getByText("Collected by month")).toBeVisible();
  await expect(page.getByText("Every month in the range, including the empty ones")).toBeVisible();
  for (const column of ["Month", "Collected", "Payments", "Total"]) {
    await expect(page.getByText(column, { exact: true }).first()).toBeVisible();
  }
  expect(failures).toEqual([]);
});

test("the month income reports is the month the ledger recorded", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  const collected = await collectionFromLedger(page);

  await page.goto(INCOME);
  // The app's own preset, clicked rather than typed. The default window is
  // "This year", and the seeded collection is two months back - so in January
  // and February it falls in the previous year and the default range excludes
  // it. A spec that passed ten months of the year would be worse than one that
  // never passed. Letting the screen compute "Last 3 months" also keeps the
  // clock arithmetic on the app's side of the line, where this spec has none.
  await page.getByRole("button", { name: "Last 3 months" }).click();

  const row = page.getByRole("row").filter({ hasText: collected.month });
  await expect(row).toHaveCount(1);

  // Same money, not merely some money in the right month: a screen that
  // bucketed every collection into one month would still put a row here.
  expect(parseVnd(await row.innerText())).toBe(collected.amount);

  // The breakdown card names the month back, so the agreement is stated by the
  // screen rather than only by this test - and it names the client the job was
  // sold to.
  await row.click();
  await expect(page.getByText(`Who paid us in ${collected.month}`)).toBeVisible();
  await expect(page.getByText(COMPANY).first()).toBeVisible();
  expect(failures).toEqual([]);
});
