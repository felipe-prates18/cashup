#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/cashup"
SERVICE_FILE="/etc/systemd/system/cashup.service"

mkdir -p "$APP_DIR"
rsync -a --delete /workspace/CashUp/ "$APP_DIR/"

cd "$APP_DIR/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python scripts/init_db.py

cd "$APP_DIR/frontend"
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
WorkingDirectory=$APP_DIR/backend
Environment=PATH=$APP_DIR/backend/.venv/bin
ExecStart=$APP_DIR/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 9020
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable cashup.service
systemctl restart cashup.service

echo "CashUp disponível em http://localhost:9020"
