# e-isa kurumsal site (Next.js, standalone) — üretim imajı
#
#   docker build -t ghcr.io/ysnzgl/eisa-site:2.0.0 web_site
#   docker run --rm -p 3000:3000 -e API_INTERNAL_URL=http://host.docker.internal:8000 ghcr.io/ysnzgl/eisa-site:2.0.0
#
# Notlar:
# - Build sırasında backend'e ERİŞİLMESİ GEREKMEZ: sayfa listesi alınamazsa generateStaticParams []
#   döner ve sayfalar ilk istekte üretilir (ISR). Site ayarları için seed içerikli yedek kullanılır.
# - SITE_URL ve MEDIA_BASE_URL build sırasında da okunur (next.config images.remotePatterns,
#   build'de önceden üretilen metadata). Varsayılanlar üretim değerleridir; farklı ortam için
#   --build-arg ile verin. Çalışma zamanı değerleri ayrıca ENV ile (K8s manifest) verilir.
# - Kullanıcı uid/gid 1001 (nextjs/nodejs) — deploy/eisa-site-production.yaml securityContext ile aynı.

# ─── Bağımlılıklar ───────────────────────────────────────────────────────────
FROM node:22-alpine AS deps
WORKDIR /app
# sharp/swc gibi native paketler için (Alpine/musl)
RUN apk add --no-cache libc6-compat
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# ─── Build ───────────────────────────────────────────────────────────────────
FROM node:22-alpine AS build
WORKDIR /app
RUN apk add --no-cache libc6-compat

ARG SITE_URL=https://eisa.com.tr
ARG MEDIA_BASE_URL=https://api.eisa.com.tr
# Build'de erişilemezse sorun değil (bkz. üstteki not).
ARG API_INTERNAL_URL=http://localhost:8000
# Yalnızca demo/önizleme imajı için: MOCK_API=1 ile fixture içerikle derlenir.
ARG MOCK_API=

ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production \
    SITE_URL=${SITE_URL} \
    MEDIA_BASE_URL=${MEDIA_BASE_URL} \
    API_INTERNAL_URL=${API_INTERNAL_URL} \
    MOCK_API=${MOCK_API}

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ─── Çalışma zamanı ──────────────────────────────────────────────────────────
FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 --ingroup nodejs nextjs

# Standalone sunucu (server.js + izlenen node_modules) + statik dosyalar
COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=build --chown=nextjs:nodejs /app/public ./public

# Yazılabilir dizinler (K8s'te readOnlyRootFilesystem ile emptyDir olarak bağlanır):
#   .next/cache               → görsel optimizasyon + fetch önbelleği
#   .next/server/route-cache  → ISR sayfa önbelleği (Next 16; yoksa yeniden üretilen sayfalar diske yazılamaz)
RUN mkdir -p .next/cache .next/server/route-cache \
    && chown -R nextjs:nodejs .next/cache .next/server/route-cache

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:3000/api/health >/dev/null 2>&1 || exit 1

CMD ["node", "server.js"]
