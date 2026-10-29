#!/usr/bin/env bash
# Instalación de NutriPAE v2 en una instancia Lightsail (Ubuntu 22.04/24.04, plan de 12 USD = 2 GB RAM).
# Uso (con el repo ya clonado en /home/ubuntu/nutripae):
#   chmod +x deploy/setup_lightsail.sh && sudo deploy/setup_lightsail.sh midominio.edu.co
# Para crear también el primer administrador (la contraseña se lee del entorno, puede tener cualquier carácter):
#   sudo NUTRIPAE_ADMIN=admin NUTRIPAE_ADMIN_PASS='una-clave-larga' deploy/setup_lightsail.sh midominio.edu.co
# Volver a ejecutarlo no toca el sitio de Nginx (ni el bloque HTTPS de certbot) salvo con --forzar-nginx.
set -euo pipefail

APP_DIR="/home/ubuntu/nutripae"
APP_USER="ubuntu"
SERVER_NAME=""
FORZAR_NGINX=0
for arg in "$@"; do
  case "$arg" in
    --forzar-nginx) FORZAR_NGINX=1 ;;
    -*) echo "Opción desconocida: $arg" >&2; exit 2 ;;
    *) SERVER_NAME="$arg" ;;
  esac
done

echo "▶ Swap de 2 GB (torch + FastSAM usan cerca de 1 GB al analizar)"
if ! swapon --show | grep -q /swapfile; then
  [ -f /swapfile ] || fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "▶ Paquetes del sistema"
apt-get update -y
apt-get install -y python3-venv python3-pip nginx git libgl1 libglib2.0-0

echo "▶ Entorno virtual, PyTorch solo-CPU y dependencias"
# torch y torchvision juntos desde el índice CPU: así ultralytics no arrastra una versión con CUDA.
sudo -u "$APP_USER" bash -c "
  set -euo pipefail
  cd $APP_DIR
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
  .venv/bin/pip install -r requirements.txt
  [ -f .env ] || cp .env.example .env
  mkdir -p data/fotos
"

echo "▶ Cookie de sesión solo por HTTPS y clave secreta"
sudo -u "$APP_USER" bash -c "
  cd $APP_DIR
  grep -q '^NUTRIPAE_HTTPS=' .env || echo 'NUTRIPAE_HTTPS=1' >> .env
  if ! grep -q '^NUTRIPAE_SECRET=.\+' .env; then
    sed -i '/^NUTRIPAE_SECRET=/d' .env
    echo \"NUTRIPAE_SECRET=\$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')\" >> .env
  fi
"

echo "▶ Pesos de FastSAM (se descargan una sola vez)"
sudo -u "$APP_USER" bash -c "
  cd $APP_DIR
  .venv/bin/python -c 'from ultralytics import FastSAM; FastSAM(\"FastSAM-s.pt\")'
"

echo "▶ Servicio systemd (un solo proceso)"
cp "$APP_DIR/deploy/nutripae.service" /etc/systemd/system/nutripae.service
systemctl daemon-reload
systemctl enable --now nutripae
systemctl restart nutripae

echo "▶ Nginx (proxy HTTP, sin WebSockets)"
SITIO=/etc/nginx/sites-available/nutripae
if [ -f "$SITIO" ] && [ "$FORZAR_NGINX" -eq 0 ]; then
  echo "  $SITIO ya existe: no se modifica (conserva el HTTPS de certbot). Usa --forzar-nginx para reescribirlo."
else
  sed "s/SERVER_NAME/${SERVER_NAME:-_}/" "$APP_DIR/deploy/nginx.conf" > "$SITIO"
fi
ln -sf "$SITIO" /etc/nginx/sites-enabled/nutripae
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

if [ -n "${NUTRIPAE_ADMIN:-}" ] || [ -n "${NUTRIPAE_ADMIN_PASS:-}" ]; then
  echo "▶ Primer administrador"
  # Usuario y contraseña viajan por el entorno, nunca dentro de un comando armado como texto.
  if ! (cd "$APP_DIR" && sudo -u "$APP_USER" env \
        NUTRIPAE_ADMIN="${NUTRIPAE_ADMIN:-}" NUTRIPAE_ADMIN_PASS="${NUTRIPAE_ADMIN_PASS:-}" \
        .venv/bin/python -m nutripae.cli crear-admin-env); then
    echo "✖ ERROR: no se creó el administrador. Revisa el mensaje de arriba (¿faltan NUTRIPAE_ADMIN y" >&2
    echo "  NUTRIPAE_ADMIN_PASS, o el usuario ya existe?). El resto de la instalación quedó lista." >&2
    exit 1
  fi
fi

echo
echo "✅ NutriPAE instalado."
echo "   1. Edita $APP_DIR/.env con la clave de la IA de visión (OPENAI_API_KEY u otra) y reinicia:"
echo "        sudo systemctl restart nutripae"
echo "   2. HTTPS es OBLIGATORIO: sin HTTPS el navegador no deja usar la cámara."
if [ -n "$SERVER_NAME" ]; then
  echo "        sudo apt install -y certbot python3-certbot-nginx && sudo certbot --nginx -d $SERVER_NAME"
else
  echo "        Apunta un dominio a esta instancia, ejecuta de nuevo: sudo deploy/setup_lightsail.sh TU_DOMINIO --forzar-nginx"
  echo "        y luego: sudo apt install -y certbot python3-certbot-nginx && sudo certbot --nginx -d TU_DOMINIO"
fi
if [ -z "${NUTRIPAE_ADMIN:-}" ]; then
  echo "   3. Crea el primer administrador:"
  echo "        cd $APP_DIR && .venv/bin/python -m nutripae.cli crear-admin USUARIO CONTRASENA"
fi
echo "   Logs: journalctl -u nutripae -f"
