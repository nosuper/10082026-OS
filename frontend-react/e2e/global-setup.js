import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";

import { administratorState, authDirectory, producerState } from "./auth-state.js";

// Sign in through Frappe's own login page rather than posting to the API, so
// the session cookie and the CSRF token the app reads are the real ones. The
// React app is same-origin with Frappe precisely so this works unchanged.
async function logIn(baseURL, credentials, stateFile) {
  const browser = await chromium.launch();
  const context = await browser.newContext({ baseURL });
  const page = await context.newPage();

  try {
    await page.goto("/login?redirect-to=%2Faura-next%2Fdeals");
    await page.locator("#login_email").fill(credentials.user);
    await page.locator("#login_password").fill(credentials.password);
    await page.locator("button.btn-login").click();
    await page.waitForURL("**/aura-next/deals**");
    // Wait for the app itself, not just the URL: the shell is served before
    // the bundle has mounted, and a state captured too early is useless.
    await page.getByRole("heading", { name: "Deals", exact: true }).waitFor();
    await context.storageState({ path: stateFile });
  } finally {
    await context.close();
    await browser.close();
  }
}

function requiredEnvironment(name) {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required for the disposable E2E site`);
  return value;
}

export default async function globalSetup(config) {
  const baseURL = config.projects[0].use.baseURL;
  await mkdir(authDirectory, { recursive: true });

  await logIn(
    baseURL,
    {
      user: process.env.E2E_ADMIN_USER || "Administrator",
      password: process.env.E2E_ADMIN_PASSWORD || "admin",
    },
    administratorState,
  );
  await logIn(
    baseURL,
    {
      user: requiredEnvironment("E2E_PRODUCER_USER"),
      password: requiredEnvironment("E2E_PRODUCER_PASSWORD"),
    },
    producerState,
  );
}
