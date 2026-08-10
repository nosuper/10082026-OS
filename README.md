# AuraOS

One shared place for a small video production house: deal pipeline,
cost breakdowns and quotes, jobs, money tracking, paperwork and a
founder-only overhead view. A single custom [Frappe](https://frappeframework.com)
app (`auraos/`) with [frappe-ui](https://github.com/frappe/frappe-ui)
pages for daily screens (`frontend/`).

Spec and tickets live as GitHub issues — see
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

- Site: <http://localhost:8000> — login `Administrator` / `admin`
- frappe-ui app (Contacts): <http://localhost:8000/aura>

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

**Pure pytest** (`tests/`) — framework-free logic (the pricing seam).
Runs anywhere, including Windows, no Frappe needed:

```bash
pip install -e . pytest && pytest
```

**Frappe site tests** (`auraos/**/test_*.py`) — document/HTTP API and
permission behavior against a test site. Needs a bench, so run inside
the dev container (`docker compose exec frappe bash`):

```bash
cd ~/frappe-bench
bench new-site --db-root-password admin --admin-password admin test_site
bench --site test_site install-app auraos
bench --site test_site set-config allow_tests true
bench --site test_site run-tests --app auraos
```

CI (`.github/workflows/ci.yml`) runs both harnesses plus the frontend
build on every push.

### The permission proof

`auraos/auraos/doctype/founder_spike_note/test_founder_spike_note.py`
is the standing regression proof that a Producer-role session cannot
read a founder-only DocType via the document API, list API, or global
search. Any future founder-only DocType (overhead, commission fields)
should copy that test pattern before real data enters it.

## Maintenance notes (evening-hobby budget)

- Everything is one compose file and one custom app; no extra services.
- If the site misbehaves, `docker compose restart frappe` is the first
  move; `docker compose logs -f frappe` tells you why.
- Production deployment (Proxmox, backups to Synology) is ticket T13 —
  this compose file is for development only.
