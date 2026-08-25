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
# The live site, only so its backup marker can be read - see the
# judgement below. Never written to.
SITE="${AURA_BACKUP_SITE:-dev.localhost}"
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

# What the site held when this archive was taken. `backup.sh` records it
# on the marker's one line, as `Doctype_Name=count` pairs, because that
# is the only moment the number exists (#73).
#
# **The comparison is against the marker, never against the live site.**
# The archive is last night's and the site has lived since, so a healthy
# studio would fail "restored not fewer than live" the first day somebody
# creates a deal - and a check that cries on healthy days gets muted.
#
# **`>=` rather than `==`, because the counts are taken before the dump.**
# Anything written in the window between counting and the snapshot can
# only make the restored figure higher. Lower is a real finding.
#
# **The names come from the marker, not from a list here**, so the two
# scripts cannot drift about which doctypes matter and adding one is a
# one-line change in one place.
recorded=$(docker exec "$CONTAINER" bash -lc \
  "cat $BENCH_DIR/sites/$SITE/private/last-backup 2>/dev/null || true" | tr -d '\r')
pairs=$(printf '%s\n' "$recorded" | tr ' ' '\n' | grep '=' || true)

query="print('RESTORE_TEST app=%s' % ('auraos' in frappe.get_installed_apps()))"
for pair in $pairs; do
  doctype=$(printf '%s' "${pair%%=*}" | tr '_' ' ')
  query="$query
print('RESTORE_COUNT ${pair%%=*}=%s' % frappe.db.count('$doctype'))"
done

answered=$(docker exec -i "$CONTAINER" bash -lc \
  "cd $BENCH_DIR && bench --site $SCRATCH_SITE console" <<EOF | grep -oE 'RESTORE_(TEST|COUNT).*' || true
$query
EOF
)

if [ -z "$answered" ]; then
  log "FAIL: $(basename "$archive") restored but the scratch site answered nothing"
  exit 1
fi

case "$answered" in
  *app=True*) : ;;
  *)
    log "FAIL: $(basename "$archive") restored without the auraos app - schema did not come back"
    exit 1
    ;;
esac

if [ -z "$pairs" ]; then
  # No pairs on the marker: an archive older than this check, or a run
  # whose counting failed. **Different from "the backup did not run"**,
  # and said in its own words rather than borrowing that alarm's. The
  # fallback is a floor: whatever the live site is not empty of, the
  # restored site must not be empty of either.
  floor=$(docker exec -i "$CONTAINER" bash -lc \
    "cd $BENCH_DIR && bench --site $SITE console" <<'EOF' | grep -o 'LIVE.*' || true
print("LIVE deals=%s jobs=%s" % (frappe.db.count("Deal"), frappe.db.count("Job")))
EOF
  )
  log "NOTE: $(basename "$archive") - the marker recorded no counts; checking a floor instead ($floor)"
  for name in deals jobs; do
    live=$(printf '%s' "$floor" | tr ' ' '\n' | grep "^$name=" | cut -d= -f2)
    [ -n "$live" ] && [ "$live" -gt 0 ] || continue
    restored=$(printf '%s' "$answered" | tr ' ' '\n' | grep -iE "^(Deal|Job)=" | cut -d= -f2 | head -1)
    [ -n "$restored" ] || restored=0
    if [ "$restored" -eq 0 ]; then
      log "FAIL: the live site holds $name and the restored one holds none"
      exit 1
    fi
  done
  log "OK $(basename "$archive") → $answered (no recorded counts to compare)"
  exit 0
fi

# The judgement.
for pair in $pairs; do
  name="${pair%%=*}"
  was="${pair#*=}"
  now=$(printf '%s\n' "$answered" | grep -o "RESTORE_COUNT $name=[0-9]*" | cut -d= -f2)
  [ -n "$now" ] || {
    log "FAIL: the restored site did not answer for $name"
    exit 1
  }
  if [ "$now" -lt "$was" ]; then
    log "FAIL: $(basename "$archive") restored $now $name where the backup recorded $was"
    exit 1
  fi
done

# One line per run: this log is the paper trail and `tail` is how anyone
# reads it, so the pairs are flattened rather than printed as the
# newline-separated list the loop wanted them to be.
log "OK $(basename "$archive") → $(printf '%s' "$answered" | tr '\n' ' ') (recorded: $(printf '%s' "$pairs" | tr '\n' ' '))"
