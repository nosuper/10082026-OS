// The founder's overhead log and break-even line (#14).
//
// The assertion this file exists for is the refusal. #14's third criterion is
// that the whole module is invisible to a producer through UI, API and search -
// and "invisible" is worth almost nothing as a statement about a screen. A spec
// that only checked the tab was missing would go green on the day the endpoints
// started answering a producer, which is the exact day it matters.
//
// So every door is knocked on in the producer's own session and the answers are
// checked by key set rather than by reading the page. The screen assertions
// below are the courtesy; the refusals are the guarantee.
//
// The other half is the arithmetic on the screen. Break-even is a subtraction,
// and a subtraction rendered by a browser that fetched two numbers separately
// is exactly the kind of figure that goes quietly wrong. Every figure here is
// compared against what the server just sent rather than against a constant, so
// a run against a site with forty jobs on it means what a run against an empty
// one means.

import { expect, test } from "@playwright/test";

import { producerState } from "./auth-state.js";
import { callAs, keysDeep } from "./call.js";

const producerTest = test.extend({ storageState: producerState });

const BREAK_EVEN = "auraos.api.break_even";
const RANGE = { date_from: "2020-01-01", date_to: "2099-12-31" };

/**
 * Every door into the module, with the arguments each needs to get past
 * argument validation and reach its permission check.
 *
 * All of them, not a sample. A boundary with a hole in it reads as a guarantee,
 * and the hole is always the endpoint somebody added after the spec was
 * written - so this list is meant to be added to alongside the API section it
 * mirrors, and a reader comparing the two should find them the same length.
 */
const DOORS = [
  [BREAK_EVEN, RANGE],
  ["auraos.api.overhead_log", RANGE],
  ["auraos.api.recurring_overheads", {}],
  ["auraos.api.overheads_due", {}],
  ["auraos.api.company_expense_categories", {}],
  ["auraos.api.save_recurring_overhead", { values: { label: "x", amount: 1 } }],
  ["auraos.api.delete_recurring_overhead", { name: "RO-00001" }],
  ["auraos.api.record_recurring_overheads", { rows: [] }],
  ["auraos.api.log_company_expense", { amount: 1 }],
  ["auraos.api.update_company_expense", { name: "CE-2026-00001", amount: 1 }],
  ["auraos.api.delete_company_expense", { name: "CE-2026-00001" }],
];

/**
 * Every key the break-even payload puts a number in.
 *
 * Names, not prose. `contribution_basis` and `overhead_basis` are deliberately
 * absent: they are the sentences saying what was measured, and a refusal is
 * allowed to use the words without handing over the figures.
 */
const FIGURE_KEYS = [
  "overhead",
  "contribution",
  "surplus",
  "final_contribution",
  "provisional_contribution",
  "coverage_pct",
  "monthly_committed",
];

/** The two doctypes the module is made of, for the search half of the claim. */
const FOUNDER_DOCTYPES = ["Company Expense", "Recurring Overhead"];

async function openOverhead(page) {
  await page.goto("/aura-next/finance/overhead");
  await expect(page.getByRole("heading", { name: "Overhead", exact: true })).toBeVisible();
}

async function openFinance(page) {
  await page.goto("/aura-next/finance");
  await expect(page.getByRole("link", { name: "Reports", exact: true })).toBeVisible();
}

// The control. Without it the refusals below prove nothing: a stack where every
// call fails - a broken CSRF token, an app that never booted - would pass the
// producer tests on its own and report a permission boundary that was never
// exercised. Same requests, same transport; the only difference is who asks.
test("the founder is answered, and the surplus is the contribution less the overhead", async ({
  page,
}) => {
  await openOverhead(page);
  const answer = await callAs(page, BREAK_EVEN, RANGE);

  expect(
    answer.status,
    `the founder's own request was refused, so nothing below tests permission: ${JSON.stringify(answer.body)}`,
  ).toBe(200);

  const report = answer.body?.message ?? {};
  const keys = keysDeep(report);
  for (const key of FIGURE_KEYS) {
    expect(keys.has(key), `the answer is missing ${key}`).toBe(true);
  }

  // Arithmetic, not a figure anyone typed. It holds on a site with nothing
  // booked and on one with forty jobs, so it needs no fixture to mean
  // something.
  const total = report.total;
  expect(total.surplus).toBe(total.contribution - total.overhead);
  expect(total.final_surplus).toBe(total.final_contribution - total.overhead);
  expect(total.contribution).toBe(total.final_contribution + total.provisional_contribution);

  // The months add to the range, on both sides. Two additions of one set of
  // rows is how a footer comes to disagree with the column above it.
  const sum = (key) => report.months.reduce((running, month) => running + month[key], 0);
  expect(sum("overhead")).toBe(total.overhead);
  expect(sum("contribution")).toBe(total.contribution);

  // Show, don't suggest - asserted over the whole payload, at any depth. A key
  // called recommended_floor would be read as a recommendation the moment it
  // existed, and #14 says the floor stays the founder's judgement.
  const advice = [...keys].filter((key) =>
    ["floor", "recommend", "suggest", "target", "advice"].some((word) => key.includes(word)),
  );
  expect(advice, `the payload carries ${advice.join(", ")}`).toEqual([]);
});

// The one that matters, asked as the producer over the transport the control
// just proved works.
producerTest("a producer is refused at every door into the module", async ({ page }) => {
  await openFinance(page);

  for (const [method, args] of DOORS) {
    const answer = await callAs(page, method, args);
    expect(
      answer.status,
      `the server answered a producer at ${method} instead of refusing: ${JSON.stringify(answer.body)}`,
    ).toBe(403);
    expect(answer.excType, `${method} refused with the wrong class`).toBe("PermissionError");

    // And no figure came back in the refusal either. A key set, so the sentence
    // Frappe sends with a PermissionError is free to use the words "overhead"
    // and "break-even" - it does - without that being mistaken for the number.
    const leaked = FIGURE_KEYS.filter((key) => keysDeep(answer.body).has(key));
    expect(leaked, `${method}'s refusal carried ${leaked.join(", ")}`).toEqual([]);
  }
});

producerTest("a producer cannot reach the records around the endpoints", async ({ page }) => {
  await openFinance(page);

  // The API and search half of #14's criterion, at the layer that decides it:
  // there is no Producer row on either doctype, so the generic REST reads a
  // producer *can* make - the ones behind the awesome bar and every list view -
  // are refused by the framework rather than by an endpoint of ours. An
  // endpoint check that did not extend here would leave the whole module one
  // frappe.client.get_list away from being public.
  for (const doctype of FOUNDER_DOCTYPES) {
    const listed = await callAs(page, "frappe.client.get_list", {
      doctype,
      fields: ["name"],
      limit_page_length: 1,
    });
    expect(listed.status, `a producer listed ${doctype}: ${JSON.stringify(listed.body)}`).toBe(403);

    const counted = await callAs(page, "frappe.client.get_count", { doctype });
    expect(counted.status, `a producer counted ${doctype}: ${JSON.stringify(counted.body)}`).toBe(
      403,
    );
  }
});

producerTest(
  "the tab is not in a producer's finance nav, and its absence is not an error",
  async ({ page }) => {
    const failures = [];
    page.on("pageerror", (error) => failures.push(error.message));

    await openFinance(page);

    // The courtesy, not the guarantee - the refusals above are the guarantee, and
    // this assertion would still pass on a server that had started handing the
    // figures out. Its own value is that a producer is never shown a link to a
    // page that will refuse them.
    await expect(page.getByRole("link", { name: "Overhead", exact: true })).toHaveCount(0);
    expect(failures).toEqual([]);
  },
);

test("the screen prints the server's figures and never its own", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  await openOverhead(page);

  // The four headline tiles and the two cards that carry the line. Named, so a
  // screen that rendered its shell and lost its body fails here rather than
  // passing on an empty page.
  for (const label of ["Overhead in range", "Contribution", "Upkeep covered"]) {
    await expect(page.getByText(label, { exact: true })).toBeVisible();
  }
  await expect(page.getByRole("heading", { name: "Break-even by month" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Overhead log" })).toBeVisible();

  // The endpoint behind them answers, so a page that quietly could not load is
  // told apart from one whose figures are genuinely zero.
  const answer = await callAs(page, BREAK_EVEN, RANGE);
  expect(answer.status, `the screen's own endpoint failed: ${JSON.stringify(answer.body)}`).toBe(
    200,
  );

  // Nothing on the page reads NaN, undefined or Infinity. textContent, not
  // innerText: innerText applies text-transform, so a NaN inside a label-caps
  // element would come back as NAN and slip past.
  const text = String((await page.locator("main").textContent()) ?? "");
  expect(text).not.toMatch(/NaN|undefined|Infinity/);
  expect(failures).toEqual([]);
});

// -- a standing cost becomes a payment once, and only when confirmed --
//
// Written as a change rather than as a figure. Nothing here knows what the site
// is carrying: every assertion is a difference against the report taken a
// moment earlier, so the seed can grow underneath it without touching this
// file.
//
// The unwind is in a finally block because workers is 1 and fullyParallel is
// off: a spec that failed halfway would otherwise hand every later file a
// different set of books.

const RENT = 30_000_000;
const MONTH = "2021-03";

test("a standing cost is due until it is confirmed, and confirming it twice pays once", async ({
  page,
}) => {
  await openOverhead(page);

  const created = await callAs(page, "auraos.api.save_recurring_overhead", {
    values: {
      label: "Playwright standing cost",
      amount: RENT,
      day_of_month: 5,
      // Long past, so every month of the window has started and the backlog is
      // the same whatever day this runs.
      starts_on: "2021-01-01",
      ends_on: "2021-12-31",
    },
  });
  expect(created.status, `the standing cost was refused: ${JSON.stringify(created.body)}`).toBe(
    200,
  );
  const template = created.body.message.name;

  const written = [];
  const dueMonths = async () => {
    const answer = await callAs(page, "auraos.api.overheads_due", {
      date_from: "2021-01-01",
      date_to: "2021-12-31",
    });
    expect(answer.status, `the backlog was refused: ${JSON.stringify(answer.body)}`).toBe(200);
    return answer.body.message.rows
      .filter((row) => row.template === template)
      .map((row) => row.month);
  };

  try {
    // Twelve months running, none of them recorded: the whole year is due, and
    // nothing has been posted by merely existing.
    expect(await dueMonths()).toHaveLength(12);

    const first = await callAs(page, "auraos.api.record_recurring_overheads", {
      rows: [{ template, month: MONTH }],
    });
    expect(first.status, `recording was refused: ${JSON.stringify(first.body)}`).toBe(200);
    expect(first.body.message.written).toHaveLength(1);
    written.push(first.body.message.written[0].name);

    // The day inside the month it covers, and the amount off the record.
    expect(first.body.message.written[0].amount).toBe(RENT);
    expect(String(first.body.message.written[0].spent_on)).toContain("2021-03-05");

    const afterOne = await dueMonths();
    expect(afterOne).toHaveLength(11);
    expect(afterOne).not.toContain(MONTH);

    // Two clicks on a slow connection must not become two rents. Skipped rather
    // than refused, so one already-written line cannot stop the other eleven.
    const again = await callAs(page, "auraos.api.record_recurring_overheads", {
      rows: [{ template, month: MONTH }],
    });
    expect(again.status).toBe(200);
    expect(again.body.message.written).toHaveLength(0);
    expect(again.body.message.skipped).toHaveLength(1);
    expect(await dueMonths()).toHaveLength(11);
  } finally {
    for (const name of written) {
      const gone = await callAs(page, "auraos.api.delete_company_expense", { name });
      expect(gone.status, `the spec could not remove ${name}: ${JSON.stringify(gone.body)}`).toBe(
        200,
      );
    }
    const gone = await callAs(page, "auraos.api.delete_recurring_overhead", { name: template });
    expect(gone.status, `the spec could not remove ${template}`).toBe(200);
  }

  // Deleting the payment made the month due again, because recorded is a fact
  // about the payments rather than a stamp on the template - and with the
  // template gone the backlog is exactly what it was before any of this.
  const closing = await callAs(page, "auraos.api.overheads_due", {
    date_from: "2021-01-01",
    date_to: "2021-12-31",
  });
  expect(closing.body.message.rows.filter((row) => row.template === template)).toHaveLength(0);
});

// A one-off overhead moves the line, and the line is the server's subtraction.
test("a one-off overhead raises the overhead side and lowers the surplus by the same amount", async ({
  page,
}) => {
  await openOverhead(page);

  const opening = await callAs(page, BREAK_EVEN, RANGE);
  expect(opening.status, `the line was refused: ${JSON.stringify(opening.body)}`).toBe(200);
  const before = opening.body.message.total;

  const spend = 4_400_000;
  const logged = await callAs(page, "auraos.api.log_company_expense", {
    amount: spend,
    description: "Playwright spec printer",
    spent_on: "2021-03-09",
  });
  expect(logged.status, `the overhead was refused: ${JSON.stringify(logged.body)}`).toBe(200);
  const expense = logged.body.message.name;

  try {
    const raised = (await callAs(page, BREAK_EVEN, RANGE)).body.message.total;
    expect(raised.overhead).toBe(before.overhead + spend);
    // The contribution side is untouched: an overhead is not a job cost, and
    // the whole point of the two sides is that they move independently.
    expect(raised.contribution).toBe(before.contribution);
    expect(raised.surplus).toBe(before.surplus - spend);
    expect(raised.surplus).toBe(raised.contribution - raised.overhead);
  } finally {
    const gone = await callAs(page, "auraos.api.delete_company_expense", { name: expense });
    expect(gone.status, `the spec could not remove ${expense}`).toBe(200);
  }

  // Derived, not stored: with the payment gone the line is exactly what it was.
  const closing = (await callAs(page, BREAK_EVEN, RANGE)).body.message.total;
  expect(closing.overhead).toBe(before.overhead);
  expect(closing.surplus).toBe(before.surplus);
});
