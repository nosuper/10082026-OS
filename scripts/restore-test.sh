#!/usr/bin/env bash
# Prove the newest backup restores - docs/02: "backup chưa từng restore
# thử là backup không tồn tại". Run quarterly (and after any change to
# backup.sh); every run is appended to restore-test.log as the ritual's
# paper trail.
#
# Restores the newest archive from AURA_BACKUP_DEST into a scratch site
# inside the same stack, counts core records, then drops the scratch
# site. The live site is never touched.
#
# Usage:
#   scripts/restore-test.sh                    # dev defaults
#   AURA_BACKUP_PROJECT=prod AURA_BACKUP_DEST=/var/backups/auraos \
#   AURA_DB_ROOT_PW=... scripts/restore-test.sh
set -euo pipefail

PROJECT="${AURA_BACKUP_PROJECT:-docker}"
DEST="${AURA_BACKUP_DEST:-/var/backups/auraos}"
DB_ROOT_PW="${AURA_DB_ROOT_PW:-admin}"
SCRATCH_SITE=restore-test.localhost

CONTAINER="${PROJECT}-frappe-1"
BENCH_DIR=/home/frappe/frappe-bench

log() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$DEST/restore-test.log"
  printf '%s\n' "$*"
}

archive=$(ls -t "$DEST"/auraos-*.tar 2>/dev/null | head -1)
if [ -z "$archive" ]; then
  log "FAIL: no archive found in $DEST - run scripts/backup.sh first"
  exit 1
fi

cleanup() {
  docker exec "$CONTAINER" bash -lc \
    "cd $BENCH_DIR && bench drop-site $SCRATCH_SITE \
       --db-root-password '$DB_ROOT_PW' --force --no-backup" \
    > /dev/null 2>&1 || true
  docker exec "$CONTAINER" rm -rf /tmp/restore-test || true
}
trap cleanup EXIT
cleanup

docker exec "$CONTAINER" mkdir -p /tmp/restore-test
docker exec -i "$CONTAINER" tar -xf - -C /tmp/restore-test < "$archive"

db=$(docker exec "$CONTAINER" bash -lc 'ls /tmp/restore-test/*-database.sql.gz')
files=$(docker exec "$CONTAINER" bash -lc 'ls /tmp/restore-test/*-files.tar 2>/dev/null | grep -v private || true')
private=$(docker exec "$CONTAINER" bash -lc 'ls /tmp/restore-test/*-private-files.tar 2>/dev/null || true')

docker exec "$CONTAINER" bash -lc \
  "cd $BENCH_DIR && bench new-site $SCRATCH_SITE \
     --db-root-password '$DB_ROOT_PW' --admin-password admin" > /dev/null

restore_args="$db"
[ -n "$files" ] && restore_args="$restore_args --with-public-files $files"
[ -n "$private" ] && restore_args="$restore_args --with-private-files $private"
docker exec "$CONTAINER" bash -lc \
  "cd $BENCH_DIR && bench --site $SCRATCH_SITE --force restore $restore_args \
     --db-root-password '$DB_ROOT_PW'" > /dev/null 2>&1

counts=$(docker exec -i "$CONTAINER" bash -lc \
  "cd $BENCH_DIR && bench --site $SCRATCH_SITE console" <<'EOF' | grep -o 'RESTORE_TEST.*' || true
print("RESTORE_TEST auraos=%s deals=%s jobs=%s quotes=%s" % ("auraos" in frappe.get_installed_apps(), frappe.db.count("Deal"), frappe.db.count("Job"), frappe.db.count("Deal Quote")))
EOF
)

if [ -z "$counts" ]; then
  log "FAIL: $(basename "$archive") restored but the scratch site answered nothing"
  exit 1
fi

# The proof is the schema coming back whole - the app present and its
# tables answering. Record counts are reported, not judged: a fresh
# production site legitimately holds zero deals before go-live.
case "$counts" in
  *auraos=True*) log "OK $(basename "$archive") → $counts" ;;
  *)
    log "FAIL: $(basename "$archive") restored without the auraos app - schema did not come back"
    exit 1
    ;;
esac
