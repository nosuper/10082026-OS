import { expect, test } from "@playwright/test"

const seededDeal = "Playwright Existing Deal"
const seededCompany = "Playwright Client"

// Regression test for the bug the founder reported: clicking any deal landed
// on the fixture TVC Tet 2027 "Vi Xuan" for Nhat Minh Beverage, whichever deal
// was clicked, because the route made no server calls and rendered hardcoded
// content. This is the spec that must fail if that ever comes back.
test("the deal you open is the deal you get", async ({ page }) => {
  await page.goto("/aura-next/deals")
  await page.getByRole("link", { name: seededDeal }).first().click()

  await expect(page).toHaveURL(/\/aura-next\/deals\/DEAL-/)
  await expect(page.getByText(seededDeal).first()).toBeVisible()
  await expect(page.getByText(seededCompany).first()).toBeVisible()
})

test("no deal page shows the fixture that used to be hardcoded here", async ({ page }) => {
  await page.goto("/aura-next/deals")
  await page.getByRole("link", { name: seededDeal }).first().click()
  await expect(page).toHaveURL(/\/aura-next\/deals\/DEAL-/)

  const body = await page.locator("body").innerText()
  expect(body).not.toContain("Vị Xuân")
  expect(body).not.toContain("Nhất Minh")
})

test("a deal code that does not exist is a calm state, not a crash", async ({ page }) => {
  const failures = []
  page.on("pageerror", (error) => failures.push(error.message))

  await page.goto("/aura-next/deals/DEAL-does-not-exist")
  await expect(page.locator("body")).toContainText(/no such deal|nothing on this site is filed/i)
  expect(failures).toEqual([])
})
