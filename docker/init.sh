#!/bin/bash
# First-boot initialisation for the dev container, then `bench start`.
# Idempotent: a bench that already exists is reused as-is.
set -euo pipefail

BENCH_DIR=/home/frappe/frappe-bench
SITE=dev.localhost

if [ ! -f "$BENCH_DIR/sites/common_site_config.json" ]; then
    bench init --frappe-branch version-15 "$BENCH_DIR"
fi

cd "$BENCH_DIR"
bench set-config -g db_host mariadb

if [ ! -d "apps/auraos" ]; then
    bench get-app auraos /workspace/repo
fi

if [ ! -d "sites/$SITE" ]; then
    bench new-site "$SITE" \
        --mariadb-user-host-login-scope='%' \
        --db-root-password admin \
        --admin-password admin
    bench --site "$SITE" install-app auraos
    bench --site "$SITE" set-config developer_mode 1
    bench --site "$SITE" clear-cache
fi

bench use "$SITE"

# Build the frappe-ui page so /aura serves (skipped if already built).
if [ ! -f "apps/auraos/auraos/www/aura.html" ]; then
    (cd apps/auraos/frontend && npm install --no-audit --no-fund && npm run build)
fi

exec bench start
