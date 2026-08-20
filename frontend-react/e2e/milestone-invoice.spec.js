import { expect, test } from "@playwright/test";

import { COMPANY } from "./fixture.js";
import { openJob, openJobTab } from "./records.js";
import { saving } from "./writes.js";

// #126, the invoice on a payment milestone.
//
// The behaviour worth pinning is not that a number can be typed. It is that
// **the number and the issue date are one record, and neither is stored
// independently of the status.** `stamps_for()` clears every step ahead of the
// status on each save, and the invoice number dies with `invoiced_on` - its own
// words, "walking back before đã xuất HĐ clears all three together". A test
// that types a number and reads it back cannot tell that from a field that
// simply holds what it was given. **The assertion that matters is the one that
// walks the status back and looks again** - the same shape as the derived
// balance in cash-accounts.spec.js, for the same reason.
//
// Fixture: the seed marks milestone 1 Paid with an invoice number and leaves
// the rest at Not requested. These tests work on **milestone 2**, which is
// therefore untouched by the seed's own statements and is put back where it
// started by the last test that moves it.
//
// Selector notes:
//   - The tabs are **hidden, not unmounted**; everything is scoped to the Money
//     panel by `openJobTab`.
//   - **A milestone's title lives in an `<input>`'s `value`**, so a row cannot
//     be found by its text. Rows are addressed by the index of their controls,
//     which is safe here because the panel renders exactly the stored rows -
//     there is no blank row until someone presses Add milestone.
//   - The status is a `<select>` and the number an `<input>`: `toHaveValue`,
//     never `getByText`.
//
// **These four run in order and depend on it.** Test 3 needs the number test 2
// wrote, and asserts that as a precondition rather than assuming it, so running
// it alone fails saying so instead of passing vacuously. Deliberate: making
// test 3 set up its own invoice would duplicate test 2's write, and then a
// failure in that shared step would be a red in two tests with no way to tell
// which behaviour broke.

/** Milestone 2's controls. Index 1, because the seed states milestone 1. */
const SECOND = 1;

function statusOf(panel) {
  return panel.getByLabel("Collection status").nth(SECOND);
}

function invoiceOf(panel) {
  return panel.getByLabel("Invoice number").nth(SECOND);
}

async function moneyTab(page) {
  return openJobTab(page, await openJob(page), "Money");
}

// `saveInvoiceNo` returns early without mutating when the stored number
// already equals the typed one, so saving the same value twice would wait for
// a request that is never sent. It cannot happen within a run - the seed
// leaves this milestone blank and the last test puts it back - but it is how
// `saving` hangs here, and a hang is not self-explaining.
const SET_STATUS = "auraos.api.set_milestone_status";

test("an invoice number belongs to an invoiced milestone and nowhere else", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  const panel = await moneyTab(page);

  await expect(panel.getByText("Payment milestones")).toBeVisible();

  // Closed rather than merely ignored. The server refuses a number sent with
  // any other status, and the screen asks the same question rather than letting
  // someone type into a field whose contents would be thrown away.
  await expect(statusOf(panel)).toHaveValue("Not requested");
  await expect(invoiceOf(panel)).toBeDisabled();
  await expect(invoiceOf(panel)).toHaveValue("");
  // The field says why it is closed, which is the difference between a
  // disabled control and a broken one.
  await expect(invoiceOf(panel)).toHaveAttribute("title", /set the status first/i);
  expect(failures).toEqual([]);
});

test("marking a milestone invoiced opens the field, and the number is kept", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  const panel = await moneyTab(page);

  await saving(page, SET_STATUS, () => statusOf(panel).selectOption("Invoiced"));
  await expect(invoiceOf(panel)).toBeEnabled();

  // Typed and blurred, the way it is entered: the number is saved on blur, not
  // by a button, so a test that only fills the box asserts nothing.
  await invoiceOf(panel).fill("PW-E2E-0126");
  await saving(page, SET_STATUS, () => invoiceOf(panel).blur());

  // Read back from the server rather than from React's state. Without the
  // reload a green would only prove the input holds what was typed into it.
  //
  // The reload is right and it was not enough: it answers *where* the value
  // came from and says nothing about *whether the write finished*. Two
  // questions, and the careful reasoning about the first is exactly what made
  // the second easy to miss.
  await page.reload();
  const reloaded = await moneyTab(page);
  await expect(statusOf(reloaded)).toHaveValue("Invoiced");
  await expect(invoiceOf(reloaded)).toHaveValue("PW-E2E-0126");
  expect(failures).toEqual([]);
});

test("walking the status back takes the invoice number with it", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  const panel = await moneyTab(page);

  // Precondition, asserted rather than assumed: this test is only meaningful if
  // the previous one left a number here.
  await expect(invoiceOf(panel)).toHaveValue("PW-E2E-0126");

  await saving(page, SET_STATUS, () => statusOf(panel).selectOption("Not requested"));

  // The point of the whole spec. An invoice number that survived this would be
  // a number nobody issued, sitting on a milestone the client has not been
  // billed for - and T9 reads exactly that field to find uncovered spend.
  await page.reload();
  const reloaded = await moneyTab(page);
  await expect(statusOf(reloaded)).toHaveValue("Not requested");
  await expect(invoiceOf(reloaded)).toHaveValue("");
  await expect(invoiceOf(reloaded)).toBeDisabled();

  // And the fixture is back where the seed left it, which is this spec's job
  // rather than the seed's - see #134 for why that cannot be assumed.
  expect(failures).toEqual([]);
});

test("the invoice request is the accountant's message, with the gaps named", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  const panel = await moneyTab(page);

  await panel.getByRole("button", { name: "Invoice request" }).nth(SECOND).click();

  // Asserted on the text that is *shown*, not on the clipboard: the panel says
  // in its own comment that it renders the request as well as copying it, "so
  // a browser that refuses the clipboard still leaves them something to
  // select". The heading flips on whether the copy succeeded, so it is
  // deliberately not asserted - the message body does not.
  const request = panel.locator("pre");
  await expect(request).toContainText("Nhờ chị xuất hoá đơn giúp em:");
  await expect(request).toContainText(`Khách hàng: ${COMPANY}`);
  await expect(request).toContainText("Số tiền:");
  await expect(request).toContainText("Em cảm ơn chị!");

  // **The seeded client has no tax code, and that is the case worth having.**
  // A blank there sends the accountant back with a question; the message writes
  // the gap out as a gap instead. Nobody arranged this fixture for it - the
  // company was seeded with a name and nothing else.
  await expect(request).toContainText("Mã số thuế: (chưa có trong hệ thống)");

  // Reading the request must not move the milestone: sending it is a separate,
  // human act, and the screen says so.
  await expect(panel.getByText(/Copying does not change the milestone/i)).toBeVisible();
  await expect(statusOf(panel)).toHaveValue("Not requested");
  expect(failures).toEqual([]);
});
