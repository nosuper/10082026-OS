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
seed() {
  printf '%s\n' \
    'namespace = {}; exec(compile(open("/workspace/repo/scripts/e2e-seed.py", "rb").read(), "e2e-seed.py", "exec"), namespace); namespace["run"]()' \
    | "${COMPOSE[@]}" exec --no-TTY \
    frappe bash -lc \
    'cd /home/frappe/frappe-bench && bench --site dev.localhost console'
}

seed

# Two suites against one seeded stack: the Vue app at /aura and the React app
# at /aura-next. Both run even if the first fails, so one red suite does not
# hide the state of the other, and the script still exits non-zero.
vue_status=0
react_status=0

"${COMPOSE[@]}" run --rm playwright \
  bash -lc 'npm ci --no-audit --no-fund && npm run test:e2e' || vue_status=$?

# Re-seed between the suites. They share one site, and the Vue breakdown spec
# edits the seeded cost line and puts it back afterwards - so a Vue failure in
# between leaves the React suite reading a price the Vue spec typed. That is
# what run 8 caught: Vue died waiting for "All changes saved", never reached its
# restore, and React then read a 11.000.000 subtotal where the seed says
# 8.000.000. Cheaper and more honest than asking every spec to clean up after
# itself on the way out of a failure.
seed

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
  # stack", and by the time it runs, two suites have edited that stack - which
  # is the mistake this script was just fixed for, repeated one step further
  # down. Run 9 caught it: the repeats failed 10 out of 10 at the same save,
  # deterministically, on a site the seed had not touched since before the
  # React suite.
  seed
  # Which suite the follow-up belongs to. Defaults to the Vue container
  # because the first use of this hook asked for breakdown.spec.js and got
  # "No tests found" - that spec lives in frontend/, and the hook had the
  # React container hardcoded.
  "${COMPOSE[@]}" run --rm "${E2E_AFTER_SERVICE:-playwright}" \
    bash -lc "npm ci --no-audit --no-fund && ${E2E_AFTER}" || after_status=$?
  echo "e2e: follow-up exit ${after_status}"
fi

echo "e2e: vue suite exit ${vue_status}, react suite exit ${react_status}"
if [ "$vue_status" -ne 0 ] || [ "$react_status" -ne 0 ]; then
  exit 1
fi
