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
    // A considered budget rather than Playwright's default 30s, which was
    // never anyone's decision - it was what you get for not passing one.
    //
    // This wait spans a login POST, a redirect, and the SPA's first paint on a
    // site that has existed for about a minute. e2e.sh warms both pages before
    // handing over, so on a warm stack this returns in well under a second and
    // the ceiling costs nothing. It exists for the case where the warm-up did
    // not cover something: run 27 spent 30s here and reported zero of 65 tests,
    // which is the most expensive way this can fail - the whole boot wasted and
    // no evidence about anything.
    //
    // Two minutes because the failure it guards against is a cold render, and a
    // cold render on a busy box is minutes rather than seconds. A hang that is
    // genuinely a hang still ends; it just ends having told us it was not this.
    const SIGN_IN_BUDGET_MS = 120_000;
    await page.waitForURL("**/aura-next/deals**", { timeout: SIGN_IN_BUDGET_MS });
    // Wait for the app itself, not just the URL: the shell is served before
    // the bundle has mounted, and a state captured too early is useless.
    await page
      .getByRole("heading", { name: "Deals", exact: true })
      .waitFor({ timeout: SIGN_IN_BUDGET_MS });
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
