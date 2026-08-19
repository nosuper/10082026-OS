// The founder's no-invoice tax exposure tile (#11, spec'd by #121).
//
// The assertion this file exists for is the refusal. A producer records that
// the replacement invoice arrived; what the missing invoice costs the company
// in tax is the founder's. The tile being hidden from a producer is noise
// reduction - the server refusing is the guarantee, and a spec that only
// asserted the tile was absent would go green on the day the endpoint started
// answering a producer, which is the exact day it matters.
//
// So the refusal is asked for directly, in the producer's own session, and the
// answer is checked by key set rather than by reading the screen. Both this
// screen and finance/reports carry sentences with the word TNDN in them - one
// prints the rate, the other explains that the tax position is deliberately
// not there yet - so a spec that matched the word would be asserting something
// about English rather than about permission.

import { expect, test } from "@playwright/test";

import { producerState } from "./auth-state.js";
import { callAs, keysDeep, figureIn, vnd } from "./call.js";
import { openJob } from "./records.js";

const producerTest = test.extend({ storageState: producerState });

const EXPOSURE = "auraos.api.no_invoice_exposure";

/**
 * Every key auraos.lib.exposure.exposure_report puts a number in, plus the
 * line list, whose rows carry the amounts. A refusal must contain none of them
 * at any depth; an answer must contain all of them.
 *
 * Names, not prose. `basis` is deliberately not here: it is the sentence
 * saying what was measured, and a screen is allowed to say that a figure is
 * withheld without handing the figure over.
 */
const EXPOSURE_FIGURE_KEYS = [
  "uncovered_total",
  "tndn_exposure",
  "uncovered_count",
  "covered_total",
  "covered_count",
  "rate_pct",
  "lines",
];

/** A booted shell for either session. The greeting is not founder-gated. */
async function openDashboard(page) {
  await page.goto("/aura-next/");
  await expect(
    page.getByRole("heading", { name: /Good (morning|afternoon|evening)/ }),
  ).toBeVisible();
}

const tileHeading = { name: "No-invoice exposure", exact: true };

// The control. Without it the refusal below proves nothing: a stack where
// every call fails - a broken CSRF token, an app that never booted - would
// pass the producer test on its own and report a permission boundary that was
// never exercised. Same request, same transport; the only difference between
// this test and the next one is who is asking.
test("the founder is answered, and the exposure is TNDN on the uncovered total", async ({
  page,
}) => {
  await openDashboard(page);
  const answer = await callAs(page, EXPOSURE);

  expect(
    answer.status,
    `the founder's own request was refused, so nothing below tests permission: ${JSON.stringify(answer.body)}`,
  ).toBe(200);

  const report = answer.body?.message ?? {};
  const keys = keysDeep(report);
  for (const key of EXPOSURE_FIGURE_KEYS) {
    expect(keys.has(key), `the answer is missing ${key}`).toBe(true);
  }

  // Arithmetic, not a figure anyone typed: whatever the site is carrying, the
  // tax on it is the rate the payload names applied to the total it names. It
  // holds on a site with nothing uncovered and on one with forty lines, so it
  // needs no fixture to mean something - which is the only reason it can be
  // written before #130 extends the seed. One đồng of slack because the server
  // rounds per part with ROUND_HALF_UP and Math.round does not.
  expect(typeof report.uncovered_total).toBe("number");
  expect(typeof report.tndn_exposure).toBe("number");
  expect(report.rate_pct).toBe(20);
  const expected = (report.uncovered_total * report.rate_pct) / 100;
  expect(Math.abs(report.tndn_exposure - expected)).toBeLessThanOrEqual(1);
});

// The one that matters, asked as the producer over the transport the control
// just proved works.
producerTest(
  "a producer is refused the exposure, not merely shown a page without it",
  async ({ page }) => {
    await openDashboard(page);
    const answer = await callAs(page, EXPOSURE);

    expect(
      answer.status,
      `the server answered a producer instead of refusing: ${JSON.stringify(answer.body)}`,
    ).toBe(403);
    expect(answer.excType).toBe("PermissionError");

    // And no figure came back in the refusal either. A key set, so the sentence
    // Frappe sends with a PermissionError is free to say the words "tax" and
    // "exposure" - it does - without that being mistaken for the number.
    const leaked = EXPOSURE_FIGURE_KEYS.filter((key) => keysDeep(answer.body).has(key));
    expect(leaked, `the refusal carried ${leaked.join(", ")}`).toEqual([]);
  },
);

producerTest(
  "the tile is not on a producer's dashboard, and its absence is not an error",
  async ({ page }) => {
    const failures = [];
    page.on("pageerror", (error) => failures.push(error.message));

    await openDashboard(page);

    // The card's own h2, matched exactly. This is the courtesy, not the
    // guarantee - the refusal above is the guarantee, and this assertion would
    // still pass on a server that had started handing the figure out.
    await expect(page.getByRole("heading", tileHeading)).toHaveCount(0);
    expect(failures).toEqual([]);
  },
);

test("the tile prints the server's figure, and nothing uncovered reads as zero", async ({
  page,
}) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  await openDashboard(page);
  const answer = await callAs(page, EXPOSURE);
  const report = answer.body?.message ?? {};
  // Guarded, because vnd() prints a short dash for a figure that is not there
  // and <Figure> prints a short dash when its query failed. Without this, a
  // run where the endpoint fell over would compare "-" against "-" and go
  // green on two failures at once.
  expect(answer.status, `the tile's own endpoint failed: ${JSON.stringify(answer.body)}`).toBe(200);
  expect(typeof report.tndn_exposure).toBe("number");

  const tile = page.locator("section").filter({ has: page.getByRole("heading", tileHeading) });
  await expect(tile).toHaveCount(1);

  // The headline figure, compared against the number the server just sent
  // rather than against one worked out here. <Figure> renders a short dash
  // when its query failed and an empty skeleton while it is pending, so this
  // also fails on a tile that quietly could not load - which a check for "some
  // digits somewhere in the card" would not, because the sentence underneath
  // prints a zero of its own whatever happens.
  //
  // Polled because the tile appears as soon as the session is known to be a
  // founder, which is before its own query has come back.
  const figure = tile.locator(".num").first();
  await expect
    .poll(async () => figureIn(await figure.textContent()))
    .toBe(vnd(report.tndn_exposure));

  // textContent, not innerText: innerText is the rendered page and applies
  // text-transform, so a NaN inside a `label-caps` element would come back as
  // NAN and slip past. The DOM is what Playwright queries and what this asks.
  const text = String((await tile.textContent()) ?? "");
  expect(text).not.toMatch(/NaN|undefined|Infinity/);
  expect(failures).toEqual([]);
});

// -- the status is derived, and this is what proves it --
//
// #121 asks for this through the screen: record a cover and the money reads
// covered, take it away and it reads uncovered again. It was blocked twice
// over and both blockers are gone. #123 gave `log_job_expense` a `cost_line`,
// so spending can be attributed through the app at all; #130 seeded a job
// carrying a Không hoá đơn line, so there is something to attribute it to.
//
// It is written as a change rather than as a figure. Nothing here knows what
// the site is carrying - every assertion is a difference against the report
// taken a moment earlier, so the seed can grow underneath it without touching
// this file, and a run against a site with forty other payments on it means
// exactly what a run against an empty one means.
//
// **The unwind uses frappe.client.delete because the app has no way to delete
// an expense**, and no way to put an invoice number on one that already
// exists. That is a finding about the product, not a convenience taken here:
// see the ticket filed against #11. A reader should not infer from this spec
// that a person could undo what it does - they could not.

/** The seeded line whose tax treatment is the one that carries exposure.
 *
 * Found by tax type rather than by name. The name would have to be mirrored
 * from the seed through e2e/fixture.js, and the property this test depends on
 * is not what the line is called - it is that its treatment is Không hoá đơn,
 * which is what auraos.lib.exposure reads. Exactly one is required: a fixture
 * that grew a second would make "the line" an ambiguous phrase, and this fails
 * saying so instead of picking one and asserting against the other.
 */
async function noInvoiceLine(page, job) {
  const answer = await callAs(page, "auraos.api.job_cost_lines", { job });
  expect(answer.status, `the job's cost lines were refused: ${JSON.stringify(answer.body)}`).toBe(
    200,
  );
  const lines = (answer.body?.message ?? []).filter((line) => line.tax_type === "Không hoá đơn");
  expect(
    lines.length,
    `the seeded job carries ${lines.length} Không hoá đơn lines, so "the no-invoice line" names nothing definite`,
  ).toBe(1);
  return lines[0].name;
}

// Two amounts, distinct and distinctive, so a failure message says which
// payment moved the figure. Whole đồng: the server rounds per part, and a
// fraction would make the arithmetic below a near-miss rather than an equality.
const EXPOSED = 2_500_000;
const COVERED = 1_500_000;

test("the exposure follows the money, and an invoice number keeps it out of the figure", async ({
  page,
}) => {
  await openDashboard(page);
  const job = await openJob(page);
  const line = await noInvoiceLine(page, job);

  const opening = await callAs(page, EXPOSURE);
  expect(opening.status, `the exposure was refused: ${JSON.stringify(opening.body)}`).toBe(200);
  const before = opening.body.message;

  const logged = [];
  const log = async (amount, values) => {
    const answer = await callAs(page, "auraos.api.log_job_expense", {
      job,
      amount,
      cost_line: line,
      ...values,
    });
    expect(answer.status, `logging the expense failed: ${JSON.stringify(answer.body)}`).toBe(200);
    logged.push(answer.body.message.name);
    const report = await callAs(page, EXPOSURE);
    expect(report.status, `the exposure was refused: ${JSON.stringify(report.body)}`).toBe(200);
    return report.body.message;
  };

  try {
    // Uncovered: money out against a line whose treatment says no invoice is
    // coming. The count, the total and the tax all move together - the tax
    // recomputed from the payload rather than compared against a number typed
    // here, so this stays true if the rate ever changes.
    const raised = await log(EXPOSED, { description: "Playwright spec exposed spend" });
    expect(raised.uncovered_count).toBe(before.uncovered_count + 1);
    expect(raised.uncovered_total).toBe(before.uncovered_total + EXPOSED);
    // One đồng of slack, for the same reason as the control test above: the
    // server rounds per part with ROUND_HALF_UP and this does not.
    expect(
      Math.abs(raised.tndn_exposure - (raised.uncovered_total * raised.rate_pct) / 100),
    ).toBeLessThanOrEqual(1);
    expect(raised.covered_count).toBe(before.covered_count);

    // And the screen agrees, on a fresh load. Without this the test would prove
    // the endpoint derives the status and say nothing about the tile the
    // founder actually reads - which is what #121 asked about.
    await openDashboard(page);
    const tile = page.locator("section").filter({ has: page.getByRole("heading", tileHeading) });
    await expect
      .poll(async () => figureIn(await tile.locator(".num").first().textContent()))
      .toBe(vnd(raised.tndn_exposure));

    // Covered: the same line, the same kind of spend, with paper on file. The
    // uncovered figure must not move, which is the half of the model that lets
    // the number come down.
    const covered = await log(COVERED, {
      description: "Playwright spec covered spend",
      invoice_no: "PW-SPEC-0001",
    });
    expect(covered.uncovered_total, "an expense carrying an invoice raised the exposure").toBe(
      raised.uncovered_total,
    );
    expect(covered.uncovered_count).toBe(raised.uncovered_count);
    expect(covered.covered_count).toBe(before.covered_count + 1);
    expect(covered.covered_total).toBe(before.covered_total + COVERED);
  } finally {
    // In a finally block because everything above runs against a site the rest
    // of the suite reads afterwards: workers is 1 and fullyParallel is off, so
    // a spec that fails halfway would otherwise hand every later file a
    // different set of books. #135 means the re-seed cannot be relied on to
    // tidy up afterwards either.
    for (const name of logged) {
      const gone = await callAs(page, "frappe.client.delete", {
        doctype: "Job Expense",
        name,
      });
      expect(gone.status, `the spec could not remove ${name}: ${JSON.stringify(gone.body)}`).toBe(
        200,
      );
    }
  }

  // Derived, not stored: with the payments gone the figure is exactly what it
  // was before they existed. An equality, not a fall - a stored status would
  // leave the count right and the total stale, and only this catches that.
  const closing = await callAs(page, EXPOSURE);
  const after = closing.body.message;
  expect(after.uncovered_total).toBe(before.uncovered_total);
  expect(after.uncovered_count).toBe(before.uncovered_count);
  expect(after.covered_total).toBe(before.covered_total);
  expect(after.covered_count).toBe(before.covered_count);
  expect(after.tndn_exposure).toBe(before.tndn_exposure);
});
