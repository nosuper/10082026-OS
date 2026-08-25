import { expect, test } from "@playwright/test";

import { callAs } from "./call.js";

// #118, the "+ New client..." row on the deal form's company picker.
//
// **Written by a lane that did not build it** (rule 23). The builder recorded
// their intent and I have written assertions against it; where I have had to
// choose, I have chosen what a cold reader would expect and said so.
//
// The behaviour is small and the risk is not: this dialog opens **over a form
// that may already have unsaved work in it**, and the cheap implementation -
// reset the draft, or write the picker's sentinel into it - loses that work in
// a way nobody notices until a deal comes back wrong.
//
// **Cleanup is in `finally`, through `frappe.client.delete`, and the product
// has no delete for a Party Company.** That asymmetry is deliberate and worth
// stating rather than hiding: a studio does not delete clients, so the app
// offers no way to. A spec that creates one is therefore obliged to remove it
// by a door no user has, because `workers: 1` means everything after this file
// reads the site it leaves behind - and #135 means the re-seed cannot be
// relied on to tidy up either.
//
// Selector notes: `Field` wraps its control in a `<label>`, so `getByLabel`
// reaches the picker. The picker is a `<select>` - its value lives in `value`
// where `getByText` cannot see it, and the *label* of the chosen row lives in
// `option:checked`, which is the difference this spec turns on twice.

const SEEDED_DEAL = "Playwright Existing Deal";

/** The sentinel the picker uses for its create row. Safe because Party Company
 *  is `autoname: format:COM-{####}`, so no real record can be called this. */
const NEW_COMPANY = "__new_company__";

/** Distinct enough to sweep, and never the seeded client. */
const PREFIX = "Playwright E2E118";

function companyName() {
  return `${PREFIX} ${Date.now()}`;
}

async function openSeededDeal(page) {
  await page.goto("/aura-next/deals");
  await page.getByRole("link", { name: SEEDED_DEAL }).first().click();
  await expect(page).toHaveURL(/\/aura-next\/deals\/DEAL-/);
  return page.url().split("/").pop();
}

const picker = (page) => page.getByLabel("Client company");
const dialog = (page) => page.getByRole("dialog", { name: "New client" });

/** The row the picker is showing, as text. Not `toHaveValue`, which is COM-0142. */
async function chosenLabel(page) {
  return (await picker(page).locator("option:checked").innerText()).trim();
}

/** Every company this file has ever created, including a crashed earlier run's. */
async function strays(page) {
  const found = await callAs(page, "frappe.client.get_list", {
    doctype: "Party Company",
    filters: [["company_name", "like", `${PREFIX}%`]],
    fields: ["name"],
    limit_page_length: 0,
  });
  return (found.body?.message ?? []).map((row) => row.name);
}

async function sweep(page) {
  for (const name of await strays(page)) {
    const gone = await callAs(page, "frappe.client.delete", {
      doctype: "Party Company",
      name,
    });
    expect(gone.status, `could not remove ${name}: ${JSON.stringify(gone.body)}`).toBe(200);
  }
}

test("choosing the create row is an action, and never a value", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  await openSeededDeal(page);

  // The row exists and carries the sentinel, which is the contract between the
  // option and the handler that reads it.
  await expect(picker(page).locator(`option[value="${NEW_COMPANY}"]`)).toHaveText(
    "+ New client...",
  );

  const before = await picker(page).inputValue();
  expect(before, "the seeded deal should already have a client").not.toBe("");

  await picker(page).selectOption(NEW_COMPANY);
  await expect(dialog(page)).toBeVisible();

  // The browser really does set the select to `__new_company__` for an
  // instant. The handler declines to write it to the draft and opens the
  // dialog, and the re-render that opening causes snaps the controlled select
  // back to the real client.
  await expect(picker(page)).toHaveValue(before);

  await dialog(page).getByRole("button", { name: "Cancel" }).click();
  await expect(dialog(page)).toHaveCount(0);
  await expect(picker(page)).toHaveValue(before);

  // **This is the assertion that the draft is untouched, and the two above are
  // not.** The select's DOM value and the draft are different things: the
  // sentinel could sit in the DOM while the draft was clean, or the reverse,
  // and neither assertion above can tell those apart. Save is enabled only
  // when the draft differs from what the server holds - so a Save still
  // disabled after a full open-and-cancel is the form saying, in its own
  // terms, that nothing was written. Nothing has been typed in this test, so
  // any change at all would light it.
  await expect(page.getByRole("button", { name: "Save", exact: true })).toBeDisabled();
  expect(failures).toEqual([]);
});

test("cancelling writes nothing and loses nothing", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  await openSeededDeal(page);

  const company = await picker(page).inputValue();
  const contact = await page.getByLabel("Contact").inputValue();

  // Dirty the form *before* opening the dialog. This is the whole test: the
  // builder expected this one to break, and the way it breaks is a dialog that
  // resets the draft it opened over. Nobody types into a form and then opens
  // this dialog in a unit test; they do it constantly in real life.
  const typed = `${SEEDED_DEAL} - unsaved edit`;
  await page.getByLabel("Title").fill(typed);

  await picker(page).selectOption(NEW_COMPANY);
  await expect(dialog(page)).toBeVisible();
  const abandoned = companyName();
  await dialog(page).getByPlaceholder("Company name").fill(abandoned);

  await dialog(page).getByRole("button", { name: "Cancel" }).click();
  await expect(dialog(page)).toHaveCount(0);

  // Nothing typed before the dialog is gone, and nothing chosen has changed.
  await expect(page.getByLabel("Title")).toHaveValue(typed);
  await expect(picker(page)).toHaveValue(company);
  await expect(page.getByLabel("Contact")).toHaveValue(contact);

  // And nothing was written. Asked of the server rather than inferred from the
  // screen: a dialog that created the record and then failed to select it
  // would leave this screen looking exactly like a clean cancel.
  const created = await callAs(page, "frappe.client.get_list", {
    doctype: "Party Company",
    filters: [["company_name", "=", abandoned]],
    fields: ["name"],
  });
  expect(created.body?.message ?? [], "cancel created a Party Company").toEqual([]);

  // Deliberately not saved: the draft is abandoned by navigating away, which
  // is what leaves the seeded deal as the rest of the suite expects it.
  expect(failures).toEqual([]);
});

test("creating selects the new client in, without leaving the form", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  await openSeededDeal(page);
  const url = page.url();
  const contact = await page.getByLabel("Contact").inputValue();

  const typed = `${SEEDED_DEAL} - still here`;
  await page.getByLabel("Title").fill(typed);

  const wanted = companyName();
  try {
    await picker(page).selectOption(NEW_COMPANY);
    await dialog(page).getByPlaceholder("Company name").fill(wanted);
    await dialog(page).getByRole("button", { name: "Create and select" }).click();
    await expect(dialog(page)).toHaveCount(0);

    // Selected, and selected as a real record: the value is the generated
    // name, which is what proves an insert happened rather than a local
    // placeholder being appended to the options.
    await expect(picker(page)).toHaveValue(/^COM-\d+$/);

    // **And the row reads as what was typed.** Frappe answers an insert with
    // COM-0142, and the list that carries the real label has not refetched
    // yet - so for a moment the screen could show a code the person has never
    // seen, which reads as the wrong company having been chosen. Asserting the
    // label rather than the value is asserting that deliberate choice.
    //
    // Honest limit: this asserts the *outcome*, which holds both during that
    // gap and after the refetch lands. It does not isolate the gap itself -
    // that would need the list request stalled on purpose, and a spec that
    // stalls a request to observe a frame is testing its own instrumentation.
    expect(await chosenLabel(page)).toBe(wanted);
    expect(await chosenLabel(page), "the picker showed the generated code").not.toContain("COM-");

    // Still on the deal, with everything typed before the dialog intact.
    expect(page.url()).toBe(url);
    await expect(page.getByLabel("Title")).toHaveValue(typed);

    // **Asserted as intent, not as an oversight.** Changing the company leaves
    // the contact alone everywhere else on this form - the picker filters and
    // the saved one stays reachable - and creating a company is not a reason
    // for a second rule. If this ever fails, read the builder's note before
    // deciding it is a bug.
    await expect(page.getByLabel("Contact")).toHaveValue(contact);
    expect(failures).toEqual([]);
  } finally {
    // The draft was never saved, so the deal still points at its seeded
    // client and only the company needs removing.
    await sweep(page);
  }
});

test("a client created here is really the deal's client after a save", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  const deal = await openSeededDeal(page);
  const original = await picker(page).inputValue();
  const wanted = companyName();

  try {
    await picker(page).selectOption(NEW_COMPANY);
    await dialog(page).getByPlaceholder("Company name").fill(wanted);
    await dialog(page).getByRole("button", { name: "Create and select" }).click();
    await expect(dialog(page)).toHaveCount(0);
    await expect(picker(page)).toHaveValue(/^COM-\d+$/);
    const chosen = await picker(page).inputValue();

    await page.getByRole("button", { name: "Save", exact: true }).click();

    // **This screen is where #117 lived**: a write that landed on the server
    // while the page kept rendering a stale snapshot, so the header and a
    // second card both showed the old value and it read as a failed save. A
    // reload is the only assertion that cannot be satisfied by client state,
    // which is why it is here and not an equivalent in-page check.
    await page.reload();
    await expect(picker(page)).toHaveValue(chosen);
    expect(await chosenLabel(page)).toBe(wanted);
    expect(failures).toEqual([]);
  } finally {
    // Order matters: put the deal back before removing the company, or the
    // seeded deal spends the rest of the run pointing at a record that is not
    // there. Every later file reads this deal.
    const restored = await callAs(page, "frappe.client.set_value", {
      doctype: "Deal",
      name: deal,
      fieldname: "company",
      value: original,
    });
    expect(
      restored.status,
      `the seeded deal was left on a throwaway client: ${JSON.stringify(restored.body)}`,
    ).toBe(200);
    await sweep(page);
  }
});
