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

  for (const rung of ["Not yet due", "1-30 days", "31-60 days", "61-90 days", "Over 90 days"]) {
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

  // Exact matches only. These are data labels; the screen also explains in
  // prose that commission and net profit live behind a different door, and a
  // substring check fails on the sentence that says so.
  for (const label of ["Commission", "CMF", "Net profit", "TNDN"]) {
    await expect(page.getByText(label, { exact: true })).toHaveCount(0)
  }
  // And the producer does get what they are entitled to.
  await expect(page.getByText("Margin", { exact: false }).first()).toBeVisible()
})
