// T3.4 (issue #28): the half of collaboration no seam test can see.
//
// The API tests prove who may edit what and which mention notifies
// whom. What they cannot prove is that a rich-text editor is actually
// wired into the card - that typing @ offers the other seat, that the
// comment posts, edits and deletes from the browser, and that the file
// manager is reachable from the nav and lists what is hanging on a deal.
import { expect, test } from "@playwright/test"

const existingDeal = "Playwright Existing Deal"
const producerName = "Playwright Producer"
const seededFile = "playwright-brief.txt"
const renamedFile = "brief khách gửi.txt"

async function openCard(page) {
  await page.goto("/aura/deals")
  await page.getByRole("button", { name: "Table", exact: true }).click()
  await page.getByRole("button", { name: existingDeal, exact: true }).click()
  const dialog = page.getByRole("dialog")
  await expect(dialog).toContainText("Edit Deal")
  // The editor is a lazily loaded chunk - wait for it, not for the dialog.
  const thread = dialog.locator(".comment-thread")
  await expect(thread.locator('[contenteditable="true"]')).toBeVisible()
  return thread
}

async function writeInto(thread, text) {
  const editor = thread.locator('[contenteditable="true"]').first()
  await editor.click()
  await editor.pressSequentially(text)
  return editor
}

test("a comment posts, edits and deletes from the deal card", async ({ page }) => {
  const thread = await openCard(page)

  await writeInto(thread, "khách muốn quay trước Tết")
  await thread.getByRole("button", { name: "Comment", exact: true }).click()
  await expect(thread.getByText("khách muốn quay trước Tết")).toBeVisible()
  await expect(thread.getByText("edited", { exact: true })).toHaveCount(0)

  await thread.getByRole("button", { name: "Edit", exact: true }).click()
  const editor = thread.locator('[contenteditable="true"]').first()
  await editor.click()
  await page.keyboard.press("ControlOrMeta+a")
  await editor.pressSequentially("quay sau Tết")
  await thread.getByRole("button", { name: "Save", exact: true }).click()

  await expect(thread.getByText("quay sau Tết")).toBeVisible()
  await expect(thread.getByText("khách muốn quay trước Tết")).toHaveCount(0)
  await expect(thread.getByText("edited", { exact: true })).toBeVisible()

  // Two taps: a modal confirm inside a modal dialog is worse than a mis-tap.
  await thread.getByRole("button", { name: "Delete", exact: true }).click()
  await thread.getByRole("button", { name: "Delete for good" }).click()
  await expect(thread.getByText("quay sau Tết")).toHaveCount(0)
})

test("typing @ offers the other seat and names them in the thread", async ({
  page,
}) => {
  const thread = await openCard(page)

  await writeInto(thread, "@Play")
  const suggestion = thread.locator(".mention-suggestions")
  await expect(suggestion).toContainText(producerName)
  await suggestion.getByRole("button", { name: producerName }).click()

  await thread.getByRole("button", { name: "Comment", exact: true }).click()
  await expect(thread.getByText(`@${producerName}`)).toBeVisible()

  await thread.getByRole("button", { name: "Delete", exact: true }).click()
  await thread.getByRole("button", { name: "Delete for good" }).click()
  await expect(thread.getByText(`@${producerName}`)).toHaveCount(0)
})

test("the file manager is reachable from the nav and manages a deal's files", async ({
  page,
}) => {
  await page.goto("/aura/deals")
  await page.getByRole("link", { name: "Files", exact: true }).click()
  await expect(page).toHaveURL(/\/aura\/files$/)
  await expect(page.getByRole("heading", { name: "Files", exact: true })).toBeVisible()

  // Located by its deal, not its file name: renaming swaps the name for
  // an input, and a row filtered on the old name stops matching mid-test.
  const row = page.getByRole("row").filter({ hasText: existingDeal })
  await expect(row).toContainText(seededFile)
  // Uploaded private, so no "public" badge to warn about a shared link.
  await expect(row.getByText("public", { exact: true })).toHaveCount(0)

  await row.getByRole("button", { name: "Rename" }).click()
  await row.locator("input").fill(renamedFile)
  await row.getByRole("button", { name: "Save", exact: true }).click()

  await expect(page.getByRole("link", { name: renamedFile })).toBeVisible()
  await page.reload()
  await expect(page.getByRole("link", { name: renamedFile })).toBeVisible()
})
