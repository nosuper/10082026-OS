import { expect, test } from "@playwright/test"
import { readFile } from "node:fs/promises"

import { administratorState, producerState } from "./auth-state.js"

const existingDeal = "Playwright Existing Deal"
const company = "Playwright Client"
const producerName = "Playwright Producer"
const persistedBudget = "12.500.000"
const producerTest = test.extend({
  storageState: producerState,
})

async function openDeals(page) {
  await page.goto("/aura/deals")
  await expect(page).toHaveURL(/\/aura\/deals$/)
  await expect(page.getByRole("heading", { name: "Deals", exact: true })).toBeVisible()
}

async function openTable(page) {
  await page.getByRole("button", { name: "Table", exact: true }).click()
  await expect(columnHeader(page, "Title")).toBeVisible()
}

function columnHeader(page, name) {
  return page.locator("thead").getByText(name, { exact: true })
}

async function dealRow(page, title = existingDeal) {
  return page.getByRole("row").filter({ has: page.getByRole("button", { name: title }) })
}

async function openColumns(page) {
  await page.getByText("Columns", { exact: true }).click()
}

test("logs in and renders the deals SPA without critical browser failures", async ({ page }) => {
  const failures = []
  page.on("pageerror", (error) => failures.push(`page error: ${error.message}`))
  page.on("requestfailed", (request) => {
    const url = new URL(request.url())
    if (url.origin === new URL(page.url()).origin) {
      failures.push(`request failed: ${url.pathname}`)
    }
  })
  page.on("response", (response) => {
    const url = new URL(response.url())
    if (
      url.origin === new URL(page.url()).origin &&
      (response.request().resourceType() === "document" || url.pathname.startsWith("/api/")) &&
      response.status() >= 500
    ) {
      failures.push(`critical response: ${response.status()} ${url.pathname}`)
    }
  })

  await openDeals(page)
  await expect(page.getByText(existingDeal, { exact: true })).toBeVisible()
  expect(failures).toEqual([])
})

test("table view and optional columns persist while required columns stay fixed", async ({ page }) => {
  await openDeals(page)
  await openTable(page)
  await openColumns(page)

  const title = page.getByRole("checkbox", { name: "Title" })
  const companyColumn = page.getByRole("checkbox", { name: "Company" })
  const budget = page.getByRole("checkbox", { name: "Budget (VND)" })
  await expect(title).toBeDisabled()
  await expect(companyColumn).toBeDisabled()
  await budget.uncheck()

  await page.reload()
  await expect(columnHeader(page, "Title")).toBeVisible()
  await expect(columnHeader(page, "Budget (VND)")).toHaveCount(0)
  await openColumns(page)
  await expect(page.getByRole("checkbox", { name: "Budget (VND)" })).not.toBeChecked()
})

producerTest("blank table row creates a deal with normal defaults and no card dialog", async ({ page }) => {
  const title = "Playwright Created Deal"
  await openDeals(page)
  await openTable(page)

  const blankRow = page.locator("tbody tr").first()
  await blankRow.getByPlaceholder("Title").fill(title)
  await blankRow.locator("select").first().selectOption({ label: company })
  await blankRow.getByRole("button", { name: "Add" }).click()

  await expect(page.getByRole("button", { name: title })).toBeVisible()
  await expect(page.getByRole("dialog")).toHaveCount(0)
  await page.reload()
  const created = await dealRow(page, title)
  await expect(created).toContainText(company)
  await expect(created).toContainText("Brief Received")
  await expect(created).toContainText(producerName)
})

test("inline money edits format as typed, persist, and swallow non-digits", async ({ page }) => {
  await openDeals(page)
  await openTable(page)
  let row = await dealRow(page)

  const budgetCell = row.locator("td").nth(4)
  await budgetCell.click()
  const editor = budgetCell.locator("input")
  await editor.fill("12500000")
  // The field itself reads the way money is written - the A1
  // walkthrough failed on raw digits sitting beside formatted cells.
  await expect(editor).toHaveValue(persistedBudget)
  await editor.blur()
  await expect(budgetCell).toHaveText(persistedBudget)

  await page.reload()
  row = await dealRow(page)
  await expect(row.locator("td").nth(4)).toHaveText(persistedBudget)
  await row.locator("td").nth(4).click()
  // Anything that isn't digits never even lands in the field, and Esc
  // walks away without saving.
  await row.locator("input").fill("-abc")
  await expect(row.locator("input")).toHaveValue("")
  await row.locator("input").press("Escape")

  await page.reload()
  row = await dealRow(page)
  await expect(row.locator("td").nth(4)).toHaveText(persistedBudget)
})

test("deal titles open the card while editable cells stay inline", async ({ page }) => {
  await openDeals(page)
  await openTable(page)
  const row = await dealRow(page)

  await row.getByRole("button", { name: existingDeal, exact: true }).click()
  await expect(page.getByRole("dialog")).toContainText("Edit Deal")
  await page.getByRole("button", { name: "Cancel" }).click()

  await row.locator("td").nth(4).click()
  await expect(row.locator("input")).toBeVisible()
  await expect(page.getByRole("dialog")).toHaveCount(0)
})

test("two users keep distinct view and column preferences in one browser context", async ({ browser }) => {
  const administrator = JSON.parse(await readFile(administratorState, "utf8"))
  const producer = JSON.parse(await readFile(producerState, "utf8"))
  const context = await browser.newContext()
  const page = await context.newPage()

  async function become(state) {
    await context.clearCookies()
    await context.addCookies(state.cookies)
    await openDeals(page)
  }

  try {
    await become(administrator)
    await openTable(page)
    await openColumns(page)
    await page.getByRole("checkbox", { name: "Budget (VND)" }).uncheck()

    await become(producer)
    await expect(page.getByRole("button", { name: "Board", exact: true })).toHaveClass(/bg-white/)
    await openTable(page)
    await openColumns(page)
    await page.getByRole("checkbox", { name: "Source" }).uncheck()
    await page.getByRole("button", { name: "Board", exact: true }).click()
    // Wait for the click to land (and its preference to persist) before
    // swapping users - switching mid-flight flaked this spec twice.
    await expect(
      page.getByRole("button", { name: "Board", exact: true })
    ).toHaveClass(/bg-white/)

    await become(administrator)
    await expect(columnHeader(page, "Budget (VND)")).toHaveCount(0)
    await openColumns(page)
    await expect(page.getByRole("checkbox", { name: "Source" })).toBeChecked()

    await become(producer)
    await expect(page.getByRole("button", { name: "Board", exact: true })).toHaveClass(/bg-white/)
    await openTable(page)
    await openColumns(page)
    await expect(page.getByRole("checkbox", { name: "Budget (VND)" })).toBeChecked()
    await expect(page.getByRole("checkbox", { name: "Source" })).not.toBeChecked()
  } finally {
    await context.close()
  }
})
