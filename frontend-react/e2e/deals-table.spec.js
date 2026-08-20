import { expect, test } from "@playwright/test"
import { readFile } from "node:fs/promises"

import { administratorState, producerState } from "./auth-state.js"
import { saving } from "./writes.js"

// The table's inline cells write through one endpoint - deals.index.tsx calls
// it on blur, not on a button - so every edit below is a request to wait for.
const UPDATE_ROW = "auraos.api.update_deal_table_row"

// The deals table: inline money editing, and the column and view choices
// that are a habit rather than data.
//
// **These are ports, not new specs.** They lived in the Vue suite
// (frontend/e2e/deals.spec.js) and #103 deletes it. The three behaviours they
// cover all still exist in the React app - per-user preferences at
// deals.index.tsx:165, inline money editing through MoneyInput - so deleting
// the Vue suite without these would have dropped the only e2e coverage of live
// code, silently: nothing fails, nothing warns, and in a month nobody
// remembers those behaviours were ever covered.
//
// Written while the Vue specs still existed to read the *intent* from. Doing
// this later would have meant reconstructing what the behaviour was for out of
// deals.index.tsx, which is the cold-read problem in reverse - inferring the
// spec from the implementation is how a spec ends up testing the wrong thing.
//
// The assertions are ported; the selectors are not. The React screen has its
// own DOM - a `details` disclosure rather than a popover, column labels "Deal"
// and "Budget" where Vue said "Title" and "Budget (VND)" - so translating
// selector for selector would have produced a spec that tests nothing.

const existingDeal = "Playwright Existing Deal"
// The cell renders the symbol; the editor does not. Keeping both forms named
// here means the next display change breaks in one place rather than four.
const seededBudget = "10.000.000"
const typedBudget = "12.500.000"
const seededCell = `${seededBudget}₫`
const typedCell = `${typedBudget}₫`

async function openDeals(page) {
  await page.goto("/aura-next/deals")
  await expect(page.getByRole("heading", { name: "Deals", exact: true })).toBeVisible()
}

async function openTable(page) {
  await page.getByRole("button", { name: "Table", exact: true }).click()
  await expect(page.getByRole("button", { name: "Table", exact: true })).toHaveAttribute(
    "aria-pressed",
    "true",
  )
}

function openColumns(page) {
  return page.getByText("Columns", { exact: true }).click()
}

function dealRow(page) {
  return page.getByRole("row").filter({ hasText: existingDeal })
}

/** The Budget cell, found by its column position rather than assumed: the
 *  column set is a user preference, so a fixed index is a spec that breaks
 *  the first time somebody reorders or hides one. */
async function budgetCell(page) {
  const headers = page.locator("thead th")
  const labels = await headers.allInnerTexts()
  const index = labels.findIndex((text) => text.trim() === "Budget")
  expect(index, "Budget column is visible").toBeGreaterThanOrEqual(0)
  return dealRow(page).locator("td").nth(index)
}

test("inline money edits format as typed, persist, and swallow non-digits", async ({ page }) => {
  await openDeals(page)
  await openTable(page)

  let cell = await budgetCell(page)
  await cell.click()
  const editor = cell.locator("input")

  // The field reads the way money is written. Raw digits sitting beside
  // formatted cells is what the A1 walkthrough failed on.
  await editor.fill("12500000")
  await expect(editor).toHaveValue(typedBudget)
  // Awaited rather than polled for. The blur fires the write and returns; the
  // cell then re-renders from the response. Run 20 read 10.000.000 back here -
  // the seeded figure - because the assertion asked before the write landed
  // and the reload two lines down cancelled it.
  await saving(page, UPDATE_ROW, () => editor.blur())
  await expect(cell).toHaveText(typedCell)

  await page.reload()
  await openTable(page)
  cell = await budgetCell(page)
  await expect(cell).toHaveText(typedCell)

  // Anything that is not a digit never lands in the field, and Escape walks
  // away without saving.
  await cell.click()
  await cell.locator("input").fill("-abc")
  await expect(cell.locator("input")).toHaveValue("")
  // No saving() here on purpose: Escape abandons the edit without writing, and
  // that is what the next reload proves. Waiting for a request nobody sends
  // would hang until timeout and look like a slow box.
  await cell.locator("input").press("Escape")

  await page.reload()
  await openTable(page)
  await expect(await budgetCell(page)).toHaveText(typedCell)

  // Put the seeded figure back. The Vue original did not, and because
  // ensure_deal() only created the deal rather than restoring it, every site
  // that had run these specs once carried a budget nobody seeded. The seed
  // states the value now, but a spec that cleans up after itself does not
  // depend on the next reseed happening.
  cell = await budgetCell(page)
  await cell.click()
  await cell.locator("input").fill("10000000")
  // The last statement in the test, so nothing after it would force the wait:
  // an unawaited restore here dies with the context and leaves the shared deal
  // carrying 12.500.000 for whoever runs next.
  await saving(page, UPDATE_ROW, () => cell.locator("input").blur())
  await expect(cell).toHaveText(seededCell)
})

test("table view and optional columns persist while required columns stay fixed", async ({
  page,
}) => {
  await openDeals(page)
  await openTable(page)
  await openColumns(page)

  // Deal and Client are what a row is; they cannot be turned off.
  await expect(page.getByRole("checkbox", { name: "Deal", exact: true })).toBeDisabled()
  await expect(page.getByRole("checkbox", { name: "Client", exact: true })).toBeDisabled()

  await page.getByRole("checkbox", { name: "Budget", exact: true }).uncheck()
  await expect(page.locator("thead th").filter({ hasText: "Budget" })).toHaveCount(0)

  // The view is a habit too: reloading comes back to the table, not the
  // kanban default, because this user chose the table.
  await page.reload()
  await expect(page.getByRole("button", { name: "Table", exact: true })).toHaveAttribute(
    "aria-pressed",
    "true",
  )
  await expect(page.locator("thead th").filter({ hasText: "Budget" })).toHaveCount(0)
  await openColumns(page)
  await expect(page.getByRole("checkbox", { name: "Budget", exact: true })).not.toBeChecked()

  // Restore, so the next spec sees the column set the app ships with.
  await page.getByRole("checkbox", { name: "Budget", exact: true }).check()
  await expect(page.locator("thead th").filter({ hasText: "Budget" })).toHaveCount(1)
})

test("two users keep distinct view and column preferences in one browser context", async ({
  browser,
}) => {
  const administrator = JSON.parse(await readFile(administratorState, "utf8"))
  const producer = JSON.parse(await readFile(producerState, "utf8"))
  const context = await browser.newContext()
  const page = await context.newPage()

  // Preferences are keyed by the signed-in account (deals.index.tsx
  // prefsKey), so two people sharing a machine must not inherit each other's
  // table. One browser context, two sessions - the same shape as the bug.
  async function become(state) {
    await context.clearCookies()
    await context.addCookies(state.cookies)
    await openDeals(page)
  }

  try {
    await become(administrator)
    await openTable(page)
    await openColumns(page)
    await page.getByRole("checkbox", { name: "Budget", exact: true }).uncheck()
    await expect(page.locator("thead th").filter({ hasText: "Budget" })).toHaveCount(0)

    await become(producer)
    // The producer has chosen nothing, so they get the shipped default -
    // kanban - rather than the administrator's table.
    await expect(page.getByRole("button", { name: "Kanban", exact: true })).toHaveAttribute(
      "aria-pressed",
      "true",
    )
    await openTable(page)
    await openColumns(page)
    await page.getByRole("checkbox", { name: "Source", exact: true }).uncheck()
    await expect(page.locator("thead th").filter({ hasText: "Source" })).toHaveCount(0)

    await become(administrator)
    await openTable(page)
    // The administrator's hidden column is still hidden, and the producer's
    // is not hidden for them.
    await expect(page.locator("thead th").filter({ hasText: "Budget" })).toHaveCount(0)
    await openColumns(page)
    await expect(page.getByRole("checkbox", { name: "Source", exact: true })).toBeChecked()

    // Put the administrator back to the shipped column set - this context is
    // throwaway, but the localStorage it wrote belongs to the site.
    await page.getByRole("checkbox", { name: "Budget", exact: true }).check()

    await become(producer)
    await openTable(page)
    await openColumns(page)
    await expect(page.getByRole("checkbox", { name: "Budget", exact: true })).toBeChecked()
    await expect(page.getByRole("checkbox", { name: "Source", exact: true })).not.toBeChecked()
    await page.getByRole("checkbox", { name: "Source", exact: true }).check()
  } finally {
    await context.close()
  }
})
