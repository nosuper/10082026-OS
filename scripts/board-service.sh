#!/usr/bin/env bash
# The board, served off this box and refreshed on a timer.
#
#   ./scripts/board-service.sh install     # units in, timer on, prints the URL
#   ./scripts/board-service.sh status      # is it running, when did it last build
#   ./scripts/board-service.sh refresh     # rebuild now, don't wait for the timer
#   ./scripts/board-service.sh uninstall   # units and served copy, gone
#
# Two units: a timer that re-runs scripts/board.py every five minutes, and a
# static server on the LAN. Nothing here is precious — uninstall and reinstall
# rebuilds it from this file.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVE_DIR="${AURA_BOARD_DIR:-/var/lib/aura-board}"
# Outside the preview stacks' ranges on purpose: preview.sh hands out
# 8000-8099 for web and 8100-8199 for vite.
PORT="${AURA_BOARD_PORT:-8200}"
UNITS=/etc/systemd/system

die() { echo "error: $*" >&2; exit 1; }
url() { echo "http://$(hostname -I | awk '{print $1}'):$PORT/"; }

require_root() {
    [ "$(id -u)" -eq 0 ] || die "needs root — systemd units and $SERVE_DIR"
}

install_units() {
    require_root
    command -v gh >/dev/null || die "gh is not on PATH; the board reads GitHub through it"
    mkdir -p "$SERVE_DIR"

    cat > "$UNITS/aura-board.service" <<EOF
[Unit]
Description=Rebuild the AuraOS board
Documentation=file://$REPO/scripts/board.py
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$REPO
# gh reads its token from /root/.config/gh, docker from the root socket.
Environment=HOME=/root
ExecStart=$REPO/scripts/board.py --fetch --out $SERVE_DIR/index.html
# A GitHub blip should leave the last good board up, not a half-written file.
TimeoutStartSec=180
EOF

    cat > "$UNITS/aura-board.timer" <<EOF
[Unit]
Description=Rebuild the AuraOS board every five minutes

[Timer]
OnBootSec=90s
OnUnitActiveSec=5min
# A missed window (box asleep, reboot) rebuilds on the next start.
Persistent=true
AccuracySec=30s

[Install]
WantedBy=timers.target
EOF

    cat > "$UNITS/aura-board-http.service" <<EOF
[Unit]
Description=Serve the AuraOS board on the LAN
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/python3 -m http.server $PORT --bind 0.0.0.0 --directory $SERVE_DIR
Restart=always
RestartSec=5s
# Read-only static files; it needs nothing else on this box.
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable --now aura-board.timer aura-board-http.service >/dev/null
    systemctl start aura-board.service
    echo "board → $(url)"
    echo "rebuilds every 5 min; ./scripts/board-service.sh status to check"
}

uninstall_units() {
    require_root
    systemctl disable --now aura-board.timer aura-board-http.service 2>/dev/null || true
    rm -f "$UNITS/aura-board.service" "$UNITS/aura-board.timer" \
          "$UNITS/aura-board-http.service"
    systemctl daemon-reload
    rm -rf "$SERVE_DIR"
    echo "removed: units, timer and $SERVE_DIR"
}

show_status() {
    systemctl is-active --quiet aura-board-http.service \
        && echo "serving   $(url)" \
        || echo "serving   DOWN"
    systemctl is-active --quiet aura-board.timer \
        && echo "timer     on" \
        || echo "timer     off"
    if [ -f "$SERVE_DIR/index.html" ]; then
        echo "built     $(date -r "$SERVE_DIR/index.html" '+%F %T %Z')"
    else
        echo "built     never"
    fi
    systemctl list-timers aura-board.timer --no-pager 2>/dev/null | sed -n 2p
    journalctl -u aura-board.service -n 3 --no-pager -o cat 2>/dev/null | sed 's/^/log       /'
}

case "${1:-}" in
    install)   install_units ;;
    uninstall) uninstall_units ;;
    refresh)   require_root; systemctl start aura-board.service; show_status ;;
    status)    show_status ;;
    *) sed -n '2,10p' "$0" | sed 's/^# \?//'; exit 1 ;;
esac
