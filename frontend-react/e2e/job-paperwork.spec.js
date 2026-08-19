import { expect, test } from "@playwright/test";

import { producerState } from "./auth-state.js";
import { HANDOVER_TEMPLATE, TEMPLATE } from "./fixture.js";
import { openJob, openJobTab } from "./records.js";

// #114, the job's Paperwork tab (#106).
//
// What the tab is for is not "list the files" - it is **has the client actually
// signed it, and who says so.** A registry of documents nobody can answer that
// question about is a folder. So the assertions here are about the status
// control and the stamp beside it, not about the rows existing.
//
// **The fixture assumed, stated because it is about to change.** #134 is open:
// `ensure_paper()` returns early when a paper exists and `ensure_paperwork`
// states a status for only the handover, so the contract's status is never
// restated by the seed. On a fresh site the contract is therefore at its
// doctype default, `Draft`, and every e2e run is a fresh site - `e2e.sh` tears
// down with `--volumes` and seeds once. **These tests are written against that:
// contract Draft, handover Signed.** When #134 lands and states the contract
// explicitly, nothing here should need to change; if it does, this comment is
// where to look.
//
// **Restoring is this spec's own job, for the same reason.** The seed will not
// put back a status these tests move, so each test that moves one moves it
// back. That is not tidiness: with the statuses left where a test dropped them,
// the two-sided fixture is one-sided for every test after it.
//
// Selector notes, all found by reading rather than by a red run:
//   - The three tabs are **hidden, not unmounted**, so every tab's controls are
//     in the DOM at once. Everything below is scoped to the tab's panel by
//     `openJobTab`, never to the page.
//   - The column headers carry `label-caps` (`text-transform: uppercase`), so
//     the DOM holds `Last change` while the screen shows `LAST CHANGE`.
//   - The signing status is a `<select>`. Its value lives in `value`, where
//     `getByText` cannot see it - `toHaveValue` is the assertion.
//   - A paper's file name is a `<button>`, not a link.

const producerTest = test.extend({ storageState: producerState });

/** The row for one template's paper. Files are named `{job} - {template} - {stamp}`. */
function paperRow(panel, template) {
  return panel.getByRole("row").filter({ hasText: template });
}

/** The signing control on that row. */
function statusSelect(panel, template) {
  return paperRow(panel, template).getByLabel("Signing status");
}

test("the tab lists each paper with who moved it and when", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  const panel = await openJobTab(page, await openJob(page), "Paperwork");

  await expect(panel.getByText("Paperwork", { exact: true }).first()).toBeVisible();
  await expect(
    panel.getByText("Filled from this job and printed for wet-ink signature."),
  ).toBeVisible();

  // `Signing` and `Last change` are the two that make this a register rather
  // than a folder, so they are asserted by name rather than by column count.
  for (const column of ["Document on this job", "Added", "By", "Signing", "Last change"]) {
    await expect(panel.getByText(column, { exact: true }).first()).toBeVisible();
  }

  await expect(paperRow(panel, TEMPLATE)).toHaveCount(1);
  await expect(paperRow(panel, HANDOVER_TEMPLATE)).toHaveCount(1);
  expect(failures).toEqual([]);
});

test("the two papers carry different signing statuses", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  const panel = await openJobTab(page, await openJob(page), "Paperwork");

  // The distinction is the whole point of seeding two templates. A tab that had
  // lost the status entirely - rendering every paper the same - would still
  // satisfy a spec that only ever looked at one paper.
  await expect(statusSelect(panel, HANDOVER_TEMPLATE)).toHaveValue("Signed");
  await expect(statusSelect(panel, TEMPLATE)).toHaveValue("Draft");
  expect(failures).toEqual([]);
});

producerTest("moving a status records the person who moved it, by name", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  const panel = await openJobTab(page, await openJob(page), "Paperwork");
  const row = paperRow(panel, TEMPLATE);

  await statusSelect(panel, TEMPLATE).selectOption("Awaiting signature");
  await expect(statusSelect(panel, TEMPLATE)).toHaveValue("Awaiting signature");

  // **Run as the producer deliberately, and this is the reason.** The stamp
  // renders `status_changed_by_label` and falls back to the raw login, so a
  // server that never resolved the name would still render something. As
  // Administrator the two are the same string and the test could not tell them
  // apart; the seeded producer's name is "Playwright Producer" and its login is
  // an email, so asserting the name is present *and the login is absent* is the
  // one assertion that isolates the resolution.
  const login = process.env.E2E_PRODUCER_USER;
  await expect(row).toContainText("Playwright Producer");
  if (login) await expect(row).not.toContainText(login);

  // What a green here covers, said plainly: the select fired, the server wrote
  // the status, the server resolved the name, and the panel refetched. Four
  // links. A red is not by itself a verdict on which - except that the
  // name-vs-login pair above separates the third from the rest.

  await statusSelect(panel, TEMPLATE).selectOption("Draft");
  await expect(statusSelect(panel, TEMPLATE)).toHaveValue("Draft");
  expect(failures).toEqual([]);
});

test("a status set by mistake is not a one-way door", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  const panel = await openJobTab(page, await openJob(page), "Paperwork");
  const select = statusSelect(panel, HANDOVER_TEMPLATE);

  // PaperStatus.tsx states the rule in its own header: "every state is offered
  // from every state, because a paper sometimes has to be redone and a status
  // set by mistake must not be a one-way door." Asserting the options are all
  // present from `Signed` - the far end - is what makes that more than a
  // comment.
  await expect(select.locator("option")).toHaveText(["Draft", "Awaiting signature", "Signed"]);

  // And walking it back is the behaviour itself rather than the offer of it.
  await select.selectOption("Draft");
  await expect(select).toHaveValue("Draft");

  await select.selectOption("Signed");
  await expect(select).toHaveValue("Signed");
  expect(failures).toEqual([]);
});
