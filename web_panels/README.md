# Web Panels — E-İSA Yönetim Panelleri

Vue 3 tabanlı web paneli. SuperAdmin ve Eczacı rollerine yönelik iki ayrı arayüz içerir.

## Teknoloji Yığını

| Katman | Araç |
|--------|------|
| Framework | Vue 3 (Composition API) |
| State | Pinia |
| Router | Vue Router 4 |
| HTTP | Axios |
| CSS | Tailwind CSS 3 |
| Build | Vite 5 |
| Test | Vitest + @vue/test-utils |
| Prod Sunucu | Nginx (Docker) |

---

## Lokal Geliştirme (Docker olmadan)

### Gereksinimler

- Node.js 20+
- Çalışan bir backend API (varsayılan: `http://localhost:8000`)

### Kurulum ve Başlatma

```bash
cd web_panels

npm install
npm run dev
```

UI `http://localhost:5174` adresinde başlar.

> Vite dev server API isteklerini proxy etmez; backend `localhost:8000`'de ayrıca çalışıyor olmalıdır. Backend'i başlatmak için [backend/README.md](../backend/README.md) dosyasına bakın.

### Diğer Komutlar

```bash
# Testleri çalıştır
npm test

# Coverage ile test
npm run test:coverage

# Production build oluştur (dist/ klasörü)
npm run build

# Build'i önizle (Nginx benzeri static serving)
npm run preview
```

---

## Docker ile Çalıştırma

### Tüm Merkezi Servislerle Birlikte (Önerilen)

```bash
# Repo kökünden
cd ..   # eisa/ kök dizini

# .env dosyası yoksa oluştur
cp .env.example .env

# Geliştirme compose (Traefik olmadan, portlar expose edilmiş)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

Panel `http://localhost:8080` adresinde erişilebilir olur.

### Yalnızca Panel Servisini Build Et

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml build panels
docker compose -f docker-compose.yml -f docker-compose.dev.yml up panels
```

### Logları İzle

```bash
docker compose logs -f panels
```

### Servisleri Durdur

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

---

## Production Docker İmajı

Panel, multi-stage Dockerfile ile derlenir:

1. **Build aşaması** — `node:20-alpine` içinde `npm run build` çalışır, `dist/` üretir.
2. **Serve aşaması** — `nginx:1.27-alpine` üzerinde statik dosyaları sunar.

Nginx konfigürasyonu (`nginx.conf`):
- Vue Router `history` modu için `try_files` yönlendirmesi
- Güvenlik başlıkları (CSP, HSTS, X-Frame-Options vb.)
- Statik varlıklar için 30 günlük cache

Üretimde Traefik reverse-proxy TLS sonlandırmasını üstlenir (`docker-compose.yml`).

---

## Testler

```bash
cd web_panels

# Tüm testleri çalıştır
npm test

# Watch modunda
npm test -- --watch

# Coverage raporu
npm run test:coverage
```

---

## Proje Yapısı

```
web_panels/
├── Dockerfile             # Multi-stage: Vite build → Nginx serve
├── nginx.conf             # Nginx konfigürasyonu (güvenlik başlıkları dahil)
├── package.json
├── vite.config.js         # Port: 5174
├── tailwind.config.js
└── src/
    ├── main.js
    ├── App.vue
    ├── styles.css
    ├── router/
    │   └── index.js
    ├── stores/
    │   └── auth.js        # Pinia — JWT oturum yönetimi
    ├── services/
    │   ├── api.js         # Axios base instance
    │   ├── analytics.js
    │   └── campaigns.js
    └── views/
        ├── Login.vue
        ├── admin/
        │   ├── AdminLayout.vue
        │   ├── Dashboard.vue
        │   └── Campaigns.vue
        └── pharmacist/
```

---

## Ortam / API Adresi

Backend API adresi `src/services/api.js` içinde tanımlıdır. Geliştirme ortamında farklı bir adres kullanmak için Vite'ın `.env` desteğinden yararlanabilirsiniz:

```bash
# web_panels/.env.local (gitignore'a dahil edilmeli)
VITE_API_BASE_URL=http://localhost:8000
```

> Not: Üretim build'inde API adresi statik olarak gömülür. Üretim için `nginx.conf`'a `proxy_pass` eklemek ya da ayrı env değişkeni kullanmak tercih edilebilir.
