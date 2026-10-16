# DOOH Advertising System — Kiosk Sponsorluk (cihaz bazlı)

**Amaç:** Kiosk sponsorluk (DOOH) mimarisini, cihaz bazlı atama modelini, yerleşim motorunu, playlist üretimini ve proof-of-play akışını dokümante etmek. Eczacı paneli kampanya sistemi (PharmacyCampaign) de bu dokümana dahildir.

> **2026-10-16 yeniden tasarım (temiz başlangıç):** İl/ilçe/eczane hedefleme, ScheduleRule/DeliveryRule frekansları,
> GUARANTEED/CAMPAIGN_TOTAL, follows/priority, V1 scheduler + PlacementEngineV2 + ActivationService, PlaylistEditor,
> PlaylistTemplate/HourPlan/DayPlan ve PricingMatrix (fiyat matrisi) **tamamen kaldırıldı** (migration 0033 veri temizliği, 0034 şema).
> Sponsorluklar yalnız **kiosk (cihaz) bazlı** atanır; yeni cihaz, atama yapılmadıkça hiçbir sponsorluk göstermez.

---

## Important Source Files

- `backend/apps/campaigns/models.py` — Campaign (Sponsorluk), Creative, **KioskSponsorship**, Playlist, PlaylistItem, PlayLog, GenerationJob, IdleScreenContent, PharmacyCampaign
- `backend/apps/campaigns/services/sponsorship_engine.py` — tek yerleşim motoru (plan / persist / kapasite doğrulama / simülasyon)
- `backend/apps/campaigns/services/queue_worker.py` — GenerationJob kuyruğu → `regenerate_kiosk_day`
- `backend/apps/campaigns/services/invalidation_service.py` — değişiklik → (kiosk, gün) job'ları
- `backend/apps/campaigns/signals.py`, `jobs.py` (nightly = tüm aktif kiosklar × horizon kuyruğa)
- `backend/apps/campaigns/views_v2.py`, `urls.py` — yönetim API'si
- `web_panels/src/views/admin/KioskSponsorship.vue` — `/admin/kiosk-sponsorships` (Kiosk Sponsorluk)
- `web_panels/src/views/admin/SponsorshipDefinitions.vue` — `/admin/campaigns` (Sponsorluk Tanımları)
- `web_panels/src/composables/useSponsorship.js`, `web_panels/src/services/dooh.js`
- Kiosk: `kiosk_edge/ui/src/lib/playlistSlot.js` (saat-içi slot çözümleme — sözleşme DEĞİŞMEDİ)

---

## Veri Modeli

```
Campaign (Sponsorluk): name, advertiser_name, start_date, end_date, status (ACTIVE/PAUSED/COMPLETED)
  └── Creative[]: media_url (bekleme ekranı 9:16), active_media_url (işlem ekranı alt alan), duration_seconds (1-60), name, checksum, object_key
KioskSponsorship (dooh_kiosk_sponsorships) — kiosk × sponsorluk, unique(kiosk, campaign)
  window_start_minute (0..1439), window_end_minute (1..1440, exclusive), count (pencere içinde günlük gösterim N ≥ 1),
  active_weekdays ([1..7] ISO, null/[] = her gün), start_date/end_date (opsiyonel, sponsorluk tarihleriyle kesişir), is_active
Playlist (kiosk, target_date, target_hour, version) → PlaylistItem (creative, playback_order, estimated_start_offset_seconds 0..3599)
PlayLog (proof-of-play), GenerationJob (DB kuyruğu)
```

**Frekans modeli:** Tek kavram "saat aralığı + N gösterim" (ör. 08:00–19:00, 100 kez). Saatte-N / Günde-N / Her-döngü ve garanti kavramları yoktur.

**Opt-in:** Ataması olmayan kiosk 24 boş playlist alır → idle ekranı gösterir.

## Yerleşim Motoru (`sponsorship_engine.py`)

- Bir gün için uygulanabilir atamalar: atama aktif, sponsorluk ACTIVE, tarih sponsorluk + atama aralığında, haftanın günü uygun, ≥1 creative.
- Gösterim i, creative'ler arasında sırayla döner (round-robin, oluşturulma sırasına göre).
- İdeal zaman `t_i = S + (i + phase_j)·(E−S)/N` — pencereye **homojen** yayılır; `phase_j` farklı sponsorlukları kaydırır (art arda yığılma yok).
- Her gösterim idealine en yakın boş yere konur; **saat sınırını aşamaz** ve çakışamaz. Yer yoksa "yerleşemeyen" sayılır.
- Deterministik: aynı girdi → aynı plan ve fingerprint (önizleme = yayın).
- Persist: kiosk+gün için 24 saatlik playlist yeniden yazılır; versiyon = max(Playlist.version, kiosk.last_playlist_version)+1; içerik aynıysa versiyon artmaz.
- **Kapasite doğrulama:** Kayıt (kiosk PUT, kioskl. atama, sponsorluk tarih/durum değişikliği, creative ekleme/değişikliği) tüm ilgili günler için motorla test edilir; yerleşemeyen varsa **kayıt engellenir** (HTTP 400 `capacity_exceeded`).

## Yönetim API'si (JWT SuperAdmin, `/api/campaigns/v2/`)

| Endpoint | Açıklama |
|---|---|
| `campaigns/` CRUD, `campaigns/bulk-action/` | Sponsorluk tanımı (pause/resume/delete) |
| `campaigns/{id}/kiosks/` | Sponsorluğun atandığı kiosklar |
| `campaigns/{id}/assign-kiosks/` | Çoklu kioska atama; zaten atanmış kiosklar **atlanır**; `dry_run`; kapasite reddi varsa hiçbir şey kaydedilmez |
| `creatives/` CRUD | Görseller (alan adı `campaign`) |
| `sponsorship-kiosks/?search=&unassigned=1` | Kiosk listesi + atama sayıları |
| `sponsorship-kiosks/{id}/sponsorships/` GET/PUT | Kioskun atamaları; PUT tam değiştirme |
| `sponsorship-kiosks/{id}/preview/` | Taslak/kayıtlı atamalarla gün planı (HH:MM:SS, saatlik doluluk) — DB yazmaz |
| `sponsorship-kiosks/{id}/copy/` | Kaynak kioskun takvimini hedeflere kopyalar — **üzerine yazar**; `dry_run` fark önizlemesi |
| `sponsorship-kiosks/{id}/simulate/` | Cihaz simülasyonu: `probe` (ör. 15 sn görsel 08:00–19:00 arası en fazla kaç kez; boş kioskta 2640) ve `scenario` (varsayımsal satırlarla uygulanabilirlik) |
| `playlists/day-stream/?kiosk=&date=` | Yayındaki gerçek akış |
| `playlists/jobs/`, `playlists/generate/` | Kuyruk izleme / zorla yeniden üretim |

Kapasite hata şekli: `400 {"code":"capacity_exceeded","detail":"...","conflicts":[{date, campaign_id, campaign_name, requested, placed}]}`.

## Üretim Akışı

1. Atama/sponsorluk/creative/kiosk değişikliği → sinyal → `on_commit` → etkilenen kiosklar × horizon (DOOH_HORIZON_DAYS, varsayılan 3) için GenerationJob.
2. `drain_queue` (30 sn) → `regenerate_kiosk_day` → yeni motor → Playlist/PlaylistItem.
3. Gece işi (`nightly_generate`) tüm aktif kiosklar × horizon için job kuyruğa alır.
4. Kiosk ping/manifest/ack ile yeni versiyonu çeker (sözleşme değişmedi).

## Panel

- **Kiosk Sponsorluk** (`/admin/kiosk-sponsorships`): solda aranabilir kiosk listesi ("Atanmamış" filtresi); sağda sekmeler **Sponsorluklar** (atama tablosu, canlı kapasite), **Yayın Takvimi** (taslak/yayında; 24 saat ısı haritası → dakika/saniye çizelgesi, görsel önizleme), **Simülasyon** (probe + senaryo), **Kopyala** (önizle → onayla, üzerine yazar).
- **Sponsorluk Tanımları** (`/admin/campaigns`): Bilgiler → Medya → Kiosklar (atanmış kiosklar + "Kiosklara Ata").
- Kaldırılanlar: CampaignWizard, PlaylistEditor (Gelişmiş Manuel Yayın), Fiyat Matrisi.

---
## IdleScreenContent Model *(2026-08-16 — HouseAd'in yerine)*

```python
class IdleScreenContent(BaseModel):
    id = BigAutoField(pk)
    baslik = CharField(max_length=250)            # zorunlu (serializer ≤100)
    baslik_en = CharField(blank, null)            # TR/EN, boş = TR fallback
    metin = CharField(max_length=1000)            # zorunlu (serializer ≤300)
    metin_en = CharField(blank, null)             # TR/EN
    aktif = BooleanField(default=True)            # NOT: "aktif" (TR)
    kategori = FK(products.Kategori, null)        # opsiyonel
    # + BaseModel: olusturulma_tarihi / guncellenme_tarihi
    # Tablo: dooh_idle_screen_contents
```

### Kullanım
- "İçerik Yönetimi" idle (bekleme) ekranı başlık/metin içeriği; **medya YOK, HTML YOK, düz metin**
- CRUD API: `GET/POST/PUT/PATCH/DELETE /api/campaigns/v2/idle-contents/` (JWT SuperAdmin, basename `dooh-idle-content`); serializer `id, baslik, baslik_en, metin, metin_en, aktif, kategori, created_at, updated_at`
- Kiosk sync: `/api/kiosk/v1/sync/` → `idle_contents` (yalnız AKTİF; `KioskIdleContentSyncSerializer`)
- Kiosk UI shuffled-bag ile aktif idle içerikleri döndürür (bkz. 04-kiosk-edge-ui.md `idleContentStore.js` / `AdPromo` large)
- Eski `HouseAd` modeli/tablosu (`dooh_house_ads`), viewset (`/api/campaigns/v2/house-ads/`) ve filler mantığı uçtan uca **KALDIRILDI** (migration 0027)

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
### IdleScreen vs AdStrip Medya Secimi

- **IdleScreen**: `item.media_url` (portrait, tam ekran, cover)
- **AdStrip** (islem sirasinda): `item.active_media_url` varsa cover; yoksa `item.media_url` + `object-fit: contain` (letterbox fallback)
- Tek impression kaydedilir; iki ayri impression sistemi yoktur
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


## Proof-of-Play (PlayLog)

### Model
```python
class PlayLog(BaseModel):
    id = UUIDField(pk)
    kiosk = FK(Kiosk)
    creative = FK(Creative, null=True, on_delete=SET_NULL)  # house_ad FK KALDIRILDI (migration 0027)
    played_at = DateTimeField(db_index=True)
    duration_played = PositiveSmallIntegerField   # gercekten oynatilan saniye
```

**Backend implementation:**
- File: `backend/apps/kiosk_api/views.py`
- Class: `KioskProofOfPlayView` (AppKey+MAC; `play_event_id` ile idempotent ingest)
- URL: `POST /api/kiosk/v1/proof-of-play/`
- Bulk ingest: `PlayLog.objects.bulk_create(...)`

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

**Impression logging (creative-only):**
- UI: `AdStrip.svelte` yalnız `asset_type='creative'` öğeleri için impression gönderir
- api-node: `server.js` outbox'a `creative_id` yazar; `scheduler.js` `pushToCentral()` `creative_id` maplar
- Backend: `ProofOfPlayView` `creative_id` kabul eder; `house_ad_id` gelse de yok sayılır (playlist creative-only)

**Status:** HouseAd uçtan uca kaldırıldı (migration 0027); proof-of-play creative-only.

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

## Admin Endpoint — Yayın Akışı (2026-08-09)

```
GET /api/campaigns/v2/playlists/day-stream/?kiosk=<id>&date=YYYY-MM-DD
```
- Read-only; DB mutation yok.
- Dönen: `{ kiosk_id, kiosk_name, is_online, son_goruldu, last_playlist_version, desired_version, applied_version, applied_horizon_end, playlist_applied_at, target_date, hours: [{target_hour, version, items: [...]}] }`
- Her item: `{ id, asset_id, asset_type, name, media_url, active_media_url, duration_seconds, playback_order, estimated_start_offset_seconds }`
- N+1 yok: `prefetch_related("items__creative__campaign")` (playlist creative-only)
- **Desired/applied canonical (2026-08-09):** `desired_version = Kiosk.last_playlist_version`, `applied_version = Kiosk.applied_playlist_version`. `KioskDesiredBundle` KULLANILMAZ (Faz 5 stub, boş). Frontend rollout durumu `calcKioskRolloutStatus` ile hesaplanır (Control Center ile aynı sözleşme).


---

## PharmacyCampaign — Eczacı Paneli Kampanyaları *(2026-07-31, 2026-08-01)*

Kiosk playlist/scheduler/PlayLog sisteminden **tamamen bağımsız** sade kampanya sistemi.

### Model

```python
class PharmacyCampaign(BaseModel):
    id = UUIDField(pk)
    name = CharField
    media_url = URLField           # yatay görsel (eczacı paneli şerit + overlay)
    object_key = CharField(null)   # S3 key (upload servisinden türetilir)
    start_at = DateTimeField
    end_at = DateTimeField
    duration_seconds = PositiveSmallIntegerField(default=15)  # İzin verilenler: 15, 30, 60
    is_active = BooleanField(default=True)
    target_pharmacies = M2M(Eczane)   # tekil eczane hedefi
    target_iller = M2M(Il)            # il hedefi (migration 0024)
    target_ilceler = M2M(Ilce)        # ilçe hedefi (migration 0024)
```

### Feed Endpoint

`GET /api/campaigns/v2/pharmacy-campaigns/feed/` (IsEczaci izni)

- Eczaneyi frontend'den ALMAZ; `request.user.eczane_id` kullanır.
- Eşleşme kuralı (OR): `target_pharmacies__id=eczane_id` VEYA `target_iller__id=il_id` VEYA `target_ilceler__id=ilce_id`
- `.distinct()` — birden fazla koşula uyan kampanya bir kez döner.
- Hiç hedefi olmayan kampanya (üç M2M de boş) feed'e girmez.
- Aktif + tarih aralığı geçerli olması zorunlu.
- Response: `[{id, name, media_url, duration_seconds}]`

### Admin CRUD

`/api/campaigns/v2/pharmacy-campaigns/` (IsSuperAdmin)

- Upload: mevcut `POST /api/campaigns/upload-media/` (shared)
- duration_seconds serializer validation: yalnız 15, 30, 60 kabul edilir. Eski kayıt aynı değerle güncelleniyorsa izin verilir.
- Hedef zorunluluğu: en az bir `target_pharmacies`, `target_iller` veya `target_ilceler`.

### Frontend Entegrasyon

- `PharmacyCampaigns.vue` — admin CRUD; il/ilçe/eczane chip tabanlı çoklu seçim.
- `EisaLookup` bileşeni `options: [{id, label, sub?}]` alır; eczaneler `/api/pharmacies/` (list aksiyon), iller `/api/lookups/iller/`, ilçeler `/api/lookups/ilceler/?il={id}` üzerinden yüklenir.
- `PharmacistCampaignDisplay.vue` — AdminLayout'ta `v-if="isPharmacist"` ile mount edilir; alt şerit + 90s idle overlay; shuffle-bag rotasyon; visibility API ile sekme gizliyken ilerleme durur.

