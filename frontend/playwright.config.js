import { defineConfig, devices } from "@playwright/test"

import { administratorState } from "./e2e/auth-state.js"

const baseURL = process.env.E2E_BASE_URL || "http://127.0.0.1:18000"

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI
    ? [["line"], ["html", { open: "never" }]]
    : [["list"], ["html", { open: "never" }]],
  outputDir: "test-results",
  globalSetup: "./e2e/global-setup.js",
  use: {
    baseURL,
    storageState: administratorState,
    // Keep action timelines and screenshots without recording authenticated
    // request headers in network/DOM snapshots uploaded by CI.
    trace: { mode: "retain-on-failure", snapshots: false },
    screenshot: "only-on-failure",
    video: "off",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
})
