#!/bin/bash
# First-boot initialisation for the dev container, then `bench start`.
# Idempotent: a bench that already exists is reused as-is.
#
# Follows the frappe_docker development pattern: redis runs as its own
# compose service (the bench image ships no redis-server), so redis
# config generation is skipped and redis lines are stripped from the
# Procfile.
set -euo pipefail

BENCH_DIR=/home/frappe/frappe-bench
# Parametrized for the production overlay (compose.prod.yaml); the
# defaults keep dev, e2e and CI exactly as they were.
SITE="${AURA_SITE:-dev.localhost}"
DB_ROOT_PW="${AURA_DB_ROOT_PW:-admin}"
ADMIN_PW="${AURA_ADMIN_PW:-admin}"
DEV_MODE="${AURA_DEV_MODE:-1}"

if [ ! -f "$BENCH_DIR/sites/common_site_config.json" ]; then
    # python3.12: the image defaults to 3.14, which Frappe v15 does not support.
    bench init --skip-redis-config-generation --frappe-branch version-15 \
        --python python3.12 "$BENCH_DIR"
fi

cd "$BENCH_DIR"
bench set-config -g db_host mariadb
bench set-config -g redis_cache redis://redis:6379
bench set-config -g redis_queue redis://redis:6379
bench set-config -g redis_socketio redis://redis:6379
sed -i '/redis/d' ./Procfile

# The repo mount is owned by a different uid than the container user;
# without this, git (and therefore bench get-app) refuses to read it.
git config --global --add safe.directory '*'

if [ ! -d "apps/auraos" ]; then
    bench get-app auraos /workspace/repo
fi

if [ ! -d "sites/$SITE" ]; then
    bench new-site "$SITE" \
        --mariadb-user-host-login-scope='%' \
        --db-root-password "$DB_ROOT_PW" \
        --admin-password "$ADMIN_PW"
    bench --site "$SITE" install-app auraos
    if [ "$DEV_MODE" = "1" ]; then
        bench --site "$SITE" set-config developer_mode 1
    fi
    bench --site "$SITE" clear-cache
fi

bench use "$SITE"

# Build the frappe-ui page so /aura serves (skipped if already built).
if [ ! -f "apps/auraos/auraos/www/aura.html" ]; then
    (cd apps/auraos/frontend && npm install --no-audit --no-fund && npm run build)
fi

# Ensure the app's assets symlink exists - without it the built
# frontend 404s and /aura renders as a white page.
mkdir -p sites/assets
ln -sfn "$BENCH_DIR/apps/auraos/auraos/public" sites/assets/auraos

exec bench start
