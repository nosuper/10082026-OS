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
  await expect.poll(async () => figureIn(await figure.textContent())).toBe(vnd(report.tndn_exposure));

  // textContent, not innerText: innerText is the rendered page and applies
  // text-transform, so a NaN inside a `label-caps` element would come back as
  // NAN and slip past. The DOM is what Playwright queries and what this asks.
  const text = String((await tile.textContent()) ?? "");
  expect(text).not.toMatch(/NaN|undefined|Infinity/);
  expect(failures).toEqual([]);
});

// -- blocked on the seed, not on the screen (#130) --
//
// The status is derived and stored nowhere: record a covering expense and the
// line reads covered, delete it and it reads uncovered again. #121 asks for
// this through the screen, and #130 agrees it belongs in the spec rather than
// in the seed, because proving a status is derived means writing and deleting
// the thing it derives from.
//
// It cannot be written yet, and the blocker is bigger than a missing fixture.
// **Nothing in the app writes `covers_cost_line`.** `auraos.api.log_job_expense`
// takes no such argument, and no React screen references the field; its only
// writers in the repo are the doctype's own seam test and a direct get_doc.
// So a cover cannot be recorded through the app at all, by anyone, and this
// case cannot become an end-to-end spec until something can record one. It is
// reported as a finding against #11 rather than guessed at here.
//
// When it can be written it needs, from #130: a Job carrying a cost line typed
// Không hoá đơn, and a way to record and unrecord a covering expense against
// it. The assertion is then uncovered_count before, after and after the
// delete - counts off the payload, with nothing left behind.
