#!/bin/sh
# /docker-entrypoint.d/ altındaki bu script, resmi nginx imajının entrypoint'i
# tarafından nginx başlatılmadan önce çalıştırılır. Container ENV'sinden okuyup
# /usr/share/nginx/html/config.js dosyasını yeniden yazar — böylece API base
# URL build-time değil runtime'da belirlenir.
set -eu

: "${API_BASE_URL:=https://api.eisa.com.tr}"

CONFIG_PATH="/usr/share/nginx/html/config.js"

cat > "${CONFIG_PATH}" <<EOF
window.__APP_CONFIG__ = {
  API_BASE_URL: "${API_BASE_URL}"
};
EOF

echo "[entrypoint] /config.js yazıldı (API_BASE_URL=${API_BASE_URL})"
