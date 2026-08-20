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
// The active state is expressed only through Tailwind classes today - there is
// no aria-current, which #136 is open to add.
//
// **The first version of this test could not fail.** It asserted
// `toHaveClass(/bg-secondary/)`, and the *inactive* branch of the same
// className in AppShell is `text-muted-foreground hover:bg-secondary/70
// hover:text-foreground` - in which `hover:bg-secondary/70` contains the
// substring `bg-secondary`. Delete the `match` prop, let the section light go
// out on Library exactly as it did before #66, and the assertion still passed.
// The one test written for that regression could not see it, and it went green.
//
// The general form, worth more than this file: **a substring regex over a
// Tailwind class list is not an assertion about state, because the hover
// variant of a colour contains the colour.**
//
// So the assertion is "unchanged" and names no class: capture whatever the lit
// value is where the section is unambiguously current, and require the other
// tab to match it. A restyle then leaves this test alone.
//
// The sibling check is what makes the captured value mean anything. Without it
// the test would pass just as happily against a nav that lit nothing at all,
// because "unchanged" is also true of two identically dark items.
//
// Both halves are the #115 lane's, from their own draft of this file - two
// lanes were sent #128 by mistake, and they found the vacuity by writing the
// assertion the other way and going looking for the difference.
//
// **And comparing the whole attribute failed in run 19, correctly.** TanStack
// appends its own `active` token to a Link whose `to` matches the URL exactly
// (link.js: `STATIC_ACTIVE_OBJECT = { className: "active" }`), and this nav
// item points at `/documents/paperwork` - so it carries the token on Paperwork
// and not on Library, while the app's own lit classes are on both. The nav was
// working; the assertion was comparing the router's opinion along with the
// app's, and its failure message said the light had gone out when it had not.
//
// **A red that lies about what is wrong is worse than a noisy one**, because
// the next person goes and looks at the nav. So the comparison is over the
// app's tokens only: split on whitespace, drop what the router owns, compare
// as sets. Whole tokens rather than a substring, which is what the first
// version got wrong in the other direction.
//
// **All of that is now history rather than mechanism.** Three drafts spent
// working out which classes mean "current" is what argued for #136: the
// information existed and the DOM did not say it. The test below asserts
// `aria-current` and none of the above applies to it - kept because it is the
// case for the attribute, and because the next person to reach for a class as
// a state signal should see how that went.

test("the Documents nav item stays lit on both tabs", async ({ page }) => {
  // Now asserted on `aria-current`, which #136 added for this reason and for
  // the better one: the open section used to be carried by background colour
  // alone. The class comparison this replaces was sound but was reasoning
  // about Tailwind - and the version before *that* matched `bg-secondary` as
  // a substring, which the inactive branch also contains via
  // `hover:bg-secondary/70`, so it passed on a nav item that was dark.
  //
  // Not scoped through getByRole("navigation"): the sidebar is a <nav> and so
  // is the tab strip, so that locator matches two landmarks and a strict mode
  // violation is a crash, not a failure. The nav item is the only link on the
  // page whose whole name is "Documents" - the tabs say Paperwork and Library.
  const navItem = () => page.getByRole("link", { name: "Documents", exact: true });

  await openTab(page, PAPERWORK_URL, "Paperwork");
  await expect(navItem()).toHaveAttribute("aria-current", "page");

  // The half that keeps this from being a tautology, kept from the class
  // version: a nav that marked *every* item current would satisfy the two
  // assertions around this one.
  await expect(
    page.getByRole("link", { name: "Deals", exact: true }),
    "a section nobody is in is also marked current",
  ).not.toHaveAttribute("aria-current", "page");

  await openTab(page, LIBRARY_URL, "Library");
  await expect(navItem(), "the section light went out on the Library tab").toHaveAttribute(
    "aria-current",
    "page",
  );
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
  // Named, not counted - also the #115 lane's, and better for the same reason:
  // four columns of the wrong thing would pass a count. The coupling is to the
  // migrated document, which the founder may now edit in the app, so a red here
  // means "the tier matrix changed" and should be read before it is loosened.
  await expect(table.locator("thead th")).toHaveText(["Trạm", "Tier 1", "Tier 2", "Tier 3"]);
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

// -- a document has an address of its own (#124) --
//
// The founder's complaint was that sending someone a link landed them on the
// tab rather than on the document. So the subject of every test below is the
// **URL**, and the trap they are written against is that a screen driven by
// local state passes almost all of them: opening a document from the list
// looks identical whether or not the address bar learned anything.
//
// Which is why the fourth one is the load-bearing test. The builder said so
// themselves, and they are right - it is the only one that fails if the
// navigation is wired to the wrong place while every other assertion still
// passes on local state.
//
// **Not asserted here, deliberately: that a deep link discriminates per
// record.** `library_document_detail` opens with a doctype-level
// `has_permission`, which answers "may this person read Library Documents"
// and not "may they read this one" - correct today, because any reader may
// read any of them, and the route file says so where the exposure is. A spec
// that asserted per-record refusal would be describing a product we do not
// have, which is #143's lesson one ticket over.

/** The stored name behind a title. The URL carries the name, and only the
 *  server knows it - Frappe mints it, and no fixture may hardcode it. */
async function libraryName(page, title) {
  const answer = await callAs(page, LIBRARY);
  expect(answer.status, `the library was refused: ${JSON.stringify(answer.body)}`).toBe(200);
  const row = (answer.body.message?.documents ?? []).find((one) => one.title === title);
  expect(row, `no library document titled ${JSON.stringify(title)}`).toBeTruthy();
  return row.name;
}

const documentWindow = (page, name) => page.getByRole("dialog", { name });

test("a link to a document opens that document, not the list it lives in", async ({ page }) => {
  await openTab(page, LIBRARY_URL, "Library");
  const name = await libraryName(page, SOP);

  // A cold load at the address, the way a recipient of the link arrives -
  // rather than navigating there from a page that already had the document in
  // hand. The distinction is the whole ticket.
  await page.goto(`${LIBRARY_URL}/${name}`);

  await expect(documentWindow(page, SOP)).toBeVisible();
  await expect(documentWindow(page, SOP).locator(".aura-rich table")).toHaveCount(1);
});

test("refreshing a document's address reopens the same document", async ({ page }) => {
  await openTab(page, LIBRARY_URL, "Library");
  const name = await libraryName(page, SOP);
  await page.goto(`${LIBRARY_URL}/${name}`);
  await expect(documentWindow(page, SOP)).toBeVisible();

  await page.reload();

  // The same document, and the address unchanged - a reload that dropped the
  // param would still show *a* library and would fail here rather than
  // quietly landing on the list.
  await expect(documentWindow(page, SOP)).toBeVisible();
  expect(page.url()).toContain(`/documents/library/${name}`);
});

// The load-bearing one. Everything else in this section could pass against a
// screen that opens documents from local state and never touches the address.
test("opening a document from the list moves the address bar", async ({ page }) => {
  await openTab(page, LIBRARY_URL, "Library");
  const name = await libraryName(page, SOP);
  expect(page.url()).not.toContain(name);

  await page.getByRole("button", { name: SOP }).first().click();

  await expect(documentWindow(page, SOP)).toBeVisible();
  // Polled rather than read once: the window is drawn from the same navigation
  // that writes the address, and asserting the URL the instant the dialog
  // appears would be a race rather than a claim.
  await expect
    .poll(() => new URL(page.url()).pathname)
    .toBe(`/aura-next/documents/library/${name}`);
});

test("going back closes the document and leaves the list as it was", async ({ page }) => {
  await openTab(page, LIBRARY_URL, "Library");
  const name = await libraryName(page, SOP);

  // A search first, because "returns to the list" is a weak claim if the list
  // it returns to has forgotten what the reader had done to it. The term is a
  // fragment of the seeded SOP's own title, so it matches on any site that has
  // the patch and needs no fixture of its own.
  const search = page.getByLabel("Search the library");
  await search.fill("phân loại");
  const shown = await page.getByRole("button", { name: SOP }).count();
  expect(shown, "the search matched nothing, so this test asserts nothing").toBeGreaterThan(0);

  await page.getByRole("button", { name: SOP }).first().click();
  await expect(documentWindow(page, SOP)).toBeVisible();

  await page.goBack();

  await expect(documentWindow(page, SOP)).toHaveCount(0);
  expect(new URL(page.url()).pathname).toBe("/aura-next/documents/library");
  // The state the list route holds, still held: the child route renders
  // nothing and the list never unmounted, which is what makes back cheap.
  await expect(search).toHaveValue("phân loại");
  expect(await page.getByRole("button", { name: SOP }).count()).toBe(shown);
});

test("an address that names no document says so inside the window", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  // The shape a stale or mistyped link arrives in. It must not be a blank
  // dialog and must not be a crash: the window opens on the fallback title and
  // the query's failure renders where the document would have been.
  await page.goto(`${LIBRARY_URL}/NOT-A-DOCUMENT-0000`);

  const window = documentWindow(page, "Document");
  await expect(window).toBeVisible();
  await expect(window.getByRole("alert")).toBeVisible();
  // An empty dialog would satisfy "no document is shown" just as well, so the
  // assertion is that something was said.
  expect(
    String((await window.getByRole("alert").textContent()) ?? "").trim().length,
  ).toBeGreaterThan(0);
  expect(failures).toEqual([]);
});

producerTest(
  "a producer reads a linked document and is offered no way to edit it",
  async ({ page }) => {
    await openTab(page, LIBRARY_URL, "Library");
    const name = await libraryName(page, SOP);

    await page.goto(`${LIBRARY_URL}/${name}`);
    const window = documentWindow(page, SOP);
    await expect(window).toBeVisible();

    // The link is not a bypass: the same server check answers whatever route
    // reached it. Read is allowed - a producer may read the SOP - and writing is
    // the founder's, decided by the server rather than by the screen.
    await expect(window.getByRole("button", { name: "Edit", exact: true })).toHaveCount(0);
    const index = await callAs(page, LIBRARY);
    expect(index.status).toBe(200);
    expect(index.body.message.can_manage).toBe(false);
  },
);
