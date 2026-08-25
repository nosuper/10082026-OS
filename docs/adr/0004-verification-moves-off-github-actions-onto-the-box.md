# Verification moves off GitHub Actions onto the box

> **Reversed on 2026-08-25, hours after it was written.** The repository was
> made public, which makes GitHub Actions free, so the `CI` workflow is
> **enabled again and is the authority once more**. ADR-0001's original
> sentence stands after all.
>
> This file is kept rather than deleted, for two reasons. The commands below
> still work and are the way to run a suite without pushing. And the trap it
> records - the box's `test_site` persists, so it needs `bench migrate` before
> a run - is a fact about the box that outlived the decision that found it.
>
> Read the rest as history: it is what was true while the workflow was off.

The `CI` workflow is **disabled**. The test suites still run, and they still
gate a merge — they run on LXC 102, by hand, against the benches already
there. Nothing is skipped; the authority moved.

The founder ruled on 2026-08-25, against paying GitHub for Actions minutes on
a project with one developer, a box that is already running, and a suite that
takes about twenty minutes end to end wherever it runs.

## What this replaces

ADR-0001 said, in as many words: *"Automated tests do not run on a preview
stack. CI builds a fresh site per branch and is the authority on whether the
suite passes."* The second sentence is no longer true and that ADR should be
read with this one beside it. The first still is: a preview stack is for a
human to click through, and it is not where the suite runs.

**This file exists because of what happened on 2026-08-25.** #103 retired the
Vue frontend, the retirement lived on a branch `main` could not see, and three
tickets went on building Vue against a decision that was invisible from where
they were standing. Disabling CI while leaving ADR-0001 saying CI decides
would be the same shape of trap: a live document describing a machine that is
switched off. So the decision is written where the other decisions are.

## How the suite runs now

Four checks, the same four the workflow ran. The first two run on any machine;
the last two need the box.

```bash
# 1. Pure python - anywhere, including Windows
pip install -e . pytest && pytest

# 2. Frontend - anywhere with node
cd frontend-react && npm ci && npx tsc --noEmit && npx eslint . && npm run build

# 3. Frappe site tests - on the box, against the dev bench's test site
ssh root@192.168.1.94
docker exec docker-frappe-1 bash -lc \
  'cd /home/frappe/frappe-bench && bench --site test_site migrate && \
   bench --site test_site run-tests --app auraos'

# 4. Browser tests - on the box, disposable stack on port 18000
cd /opt/auraos && ./scripts/e2e.sh
```

**`bench --site test_site migrate` first, and that is not optional.** The
workflow created a fresh site every run, so it never met a stale one. The
box's `test_site` persists, and a run against it without migrating fails at
collection with `DocType Bank Statement not found` — a message about the test
runner that is really a message about the site being behind. It cost a run to
learn; it is written here so it costs nobody else one.

## What is worse now, said plainly

- **Nothing runs unless a person runs it.** The workflow ran on every push
  whether anyone remembered or not. This does not.
- **It runs against benches that persist.** A fresh site per branch was a real
  guarantee of isolation; `test_site` carries whatever the last run left. The
  migrate above is the mitigation, not a cure.
- **A pull request carries no evidence.** The green tick is gone, so what was
  run has to be said in the PR or the commit message by whoever ran it. A
  claim that the suite passed is now a claim a human makes.

That third one is the cost worth watching. The tick was a fact; a sentence is
a promise.

## Turning it back on

```bash
gh workflow enable "CI" --repo nosuper/10082026-OS
```

The workflow file is untouched — it is disabled, not deleted, so restoring it
is one command and no code review. The reason it is off is billing, not the
workflow, so nothing about `.github/workflows/ci.yml` needs revisiting first.
