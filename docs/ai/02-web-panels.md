# Web Panels â€” Vue 3 + Vite + Pinia + Tailwind CSS

**AmaÃ§:** Admin ve Pharmacist panelleri; kampanya/playlist/fiyat/kullanÄ±cÄ±/cihaz yÃ¶netimi, QR tarama, session raporlarÄ±.

---

## When To Read This File

- Frontend UI deÄŸiÅŸiklikleri iÃ§in
- Yeni admin paneli sayfasÄ± eklerken
- QR tarama akÄ±ÅŸÄ± problemlerinde
- Dashboard/analytics deÄŸiÅŸikliklerinde
- Auth/RBAC sorunlarÄ±nda

---

## Important Source Files

- `web_panels/src/router/index.js` â€” Route tanÄ±mlarÄ±, RBAC guard
- `web_panels/src/stores/auth.js` â€” Auth state management
- `web_panels/src/services/api.js` â€” Backend API client
- `web_panels/src/services/dooh.js` â€” DOOH campaign/creative/playlist API client (simulate/activate/targets/kiosk-health)
- `web_panels/src/services/lookups.js` â€” Ä°l/Ä°lÃ§e lookup (getIller/getIlceler)
- `web_panels/src/views/admin/CampaignWizard.vue` â€” Kampanya yÃ¶netimi (6 adÄ±mlÄ± wizard)
- `web_panels/src/views/admin/DoohControlCenter.vue` â€” DOOH izleme merkezi
- `web_panels/src/views/admin/PlaylistEditor.vue` â€” Playlist dÃ¼zenleme
- `web_panels/src/composables/useKioskRolloutStatus.js` â€” Kiosk rollout durum hesabÄ± (tek merkezi kaynak)
- `web_panels/src/views/pharmacist/QrScan.vue` â€” QR tarama
- `web_panels/src/views/admin/Dashboard.vue` â€” Admin dashboard
- `web_panels/public/config.js` â€” Runtime config

---

## Panel Projesinin AmacÄ±

**KullanÄ±cÄ± tipleri:**
- **SuperAdmin:** TÃ¼m sistem yÃ¶netimi (kampanyalar, fiyatlandÄ±rma, kullanÄ±cÄ±lar, cihazlar, kategori/soru mantÄ±ÄŸÄ±)
- **Pharmacist (EczacÄ±):** Kendi eczanesine ait dashboard, QR tarama, inbox

**Ana iÅŸlevler:**
1. Kampanya oluÅŸturma ve yÃ¶netimi (CampaignWizard â€” 6 adÄ±mlÄ± wizard)
2. DOOH kontrol merkezi (DoohControlCenter â€” kampanya/job/kiosk izleme)
3. Playlist ÅŸablon/manuel dÃ¼zenleme (PlaylistEditor)
4. FiyatlandÄ±rma matrisi konfigÃ¼rasyonu (PricingMatrixConfigurator)
4. Kategori/Soru/Etken Madde/DanÄ±ÅŸma yÃ¶netimi (MedicalLogic, DanismaYonetimi)
5. Eczane/Kiosk cihaz yÃ¶netimi (DeviceManagement)
   - Kiosk izleme: MAC adresi, Uygulama AnahtarÄ±, durum, son ping
   - Kiosk dÃ¼zenleme: Ad, MAC adresi, Aktif/Pasif durumu gÃ¼ncellenebilir
   - Uygulama AnahtarÄ±: Salt okunur (backend tarafÄ±ndan otomatik Ã¼retilir)
   - Kopyalama Ã¶zelliÄŸi: Uygulama AnahtarÄ± yanÄ±nda kopyala butonu (clipboard API, toast notification)
6. **Onay Bekleyen Cihazlar (PendingDevices â€” 2026-07-14):** Fleet key + HMAC doÄŸrulamasÄ±ndan geÃ§miÅŸ henÃ¼z kayÄ±tlÄ± olmayan kiosk cihazlarÄ±nÄ±n yÃ¶netimi
   - Cihaz listesi: MAC, hostname, durum badge, ilk/son gÃ¶rÃ¼lme, baÅŸvuru sayÄ±sÄ±
   - Detay modal: yapÄ±landÄ±rÄ±lmÄ±ÅŸ cihaz bilgileri (hostname, OS, CPU, RAM, IP listesi, Node sÃ¼rÃ¼mÃ¼, uptime); token/secret gÃ¶sterilmez
   - Onay modal: `EisaLookup` autocomplete ile eczane arama (ad, il, ilÃ§e) + kiosk adÄ± â†’ tek transaction ile Kiosk kaydÄ± oluÅŸturulur
   - Red modal: opsiyonel red nedeni
   - Route: `/admin/devices/pending` (SuperAdmin RBAC korumalÄ±)
7. **Dashboard pending alert (2026-07-14):** `pendingCount > 0` olduÄŸunda sayfa baÅŸÄ±nda sarÄ± uyarÄ± banner'Ä±; `/admin/devices/pending`'e doÄŸrudan link
6. KullanÄ±cÄ± yÃ¶netimi (UserManagement)
7. QR kodu tarama ve session detayÄ± (QrScan)
8. Dashboard analytics (kampanya performansÄ±, session Ã¶zeti)

---

## Ana Sayfa / Component / Module YapÄ±sÄ±

### Router (`src/router/index.js`)

**Public:**
- `/` â†’ Redirect to `/login`
- `/login` â†’ `Login.vue`

**SuperAdmin routes (`/admin/*`):**
- `/admin` â†’ `Dashboard.vue`
- `/admin/devices` â†’ `DeviceManagement.vue` (Eczane/Kiosk CRUD)
- `/admin/devices/pending` â†’ `PendingDevices.vue` (Onay Bekleyen Cihazlar â€” 2026-07-14)
- `/admin/medical-logic` â†’ `MedicalLogic.vue` (Kategori/Soru/EtkenMadde CRUD)
- `/admin/danisma` â†’ `DanismaYonetimi.vue` (DanÄ±ÅŸma kategorileri CRUD)
- `/admin/campaigns` â†’ `CampaignWizard.vue` (DOOH v2 Kampanya â€” 6 adÄ±mlÄ± wizard)
- `/admin/dooh/control-center` â†’ `DoohControlCenter.vue` (DOOH izleme â€” kampanya/job/kiosk) â€” **Faz 6**
- `/admin/playlists` â†’ `PlaylistEditor.vue` (Playlist ÅŸablon/manuel dÃ¼zenleme)
- `/admin/pricing` â†’ `PricingMatrixConfigurator.vue` (FiyatlandÄ±rma matrisi)
- `/admin/users` â†’ `UserManagement.vue` (KullanÄ±cÄ± CRUD)

**Pharmacist routes (`/pharmacist/*`):**
- `/pharmacist` â†’ `Dashboard.vue`
- `/pharmacist/inbox` â†’ `Inbox.vue` (Eczane session'larÄ± listesi)
- `/pharmacist/qr` â†’ `QrScan.vue` (QR tarama)

**RBAC guard:** `router.beforeEach` â€” `useAuthStore().role` kontrolÃ¼

---

### Store YapÄ±sÄ± (`src/stores/`)

- `auth.js` (`useAuthStore`): KullanÄ±cÄ± login/logout, role/pharmacyId/userId state (localStorage sync)
- (DiÄŸer store'lar component-level state veya API Ã§aÄŸrÄ±larÄ± iÃ§in kullanÄ±lÄ±yor olabilir, merkezi store kÄ±sÄ±tlÄ±)

---

### Component YapÄ±sÄ± (`src/components/`)

TÃ¼m componentler tek dosyalÄ± Vue 3 Composition API (`.vue` dosyalarÄ±). Liste:
- Form componentleri (input/select/button wrapper'larÄ±)
- Modal/Dialog componentleri
- Table/List componentleri (kampanya listesi, kiosk listesi, vb.)

(DetaylÄ± component listesi gerekirse `src/components/` klasÃ¶rÃ¼ taranabilir; ÅŸimdilik top-level view'ler yeterli)

---

### Services (`src/services/`)

- `api.js`: Axios instance + API method'larÄ±
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
- `withCredentials: true` (httpOnly Ã§erez)
- Interceptor: 401 â†’ refresh token â†’ retry request

---

## Backend ile KonuÅŸtuÄŸu API'ler

TÃ¼m API Ã§aÄŸrÄ±larÄ± `axios` Ã¼zerinden `/api/*` endpoint'lerine yapÄ±lÄ±r.

**Auth API:**
- `POST /api/auth/token/` â†’ Login (username/password) â†’ httpOnly Ã§erez set edilir
- `POST /api/auth/token/refresh/` â†’ Token yenileme
- `POST /api/auth/logout/` â†’ Ã‡erez temizleme

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
- `PATCH /api/pharmacies/kiosklar/{id}/` â†’ Kiosk gÃ¼ncelleme (ad, mac, aktif)
- `PUT /api/pharmacies/kiosklar/{id}/`
- `DELETE /api/pharmacies/kiosklar/{id}/`
- `GET /api/analytics/sessions/?qr_kodu={qr_kodu}` â†’ QR ile session detayÄ±

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
- `POST /api/campaigns/v2/campaigns/bulk-action/` (pause/resume/delete toplu iÅŸlem)
- `GET /api/campaigns/v2/campaigns/{id}/rules/`
- `POST /api/campaigns/v2/campaigns/{id}/rules/`
- `POST /api/campaigns/upload-media/` (file upload, multipart/form-data)
- `POST /api/campaigns/v2/creatives/`
- `GET /api/campaigns/v2/house-ads/`
- `POST /api/campaigns/v2/house-ads/`

**Playlists API:**
- `GET /api/campaigns/v2/playlist-templates/`
- `POST /api/campaigns/v2/playlist-templates/`
- `POST /api/campaigns/v2/playlists/generate/` â†’ Async playlist generation job baÅŸlatma
- `GET /api/campaigns/v2/playlists/jobs/` â†’ Job listesi
- `GET /api/campaigns/v2/playlists/jobs/{job_id}/` â†’ Job durumu

**Pricing API:**
- `GET /api/campaigns/v2/pricing-matrix/`
- `PUT /api/campaigns/v2/pricing-matrix/`

**Analytics API:**
- `GET /api/analytics/oturum-loglari/?kiosk={id}&start_date={date}&end_date={date}`
- `GET /api/analytics/play-logs/?campaign={id}&kiosk={id}&start_date={date}`

---

## Yetki / Auth / Config YapÄ±sÄ±

### Authentication

**Login akÄ±ÅŸÄ±:**
1. KullanÄ±cÄ± â†’ `/login` â†’ `username` + `password` girer
2. `Login.vue` â†’ `api.login(username, password)` Ã§aÄŸrÄ±sÄ±
3. Backend â†’ `POST /api/auth/token/` â†’ JWT httpOnly Ã§erez set edilir
4. Backend â†’ response: `{ role, pharmacyId, userId }`
5. Frontend â†’ `useAuthStore().login()` â†’ localStorage'a `eisa_role`, `eisa_pharmacy_id`, `eisa_user_id` yazÄ±lÄ±r
6. Router â†’ role'e gÃ¶re `/admin` veya `/pharmacist` redirect

**Logout akÄ±ÅŸÄ±:**
1. KullanÄ±cÄ± â†’ logout butonu
2. `useAuthStore().logout()` â†’ `api.logout()` Ã§aÄŸrÄ±sÄ±
3. Backend â†’ `/api/auth/logout/` â†’ Ã§erez temizlenir
4. Frontend â†’ localStorage temizlenir, `/login` redirect

**Token refresh:**
- Axios interceptor â†’ 401 hatasÄ± â†’ `api.refreshToken()` â†’ retry request
- EÄŸer refresh baÅŸarÄ±sÄ±z â†’ `/login` redirect

### Authorization

**RBAC:**
- `router.beforeEach` guard: `to.meta.roles` kontrolÃ¼
- `useAuthStore().role` â†’ `superadmin` veya `pharmacist`
- EÄŸer role uyumsuz â†’ `/login` redirect

**Pharmacist kÄ±sÄ±tlamalarÄ±:**
- Sadece kendi eczanesine ait verileri gÃ¶rÃ¼r (backend tarafÄ±nda `request.user.eczane` kontrolÃ¼)
- Campaign/Playlist/Pricing/User Management sayfalarÄ±na eriÅŸemez

### Config

**Runtime config (`public/config.js`):**
```js
window.EISA_API_BASE_URL = 'http://localhost:8000';
```
- Prod deployment'ta nginx tarafÄ±ndan override edilebilir (config.js dosyasÄ± dinamik oluÅŸturulur)

### Loglama (2026-07-16)

- `src/lib/logger.js`: Prod'da INFO/DEBUG bastÄ±rÄ±lÄ±r; sadece WARNING/ERROR/CRITICAL iÅŸlenir.
- `main.js` iÃ§inde `installGlobalHandlers(app)` ile `app.config.errorHandler` + `window.onerror` + `unhandledrejection` yakalanÄ±r.
- Axios interceptor response'daki `X-Correlation-ID` baÅŸlÄ±ÄŸÄ±nÄ± `window.__EISA_LAST_CORRELATION_ID__` Ã¼zerinde tutar.
- Kritik hatalar `POST /api/analytics/client-events/` ile backend'e gÃ¶nderilir (allow-list: level/event/message/stack/component/route/correlation_id/occurred_at).
- KullanÄ±cÄ± verisi, form iÃ§eriÄŸi, query string DEÄERLERÄ° gÃ¶nderilmez. Sonsuz dÃ¶ngÃ¼ korumasÄ±: kendi bildirim hatasÄ± tekrar loglanmaz.
- Detay: [docs/operations/logging.md](../operations/logging.md).

---

## Kritik UI AkÄ±ÅŸlarÄ±

### 1. Campaign OluÅŸturma/DÃ¼zenleme (CampaignWizard.vue) â€” Faz 6

**Route:** `/admin/campaigns` (SuperAdmin)
**Modal:** Tek sayfada kampanya listesi + 6 adÄ±mlÄ± wizard modal

**Wizard adÄ±mlarÄ±:**

| AdÄ±m | BaÅŸlÄ±k | AÃ§Ä±klama |
|------|--------|----------|
| 1 | Bilgiler | `name`, `advertiser_name`, `start_date`, `end_date`, `status` |
| 2 | Medya | Creative upload (tek dosya), `duration_seconds` (5/10/15/30/60 sn) |
| 3 | Hedefleme | ALL (tÃ¼m aktif kiosklar) veya RULES (IL/ILCE/ECZANE hedefleri) |
| 4 | Frekans/Pacing | Frekans modu (PER_LOOP/PER_HOUR/PER_DAY + target_hours) veya GÃ¶sterim Hedefi modu |
| 5 | SimÃ¼lasyon | Read-only kapasite simÃ¼lasyonu â€” kalÄ±cÄ± mutation yok |
| 6 | Aktive Et | Ã–zet + Kaydet (taslak) + Aktive Et (onay modali) |

**Create/Edit davranÄ±ÅŸÄ±:**
- Create mode: `openCreate()` â€” empty form, formDirty=false
- Edit mode: `openEdit(c)` â€” mevcut kampanya yÃ¼klenir; `getCampaignRules` + `getCampaignTargets` Ã§aÄŸrÄ±lÄ±r
- Edit sÄ±rasÄ±nda formun yÃ¶netmediÄŸi alanlar (priority, is_guaranteed) gÃ¶nderilmez (PATCH â€” sadece deÄŸiÅŸenler)
- `saveDraft()`: AdÄ±m 4â†’5 geÃ§iÅŸinde otomatik Ã§aÄŸrÄ±lÄ±r; `createCampaignV2` â†’ `createCreative` â†’ `setCampaignTargets` â†’ `setCampaignRules`

**Hedefleme (AdÄ±m 3):**
- `target_scope = 'ALL'`: Hedef belirtmek zorunlu deÄŸil
- `target_scope = 'RULES'`: En az 1 IL/ILCE/ECZANE hedefi zorunlu
- CampaignTarget kayÄ±tlarÄ±: `{ target_type, il?, ilce?, eczane? }`
- **NOT:** `Campaign.target_pharmacies` (legacy M2M) artÄ±k CampaignWizard tarafÄ±ndan KULLANILMAMAKTADIR
- `getIller()`/`getIlceler()` â†’ `lookups.js`'den Ã§aÄŸrÄ±lÄ±r (dooh.js'de deÄŸil)
- Eczane: `EisaLookup` component (`GET /api/pharmacies/`) ile arama

**Creative Upload (AdÄ±m 2):**
- `POST /api/campaigns/upload-media/` (multipart/form-data)
- Response: `{ media_url, object_key, checksum, url[alias] }` â€” `media_url ?? url` fallback
- `POST /api/campaigns/v2/creatives/` â†’ `{ campaign, media_url, object_key, checksum, duration_seconds, name }`
- Upload hatasÄ±nda form state korunur (saving=false, creatives listesi deÄŸiÅŸmez)
- Mevcut (kaydedilmiÅŸ) creatives `c.id` varsa yeniden upload edilmez

**ScheduleRule:**
- Backend contract: `{ frequency_type, frequency_value, target_hours }` (target_days Faz 7'de UI'dan kaldırıldı)
- `frequency_type`: `PER_LOOP | PER_HOUR | PER_DAY`
- `target_hours`: `[0..23]` array veya `null` (tÃ¼m gÃ¼n)
- UI'daki "Hedef gÃ¼nler" devre dÄ±ÅŸÄ± â€” backend desteÄŸi yoktur, yakÄ±nda eklenecek

**SimÃ¼lasyon (AdÄ±m 5):**
- `POST /api/campaigns/v2/campaigns/{id}/simulate/` â€” kalÄ±cÄ± deÄŸiÅŸiklik yapmaz
- simResult var + form deÄŸiÅŸirse â†’ `simStale=true` (watcher: name, start_date, end_date, creatives.length, target_scope, rule, impression_goal)
- `simStale=true` iken Aktive Et butonu `disabled`
- Aktivasyondan Ã¶nce simÃ¼lasyon zorunlu

**Activation (AdÄ±m 6):**
- `POST /api/campaigns/v2/campaigns/{id}/activate/` â€” `DOOH_ENGINE_V2=active` gerektirir
- EisaDeleteConfirm onay modali (double-submit engeli: `activateLoading` flag)
- 409 â†’ kapasite/kota hatasÄ±; 400 â†’ validation hatasÄ±; her ikisi gÃ¶rÃ¼ntÃ¼lenir
- Activation response queued job ise UI "baÅŸarÄ±yla aktive edildi" gÃ¶sterir (job_id dÃ¶ner)

**KaydedilmemiÅŸ deÄŸiÅŸiklik uyarÄ±sÄ±:**
- `formDirty` ref â€” form name/tarih/creative deÄŸiÅŸince `true`
- `close()` â†’ `formDirty=true` ise `confirm()` diyaloÄŸu
- `saveDraft()` baÅŸarÄ±yla tamamlanÄ±nca `formDirty=false`

**Silme:**
- Tekil: EisaDeleteConfirm modal â†’ `deleteCampaignV2(id)`
- Bulk: native `confirm()` â†’ `bulkActionCampaignsV2('delete', ids)`

**KullanÄ±lan ortak componentler:**
- `EisaLookup` (eczane arama)
- `EisaDeleteConfirm` (silme/aktivasyon onayÄ±)
- `DateRangePicker` (tarih aralÄ±ÄŸÄ±)
- `vue-sonner` (toast bildirimler)
- `eisa-*` CSS sÄ±nÄ±flarÄ± (global styles.css)

### 2. DOOH Kontrol Merkezi (DoohControlCenter.vue) â€” Faz 6

**Route:** `/admin/dooh/control-center` (SuperAdmin â€” `/admin/*` meta: `roles: ['superadmin']`)

**BÃ¶lÃ¼mler:**

1. **Ã–zet kartlar:** Aktif kampanya, Bekleyen/BaÅŸarÄ±sÄ±z job, Geride kiosk sayÄ±larÄ±
2. **Kampanya listesi:** Status badge + pause/resume/cancel/delete (EisaDeleteConfirm ile)
3. **Playlist Ã¼retim iÅŸleri:** job listesi, polling (yalnÄ±z PENDING/RUNNING), `onUnmounted` cleanup
4. **Kiosk daÄŸÄ±tÄ±m durumu:** desired/applied/horizon tablosu, rollout durum badge'i

**Polling lifecycle:**
- `hasActiveJobs` true â†’ `setInterval(8000)` baÅŸlar
- `hasActiveJobs` false â†’ `clearInterval` (terminal durum = DONE/FAILED/RETRY)
- `onUnmounted(() => stopPolling())` â€” timer temizlenir
- `if (_pollInterval) return` â€” birden fazla timer oluÅŸmaz

**Kiosk Rollout Durumu (`calcKioskRolloutStatus`):**
- Tek merkezi kaynak: `composables/useKioskRolloutStatus.js`
- `applied null` â†’ `ack_pending` ("ACK Bekleniyor") â€” hata deÄŸil
- `applied < desired` â†’ `behind` ("Geride")
- `applied == desired` ama `applied_horizon_end < serverHorizonEnd` â†’ `horizon_stale` ("Horizon Eksik")
- `applied == desired` ve horizon yeterli â†’ `up_to_date` ("GÃ¼ncel")
- Europe/Istanbul gÃ¼n: `Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Istanbul' })` â€” browser timezone'una kÃ¶r biÃ§imde gÃ¼venilmez
- `serverHorizonEnd` backend'den alÄ±nÄ±r (ÅŸu an `null` â€” horizon kontrolÃ¼ atlanÄ±r)

**Status mapping:**
- `STATUS_MAP` (kampanya): ACTIVE/PAUSED/COMPLETED/DRAFT/CANCELLED â†’ label + CSS class
- `JOB_STATUS_MAP` (job): PENDING/RUNNING/DONE/FAILED/RETRY; `COMPLETED` â†’ `DONE` (backward compat)
- `ROLLOUT_ACCENT_MAP` (kiosk): up_to_date/behind/ack_pending/horizon_stale/offline/no_publish/unknown
- ÃœÃ§ map tek dosyada (DoohControlCenter.vue) â€” kopya yok

**ControlCenter salt izleme yapar:**
- Applied version deÄŸiÅŸtirmez
- ACK Ã¼retmez
- Otomatik publish tetiklemez

### 3. Gelismis Manuel Yayin (PlaylistEditor.vue) — Faz 7: Salt Okunur

**Route:** `/admin/playlists` (SuperAdmin — backward compat)
**Nav adı:** "Gelişmiş Manuel Yayın"

**Faz 7 sonrası durum — tam salt okunur:**
- Mevcut Loop Şablonları, Saatlik Planlar, Günlük Planlar **tablolar olarak** gösterilir
- Şablon/plan oluşturma/düzenleme/silme/drag-reorder mutation'ları **kaldırıldı** (sadece görüntüleme)
- `createPlaylistTemplate`, `updatePlaylistTemplate`, `deletePlaylistTemplate`, `createHourPlan`, `updateHourPlan`, `deleteHourPlan`, `createDayPlan`, `updateDayPlan`, `deleteDayPlan` importları ve fonksiyonları **kaldırıldı**
- Salt okunur banner ekranın üstünde açıkça görünür
- CampaignWizard'a ve ControlCenter'a yönlendiren linkler var

**Korunan bölüm:** Canonical `generatePlaylists` (`POST /api/campaigns/v2/playlists/generate/`)
- Seçili kiosk + tarih için async job kuyruğuna alır
- Double-submit koruması (`uretimKilit` flag)
- Confirmation dialog zorunlu
- Job durumu `setInterval` ile polling (terminal durumda `clearInterval`), `onUnmounted` cleanup

### 4. Fiyatlandirma Matrisi (PricingMatrixConfigurator.vue)

1. SuperAdmin â†’ `/admin/pricing`
2. `GET /api/campaigns/v2/pricing-matrix/` â†’ mevcut matris (singleton)
3. Form: JSON editÃ¶r (slot fiyatlarÄ±, sÃ¼re katsayÄ±larÄ±, vb.)
4. `PUT /api/campaigns/v2/pricing-matrix/` â†’ gÃ¼ncelleme
5. Backend â†’ fiyat hesaplamalarÄ±nda kullanÄ±r

### 4. QR Tarama (QrScan.vue)

1. EczacÄ± â†’ `/pharmacist/qr`
2. Fiziksel barkod okuyucu (keyboard wedge) input'a 8 karakter QR yazar ve Enter gÃ¶nderir.
3. Kamera akÄ±ÅŸÄ± kaldÄ±rÄ±lmÄ±ÅŸtÄ±r (getUserMedia/video/BarcodeDetector yoktur).
4. `GET /api/analytics/sessions/?qr_kodu={qr_kodu}` Ã§aÄŸrÄ±lÄ±r.
5. Backend 400/403/404 durumlarÄ±nÄ± ayrÄ±ÅŸtÄ±rÄ±r; UI bunu ayrÄ± mesajlarla gÃ¶sterir.
6. BaÅŸarÄ±lÄ± response'da oturum detaylarÄ±, soru-cevap Ã§Ã¶zÃ¼mÃ¼ ve Ã¶nerilen etken madde detaylarÄ± gÃ¶sterilir.
7. `POST /api/analytics/sessions/{id}/complete/` ile danÄ±ÅŸma tamamlanÄ±r; `sale_result` (`sold`/`not_sold`) opsiyonel gÃ¶nderilir.

### 5. Dashboard Analytics (Dashboard.vue)

1. SuperAdmin/Pharmacist â†’ `/admin` veya `/pharmacist`
2. Kartlar: Toplam session, tamamlanan session, toplam impression, aktif kampanya sayÄ±sÄ±
3. Grafikler: GÃ¼nlÃ¼k session trend, kampanya performansÄ±, kategori daÄŸÄ±lÄ±mÄ±
4. API Ã§aÄŸrÄ±larÄ±:
   - `GET /api/analytics/oturum-loglari/?start_date={date}&end_date={date}`
   - `GET /api/analytics/play-logs/?start_date={date}&end_date={date}`
5. **Eczane Kiosk Listesi:**
   - Eczane filtresi ile kiosk listesi gÃ¶rÃ¼ntÃ¼leme
   - Kiosk bilgileri: Ad, MAC adresi, Uygulama AnahtarÄ±, Durum, Son GÃ¶rÃ¼lme
   - Kiosk dÃ¼zenleme: Ad, MAC adresi, Aktif/Pasif durumu gÃ¼ncellenebilir
   - Uygulama AnahtarÄ±: Salt okunur (backend tarafÄ±ndan otomatik Ã¼retilir)
   - `PATCH /api/pharmacies/kiosks/{id}/` â†’ Kiosk gÃ¼ncelleme

---

## Belirsiz / Riskli Noktalar

1. **CampaignWizard target_scope (Ã‡Ã–ZÃœLDÃœ):** `target_scope` Faz 6'da wizard AdÄ±m 3'e eklendi. `ALL` veya `RULES` zorunlu.
2. **CampaignWizard medya akÄ±ÅŸÄ± (Faz 0.5):** Upload response canonical: `{object_key, media_url, checksum, url[alias]}`. `media_url ?? url` fallback Ã§alÄ±ÅŸÄ±yor. Component testi: `dooh_media_flow.test.js` âœ“.
3. **Campaign.target_pharmacies (Ã‡Ã–ZÃœLDÃœ):** CampaignWizard bu legacy alanÄ± KULLANMAMAKTADIR. Hedefleme yalnÄ±z `CampaignTarget` (IL/ILCE/ECZANE) Ã¼zerinden yapÄ±lÄ±r.
4. **Playlist generation job polling (Ã‡Ã–ZÃœLDÃœ):** PlaylistEditor ve DoohControlCenter polling yalnÄ±z PENDING/RUNNING durumunda Ã§alÄ±ÅŸÄ±r; terminal durumda (DONE/FAILED) durur. `onUnmounted` ile timer temizlenir.
5. **HouseAd yÃ¶netim ekranÄ± eksik:** AyrÄ± HouseAd management vue ekranÄ± yok. Backend canonical akÄ±ÅŸÄ± serializer dÃ¼zeyinde test edildi. UI kapsam aÃ§Ä±ÄŸÄ± Faz 6'da KAPATILMADI (Faz 7 kapsamÄ±).
6. **follows API write point:** `Campaign.follows` CampaignSerializer'da read-only. YalnÄ±z `set_campaign_follows()` servisi Ã¼zerinden.
7. **Vue test pre-existing failure:** `api.test.js login()` testi Ã¶nceden yanlÄ±ÅŸ contract bekliyordu (access/refresh yerine rol/userId). 2026-07-22'de dÃ¼zeltildi.
8. **Token refresh interceptor:** Axios interceptor'da retry logic dÃ¼zgÃ¼n Ã§alÄ±ÅŸÄ±yor mu, sonsuz dÃ¶ngÃ¼ riski? (DoÄŸrulanmalÄ±)

---

**SatÄ±r sayÄ±sÄ±: ~210**
