#!/usr/bin/env bash
set -euo pipefail

REPO_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
COMPOSE=(docker compose --project-name auraos-e2e --file "$REPO_DIR/docker/compose.yaml" --file "$REPO_DIR/docker/compose.e2e.yaml")

# Signed-in state lives inside the Playwright container (E2E_AUTH_DIR), so it
# goes when the container does and there is nothing here to delete.
teardown() {
  "${COMPOSE[@]}" down --volumes --remove-orphans
}

# The trap must re-raise the status that triggered it. Without the explicit
# exit, a failing Playwright run left the script reporting the exit code of
# `compose down` instead - a red suite looked green.
cleanup() {
  local status=$?
  teardown
  exit "$status"
}

trap cleanup EXIT
teardown

export AURA_WEB_PORT=18000
export AURA_SOCKET_PORT=19000
export AURA_VITE_PORT=18080
"${COMPOSE[@]}" up --detach mariadb redis frappe

ready=false
for _ in $(seq 1 600); do
  if curl --fail --silent --output /dev/null http://127.0.0.1:18000/api/method/ping; then
    ready=true
    break
  fi
  if ! "${COMPOSE[@]}" ps --status running frappe | grep -q frappe; then
    "${COMPOSE[@]}" logs --tail 200 frappe
    echo "AuraOS E2E site stopped before it became ready" >&2
    exit 1
  fi
  sleep 2
done

if [ "$ready" != true ]; then
  "${COMPOSE[@]}" logs --tail 200 frappe
  echo "AuraOS E2E site was not ready within 20 minutes" >&2
  exit 1
fi

# /api/method/ping answers long before a server-rendered page does: the first
# hit on /login compiles assets and templates and can take minutes on a cold
# site. Playwright's global setup navigates straight there with a 30s
# timeout, so gating on ping alone let the suite start too early and fail in
# setup with zero tests run. Warm the real page before handing over.
warm=false
for _ in $(seq 1 300); do
  if curl --fail --silent --output /dev/null --max-time 30 \
    "http://127.0.0.1:18000/login?redirect-to=%2Faura%2Fdeals"; then
    warm=true
    break
  fi
  sleep 2
done

if [ "$warm" != true ]; then
  "${COMPOSE[@]}" logs --tail 200 frappe
  echo "AuraOS E2E login page never rendered" >&2
  exit 1
fi

# The seed belongs to the stack, not to either app. It lived in frontend/e2e/
# because the Vue suite was the first caller, and it stayed there after the
# React suite started depending on it too - so `rm -rf frontend/` in #103 would
# have deleted the React suite's seed. The failure would have been a stack that
# boots, a suite that runs, and assertions failing against data nobody created,
# which reads as "the React app broke" rather than "the seed is gone".
# The seed runs inside `bench console`, which prints a traceback and then
# exits 0. So `set -e` cannot see a seed that failed, and a half-seeded
# site runs the whole suite: most specs still pass, the ones that do not
# fail against data nobody created, and the run reads as a screen defect.
# That is not hypothetical - it is how #135 stayed invisible.
#
# The exit status cannot carry the signal, so the seed states its own
# success instead. run() prints the marker below as its last act, after
# commit(), and this checks the output for it. Anything that stops the
# seed early - a throw, an import error, a rollback - stops the marker.
#
# Read out of the seed rather than restated here. Spelling it in both
# files would be two independent statements of one value, which is the
# defect rule 32 names for dates and e2e/fixture.js avoids for names -
# they agree until somebody edits one of them.
#
# The empty case has to be fatal and is the reason this is three lines
# rather than one: `grep -q ""` matches anything, so a marker that failed
# to extract would turn the seed check into a check that always passes.
# A guard that silently becomes vacuous is worse than no guard.
SEED_MARKER=$(
  grep -m1 '^SEEDED_MARKER' "$REPO_DIR/scripts/e2e-seed.py" \
    | grep -o '"[^"]*"' | tr -d '"\n'
)
if [ -z "$SEED_MARKER" ]; then
  echo "e2e: cannot read SEEDED_MARKER out of scripts/e2e-seed.py." >&2
  echo "e2e: refusing to run, because an empty marker matches everything." >&2
  exit 1
fi

seed() {
  local output
  local status=0
  output=$(
    printf '%s\n' \
      'namespace = {}; exec(compile(open("/workspace/repo/scripts/e2e-seed.py", "rb").read(), "e2e-seed.py", "exec"), namespace); namespace["run"]()' \
      | "${COMPOSE[@]}" exec --no-TTY \
      frappe bash -lc \
      'cd /home/frappe/frappe-bench && bench --site dev.localhost console' 2>&1
  ) || status=$?

  printf '%s\n' "$output"

  if ! printf '%s' "$output" | grep -q "$SEED_MARKER"; then
    echo "e2e: the seed did not finish - no completion marker in its output." >&2
    echo "e2e: the site is half-seeded, so the suite is not being run." >&2
    return 1
  fi
  return "$status"
}

seed

# One suite now. There were two - the Vue app at /aura and the React app at
# /aura-next - and this ran both even when the first failed, so a red suite
# could not hide the state of the other. #103 retired the Vue app.
#
# The re-seed that used to sit between the two suites has gone with them. It
# existed because they shared one site: the Vue breakdown spec edited the
# seeded cost line and restored it at the end, so a Vue failure in between left
# the React suite reading a price the Vue spec typed. That is what run 8
# caught. With one suite there is nothing in between - but the reason survives
# in seed() itself, which now states what the seeded values are rather than
# only creating them when absent, and in the re-seed before E2E_AFTER below.
react_status=0

"${COMPOSE[@]}" run --rm playwright-react \
  bash -lc 'npm ci --no-audit --no-fund && npm run test:e2e' || react_status=$?

# An extra command against the same seeded stack, before teardown. Booting the
# stack costs eleven minutes and a window in which nobody else trusts the box,
# so a follow-up run that needs the same seed - a --repeat-each pass to tell a
# flaky test from a broken one - should share this boot rather than buy another.
# Its exit status is reported but does not fail the run: it is a measurement,
# not a gate.
if [ -n "${E2E_AFTER:-}" ]; then
  after_status=0
  # Seed again first. This hook's own contract says "against the same seeded
  # stack", and by the time it runs the suite has edited that stack. Run 9
  # caught it: the repeats failed 10 out of 10 at the same save,
  # deterministically, on a site the seed had not touched since before the
  # React suite.
  seed
  # Only one runner exists now. The variable stays rather than being
  # hardcoded so that an invocation still passing E2E_AFTER_SERVICE=playwright
  # - the Vue container, which #103 removed - fails loudly on an unknown
  # service instead of being silently ignored.
  "${COMPOSE[@]}" run --rm "${E2E_AFTER_SERVICE:-playwright-react}" \
    bash -lc "npm ci --no-audit --no-fund && ${E2E_AFTER}" || after_status=$?
  echo "e2e: follow-up exit ${after_status}"
fi

echo "e2e: react suite exit ${react_status}"
if [ "$react_status" -ne 0 ]; then
  exit 1
fi
