# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# E-İSA Kiosk Edge — Birleşik (All-in-One) Dockerfile
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# Tek container içinde hem API Node servisi hem de UI birlikte çalışır.
# - Node.js API (Fastify) → 127.0.0.1:8765
# - Nginx → :80
# - supervisord ile iki process yönetilir.
#
# NOT: Sadece demo.eisa.com.tr için. Gerçek kiosk'larda native deployment.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ── Stage 1: UI Build ────────────────────────────────────────────────
FROM node:20-alpine AS ui-build

WORKDIR /ui

COPY ui/package*.json ./
RUN npm ci

COPY ui/ .

# UI, aynı container içindeki Node API'ye Nginx /api proxy'si üzerinden gider.
ENV VITE_API_BASE=""

RUN npm run build


# ── Stage 2: API Dependencies ────────────────────────────────────────
FROM node:20-alpine AS api-deps

WORKDIR /api

# better-sqlite3 native derleme araçları
RUN apk add --no-cache python3 make g++

COPY api-node/package*.json ./
RUN npm ci --omit=dev


# ── Stage 3: Runner ──────────────────────────────────────────────────
FROM node:20-alpine AS runner

ENV NODE_ENV=production

# Nginx + supervisor + sqlite runtime
RUN apk add --no-cache nginx supervisor sqlite

# ── API Node ─────────────────────────────────────────────────────────
WORKDIR /app/api

COPY --from=api-deps /api/node_modules ./node_modules
COPY api-node/package.json ./
COPY api-node/src ./src

ENV EISA_PORT=8765
ENV EISA_HOST=127.0.0.1
ENV EISA_SQLITE_PATH=/var/lib/eisa/local.db
ENV EISA_MEDIA_DIR=/var/lib/eisa/media
ENV LOG_FORMAT=json
ENV LOG_LEVEL=info
ENV SERVICE_NAME=eisa-kiosk-api

# Node doğrudan merkezi API'ye değil, aynı container'daki Nginx proxy'sine gider.
ENV EISA_CENTRAL_API_BASE=http://127.0.0.1/_central-api

# Sadece veri ve Nginx runtime dizinleri; log dosyasi olusturulmuyor.
RUN mkdir -p \
    /var/lib/eisa/media \
    /run/nginx \
    /var/lib/nginx/logs \
    /var/lib/nginx/tmp/client_body \
    /var/lib/nginx/tmp/proxy \
    /var/lib/nginx/tmp/fastcgi \
    /var/lib/nginx/tmp/uwsgi \
    /var/lib/nginx/tmp/scgi

# ── UI static dosyaları ──────────────────────────────────────────────
COPY --from=ui-build /ui/dist /usr/share/nginx/html

# ── Nginx config ─────────────────────────────────────────────────────
RUN printf 'server {\n\
    listen 80;\n\
    server_name _;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
    client_max_body_size 25m;\n\
\n\
    # UI istekleri -> container icindeki Node API\n\
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
    # Node API -> Kubernetes icindeki merkezi E-ISA API\n\
    # Yalnizca ayni container icinden erisilebilir.\n\
    location /_central-api/ {\n\
        allow 127.0.0.1;\n\
        allow ::1;\n\
        deny all;\n\
\n\
        # Sondaki slash, /_central-api/ prefixini kaldirir.\n\
        proxy_pass http://eisa-api/;\n\
        proxy_http_version 1.1;\n\
\n\
        # Django istegi HTTPS arkasindan gelmis olarak kabul eder.\n\
        proxy_set_header Host api.eisa.com.tr;\n\
        proxy_set_header X-Forwarded-Proto https;\n\
        proxy_set_header X-Forwarded-Host api.eisa.com.tr;\n\
        proxy_set_header X-Forwarded-Port 443;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n\
\n\
        proxy_connect_timeout 5s;\n\
        proxy_send_timeout 30s;\n\
        proxy_read_timeout 30s;\n\
    }\n\
\n\
    # Node API health check passthrough\n\
    location = /health {\n\
        proxy_pass http://127.0.0.1:8765/health;\n\
        access_log off;\n\
    }\n\
\n\
    # Kubernetes / Docker health check\n\
    location = /healthz {\n\
        access_log off;\n\
        default_type text/plain;\n\
        return 200 "OK\\n";\n\
    }\n\
\n\
    # SPA routing\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
}\n' > /etc/nginx/http.d/default.conf

# ── supervisord config ────────────────────────────────────────────────
RUN printf '[supervisord]\n\
nodaemon=true\n\
user=root\n\
logfile=/dev/stdout\n\
logfile_maxbytes=0\n\
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
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1/healthz || exit 1

CMD ["supervisord", "-c", "/etc/supervisord.conf"]