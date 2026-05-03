# Kiosk API (Node.js)

E-İSA Kiosk lokal API — **Fastify + better-sqlite3 + node-cron**.

Bu klasör eski `api/` (FastAPI) modülünün Node.js eşleniğidir. Endpoint'ler, port (`8765`), şema, push/pull mantığı ve seed dosyası birebir korunmuştur — Svelte UI için davranış aynıdır.

## Komutlar

```bash
cd kiosk_edge/api-node

# Bağımlılıklar (better-sqlite3 native — derleme araçları gerektirebilir)
npm install

# .env'i oluştur
cp .env.example .env

# SQLite seed (opsiyonel, app açılışında zaten yüklüyor)
npm run seed

# Geliştirme sunucusu (auto-reload)
npm run dev

# Üretim
npm start

# Testler
npm test
npm run test:coverage
```

## Ortam Değişkenleri

`.env.example` dosyasına bakın. FastAPI sürümüyle birebir aynı `EISA_*` değişkenleri kullanılır.

| Değişken | Varsayılan |
|---|---|
| `EISA_KIOSK_APP_KEY` | — (zorunlu) |
| `EISA_KIOSK_MAC` | — (zorunlu) |
| `EISA_SQLITE_PATH` | `/var/lib/eisa/local.db` |
| `EISA_CENTRAL_API_BASE` | `https://api.e-isa.local` |
| `EISA_LOCAL_API_SECRET` | — |
| `EISA_PULL_INTERVAL_SEC` | `900` |
| `EISA_PUSH_INTERVAL_SEC` | `300` |
| `EISA_VERIFY_TLS` | `true` |
| `EISA_DEV_MODE` | `false` |
| `EISA_HOST` | `127.0.0.1` |
| `EISA_PORT` | `8765` |

## Endpoint'ler

| Method | URL | Yetki | Açıklama |
|---|---|---|---|
| GET | `/health` | — | Sağlık |
| GET | `/api/categories` | — | Aktif kategoriler |
| GET | `/api/categories/:slug/questions` | — | Kategori soruları |
| POST | `/api/session/submit` | — | Anket → outbox |
| GET | `/api/session/:qr` | `Bearer LOCAL_SECRET` | QR ile oturum |
| GET | `/api/campaigns/active` | — | Aktif kampanyalar (saat filtreli) |
| POST | `/api/ad-impression` | — | Reklam impression logu |

## Üretim Dağıtımı

`eisa-api.service` systemd dosyasını `/etc/systemd/system/` altına kopyalayın. Servis `node /opt/eisa/api/src/index.js` çalıştırır. Tek binary istiyorsanız Node SEA (`node --experimental-sea-config`) veya `pkg` ile derleyebilirsiniz.
