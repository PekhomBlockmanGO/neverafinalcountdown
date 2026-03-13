#!/usr/bin/env bash
# =============================================================================
#  Nevera CMMS — Full VPS Deploy Script
#  Target : Ubuntu 22.04 / 24.04
#  Domain : nevera.neverno.in
#  Stack  : Python 3.10+ | Django 5.2 LTS | Gunicorn | Nginx | Certbot SSL
#  Run as : root  (or:  sudo -i  first)
#  Usage  : bash deploy/deploy.sh
# =============================================================================
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
step()    { echo -e "\n${CYAN}══════════════════════════════════════════${NC}"; echo -e "${CYAN}  $*${NC}"; echo -e "${CYAN}══════════════════════════════════════════${NC}"; }

DOMAIN="nevera.neverno.in"
APP_USER="nevera"
APP_DIR="/home/${APP_USER}/nevera_cmms"
VENV_DIR="${APP_DIR}/venv"
LOG_DIR="/var/log/nevera"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "${SCRIPT_DIR}")"

# =============================================================================
# PREFLIGHT CHECKS
# =============================================================================
step "Preflight checks"

[ "$(id -u)" -eq 0 ] || error "Run this script as root (sudo -i first)."

# Python version check — need 3.10+
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")

info "Detected Python ${PY_VER}"
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    error "Python 3.10+ required. This server has Python ${PY_VER}. Install it first:
    sudo apt install python3.10 python3.10-venv python3.10-dev"
fi
info "Python version OK ✓"

# =============================================================================
# STEP 1 — System packages
# =============================================================================
step "Step 1/9 — Installing system packages"
apt-get update -qq
apt-get install -y -qq \
    python3 python3-pip python3-venv python3-dev \
    nginx certbot python3-certbot-nginx \
    git curl build-essential \
    libjpeg-dev zlib1g-dev libpng-dev \
    libfreetype6-dev
info "System packages installed ✓"

# =============================================================================
# STEP 2 — Create dedicated app user
# =============================================================================
step "Step 2/9 — App system user"
if ! id "${APP_USER}" &>/dev/null; then
    adduser --system --group --shell /bin/bash --home "/home/${APP_USER}" "${APP_USER}"
    info "User '${APP_USER}' created ✓"
else
    info "User '${APP_USER}' already exists — skipping"
fi
usermod -aG www-data "${APP_USER}"

# =============================================================================
# STEP 3 — Deploy application files
# =============================================================================
step "Step 3/9 — Copying application files to ${APP_DIR}"
mkdir -p "${APP_DIR}"
rsync -a \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='staticfiles/' \
    --exclude='db.sqlite3' \
    --exclude='media/' \
    --exclude='.env' \
    "${REPO_ROOT}/" "${APP_DIR}/"

chown -R "${APP_USER}:www-data" "${APP_DIR}"
chmod -R 750 "${APP_DIR}"
info "Files deployed ✓"

# =============================================================================
# STEP 4 — Python virtual environment + pip install
# =============================================================================
step "Step 4/9 — Python virtual environment & dependencies"
sudo -u "${APP_USER}" python3 -m venv "${VENV_DIR}"
sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install --upgrade pip --quiet

info "Installing requirements (this may take 1–2 minutes)..."
sudo -u "${APP_USER}" "${VENV_DIR}/bin/pip" install \
    -r "${APP_DIR}/requirements.txt" \
    --quiet \
    || error "pip install failed. Check requirements.txt and Python version compatibility."

info "Dependencies installed ✓"
# Print installed Django version as confirmation
DJANGO_VER=$(sudo -u "${APP_USER}" "${VENV_DIR}/bin/python" -c "import django; print(django.__version__)")
info "Django ${DJANGO_VER} active ✓"

# =============================================================================
# STEP 5 — Environment file
# =============================================================================
step "Step 5/9 — Environment configuration"
if [ ! -f "${APP_DIR}/.env" ]; then
    cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
    warn "┌─────────────────────────────────────────────────────────────┐"
    warn "│  .env created from template. YOU MUST SET SECRET_KEY NOW.   │"
    warn "│  Run:  nano ${APP_DIR}/.env                       │"
    warn "│  Generate key:                                               │"
    warn "│  python3 -c \"from django.core.management.utils import       │"
    warn "│  get_random_secret_key; print(get_random_secret_key())\"     │"
    warn "└─────────────────────────────────────────────────────────────┘"
else
    info ".env already exists — not overwriting ✓"
fi
chmod 600 "${APP_DIR}/.env"
chown "${APP_USER}:${APP_USER}" "${APP_DIR}/.env"

# =============================================================================
# STEP 6 — Directories, migrate, collectstatic
# =============================================================================
step "Step 6/9 — Django setup (migrate + collectstatic)"
mkdir -p "${LOG_DIR}"
chown "${APP_USER}:www-data" "${LOG_DIR}"
chmod 775 "${LOG_DIR}"

mkdir -p "${APP_DIR}/media" "${APP_DIR}/staticfiles"
chown -R "${APP_USER}:www-data" "${APP_DIR}/media" "${APP_DIR}/staticfiles"

cd "${APP_DIR}"
sudo -u "${APP_USER}" "${VENV_DIR}/bin/python" manage.py migrate --noinput
sudo -u "${APP_USER}" "${VENV_DIR}/bin/python" manage.py collectstatic --noinput --clear
info "Django setup complete ✓"

# =============================================================================
# STEP 7 — Gunicorn systemd service
# =============================================================================
step "Step 7/9 — Gunicorn systemd service"
cp "${APP_DIR}/deploy/nevera.service" /etc/systemd/system/nevera.service
systemctl daemon-reload
systemctl enable nevera
systemctl restart nevera
sleep 3

if systemctl is-active --quiet nevera; then
    info "Gunicorn service running ✓"
else
    journalctl -u nevera -n 20 --no-pager
    error "Gunicorn failed to start — see logs above."
fi

# =============================================================================
# STEP 8 — Nginx
# =============================================================================
step "Step 8/9 — Nginx configuration"
cp "${APP_DIR}/deploy/nevera_nginx.conf" /etc/nginx/sites-available/nevera
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/nevera /etc/nginx/sites-enabled/nevera

nginx -t || error "Nginx config syntax error — check /etc/nginx/sites-available/nevera"
systemctl restart nginx
info "Nginx running ✓"

# =============================================================================
# STEP 9 — SSL (Let's Encrypt / Certbot)
# =============================================================================
step "Step 9/9 — SSL certificate (Let's Encrypt)"
warn "DNS check: ${DOMAIN} must already point to this server's public IP."
warn "If DNS is not ready yet, skip SSL now and run certbot manually later."
echo ""
read -rp "  Is DNS ready? (y to get SSL now, n to skip): " SSL_READY

if [[ "${SSL_READY,,}" == "y" ]]; then
    certbot --nginx \
        -d "${DOMAIN}" \
        -d "www.${DOMAIN}" \
        --non-interactive \
        --agree-tos \
        --email "admin@neverno.in" \
        --redirect \
        --keep-until-expiring
    systemctl reload nginx
    info "SSL certificate installed ✓"
    PROTOCOL="https"
else
    warn "SSL skipped. When DNS is ready, run:"
    warn "  certbot --nginx -d ${DOMAIN} -d www.${DOMAIN} --agree-tos --email admin@neverno.in --redirect"
    PROTOCOL="http"
fi

# =============================================================================
# DONE
# =============================================================================
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅  Deploy complete!  →  ${PROTOCOL}://${DOMAIN}${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${YELLOW}REQUIRED NEXT STEPS:${NC}"
echo ""
echo "  1. Set a real SECRET_KEY in .env (⚠ DO THIS BEFORE USING THE APP):"
echo "     nano ${APP_DIR}/.env"
echo "     systemctl restart nevera"
echo ""
echo "  2. Create your superuser:"
echo "     sudo -u ${APP_USER} ${VENV_DIR}/bin/python ${APP_DIR}/manage.py createsuperuser"
echo ""
echo "  3. Open the app:"
echo "     ${PROTOCOL}://${DOMAIN}/dashboard/"
echo "     ${PROTOCOL}://${DOMAIN}/admin/"
echo ""
echo "  Useful commands:"
echo "  ├─ Live app logs    : journalctl -u nevera -f"
echo "  ├─ Django log       : tail -f ${LOG_DIR}/django.log"
echo "  ├─ Restart app      : systemctl restart nevera"
echo "  ├─ Nginx reload     : systemctl reload nginx"
echo "  └─ SSL renew test   : certbot renew --dry-run"
echo ""
