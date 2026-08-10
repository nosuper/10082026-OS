import { chromium } from "@playwright/test"
import { mkdir } from "node:fs/promises"
import path from "node:path"
import { fileURLToPath } from "node:url"

const here = path.dirname(fileURLToPath(import.meta.url))
const authDirectory = path.resolve(here, "../.playwright-auth")

async function logIn(baseURL, credentials, stateFile) {
  const browser = await chromium.launch()
  const context = await browser.newContext({ baseURL })
  const page = await context.newPage()

  try {
    await page.goto("/login?redirect-to=%2Faura%2Fdeals")
    await page.locator("#login_email").fill(credentials.user)
    await page.locator("#login_password").fill(credentials.password)
    await page.locator("button.btn-login").click()
    await page.waitForURL("**/aura/deals")
    await page.getByRole("heading", { name: "Deals", exact: true }).waitFor()
    await context.storageState({ path: stateFile })
  } finally {
    await context.close()
    await browser.close()
  }
}

export default async function globalSetup(config) {
  const baseURL = config.projects[0].use.baseURL
  await mkdir(authDirectory, { recursive: true })

  await logIn(
    baseURL,
    {
      user: process.env.E2E_ADMIN_USER || "Administrator",
      password: process.env.E2E_ADMIN_PASSWORD || "admin",
    },
    path.join(authDirectory, "administrator.json")
  )
  await logIn(
    baseURL,
    {
      user: process.env.E2E_PRODUCER_USER || "playwright-producer@example.test",
      password: process.env.E2E_PRODUCER_PASSWORD || "playwright-only",
    },
    path.join(authDirectory, "producer.json")
  )
}
