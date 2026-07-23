# Kiosk Edge API Node — Node.js + Fastify + SQLite

**Amaç:** Kiosk cihazında lokal çalışan API servisi; offline-first, backend senkronizasyonu, kategori/soru/playlist cache, session/impression log toplama, QR üretimi.

---

## When To Read This File

- Kiosk senkronizasyon problemlerinde
- Offline davranış değişikliklerinde
- Outbox/queue sorunlarında
- SQLite schema değişikliklerinde
- Lokal API endpoint'leri için

---

## Important Source Files

- `kiosk_edge/api-node/src/index.js` — Entry point, scheduler startup
- `kiosk_edge/api-node/src/server.js` — Fastify routes:
  - `POST /api/oturum/gonder` — session submission handler (**2026-07-20:** tamamlandi=true → backend QR zorunlu; sahte QR yok; backend erişilemezse 503)
  - `POST /api/reklam-gosterim` — proof-of-play ingestion handler
- `kiosk_edge/api-node/src/db.js` — SQLite schema (oturum_outbox, reklam_gosterim_outbox), outbox logic
- `kiosk_edge/api-node/src/scheduler.js` — Sync/push scheduler
- `kiosk_edge/api-node/src/provisioning.js` — Kiosk provisioning (**device_id**: `crypto.randomUUID()` ile üretilir, kiosk_meta'ya saklanır; HMAC'e dahil edilir; `/api/kiosk/v1/identity/enroll/` ile tek-seferlik bağlanır)
- `kiosk_edge/api-node/src/mediaCache.js` — Media download cache
- `kiosk_edge/api-node/src/config.js` — Config management

### Session QR Akışı (2026-07-20)
```
UI → POST /api/oturum/gonder { ..., tamamlandi: true }
  → Edge: hasAppKeyCredentials? YES
  → Edge: POST /api/kiosk/v1/sessions/ { items: [payload_without_qr] }
  → Backend: generate_qr_candidate() + DB insert + IntegrityError retry
  → Backend response: { results: [{ idempotency_key, status: "created", qr_kodu: "XXXXXXXX" }] }
  → Edge: outbox'a backend QR ile kaydet → UI'a { qr_kodu: "XXXXXXXX" } döndür
  → UI: Backend QR göster (sahte QR yok!)

Backend erişilemezse:
  → Edge: 503 { error: "...", code: "backend_unreachable" }
  → UI: Retry seçeneği göster
```

---

## Kiosk Edge API Node Amacı

**Neden gerekli:**
1. **Offline-first:** Kiosk internet bağlantısı kesilse bile çalışmaya devam etmeli (kategori/soru/playlist cache)
2. **Düşük latency:** Kullanıcı etkileşimi hızlı olmalı (lokal SQLite sorguları)
3. **Outbox pattern:** Session/impression logları lokal toplanır, batch olarak backend'e gönderilir
4. **Provisioning:** Kiosk ilk açılışta backend'e kayıt olur, App Key alır

**Mimari:** Node.js 20+, Fastify 5, better-sqlite3, node-cron scheduler

---

## Backend ile İlişkisi

### Backend → Kiosk (Pull)
1. **Kategori/Soru/Danışma/EtkenMadde senkronizasyonu:**
   - `GET /api/kiosk/v1/sync/` → backend tüm aktif kategori/soru/danışma/etken_madde verilerini JSON döner
   - Kiosk edge API → SQLite `kategoriler`, `sorular`, `cevaplar`, `danisma_kategorileri`, `etken_maddeler` tablolarına upsert
   - Scheduler: 5 dakikada bir (veya configurable)

2. **Playlist senkronizasyonu:**
   - `GET /api/kiosk/v1/ping/` → backend güncel playlist versiyonunu döner
   - Eğer lokal versiyon farklıysa → `GET /api/kiosk/v1/playlist/?date=YYYY-MM-DD` → günlük playlist JSON
   - Kiosk edge API → SQLite `playlists`, `playlist_items` tablolarına yazar
   - Scheduler: 10 dakikada bir (veya configurable)

3. **Creative/HouseAd medya senkronizasyonu:**
   - `GET /api/kiosk/v1/sync/` → backend tüm creative/house_ad listesi (media_url, checksum)
   - Kiosk edge API → media cache indirme kuyruğuna ekler
   - Media cache: `mediaCache.js` modülü (undici fetch, lokal dosya sistemi veya memory cache)

### Kiosk → Backend (Push)
1. **Session log outbox:**
   - Kiosk UI → `POST http://localhost:5234/sessions` → lokal API
   - Lokal API → SQLite `oturum_outbox` tablosuna insert
   - Scheduler: 1 dakikada bir → `POST /api/kiosk/v1/sessions/` → backend'e batch gönderim
   - Backend → `OturumLogu` modeline kayıt
   - Başarılı gönderimler → `gonderilme_tarihi` set edilir

2. **Impression log outbox:**
   - Kiosk UI → `POST http://localhost:5234/ad-impressions` → lokal API
   - Lokal API → SQLite `reklam_gosterim_outbox` tablosuna insert
   - Scheduler: 1 dakikada bir → `POST /api/kiosk/v1/proof-of-play/` → backend'e batch gönderim
   - Backend → `PlayLog` modeline kayıt
   - Başarılı gönderimler → `gonderilme_tarihi` set edilir

---

## Lokal Servisler, Queue/Cache/Log Mantığı

### SQLite Schema (`src/db.js`)

**ÖNEMLİ:** SQLite schema'sında FOREIGN KEY constraint'leri YOK (2026-07-07 itibarıyla kaldırıldı). Backend veri bütünlüğünü zaten sağladığı için offline-first SQLite'da gereksiz kontroller kaldırıldı. Tüm `REFERENCES` clause'ları silinmiş, `PRAGMA foreign_keys` komutları temizlenmiş.

**Kategori/Soru/Danışma:**
- `kategoriler`: id, slug, ad, ikon, bagli_kategori_id (INTEGER, FK YOK), hedef_cinsiyet_id (INTEGER, FK YOK), aktif, hedef_cinsiyetler JSON, hedef_yas_araliklari JSON
- `sorular`: id, kategori_id (INTEGER NOT NULL, FK YOK), metin, sira, hedef_cinsiyet_id (INTEGER, FK YOK), hedef_cinsiyetler JSON, hedef_yas_araliklari JSON, eslesme_kurallari JSON
- `cevaplar`: id, soru_id (INTEGER NOT NULL, FK YOK), metin, sira
- `cevap_etken_madde`: cevap_id (FK YOK), etken_madde_id (FK YOK), aktif
- `etken_maddeler`: id, ad, slug, aktif
- `danisma_kategorileri`: id, slug, ad, ikon, ust_kategori_id (INTEGER, FK YOK), aktif

**Playlist/Creative:**
- `creatives`: id, campaign_id, media_url, duration_seconds, name, type (creative/house_ad), checksum
- `playlists`: id, target_date, target_hour, version, items JSON
- `playlist_items`: playlist_id, asset_type, asset_id, duration_seconds, playback_order

**Outbox:**
- `oturum_outbox`: id, payload JSON, olusturulma_tarihi, gonderilme_tarihi (null = pending)
- `reklam_gosterim_outbox`: id, payload JSON, olusturulma_tarihi, gonderilme_tarihi (null = pending)

**Meta:**
- `kiosk_meta`: key, value (kiosk_app_key, kiosk_id, pharmacy_id, playlist_version, last_sync_at, provisioning_state, registration_id)
- `media_cache`: asset_id, asset_type, source_url, source_checksum (backend'den: sha256:<hex>), file_checksum (raw hex, downloadToFile), local_path, status, error_message, synced_at

**Checksum sözleşmesi (Faz 0.5+):**
- `source_checksum`: backend'den gelen `sha256:<hex>` formatı, freshness karşılaştırması için
- `file_checksum`: kiosk indirdiğinde hesapladığı raw hex (prefix yok)
- Cache hit: `source_url === asset.media_url && source_checksum === asset.source_checksum && dosya var`
- Stabil media_url sonrası gereksiz yeniden-indirme ortadan kalkar

**Outbox pressure check (`checkOutboxPressure`):**
- Eğer `oturum_outbox` veya `reklam_gosterim_outbox` tablolarında `gonderilme_tarihi IS NULL` kayıt sayısı `outboxMaxRows` (default 10000) değerini aşarsa warning log
- Tam dolunca ne olur? Şu an sadece log, overwrite veya block mekanizması yok (Belirsiz / riskli)

### Scheduler (`src/scheduler.js`)

**Cron job'lar:**
1. `pullFromCentral`: Her 5 dakikada bir → backend'den kategori/soru/danışma/creative/house_ad çek, SQLite'a upsert
2. `pingAndSyncPlaylist`: Her 10 dakikada bir → backend'den playlist versiyonu kontrol, değiştiyse playlist çek
3. `pushOutbox`: Her 1 dakikada bir → `oturum_outbox` ve `reklam_gosterim_outbox` tablolarından pending kayıtları batch olarak backend'e gönder
4. `cleanupOldLogs`: Her gece 02:00 → 90 gün eski logları sil

**Retry logic (exponential backoff):**
- `requestWithRetry` fonksiyonu: 0ms, 1000ms, 3000ms delay ile 3 deneme
- 500+ HTTP hatası veya ağ hatası → retry
- 3 deneme sonunda başarısız → log, sonraki scheduler cycle'da tekrar denenir

### Media Cache (`src/mediaCache.js`)

**Amaç:** Creative/HouseAd medya URL'lerini lokal dosya sistemine indir, offline oynatım için cache
**Durum:** Kodda placeholder var gibi görünüyor, tam implementasyon belirsiz (Doğrulanmalı)

### Provisioning (`src/provisioning.js`)

**Durum makinesi (2026-07-14):**
```
UNREGISTERED      → bootstrap dene
PENDING_APPROVAL  → admin onayi bekleniyor (polling / backoff)
APPROVED          → app_key alindi
REJECTED          → admin reddetti; normal API'lere erisim engellenir
```

**State kiosk_meta'da saklanır:**
- `provisioning_state`: UNREGISTERED / PENDING_APPROVAL / APPROVED / REJECTED
- `registration_id`: 202 PENDING yanıtından gelen UUID

**İlk açılış (App Key, 2026-07-20):**
1. `resolveRuntimeSettings` → MAC'i SQLite `kiosk_meta`'dan (yoksa sistemden) okur ve sabitler; legacy provisioning kaydı bir defalık temizlenir.
2. Provisioning durumu APPROVED ve `kiosk_app_key` mevcutsa → bootstrap atlanır.
3. REJECTED ise → bootstrap denenmez.
4. Aksi halde `POST /api/kiosk/v1/bootstrap/` → 200 APPROVED (`app_key`) / 202 PENDING / 403 REJECTED.
5. APPROVED yanıtında `app_key`, `kiosk_id`, `pharmacy_id` → `kiosk_meta`'ya yazılır.
6. Sonraki tüm operasyonel isteklerde `Authorization: AppKey <app_key>` + `X-Kiosk-MAC` kullanılır.

**Credential okuma:** `getAuthHeaders(db)` her istekte `kiosk_app_key` + `kiosk_mac`'i SQLite'tan okur → provision sonrası process restart gerekmez (freeze/stale sorunu yok).

**401/403 davranışı (2026-07-20):**
- `handle401Error` / `handle403Error` App Key'i **silmez**; secret loglanmaz (yalnız `has_app_key` bool); başka auth fallback yapılmaz; doğal scheduler aralığında backoff uygulanır.
- 401 ve 403 tüm çağrılarda ayrı işlenir: scheduler.js (pull sync+catalog, push sessions+proof-of-play, ping+playlist, diagnostics) ve server.js (anlık session).
- App Key yaşam döngüsü SQLite'tan yönetilir; `Authorization: AppKey` + `X-Kiosk-MAC` **tek operasyonel kontrattır**; SQLite dizin `700` / DB dosyası `600` (Linux) izinleriyle korunur.

**Cihaz metadata (2026-07-14):**
Bootstrap isteğinde `collectDeviceMetadata()` ile derlenen sistem bilgileri gönderilir:
- `hostname`, `os_type`, `os_platform`, `os_release`, `arch`
- `cpu_model`, `cpu_cores`, `total_memory_mb`
- `ip_addresses` (dahili olmayan IPv4 listesi + interface adı)
- `node_version`, `uptime_seconds`

Toplanan veriler `device_metadata` JSON alanı olarak `KioskProvisioningRequest`'e yazılır. Token/secret/credential içermez.

---

## Reklam, Kategori, Session/Log Akışındaki Rolü

### Kategori Akışı
1. Backend → `/api/kiosk/v1/sync/` endpoint'i → kategorileri JSON döner
2. Kiosk edge scheduler → `pullFromCentral` → kategori/soru/cevap verilerini SQLite'a upsert
3. Kiosk UI → `GET http://localhost:5234/categories` → SQLite'dan aktif kategorileri çeker
4. Filtreleme: Kullanıcının yaş/cinsiyet bilgisine göre `hedef_yas_araliklari` ve `hedef_cinsiyet_id` kontrolü

### Reklam Akışı
1. Backend → playlist üretir, kiosk için `Playlist` + `PlaylistItem` kayıtları
2. Kiosk edge scheduler → `pingAndSyncPlaylist` → yeni playlist versiyonu varsa indir
3. SQLite → `playlists` ve `playlist_items` tablolarına kayıt
4. Kiosk UI → `GET http://localhost:5234/playlist?date=YYYY-MM-DD` → günlük playlist JSON
5. Kiosk UI AdStrip → playlist item'ları sırayla oynatır (60sn döngü)

### Session/Log Akışı
1. Kiosk UI → kullanıcı kategori/soru akışını tamamlar, QR üretilir
2. Kiosk UI → `POST http://localhost:5234/sessions` → session JSON payload
   ```json
   {
     "idempotency_key": "uuid",
     "yas_araligi_id": 2,
     "cinsiyet_id": 1,
     "kategori_id": 5,
     "hassas_akis": false,
     "qr_kodu": "EISA-1234567890",
     "cevaplar": {...},
     "onerilen_etken_maddeler": [...],
     "tamamlandi": true
   }
   ```
3. Lokal API → SQLite `oturum_outbox` → insert
4. **ÖNEMLİ (2026-07-07 güncellemesi):** Eğer `tamamlandi=true` ise session ANINDA backend'e iletilir:
   - `server.js` POST `/api/oturum/gonder` handler → `requestWithRetry()` ile `POST /api/analytics/sessions/`
   - Başarılı (HTTP 200/201) → outbox kaydının `gonderilme_tarihi` set edilir
   - Başarısız (network/500 error) → log + scheduler sonraki cycle'da tekrar dener
   - Eczacı QR taradığında cevapları ANINDA görebilir (300sn scheduler beklentisi yok)
5. Scheduler → `pushOutbox` → pending kayıtlar için batch gönderim (retry mekanizması)
   - `POST /api/kiosk/v1/sessions/` → `sessions` array
6. Backend → `OturumLogu` modeline kayıt (idempotency_anahtari ile duplikasyon koruması)

### Impression Log Akışı
1. Kiosk UI AdStrip → bir reklam slotu gösterilir → `shownAt` timestamp
2. Slot değişince önceki slotun gerçek izlenme süresi hesaplanır (`durationMs`)
3. Kiosk UI → `POST http://127.0.0.1:8765/api/reklam-gosterim` → payload
   ```json
   {
     "asset_id": "uuid",
     "asset_type": "creative",
     "played_at": "2026-06-05T10:30:00Z",
     "duration_played": 15
   }
   ```
4. Lokal API → SQLite `reklam_gosterim_outbox` → insert
5. Scheduler → `pushToCentral` → backend'e batch gönderim
   - `POST /api/kiosk/v1/proof-of-play/` → `logs` array
     (her log: `creative_id` VEYA `house_ad_id` + `played_at` + `duration_played`)
6. Backend → `PlayLog` modeline bulk insert (201 `{ ingested: N }`)

---

## API Endpoint'leri (Lokal — localhost:5234)

| Method | Path | Açıklama |
|--------|------|----------|
| `GET` | `/healthz` | Health check (200 OK) |
| `GET` | `/categories` | Aktif kategoriler (yaş/cinsiyet filtreli) |
| `GET` | `/danisma-categories` | Danışma kategorileri |
| `GET` | `/questions?kategori_id={id}` | Kategoriye ait sorular (hedef filtreleme) |
| `GET` | `/answers?soru_id={id}` | Soruya ait cevaplar |
| `GET` | `/playlist?date=YYYY-MM-DD` | Günlük playlist JSON |
| `POST` | `/sessions` | Session log kaydı (outbox'a ekler) |
| `POST` | `/ad-impressions` | Impression log kaydı (outbox'a ekler) |
| `GET` | `/wifi-status` | WiFi bağlantı durumu (nmcli çağrısı, Linux) |
| `POST` | `/wifi-connect` | WiFi bağlantısı kur (nmcli, Linux) |
| `POST` | `/api/log/client` | *(2026-07-16)* Svelte UI kritik hata köprüsü — allow-list edilen event kodlarını JSON log + diagnostic_outbox'a yazar |

---

## Do Not Change Without Checking

**Critical SQLite schema and sync contracts:**

1. **SQLite Table Schema:**
   - `kategoriler`, `sorular`, `cevaplar`, `etken_maddeler`, `danisma_kategorileri`
   - `creatives`, `playlists`, `playlist_items`
   - `oturum_outbox`, `reklam_gosterim_outbox`
   - Breaking: data sync/query fails

2. **Backend Sync Response Format:**
   - Must match backend `/api/kiosk/v1/sync/` response
   - Breaking: SQLite upsert fails

3. **Outbox Payload Format:**
   - Session: `{ idempotency_key, yas_araligi_id, cinsiyet_id, kategori_id, qr_kodu, cevaplar, onerilen_etken_maddeler, tamamlandi }`
   - Impression: `{ asset_id, asset_type, played_at, duration_played }` (push'ta creative_id/house_ad_id'ye maplenir)
   - Breaking: backend cannot parse

4. **Scheduler Intervals (config.js varsayilanlari):**
   - pullFromCentral: 900sn (15 dk) — `EISA_PULL_INTERVAL_SEC`
   - pingAndSyncPlaylist: 60sn (1 dk) — `EISA_PING_INTERVAL_SEC`
   - pushToCentral: 300sn (5 dk) — `EISA_PUSH_INTERVAL_SEC`
   - Breaking: sync frequency/performance issues

5. **Lokal API Endpoints:**
   - `GET /categories`, `GET /playlist`, `POST /sessions`, `POST /ad-impressions`
   - Breaking: kiosk UI cannot function

---

## Docker Deployment (Demo)

### Birleşik (All-in-One) Container

**Dosya:** `kiosk_edge/Dockerfile` (build context: `kiosk_edge/`)

API Node ve UI **tek container** içinde birlikte çalışır:
- Nginx (:80) → UI static + `/api` proxy → 127.0.0.1:8765
- Node API (Fastify, internal port 8765)
- supervisord ile iki process yönetilir (autorestart)

**Özellikler:**
- Multi-stage build (ui-build → api-deps → runner)
- Alpine Linux + Node.js 20
- better-sqlite3 native derleme (python3/make/g++ build stage)
- SQLite + media persistence: `/var/lib/eisa` volume

### Environment Variables (container içi)

```bash
EISA_PORT=8765
EISA_HOST=127.0.0.1
EISA_SQLITE_PATH=/var/lib/eisa/local.db
EISA_MEDIA_DIR=/var/lib/eisa/media
EISA_CENTRAL_API_BASE=https://api.eisa.com.tr

# Loglama (2026-07-16)
LOG_LEVEL=info
LOG_FORMAT=json
SERVICE_NAME=eisa-kiosk-api
APP_ENV=production
APP_VERSION=1.0.2
```

> Not: API `EISA_` prefix'li env değişkenleri kullanır (`config.js`). `EISA_LOG_DIR` KALDIRILDI — loglar JSON stdout'a yazılır.

### Loglama ve Diagnostic Outbox (2026-07-16)

- `src/logger.js`: Pino tabanlı JSON stdout. `logRedaction.js` üzerinden `Authorization`, `Cookie`, `token`, `fleet_key`, `qr_kodu`, `cevaplar` vb. maskelenir.
- `src/correlationId.js`: `AsyncLocalStorage` ile korelasyon ID takibi; scheduler her döngü için `derivedId('pull'|'push'|'ping'|'diag')` üretir; `X-Correlation-ID` başlığı Fastify hook + backend çağrılarında iletilir.
- `src/diagnosticOutbox.js` + SQLite `diagnostic_outbox` tablosu (şema v10):
  - Yalnızca `WARNING/ERROR/CRITICAL`; `INFO/DEBUG` YAZILMAZ.
  - Sınırlar: 5000 kayıt, 7 gün, batch 100, mesaj 4 KB, stack 8 KB.
  - FIFO trigger + exponential backoff (max 6 retry). Uygulama outbox dolarsa DURMAZ.
- Scheduler `pushDiagnostics()` → `POST /api/kiosk/v1/diagnostics/` (backend DB'ye yazmaz, JSON stdout'a çevirir).
- Yeni endpoint: `POST /api/log/client` — Svelte UI hata köprüsü (yalnızca allow-list edilen event kodları).
- Detay: [docs/operations/logging.md](../operations/logging.md).

### Docker Compose

**Dosya:** `kiosk_edge/docker-compose.demo.yml`

```powershell
# Başlat
docker compose -f docker-compose.demo.yml up -d

# Loglar (api + nginx birlikte)
docker compose -f docker-compose.demo.yml logs -f kiosk

# Container içi process durumu
docker exec -it eisa-kiosk-demo supervisorctl status
```

**NOT:** Bu Docker yapısı sadece **demo.eisa.com.tr** için hazırlanmıştır. Gerçek kiosk cihazlarında systemd service olarak native deployment kullanılır (`eisa-api.service`).

Detay: `kiosk_edge/README_DEMO_DOCKER.md`

---

## Belirsiz / Riskli Noktalar

1. **Outbox tam dolunca ne olur:** `outboxMaxRows` aşılırsa sadece warning, overwrite/block mekanizması yok. Log kaybı riski. (Riskli)
2. **Media cache implementasyonu:** `mediaCache.js` placeholder gibi görünüyor, tam çalışır durumda mı? (Belirsiz)
3. **App Key rotation logic:** App Key rotasyonu yok; provision sonrası aynı App Key kullanılır. (Belirsiz)
4. **WiFi setup:** `nmcli` çağrıları Linux'a özel, geliştirme ortamında (Windows/macOS) çalışmaz. (Belirsiz)
5. **Session idempotency key:** `idempotency_key` kiosk UI tarafından mı üretiliyor, backend duplikasyon kontrolü düzgün çalışıyor mu? (Doğrulanmalı)
6. **Playlist version mismatch:** Kiosk uzun süre offline kalırsa playlist versiyonu çok eski olur, backend eski versiyonları tutuyor mu? (Belirsiz)

---

**Satır sayısı: ~260**
