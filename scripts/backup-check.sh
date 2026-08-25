#!/usr/bin/env bash
# Has a backup proved itself lately? (#152)
#
# **Fires on absence, not on failure**, and that is the whole design.
# scripts/backup.sh already logs FAIL and exits non-zero when a run goes
# wrong - but the failure worth catching is the one that writes nothing:
# a cron that was never installed, a container renamed, a host rebooted
# into a state where the job silently stopped firing. **A quiet month and
# a healthy month look identical in a log nobody opens.**
#
# So this reads the marker backup.sh writes on success and judges it by
# age. Missing and stale give the same verdict on purpose: both mean
# nobody has proved a backup lately, which is the only thing a person
# can act on.
#
# Read-only. It runs `docker exec ... cat` and nothing else - no bench
# command, no write, nothing that can disturb the site it is asking
# about.
#
# Usage (cron on the docker host, after the backup window):
#   scripts/backup-check.sh
#   AURA_BACKUP_PROJECT=prod AURA_BACKUP_SITE=os.example.vn \
#     scripts/backup-check.sh || mail -s 'AuraOS backup' you@example.vn
#
# Exit 0 fresh, 1 stale or missing, 2 cannot tell (container down) - and
# **2 is deliberately not 1**: "the box is off" is a different sentence
# from "the backup did not run", and a check that says the second when it
# means the first gets muted within a week.
set -euo pipefail

PROJECT="${AURA_BACKUP_PROJECT:-docker}"
SITE="${AURA_BACKUP_SITE:-dev.localhost}"
# 26 rather than 24: a nightly job plus clock drift plus a run that takes
# an hour is still healthy, and a threshold that cries on a slow Tuesday
# is a threshold somebody turns off.
MAX_AGE_HOURS="${AURA_BACKUP_MAX_AGE_HOURS:-26}"

CONTAINER="${PROJECT}-frappe-1"
MARKER="/home/frappe/frappe-bench/sites/$SITE/private/last-backup"

if ! docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -q true; then
  echo "backup-check: cannot tell - $CONTAINER is not running" >&2
  exit 2
fi

recorded=$(docker exec "$CONTAINER" cat "$MARKER" 2>/dev/null || true)
if [ -z "$recorded" ]; then
  echo "backup-check: NO BACKUP RECORDED for $SITE" >&2
  echo "backup-check: nothing has written $MARKER - either no backup has run" >&2
  echo "backup-check: since this check was installed, or backup.sh is an older" >&2
  echo "backup-check: copy that does not record one." >&2
  exit 1
fi

at="${recorded%% *}"
then_epoch=$(date -d "$at" +%s 2>/dev/null || echo 0)
if [ "$then_epoch" -eq 0 ]; then
  echo "backup-check: cannot tell - unreadable timestamp in marker: $recorded" >&2
  exit 2
fi

age_hours=$(( ( $(date +%s) - then_epoch ) / 3600 ))
if [ "$age_hours" -gt "$MAX_AGE_HOURS" ]; then
  echo "backup-check: STALE - last backup of $SITE was ${age_hours}h ago" >&2
  echo "backup-check: $recorded" >&2
  exit 1
fi

echo "backup-check: OK - $SITE backed up ${age_hours}h ago ($recorded)"
