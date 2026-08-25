// The comment thread and the file manager (#28 / T3.4), ported from the Vue
// suite along with the screens.
//
// The permission rules — you may edit and delete only your own comments, you
// may manage a file if you may write the deal — are pinned by site tests in
// `auraos/auraos/doctype/deal/test_deal_collab.py`. This file does not re-test
// them: the e2e suite signs in as one seat at a time, so a spec claiming to
// prove "the other seat cannot" from the browser would be claiming more than it
// checks.
//
// What only a browser can show is that the thread is an editor rather than a
// textarea, that a mention leaves the markup the server actually reads, and
// that editing marks a comment edited rather than quietly replacing it.
//
// Written as a change against the state a moment earlier, and unwound in a
// finally block: workers is 1 and fullyParallel is off, so a spec that failed
// halfway would hand every later file a different set of comments.

import { expect, test } from "@playwright/test";

import { callAs } from "./call.js";
import { firstName } from "./records.js";
import { JOB_DEAL } from "./fixture.js";

const THREAD = "auraos.api.deal_comments";

async function openDeal(page) {
  const deal = await firstName(page, "Deal", { title: JOB_DEAL });
  expect(deal, "the seeded deal is missing").toBeTruthy();
  await page.goto(`/aura-next/deals/${deal}`);
  await expect(page.getByRole("heading", { name: "Comments" })).toBeVisible();
  return deal;
}

/**
 * How many comments the server holds, polled rather than read once.
 *
 * The first version of this file read it straight after `.click()`, which is
 * before the POST has landed - and the page-wide text assertion beside it
 * passed anyway, because the composer still held a copy of what had just been
 * typed. Two mistakes hiding each other: a race, and an assertion that could
 * not tell a posted comment from an unsent draft.
 */
async function threadCount(page, deal) {
  const answer = await callAs(page, THREAD, { deal });
  expect(answer.status, `the thread was refused: ${JSON.stringify(answer.body)}`).toBe(200);
  return answer.body.message.length;
}

/** The composer is a contentEditable, not a textarea - type into it as one. */
async function writeComment(page, text) {
  const editor = page.getByRole("textbox", { name: "New comment" });
  await editor.click();
  await page.keyboard.press("ControlOrMeta+a");
  await editor.pressSequentially(text);
  return editor;
}

test("a comment posts, edits and deletes from the deal card", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  const deal = await openDeal(page);
  const before = await threadCount(page, deal);
  const written = [];
  // Declared once, used for every control that belongs to the thread. The page
  // header carries its own Save and the deal card its own Delete, so scoping by
  // role and name alone resolves to two elements and Playwright refuses to
  // guess - the same lesson as the text assertions, applied to the buttons.
  const thread = page.getByRole("list", { name: "Comment thread" });

  try {
    await writeComment(page, "khach muon quay truoc Tet");
    await page.getByRole("button", { name: "Comment", exact: true }).click();

    // Scoped to the thread, never to the page: the composer holds a copy of
    // this text until the post succeeds, so a page-wide match proves nothing.
    await expect(thread.getByText("khach muon quay truoc Tet")).toBeVisible();

    await expect.poll(() => threadCount(page, deal)).toBe(before + 1);
    const posted = (await callAs(page, THREAD, { deal })).body.message;
    const mine = posted.find((row) => row.content?.includes("khach muon quay truoc Tet"));
    expect(mine, "the posted comment is not in the thread").toBeTruthy();
    written.push(mine.name);

    // Not edited yet, which is the half that makes the badge below mean
    // something: `edited` compares two stamps taken from one clock read.
    expect(mine.edited).toBe(false);
    expect(mine.mine, "the author does not own their own comment").toBe(true);

    await thread.getByRole("button", { name: "Edit comment" }).first().click();
    const editor = page.getByRole("textbox", { name: "Edit comment" });
    await editor.click();
    await page.keyboard.press("ControlOrMeta+a");
    await editor.pressSequentially("quay sau Tet");
    await thread.getByRole("button", { name: "Save", exact: true }).click();

    await expect(thread.getByText("quay sau Tet")).toBeVisible();
    await expect(thread.getByText("khach muon quay truoc Tet")).toHaveCount(0);
    await expect(thread.getByText("edited", { exact: true })).toBeVisible();

    // Deleting asks first. A comment is speech, and speech that vanishes on a
    // stray click is worse than one click too many.
    await thread.getByRole("button", { name: "Delete comment" }).first().click();
    await thread.getByRole("button", { name: "Delete", exact: true }).click();
    await expect.poll(() => threadCount(page, deal)).toBe(before);
    written.length = 0;
  } finally {
    for (const name of written) {
      await callAs(page, "auraos.api.delete_deal_comment", { comment: name });
    }
  }

  expect(await threadCount(page, deal)).toBe(before);
  expect(failures).toEqual([]);
});

test("a mention leaves the markup the server reads", async ({ page }) => {
  const deal = await openDeal(page);

  // Who the picker can actually offer: the operating seats, less whoever is
  // signed in - naming yourself notifies nobody.
  //
  // **Measured, not assumed.** The first version skipped on
  // `seats.length < 2`, which takes it for granted that the session is one of
  // the seats. It is not: this suite signs in as Administrator, who holds
  // every role implicitly and therefore has no `Has Role` row, so
  // `operating_users` never returns them. One seeded producer meant one seat,
  // the guard read that as "nobody to name", and the test skipped every run
  // while the picker would have worked perfectly.
  const me = (await callAs(page, "frappe.auth.get_logged_user")).body.message;
  const seats = (await callAs(page, "auraos.api.operating_users")).body.message ?? [];
  const offerable = seats.filter((seat) => seat.name !== me);
  test.skip(offerable.length === 0, "this site has nobody the signed-in seat could name");

  const written = [];
  try {
    await writeComment(page, "@");
    // The picker opens on the caret, not on a keystroke count.
    const picker = page.getByRole("listbox", { name: "Mention someone" });
    await expect(picker).toBeVisible();
    await picker.getByRole("option").first().click();

    const before = await threadCount(page, deal);
    await page.getByRole("button", { name: "Comment", exact: true }).click();
    await expect.poll(() => threadCount(page, deal)).toBe(before + 1);

    const posted = (await callAs(page, THREAD, { deal })).body.message;
    const mentioning = posted.find((row) => (row.content ?? "").includes('class="mention"'));
    expect(mentioning, "no comment carries a mention span").toBeTruthy();
    written.push(mentioning.name);

    // The contract with auraos.lib.comments.mentioned_users, checked on the
    // *stored* content: sanitize_html keeps the span and its data attributes,
    // so a mention survives being saved rather than only being typed.
    expect(mentioning.content).toContain("data-id=");
    expect(mentioning.content).toContain('data-type="mention"');
  } finally {
    for (const name of written) {
      await callAs(page, "auraos.api.delete_deal_comment", { comment: name });
    }
  }
});

test("the file manager lists attachments with the deal each one is on", async ({ page }) => {
  const failures = [];
  page.on("pageerror", (error) => failures.push(error.message));

  await page.goto("/aura-next/documents/files");
  await expect(page.getByRole("heading", { name: "Files", exact: true })).toBeVisible();

  const answer = await callAs(page, "auraos.api.deal_files", {});
  expect(answer.status, `the files read was refused: ${JSON.stringify(answer.body)}`).toBe(200);
  const payload = answer.body.message;

  // The filter choices come from the unfiltered set, which is what stops
  // narrowing by deal from emptying the dropdown that got you there.
  expect(Array.isArray(payload.files)).toBe(true);
  expect(Array.isArray(payload.deals)).toBe(true);
  expect(Array.isArray(payload.file_types)).toBe(true);
  expect(Array.isArray(payload.uploaders)).toBe(true);

  // Every row names the deal it hangs on - the question a deal card cannot
  // answer, and the reason this screen exists.
  for (const row of payload.files) {
    expect(typeof row.deal).toBe("string");
    expect(row.deal.length).toBeGreaterThan(0);
  }

  await expect(page.getByLabel("Filter by deal")).toBeVisible();
  const text = String((await page.locator("main").textContent()) ?? "");
  expect(text).not.toMatch(/NaN|undefined|Infinity/);
  expect(failures).toEqual([]);
});
