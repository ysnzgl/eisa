# ─── Build aşaması ───────────────────────────────────────────────────────────
FROM node:20-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm ci || npm install

COPY . .
# Build-time'da API base URL gömülmez; runtime ENV'den okunur (config.js).
RUN npm run build

# ─── Runtime aşaması ─────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# nginx'i non-privileged 8080 portunda çalıştırmak için yapılandırma.
RUN apk add --no-cache curl \
    && rm -f /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker-entrypoint.sh /docker-entrypoint.d/40-runtime-config.sh

# nginx'in 8080'i bind etmesi için pid/cache dizinlerinin yazılabilir olması.
RUN chmod +x /docker-entrypoint.d/40-runtime-config.sh \
    && sed -i 's/\r$//' /docker-entrypoint.d/40-runtime-config.sh \
    && chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid

USER nginx

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8080/healthz || exit 1

# Resmi nginx imajı /docker-entrypoint.sh ile /docker-entrypoint.d/*.sh script'lerini çalıştırır.
CMD ["nginx", "-g", "daemon off;"]
