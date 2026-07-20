# DB and API Contracts

**Amaç:** Backend DB şeması, API endpoint'leri ve frontend/kiosk'un beklediği request/response yapılarını dokümante etmek.

---

## When To Read This File

- API contract değişikliklerinde
- DB migration eklerken
- Frontend/backend uyumsuzluklarında
- Yeni endpoint eklerken
- Request/response formatı sorunlarında

---

## Ana Tablolar / Entity'ler (Backend PostgreSQL)

### Core Tables

**users_eisauser**
- id, username, password, email, first_name, last_name
- rol (superadmin/pharmacist)
- eczane_id FK (nullable, pharmacist için gerekli)
- is_active, is_staff, is_superuser

**eczaneler**
- id, ad, il_id FK, ilce_id FK, adres, sahip_adi, telefon, eczane_kodu, aktif
- olusturulma_tarihi, olusturan, guncellenme_tarihi, guncelleyen, surum

**kiosklar**
- id, eczane_id FK, ad, mac_adresi (unique), uygulama_anahtari (unique), aktif, is_online, son_goruldu, last_playlist_version
- olusturulma_tarihi, guncellenme_tarihi

**kiosk_provisioning_requests** *(2026-07-14)*
- id (UUID), mac_adresi, hostname, device_metadata (JSON — token/secret içermez)
- status (PENDING/APPROVED/REJECTED), last_seen_at, request_count
- approved_at, approved_by FK (nullable), rejected_at, rejected_by FK (nullable), rejection_reason
- kiosk FK (nullable, SET_NULL — OneToOne), olusturulma_tarihi, guncellenme_tarihi, surum
- **Güvenlik:** Raw fleet_key veya provision_secret bu tabloda saklanmaz.

### Lookups

**iller**: id, ad
**ilceler**: id, il_id FK, ad
**cinsiyetler**: id, ad (Kadın, Erkek, Diğer)
**yas_araliklari**: id, etiket (0-17, 18-24, 25-34, 35-49, 50+)

### Products (Kategori/Soru)

**kategoriler**
- id, ad, slug (unique), ikon, aktif
- hedef_cinsiyet_id FK (nullable)
- hedef_yas_araliklari M2M (kategori_yas_araliklari junction table)
- bagli_kategori_id FK self (nullable)

**sorular**
- id, kategori_id FK, metin, sira
- hedef_cinsiyet_id FK (nullable)
- hedef_yas_araliklari M2M (soru_yas_araliklari junction table)
- hedef_etken_maddeler M2M (soru_etken_madde junction table)

**cevaplar**
- id, soru_id FK, metin, sira

**etken_maddeler**
- id, ad, slug (unique), aktif

**cevap_etken_madde**
- cevap_id FK, etken_madde_id FK, aktif

**danisma_kategorileri**
- id, ad, slug (unique), ikon, aktif, ust_kategori_id FK self (nullable)

### Campaigns (DOOH v2)

**dooh_campaigns**
- id (UUID), advertiser_id (UUID, nullable), advertiser_name, name
- start_date, end_date, status (ACTIVE/PAUSED/COMPLETED)
- impression_goal (nullable), frequency_cap_per_hour (nullable)
- priority (default 50), is_guaranteed (bool)
- target_pharmacies M2M (legacy)

**dooh_campaign_targets**
- id (UUID), campaign_id FK, target_type (IL/ILCE/ECZANE)
- il_id FK (nullable), ilce_id FK (nullable), eczane_id FK (nullable)

**dooh_creatives**
- id (UUID), campaign_id FK, media_url, duration_seconds (1-60), name, checksum

**dooh_schedule_rules**
- id (UUID), campaign_id FK (1to1), frequency_type (PER_LOOP/PER_HOUR/PER_DAY), frequency_value, target_hours (JSON)

**dooh_playlists**
- id (UUID), kiosk_id FK, target_date, target_hour (0-23, Istanbul yereli), loop_duration_seconds (default 60), version
- unique(kiosk, target_date, target_hour); item'lar ayri dooh_playlist_items satirlarinda

**dooh_playlist_items**
- id (UUID), playlist_id FK, creative_id FK (nullable), house_ad_id FK (nullable), playback_order, estimated_start_offset_seconds (SAAT-mutlak 0..3599)
- API contract'ta creative/house_ad -> asset_id + asset_type + media_url + duration_seconds olarak duzlestirilir

**dooh_house_ads**
- id (UUID), name, media_url, duration_seconds (1-60), aktif (bool), priority

**dooh_play_logs**
- id (UUID), kiosk_id FK, creative_id FK (nullable, SET_NULL), house_ad_id FK (nullable, SET_NULL)
- played_at (indexed), duration_played (saniye)

**dooh_pricing_matrix**
- id (singleton), matrix (JSON)

### Analytics

**oturum_loglari**
- id, idempotency_anahtari (UUID, unique), kiosk_id FK
- yas_araligi_id FK, cinsiyet_id FK, kategori_id FK
- hassas_akis (bool), qr_kodu (indexed), cevaplar (JSON), onerilen_etken_maddeler (JSON), tamamlandi (bool)
- olusturulma_tarihi
- danisma_tamamlandi (bool, default=false)
- danisma_tamamlanma_tarihi (datetime, nullable)
- danisma_notu (text, blank)
- danisma_tamamlayan_eczaci_id FK (users_eisauser, nullable)

---

## API Contract (Backend REST API)

### Auth Endpoints

**POST /api/auth/token/**
- Request: `{ "username": "admin", "password": "secret" }`
- Response: `{ "role": "superadmin", "pharmacyId": null, "userId": 1 }`
- Set-Cookie: `access_token`, `refresh_token` (httpOnly)

**POST /api/auth/token/refresh/**
- Request: (no body, çerezden refresh_token okunur)
- Response: (empty body)
- Set-Cookie: `access_token` (yenilenir)

**POST /api/auth/logout/**
- Request: (no body)
- Response: (empty body)
- Set-Cookie: `access_token`, `refresh_token` (expire)

---

### Lookups Endpoints

**GET /api/lookups/iller/**
- Response: `[{ "id": 1, "ad": "Ankara" }, ...]`

**GET /api/lookups/ilceler/?il={il_id}**
- Response: `[{ "id": 1, "il": 1, "ad": "Çankaya" }, ...]`

**GET /api/lookups/cinsiyetler/**
- Response: `[{ "id": 1, "ad": "Kadın" }, { "id": 2, "ad": "Erkek" }, { "id": 3, "ad": "Diğer" }]`

**GET /api/lookups/yas-araliklari/**
- Response: `[{ "id": 1, "etiket": "0-17" }, { "id": 2, "etiket": "18-24" }, ...]`

---

### Pharmacies Endpoints

**GET /api/pharmacies/eczaneler/**
- Auth: JWT (SuperAdmin)
- Response: `[{ "id": 1, "ad": "Merkez Eczane", "il": {...}, "ilce": {...}, "aktif": true }, ...]`

**POST /api/pharmacies/eczaneler/**
- Auth: JWT (SuperAdmin)
- Request: `{ "ad": "Yeni Eczane", "il_id": 1, "ilce_id": 5, "adres": "...", "sahip_adi": "...", "telefon": "...", "aktif": true }`
- Response: `{ "id": 2, ... }`

**GET /api/pharmacies/kiosklar/**
- Auth: JWT (SuperAdmin/Pharmacist)
- Response: `[{ "id": 1, "eczane": {...}, "mac_adresi": "AA:BB:CC:DD:EE:FF", "aktif": true, "is_online": false }, ...]`

---

### Provisioning Endpoints *(2026-07-14)*

**POST /api/kiosk/v1/bootstrap/** *(2026-07-20; provisioning bootstrap yolu)*
- Auth: `X-Kiosk-Key: <fleet_key>` (header) + HMAC; body: `{ "mac_adresi": "...", "timestamp": "ISO", "hmac": "...", "hostname": "...", "device_metadata": { ... } }`
- `hostname` ve `device_metadata` opsiyonel; kiosk_edge `collectDeviceMetadata()` ile otomatik doldurur
- Response 200 (onaylı+aktif+eczaneli kiosk): `{ "status": "APPROVED", "kiosk_id": 1, "pharmacy_id": 1, "app_key": "..." }` — aynı kiosk tekrar bootstrap yaptığında AYNI `app_key` döner (rotasyon yok)
- Response 202 (bilinmeyen/onay bekleyen cihaz, PENDING): `{ "status": "PENDING", "registration_id": "uuid", "retry_after_seconds": 30 }`
- Response 403 (reddedilmiş): `{ "status": "REJECTED" }`
- Response 401: Geçersiz fleet key veya HMAC (hangi credential yanlış belirtilmez)
- Provisioning admin API'leri değişmedi: `/api/pharmacies/kiosks/provisioning/` list/detail/approve/reject (JWT SuperAdmin). Onay anında `Kiosk.uygulama_anahtari = secrets.token_urlsafe(48)` üretilir; bootstrap bu değeri döner.

### Kiosk API (facade) — Operasyonel Endpoint'ler *(2026-07-20)*

Namespace `/api/kiosk/v1/` (backend `apps/kiosk_api/`). **Tek auth contract'ı** (bootstrap hariç):
```
Authorization: AppKey <APP_KEY>
X-Kiosk-MAC:   <NORMALIZED_MAC>   # AA:BB:CC:DD:EE:FF
```
- **401** — App Key/MAC eksik veya App Key/MAC çifti geçersiz (`code`: `app_key_missing|mac_missing|app_key_invalid|app_key_malformed`)
- **403** — kiosk pasif/onaysız veya eczaneye bağlı değil (`code`: `kiosk_inactive|kiosk_unlinked`)
- Başka auth turleri operasyonel endpoint'lerde **reddedilir**. URL'de kiosk ID **yoktur**; kiosk `request.kiosk` (auth context) üzerinden belirlenir.

| Method | Path | Amaç |
|--------|------|------|
| GET  | `/api/kiosk/v1/ping/` | Heartbeat + bugünkü playlist versiyonu |
| GET  | `/api/kiosk/v1/sync/` | Aktif creative + house_ad + lookup |
| GET  | `/api/kiosk/v1/catalog/` | Kategori/soru/cevap/etken madde/danışma |
| GET  | `/api/kiosk/v1/playlist/?date=YYYY-MM-DD` | Günün 24 saatlik playlist'i |
| POST | `/api/kiosk/v1/sessions/` | Oturum outbox (idempotent) — `OturumLoguItemSerializer` |
| POST | `/api/kiosk/v1/proof-of-play/` | Reklam gösterim (PlayLog) toplu |
| POST | `/api/kiosk/v1/diagnostics/` | Diagnostic outbox (DB'ye yazılmaz, JSON stdout) |

**Kaldırılan (hard cutover):** eski id-tabanlı kiosk yolları ve eski bootstrap yolu kaldırıldı. Kiosk oturumları artık `/api/kiosk/v1/sessions/` kullanır; `/api/analytics/sessions/` GET panel/eczacı içindir.

**GET /api/pharmacies/kiosks/provisioning/**
- Auth: JWT (SuperAdmin)
- Filters: `?status=PENDING&mac=AA:BB:...&hostname=kiosk1`
- Response: `[{ "id": "uuid", "mac_adresi": "...", "hostname": "...", "status": "PENDING", "first_seen_at": "...", "last_seen_at": "...", "request_count": 2, ... }]`

**GET /api/pharmacies/kiosks/provisioning/{id}/**
- Auth: JWT (SuperAdmin)
- Response: single KioskProvisioningRequest object (yukarıdakiyle aynı schema)

**POST /api/pharmacies/kiosks/provisioning/{id}/approve/**
- Auth: JWT (SuperAdmin)
- Request: `{ "eczane_id": 1, "ad": "Kiosk 1" }`
- Response 200: approved KioskProvisioningRequest (kiosk_id dahil)
- Response 409: MAC zaten kayıtlı / reddedilmiş talep
- Response 400: eczane_id bulunamadı / eksik alan
- **İdempotent:** Aynı kiosk ile zaten onaylanmışsa 200 döner.

**POST /api/pharmacies/kiosks/provisioning/{id}/reject/**
- Auth: JWT (SuperAdmin)
- Request: `{ "rejection_reason": "..." }` (opsiyonel)
- Response 200: rejected KioskProvisioningRequest
- Response 409: zaten onaylanmış talep

**POST /api/pharmacies/kiosklar/**
- Auth: JWT (SuperAdmin)
- Request: `{ "eczane_id": 1, "ad": "Kiosk 1", "mac_adresi": "AA:BB:CC:DD:EE:FF", "uygulama_anahtari": "secret-key", "aktif": true }`
- Response: `{ "id": 1, ... }`

**GET /api/analytics/sessions/?qr_kodu={qr_kodu}**
- Auth: JWT (SuperAdmin/Pharmacist)
- QR formatı: `^[0-9A-Z]{8}$`
- Hata durumları:
  - `400`: boş veya formatı geçersiz QR
  - `404`: QR koduna ait oturum bulunamadı
  - `403`: eczane sahipliği uyuşmuyor veya kullanıcı eczaneye bağlı değil
- Response: tek oturum objesi (`OturumLoguSerializer`) + normalize detay alanları (`kiosk_detay`, `eczane`, `yas_araligi_detay`, `cinsiyet_detay`, `kategori_detay`, `cevap_detaylari`, `onerilen_etken_madde_detaylari`)

---

### Products Endpoints

**GET /api/products/kategoriler/**
- Auth: JWT (SuperAdmin)
- Response: `[{ "id": 1, "ad": "Uyku Sorunu", "slug": "uyku-sorunu", "ikon": "fa-bed", "hedef_cinsiyet": null, "hedef_yas_araliklari": [2, 3, 4], "aktif": true }, ...]`

**POST /api/products/kategoriler/**
- Auth: JWT (SuperAdmin)
- Request: `{ "ad": "Enerji", "slug": "enerji", "ikon": "fa-bolt", "hedef_cinsiyet_id": null, "hedef_yas_araliklari": [], "aktif": true }`
- Response: `{ "id": 2, ... }`

**GET /api/products/sorular/?kategori={kategori_id}**
- Auth: JWT (SuperAdmin)
- Response: `[{ "id": 1, "kategori": 1, "metin": "Uykuya dalmakta zorluk çekiyor musunuz?", "sira": 1, "hedef_cinsiyet": null, "hedef_yas_araliklari": [] }, ...]`

**POST /api/products/sorular/**
- Auth: JWT (SuperAdmin)
- Request: `{ "kategori_id": 1, "metin": "Gece uyanıyor musunuz?", "sira": 2, "hedef_cinsiyet_id": null, "hedef_yas_araliklari": [] }`
- Response: `{ "id": 2, ... }`

**GET /api/products/danisma-kategorileri/**
- Auth: JWT (SuperAdmin)
- Response: `[{ "id": 1, "ad": "Reçete Danışma", "slug": "recete-danisma", "ikon": "fa-prescription", "ust_kategori": null, "aktif": true }, ...]`

---

### Analytics Endpoints

**GET /api/analytics/sessions/**
- Auth: JWT (SuperAdmin/Pharmacist)
- Query Params: `qr_kodu`, `qr_code`, `qr`, `hassas_akis`, `is_sensitive_flow`, `page_size`
- Response:
  - `qr*` parametresi yoksa: paginated list
  - `qr*` parametresi varsa: tek oturum objesi veya 400/403/404

**POST /api/analytics/sessions/{id}/complete/**
- Auth: JWT (Pharmacist)
- `{id}` is the integer `OturumLogu.id` primary key
- Request: `{ "note": "Optional pharmacist note.", "sale_result": "sold|not_sold" }`
- Response: (single updated `OturumLoguSerializer` object)
- Not: Satış sonucu için kalıcı DB alanı yoktur; `sale_result` response'ta `satis_sonucu` metni üretmek için kullanılabilir.

**POST /api/kiosk/v1/diagnostics/** *(2026-07-16)*
- Auth: Kiosk (AppKey + MAC)
- Rate limit: `kiosk_diagnostic` scope (varsayılan 60/min)
- Request: `{ "items": [{ "id": 1, "level": "ERROR", "event": "sync_sessions_failed", "message": "backend 503", "context": {...}, "correlation_id": "...", "occurred_at": "..." }, ...] }`
- Response 202: `{ "accepted": N, "rejected": M, "errors": [...], "accepted_keys": ["1", ...] }`
- Backend gelen kayıtları **DB'ye YAZMAZ**; sanitize edip JSON log stdout'a çevirir (`logger=eisa.kiosk.diagnostic`). Batch max 100 kayıt, mesaj 4 KB, stack 8 KB, context sanitize.

**POST /api/analytics/client-events/** *(2026-07-16)*
- Auth: JWT (SuperAdmin/Pharmacist)
- Rate limit: `client_event` scope (varsayılan 30/min)
- Request: `{ "items": [{ "level": "ERROR", "event": "vue_error_handler", "message": "...", "stack": "...", "component": "...", "route": "...", "correlation_id": "...", "occurred_at": "..." }, ...] }`
- Response 202: `{ "accepted": N }`
- Backend gelen kayıtları **DB'ye YAZMAZ**; sanitize edip JSON log stdout'a çevirir (`logger=eisa.client`). Allow-list dışı alanlar (`password`, `token` vb.) düşürülür.

**Ortak:** Tüm response'lar `X-Correlation-ID` başlığı içerir. Detay: [docs/operations/logging.md](../operations/logging.md).

---

### Campaigns Endpoints (DOOH v2)

**GET /api/campaigns/v2/campaigns/**
- Auth: JWT (SuperAdmin)
- Response: `[{ "id": "uuid", "name": "Vitamin C Kampanyası", "start_date": "2026-06-01T00:00:00Z", "end_date": "2026-06-30T23:59:59Z", "status": "ACTIVE", "priority": 50, "is_guaranteed": false, "creatives": [...], "schedule_rule": {...} }, ...]`

**POST /api/campaigns/v2/campaigns/**
- Auth: JWT (SuperAdmin)
- Request: `{ "name": "Kampanya 1", "advertiser_name": "XYZ", "start_date": "...", "end_date": "...", "priority": 50, "is_guaranteed": false }`
- Response: `{ "id": "uuid", ... }`

**POST /api/campaigns/upload-media/**
- Auth: JWT (SuperAdmin)
- Request: multipart/form-data, field: `file`
- Response: `{ "media_url": "https://cdn.example.com/creative.mp4", "checksum": "abc123" }`

**POST /api/campaigns/v2/creatives/**
- Auth: JWT (SuperAdmin)
- Request: `{ "campaign_id": "uuid", "media_url": "...", "duration_seconds": 15, "name": "Creative 1" }`
- Response: `{ "id": "uuid", ... }`

**GET /api/campaigns/v2/campaigns/{id}/rules/**
- Auth: JWT (SuperAdmin)
- Response: `{ "id": "uuid", "campaign": "uuid", "frequency_type": "PER_HOUR", "frequency_value": 2, "target_hours": [9, 10, 11, 12, 13] }`

**POST /api/campaigns/v2/campaigns/{id}/rules/**
- Auth: JWT (SuperAdmin)
- Request: `{ "frequency_type": "PER_HOUR", "frequency_value": 2, "target_hours": [9, 10, 11, 12] }`
- Response: `{ "id": "uuid", ... }`

**GET /api/campaigns/v2/pricing-matrix/**
- Auth: JWT (SuperAdmin)
- Response: `{ "matrix": { ... } }` (JSON object)

**PUT /api/campaigns/v2/pricing-matrix/**
- Auth: JWT (SuperAdmin)
- Request: `{ "matrix": { ... } }`
- Response: `{ "matrix": { ... } }`

**POST /api/campaigns/v2/playlists/generate/**
- Auth: JWT (SuperAdmin)
- Request: `{ "kiosk_id": 1, "start_date": "2026-06-01", "end_date": "2026-06-30" }`
- Response: `{ "job_id": "uuid", "status": "PENDING" }`

**GET /api/campaigns/v2/playlists/jobs/{job_id}/**
- Auth: JWT (SuperAdmin)
- Response: `{ "job_id": "uuid", "status": "COMPLETED", "result": { ... } }`

---

### Kiosk Edge Endpoints (Kiosk Authentication)

**GET /api/kiosk/v1/ping/**
- Auth: Kiosk (AppKey + MAC)
- Response: `{ "playlist_version": 42, "current_time": "2026-06-05T10:30:00Z" }`

**GET /api/kiosk/v1/sync/**
- Auth: Kiosk (AppKey + MAC)
- Response:
  ```json
  {
    "kategoriler": [{ "id": 1, "ad": "...", ... }],
    "sorular": [...],
    "cevaplar": [...],
    "etken_maddeler": [...],
    "danisma_kategorileri": [...],
    "creatives": [{ "id": "uuid", "media_url": "...", ... }],
    "house_ads": [{ "id": "uuid", "media_url": "...", ... }]
  }
  ```
- Body (optional, outbox push):
  ```json
  {
    "sessions": [
      {
        "idempotency_key": "uuid",
        "yas_araligi_id": 2,
        "cinsiyet_id": 1,
        "kategori_id": 5,
        "hassas_akis": false,
        "qr_kodu": "EISA-...",
        "cevaplar": {...},
        "onerilen_etken_maddeler": [...],
        "tamamlandi": true
      }
    ]
  }
  ```

**GET /api/kiosk/v1/playlist/?date=YYYY-MM-DD**
- Auth: Kiosk (AppKey + MAC)
- Response (günün TÜM saatleri tek istekte döner):
  ```json
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
            "media_url": "https://cdn.example.com/creative.mp4",
            "duration_seconds": 15,
            "playback_order": 1,
            "estimated_start_offset_seconds": 0
          }
        ]
      }
    ]
  }
  ```

**POST /api/kiosk/v1/proof-of-play/**
- Auth: Kiosk (AppKey + MAC)
- Request (her log'da creative_id VEYA house_ad_id):
  ```json
  {
    "logs": [
      {
        "creative_id": "uuid",
        "played_at": "2026-06-05T10:30:00.000Z",
        "duration_played": 15
      },
      {
        "house_ad_id": "uuid",
        "played_at": "2026-06-05T10:30:15.000Z",
        "duration_played": 10
      }
    ]
  }
  ```
- Response: `201 { "ingested": 10 }` (kaydedilen log sayisi)

---

## Frontend / Kiosk Beklentileri

### web_panels (Vue 3)

**Expected Response Fields:**
- Campaign list: `id`, `name`, `status`, `start_date`, `end_date`, `priority`, `is_guaranteed`, `creatives` (array), `schedule_rule` (object)
- Creative: `id`, `campaign_id`, `media_url`, `duration_seconds`, `name`
- Kategori: `id`, `ad`, `slug`, `ikon`, `hedef_cinsiyet`, `hedef_yas_araliklari` (array of IDs), `aktif`
- Session (QR tarama): `id`, `qr_kodu` (8 karakter), `kiosk`, `yas_araligi`, `cinsiyet`, `kategori`, `cevaplar`, `cevap_detaylari`, `onerilen_etken_maddeler`, `onerilen_etken_madde_detaylari`, `danisma_*` alanları

**Potential Mismatch:**
- Backend → `hedef_yas_araliklari` (array of IDs) → Frontend expects labels? (Belirsiz)
- Session → `onerilen_etken_maddeler` (backend JSON array of strings vs frontend expects array of objects?) (Belirsiz)

### kiosk_edge/ui (Svelte 5)

**Expected Response Fields (Lokal API):**
- Category: `id`, `ad`, `slug`, `ikon`, `hedef_cinsiyet_id`, `hedef_yas_araliklari` (JSON array)
- Question: `id`, `kategori_id`, `metin`, `sira`, `hedef_cinsiyet_id`, `hedef_yas_araliklari` (JSON array)
- Playlist: `id`, `items` (array: `asset_type`, `asset_id`, `media_url`, `duration_seconds`, `playback_order`)

**Potential Mismatch:**
- `hedef_yas_araliklari` → Backend M2M junction table → Lokal API JSON array → Kiosk UI filtering logic? (Doğrulanmalı)
- `onerilen_etken_maddeler` → Kiosk UI `lib/ingredients.js` tarafından hesaplanıyor, backend'den gelmiyor. Backend kaydederken string array olarak bekliyor. (Tutarlı)

---

## Do Not Change Without Checking

**Critical DB schema and API contracts:**

1. **Core Table Structure:**
   - `eczaneler`, `kiosklar` (with mac_adresi, uygulama_anahtari unique)
   - `kategoriler`, `sorular`, `cevaplar` (with hedef filtering)
   - `dooh_campaigns`, `dooh_creatives`, `dooh_playlists`
   - `oturum_loglari` (with idempotency_anahtari unique)
   - Breaking: entire system fails

2. **Kiosk API Response Format:**
  - `/api/kiosk/v1/sync/` response structure
  - `/api/kiosk/v1/playlist/` response structure
   - Breaking: kiosk cannot parse

3. **Session Log Fields:**
   - Required: `idempotency_key`, `yas_araligi_id`, `cinsiyet_id`, `kategori_id`, `qr_kodu`, `tamamlandi`
   - JSON fields: `cevaplar`, `onerilen_etken_maddeler`
   - Breaking: session logging fails

4. **Playlist Item Structure:**
   - `{ asset_type, asset_id, media_url, duration_seconds, playback_order }`
   - Breaking: ad playback fails

5. **Authentication Headers:**
   - JWT: httpOnly cookies
  - Kiosk: Authorization: AppKey <APP_KEY> + X-Kiosk-MAC
   - Breaking: auth fails

---

## Backend ile Frontend Arasında Uyumsuz Görünen Alanlar

1. **hedef_yas_araliklari format:**
   - Backend: M2M junction table → API response'da ID array `[2, 3, 4]`
   - Lokal API (kiosk_edge/api-node): JSON array `[2, 3, 4]`
   - Frontend: ID'lerden label çözümlemesi yapılıyor mu? (Belirsiz)

2. **onerilen_etken_maddeler format:**
   - Backend: JSON array of strings `["Melatonin", "Valerian"]`
   - Kiosk UI: `lib/ingredients.js` → hesaplama sonucu string array
   - web_panels QrScan: String array olarak gösterim
   - (Tutarlı gibi görünüyor ama doğrulanmalı)

3. **Campaign targeting:**
   - Backend: Hem `target_pharmacies` M2M (legacy) hem `CampaignTarget` (yeni) destekleniyor
   - Frontend: Hangi mekanizmayı kullanıyor? (Belirsiz)
   - Kiosk: Backend playlist üretiminde hangi hedefleme kullanılıyor? (Belirsiz)

4. **Session QR response:**
  - QR 8 karakterdir ve yalnızca merkezi backend'deki oturumu bulmak için kullanılır.
  - QR içine soru/cevap/kategori/etken madde payload'ı gömülmez.
  - Response, mevcut alanları bozmadan ek detay alanlarıyla normalize edilir.

5. **PlayLog creative_id vs house_ad_id:**
   - Backend: İki ayrı FK (nullable)
   - Kiosk UI: Sadece `creative_id` gönderiyor, house_ad impression'ları eksik olabilir (Riskli)

---

**Satır sayısı: ~250**
