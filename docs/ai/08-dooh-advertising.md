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
- `backend/apps/campaigns/views_v2.py` → `ProofOfPlayView` (line 1068), DOOH v2 API
- `backend/apps/campaigns/urls.py` → `/api/kiosk/v1/proof-of-play/` mapping (line 58)
- `kiosk_edge/api-node/src/db.js` — playlists/playlist_items/reklam_gosterim_outbox tables
- `kiosk_edge/api-node/src/server.js` → `POST /api/reklam-gosterim` handler (line 406)
- `kiosk_edge/api-node/src/scheduler.js` → `pushToCentral()` proof-of-play forwarding
- `kiosk_edge/ui/src/components/AdStrip.svelte` → `logCurrentImpression()` function
- `kiosk_edge/ui/src/lib/api.js` → `logAdImpression()` client function (line 166)
- `web_panels/src/views/admin/CampaignWizard.vue` — Campaign management

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

## Campaign Model

```python
class Campaign(BaseModel):
    advertiser_id = UUIDField(nullable)
    advertiser_name = CharField
    name = CharField
    start_date = DateTimeField
    end_date = DateTimeField
    status = Choices(ACTIVE, PAUSED, COMPLETED)
    
    # Pacing
    impression_goal = PositiveIntegerField(nullable)
    frequency_cap_per_hour = PositiveSmallIntegerField(nullable)
    
    # Priority & guarantee
    priority = PositiveSmallIntegerField(default=50)  # 1=highest, 100=lowest
    is_guaranteed = BooleanField(default=False)
    
    # Legacy targeting (deprecated)
    target_pharmacies = M2M(Eczane)
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
- **Legacy:** `Campaign.target_pharmacies` M2M
- **New:** `CampaignTarget` hiyerarşi
- İkisi birlikte destekleniyor, priority belirsiz (Riskli)

---

## Creative Model

```python
class Creative(BaseModel):
    campaign = FK(Campaign)
    media_url = URLField(https only)
    duration_seconds = PositiveSmallIntegerField(1-60)
    name = CharField
    checksum = CharField  # cache invalidation için
```

### Media Upload Flow
```
1. SuperAdmin → POST /api/campaigns/upload-media/ (multipart/form-data)
2. Backend → MinIO/S3 upload
3. Response: { media_url, checksum }
4. POST /api/campaigns/v2/creatives/ { campaign_id, media_url, duration_seconds }
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

### Scheduler: `generate_for_kiosk(date, kiosk_id)`

**Algorithm:**
```
1. Kiosk'un eczanesini bul
2. date/kiosk için aktif kampanyaları filtrele:
   - status=ACTIVE
   - start_date <= date <= end_date
   - CampaignTarget match (il/ilce/eczane)
   - ScheduleRule.target_hours match (şimdiki saat)
3. Kampanyaları priority'ye göre sırala (düşük değer önce)
4. 60sn slot hesaplama:
   - Pass 1: guaranteed campaigns → creative placement
   - Pass 2: non-guaranteed campaigns (priority order) → creative placement
   - Pass 3: frequency capping kontrolü
   - Pass 4: remaining slots → HouseAd filler
5. Playlist + PlaylistItem create
6. version++ (Kiosk.last_playlist_version)
```

### Slot Calculation
```
60sn total capacity
- Campaign A: 15sn creative, PER_LOOP=1 → 15sn slot
- Campaign B: 10sn creative, PER_HOUR=3 → 10sn slot
- Campaign C: 5sn creative, guaranteed → 5sn slot
- Remaining: 60 - (15+10+5) = 30sn → HouseAd filler
```

### Priority & Guarantee
```
priority=1 (highest) → placed first
priority=100 (lowest) → placed last
is_guaranteed=True → never dropped, even if capacity full
  → drops lower-priority non-guaranteed campaigns
  → or uses Pass 4 filler slots
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
