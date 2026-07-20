# Kiosk API (Node.js)

E-İSA Kiosk lokal API — **Fastify + better-sqlite3 + node-cron**.

Bu klasor kioskun Node.js lokal API moduludur. Endpoint'ler, port (`8765`), sema ve push/pull davranisi Svelte UI ile uyumludur.

## Komutlar

```bash
cd kiosk_edge/api-node

# Bağımlılıklar (better-sqlite3 native — derleme araçları gerektirebilir)
npm install

# .env'i oluştur
cp .env.example .env

# Geliştirme sunucusu (auto-reload)
npm run dev

# Üretim
npm start

# Testler
npm test
npm run test:coverage
```

## Ortam Değişkenleri

`.env.example` dosyasina bakin. Uretim ve gelistirme icin tum `EISA_*` degiskenleri buradadir.

| Değişken | Varsayılan |
|---|---|
| `EISA_KIOSK_FLEET_KEY` | — (zorunlu) |
| `EISA_KIOSK_PROVISIONING_SECRET` | — (zorunlu) |
| `EISA_SQLITE_PATH` | `/var/lib/eisa/local.db` |
| `EISA_CENTRAL_API_BASE` | `https://api.eisa.com.tr` |
| `EISA_PULL_INTERVAL_SEC` | `900` |
| `EISA_PUSH_INTERVAL_SEC` | `300` |
| `EISA_VERIFY_TLS` | `true` |
| `EISA_DEV_MODE` | `false` |
| `EISA_HOST` | `127.0.0.1` |
| `EISA_PORT` | `8765` |

Bootstrap akis:

1. Kiosk, MAC adresini sistemden otomatik okur.
2. `EISA_KIOSK_FLEET_KEY` + `EISA_KIOSK_PROVISIONING_SECRET` ile HMAC imzali provision istegi gonder.
3. Backend App Key doner; `kiosk_id` ve `pharmacy_id` yanit bodysinden alinir.
4. Bu bilgiler lokal SQLite'a yazilir ve sonraki acilislarda tekrar istenmez.

## Endpoint'ler

| Method | URL | Yetki | Açıklama |
|---|---|---|---|
| GET | `/health` | — | Sağlık |
| GET | `/api/kategoriler` | — | Aktif kategoriler |
| GET | `/api/kategoriler/:slug/sorular` | — | Kategori soruları |
| POST | `/api/oturum/gonder` | — | Anket → outbox |
| GET | `/api/oturum/:qr` | `Bearer PROVISIONING_SECRET` | QR ile oturum |
| GET | `/api/reklamlar/aktif` | — | Aktif kampanyalar |
| POST | `/api/reklam-gosterim` | — | Reklam gösterim logu |

## Üretim Dağıtımı

`eisa-api.service` systemd dosyasini `/etc/systemd/system/` altina kopyalayin. Servis `node /opt/eisa/app/kiosk_edge/api-node/src/index.js` calistirir. Tek binary istiyorsaniz Node SEA (`node --experimental-sea-config`) veya `pkg` ile derleyebilirsiniz.

Detayli VirtualBox + production kurulum adimlari icin: `kiosk_edge/PRODUCTION_VIRTUALBOX_DEPLOY.md`
