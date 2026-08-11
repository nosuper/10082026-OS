import path from "node:path"
import { fileURLToPath } from "node:url"

// Where the signed-in state for the two E2E users is written.
//
// The suite runs inside the official Playwright image as root, with the repo
// bind-mounted into it, so anything written under the repo lands on the host
// owned by root — and the host user cannot unlink it again. The state only has
// to outlive the single container run that creates and consumes it, so
// E2E_AUTH_DIR points it outside the mount. A run on the host with no such
// container keeps it beside the tests, where .gitignore already covers it.
const here = path.dirname(fileURLToPath(import.meta.url))

export const authDirectory =
  process.env.E2E_AUTH_DIR || path.resolve(here, "../.playwright-auth")

export const administratorState = path.join(authDirectory, "administrator.json")
export const producerState = path.join(authDirectory, "producer.json")
