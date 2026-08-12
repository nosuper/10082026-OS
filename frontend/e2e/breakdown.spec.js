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

function directorRow(page) {
  // getByDisplayValue reads the live input property — Vue never writes
  // the value *attribute*, so a CSS [value=…] selector finds nothing.
  return page
    .getByRole("row")
    .filter({ has: page.getByDisplayValue("Playwright director") })
}

test("unit price formats as typed, flags the page dirty, and Ctrl+S saves", async ({ page }) => {
  await openBreakdown(page)
  const row = directorRow(page)

  // The seeded price arrives already formatted — never raw digits.
  const price = row.locator('input[inputmode="numeric"]')
  await expect(price).toHaveValue("4.000.000")

  await price.fill("5500000")
  await expect(price).toHaveValue("5.500.000")
  await expect(page.getByText("Unsaved changes", { exact: false })).toBeVisible()

  await page.keyboard.press("Control+s")
  await expect(page.getByText("Unsaved changes", { exact: false })).toHaveCount(0)

  await page.reload()
  await expect(
    directorRow(page).locator('input[inputmode="numeric"]')
  ).toHaveValue("5.500.000")

  // Put the seeded figure back so specs stay order-independent.
  await directorRow(page).locator('input[inputmode="numeric"]').fill("4000000")
  await page.keyboard.press("Control+s")
  await expect(page.getByText("Unsaved changes", { exact: false })).toHaveCount(0)
})

test("detail columns are hidden by default and the choice sticks per user", async ({ page }) => {
  await openBreakdown(page)

  // Metadata stays off screen until asked for — the table must fit a
  // laptop without sideways scrolling.
  await expect(
    page.getByRole("columnheader", { name: "Item Category" })
  ).toHaveCount(0)
  await expect(
    page.getByRole("columnheader", { name: "Unit Price" })
  ).toBeVisible()

  await page.getByText("Detail columns", { exact: true }).click()
  await page.getByRole("checkbox", { name: "Item Category" }).check()
  await expect(
    page.getByRole("columnheader", { name: "Item Category" })
  ).toBeVisible()

  await page.reload()
  await expect(
    page.getByRole("columnheader", { name: "Item Category" })
  ).toBeVisible()

  // Back to default so the other spec's geometry assumptions hold.
  await page.getByText("Detail columns", { exact: true }).click()
  await page.getByRole("checkbox", { name: "Item Category" }).uncheck()
  await expect(
    page.getByRole("columnheader", { name: "Item Category" })
  ).toHaveCount(0)
})
