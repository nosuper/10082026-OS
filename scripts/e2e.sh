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

printf '%s\n' \
  'namespace = {}; exec(compile(open("/workspace/repo/frontend/e2e/seed.py", "rb").read(), "seed.py", "exec"), namespace); namespace["run"]()' \
  | "${COMPOSE[@]}" exec --no-TTY \
  frappe bash -lc \
  'cd /home/frappe/frappe-bench && bench --site dev.localhost console'

"${COMPOSE[@]}" run --rm playwright \
  bash -lc 'npm ci --no-audit --no-fund && npm run test:e2e'
