#!/usr/bin/env bash
set -euo pipefail

REPO_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
COMPOSE=(docker compose --project-name auraos-e2e --file "$REPO_DIR/docker/compose.yaml" --file "$REPO_DIR/docker/compose.e2e.yaml")

# Signed-in state lives inside the Playwright container (E2E_AUTH_DIR), so it
# goes when the container does and there is nothing here to delete.
cleanup() {
  "${COMPOSE[@]}" down --volumes --remove-orphans
}

trap cleanup EXIT
cleanup

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

printf '%s\n' \
  'namespace = {}; exec(compile(open("/workspace/repo/frontend/e2e/seed.py", "rb").read(), "seed.py", "exec"), namespace); namespace["run"]()' \
  | "${COMPOSE[@]}" exec --no-TTY \
  frappe bash -lc \
  'cd /home/frappe/frappe-bench && bench --site dev.localhost console'

"${COMPOSE[@]}" run --rm playwright \
  bash -lc 'npm ci --no-audit --no-fund && npm run test:e2e'
