#!/usr/bin/env bash
# =============================================================================
#  Nevera CMMS — Zero-downtime Update Script
#  Run this every time you push new code to the server.
#  Usage: bash deploy/update.sh
# =============================================================================
set -euo pipefail

GREEN='\033[0;32m'; NC='\033[0m'
info() { echo -e "${GREEN}[UPDATE]${NC} $*"; }

APP_USER="nevera"
APP_DIR="/home/${APP_USER}/nevera_cmms"
VENV="${APP_DIR}/venv"

info "Installing/upgrading Python dependencies..."
sudo -u "${APP_USER}" "${VENV}/bin/pip" install -r "${APP_DIR}/requirements.txt" -q

info "Running migrations..."
cd "${APP_DIR}"
sudo -u "${APP_USER}" "${VENV}/bin/python" manage.py migrate --noinput

info "Collecting static files..."
sudo -u "${APP_USER}" "${VENV}/bin/python" manage.py collectstatic --noinput --clear

info "Restarting Gunicorn..."
systemctl restart nevera

info "Reloading Nginx..."
systemctl reload nginx

echo ""
echo -e "${GREEN}✅  Update complete. App restarted.${NC}"
echo "   Check status: systemctl status nevera"
