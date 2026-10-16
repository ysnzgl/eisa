# Web Panels — Vue 3 + Vite + Pinia + Tailwind CSS

**Amaç:** Admin ve Pharmacist panelleri; kampanya/playlist/fiyat/kullanıcı/cihaz yönetimi, QR tarama, session raporları.

---

## When To Read This File

- Frontend UI değişiklikleri için
- Yeni admin paneli sayfası eklerken
- QR tarama akışı problemlerinde
- Dashboard/analytics değişikliklerinde
- Auth/RBAC sorunlarında

---

## Important Source Files

- `web_panels/src/router/index.js` — Route tanımları, RBAC guard
- `web_panels/src/stores/auth.js` — Auth state management
- `web_panels/src/services/api.js` — Backend API client
- `web_panels/src/services/dooh.js` — DOOH sponsorluk/creative/playlist API client (sponsorship-kiosks: preview/copy/simulate, assign-kiosks, kiosk-health)
- `web_panels/src/services/lookups.js` — İl/İlçe lookup (getIller/getIlceler)
- `web_panels/src/views/admin/KioskSponsorship.vue` — Kiosk Sponsorluk yönetimi (route `/admin/kiosk-sponsorships`)
- `web_panels/src/views/admin/SponsorshipDefinitions.vue` — Sponsorluk Tanımları (route `/admin/campaigns`; Bilgiler → Medya → Kiosklar)
- `web_panels/src/composables/useSponsorship.js` — Sponsorluk panel composable (preview/simulate/copy state)
- `web_panels/src/views/admin/DoohControlCenter.vue` — DOOH izleme merkezi
- `web_panels/src/views/admin/ContentManagement.vue` — "İçerik Yönetimi" (route `/admin/content-management`): IdleScreenContent CRUD; başlık/metin idle içerik (2026-08-16). **TR/EN:** Başlık (İngilizce)/Metin (İngilizce) opsiyonel alanları *(2026-09-29)* — boş bırakılırsa kioskta İngilizce dilde Türkçe metin gösterilir. Eski `HouseAdManagement.vue` (`/admin/house-ads`) KALDIRILDI.
- `web_panels/src/views/admin/GorevYonetimi.vue` — Admin-only İş Takibi (route `/admin/is-takip`); başlık/içerik/durum/atanan admin, İptal durumu, onaylı kalıcı silme, ortak KPI kartları ve shared field styles ile kompakt modal
- `web_panels/src/composables/useKioskRolloutStatus.js` — Kiosk rollout durum hesabı (tek merkezi kaynak)
- `web_panels/src/views/pharmacist/QrScan.vue` — QR tarama
- `web_panels/src/views/admin/Dashboard.vue` — Admin dashboard
- `web_panels/public/config.js` — Runtime config

---

## Panel Projesinin Amacı

**Kullanıcı tipleri:**
- **SuperAdmin:** Tüm sistem yönetimi (sponsorluklar, kullanıcılar, cihazlar, kategori/soru mantığı)
- **Pharmacist (Eczacı):** Kendi eczanesine ait dashboard, QR tarama, inbox

**Ana işlevler:**
1. Sponsorluk tanımı ve medya yönetimi (SponsorshipDefinitions — Bilgiler/Medya/Kiosklar)
2. Kiosk sponsorluk atama/yayın takvimi/simülasyon/kopyalama (KioskSponsorship)
3. DOOH kontrol merkezi (DoohControlCenter — sponsorluk/job/kiosk izleme)
4. Kategori/Soru/Etken Madde/Danışma yönetimi (MedicalLogic, DanismaYonetimi)
5. Eczane/Kiosk cihaz yönetimi (DeviceManagement)
   - Kiosk izleme: MAC adresi, Uygulama Anahtarı, durum, son ping, build numarası
   - Kiosk düzenleme: Ad, MAC adresi, Aktif/Pasif durumu güncellenebilir
   - Uygulama Anahtarı: Salt okunur (backend tarafından otomatik üretilir)
   - Kopyalama özelliği: Uygulama Anahtarı yanında kopyala butonu (clipboard API, toast notification)
6. **Onay Bekleyen Cihazlar (PendingDevices — 2026-07-14):** Fleet key + HMAC doğrulamasından geçmiş henüz kayıtlı olmayan kiosk cihazlarının yönetimi
   - Cihaz listesi: MAC, hostname, durum badge, ilk/son görülme, başvuru sayısı
   - Detay modal: yapılandırılmış cihaz bilgileri (hostname, OS, CPU, RAM, IP listesi, Node sürümü, uptime); token/secret gösterilmez
   - Onay modal: `EisaLookup` autocomplete ile eczane arama (ad, il, ilçe) + kiosk adı → tek transaction ile Kiosk kaydı oluşturulur
   - Red modal: opsiyonel red nedeni
   - Route: `/admin/devices/pending` (SuperAdmin RBAC korumalı)
7. **Dashboard pending alert (2026-07-14):** `pendingCount > 0` olduğunda sayfa başında sarı uyarı banner'ı; `/admin/devices/pending`'e doğrudan link
6. Kullanıcı yönetimi (UserManagement)
7. QR kodu tarama ve session detayı (QrScan)
8. Dashboard analytics (kampanya performansı, session özeti)
9. **Barkod Logo Yönetimi** *(2026-08-11)* — `/admin/barkod-logolar`, `BarkodLogoYonetimi.vue`. DOOH'dan bağımsız. Logo oluştur/düzenle/pasifleştir; PNG yükle (336×336, ≤1MB); kiosk hedefleme; günlük limit. DELETE yok.
10. **Görüş ve Destek** *(2026-08-15)* — Admin: `/admin/destek` → `DestekYonetimi.vue`; Eczacı: `/pharmacist/destek` → `DestekTalepleri.vue`. Admin menüsünde Yeni sayısı badge'i.
11. **İş Takibi** *(2026-09-13, updated 2026-10-03)* — Admin-only `/admin/is-takip` → `GorevYonetimi.vue`. Ana dashboard KPI diline uyumlu `eisa-stats` kartları kullanır; içerik alanında karakter sınırı yoktur. Geniş, yeniden boyutlandırılabilir editör paragrafları/satır sonlarını korur ve canlı karakter sayısı gösterir; liste görünümü kısa önizleme kullanır. İşler `İptal` durumuna alınabilir veya onay diyaloğundan sonra kalıcı olarak silinebilir.
12. **Abonelik ve Ödeme** *(2026-10-01)* — Admin: `/admin/abonelik` → `AbonelikYonetimi.vue` (Sözleşmeler + **Talepler** (onay/red) + **Ödemeler** (tarihçe) + Faturalar sekmeleri; Uzat/Geçmiş; `?eczane=` filtresi; bekleyen talep badge). Eczacı: `/pharmacist/hesabim` → `HesabimOdemeler.vue` (borç/sözleşme özeti, fatura ödeme, **sözleşme talebi** yeni/uzatma/iptal, ödeme geçmişi, sözleşme hareketleri, bitiş≤7g/ödeme≤3g ısrarlı uyarılar). **Kısıtlı panel:** sözleşmesiz/ödemesi gecikmiş eczacı giriş yapar ama yalnız Hesabım'ı görür (AdminLayout nav filtresi + router guard `auth.panelKisitli`). Demo'da sol menüde **DEMO** rozeti. Ortak `components/shared/SozlesmeForm.vue`.
13. **Eczane + sözleşme (DeviceManagement)** *(2026-10-01)* — "Yeni Eczane" modalında zorunlu sözleşme bölümü (`SozlesmeForm`); tek istekte `POST /api/pharmacies/` nested `sozlesme` ile atomik oluşur. Eczane tablosunda **Sözleşme** (tür·kalan gün) ve **Ödeme** (Güncel/Bekleyen/Gecikmiş/Demo/Sözleşme yok) renkli `eisa-pill` rozetleri + satır başı "Sözleşmeler" butonu (`/admin/abonelik?eczane=`).

---

## Ana Sayfa / Component / Module Yapısı

### Router (`src/router/index.js`)

**Public:**
- `/` → Redirect to `/login`
- `/login` → `Login.vue`

**SuperAdmin routes (`/admin/*`):**
- `/admin` → `Dashboard.vue`
- `/admin/devices` → `DeviceManagement.vue` (Eczane/Kiosk CRUD)
- `/admin/devices/pending` → `PendingDevices.vue` (Onay Bekleyen Cihazlar — 2026-07-14)
- `/admin/medical-logic` → `MedicalLogic.vue` (Kategori/Soru/EtkenMadde CRUD; **TR/EN:** Kategori Adı (İngilizce) + Soru Metni (İngilizce) opsiyonel alanları — 2026-09-29)
- `/admin/danisma` → `DanismaYonetimi.vue` (Danışma kategorileri CRUD; **TR/EN:** Kategori Adı (İngilizce) opsiyonel alanı — 2026-09-29)
- `/admin/campaigns` → `SponsorshipDefinitions.vue` (Sponsorluk Tanımları — Bilgiler/Medya/Kiosklar; Medya adımında iki medya alanı hem image hem video: Bekleme/İşlem ekranı)
- `/admin/kiosk-sponsorships` → `KioskSponsorship.vue` (Kiosk Sponsorluk — kiosk listesi + Sponsorluklar/Yayın Takvimi/Simülasyon/Kopyala sekmeleri)
- `/admin/kiosk-activities` → `KioskActivities.vue` (Kiosk Hareketleri: QR/Oturum, Kampanya Gösterimleri, Kiosk Olayları, **Yayın Akışı** — 2026-08-09)
- `/admin/pharmacy-campaigns` → `PharmacyCampaigns.vue` *(2026-07-31)* (Eczacı Paneli Kampanyaları — bağımsız CRUD)
- `/admin/dooh/control-center` → `DoohControlCenter.vue` (DOOH izleme — sponsorluk/job/kiosk)
- `/admin/users` → `UserManagement.vue` (Kullanıcı CRUD)
- `/admin/destek` → `DestekYonetimi.vue` *(2026-08-15)* (Görüş ve Destek Yönetimi)
- `/admin/is-takip` → `GorevYonetimi.vue` *(2026-09-13)* (Admin-only iş takibi; başlık/içerik/durum/atanan admin)
- `/admin/abonelik` → `AbonelikYonetimi.vue` *(2026-10-01)* (Sözleşme/cihaz planı/fatura yönetimi; AdminLayout nav "Abonelik ve Ödeme")

**Pharmacist routes (`/pharmacist/*`):**
- `/pharmacist` → `Dashboard.vue`
- `/pharmacist/inbox` → `Inbox.vue` (Eczane session'ları listesi)
- `/pharmacist/qr` → `QrScan.vue` (QR tarama)
- `/pharmacist/hesabim` → `HesabimOdemeler.vue` *(2026-10-01)* (Hesabım ve Ödemeler; sözleşme özeti + fatura ödeme)
- `/pharmacist/destek` → `DestekTalepleri.vue` *(2026-08-15)* (Görüş ve Destek)
- *(Layout seviyesinde)* `PharmacistCampaignDisplay.vue` *(2026-07-31, 2026-08-01 doğrulandı)* — alt şerit + 90s idle overlay; AdminLayout'ta `v-if="isPharmacist"` ile mount edilir; route geçişinde yeniden başlamaz. Eczane eczacı kullanıcının `request.user.eczane_id`'si üzerinden il/ilçe/eczane OR eşleşmesiyle belirlenir.

**EisaLookup Entegrasyon Notu:** `EisaLookup.vue` `options: [{id, label, sub?}]` ve `v-model` ile çalışır; `endpoint` veya `@select` prop'ları YOKTUR. Eczaneler `GET /api/pharmacies/` (list), iller `GET /api/lookups/iller/`, ilçeler `GET /api/lookups/ilceler/?il={id}` ile yüklenir ve `options` formatına dönüştürülür.

**RBAC guard:** `router.beforeEach` — `useAuthStore().role` kontrolü

---

### Store Yapısı (`src/stores/`)

- `auth.js` (`useAuthStore`): Kullanıcı login/logout, role/pharmacyId/userId state (localStorage sync)
- (Diğer store'lar component-level state veya API çağrıları için kullanılıyor olabilir, merkezi store kısıtlı)

---

### Component Yapısı (`src/components/`)

Tüm componentler tek dosyalı Vue 3 Composition API (`.vue` dosyaları). Liste:
- Form componentleri (input/select/button wrapper'ları)
- Modal/Dialog componentleri
- Table/List componentleri (kampanya listesi, kiosk listesi, vb.)

(Detaylı component listesi gerekirse `src/components/` klasörü taranabilir; şimdilik top-level view'ler yeterli)

---

### Services (`src/services/`)

- `api.js`: Axios instance + API method'ları
  - **Auth:** `login(username, password)`, `logout()`, `refreshToken()`
  - **Lookups:** `getProvinces()`, `getDistricts(provinceId)`, `getGenders()`, `getAgeRanges()`
  - **Pharmacies:** `listPharmacies()`, `createPharmacy(data)`, `updatePharmacy(id, data)`, `deletePharmacy(id)`, `listKiosks()`, `createKiosk(data)`, `updateKiosk(id, data)`, `deleteKiosk(id)`, `getSessionsByQr(qr)`
  - **Products:** `listCategories()`, `createCategory(data)`, `listQuestions(categoryId)`, `createQuestion(data)`, `listDanisma()`, `createDanisma(data)`
  - **Sponsorluk (`services/dooh.js`):** `listCampaignsV2()`, `getCampaignV2(id)`, `createCampaignV2(data)`, `updateCampaignV2(id, data)`, `deleteCampaignV2(id)`, `bulkActionCampaignsV2(action, ids)`, `getCampaignKiosks(id)`, `assignKiosksToCampaign(id, body)`, `createCreative(data)`/`updateCreative`/`deleteCreative`, `uploadMedia(file, kind)`
  - **Kiosk sponsorluk (`services/dooh.js`):** `listSponsorshipKiosks(params)`, `getKioskSponsorships(kioskId)`, `putKioskSponsorships(kioskId, items)`, `previewKioskSponsorships(kioskId, body)`, `copyKioskSponsorships(kioskId, body)`, `simulateKioskSponsorship(kioskId, body)`, `getKioskDayStream(kioskId, date)`
  - **Idle içerik (İçerik Yönetimi, 2026-08-16):** `listIdleContents()`, `createIdleContent(data)`, `updateIdleContent(id, data)`, `deleteIdleContent(id)` — eski `listHouseAds/createHouseAd/updateHouseAd/deleteHouseAd/downloadHouseAdMedia` KALDIRILDI
  - **Playlist üretim/izleme:** `generatePlaylists(payload)`, `forceRegenerateKiosk(kioskId, date)`, `listGenerationJobs()`, `getGenerationJob(id)`, `getKioskHealth()`
  - **Analytics:** `getSessionLogs(filters)`, `getPlayLogs(filters)`, `getCampaignStats(campaignId)`
  - **Abonelik (2026-10-01, `services/abonelik.js`):** admin `listSozlesmeler/createSozlesme/updateSozlesme/setCihazPlani/uzatSozlesme/getSozlesmeGecmis/listTalepler/kararVerTalep/bekleyenTalepSayisi/listOdemeler`; eczacı `getHesabim/getFaturalarim/odeFatura/getOdemelerim/getHareketlerim/getTaleplerim/createTalep`. Eczane oluşturma `createPharmacy` gövdesine nested `sozlesme` ekler. `stores/auth.js` `panelKisitli`/`demo` durumu + `setBilling()`; router guard kısıtlı eczacıyı Hesabım'a yönlendirir.

**Axios config:**
- `baseURL`: `window.EISA_API_BASE_URL` (runtime config, `/config.js`)
- `withCredentials: true` (httpOnly çerez)
- Interceptor: 401 → refresh token → retry request

---

## Backend ile Konuştuğu API'ler

Tüm API çağrıları `axios` üzerinden `/api/*` endpoint'lerine yapılır.

**Auth API:**
- `POST /api/auth/token/` → Login (username/password) → httpOnly çerez set edilir
- `POST /api/auth/token/refresh/` → Token yenileme
- `POST /api/auth/logout/` → Çerez temizleme

**Lookups API:**
- `GET /api/lookups/iller/`
- `GET /api/lookups/ilceler/?il={id}`
- `GET /api/lookups/cinsiyetler/`
- `GET /api/lookups/yas-araliklari/`

**Pharmacies API:**
- `GET /api/pharmacies/eczaneler/`
- `POST /api/pharmacies/eczaneler/`
- `GET /api/pharmacies/eczaneler/{id}/`
- `PUT /api/pharmacies/eczaneler/{id}/`
- `DELETE /api/pharmacies/eczaneler/{id}/`
- `GET /api/pharmacies/kiosklar/`
- `POST /api/pharmacies/kiosklar/`
- `PATCH /api/pharmacies/kiosklar/{id}/` → Kiosk güncelleme (ad, mac, aktif)
- `PUT /api/pharmacies/kiosklar/{id}/`
- `DELETE /api/pharmacies/kiosklar/{id}/`
- `GET /api/analytics/sessions/?qr_kodu={qr_kodu}` → QR ile session detayı

**Products API:**
- `GET /api/products/kategoriler/`
- `POST /api/products/kategoriler/`
- `GET /api/products/sorular/?kategori={id}`
- `POST /api/products/sorular/`
- `GET /api/products/danisma-kategorileri/`
- `POST /api/products/danisma-kategorileri/`

**Sponsorluk API:**
- `GET /api/campaigns/v2/campaigns/`
- `POST /api/campaigns/v2/campaigns/`
- `PUT /api/campaigns/v2/campaigns/{id}/`
- `DELETE /api/campaigns/v2/campaigns/{id}/`
- `POST /api/campaigns/v2/campaigns/bulk-action/` (pause/resume/delete toplu işlem)
- `GET /api/campaigns/v2/campaigns/{id}/kiosks/` → sponsorluğun atandığı kiosklar
- `POST /api/campaigns/v2/campaigns/{id}/assign-kiosks/` → çoklu kioska atama (dry_run opsiyonu)
- `POST /api/campaigns/upload-media/` (file upload, multipart/form-data)
- `POST /api/campaigns/v2/creatives/`
- `GET /api/campaigns/v2/idle-contents/`
- `POST /api/campaigns/v2/idle-contents/`

**Kiosk sponsorluk API:**
- `GET /api/campaigns/v2/sponsorship-kiosks/?search=&unassigned=1` → kiosk listesi + atama sayıları
- `GET/PUT /api/campaigns/v2/sponsorship-kiosks/{kiosk_id}/sponsorships/` → kioskun atamaları (PUT tam değiştirme)
- `POST /api/campaigns/v2/sponsorship-kiosks/{kiosk_id}/preview/` → gün planı önizleme (DB yazmaz)
- `POST /api/campaigns/v2/sponsorship-kiosks/{kiosk_id}/copy/` → başka kiosklara kopyala (üzerine yazar; dry_run)
- `POST /api/campaigns/v2/sponsorship-kiosks/{kiosk_id}/simulate/` → probe + senaryo simülasyonu

**Playlist API:**
- `POST /api/campaigns/v2/playlists/generate/` → Async playlist generation job başlatma
- `GET /api/campaigns/v2/playlists/jobs/` → Job listesi
- `GET /api/campaigns/v2/playlists/jobs/{job_id}/` → Job durumu
- `GET /api/campaigns/v2/playlists/day-stream/?kiosk=&date=` → yayındaki gerçek akış (read-only)

**Analytics API:**
- `GET /api/analytics/oturum-loglari/?kiosk={id}&start_date={date}&end_date={date}`
- `GET /api/analytics/play-logs/?campaign={id}&kiosk={id}&start_date={date}`

---

## Yetki / Auth / Config Yapısı

### Authentication

**Login akışı:**
1. Kullanıcı → `/login` → `username` + `password` girer
2. `Login.vue` → `api.login(username, password)` çağrısı
3. Backend → `POST /api/auth/token/` → JWT httpOnly çerez set edilir
4. Backend → response: `{ role, pharmacyId, userId }`
5. Frontend → `useAuthStore().login()` → localStorage'a `eisa_role`, `eisa_pharmacy_id`, `eisa_user_id` yazılır
6. Router → role'e göre `/admin` veya `/pharmacist` redirect

**Logout akışı:**
1. Kullanıcı → logout butonu
2. `useAuthStore().logout()` → `api.logout()` çağrısı
3. Backend → `/api/auth/logout/` → çerez temizlenir
4. Frontend → localStorage temizlenir, `/login` redirect

**Token refresh:**
- Axios interceptor → 401 hatası → `api.refreshToken()` → retry request
- Eğer refresh başarısız → `/login` redirect

### Authorization

**RBAC:**
- `router.beforeEach` guard: `to.meta.roles` kontrolü
- `useAuthStore().role` → `superadmin` veya `pharmacist`
- Eğer role uyumsuz → `/login` redirect

**Pharmacist kısıtlamaları:**
- Sadece kendi eczanesine ait verileri görür (backend tarafında `request.user.eczane` kontrolü)
- Campaign/Playlist/Pricing/User Management sayfalarına erişemez

### Config

**Runtime config (`public/config.js`):**
```js
window.EISA_API_BASE_URL = 'http://localhost:8000';
```
- Prod deployment'ta nginx tarafından override edilebilir (config.js dosyası dinamik oluşturulur)

### Loglama (2026-07-16)

- `src/lib/logger.js`: Prod'da INFO/DEBUG bastırılır; sadece WARNING/ERROR/CRITICAL işlenir.
- `main.js` içinde `installGlobalHandlers(app)` ile `app.config.errorHandler` + `window.onerror` + `unhandledrejection` yakalanır.
- Axios interceptor response'daki `X-Correlation-ID` başlığını `window.__EISA_LAST_CORRELATION_ID__` üzerinde tutar.
- Kritik hatalar `POST /api/analytics/client-events/` ile backend'e gönderilir (allow-list: level/event/message/stack/component/route/correlation_id/occurred_at).
- Kullanıcı verisi, form içeriği, query string DEĞERLERİ gönderilmez. Sonsuz döngü koruması: kendi bildirim hatası tekrar loglanmaz.
- Detay: [docs/operations/logging.md](../operations/logging.md).

---

## Kritik UI Akışları

### 1. Sponsorluk Tanımları (SponsorshipDefinitions.vue)

**Route:** `/admin/campaigns` (SuperAdmin)
**Yapı:** Sponsorluk listesi + sekmeli modal (3 sekme).

| Sekme | Açıklama |
|-------|----------|
| Bilgiler | `name`, `advertiser_name` (serbest metin), `start_date`, `end_date`, `status` (ACTIVE/PAUSED/COMPLETED) |
| Medya | Creative upload (görsel/video); iki alan: Bekleme ekranı (`media_url`, portrait) + İşlem ekranı (`active_media_url`), `duration_seconds` (1–60; grid {15,30,45,60}) |
| Kiosklar | Atanmış kiosklar (`getCampaignKiosks`) + "Kiosklara Ata" (`assignKiosksToCampaign`) |

- İl/ilçe/eczane hedefleme, frekans matrisi, öncelik/garanti, simülasyon/aktivasyon adımları **YOK** (2026-10-16 yeniden tasarım).
- Creative upload: `POST /api/campaigns/upload-media/` → `{ media_url, object_key, checksum, url[alias] }` (`media_url ?? url` fallback) → `POST /api/campaigns/v2/creatives/`.
- "Kiosklara Ata": tek pencere (`window_start`/`window_end`) + `count` + `active_weekdays` ile çoklu kioska atar; zaten atanmış kiosklar atlanır; kapasite aşarsa 400 `capacity_exceeded` (hiçbir şey kaydedilmez); `dry_run` ön kontrol.
- Silme: tekil `deleteCampaignV2(id)`; toplu `bulkActionCampaignsV2('delete'|'pause'|'resume', ids)`.

### 1b. Kiosk Sponsorluk (KioskSponsorship.vue)

**Route:** `/admin/kiosk-sponsorships` (SuperAdmin). Composable: `composables/useSponsorship.js`.
**Yapı:** Solda aranabilir kiosk listesi (çevrimiçi durumu, sponsorluk sayısı, "Atanmamış" filtresi); sağda seçili kiosk için 4 sekme.

| Sekme | Açıklama |
|-------|----------|
| Sponsorluklar | Düzenlenebilir atama tablosu (sponsorluk, pencere başlangıç/bitiş, `count`, aktif günler, tarih, aktif); canlı kapasite önizlemesi (requested vs placed, debounce). `PUT .../sponsorships/` tam değiştirme (set). |
| Yayın Takvimi | Taslak/yayında günlük plan: 24 saat ısı haritası → dakika/saniye şeridi + görsel önizleme (`POST .../preview/`, DB yazmaz). |
| Simülasyon | `probe` (bir pencere + süre için en fazla kaç gösterim sığar) ve `scenario` (varsayımsal satırların uygulanabilirliği) — `POST .../simulate/`. |
| Kopyala | Kaynak kioskun takvimini hedef kiosklara kopyalar — **üzerine yazar**; `dry_run` ile removed/added/kept farkı önizlenir (`POST .../copy/`). |

- Kapasite hatası şekli: `400 {code:'capacity_exceeded', detail, conflicts:[{date, campaign_id, campaign_name, requested, placed}]}` → `extractCapacityError` ile gösterilir.
- Yardımcılar (useSponsorship): `hhmmToMinutes`, `secondToHHMMSS`, `maxCountHint`, `validateRow`, `rowToPayload`, `heatmapColor`, `hourTimeline`, `diffCampaignNames`, `extractCapacityError`.

**Route:** `/admin/dooh/control-center` (SuperAdmin — `/admin/*` meta: `roles: ['superadmin']`)

**Bölümler:**

1. **Özet kartlar:** Aktif kampanya, Bekleyen/Başarısız job, Geride kiosk sayıları
2. **Sponsorluk listesi:** Status badge + pause/resume/delete (EisaDeleteConfirm ile)
3. **Playlist üretim işleri:** job listesi, polling (yalnız PENDING/RUNNING), `onUnmounted` cleanup
4. **Kiosk dağıtım durumu:** desired/applied/horizon tablosu, rollout durum badge'i

**Polling lifecycle:**
- `hasActiveJobs` true → `setInterval(8000)` başlar
- `hasActiveJobs` false → `clearInterval` (terminal durum = DONE/FAILED/RETRY)
- `onUnmounted(() => stopPolling())` — timer temizlenir
- `if (_pollInterval) return` — birden fazla timer oluşmaz

**Kiosk Rollout Durumu (`calcKioskRolloutStatus`):**
- Tek merkezi kaynak: `composables/useKioskRolloutStatus.js`
- `applied null` → `ack_pending` ("ACK Bekleniyor") — hata değil
- `applied < desired` → `behind` ("Geride")
- `applied == desired` ama `applied_horizon_end < serverHorizonEnd` → `horizon_stale` ("Horizon Eksik")
- `applied == desired` ve horizon yeterli → `up_to_date` ("Güncel")
- Europe/Istanbul gün: `Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Istanbul' })` — browser timezone'una kör biçimde güvenilmez
- `serverHorizonEnd` backend'den alınır (şu an `null` — horizon kontrolü atlanır)

**Status mapping:**
- `STATUS_MAP` (sponsorluk): ACTIVE/PAUSED/COMPLETED (+ eski DRAFT/CANCELLED fallback etiketleri) → label + CSS class
- `JOB_STATUS_MAP` (job): PENDING/RUNNING/DONE/FAILED/RETRY; `COMPLETED` → `DONE` (backward compat)
- `ROLLOUT_ACCENT_MAP` (kiosk): up_to_date/behind/ack_pending/horizon_stale/offline/no_publish/unknown
- Üç map tek dosyada (DoohControlCenter.vue) — kopya yok

**ControlCenter salt izleme yapar:**
- Applied version değiştirmez
- ACK üretmez
- Otomatik publish tetiklemez

### 3. Playlist Üretim / İzleme *(2026-10-16)*

`PlaylistEditor.vue` (Gelişmiş Manuel Yayın) ve `PricingMatrixConfigurator.vue` (Fiyat Matrisi) **kaldırıldı**; `/admin/playlists` ve `/admin/pricing` route'ları yoktur. Playlist üretimi artık sponsorluk atamalarından otomatik türetilir (`sponsorship_engine`). Manuel üretim/izleme `DoohControlCenter.vue` ve `KioskSponsorship.vue` üzerinden yapılır:
- `generatePlaylists(payload)` → `POST /api/campaigns/v2/playlists/generate/` (seçili kiosk + tarih için async job)
- `forceRegenerateKiosk(kioskId, date)` → zorla yeniden üretim
- `listGenerationJobs()` / `getGenerationJob(id)` → kuyruk izleme (polling yalnız PENDING/RUNNING; `onUnmounted` cleanup)
- `getKioskDayStream(kioskId, date)` → yayındaki gerçek akış (read-only)

### 4. QR Tarama (QrScan.vue)

1. Eczacı → `/pharmacist/qr`
2. Fiziksel barkod okuyucu (keyboard wedge) input'a 8 karakter QR yazar ve Enter gönderir.
3. Kamera akışı kaldırılmıştır (getUserMedia/video/BarcodeDetector yoktur).
4. `GET /api/analytics/sessions/?qr_kodu={qr_kodu}` çağrılır.
5. Backend 400/403/404 durumlarını ayrıştırır; UI bunu ayrı mesajlarla gösterir.
6. Başarılı response'da oturum detayları, soru-cevap çözümü ve etken madde detayları gösterilir. `source` alanına göre kiosk önerileri ile eczacının sonradan ekledikleri ayrı bölümlerde; eklenenler indigo bilgi stiliyle sunulur.
7. Detay yüklendikten sonra eczacı için `POST /api/analytics/sessions/{id}/mark-reviewed/` çağrılır; admin görüntülemesi mutation yapmaz.
8. Eczacı modalı sonuç girilene kadar çarpı/Kapat/Escape/backdrop ile kapanmaz. Açık kayıt kullanıcı+eczane anahtarlı `sessionStorage` ile yenilemede geri yüklenir; yeni QR fonksiyon seviyesinde engellenir.
9. `POST /api/analytics/sessions/{id}/complete/` zorunlu `sale_result` (`sold|not_sold`) ve opsiyonel `ingredient_ids` alır. Diğer etken maddeler yalnız aramalı mevcut katalogdan çoklu seçilir.

### 5. Dashboard Analytics (Dashboard.vue)

1. SuperAdmin/Pharmacist → `/admin` veya `/pharmacist`
2. Kartlar: Toplam session, tamamlanan session, toplam impression, aktif kampanya sayısı
3. Ortak `DashboardPeriodCharts`, bağımsız veri yükleyen dört `DashboardPeriodCard` bileşeninden oluşur: seçili ayın tüm günleri ile Pazartesi-Pazar haftanın tüm günlerini sıfır dolgulu gösterir. QR etkileşimleri Danışma sonucuna göre Bekleyen / Satış Yapılan / Satış Yapılmayan serileridir; etkileşim başlığında toplam rozeti bulunur. Satış grafikleri yalnız `SATIS_YAPILDI` oturumlarındaki Önerilen / Satılan etken madde çift serisini gösterir (`--eisa-turquoise` / `--eisa-red`). Admin masaüstünde başlığın altında İl ve Eczane picker'larından oluşan Analitik Filtresi bulunur: İl seçimi eczane listesini daraltır, boş filtre ise tüm veriyi gösterir. İlk satır dört KPI, ikinci satır ilk 10 kayıttan oluşan dört donut (kategori, satış eczanesi, satılan etken madde, önerilen etken madde) bulunur. Aylık analitik tam genişlikte üçüncü satırı kaplar; altında solda haftalık analitik, sağda dikey Son Eklenenler ve Sistem Durum panelleri yer alır. Her bar/donut kendi isteği, loading durumu ve giriş animasyonuyla çalışır. Dönem gezinmesi erişilebilir başlıklı FA ikonlarıyla yapılır; gelecek dönem kapalıdır. Haftalık başlık ve ikon navigasyonu tek satır kalır. Kategorisiz danışmanlık oturumları kategori donut'ına dahil edilmez.
   - Dört sabit başlık `Aylık Etkileşim`, `Aylık Satış`, `Haftalık Etkileşim`, `Haftalık Satış`tır. Etkileşim günü `tab=sessions`, satış günü `tab=sales` ile aynı gün başlangıç/bitiş filtresini Kiosk Hareketleri'ne taşır.
4. API çağrıları:
   - `GET /api/analytics/oturum-loglari/?start_date={date}&end_date={date}`
   - `GET /api/analytics/play-logs/?start_date={date}&end_date={date}`
5. **Eczane Kiosk Listesi:**
   - Eczane filtresi ile kiosk listesi görüntüleme
   - Kiosk bilgileri: Ad, MAC adresi, Uygulama Anahtarı, Durum, Son Görülme
   - Kiosk düzenleme: Ad, MAC adresi, Aktif/Pasif durumu güncellenebilir
   - Uygulama Anahtarı: Salt okunur (backend tarafından otomatik üretilir)
   - `PATCH /api/pharmacies/kiosks/{id}/` → Kiosk güncelleme
   - Eczane doğrudan PATCH edilemez. Her cihaz kartındaki metinli “Eczaneye Taşı” aksiyonu `Cihazı Başka Eczaneye Taşı` modalını açar; mevcut eczane salt okunur, hedef `EisaLookup` ile seçilir, neden ve taşıma özeti gösterilir. İşlem `POST .../{id}/transfer/` çağırır ve detayda atama geçmişini gösterir.

### DeviceManagement — cihaz zamanlayıcıları ve idle ses *(2026-09-11)*

Ses önizlemesi süreli S3 URL'si kullanmaz: yetkili backend proxy'si object key üzerinden dosyayı okur; portal blob URL üretir. Yayın Nginx CSP'sinde `media-src 'self' blob:` zorunludur. Eski blob URL oynatıcı DOM'dan kaldırıldıktan sonra serbest bırakılır; eski kaynağın gecikmiş hata olayları gösterilmez.

Düzenleme açılışında cihaz detay API'sinden güncel ayarlar alınır; ses süreleri yuvarlanmaz (tam dakika değilse Sn seçili gelir). Kütüphane Tümünü Seç / Seçimi Temizle sunar. Doğrulama hataları Güncelle yanında da görünür; kütüphane yüklemesi cihaz ayarlarını kaydetme butonunu kilitlemez.

Ses kütüphanesi kart satırları, seçili sayısı/sırası, Dinle düğmesi ve ayrı oynatıcıyla sunulur. Dosya seçimi ikonlu alan ve belirgin kırmızı Kütüphaneye Ekle düğmesi kullanır; stiller yalnız bu bileşene scoped uygulanır.
Her ses satırındaki çöp kutusu, ortak silme onayıyla sesi kütüphaneden ve tüm kiosk atamalarından kaldırır. Cihazlar sonraki sync'te güncellenir. Varlık pasifleştirilir; fiziksel dosya kurtarma için korunur.

- Mevcut `/admin/devices` kart ve düzenleme modalı aynı tasarım sistemi korunarak genişletildi; yeni sayfa/route eklenmedi.
- Kiosk bazında etkileşim sonrası idle'a dönüş, idle içerik min/max gösterim süresi, idle içerik yenileme süresi, ilk ses gecikmesi ve sonraki sesler arası süre düzenlenebilir. Her alan Sn/Dk seçicisi sunar; panel seçimi API/tabloda saniyeye dönüştürür. Defaultlar 20 sn, 10/12 sn, 300 sn, 20 dk ve 5 dk'dır.
- “Kütüphaneye Yükle” MP3/WAV/OGG dosyalarını bağımsız olarak kaydeder; otomatik kiosk ataması yapmaz. Kullanıcı kütüphaneden sesleri seçip Güncelle ile kioska bağlar. Dinle düğmesi yetkili preview endpoint'inden sesi alır; oynat/duraklat ve ilerleme kontrolleri portalda sunulur. Modal kapanınca önizleme temizlenir.
- Idle Ses bölümünde “Mesai içi (08:00–19:00)” veya “Mesai dışı / 24 saat” seçilir. “Nöbet günlerinde çal” seçeneği, eczacının girdiği nöbet gününde mesai içi sınırını kaldırır.
- Servis sözleşmesi: `PATCH /api/pharmacies/kiosks/{id}/`, `GET/POST .../idle-audio-library/` ve `POST .../{id}/set-idle-audios/`. Idle ses bölümündeki `Ses Süresi Görünür` seçeneği `idle_audio_countdown_visible` alanını yönetir; yalnız `true` iken kioskta geri sayım gösterilir.
- Kampanya yönetimi ve edge'in teknik pull/push/ping/diagnostic aralıkları bu ekrana dahil değildir.

### Ortak UI kuralları
- Global `vue-sonner` provider `top-center`, 22 px offset ve modal üstü z-index ile çalışır.
- `--eisa-turquoise: #0F8F8A` Evet/olumlu seçim rengidir; Hayır mevcut `--eisa-red` rengini kullanır.
- `.eisa-modal--big` yalnız Yeni Eczane oluşturma modalında (`95%`, en çok `1100px`) uygulanır.

---

## Duyuru ve Nöbet UI Akışı *(2026-08-18)*

**Kaynak dosyalar:**
- `src/views/admin/AnnouncementManagement.vue` — genel duyuru CRUD ve iki korumalı sistem duyurusunun sunum alanları
- `src/views/pharmacist/Announcements.vue` — eczanenin bugün geçerli genel duyuruları ve occurrence okundu aksiyonu
- `src/views/pharmacist/DutyCalendar.vue` — query string'deki `month=YYYY-MM` ayı için gün seçimi / “Bu Ay Nöbetim Yok”
- `src/components/pharmacist/DutyAlertModal.vue` — aktif okunmamış genel duyuru ve sistem nöbet uyarısı kuyruğu
- `src/views/admin/AdminLayout.vue` — eczacı rolünde popup'ın ortak mount noktası

**Route'lar:**
- `/admin/announcements` → `AnnouncementManagement.vue` (SuperAdmin)
- `/pharmacist/announcements` → `Announcements.vue` (Eczacı)
- `/pharmacist/duty?month=YYYY-MM` → `DutyCalendar.vue` (Eczacı)

**Admin davranışı:**
- Genel duyuru formu tek seferlik/günlük/haftalık/aylık tekrar, başlangıç/bitiş ve `ALL|PROVINCE|DISTRICT|PHARMACY` hedeflerini yönetir.
- Aylık UI belirli gün, gün aralığı, ilk N gün, son N gün ve son hafta (son 7 takvim günü) seçeneklerini sunar.
- Sistem kartında yalnız başlık, mesaj, aksiyon butonu metni, seviye ve aktiflik düzenlenir; koşul/tarih/hedef ay/aksiyon URL'si UI formuna açılmaz ve silme aksiyonu yoktur.
- Backend `system_key` alanını contract için döndürmeye devam eder; admin liste, detay ve düzenleme modalı bu teknik anahtarı hiçbir yerde göstermez, yalnız “Sistem Duyurusu” etiketi kullanır.

**Popup / provider doğrulaması:**
- Uygulamada ayrı bir global modal provider yoktur. `DutyAlertModal`, ortak `AdminLayout` içinde yalnız `isPharmacist` olduğunda render edilir; böylece giriş/yenileme sonrası tüm eczacı alt route'larını kapsar.
- Popup `/api/announcements/me/active/` sonucundaki genel ve sistem kayıtlarını tek tek, sırayla gösterir. Genel duyuru ancak açık “Okudum” isteği başarılı olunca kapanır; istek hatasında modal açık kalır.
- Sistem aksiyonları korunur: hedef ayla nöbet takvimini açma, hedef ayı `has_no_duty=true` kaydetme ve yalnız bugünkü occurrence'ı okundu işaretleme.

**Kullanılan API'ler:**
- `GET|POST /api/announcements/admin/`, `GET|PATCH|DELETE /api/announcements/admin/{id}/`
- `GET /api/announcements/me/active/?include_read=true|false`
- `POST /api/announcements/{id}/read/`
- `GET|PUT /api/announcements/duty/?month=YYYY-MM`

**Sınır:** Mevcut `/pharmacist/inbox` hassas session akışını göstermeye devam eder; genel duyurular analytics inbox state'ine veya local okundu setine bağlanmaz.

## Belirsiz / Riskli Noktalar

1. **Sponsorluk hedefleme (2026-10-16):** İl/ilçe/eczane hedefleme, frekans matrisi ve simülasyon/aktivasyon wizard adımları kaldırıldı; atama yalnız kiosk bazlı `KioskSponsorship` (SponsorshipDefinitions + KioskSponsorship ekranları).
2. **Medya akışı:** Upload response canonical: `{object_key, media_url, checksum, url[alias]}`. `media_url ?? url` fallback çalışıyor.
3. **Kapasite doğrulama:** Atama kaydı sırasında kapasite aşımı 400 `capacity_exceeded` ile reddedilir (hiçbir şey kaydedilmez); panel `conflicts` listesini gösterir.
4. **Playlist generation job polling (ÇÖZÜLDÜ):** DoohControlCenter polling yalnız PENDING/RUNNING durumunda çalışır; terminal durumda (DONE/FAILED) durur. `onUnmounted` ile timer temizlenir.
5. **İçerik Yönetimi (2026-08-16):** Sol menü + sayfa başlığı "İçerik Yönetimi" (route `/admin/content-management`) KORUNDU ama artık yeni `IdleScreenContent` CRUD'unu açar (`ContentManagement.vue`): Başlık/Metin/Durum/Son Güncelleme listesi, ekle/düzenle/aktif-pasif/onaylı silme, karakter sayacı 0/100 & 0/300, "Tanı, tedavi veya kesin sağlık sonucu ifade eden içerikler kullanmayın." notu, küçük 1080×1920 kiosk önizlemesi. Ayrı "HouseAd Yönetimi" ekranı (`/admin/house-ads`, `HouseAdManagement.vue`) ve `dooh.js` house-ad metotları KALDIRILDI.
6. **Kaldırılan ekranlar:** CampaignWizard.vue, PlaylistEditor.vue, PricingMatrixConfigurator.vue ve `/admin/playlists`, `/admin/pricing` route'ları artık yok.
7. **Token refresh interceptor:** Axios interceptor'da retry logic düzgün çalışıyor mu, sonsuz döngü riski? (Doğrulanmalı)

---

**Satır sayısı: ~210**
