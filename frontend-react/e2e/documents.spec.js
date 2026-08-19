// The Documents screen, both halves of it (#66, spec'd by #128).
//
// Written by a lane that did not build it, which is standing rule 23: the
// person who chose a behaviour is the worst person to write the test that
// says the behaviour is still there, because they will assert what they
// meant rather than what shipped.
//
// Three of the six tests below are about a distinction rather than a figure.
// Paperwork is transactional - a template filled from a job's records, with a
// lifecycle - and the Library is knowledge, written once and read often. The
// design decision was two lists under one roof, and a suite that passed just
// as happily against one merged list would have tested the roof and missed the
// building. So the separation is asserted in both directions, on the screen
// and in the payloads underneath it.
//
// Nothing here asserts a count the seed happens to produce. Every quantity is
// compared against what the endpoint sent, for the same reason the finance
// specs do it: the seed grows, and a spec that pins its size turns every
// future fixture change into a red belonging to nobody.

import { expect, test } from "@playwright/test";

import { producerState } from "./auth-state.js";
import { callAs } from "./call.js";

const producerTest = test.extend({ storageState: producerState });

const LIBRARY = "auraos.api.library_documents";
const DETAIL = "auraos.api.library_document_detail";
const TEMPLATES = "auraos.api.paperwork_library";
const PAPERS = "auraos.api.generated_papers";

const PAPERWORK_URL = "/aura-next/documents/paperwork";
const LIBRARY_URL = "/aura-next/documents/library";

/** The SOP that #66 moved out of a Vue page. Named by the patch that seeds it,
 *  auraos/patches/seed_sop_deals_library_document.py, and not by the e2e seed -
 *  so it is on every site the app has ever been installed on, which is why this
 *  file can assert against it without waiting on a fixture. */
const SOP = "SOP - Đánh giá & phân loại deal";

async function openTab(page, url, tab) {
  await page.goto(url);
  // The tab strip, not the nav: both say "Paperwork" and "Library", and the
  // heading is "Documents" on both routes.
  await expect(page.getByRole("link", { name: tab, exact: true })).toHaveAttribute(
    "data-status",
    "active",
  );
}

// -- one roof, two lists --

test("the two halves are two lists, on the screen and in the payloads", async ({ page }) => {
  await openTab(page, LIBRARY_URL, "Library");

  const documents = await callAs(page, LIBRARY);
  const templates = await callAs(page, TEMPLATES);
  const papers = await callAs(page, PAPERS);
  for (const [what, answer] of [
    ["the library", documents],
    ["the template library", templates],
    ["the generated papers", papers],
  ]) {
    expect(answer.status, `${what} was refused: ${JSON.stringify(answer.body)}`).toBe(200);
  }

  const titles = (documents.body.message?.documents ?? []).map((row) => row.title);
  const templateNames = (templates.body.message?.templates ?? []).map((row) => row.template_name);
  const paperNames = (papers.body.message ?? []).map((row) => row.file_name ?? row.name);

  // The fixture has to be able to tell the two apart before anything below
  // means something. A site with an empty library would pass every "does not
  // appear" assertion in this file for the wrong reason.
  expect(
    titles.length,
    "the library is empty, so nothing here is being told apart",
  ).toBeGreaterThan(0);
  expect(
    templateNames.length,
    "there are no paperwork templates, so nothing here is being told apart",
  ).toBeGreaterThan(0);

  // The lists are disjoint at the source. If the two endpoints ever start
  // answering out of one table, this fails before any screen assertion does.
  const shared = titles.filter((title) => templateNames.includes(title));
  expect(shared, `a name is in both lists: ${shared.join(", ")}`).toEqual([]);

  // And on the screen, in both directions. A document belongs to the Library
  // tab and a template to the Paperwork tab, and neither leaks into the other.
  const main = page.getByRole("main");
  await expect(main.getByText(SOP, { exact: false }).first()).toBeVisible();
  for (const name of templateNames) {
    await expect(main.getByText(name, { exact: true })).toHaveCount(0);
  }

  await openTab(page, PAPERWORK_URL, "Paperwork");
  await expect(page.getByRole("main").getByText(SOP, { exact: false })).toHaveCount(0);
  // Templates and papers are both on this tab and they are two cards, not one
  // list: the papers card exists even when a template of the same name does.
  await expect(page.getByRole("heading", { name: "Template library" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Generated papers" })).toBeVisible();
  expect(paperNames.length).toBeGreaterThanOrEqual(0);
});

// The bug that would have shipped invisibly. The nav's active test was
// `pathname.startsWith(item.to)`, and the one Documents item points at
// /documents/paperwork - so opening the Library tab took the section light out
// while the user was still inside the section. Contacts never hit it because
// it spends two nav items on two tabs.
//
// Asserted through the class, which is the only signal the DOM carries today.
// #136 is open to give the nav an aria-current; when it lands this assertion
// should move to it, and the move is a strict improvement rather than a
// rewrite - the claim is the same claim.
test("the Documents nav item stays lit on both tabs", async ({ page }) => {
  for (const [url, tab] of [
    [PAPERWORK_URL, "Paperwork"],
    [LIBRARY_URL, "Library"],
  ]) {
    await openTab(page, url, tab);
    // Not scoped through getByRole("navigation"): the sidebar is a <nav> and
    // so is the tab strip, so that locator matches two landmarks and a strict
    // mode violation is a crash, not a failure. The nav item is the only link
    // on the page whose whole name is "Documents" - the tabs say Paperwork and
    // Library - so it can be named directly.
    const item = page.getByRole("link", { name: "Documents", exact: true });
    await expect(item, `the section light went out on the ${tab} tab`).toHaveClass(/bg-secondary/);
  }
});

// -- the document that used to be a page --

test("the SOP opens and its tier matrix renders as a table with visible rules", async ({
  page,
}) => {
  await openTab(page, LIBRARY_URL, "Library");
  await page.getByRole("button", { name: SOP }).first().click();

  const window = page.getByRole("dialog", { name: SOP });
  await expect(window).toBeVisible();

  // Four columns - Trạm and three tiers - and a body with a row per station.
  // The header row is what says the migration kept the matrix a matrix: the
  // Vue page drew it with divs, and sanitize_html would drop a table the
  // editor could not produce.
  const table = window.locator(".aura-rich table");
  await expect(table).toHaveCount(1);
  await expect(table.locator("thead th")).toHaveCount(4);
  expect(await table.locator("tbody tr").count()).toBeGreaterThan(1);

  // `.aura-rich` carried no table rules at all until #66 added them, so a
  // table rendered inside it read as four columns of text with nothing
  // separating them. That is invisible to a structural assertion and obvious
  // to a person, which is exactly the kind of regression a spec is for.
  const ruled = await table
    .locator("thead th")
    .first()
    .evaluate((cell) => {
      const style = getComputedStyle(cell);
      return {
        borderBottom: style.borderBottomStyle,
        width: parseFloat(style.borderBottomWidth),
        padding: parseFloat(style.paddingLeft),
      };
    });
  expect(ruled.borderBottom, "the tier matrix has no rules, so it reads as loose text").not.toBe(
    "none",
  );
  expect(ruled.width).toBeGreaterThan(0);
  expect(ruled.padding).toBeGreaterThan(0);
});

test("the SOP states no positioning mix, and says where the mix lives", async ({ page }) => {
  await openTab(page, LIBRARY_URL, "Library");
  await page.getByRole("button", { name: SOP }).first().click();
  const window = page.getByRole("dialog", { name: SOP });
  await expect(window).toBeVisible();

  const body = String((await window.locator(".aura-rich").textContent()) ?? "");
  expect(body.length, "the document rendered empty").toBeGreaterThan(200);

  // The absence of a figure, not the absence of a word. The Vue page
  // interpolated the live cash/bridge/brand targets in two places; the founder
  // replaced both with a pointer to Settings, because a document that states
  // the mix becomes a lie the first time the mix is retuned and nothing on
  // screen marks it stale. `positioning_mix()` falls back to 70/20/10 whenever
  // the setting is unset, so a transcription would have looked right on the
  // day it ran whatever the site was configured for.
  //
  // Matched as numbers rather than as prose: a spec that asserted the string
  // "70/20/10" would pass a document that had quietly grown "70% / 20% / 10%".
  expect(body, "the SOP states a positioning mix again").not.toMatch(/\d+\s*%/);
  expect(body).not.toMatch(/70\s*[/-]\s*20\s*[/-]\s*10/);

  // And the pointer is there, which is the other half of the decision. Without
  // this, deleting the sentence would turn the assertion above green.
  expect(body, "the document no longer says where the mix lives").toMatch(/Settings/);
});

// -- the point of the whole ticket --

test("a document written in the app is there after a reload", async ({ page }) => {
  await openTab(page, LIBRARY_URL, "Library");

  // A document of this spec's own, not the SOP. The SOP's seed patch is keyed
  // off its title, so a spec that renamed it would make the patch re-seed a
  // second copy on the next migrate - and editing its body in place would
  // leave a failed run's half-edit on a document the whole company reads.
  const stamp = String(process.pid);
  const title = `Playwright spec document ${stamp}`;
  const body = `Written by the spec at pid ${stamp}.`;
  let written = null;

  try {
    await page.getByRole("button", { name: "New document" }).click();
    const editor = page.getByRole("dialog", { name: "New document" });
    await editor.getByLabel("Title").fill(title);
    await editor.getByLabel("Category").fill("SOP");
    await editor.getByRole("textbox", { name: "Document body" }).fill(body);
    await editor.getByRole("button", { name: "Save", exact: true }).click();

    // Saving opens the new document, which is the app's own confirmation that
    // the write came back with a name rather than that a dialog closed.
    await expect(page.getByRole("dialog", { name: title })).toBeVisible();
    // Scoped to the dialog and taken last: Modal renders a backdrop button and
    // a header X, both labelled Close, and the footer's is the one a person
    // presses. An unscoped locator here is a strict mode violation, not a pass.
    await page
      .getByRole("dialog", { name: title })
      .getByRole("button", { name: "Close" })
      .last()
      .click();

    // The reload is the assertion. Without it this proves the list re-rendered
    // from a cache that a successful-looking mutation had already updated.
    await page.reload();
    await expect(page.getByRole("main").getByText(title, { exact: true }).first()).toBeVisible();

    const index = await callAs(page, LIBRARY);
    const row = (index.body.message?.documents ?? []).find((one) => one.title === title);
    expect(row, "the saved document is not in the library index").toBeTruthy();
    written = row.name;

    // The body survived the round trip through the Text Editor field, which
    // sanitises on save. A title-only check would pass a document whose prose
    // was thrown away.
    const detail = await callAs(page, DETAIL, { name: written });
    expect(detail.status).toBe(200);
    expect(detail.body.message.body).toContain(stamp);
  } finally {
    // Through frappe.client.delete, because the app has no way to delete a
    // Library document - the same shape as the missing expense delete on #125,
    // and said out loud here so nobody reads this spec as evidence that a
    // person could undo what it just did. workers is 1 and fullyParallel is
    // off, so whatever this leaves behind, every later file reads.
    if (written) {
      const gone = await callAs(page, "frappe.client.delete", {
        doctype: "Library Document",
        name: written,
      });
      expect(gone.status, `the spec could not remove ${written}`).toBe(200);
    }
  }
});

// -- the renamed route, and the gate on writing --

test("the paperwork tab still answers at its renamed route", async ({ page }) => {
  await openTab(page, PAPERWORK_URL, "Paperwork");

  const templates = await callAs(page, TEMPLATES);
  expect(templates.status).toBe(200);
  const rows = templates.body.message?.templates ?? [];
  const placeholders = templates.body.message?.placeholders ?? [];

  // Every template the server lists is on the screen, by name. Counted off the
  // payload rather than pinned at a number, so #130 growing the fixture does
  // not make this red.
  const main = page.getByRole("main");
  for (const row of rows) {
    await expect(main.getByText(row.template_name, { exact: true }).first()).toBeVisible();
  }

  // The placeholder card names its own size, and the card exists because a
  // person writing a template needs to know what they may write.
  await expect(
    page.getByRole("heading", { name: `Placeholders a template can use (${placeholders.length})` }),
  ).toBeVisible();

  // The founder's write affordance. A producer sees the tab and not this,
  // which the next test asserts from the other side.
  await expect(page.getByRole("heading", { name: "New template" })).toBeVisible();
});

producerTest("a producer reads both tabs and is offered no way to write", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  await openTab(page, PAPERWORK_URL, "Paperwork");
  await expect(page.getByRole("heading", { name: "Template library" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "New template" })).toHaveCount(0);

  await openTab(page, LIBRARY_URL, "Library");
  await expect(page.getByRole("main").getByText(SOP, { exact: false }).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "New document" })).toHaveCount(0);

  // The gate is the server's: can_manage comes back false, and the screen is
  // reading it rather than deciding for itself. A screen that hid the button
  // on its own would pass the two assertions above on a site where the
  // producer could still write.
  const index = await callAs(page, LIBRARY);
  expect(index.status).toBe(200);
  expect(index.body.message.can_manage).toBe(false);

  expect(failures).toEqual([]);
});
