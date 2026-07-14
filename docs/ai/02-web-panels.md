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
- `web_panels/src/views/admin/CampaignWizard.vue` — Kampanya yönetimi
- `web_panels/src/views/admin/PlaylistEditor.vue` — Playlist düzenleme
- `web_panels/src/views/pharmacist/QrScan.vue` — QR tarama
- `web_panels/src/views/admin/Dashboard.vue` — Admin dashboard
- `web_panels/public/config.js` — Runtime config

---

## Panel Projesinin Amacı

**Kullanıcı tipleri:**
- **SuperAdmin:** Tüm sistem yönetimi (kampanyalar, fiyatlandırma, kullanıcılar, cihazlar, kategori/soru mantığı)
- **Pharmacist (Eczacı):** Kendi eczanesine ait dashboard, QR tarama, inbox

**Ana işlevler:**
1. Kampanya oluşturma ve yönetimi (CampaignWizard)
2. Playlist şablon/manuel düzenleme (PlaylistEditor)
3. Fiyatlandırma matrisi konfigürasyonu (PricingMatrixConfigurator)
4. Kategori/Soru/Etken Madde/Danışma yönetimi (MedicalLogic, DanismaYonetimi)
5. Eczane/Kiosk cihaz yönetimi (DeviceManagement)
   - Kiosk izleme: MAC adresi, Uygulama Anahtarı, durum, son ping
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
- `/admin/medical-logic` → `MedicalLogic.vue` (Kategori/Soru/EtkenMadde CRUD)
- `/admin/danisma` → `DanismaYonetimi.vue` (Danışma kategorileri CRUD)
- `/admin/campaigns` → `CampaignWizard.vue` (Campaign/Creative/ScheduleRule yönetimi)
- `/admin/playlists` → `PlaylistEditor.vue` (Playlist şablon/manuel düzenleme)
- `/admin/pricing` → `PricingMatrixConfigurator.vue` (Fiyatlandırma matrisi)
- `/admin/users` → `UserManagement.vue` (Kullanıcı CRUD)

**Pharmacist routes (`/pharmacist/*`):**
- `/pharmacist` → `Dashboard.vue`
- `/pharmacist/inbox` → `Inbox.vue` (Eczane session'ları listesi)
- `/pharmacist/qr` → `QrScan.vue` (QR tarama)

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
  - **Campaigns:** `listCampaignsV2()`, `createCampaignV2(data)`, `updateCampaignV2(id, data)`, `deleteCampaignV2(id)`, `getCampaignRules(campaignId)`, `setCampaignRules(campaignId, data)`, `createCreative(data)`, `uploadMedia(file)`, `listHouseAds()`, `createHouseAd(data)`
  - **Playlists:** `listPlaylistTemplates()`, `createPlaylistTemplate(data)`, `listDayPlans(kioskId, date)`, `generatePlaylists(kioskId, dateRange)`
  - **Pricing:** `getPricingMatrix()`, `updatePricingMatrix(data)`
  - **Analytics:** `getSessionLogs(filters)`, `getPlayLogs(filters)`, `getCampaignStats(campaignId)`

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
- `GET /api/pharmacies/sessions/?qr={qr_kodu}` → QR ile session detayı

**Products API:**
- `GET /api/products/kategoriler/`
- `POST /api/products/kategoriler/`
- `GET /api/products/sorular/?kategori={id}`
- `POST /api/products/sorular/`
- `GET /api/products/danisma-kategorileri/`
- `POST /api/products/danisma-kategorileri/`

**Campaigns API:**
- `GET /api/campaigns/v2/campaigns/`
- `POST /api/campaigns/v2/campaigns/`
- `PUT /api/campaigns/v2/campaigns/{id}/`
- `DELETE /api/campaigns/v2/campaigns/{id}/`
- `POST /api/campaigns/v2/campaigns/bulk-action/` (pause/resume/delete toplu işlem)
- `GET /api/campaigns/v2/campaigns/{id}/rules/`
- `POST /api/campaigns/v2/campaigns/{id}/rules/`
- `POST /api/campaigns/upload-media/` (file upload, multipart/form-data)
- `POST /api/campaigns/v2/creatives/`
- `GET /api/campaigns/v2/house-ads/`
- `POST /api/campaigns/v2/house-ads/`

**Playlists API:**
- `GET /api/campaigns/v2/playlist-templates/`
- `POST /api/campaigns/v2/playlist-templates/`
- `POST /api/campaigns/v2/playlists/generate/` → Async playlist generation job başlatma
- `GET /api/campaigns/v2/playlists/jobs/` → Job listesi
- `GET /api/campaigns/v2/playlists/jobs/{job_id}/` → Job durumu

**Pricing API:**
- `GET /api/campaigns/v2/pricing-matrix/`
- `PUT /api/campaigns/v2/pricing-matrix/`

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

---

## Kritik UI Akışları

### 1. Campaign Oluşturma (CampaignWizard.vue)

1. SuperAdmin → `/admin/campaigns`
2. "Yeni Kampanya" butonu → modal açılır
3. Form: `name`, `advertiser_name`, `start_date`, `end_date`, `priority`, `is_guaranteed`, `impression_goal`, `frequency_cap_per_hour`
4. Target seçimi: Il/Ilce/Eczane hiyerarşisi (`CampaignTarget` kayıtları)
5. `POST /api/campaigns/v2/campaigns/` → campaign kaydı
6. Creative upload:
   - Dosya seçimi → `POST /api/campaigns/upload-media/` → media_url
   - `POST /api/campaigns/v2/creatives/` → creative kaydı (campaign FK, media_url, duration_seconds)
7. ScheduleRule tanımlama:
   - Form: `frequency_type`, `frequency_value`, `target_hours` (JSON)
   - `POST /api/campaigns/v2/campaigns/{id}/rules/` → rule kaydı
8. Campaign listesinde görünür, status (ACTIVE/PAUSED/COMPLETED) değiştirilebilir

### 2. Playlist Şablon Oluşturma (PlaylistEditor.vue)

1. SuperAdmin → `/admin/playlists`
2. "Yeni Şablon" butonu → modal
3. Form: `name`, `target_hour` (0-23), `locked` (bool)
4. Drag-and-drop playlist item sıralaması (creative/house_ad seçimi, duration)
5. `POST /api/campaigns/v2/playlist-templates/` → şablon kaydı
6. Şablon üzerinden kiosk için playlist üretimi:
   - Kiosk seçimi + tarih aralığı
   - `POST /api/campaigns/v2/playlists/generate/` → async job başlatılır
   - `GET /api/campaigns/v2/playlists/jobs/{job_id}/` → job durumu polling

### 3. Fiyatlandırma Matrisi (PricingMatrixConfigurator.vue)

1. SuperAdmin → `/admin/pricing`
2. `GET /api/campaigns/v2/pricing-matrix/` → mevcut matris (singleton)
3. Form: JSON editör (slot fiyatları, süre katsayıları, vb.)
4. `PUT /api/campaigns/v2/pricing-matrix/` → güncelleme
5. Backend → fiyat hesaplamalarında kullanır

### 4. QR Tarama (QrScan.vue)

1. Eczacı → `/pharmacist/qr`
2. QR kodu okutulur (kamera veya manuel input)
3. `GET /api/pharmacies/sessions/?qr={qr_kodu}` → session detayı
4. Modal: Kullanıcı demografisi, kategori, cevaplar, önerilen etken maddeler
5. Eczacı → danışmanlık sonuçlandırma (bu akış backend'de şu an eksik olabilir)

### 5. Dashboard Analytics (Dashboard.vue)

1. SuperAdmin/Pharmacist → `/admin` veya `/pharmacist`
2. Kartlar: Toplam session, tamamlanan session, toplam impression, aktif kampanya sayısı
3. Grafikler: Günlük session trend, kampanya performansı, kategori dağılımı
4. API çağrıları:
   - `GET /api/analytics/oturum-loglari/?start_date={date}&end_date={date}`
   - `GET /api/analytics/play-logs/?start_date={date}&end_date={date}`
5. **Eczane Kiosk Listesi:**
   - Eczane filtresi ile kiosk listesi görüntüleme
   - Kiosk bilgileri: Ad, MAC adresi, Uygulama Anahtarı, Durum, Son Görülme
   - Kiosk düzenleme: Ad, MAC adresi, Aktif/Pasif durumu güncellenebilir
   - Uygulama Anahtarı: Salt okunur (backend tarafından otomatik üretilir)
   - `PATCH /api/pharmacies/kiosks/{id}/` → Kiosk güncelleme

---

## Belirsiz / Riskli Noktalar

1. **QR tarama sonrası akış:** Eczacı QR okutunca session detayını görüyor ama sonrasında ne yapılacak? Danışmanlık sonuçlandırma endpoint'i yok gibi görünüyor. (Belirsiz)
2. **Playlist generation job polling:** Job durumu polling yapılıyor mu, yoksa kullanıcı manuel yenileme mi yapıyor? (Belirsiz)
3. **Campaign targeting UI:** `CampaignTarget` hiyerarşisi UI'da tam destekleniyor mu, yoksa legacy `target_pharmacies` M2M mi kullanılıyor? (Belirsiz)
4. **Pharmacist kısıtlamaları:** Backend'de pharmacist'in kendi eczanesine ait verileri filtreleme mantığı var mı? (Doğrulanmalı)
5. **Token refresh interceptor:** Axios interceptor'da retry logic düzgün çalışıyor mu, sonsuz döngü riski? (Doğrulanmalı)
6. **Kiosk düzenleme (Dashboard):** ✅ Dashboard'da kiosk düzenleme eklendi (ad, MAC, aktif/pasif durum güncellenebilir, uygulama anahtarı salt okunur)
7. **Kiosk düzenleme (DeviceManagement):** ✅ Cihaz yönetimi sayfasında kiosk düzenleme eklendi (ad, MAC, aktif/pasif durum güncellenebilir, uygulama anahtarı görüntülenir ve salt okunur)

---

**Satır sayısı: ~200**
