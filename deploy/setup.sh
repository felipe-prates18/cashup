#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/cashup"
SERVICE_FILE="/etc/systemd/system/cashup.service"
BACKEND_DIR=""
FRONTEND_DIR=""
SKIP_SYSTEMD=0
CASHUP_PORT="${CASHUP_PORT:-80}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

log() {
  echo "[cashup-setup] $*"
}

fail() {
  echo "[cashup-setup] ERRO: $*" >&2
  exit 1
}

require_command() {
  local cmd="$1"
  local hint="$2"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    fail "$hint"
  fi
}

for arg in "$@"; do
  case "$arg" in
    --skip-systemd)
      SKIP_SYSTEMD=1
      ;;
    *)
      fail "Argumento inválido: $arg"
      ;;
  esac
done

if [[ "$PROJECT_ROOT" != "$APP_DIR" ]]; then
  if [[ "$SKIP_SYSTEMD" -eq 1 ]]; then
    log "Modo de validação ativo fora de $APP_DIR; usando $PROJECT_ROOT apenas para checagem local"
  else
    fail "Execute este script a partir de $APP_DIR (repo clonado em /opt/cashup)."
  fi
fi

if [[ "$SKIP_SYSTEMD" -eq 0 && "${EUID:-$(id -u)}" -ne 0 ]]; then
  fail "Execute como root para criar o serviço systemd e publicar em /opt/cashup."
fi

require_command python3 "python3 não encontrado. Instale o Python 3 antes de continuar."
require_command systemctl "systemctl não encontrado. Este script requer systemd para gerenciar o serviço."

if ! python3 -m venv --help >/dev/null 2>&1; then
  fail "O módulo venv não está disponível. Instale o pacote python3-venv."
fi

if [[ ! -d "$BACKEND_DIR/app" ]]; then
  fail "Backend não encontrado em $BACKEND_DIR."
fi

if [[ ! -f "$BACKEND_DIR/requirements.txt" ]]; then
  fail "Arquivo de dependências do backend não encontrado."
fi

if [[ ! -f "$FRONTEND_DIR/package.json" ]]; then
  fail "Frontend não encontrado em $FRONTEND_DIR."
fi

log "Criando ambiente virtual do backend"
cd "$BACKEND_DIR"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

log "Inicializando banco de dados"
python scripts/init_db.py

if command -v npm >/dev/null 2>&1; then
  log "Instalando dependências e gerando build do frontend"
  cd "$FRONTEND_DIR"
  npm install
  npm run build
elif [[ -d "$FRONTEND_DIR/dist" && -f "$FRONTEND_DIR/dist/index.html" ]]; then
  log "npm não encontrado; reutilizando build existente em $FRONTEND_DIR/dist"
else
  fail "npm não encontrado e não há build prévio em $FRONTEND_DIR/dist. Instale Node.js/npm para subir a aplicação completa."
fi

if [[ ! -f "$FRONTEND_DIR/dist/index.html" ]]; then
  fail "Build do frontend não encontrado após a etapa de instalação."
fi

if [[ "$SKIP_SYSTEMD" -eq 1 ]]; then
  log "Validação concluída com --skip-systemd; serviço systemd não foi alterado."
  exit 0
fi

log "Criando/atualizando serviço systemd"
cat <<SERVICE > "$SERVICE_FILE"
[Unit]
Description=CashUp Finance Manager
After=network.target

[Service]
WorkingDirectory=$BACKEND_DIR
Environment=PATH=$BACKEND_DIR/.venv/bin
Environment=PYTHONUNBUFFERED=1
ExecStart=$BACKEND_DIR/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $CASHUP_PORT
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

log "Recarregando systemd e reiniciando serviço"
systemctl daemon-reload
systemctl enable cashup.service
systemctl restart cashup.service
systemctl --no-pager --full status cashup.service

if [[ "$CASHUP_PORT" == "80" ]]; then
  log "CashUp disponível em http://localhost"
else
  log "CashUp disponível em http://localhost:$CASHUP_PORT"
fi
log "Usuário inicial: admin@cashup.local / admin"
