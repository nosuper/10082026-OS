import { expect, test } from "@playwright/test"

// A2: the breakdown editor — money that reads as money, a table that
// fits a laptop, and a save that never scrolls away.

const dealTitle = "Playwright Existing Deal"

async function openBreakdown(page) {
  await page.goto("/aura/deals")
  await expect(
    page.getByRole("heading", { name: "Deals", exact: true })
  ).toBeVisible()
  // Card roots carry the `group` class; scoping the button to the card
  // keeps this correct when other specs have created more deals.
  const card = page.locator("div.group", { hasText: dealTitle }).last()
  await card.hover()
  await card.getByTitle("Breakdown & Quote").click()
  await expect(page).toHaveURL(/\/breakdown$/)
  await expect(page.getByText("Cost lines", { exact: true })).toBeVisible()
}

// Text-anchored, not role-anchored: Chromium's layout-table heuristics
// can demote a one-row table to a layout table and strip columnheader
// roles — exactly what the seeded single-line table hits on CI.
function columnHeader(page, name) {
  return page.locator("thead").first().getByText(name, { exact: true })
}

function directorRow(page) {
  // The seed guarantees exactly one cost line; the cost-lines table is
  // the first table on the page (packages sit below it). CSS, not
  // getByRole("table") — same layout-table heuristic risk.
  return page.locator("table").first().locator("tbody tr").first()
}

test("unit price formats as typed, flags the page dirty, and Ctrl+S saves", async ({ page }) => {
  await openBreakdown(page)
  const row = directorRow(page)
  await expect(row.locator("input").first()).toHaveValue("Playwright director")

  // The seeded price arrives already formatted — never raw digits.
  const price = row.locator('input[inputmode="numeric"]')
  await expect(price).toHaveValue("4.000.000")

  await price.fill("5500000")
  await expect(price).toHaveValue("5.500.000")
  await expect(page.getByText("Unsaved changes", { exact: false })).toBeVisible()

  await page.keyboard.press("Control+s")
  // "Saving…" replaces the dirty note the instant the request STARTS,
  // so the dirty note vanishing proves nothing. Only "All changes
  // saved" means the save landed - reloading any earlier kills the
  // in-flight request and reads back the seeded price (CI flake,
  // 2026-08-13).
  await expect(
    page.getByText("All changes saved", { exact: true })
  ).toBeVisible()

  await page.reload()
  await expect(
    directorRow(page).locator('input[inputmode="numeric"]')
  ).toHaveValue("5.500.000")

  // Put the seeded figure back — and let AUTOSAVE do it: no Ctrl+S,
  // the page saves itself a moment after the last edit.
  await directorRow(page).locator('input[inputmode="numeric"]').fill("4000000")
  // Same race as Ctrl+S above: wait for the save to land, not merely
  // for the dirty note to give way to "Saving…".
  await expect(
    page.getByText("All changes saved", { exact: true })
  ).toBeVisible({ timeout: 15_000 })
  await page.reload()
  await expect(
    directorRow(page).locator('input[inputmode="numeric"]')
  ).toHaveValue("4.000.000")
})

test("detail columns are hidden by default and the choice sticks per user", async ({ page }) => {
  await openBreakdown(page)

  // Metadata stays off screen until asked for — the table must fit a
  // laptop without sideways scrolling.
  await expect(columnHeader(page, "Item Category")).toHaveCount(0)
  await expect(columnHeader(page, "Unit Price")).toBeVisible()

  await page.getByText("Detail columns", { exact: true }).click()
  await page.getByRole("checkbox", { name: "Item Category" }).check()
  await expect(columnHeader(page, "Item Category")).toBeVisible()

  await page.reload()
  await expect(columnHeader(page, "Item Category")).toBeVisible()

  // Back to default so the other spec's geometry assumptions hold.
  await page.getByText("Detail columns", { exact: true }).click()
  await page.getByRole("checkbox", { name: "Item Category" }).uncheck()
  await expect(columnHeader(page, "Item Category")).toHaveCount(0)
})
