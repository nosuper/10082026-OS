// #125: correcting a Company-paid spend, and the founder's tax exposure moving
// because of it.
//
// **The fall is the ticket.** Before #125 there was no way to attribute a
// payment to a quoted line or to record the invoice that arrived late, so the
// exposure tile could only ever rise. Every test here reads the tile, changes
// one field through the screen, and reads the tile again - and the assertion
// is the *difference*, never a figure typed in here. A spec that hardcoded
// 1.500.000 would be asserting the seed's arithmetic rather than the screen's.
//
// **The control is the last test**, and it is the reason the other three mean
// anything: correcting a field that is neither the number nor the line must
// leave the figure exactly where it was. Without it, a run in which the tile
// merely reloaded to some other number would pass three times over.
//
// **Adds nothing to the fixture.** All four spends are already seeded, one per
// state the editor has to reach - see ensure_exposure_states in
// scripts/e2e-seed.py. Their names live in fixture.js so fixture.spec.js
// guards them.
//
// Two navigations per test, and that is not incidental: the tile is on the
// founder's dashboard and the editor is on the job. Nothing here can be a
// producer spec - a producer is refused the figure outright, which
// exposure.spec.js owns.
//
// **Not asserted here, deliberately.** The ledger repost that follows a
// correction belongs to the seam tests: from a browser it would be three
// layers away, at a table this spec cannot see, and a green would say more
// than it knows. The editor's absence on a closed job is a different claim
// again, and would be its own spec.

import { expect, test } from "@playwright/test";

import { callAs, figureIn, vnd } from "./call.js";
import { EXPOSED_SPEND, INVOICED_LINE, INVOICED_SPEND, UNATTRIBUTED_SPEND } from "./fixture.js";
import { openJob, openJobTab } from "./records.js";
import { saving } from "./writes.js";

const EXPOSURE = "auraos.api.no_invoice_exposure";
const MONEY = "auraos.api.job_money";
const CORRECT = "auraos.api.update_job_expense";

const tileHeading = { name: "No-invoice exposure", exact: true };

async function openDashboard(page) {
  await page.goto("/aura-next/");
  await expect(
    page.getByRole("heading", { name: /Good (morning|afternoon|evening)/ }),
  ).toBeVisible();
}

/**
 * The tile's headline figure and the server's own report, together.
 *
 * Both, because either alone is weak. The server number is what the arithmetic
 * below works on; the tile is the claim the ticket makes, and <Figure> prints a
 * short dash for a query that failed - so a spec reading only the server would
 * pass on a dashboard that had quietly stopped rendering.
 */
async function readExposure(page) {
  await openDashboard(page);
  const answer = await callAs(page, EXPOSURE);
  expect(answer.status, `the exposure endpoint failed: ${JSON.stringify(answer.body)}`).toBe(200);
  const report = answer.body?.message ?? {};
  expect(typeof report.uncovered_total).toBe("number");
  expect(typeof report.tndn_exposure).toBe("number");

  const tile = page.locator("section").filter({ has: page.getByRole("heading", tileHeading) });
  await expect(tile).toHaveCount(1);
  // Polled: the tile renders as soon as the session is known to be a founder,
  // which is before its own query has answered.
  await expect
    .poll(async () => figureIn(await tile.locator(".num").first().textContent()))
    .toBe(vnd(report.tndn_exposure));

  return report;
}

/** What the seed says this spend is worth, read from the screen's own payload
 *  rather than repeated here. */
async function amountOf(page, description) {
  const answer = await callAs(page, MONEY, { job: await openJob(page) });
  expect(answer.status, `job_money failed: ${JSON.stringify(answer.body)}`).toBe(200);
  const rows = answer.body?.message?.expenses ?? [];
  const row = rows.find((entry) => entry.description === description);
  expect(row, `no seeded spend described "${description}"`).toBeTruthy();
  return row.amount;
}

/**
 * Open one spend's editor and change one field through it.
 *
 * Rows are addressed by the button's own label - `Correct <description>` - and
 * never by index: the table's order is the server's business and a row that
 * moved would silently retarget every assertion here.
 *
 * The controls are all `Corrected ...` on purpose. The Money tab also holds the
 * milestone plan, whose field is `Invoice number`, and the log-expense form,
 * whose fields are `Expense amount` and `Expense category` - and the tabs are
 * hidden rather than unmounted, so all of it is in the DOM at once. Asking for
 * `Invoice number` here matches the milestone's field as happily as this one.
 */
async function correct(page, description, edit) {
  const panel = await openJobTab(page, await openJob(page), "Money");
  await panel.getByRole("button", { name: `Correct ${description}`, exact: true }).click();

  const field = (label) => panel.getByLabel(label, { exact: true });
  await expect(field("Corrected amount")).toBeVisible();
  await edit(field);

  await saving(page, CORRECT, () =>
    panel.getByRole("button", { name: "Save", exact: true }).click(),
  );
}

/**
 * A restore that says whether it worked.
 *
 * A spec that leaves the fixture moved is the defect that cost four runs on
 * this project, and `workers: 1` with no tidy between files means the next
 * spec inherits whatever this one left.
 *
 * **Soft, and that is not laziness.** This runs in a `finally`, so a hard
 * assertion that failed here would replace whatever failure sent us into the
 * `finally` - and the restore is the more likely of the two to fail once the
 * body has already gone wrong. Soft records it, still fails the test, and
 * leaves the original error the first thing anyone reads.
 */
async function restore(page, description, edit, expected) {
  await correct(page, description, edit);
  const after = await readExposure(page);
  expect
    .soft(
      after.uncovered_total,
      `the restore did not take - the fixture is left moved for the next spec`,
    )
    .toBe(expected);
}

test("recording the invoice that arrived takes the spend out of the exposure", async ({ page }) => {
  const before = await readExposure(page);
  const amount = await amountOf(page, EXPOSED_SPEND);

  try {
    await correct(page, EXPOSED_SPEND, (field) =>
      field("Corrected invoice number").fill("PW-CORRECTION-0001"),
    );

    const after = await readExposure(page);
    expect(
      before.uncovered_total - after.uncovered_total,
      "the uncovered total did not fall by this spend's own amount",
    ).toBe(amount);

    // The tax is recomputed, not merely redrawn: the rate comes from the
    // payload rather than from a constant here, so a rate change is a rate
    // change and not a failure. One đồng of slack - the server rounds per part
    // with ROUND_HALF_UP.
    const expectedTax = (after.uncovered_total * after.rate_pct) / 100;
    expect(Math.abs(after.tndn_exposure - expectedTax)).toBeLessThanOrEqual(1);
    expect(after.tndn_exposure).toBeLessThan(before.tndn_exposure);
  } finally {
    await restore(
      page,
      EXPOSED_SPEND,
      (field) => field("Corrected invoice number").fill(""),
      before.uncovered_total,
    );
  }
});

test("removing an invoice number puts the spend back into the exposure", async ({ page }) => {
  const before = await readExposure(page);
  const amount = await amountOf(page, INVOICED_SPEND);

  try {
    await correct(page, INVOICED_SPEND, (field) => field("Corrected invoice number").fill(""));

    const after = await readExposure(page);
    expect(
      after.uncovered_total - before.uncovered_total,
      "the figure did not come back when the invoice number was removed",
    ).toBe(amount);
  } finally {
    await restore(
      page,
      INVOICED_SPEND,
      (field) => field("Corrected invoice number").fill("PW-INV-0001"),
      before.uncovered_total,
    );
  }
});

test("attributing a spend to a line that came with paper leaves the exposure", async ({ page }) => {
  const before = await readExposure(page);
  const amount = await amountOf(page, UNATTRIBUTED_SPEND);

  try {
    // By label, not by value: the option's value is the child row's name, which
    // is generated. The label is the line's description, and a line with no
    // paper carries a " · no invoice" suffix - this one does not, which is the
    // whole point of picking it.
    await correct(page, UNATTRIBUTED_SPEND, (field) =>
      field("Corrected quoted line").selectOption({ label: INVOICED_LINE }),
    );

    const after = await readExposure(page);
    expect(
      before.uncovered_total - after.uncovered_total,
      "an unattributed spend attributed to a covered line stayed in the figure",
    ).toBe(amount);
  } finally {
    await restore(
      page,
      UNATTRIBUTED_SPEND,
      (field) => field("Corrected quoted line").selectOption({ label: "Not attributed" }),
      before.uncovered_total,
    );
  }
});

// The control, and the reason the three above are worth their boot. It changes
// a field the exposure does not depend on. If the figure moves here, then it
// moves on any correction, and the three falls above were the tile reloading
// rather than the ticket working.
test("correcting a field the exposure does not depend on leaves the figure alone", async ({
  page,
}) => {
  const before = await readExposure(page);
  const renamed = `${EXPOSED_SPEND} (renamed by e2e)`;

  try {
    await correct(page, EXPOSED_SPEND, (field) => field("Corrected description").fill(renamed));

    const after = await readExposure(page);
    expect(
      after.uncovered_total,
      "the uncovered total moved on a correction that touched neither the amount nor the line",
    ).toBe(before.uncovered_total);
    expect(after.tndn_exposure).toBe(before.tndn_exposure);
  } finally {
    // Addressed by its new description, because that is what the button says
    // now - the same rule as everywhere else here, applied to a row this test
    // renamed itself.
    await restore(
      page,
      renamed,
      (field) => field("Corrected description").fill(EXPOSED_SPEND),
      before.uncovered_total,
    );
  }
});
