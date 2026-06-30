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
  - `POST /api/oturum/gonder` (line 189) — session submission handler
  - `POST /api/reklam-gosterim` (line 406) — proof-of-play ingestion handler
- `kiosk_edge/api-node/src/db.js` — SQLite schema (oturum_outbox, reklam_gosterim_outbox), outbox logic
- `kiosk_edge/api-node/src/scheduler.js` — Sync/push scheduler:
  - `pullFromCentral()` (line 315) — backend data pull
  - `pushToCentral()` (line 494) — outbox forwarding
  - `pingAndSyncPlaylist()` — playlist version check
- `kiosk_edge/api-node/src/provisioning.js` — Kiosk provisioning
- `kiosk_edge/api-node/src/mediaCache.js` — Media download cache
- `kiosk_edge/api-node/src/config.js` — Config management

---

## Kiosk Edge API Node Amacı

**Neden gerekli:**
1. **Offline-first:** Kiosk internet bağlantısı kesilse bile çalışmaya devam etmeli (kategori/soru/playlist cache)
2. **Düşük latency:** Kullanıcı etkileşimi hızlı olmalı (lokal SQLite sorguları)
3. **Outbox pattern:** Session/impression logları lokal toplanır, batch olarak backend'e gönderilir
4. **Provisioning:** Kiosk ilk açılışta backend'e kayıt olur, IoT token alır

**Mimari:** Node.js 20+, Fastify 5, better-sqlite3, node-cron scheduler

---

## Backend ile İlişkisi

### Backend → Kiosk (Pull)
1. **Kategori/Soru/Danışma/EtkenMadde senkronizasyonu:**
   - `GET /api/kiosk/v1/{kiosk_id}/sync/` → backend tüm aktif kategori/soru/danışma/etken_madde verilerini JSON döner
   - Kiosk edge API → SQLite `kategoriler`, `sorular`, `cevaplar`, `danisma_kategorileri`, `etken_maddeler` tablolarına upsert
   - Scheduler: 5 dakikada bir (veya configurable)

2. **Playlist senkronizasyonu:**
   - `GET /api/kiosk/v1/{kiosk_id}/ping/` → backend güncel playlist versiyonunu döner
   - Eğer lokal versiyon farklıysa → `GET /api/kiosk/v1/{kiosk_id}/playlist/?date=YYYY-MM-DD` → günlük playlist JSON
   - Kiosk edge API → SQLite `playlists`, `playlist_items` tablolarına yazar
   - Scheduler: 10 dakikada bir (veya configurable)

3. **Creative/HouseAd medya senkronizasyonu:**
   - `GET /api/kiosk/v1/{kiosk_id}/sync/` → backend tüm creative/house_ad listesi (media_url, checksum)
   - Kiosk edge API → media cache indirme kuyruğuna ekler
   - Media cache: `mediaCache.js` modülü (undici fetch, lokal dosya sistemi veya memory cache)

### Kiosk → Backend (Push)
1. **Session log outbox:**
   - Kiosk UI → `POST http://localhost:5234/sessions` → lokal API
   - Lokal API → SQLite `oturum_outbox` tablosuna insert
   - Scheduler: 1 dakikada bir → `POST /api/kiosk/v1/{kiosk_id}/sync/` → backend'e batch gönderim
   - Backend → `OturumLogu` modeline kayıt
   - Başarılı gönderimler → `gonderilme_tarihi` set edilir

2. **Impression log outbox:**
   - Kiosk UI → `POST http://localhost:5234/ad-impressions` → lokal API
   - Lokal API → SQLite `reklam_gosterim_outbox` tablosuna insert
   - Scheduler: 1 dakikada bir → `POST /api/kiosk/v1/{kiosk_id}/proof-of-play/` → backend'e batch gönderim
   - Backend → `PlayLog` modeline kayıt
   - Başarılı gönderimler → `gonderilme_tarihi` set edilir

---

## Lokal Servisler, Queue/Cache/Log Mantığı

### SQLite Schema (`src/db.js`)

**Kategori/Soru/Danışma:**
- `kategoriler`: id, slug, ad, ikon, bagli_kategori_id, hedef_cinsiyet_id, aktif, hedef_cinsiyetler JSON, hedef_yas_araliklari JSON
- `sorular`: id, kategori_id, metin, sira, hedef_cinsiyet_id, hedef_cinsiyetler JSON, hedef_yas_araliklari JSON, eslesme_kurallari JSON
- `cevaplar`: id, soru_id, metin, sira
- `cevap_etken_madde`: cevap_id, etken_madde_id, aktif
- `etken_maddeler`: id, ad, slug, aktif
- `danisma_kategorileri`: id, slug, ad, ikon, ust_kategori_id, aktif

**Playlist/Creative:**
- `creatives`: id, campaign_id, media_url, duration_seconds, name, type (creative/house_ad), checksum
- `playlists`: id, target_date, target_hour, version, items JSON
- `playlist_items`: playlist_id, asset_type, asset_id, duration_seconds, playback_order

**Outbox:**
- `oturum_outbox`: id, payload JSON, olusturulma_tarihi, gonderilme_tarihi (null = pending)
- `reklam_gosterim_outbox`: id, payload JSON, olusturulma_tarihi, gonderilme_tarihi (null = pending)

**Meta:**
- `kiosk_meta`: key, value (iot_token, playlist_version, last_sync_at)
- `media_cache`: url, local_path, cached_at, checksum

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

**İlk açılış:**
1. `resolveRuntimeSettings` fonksiyonu → env'den `KIOSK_APP_KEY` ve `KIOSK_MAC` oku
2. Eğer SQLite'da `iot_token` yoksa → `POST /api/kiosk/v1/{kiosk_id}/provision/` → IoT token al
3. IoT token → `kiosk_meta` tablosuna yaz
4. Sonraki isteklerde `Authorization: Bearer {iot_token}` kullanılır

**Token refresh:**
- `refreshIotTokenIfNeeded` fonksyonu → token expiry kontrolü (şu an placeholder, tam implementasyon belirsiz)

---

## Reklam, Kategori, Session/Log Akışındaki Rolü

### Kategori Akışı
1. Backend → `/api/kiosk/v1/{kiosk_id}/sync/` endpoint'i → kategorileri JSON döner
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
4. Scheduler → `pushOutbox` → backend'e batch gönderim
   - `POST /api/kiosk/v1/{kiosk_id}/sync/` → `sessions` array
5. Backend → `OturumLogu` modeline kayıt (idempotency_anahtari ile duplikasyon koruması)

### Impression Log Akışı
1. Kiosk UI AdStrip → creative oynatma başlar → `play_started` timestamp
2. Kiosk UI AdStrip → creative oynatma biter → `play_ended` timestamp, `completed` bool
3. Kiosk UI → `POST http://localhost:5234/ad-impressions` → impression JSON payload
   ```json
   {
     "creative_id": "uuid",
     "playlist_id": "uuid",
     "play_started": "2026-06-05T10:30:00Z",
     "play_ended": "2026-06-05T10:30:15Z",
     "completed": true,
     "failure_reason": null
   }
   ```
4. Lokal API → SQLite `reklam_gosterim_outbox` → insert
5. Scheduler → `pushOutbox` → backend'e batch gönderim
   - `POST /api/kiosk/v1/{kiosk_id}/proof-of-play/` → `logs` array
6. Backend → `PlayLog` modeline bulk insert

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

---

## Do Not Change Without Checking

**Critical SQLite schema and sync contracts:**

1. **SQLite Table Schema:**
   - `kategoriler`, `sorular`, `cevaplar`, `etken_maddeler`, `danisma_kategorileri`
   - `creatives`, `playlists`, `playlist_items`
   - `oturum_outbox`, `reklam_gosterim_outbox`
   - Breaking: data sync/query fails

2. **Backend Sync Response Format:**
   - Must match backend `/api/kiosk/v1/{id}/sync/` response
   - Breaking: SQLite upsert fails

3. **Outbox Payload Format:**
   - Session: `{ idempotency_key, yas_araligi_id, cinsiyet_id, kategori_id, qr_kodu, cevaplar, onerilen_etken_maddeler, tamamlandi }`
   - Impression: `{ creative_id, playlist_id, play_started, play_ended, completed, failure_reason }`
   - Breaking: backend cannot parse

4. **Scheduler Intervals:**
   - pullFromCentral: 5 min
   - pingAndSyncPlaylist: 10 min
   - pushOutbox: 1 min
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
EISA_LOG_DIR=/var/log/eisa
EISA_CENTRAL_API_BASE=https://api.eisa.com.tr
```

> Not: API `EISA_` prefix'li env değişkenleri kullanır (`config.js`).

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
3. **Token refresh logic:** `refreshIotTokenIfNeeded` fonksiyonu placeholder, token expiry kontrolü tam değil. (Belirsiz)
4. **WiFi setup:** `nmcli` çağrıları Linux'a özel, geliştirme ortamında (Windows/macOS) çalışmaz. (Belirsiz)
5. **Session idempotency key:** `idempotency_key` kiosk UI tarafından mı üretiliyor, backend duplikasyon kontrolü düzgün çalışıyor mu? (Doğrulanmalı)
6. **Playlist version mismatch:** Kiosk uzun süre offline kalırsa playlist versiyonu çok eski olur, backend eski versiyonları tutuyor mu? (Belirsiz)

---

**Satır sayısı: ~260**
