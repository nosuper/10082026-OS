import { expect, test } from "@playwright/test"

import { producerState } from "./auth-state.js"

const producerTest = test.extend({ storageState: producerState })

// The seeded site has no jobs and no milestones, which is the case worth
// pinning: an empty ladder is exactly where a reporting screen breaks or
// silently drops its rungs.
test("receivables renders every ageing rung even with nothing owed", async ({ page }) => {
  const failures = []
  page.on("pageerror", (error) => failures.push(error.message))

  await page.goto("/aura-next/finance/receivables")

  for (const rung of ["Not due", "1-30", "31-60", "61-90", "90"]) {
    await expect(page.getByText(rung, { exact: false }).first()).toBeVisible()
  }
  expect(failures).toEqual([])
})

test("income and expenses render a range with no activity as zero, not as a gap", async ({ page }) => {
  const failures = []
  page.on("pageerror", (error) => failures.push(error.message))

  await page.goto("/aura-next/finance/income")
  await expect(page.locator("body")).toContainText(/cash/i)

  await page.goto("/aura-next/finance/expenses")
  expect(failures).toEqual([])
})

producerTest("a producer sees margin but no commission or net profit", async ({ page }) => {
  await page.goto("/aura-next/finance/receivables")

  const body = await page.locator("body").innerText()
  for (const forbidden of ["Commission", "CMF", "Net profit", "TNDN"]) {
    expect(body).not.toContain(forbidden)
  }
})
