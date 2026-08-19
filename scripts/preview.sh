#!/usr/bin/env bash
# Preview stacks: one throwaway environment per ticket, for a human to
# click through. See docs/adr/0001-development-moves-onto-the-proxmox-box.md.
#
#   ./scripts/preview.sh up t6        # worktree + stack + seed, prints the URL
#   ./scripts/preview.sh down t6      # stack and its data, gone
#   ./scripts/preview.sh list         # what is up, and what it costs
#
# A stack is disposable by definition: everything in it can be rebuilt
# from the branch plus the seed script, so nothing here is precious.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKTREES="${AURA_WORKTREES:-$(dirname "$REPO")/aura-previews}"
STATE="${AURA_PREVIEW_STATE:-$HOME/.aura-previews}"
MAX_STACKS="${AURA_MAX_STACKS:-3}"
PRUNE_DAYS="${AURA_PRUNE_DAYS:-7}"
SITE=dev.localhost

die() { echo "error: $*" >&2; exit 1; }

# A ticket's ports are derived from its name, so its URL is stable
# across reboots and can be bookmarked. t6 -> 8006/9006/8106; a name
# without a number falls back to a hash, which is stable too.
port_offset() {
    local ticket=$1 digits
    digits="$(printf '%s' "$ticket" | tr -cd '0-9')"
    if [ -n "$digits" ] && [ "$digits" -ge 1 ] && [ "$digits" -le 99 ]; then
        printf '%s' "$digits"
    else
        printf '%s' "$(( ( $(printf '%s' "$ticket" | cksum | cut -d' ' -f1) % 89 ) + 10 ))"
    fi
}

project() { printf 'aura-%s' "$1"; }
worktree() { printf '%s/%s' "$WORKTREES" "$1"; }
stamp_file() { printf '%s/%s' "$STATE" "$1"; }

running_stacks() {
    docker compose ls --format json 2>/dev/null \
        | grep -o '"Name":"aura-[^"]*"' | cut -d'"' -f4 | sed 's/^aura-//' || true
}

touch_stamp() { mkdir -p "$STATE"; date +%s > "$(stamp_file "$1")"; }

last_used() {
    local f; f="$(stamp_file "$1")"
    [ -f "$f" ] && cat "$f" || echo 0
}

compose() {
    local ticket=$1; shift
    local n; n="$(port_offset "$ticket")"
    AURA_WEB_PORT="$(( 8000 + n ))" \
    AURA_SOCKET_PORT="$(( 9000 + n ))" \
    AURA_VITE_PORT="$(( 8100 + n ))" \
    docker compose -p "$(project "$ticket")" \
        -f "$(worktree "$ticket")/docker/compose.yaml" "$@"
}

# Stacks nobody has touched in PRUNE_DAYS are gone when the next one
# boots - an abandoned branch cannot hold a slot forever.
prune_stale() {
    local now cutoff ticket
    now="$(date +%s)"
    cutoff="$(( now - PRUNE_DAYS * 86400 ))"
    for ticket in $(running_stacks); do
        if [ "$(last_used "$ticket")" -lt "$cutoff" ]; then
            echo "pruning $ticket (untouched for over $PRUNE_DAYS days)"
            down "$ticket"
        fi
    done
}

# Three stacks is what the box's RAM carries. A fourth stops the
# least-recently-used one rather than refusing: a stopped stack keeps
# its volume, so bringing it back is seconds, not a rebuild.
evict_if_needed() {
    local keep=$1 count oldest oldest_time t
    count="$(running_stacks | grep -vcx "$keep" || true)"
    while [ "$count" -ge "$MAX_STACKS" ]; do
        oldest=""; oldest_time=""
        for t in $(running_stacks); do
            [ "$t" = "$keep" ] && continue
            if [ -z "$oldest_time" ] || [ "$(last_used "$t")" -lt "$oldest_time" ]; then
                oldest="$t"; oldest_time="$(last_used "$t")"
            fi
        done
        [ -z "$oldest" ] && break
        echo "stopping $oldest to make room (restart it with: $0 up $oldest)"
        compose "$oldest" stop >/dev/null
        count="$(( count - 1 ))"
    done
}

up() {
    local ticket=${1:-} branch=${2:-}
    [ -n "$ticket" ] || die "usage: $0 up <ticket> [branch]"
    branch="${branch:-$ticket}"
    local wt n
    wt="$(worktree "$ticket")"
    n="$(port_offset "$ticket")"

    prune_stale
    evict_if_needed "$ticket"

    if [ ! -d "$wt" ]; then
        mkdir -p "$WORKTREES"
        # A full clone, not a git worktree: `bench get-app` inside the
        # container runs `git clone /workspace/repo`, and a linked
        # worktree's .git is a *file* pointing at the parent repo's
        # object store - which isn't mounted in there, so the clone
        # fails. A standalone clone carries its own objects.
        local url; url="$(git -C "$REPO" remote get-url origin)"
        git clone --quiet --branch "$branch" "$url" "$wt" \
            || die "no branch $branch on origin - push it first"
    fi

    echo "booting $ticket on :$(( 8000 + n )) (first boot takes a few minutes)"
    compose "$ticket" up -d
    touch_stamp "$ticket"

    echo "waiting for the site to answer…"
    local tries=0
    until curl -sf -o /dev/null "http://localhost:$(( 8000 + n ))/api/method/ping"; do
        tries=$(( tries + 1 ))
        [ "$tries" -gt 180 ] && die "site did not come up; try: $0 logs $ticket"
        sleep 5
    done

    compose "$ticket" exec -T frappe bash -lc \
        "cd /home/frappe/frappe-bench && bench --site $SITE migrate" >/dev/null
    seed "$ticket"

    echo
    echo "  $ticket → http://$(hostname -I | awk '{print $1}'):$(( 8000 + n ))/aura-next"
    echo "  login Administrator / admin"
}

# Seed data belongs to the branch: the ticket that adds a feature is the
# only thing that knows what data makes it visible, so it ships its seed
# in the same commit. Branches without one simply start empty.
seed() {
    local ticket=${1:-} out
    [ -n "$ticket" ] || die "usage: $0 seed <ticket>"
    # Piped into `console`, not `bench execute`: execute evals the dotted
    # path against its own module globals, where `auraos` is not a name.
    out="$(compose "$ticket" exec -T frappe bash -lc \
        "cd /home/frappe/frappe-bench && echo 'from auraos.setup.seed import run; run()' \
         | bench --site $SITE console" 2>&1 || true)"

    if grep -q "seed complete" <<<"$out"; then
        echo "seeded"
    elif grep -qE "No module named .auraos.setup.seed|ModuleNotFoundError" <<<"$out"; then
        echo "no seed on this branch - starting empty"
    else
        # Never swallow a real failure into "no seed": an empty preview
        # you cannot explain is worse than a loud error.
        echo "seed FAILED:"
        printf '%s\n' "$out" | tail -15
    fi
}

down() {
    local ticket=${1:-}
    [ -n "$ticket" ] || die "usage: $0 down <ticket>"
    compose "$ticket" down -v --remove-orphans >/dev/null 2>&1 || true
    rm -f "$(stamp_file "$ticket")"
    rm -rf "$(worktree "$ticket")"
    echo "$ticket is gone"
}

list() {
    local ticket n
    printf '%-12s %-8s %-24s %s\n' TICKET PORT URL 'LAST USED'
    for ticket in $(running_stacks); do
        n="$(port_offset "$ticket")"
        printf '%-12s %-8s %-24s %s\n' \
            "$ticket" "$(( 8000 + n ))" \
            "http://$(hostname -I | awk '{print $1}'):$(( 8000 + n ))/aura-next" \
            "$(date -d "@$(last_used "$ticket")" '+%Y-%m-%d %H:%M' 2>/dev/null || echo unknown)"
    done
}

logs() { compose "${1:?usage: $0 logs <ticket>}" logs -f frappe; }

case "${1:-}" in
    up) shift; up "$@" ;;
    down) shift; down "$@" ;;
    seed) shift; seed "$@" ;;
    list) shift; list "$@" ;;
    logs) shift; logs "$@" ;;
    *) die "usage: $0 {up|down|seed|list|logs} [ticket]" ;;
esac
