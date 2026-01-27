#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/cashup"
SERVICE_FILE="/etc/systemd/system/cashup.service"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ "$PROJECT_ROOT" != "$APP_DIR" ]]; then
  echo "Execute este script a partir de $APP_DIR (repo clonado em /opt/cashup)."
  exit 1
fi

cd "$PROJECT_ROOT/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python scripts/init_db.py

cd "$PROJECT_ROOT/frontend"
if command -v npm >/dev/null 2>&1; then
  npm install
  npm run build
else
  echo "npm not found. Install Node.js to build the frontend."
fi

cat <<SERVICE | tee "$SERVICE_FILE"
[Unit]
Description=CashUp Finance Manager
After=network.target

[Service]
WorkingDirectory=$PROJECT_ROOT/backend
Environment=PATH=$PROJECT_ROOT/backend/.venv/bin
ExecStart=$PROJECT_ROOT/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 9020
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable cashup.service
systemctl restart cashup.service

echo "CashUp disponível em http://localhost:9020"
