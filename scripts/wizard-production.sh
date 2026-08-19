#!/usr/bin/env bash
# Phase D wizard - the steps only the founder can take, in order, with
# nothing to re-explain. Run it on the docker host and follow along:
#
#   bash scripts/wizard-production.sh
#
# It interviews you for the production values, writes docker/.env.prod,
# brings the aura-prod stack up, installs the nightly backup cron, and
# prints the two snippets you paste yourself: the reverse-proxy vhost
# and the Cloudflare DNS record. It is safe to re-run - every step
# skips what already exists.
set -euo pipefail

REPO_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ENV_FILE="$REPO_DIR/docker/.env.prod"
COMPOSE=(docker compose --project-name aura-prod
  --file "$REPO_DIR/docker/compose.yaml"
  --file "$REPO_DIR/docker/compose.prod.yaml"
  --env-file "$ENV_FILE")

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }
ask() { # ask "prompt" default -> $REPLY
  local prompt="$1" default="${2:-}"
  if [ -n "$default" ]; then
    read -r -p "$prompt [$default]: " REPLY
    REPLY="${REPLY:-$default}"
  else
    read -r -p "$prompt: " REPLY
  fi
}

say "1/6 · Production values"
if [ -f "$ENV_FILE" ]; then
  echo "docker/.env.prod already exists - reusing it. Delete it to start over."
else
  ask "Public domain (also the site name)" ""
  domain="$REPLY"
  [ -n "$domain" ] || { echo "A domain is required."; exit 1; }
  ask "Web port on this host" 8100
  web_port="$REPLY"
  ask "Socketio port on this host" 9100
  socket_port="$REPLY"
  db_pw=$(openssl rand -hex 16)
  admin_pw=$(openssl rand -hex 8)
  cat > "$ENV_FILE" <<ENV
AURA_SITE=$domain
AURA_WEB_PORT=$web_port
AURA_SOCKET_PORT=$socket_port
AURA_VITE_PORT=$((web_port + 80))
AURA_DB_ROOT_PW=$db_pw
AURA_ADMIN_PW=$admin_pw
ENV
  chmod 600 "$ENV_FILE"
  echo "Wrote docker/.env.prod (Administrator password: $admin_pw - store it in your password manager NOW)."
fi
# shellcheck disable=SC1090
source "$ENV_FILE"

say "2/6 · Bring the aura-prod stack up"
"${COMPOSE[@]}" up --detach
echo "First boot initialises a fresh bench + site '$AURA_SITE' - this can take several minutes."
echo "Waiting for the site to answer..."
for _ in $(seq 1 900); do
  if curl --fail --silent --output /dev/null "http://127.0.0.1:$AURA_WEB_PORT/api/method/ping"; then
    echo "Site is up: http://$(hostname -I | awk '{print $1}'):$AURA_WEB_PORT"
    break
  fi
  sleep 2
done

say "3/6 · Reverse-proxy vhost (paste into YOUR proxy, then reload it)"
cat <<SNIPPET
# --- nginx ---
server {
    server_name $AURA_SITE;
    location /socket.io {
        proxy_pass http://127.0.0.1:$AURA_SOCKET_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
    }
    location / {
        proxy_pass http://127.0.0.1:$AURA_WEB_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
# --- caddy equivalent ---
# $AURA_SITE {
#     reverse_proxy /socket.io/* 127.0.0.1:$AURA_SOCKET_PORT
#     reverse_proxy 127.0.0.1:$AURA_WEB_PORT
# }
SNIPPET
read -r -p "Press Enter once the proxy vhost is in place..."

say "4/6 · Cloudflare"
cat <<TEXT
In the Cloudflare dashboard for your zone:
  - DNS: A (or CNAME) record '$AURA_SITE' → your proxy's public IP, proxied (orange cloud).
  - SSL/TLS mode: Full (strict if your proxy has a valid cert).
Then https://$AURA_SITE should show the login page (Administrator + the password from step 1).
TEXT
read -r -p "Press Enter once https://$AURA_SITE answers..."

say "5/6 · Nightly backup + offsite"
ask "Offsite target (mounted Synology path or user@nas:/path; empty = decide later)" ""
offsite="$REPLY"
backup_env="AURA_BACKUP_PROJECT=aura-prod AURA_BACKUP_SITE=$AURA_SITE AURA_BACKUP_DEST=/var/backups/auraos"
[ -n "$offsite" ] && backup_env="$backup_env AURA_BACKUP_OFFSITE=$offsite"
cron_line="30 2 * * * $backup_env $REPO_DIR/scripts/backup.sh >> /var/backups/auraos/cron.log 2>&1"
if crontab -l 2>/dev/null | grep -qF "scripts/backup.sh"; then
  echo "A backup cron line already exists - leaving it alone."
else
  (crontab -l 2>/dev/null; echo "$cron_line") | crontab -
  echo "Installed: $cron_line"
fi
echo "Run the first backup + restore proof now:"
echo "  $backup_env $REPO_DIR/scripts/backup.sh"
echo "  AURA_BACKUP_PROJECT=aura-prod AURA_BACKUP_DEST=/var/backups/auraos AURA_DB_ROOT_PW=\$AURA_DB_ROOT_PW $REPO_DIR/scripts/restore-test.sh"

say "6/6 · Settings the new site does NOT inherit"
cat <<TEXT
Frappe never migrates Single defaults - on https://$AURA_SITE/aura-next/settings
enter these by hand (the go-live checklist, issue #67):
  - Global margin floor %: 20
  - Quote silence nudge: 5 days
  - Payment terms: 7 days
  - Tier thresholds: 50.000.000 / 200.000.000 (or your current numbers)
  - Positioning mix targets + positioning-segment job types: as on dev
  - Company identity block (logo, tax code, bank) - the quote letterhead
Done. Phase D's walkthrough file records the GO.
TEXT
