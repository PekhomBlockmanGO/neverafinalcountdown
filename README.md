# Nevera CMMS — VPS Deploy Guide

**Domain:** `nevera.neverno.in`  
**Stack:** Python 3.10 · Django 5.2 LTS · Gunicorn 22 · Nginx · Let's Encrypt  
**DB:** SQLite (safe for single-server, low-concurrency use)

---

## ⚡ First-Time Deploy — 3 Commands

```bash
# 1. Upload project to your VPS
scp -r nevera_final/ root@YOUR_VPS_IP:/tmp/nevera_final

# 2. SSH in and run the script
ssh root@YOUR_VPS_IP
cd /tmp/nevera_final
bash deploy/deploy.sh
```

The script handles everything automatically:  
packages → system user → venv → pip install → migrate → collectstatic → Gunicorn service → Nginx → SSL cert

```bash
# 3. Create your superuser (after deploy completes)
sudo -u nevera /home/nevera/nevera_cmms/venv/bin/python \
    /home/nevera/nevera_cmms/manage.py createsuperuser
```

---

## ✅ Pre-Deploy Checklist

| Check | Detail |
|---|---|
| VPS OS | Ubuntu 22.04 or 24.04 |
| Python | 3.10 or higher (`python3 --version`) |
| DNS A record | `nevera.neverno.in` → your server IP |
| DNS A record | `www.nevera.neverno.in` → your server IP |
| Firewall | Port 80 and 443 open |
| Root access | `ssh root@YOUR_IP` works |

---

## 🔐 After Deploy — Non-Optional Steps

### Set a real SECRET_KEY
```bash
# Generate one
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Edit the .env on the server
nano /home/nevera/nevera_cmms/.env

# Restart the app
systemctl restart nevera
```

---

## 🔄 Pushing Code Updates

```bash
# From your local machine — upload changed files
scp -r . root@YOUR_VPS_IP:/home/nevera/nevera_cmms/

# On the server — run the update script
ssh root@YOUR_VPS_IP
bash /home/nevera/nevera_cmms/deploy/update.sh
```

---

## 🗂 Server File Locations

| What | Path |
|---|---|
| App code | `/home/nevera/nevera_cmms/` |
| Virtual env | `/home/nevera/nevera_cmms/venv/` |
| **Environment file** | `/home/nevera/nevera_cmms/.env` |
| Media uploads | `/home/nevera/nevera_cmms/media/` |
| Static files | `/home/nevera/nevera_cmms/staticfiles/` |
| Django log | `/var/log/nevera/django.log` |
| Gunicorn access log | `/var/log/nevera/gunicorn-access.log` |
| Gunicorn error log | `/var/log/nevera/gunicorn-error.log` |
| Nginx config | `/etc/nginx/sites-available/nevera` |
| Systemd service | `/etc/systemd/system/nevera.service` |

---

## 🛠 Useful Commands

```bash
systemctl status nevera            # App status
journalctl -u nevera -f            # Live app logs
tail -f /var/log/nevera/django.log # Django error log
systemctl restart nevera           # Restart app
systemctl reload nginx             # Reload Nginx config
nginx -t                           # Test Nginx config syntax
certbot renew --dry-run            # Test SSL auto-renewal
```

---

## 🔁 QR Code URL Note

QR codes embed `https://nevera.neverno.in/tickets/q/<token>/`.  
They are generated once when a Location is saved.  
If you ever change your domain:

1. Update `SITE_BASE_URL` in `.env`
2. `systemctl restart nevera`
3. Django Admin → Locations → Select All → **Action: Regenerate QR codes**

---

## 🧱 Architecture

```
User browser / mobile
        │  HTTPS :443
        ▼
    [ Nginx ]  ←── serves /static/ and /media/ directly
        │  Unix socket  /run/nevera/gunicorn.sock
        ▼
  [ Gunicorn ]  3 workers
        │
  [ Django 5.2 ]
        │
  [ SQLite db.sqlite3 ]   ← stored at /home/nevera/nevera_cmms/
```

---

## 📦 Requirements Summary

| Package | Version | Why |
|---|---|---|
| Django | 5.2.1 | LTS, Python 3.10 compatible |
| gunicorn | 22.0.0 | WSGI server |
| whitenoise | 6.8.2 | Static file serving |
| python-decouple | 3.8 | .env management |
| Pillow | 10.4.0 | QR image generation |
| qrcode[pil] | 8.0 | QR code creation |
