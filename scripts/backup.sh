#!/usr/bin/env bash
# Nightly database+files backup of an AuraOS site.
#
# docs/02 §Backup: "bắt buộc, không thương lượng" - nightly, offsite,
# and proven by scripts/restore-test.sh (a backup that has never been
# restored does not exist).
#
# One run produces one artifact: auraos-<site>-<stamp>.tar holding the
# database dump, public/private file tars and the site_config backup -
# a single file to rotate, ship offsite, and hand to restore-test.sh.
#
# Usage (cron on the docker host):
#   scripts/backup.sh                          # dev defaults
#   AURA_BACKUP_PROJECT=prod \
#   AURA_BACKUP_SITE=os.example.vn \
#   AURA_BACKUP_DEST=/var/backups/auraos \
#   AURA_BACKUP_OFFSITE=/mnt/synology/auraos \
#     scripts/backup.sh
#
# AURA_BACKUP_OFFSITE may be a local path (a mounted Synology share) or
# an rsync-over-ssh target (user@nas:/volume1/auraos). Empty skips the
# offsite copy - acceptable on dev only.
set -euo pipefail

PROJECT="${AURA_BACKUP_PROJECT:-docker}"
SITE="${AURA_BACKUP_SITE:-dev.localhost}"
DEST="${AURA_BACKUP_DEST:-/var/backups/auraos}"
KEEP_DAYS="${AURA_BACKUP_KEEP_DAYS:-14}"
OFFSITE="${AURA_BACKUP_OFFSITE:-}"

CONTAINER="${PROJECT}-frappe-1"
BENCH_DIR=/home/frappe/frappe-bench
BACKUP_DIR="$BENCH_DIR/sites/$SITE/private/backups"
STAMP=$(date +%Y%m%d-%H%M%S)
ARCHIVE="$DEST/auraos-${SITE//./_}-$STAMP.tar"

log() {
  mkdir -p "$DEST"
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$DEST/backup.log"
  printf '%s\n' "$*"
}

docker exec "$CONTAINER" bash -lc \
  "cd $BENCH_DIR && bench --site $SITE backup --with-files" > /dev/null

# The newest run shares one timestamp prefix; ship exactly that set.
prefix=$(docker exec "$CONTAINER" bash -lc \
  "ls -t $BACKUP_DIR/*-database.sql.gz | head -1" | sed 's/-database\.sql\.gz$//')
if [ -z "$prefix" ]; then
  log "FAIL $SITE: bench backup produced no database dump"
  exit 1
fi

mkdir -p "$DEST"
docker exec "$CONTAINER" bash -lc \
  "cd $(dirname "$prefix") && tar -cf - \$(basename -a ${prefix}*)" > "$ARCHIVE"

size=$(du -h "$ARCHIVE" | cut -f1)

# Rotate local copies; the offsite side keeps its own history.
find "$DEST" -maxdepth 1 -name 'auraos-*.tar' -mtime "+$KEEP_DAYS" -delete

if [ -n "$OFFSITE" ]; then
  rsync -a "$ARCHIVE" "$OFFSITE/"
  log "OK $SITE → $ARCHIVE ($size), offsite → $OFFSITE"
else
  log "OK $SITE → $ARCHIVE ($size), no offsite target configured"
fi
