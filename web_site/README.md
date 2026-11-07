# e-isa Kurumsal Site (`web_site`)

eisa.com.tr — Next.js (App Router) + TypeScript + Tailwind CSS v4. İçerik, portal (portal.eisa.com.tr) üzerinden
yönetilen blok tabanlı CMS'ten (Django, `backend/apps/website`) gelir.

- Bağlayıcı sözleşme: [`docs/web-sitesi/CONTRACT.md`](../docs/web-sitesi/CONTRACT.md) · Genel plan: [`docs/web-sitesi/PLAN.md`](../docs/web-sitesi/PLAN.md)
- Blok bileşen sözleşmesi: [`src/blocks/README.md`](src/blocks/README.md)
- Sürümler: Next.js 16.4, React 19.3, Tailwind 4, motion, lenis, @phosphor-icons/react.
  Bu Next sürümünün API'leri için `node_modules/next/dist/docs/` belgelerine bakın (bkz. `AGENTS.md`).

## Hızlı başlangıç

```powershell
cd web_site
npm ci

# 1) Backend olmadan (fixture içerik) — önerilen ilk çalıştırma
$env:MOCK_API = "1"; npm run dev          # http://localhost:3000

# 2) Lokal backend ile (Django :8000, settings_dev_sqlite + website_seed)
Remove-Item Env:MOCK_API -ErrorAction SilentlyContinue; npm run dev
```

Üretim derlemesi ve çalıştırma:

```powershell
npm run build
npm run start            # veya standalone: node .next/standalone/server.js (public ve .next/static kopyalanmalı)
```

Paralel geliştirme (ör. iki ajan aynı anda): `$env:NEXT_DIST_DIR = ".next-ajan1"; npx next dev -p 3001`.

Kontroller: `npm run lint`, `npx tsc --noEmit`.

## Ortam değişkenleri

`.env.example` dosyasını `.env.local` olarak kopyalayın. Hepsinin lokal varsayılanı vardır (CONTRACT §1).

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `API_INTERNAL_URL` | `http://localhost:8000` | Sunucu tarafı fetch tabanı (K8s: cluster içi servis) |
| `MEDIA_BASE_URL` | `http://localhost:8000` | Medya `yol` alanının önüne eklenir (prod `https://api.eisa.com.tr`) |
| `SITE_URL` | `http://localhost:3000` | Canonical, sitemap, OG, JSON-LD (prod `https://eisa.com.tr`) |
| `REVALIDATE_SECRET` | `dev-revalidate-secret` | Backend → `/api/revalidate` ortak sırrı |
| `WEBSITE_SERVER_TOKEN` | `dev-website-token` | Başvuru POST'unda `X-Website-Token` |
| `MOCK_API` | (boş) | `1` → API yerine `src/lib/mock` fixture'ları |
| `NEXT_DIST_DIR` | `.next` | Build/dev çıktı dizini |

`SITE_URL` ve `MEDIA_BASE_URL` build sırasında da okunur (görsel izinli host'ları, build'de üretilen metadata);
Docker imajında varsayılanları üretim değerleridir.

## Mimari

```
src/
  app/
    layout.tsx                 fontlar (Space Grotesk + Inter, latin-ext), Header/Footer, Lenis, önizleme bandı,
                               Organization + WebSite JSON-LD, varsayılan metadata (site ayarlarından)
    [[...slug]]/page.tsx       CMS sayfaları: "/" = anasayfa, "/<slug>"; BlockRenderer
    blog/page.tsx              liste (?kategori=, ?sayfa=)
    blog/[slug]/page.tsx       detay (.prose-eisa, ilgili yazılar, BlogPosting JSON-LD, paylaşım)
    actions/basvuru.ts         başvuru server action (X-Website-Token, X-Website-Client-IP)
    api/revalidate             POST, CONTRACT §6 (X-Revalidate-Secret → revalidateTag(tag, { expire: 0 }))
    api/preview, preview/exit  CONTRACT §7 (draft mode + httpOnly `eisa_preview` çerezi)
    api/health                 K8s probe (API'ye dokunmaz)
    sitemap.ts, robots.ts, opengraph-image.tsx, icon.svg, not-found.tsx, error.tsx, global-error.tsx
  blocks/                      16 blok tipi (tip → bileşen haritası: index.tsx) — bkz. blocks/README.md
  components/                  Header, Footer, CookieBanner, PreviewBanner, SmoothScroll, SiteProvider, JsonLd ...
  components/ui/               Container, Section, SectionHeading, Reveal/Stagger, ButonLink, AkilliLink, Icon,
                               MediaImage, Paragraflar, AnimatedCounter, MagneticButton, Dekor
  lib/
    types.ts                   CONTRACT tiplerinin birebir karşılığı (16 blok veri tipi + Blok union)
    api.ts                     sunucu veri katmanı (server-only)
    env.ts, media.ts, utils.ts, kaydirma.ts, hooks.ts, hareket.ts
    mock/                      MOCK_API fixture'ları (site, 7 sayfa, 3 blog yazısı)
```

### Veri ve önbellek

- Tüm API istekleri sunucuda yapılır (`fetch(url, { next: { tags, revalidate } })`; `cacheComponents` kapalı).
- Tag'ler (CONTRACT §6): `site`, `sayfalar`, `sayfa:<slug>`, `blog`, `blog:<slug>`.
  Süreler: site/sayfa/blog detayı 3600 sn, blog listesi 300 sn.
- Backend yayınlama sonrası `/api/revalidate`'i çağırır (K8s'te headless service ile pod başına).
- Draft mode açıkken sayfa/blog preview uçlarından `cache: 'no-store'` ile okunur.

### Dayanıklılık

- `getSite()` asla hata fırlatmaz: API'ye ulaşılamazsa seed içerikli yedek veri döner.
- Sayfa/yazı 404 → `notFound()`. Ağ/5xx hatası → `error.tsx` (ISR son başarılı sürümü sunmaya devam eder).
- **Build sırasında backend kapalıysa build kırılmaz:** `generateStaticParams` hatayı yakalayıp `[]` döner,
  sayfalar ilk istekte üretilir; sitemap en azından `/` ve `/blog` döner.

### MOCK modu

`MOCK_API=1` iken `src/lib/api.ts` hiçbir ağ isteği yapmaz; `src/lib/mock/` fixture'larını döner
(biçimler CONTRACT §3 ile birebir). Fixture'lar CONTRACT §9 seed planını izler: anasayfa, teknoloji, sponsorlar,
hakkimizda, iletisim, kvkk, cerez-politikasi + 3 blog yazısı; 16 blok tipinin her biri en az bir sayfada geçer.
Başvuru action'ı MOCK modunda kayıt oluşturmadan başarılı döner; önizleme her token'ı kabul eder.

## Docker

```powershell
docker build -t ghcr.io/ysnzgl/eisa-site:2.0.0 web_site
docker run --rm -p 3000:3000 -e API_INTERNAL_URL=http://host.docker.internal:8000 ghcr.io/ysnzgl/eisa-site:2.0.0
```

`node:22-alpine` çok aşamalı, `output: "standalone"`, non-root (`nextjs` uid 1001), `PORT=3000`, `HOSTNAME=0.0.0.0`,
`NEXT_TELEMETRY_DISABLED=1`. Build argümanları: `SITE_URL`, `MEDIA_BASE_URL`, `API_INTERNAL_URL`, `MOCK_API`.
Dağıtım: `deploy/eisa-site-production.yaml`, `deploy/deploy-site.ps1`.

## Hızlı doğrulama (MOCK)

```powershell
$env:MOCK_API = "1"; npm run build; npm run start
# başka bir terminalde:
Invoke-WebRequest http://localhost:3000/ -UseBasicParsing | Select-Object StatusCode
Invoke-WebRequest http://localhost:3000/api/revalidate -Method POST -UseBasicParsing `
  -Headers @{ "X-Revalidate-Secret" = "dev-revalidate-secret" } -ContentType "application/json" `
  -Body '{"tags":["site","sayfa:anasayfa"]}'
```
