// Copy the built SPA shell into auraos/www so Frappe serves it at /aura.
import { copyFileSync, mkdirSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const here = dirname(fileURLToPath(import.meta.url))
const built = join(here, "..", "auraos", "public", "aura", "index.html")
const target = join(here, "..", "auraos", "www", "aura.html")

mkdirSync(dirname(target), { recursive: true })
copyFileSync(built, target)
console.log(`copied ${built} -> ${target}`)
