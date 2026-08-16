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
- id, eczane_id FK, ad, mac_adresi (unique), device_id (unique, nullable), uygulama_anahtari (unique), aktif, is_online, son_goruldu, last_playlist_version
- olusturulma_tarihi, guncellenme_tarihi
- **device_id:** Kalici cihaz UUID, bootstrap sirasinda kilit (MAC spoofing onlenir)

**kiosk_provisioning_requests** *(2026-07-14, updated 2026-07-20)*
- id (UUID), mac_adresi, device_id, hostname, device_metadata (JSON — token/secret içermez)
- status (PENDING/APPROVED/REJECTED), last_seen_at, request_count
- approved_at, approved_by FK (nullable), rejected_at, rejected_by FK (nullable), rejection_reason
- kiosk FK (nullable, SET_NULL — OneToOne), olusturulma_tarihi, guncellenme_tarihi, surum
- **Güvenlik:** Raw fleet_key veya provision_secret bu tabloda saklanmaz. device_id bootstrap HMAC'e dahil edilir.

### Destek (Görüş ve Destek) *(new 2026-08-15)*

**destek_parametreler**
- id, grup (TALEP_TURU|ALAN|ALT_KONU|DURUM), kod (unique), ad, ust_parametre_id FK self (nullable, PROTECT), sira, aktif
- BaseModel alanları (olusturulma_tarihi, guncellenme_tarihi, surum, vb.)
- Başlangıç seed: TALEP_TURU (ONERI, SIKAYET), ALAN (KIOSK, PORTAL), DURUM (YENI, INCELENIYOR, YANITLANDI, KAPATILDI) + 10 ALT_KONU

**destek_talep_sayac**
- yil (PK, SmallInt), son_sayi (PositiveInt) — `select_for_update` ile concurrency-safe talep no üretimi

**destek_talepler**
- id, talep_no (unique, `EISA-YYYY-NNNNNN`), eczane_id FK (PROTECT), olusturan_kullanici_id FK (PROTECT)
- talep_turu_id FK destek_parametreler (PROTECT), alan_id FK (PROTECT), alt_konu_id FK (PROTECT), durum_id FK (PROTECT)
- kiosk_id FK kiosklar (PROTECT, nullable), aciklama (max 1000), son_hareket_tarihi
- BaseModel alanları

**destek_yorumlar**
- id, talep_id FK destek_talepler (CASCADE), yorum_metni (max 1000)
- BaseModel alanları (olusturan = yorum yazarı)

### Destek API Sözleşmesi *(2026-08-15)*

**GET `/api/destek/parametreler/`** — Auth: JWT (any)
- Response: `[{id, grup, kod, ad, ust_parametre_id, sira}]`

**GET `/api/destek/talepler/`** — Auth: JWT (any); sayfalı
- Admin: tüm talepler
- Eczacı: yalnız kendi eczanesinin talepleri
- Query params: `eczane_id, talep_turu_kod, alan_kod, alt_konu_kod, durum_kod, durum_kategori (acik|kapali), baslangic_tarihi, bitis_tarihi, talep_no, page, page_size`
- Response: `{count, next, previous, results: [{id, talep_no, eczane_adi, olusturan_adi, talep_turu_ad, talep_turu_kod, alan_ad, alan_kod, alt_konu_ad, alt_konu_kod, durum_ad, durum_kod, kiosk_ad, olusturulma_tarihi, son_hareket_tarihi}]}`

**POST `/api/destek/talepler/`** — Auth: JWT (IsEczaci only)
- Request: `{talep_turu_id, alan_id, alt_konu_id, kiosk_id?, aciklama}`
- Validasyon: grup kontrolü, aktiflik, alan↔alt_konu eşleşmesi, Portal→kiosk boş, kiosk eczane sahipliği, KIOSK_CIHAZ tek kiosk otomatik atama
- Response 201: DestekTalebiDetailSerializer

**GET `/api/destek/talepler/{id}/`** — Auth: JWT (any)
- Response: list alanları + `{eczane_id, kiosk_id, aciklama, yorumlar: [{id, yorum_metni, olusturulma_tarihi, yazar_adi, yazar_rol}]}`

**POST `/api/destek/talepler/{id}/yorum-ekle/`** — Auth: JWT (any)
- Request: `{yorum_metni}` (max 1000 karakter)
- 400: KAPATILDI ticket
- Admin yorum → durum YANITLANDI; Eczacı YANITLANDI'da cevap → INCELENIYOR
- Response 201: `{id, yorum_metni, olusturulma_tarihi, yazar_adi, yazar_rol}`

**PATCH `/api/destek/talepler/{id}/durum-degistir/`** — Auth: JWT (IsSuperAdmin)
- Request: `{durum_kod}` — YENI|INCELENIYOR|YANITLANDI|KAPATILDI
- Response 200: DestekTalebiListSerializer

**GET `/api/destek/talepler/yeni-sayisi/`** — Auth: JWT (IsSuperAdmin)
- Response: `{sayi: <int>}`

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

**dooh_campaigns** *(Faz 7 sonrasi — 0020 migrasyonu)*
- id (UUID), advertiser_id (UUID, nullable), advertiser_name, name
- start_date, end_date, status (DRAFT/ACTIVE/PAUSED/COMPLETED/CANCELLED)
- target_scope (ALL|RULES|null-legacy), follows_id FK self (nullable)
- priority (default 50)
- target_pharmacies M2M (legacy, fiziksel korunuyor; API write path kapali)
- **Kaldirildi (migration 0020):** is_guaranteed, impression_goal, frequency_cap_per_hour
- **Canonical:** DeliveryRule.guarantee_mode + max_per_hour + CAMPAIGN_TOTAL
- **constraints:** dooh_campaign_no_self_follow, dooh_campaign_follows_unique_predecessor

**dooh_campaign_targets** *(Faz 1: KIOSK + mode)*
- id (UUID), campaign_id FK, target_type (IL/ILCE/ECZANE/KIOSK), mode (INCLUDE/EXCLUDE|null)
- il_id FK (nullable), ilce_id FK (nullable), eczane_id FK (nullable), kiosk_id FK (nullable)

**dooh_delivery_rules** *(Faz 1 yeni)*
- id (UUID), campaign_id FK (1to1), delivery_type (TIME_WINDOW/PER_HOUR/PER_DAY/CAMPAIGN_TOTAL/LEGACY_PER_LOOP)
- count (>=1), window_start/end_time, active_hours JSON, active_weekdays JSON
- guarantee_mode (GUARANTEED/BEST_EFFORT), max_per_hour (nullable)
- API: LEGACY_PER_LOOP yazılamaz; TIME_WINDOW için window zorunlu

**dooh_planning_runs** / **dooh_campaign_total_allocations** / **dooh_kiosk_day_quotas** *(Faz 1 yeni)*
- KioskDayQuota: placed>=0, quota>=0, placed<=quota DB constraint; unique(run,campaign,kiosk,date)

**dooh_creatives** *(Faz 0.5: object_key, Faz 1: weight, 2026-07-31: active_media_url)*
- id (UUID), campaign_id FK, media_url (kalici URL Faz 0.5+), active_media_url (blank=True, islem ekrani alt alan gorseli ~1080x768), duration_seconds (grid:{15,30,45,60} yeni kayit), name, checksum ('sha256:<hex>'), object_key (nullable, 0015), weight (default 1)
- Migration 0021: active_media_url eklendi (additive, nullable)

**pharmacy_campaigns** *(2026-07-31, 2026-08-01)*
- id (UUID), name, media_url, object_key (nullable), start_at, end_at, duration_seconds (default 15; izin verilen: 15, 30, 60), is_active (bool)
- M2M: pharmacy_campaigns_target_pharmacies (campaign_id, eczane_id)
- M2M: pharmacy_campaigns_target_iller (campaign_id, il_id)
- M2M: pharmacy_campaigns_target_ilceler (campaign_id, ilce_id)
- Migration 0022: tablo ve M2M olusturuldu; Migration 0024: target_iller + target_ilceler eklendi
- Feed eşleşme: target_pharmacies OR target_iller OR target_ilceler (OR mantığı); hiç hedefi olmayan → feed'e girmez

**dooh_schedule_rules** *(Legacy, ScheduleRule → DeliveryRule geçiş)*
- id (UUID), campaign_id FK (1to1), frequency_type (PER_LOOP/PER_HOUR/PER_DAY), frequency_value, target_hours (JSON)

**dooh_playlists**
- id (UUID), kiosk_id FK, target_date, target_hour (0-23, Istanbul yereli), loop_duration_seconds (default 60), version
- unique(kiosk, target_date, target_hour); item'lar ayri dooh_playlist_items satirlarinda

**dooh_playlist_items**
- id (UUID), playlist_id FK, creative_id FK (creative-only; house_ad_id FK KALDIRILDI — migration 0027; `clean()` creative zorunlu), playback_order, estimated_start_offset_seconds (SAAT-mutlak 0..3599)
- API contract'ta creative -> asset_id + asset_type ("creative") + media_url + **active_media_url** + duration_seconds olarak duzlestirilir
- Playlist campaign-only: uygun creative yoksa 0 item (bos playlist gecerli) -> kiosk idle ekranini gosterir

**dooh_idle_screen_contents** *(2026-08-16)*
- id (BigAutoField), baslik (CharField<=100, zorunlu), metin (CharField<=300, zorunlu), aktif (bool default True), olusturulma_tarihi, guncellenme_tarihi
- "Icerik Yonetimi" idle (bekleme) ekrani baslık/metin icerigi; medya/HTML YOK. Eski `dooh_house_ads` tablosu migration 0027 ile dusuruldu.

**dooh_play_logs**
- id (UUID), kiosk_id FK, creative_id FK (nullable, SET_NULL) [house_ad_id FK KALDIRILDI — migration 0027]
- played_at (indexed), duration_played (saniye)

**dooh_pricing_matrix**
- id (singleton), matrix (JSON)

### Analytics

**oturum_loglari** *(updated 2026-08-11)*
- id, idempotency_anahtari (UUID, unique), kiosk_id FK
- yas_araligi_id FK, cinsiyet_id FK
- kategori_id FK (nullable), danisma_kategorisi_id FK (nullable)
- oturum_tipi (SIKAYET/OZEL_DANISMANLIK, indexed)
- hassas_akis (bool), qr_kodu (unique, indexed)
- cevaplar (JSON, backup), onerilen_etken_maddeler (JSON, backup), tamamlandi (bool)
- olusturulma_tarihi
- danisma_tamamlandi (bool, default=false)
- danisma_tamamlanma_tarihi (datetime, nullable)
- danisma_notu (text, blank)
- danisma_tamamlayan_eczaci_id FK (users_eisauser, nullable)
- **barkod_logo_id FK (barkod_logolar, PROTECT, nullable)** — fişte basılan logo; null = e-ISA fallback *(2026-08-11)*. PROTECT: geçmiş ölçüm kaybolmaz; logo fiziksel silinemez.

### Barkod Logo *(new 2026-08-11)*

**barkod_logolar**
- id (UUID PK), ad (max 255)
- media_url (kalıcı public URL), object_key (RustFS key), checksum (sha256:\<hex>)
- baslangic_zamani, bitis_zamani (UTC DateTimeField)
- aktif (bool, indexed), gunluk_baski_limiti (nullable PositiveInt, ≥1)
- olusturulma_tarihi, hedef_kiosklar (M2M → kiosklar)
- Endpoint: `/api/barkod-logo/logolar/` (ModelViewSet, SuperAdmin JWT)
- Upload: `POST /api/barkod-logo/upload-gorsel/` — PNG, 336×336, ≤1MB, alfa yok
- Catalog (kiosk): `GET /api/kiosk/v1/catalog/` artık `barkod_logolar` listesini içerir (aktif + bitis > now + hedef kiosk filtreli)

**oturum_cevaplar** *(new 2026-07-20)*
- id, oturum_id FK (CASCADE), soru_id FK (PROTECT, nullable), cevap_id FK (PROTECT, nullable)
- soru_metni_snapshot, cevap_metni_snapshot, cevap_degeri_snapshot
- unique (oturum_id, soru_id)

**oturum_onerilen_etken_maddeler** *(new 2026-07-20)*
- id, oturum_id FK (CASCADE), etken_madde_id FK (PROTECT, nullable)
- etken_madde_adi_snapshot
- unique (oturum_id, etken_madde_id)

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

**POST /api/kiosk/v1/bootstrap/** *(2026-07-20; provisioning bootstrap yolu, updated 2026-07-20)*
- Auth: `X-Kiosk-Key: <fleet_key>` (header) + HMAC; body: `{ "mac_adresi": "...", "device_id": "...", "timestamp": "ISO", "hmac": "...", "hostname": "...", "device_metadata": { ... } }`
- `device_id`: Kalici cihaz UUID (crypto.randomUUID), HMAC'e dahil edilir: `HMAC-SHA256(MAC_UPPER + iso_timestamp + device_id, provision_secret)`
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
X-Kiosk-Device-ID: <DEVICE_UUID>  # zorunlu (device_id set edildiyse)
```
- **401** — App Key/MAC eksik veya App Key/MAC çifti geçersiz; device_id eksik/uyumsuz (`code`: `app_key_missing|mac_missing|device_id_missing|device_id_mismatch|app_key_invalid|app_key_malformed`)
- **403** — kiosk pasif/onaysız veya eczaneye bağlı değil (`code`: `kiosk_inactive|kiosk_unlinked`)
- Başka auth turleri operasyonel endpoint'lerde **reddedilir**. URL'de kiosk ID **yoktur**; kiosk `request.kiosk` (auth context) üzerinden belirlenir.

| Method | Path | Amaç |
|--------|------|------|
| GET  | `/api/kiosk/v1/ping/` | Heartbeat + bugünkü playlist versiyonu |
| GET  | `/api/kiosk/v1/sync/` | Aktif creative + idle içerik (`idle_contents`) + lookup |
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
- Response: `[{ "id": "uuid", "name": "...", "start_date": "...", "end_date": "...", "status": "ACTIVE", "priority": 50, "target_scope": "ALL", "creatives": [...], "targets": [...] }, ...]`
- **Faz 7:** is_guaranteed, impression_goal, frequency_cap_per_hour, target_pharmacies response'da YOK

**POST /api/campaigns/v2/campaigns/**
- Auth: JWT (SuperAdmin)
- Request: `{ "name": "Kampanya 1", "advertiser_name": "XYZ", "start_date": "...", "end_date": "...", "priority": 50, "target_scope": "ALL" }`
- **Faz 7:** is_guaranteed/impression_goal/frequency_cap_per_hour gonderilenince 400 donar (deprecated)
- Response: `{ "id": "uuid", ... }`

**POST /api/campaigns/upload-media/** *(Faz 0.5 guncellendi)*
- Auth: JWT (SuperAdmin)
- Request: multipart/form-data, field: `file`
- Feature flag: `DOOH_PERSISTENT_MEDIA_URL` (settings)
- Response (flag=True): `{ "object_key": "ads/uuid.mp4", "media_url": "https://files.eisa.com.tr/eisa-files/ads/uuid.mp4", "checksum": "sha256:...", "url": "(alias=media_url)", "filename": "...", "object_name": "(alias=object_key)" }`
- Response (flag=False, legacy): `{ "url": "https://...?X-Amz-Signature=...", "filename": "...", "object_name": "ads/uuid.mp4" }`
- URL format (production, S3_FORCE_PATH_STYLE=True): `https://<S3_ENDPOINT>/<S3_BUCKET>/<object_key>`

**POST /api/campaigns/v2/creatives/**
- Auth: JWT (SuperAdmin)
- Request: `{ "campaign_id": "uuid", "media_url": "...", "duration_seconds": 15, "name": "Creative 1" }`
- Response: `{ "id": "uuid", ... }`

**GET/POST/PUT/PATCH/DELETE /api/campaigns/v2/idle-contents/** *(2026-08-16)*
- Auth: JWT (SuperAdmin); router basename `dooh-idle-content`
- "İçerik Yönetimi" idle (bekleme) başlık/metin CRUD; eski `/api/campaigns/v2/house-ads/` KALDIRILDI
- Serializer alanları: `id, baslik, metin, aktif, created_at, updated_at`
- Request (POST): `{ "baslik": "...", "metin": "...", "aktif": true }`

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

### Faz 3 — Simulation / Activation Endpoints *(2026-07-22)*

**POST /api/campaigns/v2/campaigns/{id}/simulate/**
- Auth: JWT (SuperAdmin)
- DOOH_ENGINE_V2: `shadow` veya `active` gerektirir. `off` ise 403.
- Request: body yok (campaign id URL'de)
- Response 200:
  ```json
  {
    "campaign_id": "uuid",
    "fingerprint": "hex16",
    "target_kiosks": [1, 2],
    "date_range": ["2026-07-22", "2026-07-25"],
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
  ```
- Response 403: `DOOH_ENGINE_V2=off`
- Response 404: campaign bulunamadı
- **Read-only**: hiçbir tabloya yazma yapmaz (Playlist, PlaylistItem, GenerationJob, KioskDayQuota, CampaignTotalAllocation, PlanningRun değişmez)
- **Deterministic**: aynı input, aynı campaign durumunda aynı fingerprint ve aynı kiosk_days üretir
- **Serializer**: `SimulationResultSerializer` (apps/campaigns/serializers.py)

**POST /api/campaigns/v2/campaigns/{id}/activate/**
- Auth: JWT (SuperAdmin)
- Faz 7+: Feature flag yok, endpoint her zaman açık.
- Request: body yok
- Response 200:
  ```json
  {
    "campaign_id": "uuid",
    "planning_run_id": null,
    "activated_kiosks": 2,
    "activated_dates": 3,
    "total_placements": 0,
    "fingerprint": "hex16",
    "is_complete": true,
    "blocking_reasons": []
  }
  ```
- Response 400: `ActivationValidationError`
  ```json
  { "error": "...", "validation_errors": { "delivery_rule": "...", "creatives": "..." } }
  ```
- Response 404: campaign bulunamadı
- Response 409: `CapacityError` (GUARANTEED kapasite yetersiz)
  ```json
  { "error": "...", "blocking_reasons": ["kiosk=1 date=2026-07-22: ..."] }
  ```
- **Çalışma akışı (2026-08):**
  - Endpoint artık kampanya tarih aralığının tamamı için senkron playlist üretmez.
  - `activate` yalnız doğrulama + (GUARANTEED ise) rolling horizon kapasite kontrolü yapar.
  - Ağır üretim `GenerationJob` kuyruğuna bırakılır (`triggered_by=campaign_activate`).
  - Üretim kapsamı yalnız rolling horizon'dur (varsayılan: bugün + 2 gün).
- **Dedupe/coalesce:** Aynı kiosk+tarih için mevcut `dedupe_key=kd:{kiosk_id}:{date}` mekanizması duplicate `PENDING` job üretimini engeller.
- **GUARANTEED all-or-nothing:** GUARANTEED pre-check başarısızsa 409 döner, `campaign_activate` job enqueue edilmez; kısmi publish başlamaz.
- **Serializer**: `ActivationResultSerializer` (apps/campaigns/serializers.py)

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
    "idle_contents": [{ "id": 1, "baslik": "...", "metin": "...", "aktif": true, "updated_at": "..." }]
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
- Request (her log'da creative_id; house_ad_id kabul edilir ama yok sayılır):
  ```json
  {
    "logs": [
      {
        "creative_id": "uuid",
        "played_at": "2026-06-05T10:30:00.000Z",
        "duration_played": 15
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

5. **PlayLog creative-only:**
   - Backend: yalnız `creative_id` FK (nullable); `house_ad_id` FK kaldırıldı (migration 0027)
   - Kiosk UI yalnız `creative_id` gönderir; playlist creative-only, house_ad_id payload'da gelse de yok sayılır

---

**Satır sayısı: ~250**
