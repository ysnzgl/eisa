# DOOH Kural Tabanlı Otomatik Reklam Planlayıcı — Uygulama Planı

**Durum:** ONAYLANDI (v4) — uygulamaya hazır. **Kapsam:** Backend (Django/DRF/PostgreSQL), Vue 3 admin panel, kiosk edge (Fastify + SQLite), Svelte UI. **Tarih:** 2026-07-21.

> Bu doküman self-contained'dir; başka bir sohbet/oturum belleğine bağımlı değildir. Uygulama Faz 0'dan başlar. Onaysız kod değişikliği yapılmaz.

---

## 0. TL;DR

Manuel `PlaylistEditor` (LoopTemplate→HourPlan→DayPlan) akışını ana yoldan çıkarıp, **Campaign + Creative + Target + DeliveryRule → PlacementDemand → tek PlacementEngine → staged per-kiosk playlist bundle → all-or-nothing publish → versiyonlu kiosk pull → playback → idempotent proof-of-play** mimarisine geçiyoruz. Medya URL'leri kalıcı (`files.eisa.com.tr/<object_key>`) hale getiriliyor. Kiosk playlist contract'ı korunuyor; yalnızca applied-version ACK ve horizon manifest ekleniyor. Geçiş feature-flag + shadow karşılaştırma ile, kademeli ve forward-only yapılıyor.

### Kesinleşmiş kararlar (onaylı)
1. **CAMPAIGN_TOTAL kapsamı:** global (PlanningRun + KioskDayQuota).
2. **DeliveryRule:** yeni tablo + dual-read (ScheduleRule korunur).
3. **Job altyapısı:** APScheduler + DB-backed queue + lock.
4. **Rolling horizon:** varsayılan 3 gün (bugün + 2).
5. **files.eisa.com.tr erişim:** bucket read-only GET/HEAD policy + CDN/proxy.
6. **Legacy grid-dışı creative/HouseAd:** unschedulable olarak işaretle + admin uyarısı (değiştirme/yeniden yerleştirme yok).

### Son uygulama kuralları (onaylı)
- **K1 — 12 isimli golden-master senaryo** (bkz. 11 · Faz 0).
- **K2 — Grid-dışı legacy HouseAd** 15sn grid'de oynatılmaya çalışılmaz; `unschedulable` + admin uyarısı (bkz. 3.4).
- **K3 — Kiosk ACK** yalnızca manifestteki **tüm günler** SQLite'a **başarıyla ve atomik** uygulandıktan sonra gönderilir; kısmi indirmede ACK yok (bkz. 6.1, 7).
- **K4 — V2 genel production cutover Faz 4 tamamlanmadan yapılmaz;** Faz 3 yalnızca kontrollü aktivasyon/staging kapsamında çalışır (bkz. 4.5, 11).
- **K5 — Veriyi etkileyen alanlar** (`object_key`, `play_event_id` vb.) çok adımlı eklenir: **nullable ekle → backfill → doğrula → unique/not-null constraint**; tek adımlı riskli migration yok (bkz. 9).

---

## 1. Doğrulanmış mevcut sistem (gerçek kod)

### 1.1 Backend — `backend/apps/campaigns/`
- **models.py**: `Campaign` (status `ACTIVE/PAUSED/COMPLETED`; `start_date/end_date` DateTimeField; `priority`=50; `is_guaranteed`; `impression_goal`; `frequency_cap_per_hour`; legacy `target_pharmacies` M2M), `CampaignTarget` (`IL/ILCE/ECZANE`; il/ilce PROTECT, eczane CASCADE — **KIOSK yok**), `Creative` (`duration_seconds` 1–60 CheckConstraint; `checksum`), `ScheduleRule` (OneToOne; `PER_LOOP/PER_HOUR/PER_DAY`; `target_hours` JSON), `Playlist` (unique `kiosk+target_date+target_hour`; `version`; `loop_duration_seconds`=60), `PlaylistItem` (`creative` XOR `house_ad`; `playback_order`; `estimated_start_offset_seconds` 0..3599 saat-mutlak), `PlayLog` (`creative/house_ad` SET_NULL; `played_at`; `duration_played`; **dedup yok**), `HouseAd` (`aktif`; `priority`; `duration_seconds` 1–60), `PlaylistTemplate/HourPlan/DayPlan` (manuel JSON), `GenerationJob` (PENDING/RUNNING/DONE/FAILED).
- **services/scheduler.py**: `PlaylistGenerator`; `rng=Random(kiosk.pk*100000+date.toordinal())`; 4 pass (PER_LOOP spacing / PER_HOUR `rng.shuffle`+sort used / PER_DAY `rng.shuffle` / HouseAd filler). `_persist()`: kiosk+date tüm playlist DELETE→recreate; `version=Max(version per kiosk)+1` (**içerik değişmese de artar**). `_pick_creative()` → **yalnızca ilk creative**. `_campaign_targets_eczane()`: CampaignTarget > legacy M2M > (hedef yoksa) **True=tüm eczaneler**. `available_seconds()` ve `simulate_campaign_capacity()` **generator'dan ayrı kaba algoritma** (motor birliği yok). Guaranteed **enforce edilmiyor**, çakışma tespiti yok, tie-breaker `rng.shuffle`.
- **jobs.py**: `nightly_generate` (**sadece yarın**), `regenerate_for_campaign` (bugün+yarın), `mark_kiosks_offline` (5dk). APScheduler.
- **signals.py**: `Campaign` `post_save` → `regenerate_for_campaign` **raw daemon thread**; trigger alanları yalnız `status,start_date,end_date,name` (**Creative/ScheduleRule/CampaignTarget tetiklemiyor**); lock/concurrency yok.
- **views_v2.py**: `CampaignViewSet` + `preview` action (`POST /api/campaigns/v2/campaigns/preview/`), `PlaylistGenerateView` (template yolu `_generate_from_day_plan` — **2. üretim motoru**), `InventoryAvailabilityView`, `GenerationJob*View`.
- **serializers.py**: `KioskPlaylistItemSerializer` → `asset_id/asset_type/media_url/duration_seconds/playback_order/estimated_start_offset_seconds/campaign_name`.
- **kiosk_api/views.py**: `KioskPingView` (`playlist_version=Max(version)` bugün; `son_goruldu/is_online` update; **`Kiosk.last_playlist_version` yazılmıyor**), `KioskPlaylistView` (full day; `loop_duration_seconds`=60 hardcoded), `KioskProofOfPlayView` (bulk_create; **dedup yok**). **Auth: `Authorization: AppKey` + `X-Kiosk-MAC`** (+ opsiyonel `X-Kiosk-Device-ID`, zorunlu değil).
- **pharmacies/models.py**: `Kiosk` (`mac_adresi` unique; `device_id`; `uygulama_anahtari`; `son_goruldu`; `is_online`; `last_playlist_version` **var ama kullanılmıyor**).

### 1.2 Medya / storage
- **core/services/storage_service.py**: `StorageService` (MinIO singleton). `upload_file()` → `object=ads/{uuid.hex}.{ext}` (**zaten UUID-versioned**). `get_object_url()` → **presigned** (`S3_PRESIGNED_URL_TTL_MINUTES`, varsayılan 60). `delete_object()` var. `_ensure_bucket()` otomatik oluşturur.
- **campaigns/views.py `MediaUploadView`**: `url=get_object_url(...)` → **presigned URL** döner; response `{url, filename, object_name}`. Frontend bu URL'yi `media_url` olarak kaydeder → **`X-Amz-*` imzalı, 60 dk sonra kırılır**.
- **settings.py**: `S3_ENDPOINT/S3_BUCKET/S3_SECURE/S3_FORCE_PATH_STYLE/S3_PRESIGNED_URL_TTL_MINUTES` + `RUSTFS_*` alias. **`files.eisa.com.tr` / kalıcı public base URL ayarı YOK.**

### 1.3 Kiosk edge — `kiosk_edge/`
- **api-node/src/db.js**: SQLite `playlists` (UNIQUE `target_date,target_hour`), `playlist_items`, `kiosk_meta.playlist_version`, `creatives`/`house_ads` (`media_url`, `checksum`), `media_cache` (`source_url`, `file_checksum`, `local_path`, `status`).
- **scheduler.js**: ping 60s / pull 900s / push 300s. Version: `server>local → full-day download`; atomik tx (upsert playlist + delete items + insert). **Applied-version ACK yok.**
- **mediaCache.js**: `localReady = prev.source_url===asset.media_url && checksum eşit && dosya var` → **presigned URL her sync değişince yeniden indirir** (somut bug). Local serve: `GET /api/media/:assetType/:assetId` (server.js:147) → `sendFile(local_path)`.
- **ui/src/lib/api.js**: `_normalizeMediaUrl` → api-node local URL'ye yeniden yazar. **ui/src/components/AdStrip.svelte**: `HOUR_SECONDS=3600`, Istanbul duvar saati, `offset<=pos` son item, fallback sequential. Offline: local dosyadan oynatır.

### 1.4 Web panel — `web_panels/src/`
- **views/admin/CampaignWizard.vue**: 4 adım (Bilgi / tek Creative / Frekans&Pacing [FREQUENCY|GOAL] / Özet). **Targeting UI yok** (ölü CSS), **"Şimdi başlat" yok**, `datetime-local→toISOString` TZ riski.
- **views/admin/PlaylistEditor.vue**: 3-tier manuel; ana nav `/admin/playlists`.
- **services/dooh.js**: `previewCampaignCapacity` var, UI'de kullanılmıyor. **views/admin/KioskHealthView.vue** var, **nav'da yok**.

### 1.5 Doküman–kod uyumsuzlukları
- Doc `PER_LOOP/PER_HOUR/PER_DAY`; gereksinim `TIME_WINDOW/PER_HOUR/PER_DAY/CAMPAIGN_TOTAL`.
- Doc proof-of-play `views_v2:1068`; gerçek `kiosk_api/views.py KioskProofOfPlayView`.
- Doc auth `X-Kiosk-App-Key/X-Kiosk-Mac-Address` **yanlış**; gerçek `Authorization: AppKey`+`X-Kiosk-MAC`.
- `Kiosk.last_playlist_version` kullanılmıyor. Campaign'de `CANCELLED`/`DRAFT` yok. `media_url` presigned kaydediliyor.

---

## 2. Gap analizi

| Alan | Var | Kısmen | Yok |
|---|---|---|---|
| Playlist/version/offset/targeting | ✔ per-kiosk saatlik, 0..3599 offset, IL/ILCE/ECZANE | version bump içerik-farkı gözetmiyor | KIOSK hedef, desired/applied ayrımı |
| Delivery tipleri | ✔ PER_HOUR/PER_DAY | guaranteed enforce yok | TIME_WINDOW, CAMPAIGN_TOTAL, A→B |
| Motor | ✔ deterministik seed | sim≠generate (iki algoritma) | tek PlacementEngine, tie-breaker |
| Aktivasyon | — | preview var | all-or-nothing, reservation, staged publish |
| Invalidation | ✔ campaign save | raw thread, dar tetik | (kiosk,date) hesaplı, lock, horizon config |
| Medya URL | — | uuid key var | kalıcı URL, object_key, backfill, read-only erişim, lifecycle koruma |
| Proof-of-play | ✔ bulk | — | idempotency/dedup, planlanan-gerçekleşen ref |
| Panel | ✔ wizard iskeleti | health view gizli | targeting/start-now/rule/sim adımları, control center |

---

## 3. Canonical domain model kararları

### 3.1 Truth source
- **Canonical garanti = `DeliveryRule.guarantee_mode` (`GUARANTEED|BEST_EFFORT`).** `Campaign.is_guaranteed` **deprecate**: Faz 1'de read-only mirror (signal ile DeliveryRule'dan set), Faz 7'de kaldırılır.
- **`Campaign.impression_goal` deprecate** → `DeliveryRule(delivery_type=CAMPAIGN_TOTAL, count=goal)`. Faz 1'de dual-read helper; yeni kayıt yazmaz.
- **`Campaign.frequency_cap_per_hour` deprecate** → `DeliveryRule.max_per_hour` (per-kiosk hourly cap). Faz 1'de mirror.

### 3.2 Campaign lifecycle
- `status`: **`DRAFT`** (yeni), `ACTIVE`, `PAUSED`, `COMPLETED`, **`CANCELLED`** (yeni).
- **`SCHEDULED` türetilmiş durumdur** (ayrı alan değil): `status==ACTIVE and start_date>now()`. Serializer'da `effective_state` computed.
- **`target_scope`**: `ALL | RULES`. Targetsız `RULES` = hiçbir kiosk (ALL değil). `ALL` = tüm aktif kiosklar dinamik.
- **start_now**: request'te `start_now=true` → frontend timestamp göndermez; backend `start_date=timezone.now()`. Manuel tarih: sunucu zamanından **>2 dk geçmişse reddet**; aksi halde `max(seçilen, now())`'a normalize. `end_date` yoksa `duration_days`'ten `start_date + duration` hesaplanır. TZ dönüşümü tek noktada (Europe/Istanbul ↔ UTC).

### 3.3 DeliveryRule (ScheduleRule yerine, additive)
- `delivery_type`: `TIME_WINDOW | PER_HOUR | PER_DAY | CAMPAIGN_TOTAL | LEGACY_PER_LOOP` (PER_LOOP exact map kanıtlanamazsa read-only legacy).
- Alanlar: `count`, `window_start_time`/`window_end_time` (TIME_WINDOW), `active_hours` JSON, `active_weekdays` JSON (opsiyonel), `guarantee_mode`, `max_per_hour` (opsiyonel cap).
- Constraint: `count>=1`; TIME_WINDOW window zorunlu; CAMPAIGN_TOTAL global (bkz. 4.3).
- `ScheduleRule` bir süre korunur (dual-read); `LEGACY_PER_LOOP` üretimde read-only.

### 3.4 Creative & HouseAd süre + grid uyumu
- **Yeni kayıt**: `duration_seconds ∈ {15,30,45,60}` validation (serializer). Planlama grid'i 15sn.
- **Legacy kayıt (değiştirilmez):** `is_grid_compliant` computed + management raporu.
  - **Grid-dışı legacy Creative** → `unschedulable`: üretimde atlanır, kampanya bazında admin uyarısı üretilir; kampanya sahibi düzeltene kadar yerleştirilmez.
  - **Grid-dışı legacy HouseAd (K2)** → 15sn grid'de oynatılmaya **çalışılmaz**; `unschedulable` işaretlenir ve **admin uyarısı** üretilir. Filler seçiminde bu HouseAd'ler **atlanır** (grid'e sığdırma/kırpma yok). Yeni HouseAd'lerde `{15,30,45,60}` zorunlu.
- Grid-dışı içerik envanteri Control Center'da "Uyumsuz Medya" uyarı listesinde gösterilir.

### 3.5 Çoklu creative & KIOSK hedef
- `Creative.weight` (default 1) + **deterministik ağırlıklı round-robin** (seed'e bağlı) → V1 kuralı.
- `CampaignTarget.target_type += KIOSK`, `kiosk=FK(Kiosk,null=True)`. **Include/exclude**: `mode=INCLUDE|EXCLUDE`. Çözüm: `resolved = union(INCLUDE) - union(EXCLUDE)`, **dedup kiosk-id set** (aynı kiosk çift gösterim yok). Yeni onaylanan kiosk `ALL` veya eşleşen `RULES`'a **dinamik** dahil.

### 3.6 A→B ardışıklık
- `Campaign.follows = FK("self", null=True, related_name="followed_by")`.
- Kısıtlar (**yalnız model clean() değil**; DB + service-level tx validation):
  - Self-link yasak (`follows_id != id`).
  - **Unique predecessor**: partial unique index on `follows_id` (bir kampanya tek bir kampanya tarafından takip edilir); bir kampanya tek bir kampanyayı takip eder.
  - **Zincir/döngü engeli**: yalnız ikili (A→B); B'nin `follows`'u olamaz, A `followed_by` olamaz — service validation.
  - **Kesişim zorunluluğu**: B'nin target/date/active_hours'u A ile **kesişmeli**; kesişmezse aktivasyon reddi.
  - **Atomic block**: A+B tek `PlacementDemand` bloğu; B'nin her yerleşimi için A hemen öncesinde. Guaranteed B için A'nın ≥ B.count uygun yerleşimi olmalı.
  - **pause/cancel**: A pause/cancel → B bağımsız oynatılmaz (blok düşer); yalnız B pause → blok düşer, A tek başına kalabilir.

### 3.7 Silme davranışı
- `PlayLog` veya aktif/gelecek `PlaylistItem` bağımlılığı olan Creative/Campaign/HouseAd fiziksel silinmez → **409** + `used_in`. archive/pause/cancel medya/kayıt silmez.

### 3.8 Medya kalıcılık
- `Creative.object_key` + `HouseAd.object_key` (`CharField(512)`). Çok adımlı migration (bkz. 9, K5).
- `media_url` **kalıcı** = `S3_PUBLIC_BASE_URL + "/" + object_key`. **Prod'da `S3_PUBLIC_BASE_URL` zorunlu** (boşsa startup fail).
- **Path→bucket/object map**: `S3_FORCE_PATH_STYLE=True` olduğundan proxy `files.eisa.com.tr/<object_key>` → `s3://<S3_BUCKET>/<object_key>`. `object_key` bucket adını içermez; proxy/policy bucket'ı sabitler.
- **ETag ≠ SHA-256**: `checksum` = upload sırasında **stream'den hesaplanan SHA-256** (`hashlib.sha256`, chunk okuma, `seek(0)` reset, `sha256:` prefix). ETag storage'ın döndürdüğü ayrı değer; manuel metadata olarak set edilmez, yalnız doğrulama/log için okunur. `put_object` başlıkları: `Content-Type`, `Content-Length`, `Cache-Control: public, max-age=31536000, immutable`.

### 3.9 Versioning
- **`KioskDesiredBundle`** (yeni): `kiosk`, `desired_bundle_version` (kiosk bazında **monoton artan**, `Max(playlist.version)` KULLANILMAZ), `content_fingerprint`, `valid_from`, `horizon_days`.
- **`Kiosk.applied_playlist_version`** (mevcut `last_playlist_version` yeniden amaçlanır): kiosk ACK ile yazılır.
- **Fingerprint** = tüm horizon günleri için canonical kiosk payload'ının kararlı hash'i: her item'ın `asset_type + asset_id + object_key + media_url + checksum + duration_seconds + playback_order + estimated_start_offset_seconds` + `target_date + target_hour`. Fingerprint değişmediyse `desired_bundle_version` **artmaz**.
- **valid_until ≠ medya kalıcılığı**: playlist `valid_until` yalnız fail-safe/stale kontrol içindir; medya URL'leri süresizdir.

---

## 4. PlacementEngine V2 tasarımı

### 4.1 Demand modeli (pass-per-type DEĞİL)
1. Aktif kampanyaların `DeliveryRule`'larından **`PlacementDemand`** listesi üret. Her demand: `campaign, creative_selector(weighted RR), duration, required_slots, constraint(window/hours/weekday), guarantee_mode, deadline, tightness, priority, ab_block_ref`.
2. A→B demand'leri **tek atomic block** olarak birleştir (A+B ardışık, bölünmez).
3. **Sıralama (tie-breaker deterministik):** `(guarantee_mode GUARANTEED first, constraint_tightness DESC, deadline ASC, priority ASC, campaign.start_date ASC, campaign.id ASC)`. `rng.shuffle` **kaldırılır**; jitter gerekiyorsa seed'li deterministik jitter.
4. **Yerleştirme**: guaranteed/TIME_WINDOW demand'leri kapasiteye **rezerve** ederek yerleştir (çakışma → `collision`/`blocking_reason`, sessiz kaydırma yok). Sonra best-effort demand'ler kalan boşluğa. En son **HouseAd filler** (grid-uyumlu HouseAd'ler; grid-dışı legacy atlanır — K2).
5. Her saat için 0..3599 mutlak offset `PlaylistItem` üret (grid=15sn).

### 4.2 simulate == generate
Tek fonksiyon iki mod: `PlacementEngine.run(kiosk, date, commit=False|True)`. `simulate` staged sonucu döndürür (commit etmez); `generate` staging'e yazar. **Ayrı `available_seconds`/`simulate_campaign_capacity` algoritması kaldırılır**, bu motora bağlanır.

### 4.3 Global CAMPAIGN_TOTAL — PlanningRun + KioskDayQuota
- **`PlanningRun`**: `id, horizon_start, horizon_end, status, created_at`. Bir horizon üretiminin atomik referansı.
- **`CampaignTotalAllocation`**: `campaign, planning_run, total_target, allocated_total`.
- **`KioskDayQuota`**: `planning_run, campaign, kiosk, date, quota, placed`. Global toplam, hedef kiosk-gün kapasitelerine **oransal (capacity-weighted)** bölünür.
- **Bağımsız kiosk+gün işlemleri global toplamı nasıl korur:** her kiosk-gün üretimi kendi `KioskDayQuota.quota`'sını aşamaz; kota `PlanningRun` içinde önceden hesaplanır (tek noktadan). Kısmi placed değerleri `KioskDayQuota.placed`'e yazılır; `sum(placed) ≤ total_target` invariant'ı `PlanningRun` commit'inde doğrulanır. Böylece paralel kiosk işleri toplamı bozmaz.

### 4.4 Guaranteed activation — all-or-nothing
- Aktivasyon akışı: `activate()` → **advisory lock (kampanya + etkilenen kiosk seti)** → **re-validate** (simülasyon anındaki kapasite hâlâ geçerli mi) → tüm hedef kiosk-günler için **staging bundle üret** → hepsi başarılıysa **tek transaction'da publish** (`desired_bundle_version` bump). Herhangi bir hedef başarısızsa **hiçbiri publish edilmez** (kısmi publish yok), `blocking_reasons` döner, kampanya `DRAFT`/blocked kalır.
- Simülasyon↔aktivasyon race: lock + re-validate + fingerprint karşılaştırma ile çözülür.

### 4.5 Faz 0 karakterizasyon + shadow + cutover sınırı (K4)
- **Faz 0 yalnız test**: mevcut `generate_for_kiosk` çıktısı için golden-master snapshot'lar (bkz. 12 isimli senaryo, Faz 0), kiosk contract testleri, proof-of-play testleri. **V2 kod yazılmaz.**
- **Faz 2 shadow**: `DOOH_ENGINE_V2` feature flag. V2 **üretime yazmaz**; V1 ile paralel çalışıp **fingerprint/diff karşılaştırması** loglar (`EngineShadowDiff`). Eşdeğerlik + kabul edilen farklar doğrulanınca ilerlenir.
- **Faz 3 sınırı (K4):** Faz 3'te V2 **yalnızca kontrollü aktivasyon/staging** kapsamında çalışır (belirli kampanyalar/kiosklar için opt-in). **Genel production cutover Faz 4 tamamlanmadan yapılmaz.** Sistem geneli otomatik üretim V1'de kalır; V2 cutover'ı Faz 4 kabul kriterleri karşılanınca (`DOOH_ENGINE_V2=active-global`) yapılır.

### 4.6 Pseudocode
```
def run(kiosk, date, planning_run, commit):
    demands = build_demands(active_campaigns(kiosk, date))     # DeliveryRule → PlacementDemand
    blocks  = coalesce_ab_blocks(demands)                       # A→B atomic
    grid    = HourGrid(date, step=15)                           # 24h, 0..3599
    reasons = []
    for d in sorted(blocks, key=tiebreak):                      # guaranteed/tightness/deadline/priority/id
        if d.guarantee_mode == GUARANTEED or d.type == TIME_WINDOW:
            ok = reserve(grid, d, quota=KioskDayQuota.get(...))
            if not ok: reasons.append(blocking(d))
    for d in best_effort(blocks): place_if_fits(grid, d, quota)
    fill_house_ads(grid)                                        # 15s grid aware; grid-dışı legacy atlanır (K2)
    items = materialize(grid)                                   # offset = loop_index*loop_sec + slot.offset
    fp = fingerprint(items, include=[object_key, media_url, checksum, ...])
    if commit: stage(kiosk, date, items, fp)                    # publish ayrı adım (all-or-nothing)
    return StagedResult(items, fp, reasons)
```

---

## Faz 2 — PlacementEngine V2 Shadow Mode (BAŞLANIYOR 2026-07-22)

**Kapsam:**
- PlacementEngine V2 kodu: DeliveryRule tabanlı slot placement
- Shadow mode: V1 scheduler korunur ve üretim playlist'i üretmeye devam eder
- V2 paralel çalışır, ancak sonucu yalnızca log'a/metriğe yazar
- V1 ↔ V2 diff metrikleri
- Feature flag: `DOOH_ENGINE_V2=shadow` (default: `off`)
- **Production cutover YOK, V1 kapatma YOK**

**Önkoşullar (Faz 2 DOOH_ENGINE_V2=shadow açılmadan):**
1. PostgreSQL integration testi: select_for_update/MVCC concurrency (A→B race)
2. A→B target intersection validation testi (real DB)
3. staging migration 0015–0018 apply + smoke test
4. files.eisa.com.tr GET/HEAD gerçek bucket policy testi

**Yapılacaklar:**

**2.1. PlacementEngine V2 Core**
- `apps/campaigns/services/placement_engine_v2.py`:
  - `plan_kiosk_hour(kiosk, date, hour) -> ShadowPlan`
  - DeliveryRule.delivery_type dispatch: TIME_WINDOW / PER_HOUR / PER_DAY / CAMPAIGN_TOTAL
  - target_scope resolver: ALL / RULES (CampaignTarget union/dedup)
  - follows chain resolver: A→B sıralama
  - Slot allocation (guarantee_mode priority)
  - HouseAd filler
  - Çıktı: `{ playlist_items: [...], metrics: {...}, diff_v1: {...} }`

**2.2. Shadow Mode Orchestration**
- `apps/campaigns/services/scheduler.py`:
  - `generate_for_kiosk()` V1 mantığını korur (değişiklik yok)
  - `DOOH_ENGINE_V2=shadow` ise V2'yi de çağır:
    ```python
    v1_playlist = generate_for_kiosk_v1(...)  # mevcut kod
    if settings.DOOH_ENGINE_V2 == 'shadow':
        v2_plan = placement_engine_v2.plan_kiosk_hour(...)
        log_shadow_diff(v1_playlist, v2_plan)
        record_shadow_metrics(v2_plan.metrics)
    return v1_playlist  # üretim her zaman V1
    ```

**2.3. Shadow Diff Metrics**
- `apps/campaigns/models.py`:
  - `ShadowRunMetric(id, run_date, kiosk, hour, v1_item_count, v2_item_count, creative_diff_count, duration_diff_seconds, recorded_at)`
- Farklılıklar: item sayısı, creative sırası, toplam süre, guaranteed placement farkı
- Günlük rapor: `python manage.py report_shadow_diff --date=YYYY-MM-DD`

**2.4. Integration Testleri (PostgreSQL)**
- PostgreSQL docker-compose test ortamı
- Gerçek MVCC concurrency testleri (follows race, KioskDayQuota race)
- A→B follows: target intersection, tarih/saat kesişimi, pause/cancel
- V1 ↔ V2 playlist karşılaştırma testleri (golden-master V1 playlist → V2 aynı mı?)

**2.5. Docs**
- `docs/ai/09-placement-engine-v2.md`: V2 algoritması, delivery_type dispatch, shadow mode kullanımı
- `01-backend.md`: PlacementEngine V2 eklenmesi
- `implementation-plan-dooh-scheduler.md`: Faz 2 kapanış kriterleri

**Kabul Kriterleri:**
- V1 scheduler değişmeden korunmuş
- `DOOH_ENGINE_V2=shadow` → V2 çalışıyor, V1 üretimi değişmiyor
- PostgreSQL concurrency testleri ✓
- staging migration + smoke test ✓
- files.eisa.com.tr GET/HEAD bucket policy ✓
- Shadow diff metrikleri 7 gün toplama → %95+ item match
- Dokümantasyon tamamlandı

**Çıktı:**
- Production'da V1 çalışıyor, V2 shadow mode
- Faz 3 için hazır: `DOOH_ENGINE_V2=dual` (V1+V2 paralel, kiosk başına A/B)

---

## 5. Invalidation, jobs, staged publish

### 5.1 Olay → etkilenen (kiosk, tarih)
| Olay | Etki |
|---|---|
| Campaign create/activate/pause/resume/cancel, tarih/priority/target/guarantee değişimi | hedef kiosklar × horizon |
| DeliveryRule / Creative (ekle/kaldır/süre) / weight | kampanya kioskları × horizon |
| A→B ilişki değişimi | A ve B kioskları × horizon |
| HouseAd değişimi | tüm kiosklar × horizon |
| Yeni kiosk onayı / eczane-il-ilçe değişimi | o kiosk × horizon |
| Guaranteed kapasiteyi etkileyen değişim | çakışan kampanya kioskları × horizon |

### 5.2 Rolling horizon
- `DOOH_PLANNING_HORIZON_DAYS` (varsayılan **3**: bugün + 2). Gerekçe: kiosk pull gecikmesi (900s) + gece penceresi + acil değişiklik tamponu.

### 5.3 Job altyapısı
- Raw daemon thread **kaldırılır** → **DB-backed queue** (`GenerationJob` + APScheduler worker; Celery opsiyonel). Aynı `(kiosk,date)` için **`select_for_update` / advisory lock**. Idempotent (aynı girdi→aynı fingerprint). Kısmi hata: kiosk-gün bazında izole; başarısız fingerprint version bump'lamaz. Signal tetikleyicileri Campaign + DeliveryRule + Creative + CampaignTarget + HouseAd + Kiosk-approve'a genişletilir.
- **Staged publish**: üretim → `PlaylistStaging` → doğrulama → publish (`desired_bundle_version` bump) tek tx. Guaranteed all-or-nothing (4.4).

---

## 6. API contract

### 6.1 Kiosk (auth: `Authorization: AppKey` + `X-Kiosk-MAC`; **Device-ID zorunlu değil**)
- `GET /api/kiosk/v1/ping/` (korunur) → `{playlist_version→desired_bundle_version, ...}`.
- **`GET /api/kiosk/v1/playlist/manifest/`** (yeni) → horizon manifesti:
  ```json
  { "kiosk_id": 12, "desired_bundle_version": 84,
    "days": [ {"date":"2026-07-21","version":84}, {"date":"2026-07-22","version":84}, {"date":"2026-07-23","version":84} ] }
  ```
  Kiosk her günü `GET /playlist/?date=` ile ayrı çeker ve 3 günü cache'ler.
- `GET /api/kiosk/v1/playlist/?date=` (contract korunur; `media_url` kalıcı, opsiyonel `object_key`/`checksum` eklenir; `valid_until` opsiyonel).
- **`POST /api/kiosk/v1/playlist/ack/`** (yeni, idempotent):
  ```json
  { "applied_version": 84, "applied_at": "2026-07-21T10:00:00+03:00" }
  ```
  - Backend `applied_version > current` ise yazar; **stale ACK version düşürmez** (monoton). 
  - **K3:** Kiosk bu ACK'i yalnızca **manifestteki tüm günler** SQLite'a **başarıyla ve atomik** yazıldıktan sonra gönderir. **Kısmi indirmede ACK gönderilmez** (yarım tx → ACK yok).
- `POST /api/kiosk/v1/proof-of-play/`: her log **`play_event_id` (UUID, zorunlu, unique)** içerir → dedup. Opsiyonel `bundle_version` + `playlist_item_id` ref (V1'de `bundle_version` yeterli, item ref opsiyonel).

### 6.2 Admin
- `POST /api/campaigns/v2/campaigns/{id}/simulate/` → kapasite/verdict (`publishable|not_publishable|best_effort`, `blocking`, `conflicting_guaranteed`).
- `POST /api/campaigns/v2/campaigns/{id}/activate/` → all-or-nothing; guaranteed karşılanmazsa `409` + nedenler.
- `DELETE .../creatives|campaigns|house-ads/{id}/` → bağımlılıkta `409` + `used_in`.
- `GET /api/pharmacies/kiosks/control-center/` → desired vs applied version, online/offline, planlanan vs son oynatılan (PlayLog), bugünkü özet, yaklaşan, uyumsuz medya uyarıları.
- **`POST /api/campaigns/upload-media/`**: response
  ```json
  { "object_key":"ads/8f3a...c1.mp4",
    "media_url":"https://files.eisa.com.tr/ads/8f3a...c1.mp4",
    "checksum":"sha256:...",
    "url":"https://files.eisa.com.tr/ads/8f3a...c1.mp4" }
  ```
  `url` = geçiş süresince **zorunlu** backward-compat alias (= media_url). Presigned imza parametreleri asla dönmez.

---

## 7. Kiosk edge etkileri

- **Contract korunur**; `media_url` değeri kalıcı olur. `mediaCache.js` `source_url` sabitleneceğinden gereksiz yeniden-indirme çözülür; cache anahtarı `checksum` bazlı, yeni revizyon (yeni object_key+checksum) doğru indirir.
- **Manifest sync**: scheduler.js `ping` → `manifest` çeker; her gün için `date` bazlı playlist indirir; SQLite `playlists` UNIQUE(`target_date,target_hour`) sayesinde 3 gün cache'lenir.
- **ACK (K3)**: kiosk manifestteki **tüm günleri** tek atomik SQLite transaction (ya da hepsi başarılı olduğunda commit edilen sıralı tx) ile uygular; **hepsi başarılı olduktan sonra** `POST /playlist/ack/` gönderir. Herhangi bir gün başarısızsa tx rollback, ACK yok, sonraki ping'te tekrar denenir.
- **Offline/cancel**: kiosk iptali ancak sonraki ping/pull'da öğrenir → Control Center "senkron bekliyor" gösterir. Opsiyonel `valid_until` fail-safe (medya kalıcılığından bağımsız).
- **AdStrip/Svelte**: değişiklik gerekmez.

---

## 8. Vue admin panel

- **CampaignWizard.vue** → 11 adım: Bilgi → Başlangıç/bitiş + "Şimdi başlat" → Creative(ler)+süre(15/30/45/60) → Hedef (`target_scope=ALL|RULES`, include/exclude, IL/ILCE/ECZANE/**KIOSK**) → Yayın tipi&frekans (DeliveryRule) → opsiyonel pencere/çalışma saatleri → GUARANTEED/BEST_EFFORT → opsiyonel A→B → **kapasite simülasyonu** → özet → activate.
- Yeni bileşenler: `TargetSelector.vue`, `DeliveryRuleForm.vue`, `CapacityPreview.vue`, `SequencingPicker.vue`, `StartNowToggle.vue`. Upload akışı `{object_key, media_url, checksum}` kullanır.
- **ControlCenter.vue** (nav'a eklenir; `KioskHealthView` ile birleşir): desired vs applied, online/offline, planlanan vs gerçekleşen (PlayLog), durum, bugünkü özet, yaklaşan, uyumsuz medya uyarıları, pause/cancel/exclusion.
- **PlaylistEditor.vue**: ana nav'dan kaldırılır → "Gelişmiş Manuel Yayın" read-only (legacy DayPlan).
- **DateRangePicker.vue**: açık Europe/Istanbul↔UTC dönüşümü tek noktada (3 saat kayması giderilir).

---

## 9. Migration & backward compatibility

### 9.1 Çok adımlı, veri-güvenli migration prensibi (K5)
Mevcut veriyi etkileyen tüm alanlar (`object_key`, `play_event_id`, `desired_bundle_version` vb.) **tek adımda unique/not-null eklenmez**. Sıra:
1. **Adım A — nullable ekle:** alan `null=True, blank=True` olarak eklenir (hızlı, kilitsiz).
2. **Adım B — backfill:** ayrı management command ile doldurulur (dry-run→apply, rapor, backup).
3. **Adım C — doğrula:** tüm satırların dolu ve geçerli olduğu doğrulama komutuyla kontrol edilir (kalan NULL = 0 raporu).
4. **Adım D — constraint:** ayrı migration ile `unique`/`not-null` constraint eklenir. Doğrulama geçmeden bu adım çalıştırılmaz.

### 9.2 Şema migration'ları (additive, reversible)
1. `Campaign`: `status` += `DRAFT/CANCELLED`; `target_scope`; `follows` FK + partial unique index (`follows_id`).
2. `Creative`: `object_key` (nullable→backfill→not-null path per K5), `weight`. Yeni grid kuralı **serializer validation** + `is_grid_compliant` computed (legacy'yi bozmamak için DB CheckConstraint eklenmez).
3. `HouseAd`: `object_key` (K5 path), `is_grid_compliant`.
4. `CampaignTarget`: `target_type += KIOSK`; `kiosk` FK; `mode` (INCLUDE/EXCLUDE).
5. `DeliveryRule` yeni tablo. `ScheduleRule` korunur (dual-read); PER_LOOP → `LEGACY_PER_LOOP`.
6. `PlanningRun`, `CampaignTotalAllocation`, `KioskDayQuota`, `KioskDesiredBundle` yeni tablolar. `Kiosk.applied_playlist_version` (mevcut `last_playlist_version` yeniden amaçlanır).
7. `PlayLog`: `play_event_id` (UUID) — **K5 path**: nullable ekle → backfill (geçmiş satırlara deterministik/rastgele UUID) → doğrula → unique constraint. Opsiyonel `bundle_version`.

### 9.3 Presigned → object_key backfill (schema migration'a BAĞLANMAZ)
- **Ayrı management command**: `python manage.py backfill_media_object_keys`.
  - **Dry-run varsayılan**; `--apply` ile yazar.
  - **Doğrulama**: her `media_url` için endpoint+bucket **gerçek upload verisinden** doğrulanır; query string **körlemesine kesilmez**; `object_key` bucket/path eşleşmesiyle çıkarılır. `HEAD` ile object varlığı doğrulanır.
  - **Rapor**: çıkarılabilen / çıkarılamayan / doğrulanamayan kayıtlar CSV.
  - **Backup**: değişiklik öncesi `media_url` snapshot (audit tablosu/CSV).
  - **Forward-only**: rollback = eski presigned'a dönmek değil; kalıcı URL zaten geçerli. Ayrıştırılamayanlar elle inceleme (silinmez).
- Django data migration'ı **storage ağına erişmez**; yalnız alan ekler.

### 9.4 Bucket / erişim (deployment adımı, kod dışı)
- `files.eisa.com.tr` → read-only GET/HEAD (bucket read-only GET policy + CDN/proxy). **List / anon upload / update / delete kapalı.** `ads/` prefix için **lifecycle/expiration uygulanmaz**; mevcut varsa kaldırılır.
- Prod'da `S3_PUBLIC_BASE_URL` **zorunlu** (boşsa startup fail).

### 9.5 Deployment sırası (forward-only)
DB migrate (additive, nullable) → `S3_PUBLIC_BASE_URL` + bucket policy → backend deploy (upload kalıcı URL + `url` alias) → backfill command (dry-run→apply) → doğrula → constraint migration → kiosk ACK/manifest endpoint → web panel → doğrulama → legacy UI read-only.

---

## 10. Test planı (ölçülebilir)

### 10.1 Scheduler / motor
- TIME_WINDOW/PER_HOUR/PER_DAY/CAMPAIGN_TOTAL yerleşim; guaranteed reservation + blocking; collision (sessiz kaydırma yok); tie-breaker determinism; A→B atomik (A yoksa B yok; A pause→B düşer); TZ boundary (00:00/23:00); tarih aralığı dışı üretim yok; paused/cancelled dışlama; `target_scope=RULES` targetsız→hiç kiosk; include/exclude dedup.
- CAMPAIGN_TOTAL: paralel kiosk-gün işleri `sum(placed) ≤ total_target` invariant.
- Activation: all-or-nothing (bir hedef fail → hiç publish yok); sim↔activate race (lock+revalidate).

### 10.2 Versioning / kiosk
- Fingerprint değişmezse `desired_bundle_version` artmaz; media_url/object_key/checksum değişimi fingerprint'i değiştirir.
- ACK idempotent; stale ACK version düşürmez; **kısmi indirmede ACK yok (K3)**; tüm günler uygulanınca ACK.
- Manifest 3 günü döndürür; kiosk 3 günü cache'ler.

### 10.3 Proof-of-play
- `play_event_id` unique → duplicate reddedilir/yok sayılır; planlanan↔gerçekleşen (`bundle_version`) karşılaştırması.

### 10.4 Medya (10 zorunlu test)
1. Upload URL'sinde `X-Amz-Expires/Signature/Credential` **yok**.
2. Creative & HouseAd'de presigned tutulmuyor (media_url kalıcı, object_key dolu).
3. Aynı medya farklı zamanlarda üretimde **aynı kalıcı URL**.
4. Eski presigned kayıtlar doğru object_key'e backfill (endpoint/bucket doğrulamalı, dry-run raporu).
5. Kampanya bittikten sonra medya erişilebilir.
6. Archive/pause/cancel medyayı fiziksel silmiyor.
7. Yetkisiz upload/delete/list reddediliyor (permission + bucket policy).
8. Kiosk kalıcı URL'den indirip offline cache'e yazıyor; merkez erişilemezken local oynatım.
9. Yeni revizyon eski object_key üzerine yazmıyor (yeni key+URL).
10. Lifecycle politikası `ads/` medyalarını süre sonunda silmiyor.
- Ek: SHA-256 stream hesabı doğru; ETag ayrı okunuyor; `Cache-Control/Content-Type/Content-Length` set; `url` alias = media_url.

### 10.5 Frontend / edge
- Wizard adım validasyonu, start_now (2dk tolerans), sim disable; ControlCenter desired vs applied; DateRangePicker TZ.
- Fastify manifest+ACK; SQLite atomik replace; mediaCache re-download olmuyor; AdStrip slot seçimi + fallback.
- E2E: kampanya→sim→activate→manifest→pull→playback→proof-of-play→analytics eşleşme.

---

## 11. Fazlar — her fazda dosya, migration, test, flag, rollback/cutover, kabul kriteri

### Faz 0 — Characterization / golden-master
- **Amaç:** mevcut davranışı kilitle. **Kod değişikliği yok (sadece test).**
- **Dosyalar/testler:** `backend/apps/campaigns/tests/test_dooh_v2.py` genişlet; golden snapshot fixtures; kiosk contract testleri; `kiosk_edge/api-node/tests/`.
- **Flag:** yok. **Rollback:** yok (yalnız test).
- **Kabul kriteri (K1) — en az 12 isimli golden-master senaryo yeşil:**
  1. `gm_single_per_hour_all_kiosks` — tek PER_HOUR kampanya, `target_scope=ALL`.
  2. `gm_per_day_even_distribution` — PER_DAY, gün içi dağılım snapshot'ı.
  3. `gm_per_loop_legacy_multiplicity` — mevcut PER_LOOP çoklu yerleşim (legacy davranış).
  4. `gm_target_il_only` — IL hedefli kampanya, yalnız eşleşen eczane kioskları.
  5. `gm_target_ilce_only` — ILCE hedefli kampanya.
  6. `gm_target_eczane_specific` — tek eczane hedefi.
  7. `gm_legacy_target_pharmacies_m2m` — yalnız legacy M2M ile hedefleme.
  8. `gm_no_target_means_all_current` — hedefsiz kampanya = tüm eczaneler (mevcut davranış).
  9. `gm_priority_ordering_two_campaigns` — iki kampanya, priority sıralaması.
  10. `gm_guaranteed_flag_ordering` — `is_guaranteed` sıralamada önce.
  11. `gm_house_ad_filler_fill` — boş kapasite HouseAd priority sırasıyla dolar.
  12. `gm_multi_creative_first_only` — çoklu creative'de yalnız ilk creative kullanılır (mevcut davranış).
  13. `gm_hourly_offset_absolute_0_3599` — offset'lerin saat-mutlak (0..3599) üretimi.
  14. `gm_date_range_boundary` — start/end sınırında üretim/üretmeme.
  - Not: 12 zorunlu; 13–14 ek güvence. Her senaryo deterministik snapshot (fingerprint) ile kilitlenir.

### Faz 0.5 — Kalıcı medya URL

**Durum:** KOD/TEST TAMAMLANDI ✅ | MİGRASYON BEKLIYOR ⏳ | STORAGE POLİCY BEKLIYOR ⏳ | ROLLOUT BEKLIYOR ⏳

**URL Sözleşmesi (kesinleşti):** `S3_PUBLIC_BASE_URL=https://files.eisa.com.tr/eisa-files` (bucket dahil) → `media_url = S3_PUBLIC_BASE_URL + "/" + object_key`. Bucket otomatik ekleme kaldırıldı.
**Kapanış testleri:** C01–C05 (test_closure.py). 123/123 backend, 80/80 kiosk edge, Vue build ✓.
**Migration:** `0015_creative_object_key_housead_object_key.py` hazır; canlıya uygulanmadı.
**Storage policy:** `files.eisa.com.tr` GET/HEAD-only policy ve `ads/` lifecycle muafiyeti operasyonel ekip tarafından yapılmalı.
**Rollout:** `DOOH_PERSISTENT_MEDIA_URL=True` ortam değişkeni set edilmeden kalıcı URL akışı aktif olmaz (False=legacy fallback).

- **Dosyalar:** `storage_service.py` (`public_url` bucket-aware, SHA-256 chunk stream), `campaigns/views.py MediaUploadView` (feature flag + kalıcı URL + `{object_key,media_url,checksum,url}`), `models.py` (Creative/HouseAd `object_key` null=True), `serializers.py` (`_derive_object_key_from_url` bucket-aware + güvenlik), `settings.py` (`S3_PUBLIC_BASE_URL` opsiyonel, `DOOH_PERSISTENT_MEDIA_URL`), `test_settings.py`.
- **Dosyalar:** `storage_service.py` (`public_url`, SHA-256 stream, başlıklar, `get_object_url` yalnız preview), `campaigns/views.py MediaUploadView` (kalıcı URL + `{object_key,media_url,checksum,url}`), `models.py` (Creative/HouseAd `object_key` — K5 nullable), `serializers.py`, `settings.py` (`S3_PUBLIC_BASE_URL`), `web_panels/src/services/dooh.js`+`CampaignWizard.vue`.
- **Migration:** `object_key` nullable ekle. **Backfill:** ayrı `backfill_media_object_keys` command (dry-run→apply→doğrula), sonra ayrı constraint migration.
- **Deployment:** bucket read-only policy + lifecycle muafiyeti + prod `S3_PUBLIC_BASE_URL` zorunlu.
- **Flag:** `DOOH_PERSISTENT_MEDIA_URL`. **Rollback:** flag kapatma yeni upload'ı etkiler; mevcut kalıcı URL'ler geçerli kalır (forward-only).
- **Kabul:** 10 medya testi + SHA-256/ETag/başlık testleri yeşil; kiosk re-download kaybolur; backfill NULL kalan = 0.

### Faz 1 — Additive domain schema + legacy compatibility ⚠️ KOŞULLU KABUL (2026-07-22)

**Kod tarafı tamamlandı:** 143/143 backend, 80/80 kiosk edge, 14/14 Vue, Vue build ✓, migration 0015–0018 forward/backward ✓.

**Tamamlanan kod maddeleri:**
- target_scope CREATE'te zorunlu (API) → 400 eksikse
- is_guaranteed=True API → 400 (açık hata, canonical: DeliveryRule.guarantee_mode)
- Campaign.follows read-only (serializer) + set_campaign_follows() service (tarih/saat/CANCELLED intersection)
- follows unique predecessor: DB constraint (0018) + application-level check
- Grid validation API (15/30/45/60); legacy aynı değer korunur
- LEGACY_PER_LOOP API yazımı reddedilir
- KioskDayQuota: placed>=0, quota>=0, placed<=quota (0017)
- Vue canonical akış: media_url+object_key+checksum form state + create payload
- Vue component testi: dooh_media_flow.test.js (14 test)
- HouseAd UI kapsam açığı belgelendi (Faz 6 işi)
- SQLite concurrency sınırı belgelendi (PostgreSQL integration testi gerektirir)

**Faz 2 Giriş Önkoşulları (BEKLIYOR — Faz 2 DOOH_ENGINE_V2=shadow açılmadan tamamlanmalı):**
- [ ] PostgreSQL integration testi: gerçek select_for_update/MVCC concurrency (A→B follows race condition)
- [ ] A→B target intersection validation testi (PostgreSQL)
- [ ] staging migration apply (0015–0018) + smoke test
- [ ] files.eisa.com.tr GET/HEAD gerçek bucket policy testi

**Faz 0.5 operasyonel rollout (DEVAM EDİYOR — production için gerekli):**
- [ ] staging/prod migration apply (0015–0018)
- [ ] backfill_media_object_keys --dry-run → rapor inceleme → --apply
- [ ] `files.eisa.com.tr/eisa-files/` GET/HEAD-only bucket policy
- [ ] `ads/` prefix lifecycle/expiration muafiyeti
- [ ] production env: DOOH_PERSISTENT_MEDIA_URL=true + S3_PUBLIC_BASE_URL=https://files.eisa.com.tr/eisa-files
- [ ] production smoke test: Creative upload → kalıcı URL doğrulama
- **Dosyalar:** `models.py` (Campaign `DRAFT/CANCELLED/target_scope/follows`, Creative `weight`, CampaignTarget `KIOSK/mode`, `DeliveryRule`, `PlanningRun/CampaignTotalAllocation/KioskDayQuota/KioskDesiredBundle`, PlayLog `play_event_id` — K5 nullable), serializers, `is_grid_compliant`.
- **Migration:** additive (nullable); `ScheduleRule→DeliveryRule` dual-read helper; PER_LOOP→LEGACY_PER_LOOP; legacy creative/HouseAd **değiştirilmez**, `report_grid_noncompliant_media` command. `play_event_id` K5 sırası (nullable→backfill→doğrula→unique).
- **Flag:** `DOOH_DELIVERY_RULE_MODEL`. **Rollback:** DeliveryRule kaldırılırsa ScheduleRule fallback.
- **Kabul:** yeni alan/constraint testleri; legacy raporu üretiliyor; grid-dışı legacy `unschedulable` işaretleniyor; Faz 0 snapshot bozulmadı.

### Faz 2 — PlacementEngine V2 shadow mode
- **Dosyalar:** `services/placement_engine.py` (yeni), demand builder, tie-breaker; `EngineShadowDiff` log/tablo.
- **Flag:** `DOOH_ENGINE_V2=shadow`. V2 **üretime yazmaz**, V1 ile diff loglar.
- **Rollback:** flag kapat. **İlerleme koşulu:** kabul edilen diff seti + determinism + golden eşdeğerlik.
- **Kabul:** shadow diff raporunda açıklanamayan fark = 0; determinism testleri yeşil.

### Faz 3 — Simulation / activation / reservation ✅ TAMAMLANDI (2026-07-22)

**Kabul Kriterleri (tümü karşılandı):**
- ✅ simulation read-only (Playlist, PlaylistItem, PlanningRun, KioskDayQuota, CampaignTotalAllocation değişmez)
- ✅ sim == generation fingerprint (aynı PlacementEngineV2.plan_kiosk_day yolu, aynı fingerprint)
- ✅ GUARANTEED all-or-nothing (kapasite yetersizse CapacityError → tam rollback)
- ✅ CAMPAIGN_TOTAL invariant (GlobalQuotaService + select_for_update → concurrency güvenli)
- ✅ PostgreSQL race testleri geçti (test_fa10, test_fa11)
- ✅ 21 Faz 3 testi, 185 campaigns testi, 371 backend testi: 0 failed, 7 skipped

**Dosyalar:**
- `services/activation_service.py` (yeni): ActivationService.simulate(), activate(), _persist_plan()
- `services/placement_engine_v2.py`: is_active_mode(), should_publish() eklendi
- `views_v2.py`: simulate, activate ViewSet action'ları
- `serializers.py`: SimulationResultSerializer, ActivationResultSerializer, KioskDaySimResultSerializer
- `settings.py`: DOOH_ENGINE_V2 comment (off/shadow/active)
- `tests/test_faz3_simulation_activation.py` (yeni): 21 test
- `tests/integration/test_faz3_concurrency.py` (yeni): 2 test

**DOOH_ENGINE_V2 flag davranışı:**
- `off`: V2 kapalı; simulate → 403, activate → 403
- `shadow`: simulate çalışır; activate → 403; nightly generation V1 (K4)
- `active`: simulate + activate çalışır; nightly generation V1 (K4)

### Faz 4 — Invalidation / jobs / staged publish ✅ TAMAMLANDI (2026-07-22)

**Kabul Kriterleri (tümü karşılandı):**
- ✅ Domain rollback → invalidation job üretmez (on_commit)
- ✅ Campaign/Creative/DeliveryRule/CampaignTarget/HouseAd/Kiosk/Eczane invalidation sinyalleri
- ✅ Kiosk eczane değişimi → eski+yeni kapsam invalidation
- ✅ Eczane il/ilçe/aktiflik → eczanedeki kiosk-day kapsamı
- ✅ Duplicate PENDING coalesce (dedupe_key)
- ✅ RUNNING sırasında yeni invalidation kaybolmaz
- ✅ Select-for-update SKIP LOCKED → iki worker aynı job'u alamaz (PostgreSQL)
- ✅ Stale RUNNING job recovery → RETRY/FAILED (exponential backoff)
- ✅ Fingerprint from actual PlaylistItem DB (not stale metadata) — inside lock
- ✅ Manuel/V1 mutasyon sonrası fingerprint "aynı" sayılmaz
- ✅ Concurrent same-fingerprint → tek version bump (lock-based re-check)
- ✅ CAMPAIGN_TOTAL invariant concurrency altında
- ✅ SQLite: 430 passed (exit 0) | PostgreSQL: 16 passed (exit 0) | Node.js: 96 passed (exit 0)

**Dosyalar:**
- `signals.py`: Campaign/Creative/DeliveryRule/CampaignTarget/HouseAd/Kiosk(pre+post)/Eczane sinyalleri
- `models.py GenerationJob`: +payload/available_at/attempt_count/max_attempts/worker_id/lock_expires_at/dedupe_key/RETRY
- `services/invalidation_service.py`: enqueue_for_campaign/all_kiosks/kiosk/kiosk_dates, coalescing
- `services/queue_worker.py`: claim/process(fingerprint inside lock)/recover/drain
- `services/activation_service.py`: _persist_plan race-safe(select_for_update), _compute_playlist_fingerprint
- `jobs.py`: +drain_queue
- `views_v2.py`: PlaylistGenerateView queue mode
- `migration 0019`: GenerationJob queue fields
- `migration 0008 (pharmacies)`: Kiosk Faz4/5 alanları
- `tests/test_faz4_invalidation_queue.py` (31 test) + `tests/test_faz4_hardening_regression.py` (12 test)
- `tests/integration/test_faz4_concurrency.py` (7 test) + `test_faz4_hardening_pg.py` (2 test)

**Flags:** `DOOH_HORIZON_DAYS=3`, `DOOH_ASYNC_QUEUE=false`

### Faz 5 — Desired/applied version + kiosk ACK/horizon sync ✅ TAMAMLANDI (2026-07-22)

**Kabul Kriterleri (tümü karşılandı):**
- ✅ desired (last_playlist_version) ve applied (applied_playlist_version) ayrımı
- ✅ 3 günlük manifest tutarlı snapshot (select_for_update)
- ✅ Boş gün authoritative ({"playlists": []} response'da)
- ✅ SQLite manifest atomik uygulama + rollback
- ✅ Pending ACK sonsuz korunur; siler sadece eşleşen version+horizon (conditional clear)
- ✅ ACK idempotent/stale/future/resync davranışı
- ✅ Pending ACK crash/restart recovery (SQLite singleton + push cycle retry)
- ✅ 409 FUTURE_REJECTED → resync flag + ACK korunur (silinmez)
- ✅ 401/403 → App Key korunur, ACK korunur
- ✅ flag=false legacy kiosklar bozulmaz
- ✅ Capped backoff (30s→1800s), tight loop yok
- ✅ Backend: 18 Faz5 test + 12 regression test
- ✅ SQLite: 430 passed | PostgreSQL: 16 passed | Node.js: 96 passed

**Dosyalar:**
- `pharmacies/models.py Kiosk`: +last_v2_fingerprints/applied_playlist_version/playlist_applied_at/applied_horizon_start/applied_horizon_end
- `kiosk_api/views.py`: KioskPingView (ACK mode), +KioskManifestView, +KioskAckView
- `kiosk_api/urls.py`: +manifest/, +ack/
- `settings.py`: +DOOH_KIOSK_ACK
- `kiosk_edge/api-node/src/db.js`: +pending_ack table, +next_retry_at, +clearPendingAckIfMatches, +setAckNextRetry
- `kiosk_edge/api-node/src/scheduler.js`: +pingAndSyncManifest, retryPendingAck(capped backoff, no-delete), +retryPendingAck in pushToCentral
- `kiosk_edge/api-node/src/config.js`: +doohKioskAck
- `tests/test_faz5_kiosk_ack.py` (18 test) + `tests/test_faz4_hardening_regression.py`
- `tests/integration/test_faz4_hardening_pg.py` (2 test)
- `kiosk_edge/api-node/tests/manifest.test.js` (15 test)

**Flags:** `DOOH_KIOSK_ACK=false`

### Faz 6 — Vue Wizard / Control Center: TAMAMLANDI (2026-07-22)

**Kabul Kriterleri (tümü karşılandı):**
- ✅ CampaignWizard gerçek V2 contractlarla çalışıyor (6 adım)
- ✅ Create/edit veri kaybetmiyor (PATCH, existing fields korunur)
- ✅ IL/ILCE/ECZANE hedefleme — CampaignTarget; legacy target_pharmacies kullanılmıyor
- ✅ Upload ve ScheduleRule doğru (media_url/object_key/checksum; target_hours)
- ✅ Simulation stale-state koruması (formDirty watcher; simStale)
- ✅ Stale simulation ile activation yapılamıyor (disabled + aktivasyon bloğu)
- ✅ Activation double-submit üretmiyor (activateLoading flag)
- ✅ ControlCenter gerçek verileri gösteriyor
- ✅ Polling lifecycle temiz (PENDING/RUNNING → polling; terminal → stop; unmount cleanup)
- ✅ desired/applied/horizon semantiği doğru (calcKioskRolloutStatus composable)
- ✅ applied null → "ACK Bekleniyor" (hata değil)
- ✅ RBAC doğru (SuperAdmin-only `/admin/*` guard)
- ✅ Kaydedilmemiş değişiklik uyarısı çalışıyor (formDirty + confirm())
- ✅ 43 frontend test (FW-01..FW-20 + regresyon), 430 SQLite + 16 PG backend test

**Bulgular ve düzeltmeler (Kapanış Denetimi):**
- BUG: `summaryStats.behindKiosks` snake_case key → camelCase düzeltildi
- BUG: `close()` unsaved warning eksikti → `formDirty` + `confirm()` eklendi
- BUG: dooh.js `getIller`/`getIlceler` duplicate → kaldırıldı
- `target_days` UI disabled (backend ScheduleRuleSerializer desteklemiyor)

**Dosyalar:**
- `web_panels/src/views/admin/CampaignWizard.vue`
- `web_panels/src/views/admin/DoohControlCenter.vue` (yeni)
- `web_panels/src/composables/useKioskRolloutStatus.js` (yeni)
- `web_panels/src/services/dooh.js`
- `web_panels/src/router/index.js`
- `web_panels/src/views/admin/AdminLayout.vue`
- `web_panels/src/views/admin/PlaylistEditor.vue`
- `web_panels/src/services/__tests__/faz6_campaign_wizard.test.js` (yeni)

### Faz 7 — Legacy UI Read-Only + Cleanup: UYGULAMASI HAZIR (2026-07-22)

**Gerçekleştirilenler:**
- ✅ PlaylistEditor "Gelişmiş Manuel Yayın" altında salt okunur (CRUD butonları gizlendi)
- ✅ Campaign.is_guaranteed, impression_goal, frequency_cap_per_hour model'den kaldırıldı
- ✅ Migration 0020_faz7_drop_deprecated_campaign_fields.py oluşturuldu
- ✅ CampaignSerializer bu alanları kabul etmiyor / expose etmiyor
- ✅ target_pharmacies: fiziksel M2M korunuyor; API write path temizlendi
- ✅ DOOH_ENGINE_V2, DOOH_ASYNC_QUEUE, DOOH_KIOSK_ACK flag'leri kaldırıldı
- ✅ V2 engine, async queue, kiosk ACK canonical ve flag'siz aktif
- ✅ Ping response: desired/applied/horizon her zaman döner
- ✅ scheduler.py: is_guaranteed ordering kaldırıldı (priority sıralaması)
- ✅ scheduler.py: V2 shadow comparison kaldırıldı
- ✅ AdminLayout nav: "Gelişmiş Manuel Yayın" adıyla erişilebilir
- ✅ Backend testleri: 430 SQLite + 16 PG (yeni test_faz4_concurrency signal fixiyle)
- ✅ Frontend testleri: 57 passed (43 Faz 6 + 14 Faz 7)
- ✅ Build: exit 0

**Faz 6+7 ortak kapanış testi: HENÜZ BEKLİYOR**

**Dosyalar:**
- `backend/apps/campaigns/models.py`: is_guaranteed/impression_goal/frequency_cap_per_hour kaldırıldı
- `backend/apps/campaigns/migrations/0020_faz7_drop_deprecated_campaign_fields.py` (yeni)
- `backend/apps/campaigns/serializers.py`: deprecated alanlar kaldırıldı
- `backend/apps/campaigns/views_v2.py`: flag checks kaldırıldı; target_pharmacies write kaldırıldı
- `backend/apps/campaigns/signals.py`: DOOH_ASYNC_QUEUE kaldırıldı; always async
- `backend/apps/campaigns/services/queue_worker.py`: DOOH_ENGINE_V2 kaldırıldı; always active
- `backend/apps/campaigns/services/placement_engine_v2.py`: is_enabled/is_active hardcode True
- `backend/apps/campaigns/services/scheduler.py`: shadow mode kaldırıldı; is_guaranteed ordering kaldırıldı
- `backend/apps/campaigns/jobs.py`: DOOH_ASYNC_QUEUE kaldırıldı
- `backend/apps/kiosk_api/views.py`: DOOH_KIOSK_ACK kaldırıldı; ACK/manifest her zaman aktif
- `backend/core_api/settings.py`: deprecated flags kaldırıldı
- `backend/apps/campaigns/tests/integration/test_faz4_concurrency.py`: Faz 7 signal fix
- `web_panels/src/views/admin/PlaylistEditor.vue`: IS_READ_ONLY=true, CRUD gizlendi
- `web_panels/src/views/admin/AdminLayout.vue`: "Gelişmiş Manuel Yayın"
- `web_panels/src/services/__tests__/faz7_readonly_cleanup.test.js` (yeni, 14 test)

---

## 12. Riskler ve açık kararlar

**Riskler:** (a) backfill'de farklı endpoint/bucket ile üretilmiş eski URL'ler → doğrulamalı ayrıştırma + rapor şart. (b) Guaranteed enforce mevcut aktifleri bloklayabilir → Faz 1'de "grandfathered/best_effort" işaretle. (c) `files.eisa.com.tr` DNS/TLS hazır değilse kiosk indirme kırılır → kalıcı URL öncesi erişim doğrula. (d) Shadow diff büyükse cutover gecikir → kabul edilen fark seti önden tanımla. (e) Lifecycle expiration mevcutsa medya sessizce silinir → deploy öncesi denetle.

**Kararlar (onaylı):** CAMPAIGN_TOTAL global; DeliveryRule yeni tablo + dual-read; APScheduler + DB-queue + lock; horizon 3 gün; files.eisa.com.tr read-only GET/HEAD + CDN; grid-dışı legacy creative/HouseAd unschedulable + admin uyarısı.

**Son uygulama kuralları (onaylı):** K1 12 isimli golden senaryo; K2 grid-dışı legacy HouseAd unschedulable+uyarı; K3 ACK yalnız tüm günler atomik uygulanınca; K4 V2 genel cutover Faz 4'te; K5 nullable→backfill→doğrula→constraint çok adımlı migration.
