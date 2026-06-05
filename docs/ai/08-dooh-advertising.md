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
- `backend/apps/campaigns/urls.py` → `/api/kiosk/v1/{id}/proof-of-play/` mapping (line 58)
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
    kiosk = FK(Kiosk)
    target_date = DateField
    target_hour = PositiveSmallIntegerField(0-23)
    version = PositiveIntegerField
    locked = BooleanField(default=False)
    total_duration_seconds = PositiveIntegerField
    items = JSONField  # [{ asset_type, asset_id, duration, order }]
    metadata = JSONField  # { generated_at, campaign_count, ... }
```

### Versioning
```
1. Playlist üretildiğinde version artırılır
2. Kiosk → GET /api/kiosk/v1/{id}/ping/ → { playlist_version: 42 }
3. Eğer lokal version != server version → playlist indir
4. GET /api/kiosk/v1/{id}/playlist/?date=YYYY-MM-DD
```

---

## PlaylistItem Model

```python
class PlaylistItem(BaseModel):
    playlist = FK(Playlist)
    asset_type = Choices(creative, house_ad)
    asset_id = UUIDField
    duration_seconds = PositiveSmallIntegerField
    playback_order = PositiveIntegerField
```

---

## HouseAd Model

```python
class HouseAd(BaseModel):
    name = CharField
    media_url = URLField(https only)
    duration_seconds = PositiveSmallIntegerField
    priority = PositiveSmallIntegerField(default=100)
    active = BooleanField(default=True)
    checksum = CharField
```

### Usage
- Slot boşsa (capacity < 60sn) → HouseAd filler
- Priority order (düşük değer önce)
- Always available (no date/targeting constraints)

---

## Kiosk Playlist Sync

### Flow
```
1. Scheduler (kiosk_edge/api-node: pingAndSyncPlaylist, 10dk)
   → GET /api/kiosk/v1/{kiosk_id}/ping/
   → Response: { playlist_version: 42 }

2. Lokal version kontrolü (SQLite kiosk_meta.playlist_version)
   → Eğer farklıysa:

3. GET /api/kiosk/v1/{kiosk_id}/playlist/?date=YYYY-MM-DD
   → Response:
     {
       "id": "uuid",
       "target_date": "2026-06-05",
       "target_hour": 10,
       "version": 42,
       "items": [
         {
           "asset_type": "creative",
           "asset_id": "uuid",
           "media_url": "https://...",
           "duration_seconds": 15,
           "playback_order": 1
         },
         ...
       ]
     }

4. SQLite upsert (playlists, playlist_items)

5. UPDATE kiosk_meta SET value=42 WHERE key='playlist_version'
```

---

## Ad Playback (kiosk_edge/ui)

### AdStrip Component
```svelte
<script>
  let playlist = [];
  let currentIndex = 0;

  onMount(async () => {
    const res = await fetch('http://localhost:5234/playlist?date=2026-06-05');
    playlist = res.items;
    startPlayback();
  });

  function startPlayback() {
    const item = playlist[currentIndex];
    playMedia(item);
    
    setTimeout(() => {
      currentIndex = (currentIndex + 1) % playlist.length;
      startPlayback();
    }, item.duration_seconds * 1000);
  }

  function playMedia(item) {
    const playStarted = new Date().toISOString();
    
    // <video> or <img> playback
    // onEnded or setTimeout → impression log
    
    const playEnded = new Date().toISOString();
    logImpression({
      creative_id: item.asset_id,
      playlist_id: playlist.id,
      play_started: playStarted,
      play_ended: playEnded,
      completed: true
    });
  }
</script>
```

### 60sn Loop
- Playlist items sırayla oynatılır (playback_order)
- Son item bittikinde başa dön
- Loop infinite

---

## Proof-of-Play (PlayLog)

### Model
```python
class PlayLog(BaseModel):
    kiosk = FK(Kiosk)
    playlist = FK(Playlist, nullable)
    creative = FK(Creative, nullable)
    house_ad = FK(HouseAd, nullable)
    play_started = DateTimeField
    play_ended = DateTimeField
    completed = BooleanField
    failure_reason = CharField(nullable)
```

**Backend implementation:**
- File: `backend/apps/campaigns/views_v2.py`
- Class: `ProofOfPlayView` (line 1068)
- URL: `POST /api/kiosk/v1/{kiosk_id}/proof-of-play/`
- Bulk ingest: `PlayLog.objects.bulk_create(bulk, batch_size=500)` (line 1101)

### Outbox Flow
```
1. Kiosk UI (AdStrip.svelte) → logCurrentImpression()
   → logAdImpression({ assetId, assetType, shownAt, durationMs })
   → POST http://localhost:5234/api/reklam-gosterim

2. api-node (server.js line 406) → reklam_gosterim_outbox INSERT
   { asset_id, asset_type, played_at, duration_played }

3. Scheduler → pushToCentral() (1dk interval)
   → reads reklam_gosterim_outbox WHERE gonderilme_tarihi IS NULL
   → POST /api/kiosk/v1/{kiosk_id}/proof-of-play/ { logs: [...] }

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
# Toplam impression
PlayLog.objects.filter(campaign__id=campaign_id).count()

# Completion rate
completed = PlayLog.objects.filter(completed=True).count()
total = PlayLog.objects.count()
rate = completed / total

# Kiosk bazında performans
PlayLog.objects.values('kiosk__ad').annotate(count=Count('id'))
```

---

## Bilinen Riskler

1. **Campaign targeting priority:** Legacy M2M vs CampaignTarget — hangisi öncelikli? (Belirsiz / doğrulanmalı)
2. **Playlist generation job tracking:** `GenerationJob` modeli mevcut ama job durumu belirsiz (Belirsiz / doğrulanmalı)
3. **Slot overflow:** 60sn'den fazla campaign varsa ne olur? (Belirsiz / doğrulanmalı)
4. **Playlist version mismatch:** Kiosk uzun süre offline kalırsa eski versiyon oynatılır mı? (Belirsiz / doğrulanmalı)
5. **Media cache:** Creative medya cache mekanizması placeholder (Belirsiz / doğrulanmalı)

---

**Satır sayısı: ~250**
