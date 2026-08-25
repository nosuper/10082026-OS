import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { FIXTURE_NAMES } from "./fixture.js";

// The guard on fixture.js. Needs no browser and no server, so it costs a run
// nothing, and it is the difference between a rename breaking in one place
// and drifting silently until four screen assertions fail for reasons that
// look like screen defects.
//
// The whole repo is mounted at /workspace/repo (docker/compose.e2e.yaml), so
// the seed is readable from here in the container and on the host alike.
const here = path.dirname(fileURLToPath(import.meta.url));
const SEED = path.resolve(here, "../../scripts/e2e-seed.py");

test("the names this suite asserts on are the names the seed writes", async () => {
  const seed = await readFile(SEED, "utf8");

  for (const [constant, value] of Object.entries(FIXTURE_NAMES)) {
    expect(
      seed,
      `e2e/fixture.js exports ${constant} = ${JSON.stringify(value)}, which no ` +
        `longer appears in scripts/e2e-seed.py. The seed is the source of ` +
        `truth: update fixture.js to match it, not the other way round.`,
    ).toContain(JSON.stringify(value));
  }
});
