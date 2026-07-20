# Backend — Django 5 + DRF + PostgreSQL

**Amaç:** Merkezi API servisi, kampanya/creative/playlist yönetimi, kullanıcı/eczane/ürün veritabanı, kiosk senkronizasyon endpoint'leri.

---

## When To Read This File

- Yeni backend endpoint eklerken
- Model/migration değişiklikleri için
- API contract sorunlarında
- Kiosk senkronizasyon problemlerinde
- Kampanya/playlist mantığı değişikliklerinde

---

## Important Source Files

- `backend/core_api/settings.py` — Django ayarları, env config
- `backend/core_api/urls.py` — Root URL routing
- `backend/apps/campaigns/models.py` — Campaign/Creative/Playlist models
- `backend/apps/campaigns/views_v2.py` — DOOH v2 API views
- `backend/apps/campaigns/services/scheduler.py` — Playlist generation
- `backend/apps/products/models.py` — Kategori/Soru/EtkenMadde models
- `backend/apps/pharmacies/models.py` — Eczane/Kiosk models
- `backend/apps/pharmacies/auth.py` — Kiosk authentication (tek `KioskAppKeyAuthentication`)
- `backend/apps/kiosk_api/` — Kiosk API facade (`/api/kiosk/v1/`; bootstrap + operasyonel endpoint'ler)
- `backend/apps/analytics/models.py` — OturumLogu/PlayLog models

---

## Teknoloji ve Giriş Noktası

- **Framework:** Django 5 + djangorestframework
- **Auth:** `djangorestframework-simplejwt` (httpOnly çerez tabanlı JWT) + Kiosk auth (yalnız App Key + MAC — `Authorization: AppKey` + `X-Kiosk-MAC`)
- **DB:** PostgreSQL (prod), SQLite (dev)
- **Entrypoint:** `backend/manage.py` (Django CLI), `core_api/wsgi.py` (WSGI), `core_api/asgi.py` (ASGI)
- **Settings:** `core_api/settings.py` (env: `DJANGO_DEBUG`, `DJANGO_SECRET_KEY`, `DB_*`, `ALLOWED_HOSTS`)
- **URLs:** `core_api/urls.py` (root routing)

**Çalıştırma:**
```
python manage.py runserver              # Dev
gunicorn core_api.wsgi --bind 0.0.0.0:8000  # Prod
```

---

## Controller / Route Yapısı

| Endpoint | View | Auth | Açıklama |
|----------|------|------|----------|
| `/api/auth/token/` | `CookieTokenObtainPairView` | Public | JWT login (httpOnly çerez) |
| `/api/auth/token/refresh/` | `CookieTokenRefreshView` | Public | Token yenileme |
| `/api/auth/logout/` | `CookieLogoutView` | JWT | Çerez temizleme |
| `/api/lookups/` | `apps.lookups.urls` | JWT/Kiosk | Il/Ilce/Cinsiyet/YasAraligi sabitleri |
| `/api/users/` | `apps.users.urls` | JWT | Kullanıcı CRUD |
| `/api/pharmacies/` | `apps.pharmacies.urls` | JWT | Eczane/Kiosk CRUD, provisioning yönetimi |
| `/api/products/` | `apps.products.urls` | JWT | Kategori/Soru/EtkenMadde/Danışma CRUD |
| `/api/analytics/` | `apps.analytics.urls` | JWT | Session log raporlama |
| `/api/campaigns/` | `apps.campaigns.urls` | JWT (SuperAdmin) | Campaign/Creative/ScheduleRule yönetimi |
| `/api/campaigns/v2/*` | `apps.campaigns.views_v2` | JWT (SuperAdmin) | DOOH v2 API (playlist, pricing, house ads) |
| `/api/inventory/availability/` | `InventoryAvailabilityView` | JWT | Slot kapasite sorgusu |
| `/api/kiosk/v1/bootstrap/` | `kiosk_api.KioskBootstrapView` | Fleet+HMAC | Provisioning; App Key döner |
| `/api/kiosk/v1/identity/enroll/` | `kiosk_api.KioskIdentityEnrollView` | AppKey+MAC | Kalıcı device_id tek-seferlik bağlama |
| `/api/kiosk/v1/ping/` | `kiosk_api.KioskPingView` | AppKey+MAC | Playlist versiyonu kontrolü |
| `/api/kiosk/v1/sync/` | `kiosk_api.KioskSyncView` | AppKey+MAC | Creative/HouseAd + lookup |
| `/api/kiosk/v1/catalog/` | `kiosk_api.KioskCatalogView` | AppKey+MAC | Kategori/soru/etken madde/danışma |
| `/api/kiosk/v1/playlist/` | `kiosk_api.KioskPlaylistView` | AppKey+MAC | Günlük playlist |
| `/api/kiosk/v1/sessions/` | `kiosk_api.KioskSessionsView` | AppKey+MAC | Oturum outbox; backend QR üretir; response: `{results:[{idempotency_key,status,qr_kodu}]}` |
| `/api/kiosk/v1/proof-of-play/` | `kiosk_api.KioskProofOfPlayView` | AppKey+MAC | Bulk PlayLog ingest |
| `/api/kiosk/v1/diagnostics/` | `kiosk_api.KioskDiagnosticsView` | AppKey+MAC | Diagnostic (DB'ye yazılmaz) |

**RBAC:** `IsSuperAdmin`, `IsPharmacist`, `IsKiosk` permission sınıfları mevcut.

---

## Service / Repository / DB Erişim Yapısı

- **ORM:** Django ORM (models.py dosyalarında tanımlı)
- **Transaction:** `apps.core.uow.UnitOfWork` (Unit of Work pattern, manuel transaction yönetimi)
- **Scheduler:** `apps.campaigns.services.scheduler` modülü (playlist üretimi, slot hesaplama)
  - `generate_for_kiosk(date, kiosk_id)` → Kiosk için günlük playlist üretir
  - `available_seconds(date, hour, kiosk_id)` → Slot kapasitesi hesaplama
  - `simulate_campaign_capacity(campaign_id, date)` → Kampanya kapasite simülasyonu
- **Background Jobs:** `django_apscheduler` (playlist üretimi async job'ları için)

**Service katmanı:** Şu an modeller arasında direkt ORM çağrıları var; servis katmanı kısıtlı. Çoğu iş logic view'lerde.

---

## Ana Entity / Model Yapısı

### Core (`apps.core`)
- `BaseModel`: olusturulma_tarihi, olusturan, guncellenme_tarihi, guncelleyen, surum (tüm iş modellerinin base'i)
- `LookupModel`: id + BaseModel (tüm lookup'ların base'i)

### Lookups (`apps.lookups`)
- `Il`: Şehirler
- `Ilce`: İlçeler (il FK)
- `Cinsiyet`: Cinsiyet sabitleri (Kadın, Erkek, Diğer)
- `YasAraligi`: Yaş aralıkları (0-17, 18-24, 25-34, vb.)

### Users (`apps.users`)
- `EisaUser`: Django AbstractUser, rol (superadmin/pharmacist), eczane FK

### Pharmacies (`apps.pharmacies`)
- `Eczane`: Eczane (il/ilce, ad, sahip, telefon, aktif)
- `Kiosk`: Kiosk cihaz (eczane FK, mac_adresi, **device_id** (UUID, unique, nullable), uygulama_anahtari, aktif, is_online, son_goruldu, last_playlist_version). device_id ilk enrollment'ta tek-seferlik bağlanır, değiştirilemez. TPM tabanlı değil; runtime DB kopyalanırsa kopyalanabilir.
- `KioskProvisioningRequest`: Kayıtsız kiosk onay talebi (UUID pk, mac_adresi, **device_id** (max 36, partial-unique non-empty), hostname, device_metadata JSON, status PENDING/APPROVED/REJECTED, last_seen_at, request_count, approved_by/at, rejected_by/at, rejection_reason, kiosk FK nullable). Onay anında `device_id` `Kiosk.device_id`'ye aktarılır. **Raw fleet_key/provision_secret saklanmaz.**

### Analytics (`apps.analytics`) *(updated 2026-07-20)*
- `OturumLogu`: Anonim kullanici session (**oturum_tipi** [SIKAYET/OZEL_DANISMANLIK],RUN_ONERI/DANISMANLIK], kategori FK (nullable), **danisma_kategorisi** FK (nullable, products.Danisma), hassas_akis bool, **qr_kodu** (max_length=8, unique, DB constraint), cevaplar JSON (backup), onerilen_etken_maddeler JSON (backup), tamamlandi bool). **QR backend tarafından üretilir; istemciden gelen qr_kodu yoksayılır.**
- `OturumCevap`: Normalize cevaplar (oturum FK CASCADE, soru FK PROTECT nullable, cevap FK PROTECT nullable, soru_metni_snapshot, cevap_metni_snapshot, cevap_degeri_snapshot). unique_together (oturum, soru).
- `OturumOnerilenEtkenMadde`: Normalize önerilen etken maddeler (oturum FK CASCADE, etken_madde FK PROTECT nullable, etken_madde_adi_snapshot). unique_together (oturum, etken_madde).

### Products (`apps.products`)
- `Kategori`: Şikayet kategorisi (ad, slug, ikon, hedef_cinsiyet, hedef_yas_araliklari M2M, bagli_kategori self-FK)
- `Danisma`: Eczacıya danışma kategorisi (ad, slug, ikon, ust_kategori self-FK)
- `Soru`: Kategori sorular (kategori FK, metin, sira, hedef_cinsiyet, hedef_yas_araliklari M2M, hedef_etken_maddeler M2M)
- `Cevap`: Soru cevapları (soru FK, metin, sira)
- `CevapEtkenMadde`: Cevap ile etken madde ilişkisi (cevap FK, etken_madde FK, aktif)
- `EtkenMadde`: Etken madde (ad, slug, aktif)

### Campaigns (`apps.campaigns`)
- `Campaign`: Reklam kampanyası (advertiser_id, advertiser_name, name, start_date, end_date, status, impression_goal, frequency_cap_per_hour, priority, is_guaranteed)
- `CampaignTarget`: Kampanya lokasyon hedefi (campaign FK, target_type [IL/ILCE/ECZANE], il/ilce/eczane FK)
- `Creative`: Kampanyaya ait medya (campaign FK, media_url, duration_seconds, name, checksum)
- `ScheduleRule`: Kampanya frekans matrisi (campaign 1to1, frequency_type [PER_LOOP/PER_HOUR/PER_DAY], frequency_value, target_hours JSON)
- `Playlist`: Kiosk için üretilmiş playlist (kiosk FK, target_date, target_hour [Istanbul yereli], loop_duration_seconds, version; unique kiosk+date+hour)
- `PlaylistItem`: Playlist öğeleri (playlist FK, creative FK nullable, house_ad FK nullable, playback_order, estimated_start_offset_seconds [saat-mutlak 0..3599])
- `PlaylistTemplate`: Playlist şablonları (name, loop_duration_seconds, slots JSON, target_hours JSON, description)
- `HouseAd`: Filler reklam (name, media_url, duration_seconds, aktif, priority)
- `PlayLog`: Reklam gösterim logu / proof-of-play (kiosk FK, creative/house_ad FK nullable, played_at, duration_played)
- `DayPlan`: Günlük plan (kiosk FK, date, playlists FK M2M)
- `HourPlan`: Saatlik plan (kiosk FK, date, hour, playlist FK)
- `GenerationJob`: Async playlist üretim job'u (job_id, status, created_at, started_at, finished_at, result JSON)
- `PricingMatrix`: Fiyatlandırma matrisi (singleton, JSON field)

### Analytics (`apps.analytics`)
- `OturumLogu`: (see above — updated 2026-07-20)

### Audit (`apps.audit`)
- `AuditLog`: Model değişiklik loglama (model_type, object_id, action, user FK, timestamp, old_values JSON, new_values JSON)

---

## Kategori, Reklam, Kiosk, Log/Session İle İlgili Backend Mantığı

### Kategori Akışı
1. SuperAdmin → web_panels MedicalLogic → `POST /api/products/kategoriler/` → `Kategori` model kaydı
2. Kiosk → `GET /api/kiosk/v1/sync/` → backend kategorileri çeker (`products.Kategori.objects.filter(aktif=True)`)
3. Backend → kategorileri + hedef_cinsiyet + hedef_yas_araliklari ile JSON response
4. Kiosk edge API → SQLite `kategoriler` tablosuna upsert

### Reklam (Campaign) Akışı
1. SuperAdmin → web_panels CampaignWizard → `POST /api/campaigns/v2/campaigns/` → `Campaign` kaydı
2. SuperAdmin → Creative upload → `POST /api/campaigns/upload-media/` → MinIO/S3'e upload → `POST /api/campaigns/v2/creatives/` → `Creative` kaydı
3. SuperAdmin → ScheduleRule tanımlama → `POST /api/campaigns/v2/campaigns/{id}/rules/` → `ScheduleRule` kaydı
4. Backend scheduler (cron job) → `generate_for_kiosk(date, kiosk_id)` → slot hesaplama → `Playlist` + `PlaylistItem` oluşturma
5. Kiosk → `GET /api/kiosk/v1/ping/` → backend playlist versiyonu döner
6. Kiosk → `GET /api/kiosk/v1/playlist/?date=YYYY-MM-DD` → günlük playlist JSON
7. Kiosk edge API → SQLite `playlists` + `playlist_items` tablolarına yazar
8. Kiosk UI → AdStrip → playlist'ten sırayla creative oynatır

### Kiosk Authentication
Tek yöntem:
- **App-Key + MAC:** `KioskAppKeyAuthentication` (HTTP header `Authorization: AppKey <app_key>`, `X-Kiosk-MAC`)

Kiosk provisioning (bootstrap):
1. `POST /api/kiosk/v1/bootstrap/` → Fleet Key + HMAC doğrulaması
2. Kiosk bulunamazsa → `KioskProvisioningRequest` PENDING kaydı oluşturulur → `202 Accepted`
3. SuperAdmin → `GET /api/pharmacies/kiosks/provisioning/` → pending cihazları listeler
4. SuperAdmin → `POST /api/pharmacies/kiosks/provisioning/{id}/approve/` → eczane seçer, Kiosk oluşturulur, APPROVED
5. Cihaz tekrar `POST /api/kiosk/v1/bootstrap/` → 200 app_key (APPROVED path)
6. REJECTED cihaz → 403 REJECTED, App Key verilmez

### Log/Session Akışı
1. Kiosk UI → kullanıcı kategori/soru akışını tamamlar → QR üretilir
2. Kiosk UI → `POST http://localhost:5234/sessions` (local edge API) → session JSON gönderilir
3. Kiosk edge API → SQLite `oturum_outbox` tablosuna yazar
4. Kiosk edge scheduler (cron) → `POST /api/kiosk/v1/sessions/` → backend'e batch gönderim
5. Backend → `OturumLogu` modeline kayıt (idempotency_anahtari ile duplikasyon koruması)
6. Eczacı → web_panels QrScan → `GET /api/analytics/sessions/?qr_kodu={qr_kodu}` → session detayı çekme

Notlar (QR contract, 2026-07-20):
- QR üretimi 8 karakter Base36 (0-9A-Z) olarak korunur; algoritma değiştirilmez.
- QR içine soru/cevap/kategori/etken madde gömülmez; QR yalnızca backend'deki `OturumLogu` kaydını bulmak için kullanılır.
- Kiosk session verisini mevcut `POST /api/oturum/gonder` akışıyla lokal API'ye yazar; bu akış merkezi backend'e `POST /api/analytics/sessions/` ile gönderilir.
- Eczacı sorgusunda sahiplik kontrolü backend'de zorunludur (`kiosk__eczane_id == request.user.eczane_id`).

### Proof-of-Play Akışı
1. Kiosk UI AdStrip → creative oynatma başlangıç/bitiş zamanlarını kaydeder
2. Kiosk UI → `POST http://localhost:5234/ad-impressions` → impression JSON gönderilir
3. Kiosk edge API → SQLite `reklam_gosterim_outbox` tablosuna yazar
4. Kiosk edge scheduler → `POST /api/kiosk/v1/proof-of-play/` → backend'e batch gönderim
5. Backend → `PlayLog` modeline kayıt (bulk insert)
6. SuperAdmin → web_panels analytics → PlayLog raporları (tamamlanma oranı, toplam impression, vb.)

---

## Önemli Config / Env Değerleri

| Env | Açıklama | Varsayılan |
|-----|----------|-----------|
| `DJANGO_DEBUG` | Debug modu | `False` |
| `DJANGO_SECRET_KEY` | JWT/session secret | (gerekli, min 50 char) |
| `DJANGO_ALLOWED_HOSTS` | İzinli hostlar | (gerekli prod'da) |
| `DB_NAME` / `POSTGRES_DB` | PostgreSQL DB adı | `eisa` |
| `DB_USER` / `POSTGRES_USER` | PostgreSQL user | `eisa` |
| `DB_PASSWORD` / `POSTGRES_PASSWORD` | PostgreSQL şifre | (gerekli) |
| `DB_HOST` / `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` / `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `CORS_ALLOWED_ORIGINS` | CORS izinli origin'ler | (gerekli) |
| `MINIO_ENDPOINT` | MinIO/S3 endpoint | (opsiyonel) |
| `MINIO_ACCESS_KEY` | MinIO access key | (opsiyonel) |
| `MINIO_SECRET_KEY` | MinIO secret key | (opsiyonel) |
| `SENTRY_DSN` | Sentry error tracking | (opsiyonel) |

**JWT ayarları:** `core_api/settings.py` içinde `SIMPLE_JWT` dict (access/refresh token TTL, algorithm, vb.)

**Loglama (2026-07-16):** Dosyaya YAZILMAZ; JSON stdout. Env: `LOG_LEVEL`, `LOG_FORMAT`, `SERVICE_NAME`, `APP_ENV`, `APP_VERSION`. Middleware: `apps.core.logging.middleware.CorrelationIdMiddleware` + `RequestLoggingMiddleware`. Formatter: `apps.core.logging.formatters.JsonFormatter`. Detay: [docs/operations/logging.md](../operations/logging.md). Ek endpoint'ler: `POST /api/kiosk/v1/diagnostics/` (AppKey+MAC; DB'ye yazmaz, JSON log üretir), `POST /api/analytics/client-events/` (JWT; rate limited).

---

## Dış Sistem Entegrasyonları

1. **MinIO / S3:** Creative/HouseAd media upload (`apps.campaigns.views.MediaUploadView`)
2. **Sentry:** Error tracking (prod ortamında `sentry_sdk.init`)
3. **Kiosk Edge API:** İki yönlü senkronizasyon (kiosk → backend: outbox push; backend → kiosk: kategori/playlist pull)

---

## Do Not Change Without Checking

**Critical system contracts — breaking these will affect all modules:**

1. **Kiosk Authentication Contract:**
   - `KioskAppKeyAuthentication`: X-Kiosk-App-Key + X-Kiosk-Mac-Address headers
   - Breaking: kiosk_edge/api-node cannot authenticate without App Key + MAC

2. **Campaign/Playlist Structure:**
   - `Campaign` → `Creative` → `ScheduleRule` → `Playlist` → `PlaylistItem`
   - Breaking: playlist generation/sync fails

3. **Kiosk Sync Payload (`/api/kiosk/v1/sync/`):**
   - Response: `{ kategoriler, sorular, cevaplar, etken_maddeler, danisma_kategorileri, creatives, house_ads }`
   - Request (outbox push): `{ sessions: [...] }`
   - Breaking: kiosk SQLite sync breaks

4. **Session Log Contract (`OturumLogu`):**
   - Required: `idempotency_anahtari`, `yas_araligi_id`, `cinsiyet_id`, `kategori_id`, `qr_kodu`, `tamamlandi`
   - Breaking: session recording fails

5. **Proof-of-Play Contract (`/api/kiosk/v1/proof-of-play/`):**
   - Implementation:
     - File: `backend/apps/campaigns/views_v2.py`
     - Class: `ProofOfPlayView` (line 1068)
     - URL mapping: `backend/apps/campaigns/urls.py` (line 58)
     - Model: `backend/apps/campaigns/models.py` → `PlayLog`
   - Request: `{ logs: [{ creative_id OR house_ad_id, played_at, duration_played, completed? }] }`
   - Bulk insert: `PlayLog.objects.bulk_create(bulk, batch_size=500)`
   - Breaking: impression tracking fails

6. **Playlist Version Mechanism:**
   - `Kiosk.last_playlist_version` + `Playlist.version` matching
   - Breaking: playlist sync loops or fails

---

## Belirsiz / Riskli Noktalar

1. **Playlist generation job'ları:** `GenerationJob` modeli ve `django_apscheduler` kullanımı mevcut ama job tracking ve error handling net değil.
2. **Campaign.target_pharmacies (legacy M2M):** Yeni kampanyalar `CampaignTarget` kullanıyor. İki mekanizma birlikte destekleniyor mu, priority? (Belirsiz)
3. **Kiosk authentication order:** App Key + MAC tek operasyonel kontrattir. (Belirsiz)
4. **OturumLogu idempotency:** `idempotency_anahtari` var ama backend'de `get_or_create` mi kullanılıyor, unique constraint yeterli mi? (Doğrulanmalı)
5. **PlayLog duplikasyon:** Kiosk aynı impression'ı iki kez gönderirse ne olur? Duplikasyon koruması yok gibi görünüyor. (Riskli)

---

**Satır sayısı: ~250**
