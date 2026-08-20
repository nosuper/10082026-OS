import { expect, test } from "@playwright/test";

import { saving } from "./writes.js";

const seededDeal = "Playwright Existing Deal";

// The header's stage control writes through frappe.client.set_value - see
// DealStage.tsx, which uses it rather than db.set_value so before_save runs
// and the history row gets written.
const SET_VALUE = "frappe.client.set_value";
const seededCompany = "Playwright Client";

// Regression test for the bug the founder reported: clicking any deal landed
// on the fixture TVC Tet 2027 "Vi Xuan" for Nhat Minh Beverage, whichever deal
// was clicked, because the route made no server calls and rendered hardcoded
// content. This is the spec that must fail if that ever comes back.
test("the deal you open is the deal you get", async ({ page }) => {
  await page.goto("/aura-next/deals");
  await page.getByRole("link", { name: seededDeal }).first().click();

  await expect(page).toHaveURL(/\/aura-next\/deals\/DEAL-/);
  await expect(page.getByText(seededDeal).first()).toBeVisible();
  await expect(page.getByText(seededCompany).first()).toBeVisible();
});

test("no deal page shows the fixture that used to be hardcoded here", async ({ page }) => {
  await page.goto("/aura-next/deals");
  await page.getByRole("link", { name: seededDeal }).first().click();
  await expect(page).toHaveURL(/\/aura-next\/deals\/DEAL-/);

  const body = await page.locator("body").innerText();
  expect(body).not.toContain("Vị Xuân");
  expect(body).not.toContain("Nhất Minh");
});

test("a deal code that does not exist is a calm state, not a crash", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  await page.goto("/aura-next/deals/DEAL-does-not-exist");
  await expect(page.locator("body")).toContainText(/no such deal|nothing on this site is filed/i);
  expect(failures).toEqual([]);
});

// #117: the stage moves from the header. The assertion that matters is not
// that the pill changed - it is that the move was *recorded*. A stage set
// straight onto the field would look identical on screen and leave the deal's
// history with a hole in it, and the payment milestone triggers read stage.
test("changing the stage in the header records the move in stage history", async ({ page }) => {
  await page.goto("/aura-next/deals");
  await page.getByRole("link", { name: seededDeal }).first().click();
  await expect(page).toHaveURL(/\/aura-next\/deals\/DEAL-/);

  const stage = page.getByLabel("Stage");
  await expect(stage).toHaveValue("Brief Received");

  // Awaited, not polled for. StageSelect is controlled by the document the
  // screen holds, so this assertion cannot pass until the write comes back -
  // and on a busy box it does not come back inside the assertion's timeout.
  // Run 20 caught it at load 5-7 with the select still disabled after nine
  // polls, which is stageChange.pending still true: the assertion was right
  // about what it wanted and early about when it asked.
  await saving(page, SET_VALUE, () => stage.selectOption("De-brief"));
  await expect(stage).toHaveValue("De-brief");

  // Read it back from the server rather than from the control that just
  // changed: the point is that Deal.before_save ran, not that a select holds
  // what was typed into it.
  await page.reload();
  await expect(page.getByLabel("Stage")).toHaveValue("De-brief");

  // The log itself, read from the server rather than located by walking up the
  // DOM from a card title. What has to be true is that a stage_history row
  // exists; proving that through a layout the screen is free to change would be
  // testing the layout.
  const code = new URL(page.url()).pathname.split("/").pop();
  const response = await page.request.get(
    `/api/method/frappe.client.get?doctype=Deal&name=${code}`,
  );
  expect(response.ok()).toBe(true);
  const moves = (await response.json()).message.stage_history ?? [];
  expect(
    moves.map((row) => `${row.from_stage} to ${row.to_stage}`),
    "no stage_history row for the move the header just made",
  ).toContain("Brief Received to De-brief");

  // Put it back. The seed restores this too, but a spec that leaves the shared
  // deal moved is the defect that cost three e2e runs this morning, and the
  // next spec should not have to know this one ran.
  // The restore is the worst place in a spec for an unawaited write: there is
  // nothing after it to force the wait, so the test ends and the request dies
  // with the context. The next spec then reads a deal this one moved.
  await saving(page, SET_VALUE, () => page.getByLabel("Stage").selectOption("Brief Received"));
  await expect(page.getByLabel("Stage")).toHaveValue("Brief Received");
});

// Lost is refused by the server without a reason, so the control has to ask
// before it writes. This fails if the header ever writes Lost directly - which
// would surface as a validation error the user cannot act on.
test("moving to Lost asks for a reason before it writes", async ({ page }) => {
  await page.goto("/aura-next/deals");
  await page.getByRole("link", { name: seededDeal }).first().click();
  await expect(page).toHaveURL(/\/aura-next\/deals\/DEAL-/);

  // Deliberately not wrapped in saving(): choosing Lost opens the dialog and
  // writes nothing, which is the claim. A saving() here would hang until it
  // timed out - failure cause 3 in writes.js, an action that never triggered
  // the write - and would read as a slow box rather than as this test passing.
  await page.getByLabel("Stage").selectOption("Lost");

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("A reason is required");

  // Cancelling leaves the deal where it was - the dialog is the write, not a
  // confirmation of one that already happened.
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await page.reload();
  await expect(page.getByLabel("Stage")).not.toHaveValue("Lost");
});
