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
# site. Playwright's global setup navigates straight there, so gating on ping
# alone let the suite start too early and fail in setup with zero tests run.
#
# **Two pages, not one, and the second is the one that was missing.** Global
# setup signs in and then waits for /aura-next/deals - so the login page being
# warm only covers the first half of what it does. The SPA page behind the
# login was still cold on every boot, and its first render happened inside
# global setup's own timeout. Run 27 died exactly there with zero of 65 tests
# run. This is a candidate mechanism for that class of void rather than a
# proven one: what is certain is that the page was never warmed, and warming
# it costs one request.
#
# The redirect-to also pointed at /aura/deals - the Vue app #103 deleted - so
# the one page it did warm was warmed for a destination that no longer exists.
warm_page() {
  local path="$1" label="$2"
  for _ in $(seq 1 300); do
    if curl --fail --silent --output /dev/null --max-time 30 \
      "http://127.0.0.1:18000${path}"; then
      return 0
    fi
    sleep 2
  done
  "${COMPOSE[@]}" logs --tail 200 frappe
  echo "AuraOS E2E ${label} never rendered" >&2
  return 1
}

warm_page "/login?redirect-to=%2Faura-next%2Fdeals" "login page" || exit 1
# Unauthenticated: this redirects to /login, and that is fine. The cost being
# paid here is Frappe rendering the www page and serving the bundle for the
# first time, which is the same work whoever asks for it.
warm_page "/aura-next/deals" "app shell" || exit 1

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
  # service instead of being silently ignored. It is also the seam that lets a
  # follow-up run somewhere else in the stack - E2E_AFTER_SERVICE=frappe for a
  # bench console check against the same seeded site.
  #
  # No npm ci is prepended. It was, and it made this hook playwright-react's
  # alone: frappe has no package.json, so the command died before E2E_AFTER
  # was ever reached (#149). Nothing is lost by dropping it - node_modules is
  # the playwright-react-node-modules named volume, which the suite run above
  # already populated and which outlives each `run --rm`. A follow-up that
  # genuinely needs a fresh install can say so in E2E_AFTER itself.
  "${COMPOSE[@]}" run --rm "${E2E_AFTER_SERVICE:-playwright-react}" \
    bash -lc "${E2E_AFTER}" || after_status=$?
  echo "e2e: follow-up exit ${after_status}"
fi

# Hold the stack open for work that runs against it from outside - seam
# modules through `docker exec`, a console check, a hand look at a screen.
#
# **Ends when the work says so, not when a timer says so.** The previous
# pattern was E2E_AFTER='sleep 900', which is wrong in both directions: it
# wastes the box when the work takes two minutes, and it tears the stack out
# from under the work when it takes twenty. It also gives a watcher nothing to
# trigger on - the only line it prints is the one that means the window has
# already closed, which is how a fifteen-minute window went unused.
#
# So: an explicit line saying the window is OPEN, and a sentinel file to close
# it. The ceiling is a backstop against an abandoned session, not the design.
if [ -n "${E2E_HOLD:-}" ]; then
  release="$REPO_DIR/.e2e-release"
  rm -f "$release"
  echo "e2e: HOLD OPEN - stack is up; touch $release to tear down"
  held=0
  limit="${E2E_HOLD_MAX:-1800}"
  while [ ! -f "$release" ] && [ "$held" -lt "$limit" ]; do
    sleep 5
    held=$((held + 5))
  done
  rm -f "$release"
  if [ "$held" -ge "$limit" ]; then
    echo "e2e: hold hit its ${limit}s ceiling and tore down on its own"
  else
    echo "e2e: hold released after ${held}s"
  fi
fi

echo "e2e: react suite exit ${react_status}"
if [ "$react_status" -ne 0 ]; then
  exit 1
fi
