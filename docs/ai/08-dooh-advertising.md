# DOOH Advertising System

**Amaç:** Digital Out-Of-Home reklam sistemi mimarisini, playlist üretimini, offline senkronizasyonu dokümante etmek.

---

## When To Read This File

- Yeni kampanya özellikleri eklerken
- Playlist generation sorunlarında
- Reklam oynatım problemlerinde
- Slot kapasite hesaplamalarında
- Proof-of-play tracking için

---

## Important Source Files

- `backend/apps/campaigns/models.py` — Campaign/Creative/Playlist/PlayLog models
- `backend/apps/campaigns/services/scheduler.py` — Playlist generation
- `backend/apps/campaigns/views.py` — `MediaUploadView` (kalici URL, DOOH_PERSISTENT_MEDIA_URL flag)
- `backend/apps/core/services/storage_service.py` — `upload_file_with_checksum`, `public_url` (Faz 0.5)
- `backend/apps/campaigns/views_v2.py` → DOOH v2 API
- `backend/apps/campaigns/urls.py` → kiosk endpoint mappings
- `kiosk_edge/api-node/src/db.js` — playlists/playlist_items/reklam_gosterim_outbox tables
- `kiosk_edge/api-node/src/mediaCache.js` — medya indirme/cache (source_url/checksum staleness)
- `kiosk_edge/api-node/src/server.js` → `POST /api/reklam-gosterim` handler
- `kiosk_edge/api-node/src/scheduler.js` → `pushToCentral()` proof-of-play forwarding
- `kiosk_edge/ui/src/components/AdStrip.svelte` → `logCurrentImpression()` function
- `kiosk_edge/ui/src/lib/api.js` → `logAdImpression()` client function
- `web_panels/src/views/admin/CampaignWizard.vue` — Campaign management
- `web_panels/src/services/dooh.js` — `uploadMedia()` (object_key, media_url, checksum, url alias)

---

## DOOH v2 Architecture

### Core Entities

```
Campaign (reklam kampanyası)
  ├── Creative[] (medya: video/image)
  ├── ScheduleRule (frekans matrisi)
  └── CampaignTarget[] (lokasyon hedefi: il/ilce/eczane)

Playlist (60sn döngü, pre-computed)
  └── PlaylistItem[] (sıralı creative/house_ad listesi)

HouseAd (filler reklam, slot boşsa oynatılır)

PlayLog (impression tracking, proof-of-play)
```

---

## Campaign Model (Faz 7 — Güncel)

```python
class Campaign(BaseModel):
    advertiser_id = UUIDField(nullable)
    advertiser_name = CharField
    name = CharField
    start_date = DateTimeField
    end_date = DateTimeField
    status = Choices(ACTIVE, PAUSED, COMPLETED)

    # Öncelik (placement ordering)
    priority = PositiveSmallIntegerField(default=50)  # 1=highest, 100=lowest

    # Kapsam & ardışıklık
    target_scope = Choices(ALL, RULES)
    follows = FK(self, nullable)  # A→B ardışıklık (set_campaign_follows servisi)

    # Faz 7'de KALDIRILDI: impression_goal, frequency_cap_per_hour, is_guaranteed
    # Canonical: DeliveryRule(CAMPAIGN_TOTAL / GUARANTEED)

    # Legacy M2M — fiziksel tablo korunuyor (legacy data compat); yeni kampanyalar CampaignTarget kullanır
    target_pharmacies = M2M(Eczane)  # Faz 7'den itibaren API üzerinden YAZILMIYOR
```

### Status Lifecycle
```
ACTIVE → campaign runs if date range valid
PAUSED → campaign temporarily disabled
COMPLETED → campaign ended (manual or auto after end_date)
```

---

## CampaignTarget (Location Targeting)

```python
class CampaignTarget(BaseModel):
    campaign = FK(Campaign)
    target_type = Choices(IL, ILCE, ECZANE)
    il = FK(Il, nullable)
    ilce = FK(Ilce, nullable)
    eczane = FK(Eczane, nullable)
```

### Examples
```
IL:     target_type=IL, il=Ankara    → tüm Ankara eczaneleri
ILCE:   target_type=ILCE, ilce=Çankaya → tüm Çankaya eczaneleri
ECZANE: target_type=ECZANE, eczane=xyz → tek spesifik eczane
```

### Legacy vs New
- **Legacy:** `Campaign.target_pharmacies` M2M — fiziksel tablo korunuyor ama yeni kampanyalarda kullanılmıyor
- **New:** `CampaignTarget` hiyerarşi (IL/ILCE/ECZANE) — canonical targeting
- **Faz 7:** `target_pharmacies` artık API üzerinden yazılmıyor; CampaignWizard yalnız CampaignTarget kullanır

---

## Creative Model

```python
class Creative(BaseModel):
    campaign = FK(Campaign)
    media_url = URLField(https only)   # kalici URL (Faz 0.5+)
    duration_seconds = PositiveSmallIntegerField(1-60)
    name = CharField
    checksum = CharField(max_length=128)  # 'sha256:<hex>' formati
    object_key = CharField(null=True)     # Faz 0.5: S3 object key
```

### Media Upload Flow (Faz 0.5+)

**Feature flag:** `DOOH_PERSISTENT_MEDIA_URL` (settings)
- `False` (varsayilan) = legacy presigned URL davranisi
- `True` = kalici URL akisi aktif

Flag=True akisi:
```
1. SuperAdmin -> POST /api/campaigns/upload-media/ (multipart/form-data)
2. Backend -> MinIO/S3 upload (upload_file_with_checksum, SHA-256 stream)
3. Response: { object_key, media_url, checksum, url (alias), filename, object_name (alias) }
   media_url = https://files.eisa.com.tr/eisa-files/ads/{uuid}.mp4  (kalici)
   checksum  = 'sha256:<hex>'
4. POST /api/campaigns/v2/creatives/ { campaign_id, media_url, duration_seconds }
   object_key -> serializer'da media_url'den otomatik turetilir
```

### URL Format (production)
```
S3_ENDPOINT = files.eisa.com.tr
S3_BUCKET   = eisa-files
S3_FORCE_PATH_STYLE = True
Kalici URL  = https://files.eisa.com.tr/eisa-files/<object_key>
Presigned   = https://files.eisa.com.tr/eisa-files/<key>?X-Amz-Expires=...
```

### Checksum contract
- Backend: `Creative.checksum = 'sha256:<hex>'` (storage_service tarafindan)
- Kiosk sync: `creatives[].checksum = 'sha256:<hex>'` -> `source_checksum`
- Kiosk local: `media_cache.file_checksum = '<hex>'` (raw, prefix yok - downloadToFile)
- Karsilastirma: `source_checksum` freshness icin; `file_checksum` bilgi amacli

### Backfill (eski presigned kayitlar)
```bash
python manage.py backfill_media_object_keys           # dry-run
python manage.py backfill_media_object_keys --apply   # HEAD dogrulamali
```

---

## ScheduleRule Model

```python
class ScheduleRule(BaseModel):
    campaign = OneToOneField(Campaign)
    frequency_type = Choices(PER_LOOP, PER_HOUR, PER_DAY)
    frequency_value = PositiveIntegerField
    target_hours = JSONField(nullable)  # [9, 10, 11, 12, 13] or None=all day
```

### Examples
```
PER_LOOP: frequency_value=1 → her 60sn döngüde 1 kez oynat
PER_HOUR: frequency_value=3 → saatte 3 kez oynat
PER_DAY:  frequency_value=50 → günde 50 kez oynat

target_hours: [9,10,11,12,13,14] → sadece bu saatlerde oynat
target_hours: null → tüm gün oynat
```

---

## Playlist Generation

### V1 Scheduler: `generate_for_kiosk(date, kiosk)` *(mevcut, Faz 0–Faz 1)*

ScheduleRule tabanlı 4-pass: PER_LOOP / PER_HOUR / PER_DAY / HouseAd filler.
V1 motor Faz 2'de shadow modda PlacementEngine V2 ile yarışacak.

**Algorithm:**
```
1. Kiosk'un eczanesini bul
2. date/kiosk için aktif kampanyaları filtrele:
   - status=ACTIVE
   - start_date <= date <= end_date
   - CampaignTarget match (il/ilce/eczane) — target_scope NULL=legacy ALL davranışı
   - ScheduleRule.target_hours match (şimdiki saat)
3. Kampanyaları priority'ye göre sırala (priority — küçük değer önce; Faz 7: is_guaranteed kaldırıldı)
4. 60sn slot hesaplama (4-pass)
5. Playlist + PlaylistItem create; version bump
```

### Faz 1 Yeni Modeller
- `DeliveryRule` (ScheduleRule halefi): delivery_type TIME_WINDOW/PER_HOUR/PER_DAY/CAMPAIGN_TOTAL/LEGACY_PER_LOOP; guarantee_mode GUARANTEED/BEST_EFFORT; max_per_hour
- `PlanningRun`/`KioskDayQuota`: CAMPAIGN_TOTAL global kota yönetimi
- `Campaign.follows`: A→B ardışıklık (yalnız set_campaign_follows() servisi)
- Medya URL kalıcı: S3_PUBLIC_BASE_URL/object_key (Faz 0.5+)
- target_scope: ALL|RULES|null-legacy (yeni create API'de zorunlu)

### Priority (Faz 7)
```
priority=1 (highest) → placed first
priority=100 (lowest) → placed last
is_guaranteed kaldırıldı (Faz 7); canonical: DeliveryRule.guarantee_mode=GUARANTEED
```

---

## Playlist Model

```python
class Playlist(BaseModel):
    id = UUIDField(pk)
    kiosk = FK(Kiosk)
    target_date = DateField
    target_hour = PositiveSmallIntegerField(0-23)   # Istanbul YEREL saati
    loop_duration_seconds = PositiveSmallIntegerField(default=60)
    version = PositiveIntegerField(default=1)
    # NOT: item'lar ayri PlaylistItem satirlarinda tutulur (JSONField DEGIL).
    # unique(kiosk, target_date, target_hour)
```

> **Zaman dilimi:** `target_hour` admin'in girdigi YEREL (Europe/Istanbul)
> saattir; backend `USE_TZ=True`, `TIME_ZONE="Europe/Istanbul"`. Kiosk dogru
> playlist'i secmek icin duvar saatini Istanbul'a gore hesaplar (bkz. Timezone).

### Versioning
```
1. Playlist üretildiğinde version artırılır
2. Kiosk → GET /api/kiosk/v1/ping/ → { playlist_version: 42 }
3. Eğer lokal version != server version → playlist indir
4. GET /api/kiosk/v1/playlist/?date=YYYY-MM-DD
```

---

## PlaylistItem Model

```python
class PlaylistItem(BaseModel):
    id = UUIDField(pk)
    playlist = FK(Playlist)
    creative = FK(Creative, null=True)     # creative VEYA house_ad (biri dolu)
    house_ad = FK(HouseAd, null=True)      # filler (Pass 4) icin
    playback_order = PositiveSmallIntegerField
    estimated_start_offset_seconds = PositiveSmallIntegerField  # SAAT-mutlak 0..3599
```

> `estimated_start_offset_seconds` = `loop_index * loop_duration_seconds + slot_offset`
> yani saatin tamami boyunca mutlak ofset (0..3599), tek bir 60sn loop'a gore
> degil. Kiosk slot hizalamasi bu nedenle 3600sn'lik saatlik dongu uzerinden
> yapilir (bkz. Slot Hizalama).
>
> API contract'ta (`KioskPlaylistItemSerializer`) bu alanlar ayrica
> `asset_id` + `asset_type` ("creative"|"house_ad") + `media_url` +
> `duration_seconds` olarak duzlestirilir.

---

## HouseAd Model

```python
class HouseAd(BaseModel):
    id = UUIDField(pk)
    name = CharField
    media_url = URLField(https only)
    duration_seconds = PositiveSmallIntegerField(1-60, default=10)
    aktif = BooleanField(default=True)            # NOT: "aktif" (TR), "active" degil
    priority = PositiveSmallIntegerField(default=100)
```

### Usage
- Slot boşsa (capacity < 60sn) → HouseAd filler
- Priority order (düşük değer önce)
- Always available (no date/targeting constraints)

---

## Kiosk Playlist Sync

### Flow
```
1. Scheduler (kiosk_edge/api-node: pingAndSyncPlaylist, ping ~60sn;
   ayrica pull 900sn / push 300sn — config.js varsayilanlari)
  → GET /api/kiosk/v1/ping/
   → Response: { kiosk_id, date, playlist_version: 42, updated_at, server_time }

2. Lokal version kontrolü (SQLite kiosk_meta.playlist_version)
   → Eğer server > lokal ise:

3. GET /api/kiosk/v1/playlist/?date=YYYY-MM-DD  (Istanbul yerel tarih)
   → Response (GÜNÜN TÜM SAATLERİ tek istekte):
     {
       "kiosk_id": 12,
       "target_date": "2026-06-05",
       "loop_duration_seconds": 60,
       "playlists": [
         {
           "id": "uuid",
           "target_hour": 10,
           "version": 42,
           "loop_duration_seconds": 60,
           "items": [
             {
               "id": "uuid",
               "asset_type": "creative",
               "asset_id": "uuid",
               "media_url": "https://...",
               "duration_seconds": 15,
               "playback_order": 1,
               "estimated_start_offset_seconds": 0
             }
           ]
         }
       ]
     }

4. SQLite upsert (playlists, playlist_items)

5. UPDATE kiosk_meta SET value=42 WHERE key='playlist_version'
```

---

## Ad Playback (kiosk_edge/ui)

### AdStrip Component

Kiosk UI, merkezi backend'e DEGIL, yerel api-node'a (`http://127.0.0.1:8765`)
baglanir. `GET /api/playlist/current` o anki saatin playlist'ini (yoksa
fallback) doner. Oynatim iki moddadir:

- **Slot modu** (gercek playlist): Duvar saatine gore SAATLIK (3600sn) dongu
  icindeki konuma karsilik gelen oge gosterilir. Boylece tum kiosklar ayni
  anda dogru slotu oynatir ve proof-of-play kayitlari hizalanir.
  ```js
  const HOUR_SECONDS = 3600;
  const pos = Math.floor(Date.now() / 1000) % HOUR_SECONDS; // saat icindeki saniye
  // offset <= pos olan SON oge aktif; sonraki sinir = sonraki offset ya da 3600
  ```
- **Sirali (fallback) modu**: Playlist yoksa veya offset uretilmemisse,
  ogeleri kendi `duration_seconds` surelerine gore dongusel oynatir.

Oge degistiginde onceki slot icin impression backend'e loglanir
(`logCurrentImpression()` -> `POST /api/reklam-gosterim`).

> **Onemli:** `estimated_start_offset_seconds` saat-mutlak (0..3599) oldugundan
> dongu suresi `loop_duration_seconds` (60) DEGIL, tam saat (3600) olmalidir.
> Aksi halde yalnizca ilk dakikanin (loop 0) ogeleri oynar; PER_HOUR/PER_DAY
> reklamlar hic gosterilmez.

### Saatlik Dongu
- Playlist ogeleri saat-mutlak offset'e gore duvar saatiyle hizalanir.
- Saat degistiginde (Istanbul yereli) UI playlist'i yeniden yukler.
- Saat icinde dongu sonsuzdur (pos saat sonunda 0'a sarar).

---

## Proof-of-Play (PlayLog)

### Model
```python
class PlayLog(BaseModel):
    id = UUIDField(pk)
    kiosk = FK(Kiosk)
    creative = FK(Creative, null=True, on_delete=SET_NULL)
    house_ad = FK(HouseAd, null=True, on_delete=SET_NULL)
    played_at = DateTimeField(db_index=True)
    duration_played = PositiveSmallIntegerField   # gercekten oynatilan saniye
```

> Eski tasarimdaki `play_started`/`play_ended`/`completed`/`failure_reason`

---

## Faz Durumları

### Faz 2 — PlacementEngine V2 Shadow Mode: TAMAMLANDI (2026-07-22)

- **Local PostgreSQL migration 0015–0018:** BAŞARILI
  - 0015: `object_key` alanları (Creative, HouseAd)
  - 0016: Faz 1 additive schema (PlanningRun, DeliveryRule, KioskDayQuota, CampaignTotalAllocation, KioskDesiredBundle)
  - 0017: KioskDayQuota check constraints (quota≥0, placed≥0, placed≤quota)
  - 0018: Campaign follows unique constraint
- **Local schema ve constraint doğrulaması:** BAŞARILI (docker exec psql doğrulandı)
- **PlacementEngine V2:** TAMAMLANDI (`placement_engine_v2.py`)
- **GlobalQuotaService:** TAMAMLANDI (`quota_service.py`, parent row locking)
- **Shadow mode scheduler integration:** TAMAMLANDI (V1 authoritative, V2 loglar)
- **Campaigns testleri (Faz 2):** 169 passed, 0 failed
- **Tüm backend testleri (Faz 2):** 348 passed, 7 skipped, 0 failed
- **V2 active/authoritative kullanım:** HENÜZ AKTİF DEĞİL (production cutover Faz 4+)

### Faz 3 — Simulation / Activation / Reservation: TAMAMLANDI (2026-07-22)

- **Simulation API:** `POST /api/campaigns/v2/campaigns/{id}/simulate/`
  - Read-only, sıfır DB mutation
  - PlacementEngineV2 ile aynı hesaplama yolu
  - sim == generate == activation fingerprint doğrulandı
- **Activation API:** `POST /api/campaigns/v2/campaigns/{id}/activate/`
  - DOOH_ENGINE_V2=active gerektirir
  - GUARANTEED: all-or-nothing (atomic rollback on any failure)
  - BEST_EFFORT: mevcut kapasiteye sığanı yerleştir
  - CAMPAIGN_TOTAL global invariant: select_for_update ile serialize edildi
- **Feature flag:** off → shadow → active (off/shadow V1 authoritative, active = V2 activate endpoint açık)
- **Idempotency:** Re-activation replaces (delete+recreate), not appends
- **Faz 3 testleri:** 21 passed (FA-01..FA-16), PostgreSQL race testleri dahil
- **Tüm backend testleri (Faz 3):** 371 passed, 7 skipped, 0 failed
- **git diff --check:** Exit 0

### Faz 4 — Invalidation / DB Queue / Staged Publish: TAMAMLANDI (2026-07-22)

- `GenerationJob` DB-backed queue (payload, available_at, attempt_count, max_attempts, lock_expires_at, dedupe_key, RETRY status)
- `InvalidationService._create_or_coalesce_job()` — domain change → queue, `on_commit` ile
- `QueueWorker.process_job()` — fingerprint check inside `select_for_update` lock
- Sinyal tablosu: Campaign/Creative/DeliveryRule/CampaignTarget/HouseAd/Kiosk/Eczane
- **Migrations:** campaigns/0019_faz4_generation_queue_fields
- **Backend testleri:** 31 test (Faz 4) + 12 hardening regression testi

### Faz 5 — Desired/Applied Version + Kiosk ACK/Horizon Sync: TAMAMLANDI (2026-07-22)

- `Kiosk`: +`last_v2_fingerprints`, +`applied_playlist_version`, +`playlist_applied_at`, +`applied_horizon_start`, +`applied_horizon_end`
- `KioskManifestView`: `GET /api/kiosk/v1/manifest/` — 3 günlük snapshot, `select_for_update`
- `KioskAckView`: `POST /api/kiosk/v1/ack/` — APPLIED/IDEMPOTENT/STALE_IGNORED/FUTURE_REJECTED(409)
- Kiosk edge: pending_ack SQLite tablosu, capped backoff (30s→1800s), `clearPendingAckIfMatches` (compare-and-swap)
- **Migrations:** pharmacies/0008_faz4_faz5_kiosk_fields
- **Backend testleri:** 18 Faz5 + 12 regression | **Node.js testleri:** 15 manifest

### Faz 6 — CampaignWizard + DoohControlCenter: TAMAMLANDI (2026-07-22)

**CampaignWizard (`web_panels/src/views/admin/CampaignWizard.vue`):**
- 6 adımlı wizard: Bilgiler → Medya → Hedefleme → Frekans → Simülasyon → Aktive Et
- Create/Edit mode: PATCH (existing fields korunur)
- IL/ILCE/ECZANE targeting: `CampaignTarget` kayıtları; `Campaign.target_pharmacies` KULLANILMAZ
- Creative upload: `POST /api/campaigns/upload-media/`, response: `{ media_url, object_key, checksum }`
- ScheduleRule: `{ frequency_type, frequency_value, target_hours }` — `target_days` backend'de yok (UI disabled)
- Simülasyon: read-only, `POST .../simulate/`; form değişince stale; stale iken activate disabled
- Activation: `POST .../activate/`; EisaDeleteConfirm modal; double-submit engeli
- Kaydedilmemiş değişiklik: `formDirty` watcher + `confirm()` close diyaloğu

**DoohControlCenter (`web_panels/src/views/admin/DoohControlCenter.vue`):**
- Route: `/admin/dooh/control-center` (SuperAdmin RBAC korumalı)
- Kampanya pause/resume/cancel/delete (EisaDeleteConfirm)
- Job polling: PENDING/RUNNING → `setInterval(8000)`; terminal durumda `clearInterval`; unmount cleanup
- Kiosk rollout tablosu: desired/applied/horizon; `calcKioskRolloutStatus` composable
- `applied null` → "ACK Bekleniyor" (hata değil)

**Ortak:**
- `composables/useKioskRolloutStatus.js`: tek merkezi rollout hesap kaynağı
- `dooh.js`: `simulateCampaign`, `activateCampaign`, `getCampaignTargets`, `setCampaignTargets`, `getKioskHealth` export'ları
- `lookups.js`: `getIller`, `getIlceler` — dooh.js'de kopyası yok
- **Frontend testleri (Faz 6):** 43 passed (FW-01..FW-20 + regresyon)
- **Backend testleri:** 430 SQLite + 16 PostgreSQL
- **Build:** exit 0

### Faz 7 — Legacy UI Read-Only + Cleanup: UYGULAMASI HAZIR (2026-07-22)

**Gerçekleştirilenler:**
- PlaylistEditor → "Gelişmiş Manuel Yayın" (salt okunur); CRUD butonları gizlendi
- Campaign.is_guaranteed, impression_goal, frequency_cap_per_hour model'den **kaldırıldı** (migration 0020)
- CampaignSerializer bu alanları artık sergilemiyor/kabul etmiyor
- target_pharmacies M2M: fiziksel tablo korunuyor; API write path temizlendi
- DOOH_ENGINE_V2 flag kaldırıldı → V2 canonical ve her zaman aktif
- DOOH_ASYNC_QUEUE flag kaldırıldı → async queue canonical ve her zaman aktif
- DOOH_KIOSK_ACK flag kaldırıldı → manifest/ACK endpoint'leri her zaman aktif
- Ping response: desired/applied/horizon alanları her zaman döner (flag koşulsuz)
- scheduler.py: is_guaranteed ordering kaldırıldı; yalnız priority sıralaması
- scheduler.py: V2 shadow comparison kaldırıldı; generate_for_kiosk V1 only (backward compat)
- AdminLayout nav: "Playlist Editörü" → "Gelişmiş Manuel Yayın"
- **Migration:** 0020_faz7_drop_deprecated_campaign_fields.py
- **Backend testleri:** 430 SQLite + 16 PostgreSQL
- **Frontend testleri:** 57 passed (43 Faz 6 + 14 Faz 7)
- Faz 6+7 ortak kapanış testi: **HENÜZ BEKLİYOR**

### Faz 3 Endpoint Contract

```
POST /api/campaigns/v2/campaigns/{id}/simulate/
  Auth: JWT SuperAdmin
  Faz 7: DOOH_ENGINE_V2 flag kaldırıldı; her zaman erişilebilir
  Response 200:
    {
      "campaign_id": "uuid",
      "fingerprint": "hex16",
      "target_kiosks": [1, 2],
      "date_range": ["2026-07-22", ...],
      "kiosk_days": [
        {
          "kiosk_id": 1,
          "date": "2026-07-22",
          "requested": 4,
          "placed": 4,
          "unplaced": 0,
          "capacity_used_seconds": 60,
          "blocking_reasons": [],
          "fingerprint": "abc123"
        }
      ],
      "total_requested": 8,
      "total_placed": 8,
      "total_unplaced": 0,
      "would_succeed": true,
      "blocking_reasons": []
    }
  Response 403: DOOH_ENGINE_V2=off

POST /api/campaigns/v2/campaigns/{id}/activate/
  Auth: JWT SuperAdmin
  Feature: DOOH_ENGINE_V2=active (zorunlu)
  Response 200:
    {
      "campaign_id": "uuid",
      "planning_run_id": "uuid",
      "activated_kiosks": 2,
      "activated_dates": 3,
      "total_placements": 6,
      "fingerprint": "hex16",
      "is_complete": true,
      "blocking_reasons": []
    }
  Response 400: Validation error (no delivery rule, no creative, etc.)
  Response 403: DOOH_ENGINE_V2 != active
  Response 404: Campaign not found
  Response 409: GUARANTEED capacity failure
```

### Kalan Faz Sırası

- **Faz 4:** Production cutover + kiosk ACK + desired/applied bundle versioning (K4)
- **Faz 5:** Kiosk horizon manifest sync
- **Faz 6:** Panel (CampaignWizard targeting + simulate/activate adımları)
- **Faz 7:** ScheduleRule deprecation
> ve `playlist` FK alanlari MEVCUT DEGIL. Kiosk yalnizca `played_at` +
> `duration_played` (+ creative_id ya da house_ad_id) gonderir.

**Backend implementation:**
- File: `backend/apps/campaigns/views_v2.py`
- Class: `ProofOfPlayView` (line 1068)
- URL: `POST /api/kiosk/v1/proof-of-play/`
- Bulk ingest: `PlayLog.objects.bulk_create(bulk, batch_size=500)` (line 1101)

### Outbox Flow
```
1. Kiosk UI (AdStrip.svelte) → logCurrentImpression()
   → logAdImpression({ assetId, assetType, shownAt, durationMs })
   → POST http://127.0.0.1:8765/api/reklam-gosterim

2. api-node (server.js line 406) → reklam_gosterim_outbox INSERT
   { asset_id, asset_type, played_at, duration_played }

3. Scheduler → pushToCentral() (push ~300sn interval)
   → reads reklam_gosterim_outbox WHERE gonderilme_tarihi IS NULL
  → POST /api/kiosk/v1/proof-of-play/ { logs: [...] }

4. Backend (ProofOfPlayView) → PlayLog.bulk_create()

5. api-node → DELETE FROM reklam_gosterim_outbox WHERE id IN (...)
```

**HouseAd logging implementation:**
- UI: `AdStrip.svelte` correctly sends `asset_type` and `asset_id`
- api-node: `server.js` stores both fields in outbox
- api-node: `scheduler.js` `pushToCentral()` (line 534) correctly maps:
  - if `asset_type === 'house_ad'` → `house_ad_id`
  - else → `creative_id`
- Backend: `ProofOfPlayView` accepts both `creative_id` and `house_ad_id`

**Status:** HouseAd impression logging verified as implemented correctly.

### Analytics
```python
# Bir kampanyanin toplam impression'i (PlayLog -> creative -> campaign)
PlayLog.objects.filter(creative__campaign_id=campaign_id).count()

# Tam izlenme orani (oynatilan sure >= creative suresi)
from django.db.models import F
completed = PlayLog.objects.filter(
    duration_played__gte=F("creative__duration_seconds")
).count()
total = PlayLog.objects.count()
rate = completed / total if total else 0

# Kiosk bazında performans
PlayLog.objects.values('kiosk__ad').annotate(count=Count('id'))
```

> PlayLog'da `completed` BooleanField'i YOKTUR; tam izlenme `duration_played`
> ile creative suresi karsilastirilarak turetilir. Kampanya iliskisi de
> dogrudan degil `creative__campaign` uzerindendir.

---

## Zaman Dilimi & Slot Hizalama (Onemli)

Backend `USE_TZ=True`, `TIME_ZONE="Europe/Istanbul"`. Playlist `target_hour`
degerleri admin'in girdigi YEREL (Istanbul) saatlerdir. Kiosk cihazi UTC ya da
baska bir TZ ile calisabilecegi icin dogru playlist'i secmek adina duvar saati
DAIMA Europe/Istanbul'a gore hesaplanir:

- `kiosk_edge/api-node/src/timezone.js` → `istanbulNow()` (date + hour).
- `server.js` `/api/playlist/current` ve `scheduler.js` playlist cekme → Istanbul
  tarih/saat kullanir.
- `AdStrip.svelte` saat-degisimi tespiti → `Intl` ile Istanbul saati.

Slot hizalama (gercek playlist): `estimated_start_offset_seconds` SAAT-mutlak
(0..3599) oldugundan dongu suresi 3600sn'dir (60sn loop DEGIL). Pozisyon:
`Math.floor(Date.now()/1000) % 3600`. Turkiye sabit UTC+3 oldugundan epoch'un
saat siniri Istanbul `:00` ile cakisir; bu sayede tum kiosklar ayni anda ayni
slotu oynatir ve proof-of-play hizalanir.

---

## Bilinen Riskler

1. **Campaign targeting priority:** Legacy M2M vs CampaignTarget — hangisi öncelikli? (Belirsiz / doğrulanmalı)
2. **Playlist generation job tracking:** `GenerationJob` modeli mevcut ama job durumu belirsiz (Belirsiz / doğrulanmalı)
3. **Slot overflow:** 60sn'den fazla campaign varsa ne olur? (Belirsiz / doğrulanmalı)
4. **Playlist version mismatch:** Kiosk uzun süre offline kalırsa eski versiyon oynatılır mı? (Belirsiz / doğrulanmalı)
5. **Media cache:** Creative medya cache mekanizması placeholder (Belirsiz / doğrulanmalı)

### Çözülen (bu denetimde)
- **TZ kaymasi (ÇÖZÜLDÜ):** Kiosk playlist'i UTC saatine göre seciyordu → reklamlar
  Istanbul yereline göre ~3 saat kayiyordu. Artık Istanbul yerel tarih/saati kullaniliyor.
- **Slot ölçeği (ÇÖZÜLDÜ):** AdStrip slot dongusu 60sn'e göre sariliyordu; saat-mutlak
  offset'lerle yalnızca ilk dakikanın öğeleri oynuyor, PER_HOUR/PER_DAY reklamlar
  hiç gösterilmiyordu. Artık 3600sn'lik saatlik dongu kullaniliyor.
- **Ölü endpoint (ÇÖZÜLDÜ):** `server.js` `/api/lookups/iller*` kaldırılmıs tabloları
  sorguluyordu (db.js v9). Kullanılmadığı için tamamen kaldırıldı.

---

**Satır sayısı: ~250**
