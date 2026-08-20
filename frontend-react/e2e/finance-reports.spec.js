// Profit and loss by month, and margin by job (#108, spec'd by #116).
//
// The defect this screen replaced is the one the first test pins: the mockup
// computed `profit / m.income` in the browser and printed NaN for a month with
// no revenue. The server now answers `margin_pct: null` rather than 0, because
// "there is no margin here" and "the margin is zero" are different claims, and
// the browser prints a short dash for the first. A month with nothing in it is
// the empty case, so it needs no fixture - it is what an untouched site is
// made of.
//
// Every figure here is compared against the payload the server sent, never
// against a number typed into this file. That is what makes the assertions
// survive #130 extending the seed: they say the screen agrees with the server,
// which stays true whatever the seed grows into.

import { expect, test } from "@playwright/test";

import { producerState } from "./auth-state.js";
import { callAs, figureIn, keysDeep, percent, vnd, vndSigned } from "./call.js";

const producerTest = test.extend({ storageState: producerState });

const PNL = "auraos.api.finance_profit_and_loss";
const MARGINS = "auraos.api.job_profitability";
/** Founder-only at the server. A producer's screen must not even ask. */
const TAX_POSITION = "auraos.api.period_tax_position";

/**
 * The range the screen opens on: FinanceRange's third preset, "This year",
 * from the first of January to today. Replicated rather than read back,
 * because useFinanceRange only writes to sessionStorage when somebody changes
 * it - on a first load there is nothing to read.
 *
 * If this ever drifts from the screen's own default, the row count assertion
 * in the first test is what says so, rather than every figure quietly being
 * compared against a different question.
 */
function thisYear() {
  const now = new Date();
  const month = `${now.getMonth() + 1}`.padStart(2, "0");
  const day = `${now.getDate()}`.padStart(2, "0");
  return { from: `${now.getFullYear()}-01-01`, to: `${now.getFullYear()}-${month}-${day}` };
}

async function openReports(page) {
  await page.goto("/aura-next/finance/reports");
  await expect(page.getByRole("heading", { name: "Reports", exact: true })).toBeVisible();
}

/**
 * The founder chain, by the names it travels under. #116 lists these: a
 * producer's payloads must carry none of them.
 *
 * A key set and not a word list, because the screen carries a paragraph
 * explaining that the tax position is deliberately not here yet, and that
 * paragraph says TNDN out loud. A producer spec on receivables once asserted
 * that the word "Commission" never appears and failed a screen for carrying
 * the sentence that says commission is hidden. The screen was right.
 */
const FOUNDER_FIGURE_KEYS = [
  "commission",
  "commission_pct",
  "commission_amount",
  "cm",
  "profit_before_tax",
  "tndn",
  "net_profit",
  "vat_payable",
];

test("a month with no activity reads as a dash in the margin cell, not NaN and not 0%", async ({
  page,
}) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  await openReports(page);

  const range = thisYear();
  const answer = await callAs(page, PNL, { date_from: range.from, date_to: range.to });
  expect(answer.status, `the report was refused: ${JSON.stringify(answer.body)}`).toBe(200);
  const months = answer.body?.message?.months ?? [];

  // Also the check that the screen and this spec asked the same question. If
  // the default range ever moves, this fails here rather than letting every
  // figure below be compared against a different set of months.
  const rows = page.locator("tbody tr");
  await expect(rows).toHaveCount(months.length);

  // The whole point of the spec, and it has to be a month that is genuinely
  // empty. Once #130 seeds a collected milestone there will be a populated
  // month and empty months around it; if a later seed ever fills every month
  // in the range, this says so instead of passing vacuously.
  const empty = months.filter((month) => month.margin_pct === null);
  expect(
    empty.length,
    "no month in this range is empty, so the defect this spec exists for went untested",
  ).toBeGreaterThan(0);

  // Every margin cell against the server's own answer, in order: a dash where
  // margin_pct is null, the formatted percentage where it is a number. Neither
  // value is invented here - `percent` is lib/format's rule, mirrored.
  // allTextContents, not allInnerTexts: innerText is the page as rendered and
  // applies text-transform, which `label-caps` uses to uppercase whole labels
  // in CSS while the DOM keeps their real casing. Nothing in this column is
  // transformed today, but reading the DOM is the habit that does not silently
  // start comparing against a different document.
  const printed = (await rows.locator("td:last-child").allTextContents()).map((t) => t.trim());
  expect(printed).toEqual(months.map((month) => percent(month.margin_pct)));

  // Named explicitly, because NaN is what this screen exists to have stopped
  // printing and a reader of this file should not have to infer it.
  expect(String((await page.locator("table").textContent()) ?? "")).not.toContain("NaN");
  expect(failures).toEqual([]);
});

test("the range foot is the server's total, not a sum of the rows on screen", async ({ page }) => {
  await openReports(page);

  const range = thisYear();
  const answer = await callAs(page, PNL, { date_from: range.from, date_to: range.to });
  // Same guard as the tile spec next door: every formatter here prints a short
  // dash for a figure that is absent, so an endpoint that failed could be
  // compared against a screen that failed and agree.
  expect(answer.status, `the report was refused: ${JSON.stringify(answer.body)}`).toBe(200);
  const report = answer.body?.message ?? {};
  const total = report.total ?? {};
  expect(typeof total.income).toBe("number");

  await expect(page.locator("tbody tr")).toHaveCount((report.months ?? []).length);

  // Income, expense, profit, margin - the four figures in the foot, each
  // against the total the endpoint sent rather than against the rows above it.
  // If a future change starts adding the table up in the browser, this is the
  // assertion that should fail.
  //
  // While the seed has no money in it this compares zero against zero, which
  // is a weak version of the claim rather than a false one. It gets its teeth
  // the moment #130 seeds a collected milestone; nothing here needs changing
  // when it does, which is why it is written against the payload and not
  // against a figure.
  const cells = (await page.locator("tfoot tr td").allTextContents()).map(figureIn);
  expect(cells[2]).toBe(vnd(total.income));
  expect(cells[3]).toBe(vnd(total.expense));
  expect(cells[4]).toBe(vndSigned(total.profit));
  expect(cells[5]).toBe(percent(total.margin_pct));
});

producerTest("a producer gets the same report, carrying no founder figure", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  // Registered before the navigation, because the point is what the screen
  // asks for and a listener attached afterwards would miss the first load.
  const asked = [];
  page.on("request", (request) => {
    if (request.url().includes(TAX_POSITION)) asked.push(request.url());
  });

  await openReports(page);

  const range = thisYear();
  const pnl = await callAs(page, PNL, { date_from: range.from, date_to: range.to });
  const margins = await callAs(page, MARGINS, { include_closed: 1 });

  // The founder's decision on 2026-08-19 was to keep the existing scoping
  // rather than gate this screen: a producer sees the report, over the jobs
  // _permitted_jobs() lets them list. So a refusal here is a regression, not a
  // safeguard - the opposite of the exposure tile next door.
  expect(pnl.status, `the profit and loss refused a producer: ${JSON.stringify(pnl.body)}`).toBe(
    200,
  );
  expect(
    margins.status,
    `job profitability refused a producer: ${JSON.stringify(margins.body)}`,
  ).toBe(200);
  expect(Array.isArray(pnl.body?.message?.months)).toBe(true);

  const leaked = FOUNDER_FIGURE_KEYS.filter(
    (key) => keysDeep(pnl.body).has(key) || keysDeep(margins.body).has(key),
  );
  expect(leaked, `a producer's payload carried ${leaked.join(", ")}`).toEqual([]);

  // **Nothing tax-shaped anywhere on the page**, which is a different claim
  // from the key set above and a stricter one: the payload check would pass a
  // screen that rendered the founder's VAT figure from some other source, and
  // this would not.
  //
  // This replaces an assertion that the screen *said* "tax position is not on
  // this screen". #109 removed that sentence, and restoring it was never on
  // the table for two reasons worth keeping written down:
  //
  //   - **It had become false.** The sentence claimed nothing in AuraOS works
  //     out a tax figure; #109 works one out.
  //   - **Write boundaries are announced, read boundaries are silent.** This
  //     app tells a producer about actions they lack - "only the founder can
  //     change templates" - and never signposts content they cannot see.
  //     Commission, profit and exposure are all silently absent, and a
  //     sentence explaining the absence of the tax card would have been the
  //     one exception.
  //
  // Word boundaries rather than substrings, which is the trap the exposure
  // spec next door met from the other side: `/vat/i` matches "private" and
  // "innovative", and a leak detector that cries at ordinary prose gets
  // loosened by the next person rather than believed.
  const said = String((await page.getByRole("main").textContent()) ?? "");
  const taxWords = said.match(/\b(tax|thu[eế]|vat|tndn)\b/gi) ?? [];
  expect(taxWords, `the reports screen said ${taxWords.join(", ")} to a producer`).toEqual([]);

  // And it did not ask, either. A screen that fetched the founder's tax
  // position and merely declined to draw it would satisfy every assertion
  // above while putting the figure in the browser - which is where a devtools
  // tab would find it.
  //
  // **One claim, two surfaces - do not split this into its own test.** "A
  // producer's screen contains nothing tax-shaped" has a DOM face and a
  // network face, and they come apart in exactly one scenario: fetched but
  // not rendered. Separated, the network half reads as redundant with the
  // DOM half and gets dropped by whoever is tidying, which is the day the
  // scenario stops being covered. The server refusing is the real guarantee;
  // this is the detector for a gate loosened client-side.
  expect(asked, "the screen asked the server for the founder's tax position").toEqual([]);
  expect(failures).toEqual([]);
});

// #130 landed the two jobs this needs. It was written before them, deliberately
// against the shape rather than against the fixture, and the only edit it took
// to un-block was removing the fixme - which is the property that was worth
// having: nothing in it reads a figure. It asserts the partition the screen
// draws, against the stages the endpoint reports, and counts more than zero
// rather than an exact number, so it says something about the screen and
// nothing about how many jobs the seed happens to make.
test("margin by job separates the closed from the still-spending", async ({ page }) => {
  await openReports(page);

  // include_closed: 1 because that is what the screen asks for (see the header
  // of routes/finance.reports.tsx) - the two groups below only both exist in an
  // answer that was allowed to carry finished work.
  const answer = await callAs(page, MARGINS, { include_closed: 1 });
  expect(answer.status, `job profitability was refused: ${JSON.stringify(answer.body)}`).toBe(200);
  const jobs = answer.body?.message ?? [];
  const closed = jobs.filter((job) => job.stage === "Complete");
  const open = jobs.filter((job) => job.stage !== "Complete");

  const noDistinction = "the seed has no such job, so there is no distinction to draw";
  expect(closed.length, noDistinction).toBeGreaterThan(0);
  expect(open.length, noDistinction).toBeGreaterThan(0);

  // The captions say which group is which. Matched on the phrase that carries
  // the claim rather than on the whole caption, so a reword is not a failure -
  // and case-insensitively, because these are `label-caps`: the screen shows
  // CLOSED JOBS while the DOM holds "Closed jobs", the transform being CSS.
  await expect(page.getByText(/margin is final/i).first()).toBeVisible();
  await expect(page.getByText(/margin is provisional/i).first()).toBeVisible();
});
