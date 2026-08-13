# AuraOS

One shared place for a small video production house: deal pipeline,
cost breakdowns and quotes, jobs, money tracking, paperwork and a
founder-only overhead view. A single custom [Frappe](https://frappeframework.com)
app (`auraos/`) with [frappe-ui](https://github.com/frappe/frappe-ui)
pages for daily screens (`frontend/`).

Spec and tickets live as GitHub issues - see
[the spec](https://github.com/nosuper/10082026-OS/issues/2) and
`docs/agents/issue-tracker.md`.

## Run the dev site (Docker)

Requires Docker with Compose. From the repo root:

```bash
cd docker && docker compose up -d
```

First boot takes several minutes (bench init, site creation, app
install, frontend build). Watch it with `docker compose logs -f frappe`.
Then:

- Site: <http://localhost:8000> - login `Administrator` / `admin`
- frappe-ui app (Contacts): <http://localhost:8000/aura>
- A published quote: `http://localhost:8000/quote/<token>` - no login

The repo is mounted into the container; the bench lives in a named
volume, so `docker compose down` keeps the site and `docker compose up`
resumes it. To rebuild from nothing: `docker compose down -v`.

## Frontend development

```bash
cd frontend
npm install
npm run dev    # vite on :8080, proxying /api and /assets to :8000
npm run build  # emits auraos/public/aura + auraos/www/aura.html
```

The built page is what Frappe serves at `/aura`; the dev server is for
hot reload while the Docker site runs.

## Tests

Two harnesses, matching the spec's testing decisions:

**Pure pytest** (`tests/`) - framework-free logic (the pricing seam).
Runs anywhere, including Windows, no Frappe needed:

```bash
pip install -e . pytest && pytest
```

**Frappe site tests** (`auraos/**/test_*.py`) - document/HTTP API and
permission behavior against a test site. Needs a bench, so run inside
the dev container (`docker compose exec frappe bash`):

```bash
cd ~/frappe-bench
bench new-site --db-root-password admin --admin-password admin test_site
bench --site test_site install-app auraos
bench --site test_site set-config allow_tests true
bench --site test_site run-tests --app auraos
```

**Browser tests** (`frontend/e2e/`) - authenticated Chromium scenarios
against a fresh, disposable Docker site. Docker with Compose is the only
local prerequisite; the version-pinned Playwright container carries its
own browser and system dependencies. From the repo root:

```bash
./scripts/e2e.sh
```

The command uses an isolated Compose project on port 18000, waits for
Frappe's HTTP readiness endpoint, seeds only disposable records, and removes
the site volumes and browser authentication state when it finishes. Downloaded
npm packages are retained in `.e2e-npm-cache/` to speed up repeat runs. A failed
run leaves screenshots, traces and the HTML report under `frontend/test-results/`
and `frontend/playwright-report/`. Password entry and authentication state files
are not recorded in or uploaded with those artifacts. Traces keep the action
timeline but disable network/DOM snapshots so session headers are not captured.

CI (`.github/workflows/ci.yml`) runs all three harnesses plus the frontend
build on every push.

### The permission proof

`auraos/auraos/doctype/founder_spike_note/test_founder_spike_note.py`
is the standing regression proof that a Producer-role session cannot
read a founder-only DocType via the document API, list API, or global
search. Any future founder-only DocType (overhead, commission fields)
should copy that test pattern before real data enters it.

### Attachments

Core File permissions let any System User create a File and point it at
any document, so every doctype here that accepts attachments is gated by
`auraos/attachments.py`: you may attach to what you may write. Add a
doctype to `GUARDED` there the moment anything starts hanging files on
it - generated paperwork made that true for Job.

### Paperwork templates

The company signs on paper, so `auraos/lib/paperwork.py` fills the
founder's own .docx rather than rendering a document of its own: the
letterhead, clauses and signature block come out byte-for-byte as
designed, with `{{client.tax_code}}` replaced. Two things it does that a
string replace would not - it matches placeholders across the runs Word
splits them into, and it never blanks a value it cannot fill, marking
the gap on the page and reporting it to the caller.

### The guest boundary

The client-facing quote page (`/quote/<token>`) is the only part of the
system a guest can reach. Two rules hold it shut, and both are tested:

- Guest has **no permission on any DocType** - the page reads the quote
  with the token as its authorization, so `/api/resource/Deal Quote`
  stays closed even with a valid token in hand.
- What the page may show is a **whitelist**
  (`auraos/lib/quote.py: CLIENT_QUOTE_FIELDS`), not a blocklist. A new
  column on Deal Quote is invisible to clients until someone adds it
  there deliberately. The page and the PDF export render the same
  template from the same builder, so they cannot drift apart.

Published quote versions are immutable: the controller refuses every
content change and leaves only the delivery status (sent / confirmed)
writable. Re-pricing means publishing a new version. The founder can
still *delete* a version (a misfire, or a deal being removed entirely) -
that 404s its link rather than changing what a client already read.

Publishing v2 does not un-send v1: the deal's quote status follows the
newest *delivered* version, so re-pricing a quote the client is sitting
on never makes it drop out of the silence nudge.

### Money out on a job

Two numbers that are easy to confuse are kept apart deliberately.

**Whose money moved.** An advance puts company cash in one person's
hands; every expense they pay *from that advance* hands part of it back
as receipts. What is left is their **float**, and settling records the
transfer that closes it - the holder returns the remainder, or the
company tops them up. An expense the company paid the vendor itself is
money out that moves nobody's float, which is why `paid_from` exists and
why nothing defaults it on the founder's form.
Settling does not end anything: the next advance opens a fresh float on
the same job.

**What it was spent against.** An expense's category is one of the
entries the client was quoted - a package, or a cost line quoted on its
own - so actual-vs-quoted per package needs no bookkeeping of its own.
The quoted side is measured in what somebody actually hands over - a
line's cost after the vendor management fee, plus VAT on an invoice -
not the price the client pays, so both columns of that table are the
same kind of money. A freelancer's PIT is deliberately left out: the
company remits it later through its accountant, and nobody logs it
against a shoot.

Both rules live framework-free in `auraos/lib/settlement.py` and are
pinned by `tests/test_settlement.py`; the doctypes and API are adapters.

## Maintenance notes (evening-hobby budget)

- Everything is one compose file and one custom app; no extra services.
- If the site misbehaves, `docker compose restart frappe` is the first
  move; `docker compose logs -f frappe` tells you why.
- Production deployment (Proxmox, backups to Synology) is ticket T13 -
  this compose file is for development only.
