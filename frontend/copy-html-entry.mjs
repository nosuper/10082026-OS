// Copy the built SPA shell into auraos/www so Frappe serves it at /aura,
// injecting the CSRF token Jinja tag (www pages are Jinja-rendered;
// auraos/www/aura.py provides csrf_token in the context). Without it,
// frappe-ui's POST calls fail CSRF for logged-in users.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const here = dirname(fileURLToPath(import.meta.url))
const built = join(here, "..", "auraos", "public", "aura", "index.html")
const target = join(here, "..", "auraos", "www", "aura.html")

const csrfTag =
  "<script>window.csrf_token = '{{ csrf_token }}'</script>"
const html = readFileSync(built, "utf8").replace(
  "<head>",
  `<head>\n    ${csrfTag}`
)
if (!html.includes(csrfTag)) {
  throw new Error("could not inject csrf_token tag into " + built)
}
mkdirSync(dirname(target), { recursive: true })
writeFileSync(target, html)
console.log(`copied ${built} -> ${target} (csrf tag injected)`)
