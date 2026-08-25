#!/usr/bin/env bash
# Put a specific commit of AuraOS onto a running stack (#73).
#
# Until now "deploy" was a sequence somebody remembered: fetch inside the
# container's clone, check out, build the frontend, copy assets, migrate,
# restart - and one of those steps left root-owned files behind and had
# to be repaired with chown. A remembered sequence is one that goes wrong
# on the day it matters, in front of the person least able to debug it.
#
# **Every step states its success rather than being inferred.** The same
# discipline scripts/backup.sh uses for its marker: nothing here says
# "done" because the command before it did not fail - each check asks the
# stack what it now holds and compares it against what was asked for.
#
# **Prod runs only what origin has.** The script refuses a commit that is
# not contained in the deploy ref, so nothing reaches production that is
# not pushed, reviewable and reachable by name from another machine. The
# founder ruled `origin/main` as that ref (relayed through the
# coordination board, 2026-08-20), which makes "merge feat/react-frontend
# into main" a named step of the cutover rather than a thing that happens
# quietly. Until that merge, this script refusing is correct behaviour.
#
# Usage:
#   scripts/deploy-prod.sh                       # dev stack, origin/main
#   AURA_DEPLOY_REF=origin/feat/x scripts/deploy-prod.sh   # refused: not on the gate
#   AURA_DEPLOY_PROJECT=aura-prod AURA_DEPLOY_SITE=os.example.vn \
#   AURA_DEPLOY_CONFIRM=yes scripts/deploy-prod.sh
#   AURA_DEPLOY_DRY_RUN=yes scripts/deploy-prod.sh   # plan only, changes nothing
#
# The confirmation variable is not ceremony: see the guard below.
set -euo pipefail

PROJECT="${AURA_DEPLOY_PROJECT:-docker}"
SITE="${AURA_DEPLOY_SITE:-dev.localhost}"
# What to deploy, and what prod is allowed to run. **Two variables, not
# one.** They were one until the acceptance run was being planned, and
# the check was vacuous: TARGET came from REF, so "is TARGET contained in
# REF" was always true, and `AURA_DEPLOY_REF=<a local sha>` would have
# deployed unpushed work while printing "contained in". A guard that
# cannot fail is not a guard - the same defect as a substring regex that
# matches its own negation, found the same way, by asking how it would be
# rehearsed.
REF="${AURA_DEPLOY_REF:-origin/main}"
GATE="${AURA_DEPLOY_GATE:-origin/main}"
REPO="${AURA_DEPLOY_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PORT="${AURA_WEB_PORT:-8000}"
URL="${AURA_DEPLOY_URL:-http://127.0.0.1:$PORT}"

CONTAINER="${PROJECT}-frappe-1"
BENCH_DIR=/home/frappe/frappe-bench
APP_DIR="$BENCH_DIR/apps/auraos"
# Where a successful deploy says so, beside the backup's marker and for
# the same reason: "what is this stack running" should be answerable
# without ssh archaeology, and absence is legible.
MARKER="sites/$SITE/private/last-deploy"

DRY="${AURA_DEPLOY_DRY_RUN:-}"

step() { printf '\n== %s\n' "$*"; }
ok() { printf '   ok: %s\n' "$*"; }
die() { printf '   FAIL: %s\n' "$*" >&2; exit 1; }
inside() { docker exec "$CONTAINER" bash -lc "$1"; }

# **Every mutation goes through here, and a dry run prints it instead.**
#
# Written after testing this script the only way it could be tested -
# by running it - and pointing it at a stack it had no business
# touching. It stopped short by luck rather than by design. **A script
# that can only be rehearsed by doing the thing will be rehearsed
# somewhere it should not be**, so rehearsing it is now a mode.
#
# Reads and checks still run in a dry run: the point is to see the
# resolved commit, the refusals, and the plan against a live stack. The
# verifications that can only follow a mutation say they were skipped
# rather than passing vacuously.
change() {
  if [ -n "$DRY" ]; then
    printf '   would: %s\n' "$1"
    return 1
  fi
  return 0
}
skipped() { printf '   skipped in dry run: %s\n' "$*"; }

# -- the fence, in the tool rather than in somebody's memory --
#
# A production stack is not a thing to deploy to by having typed the
# right project name. The variable is the founder's own act: nothing in
# any lane's environment sets it, so no automation and no half-remembered
# command line can reach production without a person deciding to.
case "$PROJECT" in
  aura-prod*)
    [ "${AURA_DEPLOY_CONFIRM:-}" = "yes" ] || die \
      "refusing to deploy to $PROJECT without AURA_DEPLOY_CONFIRM=yes - this is production"
    ;;
esac

step "Stack"
docker ps --format '{{.Names}}' | grep -qx "$CONTAINER" \
  || die "$CONTAINER is not running - start the stack first"
ok "$CONTAINER is up, site $SITE"

# -- what we are deploying, and whether we are allowed to --

# **$REPO has to be the repo the container mounts, not merely a copy of
# it.** The app clone's remote points at /workspace/repo, so a commit
# fetched into some other checkout is a commit the container cannot see -
# and the failure is a `couldn't find remote ref` three steps later,
# which reads like a bad branch name rather than a wrong directory.
# Found by running this with $REPO pointing at the wrong clone.
step "Repo"
# Compared by inode, because paths cannot be compared across a mount:
# inside the container it is always /workspace/repo whatever it is
# outside. A bind mount is the same file on the same host, so the inode
# matches; a different clone's does not. (My first attempt compared
# basenames and refused every invocation, including the correct one.)
MOUNTED=$(inside "stat -c %i /workspace/repo/.git/HEAD 2>/dev/null" | tr -d '\r')
HERE=$(stat -c %i "$(git -C "$REPO" rev-parse --absolute-git-dir)/HEAD" 2>/dev/null || echo "")
if [ -n "$MOUNTED" ] && [ -n "$HERE" ] && [ "$MOUNTED" != "$HERE" ]; then
  die "$CONTAINER does not mount $REPO - set AURA_DEPLOY_REPO to the repo the stack was started from"
fi
ok "$REPO is what the container mounts"

step "Resolving $REF"
git -C "$REPO" fetch --quiet origin || die "could not fetch origin in $REPO"
TARGET=$(git -C "$REPO" rev-parse --verify "$REF^{commit}" 2>/dev/null) \
  || die "$REF does not resolve in $REPO - has it been pushed?"
ok "$REF is ${TARGET:0:12}"

# The refusal that makes this a deployment rather than a copy. A commit
# that is not on the deploy ref is not reviewable, not reachable by name
# from another machine, and not recoverable if this box is lost.
git -C "$REPO" rev-parse --verify "$GATE^{commit}" >/dev/null 2>&1 \
  || die "$GATE does not resolve in $REPO - the gate must be an origin ref"
git -C "$REPO" merge-base --is-ancestor "$TARGET" "$GATE" \
  || die "${TARGET:0:12} is not contained in $GATE - prod runs only what origin has"
ok "contained in $GATE"

# The container's clone has this host checkout as its origin - `bench
# get-app auraos /workspace/repo`, and compose mounts `..` there. So the
# commit has to exist *here* before the container can fetch it, and it
# has to be reachable from a branch the container's fetch will advertise:
# fetching a bare sha from a non-bare repo is not something git promises.
BRANCH="${GATE#origin/}"
git -C "$REPO" fetch --quiet origin "$BRANCH:refs/heads/$BRANCH" 2>/dev/null || true
# Verified rather than assumed: the fetch above is refused outright when
# $BRANCH is the branch this checkout has open, which is the normal case
# on a box where somebody works. So the question is not whether the fetch
# succeeded - it is whether the commit is reachable from the local
# branch, because that is the only thing the container will be able to
# fetch.
git -C "$REPO" merge-base --is-ancestor "$TARGET" "$BRANCH" 2>/dev/null \
  || die "$REPO's local $BRANCH does not contain ${TARGET:0:12} - run: git -C $REPO pull --ff-only origin $BRANCH"
ok "local $BRANCH carries the commit"

# **A dirty clone stops the deploy before it starts.** Git would refuse
# the checkout anyway, three steps in, with its own message about
# overwriting local changes - but by then the run has already fetched and
# the operator is reading git's words rather than an instruction. And
# refusing is right: uncommitted files in a production app directory are
# either somebody's emergency edit or the wreckage of a failed deploy,
# and a deploy script is not the thing that should decide which.
step "Working tree"
DIRT=$(inside "cd $APP_DIR && git status --porcelain" | tr -d '\r')
if [ -n "$DIRT" ]; then
  printf '%s\n' "$DIRT" | sed 's/^/     /'
  die "the app clone in $CONTAINER has uncommitted changes - a deploy will not discard them"
fi
ok "the app clone is clean"

step "Current version"
FROM=$(inside "cd $APP_DIR && git rev-parse HEAD" | tr -d '\r')
if [ "$FROM" = "$TARGET" ]; then
  ok "already at ${TARGET:0:12} - re-running the checks, building only if the build is stale"
else
  ok "at ${FROM:0:12}, deploying ${TARGET:0:12}"
fi

# -- the app itself --

step "Updating the app clone"
# **The remote is discovered, not assumed.** `bench get-app` names it
# `upstream`, not `origin`, and narrows its fetch refspec to the single
# branch the app was installed from - so `git fetch origin` fails outright
# and a bare `git fetch` would bring back one branch that is probably not
# the one being deployed. Both were found by running this against a real
# stack; neither is visible from the host.
REMOTE=$(inside "cd $APP_DIR && git remote | head -1" | tr -d '\r')
[ -n "$REMOTE" ] || die "the app clone in $CONTAINER has no remote to fetch from"
ok "fetching from '$REMOTE' inside the container"

if change "check out ${TARGET:0:12} in $CONTAINER"; then
  inside "cd $APP_DIR && git fetch --quiet $REMOTE $BRANCH && git checkout --quiet --detach $TARGET" \
    || die "could not check out ${TARGET:0:12} inside $CONTAINER"
  AT=$(inside "cd $APP_DIR && git rev-parse HEAD" | tr -d '\r')
  [ "$AT" = "$TARGET" ] || die "clone is at ${AT:0:12}, not ${TARGET:0:12}"
  ok "clone is at ${TARGET:0:12}"
else
  skipped "verifying the clone moved"
fi

# -- the frontend --
#
# Built **inside** the container, where the bench user owns everything.
# The alternative - build on the host, copy the assets in - is what left
# root-owned files in the app directory and needed a chown to repair. A
# step that must be followed by a repair is a step with a defect in it.
step "Frontend"
PAGE="$APP_DIR/auraos/www/aura-next.html"
COMMIT_EPOCH=$(git -C "$REPO" show -s --format=%ct "$TARGET")
BUILT_EPOCH=$(inside "stat -c %Y $PAGE 2>/dev/null || echo 0" | tr -d '\r')
if [ "$BUILT_EPOCH" -gt "$COMMIT_EPOCH" ]; then
  ok "built page is newer than the commit - nothing to rebuild"
else
  if change "build the frontend in $CONTAINER"; then
    # **`npm ci`, not `npm install`.** `npm install` rewrites
    # package-lock.json whenever npm's resolution metadata differs from
    # what is committed, and it writes it *inside the app clone* - which
    # the Working tree step above then refuses, because a deploy will not
    # discard changes it cannot know the origin of. So a deploy that used
    # `npm install` armed the check that blocks the next one. That is not
    # a hypothesis: the first dry run against aura-prod stopped on exactly
    # this, a `frontend/package-lock.json` left behind by an earlier build
    # of the Vue app.
    #
    # `npm ci` installs from the lockfile and never writes to it, which is
    # also the reproducible install a deploy wants - the same command CI
    # already uses. It refuses outright when package.json and the lockfile
    # disagree, and that refusal is wanted here too: a lockfile out of step
    # with its manifest is a thing to fix in a commit, not to paper over on
    # a production box.
    inside "cd $APP_DIR/frontend-react && npm ci --no-audit --no-fund && npm run build" \
      || die "the frontend build failed - the stack is still serving the previous page"
  fi
  # The check that catches a build which ran and produced nothing: the
  # page has to be newer than the commit it was built from. A build that
  # silently no-ops leaves yesterday's page and a zero exit status.
  if [ -n "$DRY" ]; then
    skipped "checking the built page is newer than the commit"
  else
    BUILT_EPOCH=$(inside "stat -c %Y $PAGE 2>/dev/null || echo 0" | tr -d '\r')
    [ "$BUILT_EPOCH" -gt "$COMMIT_EPOCH" ] \
      || die "the built page is not newer than ${TARGET:0:12} - the build produced nothing"
    ok "rebuilt from ${TARGET:0:12}"
  fi
fi

# Without this the built page 404s its own assets. init.sh makes it on
# boot; a deploy that never restarts must make it too.
if change "relink sites/assets/auraos"; then
  inside "mkdir -p $BENCH_DIR/sites/assets && ln -sfn $APP_DIR/auraos/public $BENCH_DIR/sites/assets/auraos"
  ok "assets link in place"
fi

# -- the database --

step "Migrating $SITE"
if change "bench --site $SITE migrate"; then
  inside "cd $BENCH_DIR && bench --site $SITE migrate" || die "bench migrate failed - see the output above"
  ok "migrate finished"
  inside "cd $BENCH_DIR && bench --site $SITE clear-cache" >/dev/null
  ok "cache cleared"
fi

# -- the process --

step "Restarting"
if ! change "docker restart $CONTAINER, then wait for $URL"; then
  skipped "the restart and every check after it"
  printf '\nDry run only. Nothing was changed.\n'
  exit 0
fi
docker restart "$CONTAINER" >/dev/null || die "could not restart $CONTAINER"
ready=false
for _ in $(seq 1 120); do
  if curl --fail --silent --output /dev/null --max-time 5 "$URL/api/method/ping"; then
    ready=true
    break
  fi
  sleep 2
done
[ "$ready" = true ] || die "$URL never answered ping after the restart - the stack is down"
ok "$URL answers"

# The page the founder actually opens, asked for rather than assumed:
# a site can answer ping while serving a 404 at the app's own route.
curl --fail --silent --output /dev/null --max-time 20 "$URL/aura-next" \
  || die "$URL/aura-next does not render - the site is up and the app is not"
ok "$URL/aura-next renders"

# -- say so, where absence is legible --

step "Recording the deploy"
inside "cd $BENCH_DIR && printf '%s %s %s %s\\n' '$(date -Is)' '${FROM:0:12}' '${TARGET:0:12}' '$REF' > $MARKER"
ok "$MARKER says ${FROM:0:12} → ${TARGET:0:12}"

printf '\nDeployed %s to %s (%s), site %s\n' "${TARGET:0:12}" "$PROJECT" "$REF" "$SITE"
