import { expect, test } from "@playwright/test"

// The app boots inside Frappe with a real session. Everything else in this
// suite assumes this works, so it is asserted once here rather than implied.
test("boots at /aura-next with the signed-in user, not a hardcoded one", async ({ page }) => {
  const failures = []
  page.on("pageerror", (error) => failures.push(`page error: ${error.message}`))

  await page.goto("/aura-next/")
  await expect(page.getByRole("heading", { name: /Good (morning|afternoon|evening)/ })).toBeVisible()

  // The Lovable mockup shipped a hardcoded user. The shell must show the real
  // session instead, and the founder flag must come from the server.
  await expect(page.getByText("Trần Quốc Bảo")).toHaveCount(0)
  await expect(page.getByText("Administrator").first()).toBeVisible()

  expect(failures).toEqual([])
})

test("a guest is sent to the login page rather than shown the app", async ({ browser }) => {
  const context = await browser.newContext({ storageState: { cookies: [], origins: [] } })
  try {
    const page = await context.newPage()
    await page.goto("/aura-next/deals")
    await expect(page).toHaveURL(/\/login/)
  } finally {
    await context.close()
  }
})

test("money reads as digits, never as words", async ({ page }) => {
  await page.goto("/aura-next/")
  const body = await page.locator("body").innerText()

  // vndShort spelled "1,9 tỷ" and "850 triệu". The founder rejected reading
  // money as words; the design uses full digits everywhere.
  expect(body).not.toMatch(/\d[\d.,]*\s*(tỷ|triệu)/)
})
