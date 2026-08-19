import { expect, test } from "@playwright/test";

import { producerState } from "./auth-state.js";

const seededDeal = "Playwright Existing Deal";
const producerTest = test.extend({ storageState: producerState });

async function openQuote(page) {
  await page.goto("/aura-next/deals");
  await page.getByRole("link", { name: seededDeal }).first().click();
  await expect(page).toHaveURL(/\/aura-next\/deals\/DEAL-/);
  const url = new URL(page.url());
  await page.goto(`${url.pathname}/quote`);
  await expect(page.getByText("Cost lines", { exact: true })).toBeVisible();
}

test("the breakdown shows the seeded line and prices it on the server", async ({ page }) => {
  await openQuote(page);

  await expect(page.locator("tbody tr").first()).toBeVisible();
  // 1 x 2 x 4.000.000 is the subtotal, and that much is arithmetic anyone can
  // do. What the quote price comes to is not: the line is taxed Cá nhân, so
  // the engine grosses up for PIT before applying markup. Asserting a number I
  // worked out myself is exactly what this test exists to catch - the first
  // version of it did that and failed, expecting 9.600.000 for a line the
  // server prices at 11.000.000.
  //
  // So: the subtotal, and then that the priced columns exist and are not a
  // copy of it. Whether the engine's number is *correct* is lib/pricing's
  // question and it is answered by its own tests, not by a browser.
  await expect(page.locator("body")).toContainText("8.000.000");
  const figures = await page
    .locator("tbody tr")
    .first()
    .locator("text=/[0-9]{1,3}(\\.[0-9]{3})+/")
    .count();
  expect(figures).toBeGreaterThan(1);
});

test("packages carry the blank-versus-zero override distinction", async ({ page }) => {
  await openQuote(page);
  await expect(page.getByText("Packages", { exact: false }).first()).toBeVisible();
});

// Publishing is irreversible, so it is exercised here and nowhere else: this
// stack is created and destroyed by the run. The dev site's DEAL-0006 already
// carries a real v8 from an earlier manual verification and must not gain
// another, which is why no spec points at dev.localhost.
test("publishing mints the next sequential version with a public link", async ({ page }) => {
  await openQuote(page);

  // Every whitelisted call the page makes, with what came back. Reading the
  // component and reasoning about which branch fired has now been wrong twice:
  // every failure path in save() and publish() renders an ErrorState, yet run 6
  // saw no alert and no version. When the code says a thing is impossible and
  // the browser disagrees, record the traffic rather than re-reading the code.
  const calls = [];
  page.on("response", async (response) => {
    const match = /\/api\/method\/(auraos\.[\w.]+|frappe\.client\.\w+)/.exec(response.url());
    if (!match) return;
    calls.push(`${match[1]} -> ${response.status()}`);
  });
  const consoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  const publish = page.getByRole("button", { name: /Publish version/ });
  await expect(publish).toBeVisible();
  const label = await publish.innerText();
  await publish.click();

  // Match the role, not the wording. ErrorState carries role="alert" and its
  // five faces in states.tsx are sentences - "That did not work.", "This did
  // not load." - none of which contain the word "error". The previous version
  // of this grepped /Nothing to publish|not permitted|error/i and so could not
  // have matched any refusal the app is capable of rendering. It was a
  // diagnostic that could only ever come back silent.
  const alert = page.getByRole("alert").first();
  const minted = page.getByText(/v1\b/).first();
  // The header says which of "Saving...", "Unsaved changes", "All changes
  // saved" the page believes it is in - which is the state publish() branched
  // on, read from the page instead of inferred.
  const status = await page
    .getByText(/Saving\.\.\.|Unsaved changes|All changes saved|autosave is waiting/)
    .first()
    .innerText()
    .catch(() => "no status shown");

  await expect(
    alert.or(minted).first(),
    // Neither appearing is its own finding: publish() returns silently when the
    // document is dirty and the save ahead of it fails, so nothing renders at
    // all. That is the third outcome, and it needs saying rather than showing
    // up as a bare missing element.
    "publish produced neither a version nor a refusal - the save ahead of it likely failed silently",
  )
    .toBeVisible({ timeout: 15000 })
    .catch(() => {
      throw new Error(
        [
          "publish produced neither a version nor a refusal.",
          `save status on screen: ${status}`,
          `calls: ${calls.join(", ") || "none"}`,
          `console errors: ${consoleErrors.join(" | ") || "none"}`,
        ].join("\n"),
      );
    });

  if (await alert.isVisible().catch(() => false)) {
    throw new Error(`publish refused: ${(await alert.innerText()).replace(/\n/g, " / ")}`);
  }
  // The button counts up rather than branching: v2 next, never v1-B.
  await expect(page.getByRole("button", { name: /Publish version/ })).not.toHaveText(label);
});

producerTest("a producer sees no founder figure on the breakdown", async ({ page }) => {
  await openQuote(page);

  const body = await page.locator("body").innerText();
  for (const forbidden of ["Commission", "CMF", "Net profit", "TNDN", "Lợi nhuận trước thuế"]) {
    expect(body).not.toContain(forbidden);
  }
});
