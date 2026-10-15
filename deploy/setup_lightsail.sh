#!/usr/bin/env bash
# Instalación de NutriPAE en una instancia Lightsail (Ubuntu 22.04/24.04, plan de 12 USD = 2 GB RAM).
# Uso (como usuario ubuntu, con el repo ya clonado en /home/ubuntu/nutripae):
#   chmod +x deploy/setup_lightsail.sh && sudo deploy/setup_lightsail.sh [dominio-o-IP]
set -euo pipefail

APP_DIR="/home/ubuntu/nutripae"
APP_USER="ubuntu"
SERVER_NAME="${1:-_}"

echo "▶ Paquetes del sistema"
apt-get update -y
apt-get install -y python3-venv python3-pip nginx git

echo "▶ Entorno virtual"
sudo -u "$APP_USER" bash -c "
  cd $APP_DIR
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt
  .venv/bin/pip install anthropic google-genai
  [ -f .env ] || cp .env.example .env
  mkdir -p data
"

echo "▶ Servicio systemd"
cp "$APP_DIR/deploy/nutripae.service" /etc/systemd/system/nutripae.service
systemctl daemon-reload
systemctl enable --now nutripae

echo "▶ Nginx (proxy con WebSockets)"
sed "s/SERVER_NAME/$SERVER_NAME/" "$APP_DIR/deploy/nginx.conf" > /etc/nginx/sites-available/nutripae
ln -sf /etc/nginx/sites-available/nutripae /etc/nginx/sites-enabled/nutripae
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo
echo "✅ NutriPAE desplegado. Edita $APP_DIR/.env con tu API key y ejecuta: sudo systemctl restart nutripae"
echo "   Logs: journalctl -u nutripae -f"
echo "   HTTPS (si tienes dominio): sudo apt install certbot python3-certbot-nginx && sudo certbot --nginx -d $SERVER_NAME"
