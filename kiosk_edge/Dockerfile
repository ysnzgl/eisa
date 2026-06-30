# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# E-İSA Kiosk Edge — Birleşik (All-in-One) Dockerfile
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# Tek container içinde hem API Node servisi hem de UI birlikte çalışır.
# - Node.js API (Fastify) → 127.0.0.1:8765 (internal)
# - Nginx → :80 (UI static + /api proxy)
# - supervisord ile iki process yönetilir.
#
# Build context: kiosk_edge/ klasörü
#   docker build -f Dockerfile -t eisa-kiosk-allinone .
#
# NOT: Sadece demo.eisa.com.tr için. Gerçek kiosk'larda native deployment.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ── Stage 1: UI Build ──
FROM node:20-alpine AS ui-build
WORKDIR /ui
COPY ui/package*.json ./
RUN npm ci
COPY ui/ .
# Relative API path → nginx /api proxy üzerinden node'a yönlenir
ENV VITE_API_BASE=""
RUN npm run build

# ── Stage 2: API Dependencies ──
FROM node:20-alpine AS api-deps
WORKDIR /api
# better-sqlite3 native derleme için build araçları
RUN apk add --no-cache python3 make g++
COPY api-node/package*.json ./
RUN npm ci --omit=dev

# ── Stage 3: Runner (Node + Nginx + supervisord) ──
FROM node:20-alpine AS runner
ENV NODE_ENV=production

# Nginx + supervisor + sqlite runtime
RUN apk add --no-cache nginx supervisor sqlite

# ── API Node ──
WORKDIR /app/api
COPY --from=api-deps /api/node_modules ./node_modules
COPY api-node/package.json ./
COPY api-node/src ./src

# Node API ortam değişkenleri (container içi)
ENV EISA_PORT=8765
ENV EISA_HOST=127.0.0.1
ENV EISA_SQLITE_PATH=/var/lib/eisa/local.db
ENV EISA_MEDIA_DIR=/var/lib/eisa/media
ENV EISA_LOG_DIR=/var/log/eisa
ENV EISA_CENTRAL_API_BASE=https://api.eisa.com.tr

# Veri / log dizinleri
RUN mkdir -p /var/lib/eisa/media /var/log/eisa /run/nginx

# ── UI static dosyaları ──
COPY --from=ui-build /ui/dist /usr/share/nginx/html

# ── Nginx config (UI + /api proxy) ──
RUN printf 'server {\n\
    listen 80;\n\
    server_name _;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
    client_max_body_size 25m;\n\
\n\
    # API proxy → Node.js (127.0.0.1:8765)\n\
    location /api/ {\n\
        proxy_pass http://127.0.0.1:8765;\n\
        proxy_http_version 1.1;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n\
        proxy_set_header X-Forwarded-Proto $scheme;\n\
        proxy_read_timeout 60s;\n\
    }\n\
\n\
    # API health check passthrough\n\
    location = /health {\n\
        proxy_pass http://127.0.0.1:8765/health;\n\
        access_log off;\n\
    }\n\
\n\
    # UI health check\n\
    location = /healthz {\n\
        access_log off;\n\
        return 200 "OK";\n\
        add_header Content-Type text/plain;\n\
    }\n\
\n\
    # SPA routing\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
}\n' > /etc/nginx/http.d/default.conf

# ── supervisord config ──
RUN printf '[supervisord]\n\
nodaemon=true\n\
user=root\n\
logfile=/var/log/supervisord.log\n\
pidfile=/run/supervisord.pid\n\
\n\
[program:api]\n\
command=node /app/api/src/index.js\n\
directory=/app/api\n\
autostart=true\n\
autorestart=true\n\
stdout_logfile=/dev/stdout\n\
stdout_logfile_maxbytes=0\n\
stderr_logfile=/dev/stderr\n\
stderr_logfile_maxbytes=0\n\
priority=10\n\
\n\
[program:nginx]\n\
command=nginx -g "daemon off;"\n\
autostart=true\n\
autorestart=true\n\
stdout_logfile=/dev/stdout\n\
stdout_logfile_maxbytes=0\n\
stderr_logfile=/dev/stderr\n\
stderr_logfile_maxbytes=0\n\
priority=20\n' > /etc/supervisord.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/healthz || exit 1

CMD ["supervisord", "-c", "/etc/supervisord.conf"]
