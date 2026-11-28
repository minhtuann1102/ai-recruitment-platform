#!/usr/bin/env bash
# Cai dat VM staging (spec 014, T014): Docker Engine + Compose plugin, Ops Agent, thu muc /opt/ai-recruit.
# Chay TREN VM bang root (provision-gcp.sh in lenh chep + chay qua IAP). Chay lai an toan.
# Cron sao luu them o T033 (backup-postgres.sh chua co).
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "chay bang root: sudo bash $0" >&2
  exit 2
fi
export DEBIAN_FRONTEND=noninteractive
APP_DIR=/opt/ai-recruit

step() { printf '\n== %s\n' "$*"; }

step "goi he thong"
apt-get update -q
apt-get install -y -q ca-certificates curl gnupg

step "Docker Engine + Compose plugin (repo chinh thuc cua Docker)"
if command -v docker >/dev/null && docker compose version >/dev/null 2>&1; then
  echo "   exists: $(docker --version)"
else
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  # shellcheck source=/dev/null
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    >/etc/apt/sources.list.d/docker.list
  apt-get update -q
  apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
systemctl enable --now docker # container co restart: unless-stopped tu chay lai khi may khoi dong lai

step "Ops Agent (metrics + log may ve Cloud Monitoring / Logging)"
if systemctl list-unit-files google-cloud-ops-agent.service >/dev/null 2>&1 \
  && systemctl is-enabled google-cloud-ops-agent >/dev/null 2>&1; then
  echo "   exists: google-cloud-ops-agent"
else
  curl -fsSL https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh -o /tmp/add-ops-agent-repo.sh
  bash /tmp/add-ops-agent-repo.sh --also-install
  rm -f /tmp/add-ops-agent-repo.sh
fi

step "thu muc $APP_DIR (compose, Caddyfile, .env, env/, state/)"
install -d -m 0700 "$APP_DIR" "$APP_DIR/env" "$APP_DIR/state"

step "xong"
docker --version
docker compose version
systemctl is-active google-cloud-ops-agent || true
echo "   Tiep (T016): chep docker-compose.staging.yml + Caddyfile vao $APP_DIR, tao .env + env/*.env (chmod 600)"
