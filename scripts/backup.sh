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
# AURA_BACKUP_OFFSITE may be:
#   - smb://host/share/dir - pushed with smbclient, credentials read
#     from /root/.aura-nas-user + /root/.aura-nas-pass (chmod 600).
#     Userland on purpose: an unprivileged LXC cannot mount anything.
#   - a local path (a mounted share) or rsync target - synced with rsync.
# Empty skips the offsite copy - acceptable on dev only.
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

# Where a successful run says so, and the only place absence is legible
# (#152).
#
# **The log cannot answer the question that matters.** It records what
# happened when something happened - and the failure this exists to catch
# is a cron that never fires, which writes nothing at all. A missing
# nightly line and a quiet month look identical in a file nobody opens.
# So success writes a marker whose *age* is the signal: stale or absent
# both mean "nobody has proved a backup lately", which is the one alarm
# worth having and is true of both failure modes at once.
#
# Written inside the site rather than beside the archive, because the
# archive lives on the docker host and the app cannot see it. This path
# is the site's own private directory, which the app reads directly - so
# the founder's dashboard can answer the question without anything being
# mounted, shipped or granted.
#
# Deliberately last. `set -e` means any earlier failure exits before this
# line, so the marker cannot claim a backup that did not finish.
MARKER="sites/$SITE/private/last-backup"

mark_success() {
  docker exec "$CONTAINER" bash -lc \
    "cd $BENCH_DIR && printf '%s %s %s %s\\n' '$(date -Is)' '$(basename "$ARCHIVE")' '$1' '$COUNTS' > $MARKER"
}

# What the site held, counted **before** the dump (#73).
#
# This is what makes scripts/restore-test.sh able to judge rather than
# only report. Comparing a restored archive against the *live* site is
# the obvious rule and the wrong one: the archive is last night's and the
# site has lived since, so a healthy studio fails it the first day
# somebody creates a deal. What a restore must be measured against is
# what the site held **when the archive was taken**, and this is the only
# moment that number exists.
#
# **Counted before `bench backup`, on purpose.** The dump is a snapshot;
# anything written between the snapshot and a count taken afterwards
# would differ for a reason that is not data loss, and Frappe's own
# scheduler runs at night. Counting first makes the asymmetry safe:
# writes during the window can only make the restored count *higher*, so
# `restored >= recorded` passes and a lower count is a real finding.
# Deletes in that window would break it - rarely, and loudly, which beats
# regularly and vaguely.
#
# **Best-effort, and it must stay that way.** A count is a database call
# with its own ways to fail, and this marker's whole purpose is that its
# absence means "no backup proved itself". A transient hiccup after a
# perfectly good dump must not exit before the write and make the alarm
# cry about a backup sitting on disk: the guard must not be able to kill
# the thing it guards. So the failure is swallowed, the line is written
# either way, and the pairs are simply absent - which restore-test.sh
# reports in its own words rather than borrowing this alarm's.
# Pipe-separated because doctype names have spaces in them, and the
# marker's pairs must not: every reader of this line splits on spaces.
# So a name travels as `Job_Payment_Milestone=4` and restore-test.sh
# turns the underscores back into spaces - safe because no Frappe doctype
# name contains an underscore.
COUNTED="Deal|Job|Deal Quote|Job Payment Milestone|Company Expense"

count_rows() {
  docker exec -i "$CONTAINER" bash -lc \
    "cd $BENCH_DIR && bench --site $SITE console" <<EOF 2>/dev/null | grep -o 'COUNTS.*' || true
names = "$COUNTED".split("|")
print("COUNTS " + " ".join("%s=%s" % (n.replace(" ", "_"), frappe.db.count(n)) for n in names))
EOF
}

COUNTS=$(count_rows | sed 's/^COUNTS //')
[ -n "$COUNTS" ] || log "note: $SITE - counts unavailable, the marker will carry none"

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
  case "$OFFSITE" in
    smb://*)
      rest="${OFFSITE#smb://}"
      host="${rest%%/*}"
      rest="${rest#*/}"
      share="${rest%%/*}"
      dir="${rest#*/}"
      smbclient "//$host/$share" "$(cat /root/.aura-nas-pass)" \
        -U "$(cat /root/.aura-nas-user)" \
        -c "cd $dir; put $ARCHIVE $(basename "$ARCHIVE")" > /dev/null
      ;;
    *)
      rsync -a "$ARCHIVE" "$OFFSITE/"
      ;;
  esac
  log "OK $SITE → $ARCHIVE ($size), offsite → $OFFSITE"
  mark_success "$size"
else
  log "OK $SITE → $ARCHIVE ($size), no offsite target configured"
  # Marked all the same. An on-site-only backup is a weaker backup and a
  # real one; refusing to record it would report "no backup" about a
  # backup that exists, which is the false alarm that teaches a founder
  # to ignore the alarm.
  mark_success "$size"
fi
