# AI Changelog — Dokümantasyon ve Kod Değişiklikleri

**Amaç:** AI tarafından yapılan değişikliklerin kısa kaydı.  
**Format:** Tarih — Değişiklik (max 10 satır/kayıt)

---

## 2026-07-16

### [kiosk_edge/ui] — Dead Code Temizliği: SensitiveScreen Kaldırıldı
**Değişiklik:** Runtime'da hiçbir yerden çağrılmayan `SensitiveScreen.svelte` silindi. Yalnız bu dosyada kullanılan ölü CSS selector'ları (`.cat-card.sensitive*`, `.sensitive-badge`, `.sensitive-info-box`) temizlendi. `stores/kiosk.js` ekran state yorumu gerçek akışla hizalandı (`sensitive` → `consult`).  
**Dosyalar:** `kiosk_edge/ui/src/components/SensitiveScreen.svelte` (silindi), `kiosk_edge/ui/src/app.css`, `kiosk_edge/ui/src/stores/kiosk.js`  
**Breaking:** Yok (aktif akış `ConsultScreen` üzerinden devam ediyor).  
**Test:** `npm test`, `npm run build` (kiosk_edge/ui)

---

## 2026-07-14

### [kiosk_edge] — Bootstrap İsteğine Cihaz Metadata Eklendi
**Değişiklik:** `provisioning.js`'e `collectDeviceMetadata()` fonksiyonu eklendi. Bootstrap isteği artık `hostname` ve `device_metadata` gönderir.  
**Toplanan alanlar:** hostname, os_type, os_platform, os_release, arch, cpu_model, cpu_cores, total_memory_mb, ip_addresses (iface+IPv4), node_version, uptime_seconds.  
**Güvenlik:** Her alan `try/catch` içinde; token/secret/hmac içermiyor; `collectDeviceMetadata` export edildi.  
**Dosyalar:** `kiosk_edge/api-node/src/provisioning.js`  
**Breaking:** Yok (bootstrap body yeni isteğe bağlı alanlar aldı; backend zaten kabul ediyordu).

### [web_panels] — Dashboard Pending Devices Banner + PendingDevices UX İyileştirme
**Değişiklik:** Dashboard'a `pendingCount > 0` olduğunda sarı uyarı banner'ı eklendi (`/admin/devices/pending` linki ile). PendingDevices.vue: eczane seçimi `<select>`'ten `EisaLookup` autocomplete'e çevrildi (ad/il/ilçe arama); metadata detay modalı yapılandırılmış görünüme (insan okunur etiketler, IP listesi, uptime formatlı) geçirildi.  
**Dosyalar:** `web_panels/src/views/admin/Dashboard.vue`, `PendingDevices.vue`, `services/devices.js`  
**Breaking:** Yok.

---

## 2026-07-14

### [Backend + web_panels + kiosk_edge] — Onay Bekleyen Cihaz Provisioning Akışı
**Değişiklik:** Kayıtsız kiosklar için uçtan uca IoT cihaz kayıt ve onay sistemi eklendi.  
**Backend:** `KioskProvisioningRequest` modeli (PENDING/APPROVED/REJECTED lifecycle), migration 0006, `KioskBootstrapView` güncellendi (202 PENDING / 403 REJECTED), admin provisioning API endpoints (`/api/pharmacies/kiosks/provisioning/` list/detail/approve/reject).  
**web_panels:** `PendingDevices.vue` yeni view, `/admin/devices/pending` route, AdminLayout nav item, `devices.js` service fonksiyonları eklendi.  
**kiosk_edge:** `provisioning.js` durum makinesi (UNREGISTERED→PENDING_APPROVAL→APPROVED/REJECTED), `scheduler.js` bootstrap retry, `getProvisioningState` export edildi.  
**Güvenlik:** fleet_key/provision_secret DB/log/UI'da saklanmaz; sabit zaman karşılaştırma korundu; onay transaction+select_for_update ile race condition güvenli; pending cihaz normal API'lere erişemez.  
**Dosyalar:** `pharmacies/models.py`, `pharmacies/migrations/0006_*.py`, `pharmacies/serializers.py`, `pharmacies/views.py`, `pharmacies/urls.py`, `pharmacies/tests/test_provisioning.py`, `web_panels/.../PendingDevices.vue`, `devices.js`, `router/index.js`, `AdminLayout.vue`, `kiosk_edge/api-node/src/provisioning.js`, `scheduler.js`. **Doküman:** 00-AI-INDEX, 01-backend, 02-web-panels, 03-kiosk-edge-api-node, 05-cross-project-flows, 06-db-and-api-contracts güncellendi.  
**Test:** 24/24 backend testi geçti.  
**Breaking:** KioskBootstrapView davranışı değişti: bilinmeyen MAC artık 404 yerine 202 döndürüyor.

---

## 2026-07-07

### Kiosk Edge — SQLite FK Kaldırma + QR Anında Sync + ConsultScreen Visual Temizlik
**Değişiklik:** 3 kiosk iyileştirmesi yapıldı: (1) SQLite foreign key constraint'leri kaldırıldı, (2) QR oluştuğunda session anında backend'e iletilir, (3) Danışma kategori ikonlarının altındaki "X alt konu" yazısı kaldırıldı (alt kategori yapısı korundu).  
**Detay:**
1. **SQLite FK kaldırma:** `db.js` schema'sından tüm `REFERENCES` clause'ları kaldırıldı (kategoriler, danisma_kategorileri, sorular, cevaplar, M2M tablolar). Backend zaten veri bütünlüğünü sağladığı için lokal DB'de gereksiz kontroller kaldırıldı. `scheduler.js` PRAGMA foreign_keys komutları temizlendi.
2. **QR anında sync:** `server.js` POST `/api/oturum/gonder` endpoint'i güncellendi → `tamamlandi=true` olduğunda anında backend'e `POST /api/analytics/sessions/` yapılır (exponential backoff retry ile). Başarılı olursa outbox kaydı `gonderilme_tarihi` işaretlenir; başarısız olursa scheduler tekrar dener. `scheduler.js` `requestWithRetry` fonksiyonu export edildi.
3. **ConsultScreen visual temizlik:** `ConsultScreen.svelte` kategori ikonlarının altındaki conditional "X alt konu" badge kaldırıldı (lines 63-65). Alt kategori navigation yapısı (activeParent, selectParent, selectChild, backToParents) tamamen korundu; sadece görsel sayı gösterimi kaldırıldı.  
**Dosyalar:** `kiosk_edge/api-node/src/db.js`, `scheduler.js` (export requestWithRetry), `server.js` (immediate sync), `kiosk_edge/ui/src/components/ConsultScreen.svelte`  
**Doküman:** 03-kiosk-edge-api-node.md, 04-kiosk-edge-ui.md, 07-session-and-analytics.md güncellendi.  
**Test:** Container rebuild, sync success, 41 kategori + 6 danışma + 104 etken madde + 8 lookup başarıyla senkronize edildi.  
**Breaking:** Yok.

---

## 2026-07-01

### Kiosk UI — Normal Idle Ekranı Kaldırıldı + Bileşen Refactor
**Değişiklik:** Açılışta gelen "normal idle" bekleme ekranı kaldırıldı; uygulama artık doğrudan çekici (attractor) ekranla açılıyor. Tekrar eden parçalar bileşene çıkarıldı.  
**Detay:**
1. `IdleScreen.svelte` artık tek-durumlu attractor: açılışta anında gösterilir (10sn bekleme + iki-durumlu screensaver mantığı kaldırıldı). Reklam varsa görseller döner, yoksa `<AdPromo large />`. Eski `.screen-idle`/`.idle-*` markup ve CSS silindi.
2. `MediaView.svelte` (YENİ) — URL uzantısına göre `<video>`/`<img>` render eden ortak bileşen; AdStrip + IdleScreen kullanıyor (kopyalanan img/video mantığı tekilleştirildi).
3. `ScreenHeader.svelte` (YENİ) — Logo + opsiyonel subtitle; Welcome/Demographics/Category/Consult/Question ekranlarındaki tekrarlanan `kiosk-header` markup'ı bununla değiştirildi.  
**Dosyalar:** `IdleScreen.svelte`, `MediaView.svelte` (YENİ), `ScreenHeader.svelte` (YENİ), `AdStrip.svelte`, `Welcome/Category/Consult/Demographics/QuestionScreen.svelte`, `app.css` (ölü idle stilleri temizlendi)  
**Doküman:** 04-kiosk-edge-ui.md güncellendi.  
**Test:** ui 16/16 geçti; tarayıcıda doğrulandı.  
**Breaking:** Yok (idle screen state aynı; sadece görünüm/komponent yapısı değişti).

### Kiosk UI — Marka Logosu, Ortak AdPromo, Ekran Koruyucu Promosu, 20sn Inaktivite
**Değişiklik:** 4 UI iyileştirmesi yapıldı.  
**Detay:**
1. `Logo.svelte` (YENİ) + `assets/eisa-logo.svg` & `eisa-logo-light.svg` — tüm "e-İSA" yazıları resmi marka logosu ile değiştirildi (koyu zeminde beyaz varyant).
2. `AdPromo.svelte` (YENİ) — dönen "Bu Alana Reklam Verebilirsiniz" tasarımı ortak bileşene çıkarıldı; AdStrip (reklam yokken) ve IdleScreen ekran koruyucusunda (reklam yokken, `large`) kullanılıyor.
3. IdleScreen `ss-overlay-text` ekranın ÜSTÜNE konumlandırıldı; ekran koruyucu artık stok görseller yerine reklam yoksa AdPromo döndürüyor.
4. App.svelte global inaktivite `10s → 20s`; idle/wifi dışındaki HER ekranda 20sn işlemsizlikte idle'a döner (`finalizeAbandonedSession()` ile terk edilmiş oturum analitiği korunur).  
**Dosyalar:** `Logo.svelte`, `AdPromo.svelte`, `IdleScreen.svelte`, `AdStrip.svelte`, `App.svelte`, `Welcome/Category/Consult/Demographics/QuestionScreen.svelte`, `app.css`, `assets/eisa-logo*.svg`  
**Doküman:** 04-kiosk-edge-ui.md güncellendi.  
**Test:** ui 16/16 geçti.  
**Breaking:** Yok.

### Kiosk ↔ Backend DOOH Uyum Denetimi — TZ + Slot + Ölü Endpoint Düzeltmeleri
**Değişiklik:** Reklam gösterim mantığının backend ile uyumu denetlendi; 3 gerçek hata düzeltildi.  
**Hatalar:**
1. **Zaman dilimi (TZ):** Kiosk playlist'i UTC saatine göre seçiyordu; backend `target_hour` Istanbul yereli (USE_TZ, Europe/Istanbul) → reklamlar ~3 saat kayıyordu.
2. **Slot ölçeği:** `estimated_start_offset_seconds` saat-mutlak (0..3599) iken AdStrip slot döngüsü 60sn'e göre sarıyordu → sadece ilk dakikanın öğeleri oynuyor, PER_HOUR/PER_DAY reklamlar hiç görünmüyordu.
3. **Ölü endpoint:** `server.js` `/api/lookups/iller*` kaldırılmış SQLite tablolarını (db.js v9) sorguluyordu.  
**Dosyalar:**
- `kiosk_edge/api-node/src/timezone.js` (YENİ — `istanbulNow()`)
- `kiosk_edge/api-node/src/server.js` (`/api/playlist/current` Istanbul tarih/saat; ölü iller endpoint'leri kaldırıldı)
- `kiosk_edge/api-node/src/scheduler.js` (playlist çekme Istanbul tarihi)
- `kiosk_edge/ui/src/components/AdStrip.svelte` (slot döngüsü 3600sn; Istanbul saati ile yeniden yükleme; kullanılmayan `loopSeconds` kaldırıldı)  
**Doküman:** 08-dooh-advertising.md (Playlist/PlaylistItem/HouseAd/PlayLog modelleri, AdStrip örneği, sync aralıkları, TZ & Slot bölümü, çözülen riskler) gerçek kodla hizalandı.  
**Test:** api-node 30/30, ui 16/16 geçti.  
**Breaking:** Yok (davranış düzeltmesi; cihaz/konteyner TZ'sinden bağımsız çalışır).

### Kiosk Demo — Rancher/Kubernetes Manifest
**Değişiklik:** Birleşik kiosk container'ı demo.eisa.com.tr üzerinden yayınlamak için K8s manifest eklendi.  
**Dosyalar:** `deploy/eisa-kiosk-demo.yaml` (YENİ)  
**Kapsam:** Namespace + ConfigMap (EISA_ env'leri) + Deployment (ghcr.io/ysnzgl/eisa-kiosk:1.0.0, port 80) + Service (ClusterIP) + Ingress (traefik + cert-manager, demo.eisa.com.tr TLS).  
**Pattern:** `deploy/eisa-app-production.yaml` ile aynı konvansiyon.  
**Storage:** emptyDir (demo veri backend'den pull edilir); opsiyonel PVC örneği yorum olarak eklendi.  
**Breaking:** Yok.

### Kiosk Docker — Tek Container Birleştirme
**Değişiklik:** API Node ve UI tek container'da birleştirildi (önce ayrı 2 servisti).  
**Dosyalar:**
- `kiosk_edge/Dockerfile` (YENİ — birleşik multi-stage: ui-build + api-deps + runner)
- `kiosk_edge/.dockerignore` (YENİ)
- `kiosk_edge/docker-compose.demo.yml` (tek `kiosk` servisi, port 8080→80)
- `kiosk_edge/ui/src/lib/api.js` (`||` → `??` ki boş VITE_API_BASE relative path olsun)
- `kiosk_edge/README_DEMO_DOCKER.md` (birleşik mimari güncellendi)  
**Mimari:** Nginx (:80) UI static + `/api` proxy → Node (127.0.0.1:8765); supervisord ile 2 process.  
**Doküman:** 03-kiosk-edge-api-node.md, 04-kiosk-edge-ui.md Docker bölümleri güncellendi.  
**Breaking:** Yok (ilk versiyondaki ayrı `api-node/Dockerfile` ve `ui/Dockerfile` kaldırıldı; tek kök `Dockerfile` kullanılıyor).

### Kiosk IdleScreen Layout İyileştirmesi
**Değişiklik:** Bekleme ekranındaki logo ve ana içerik ortadan yukarıya taşındı.  
**Dosyalar:** `kiosk_edge/ui/src/app.css` (.screen-idle: `align-items: flex-start`, .idle-content: `margin-top: 80px`)  
**Etki:** Daha dengeli görsel yerleşim, alt banner için daha fazla alan.

### Kiosk Docker Deployment (Demo)
**Değişiklik:** demo.eisa.com.tr için Docker yapısı oluşturuldu. Gerçek kiosk deployment'ında kullanılmaz.  
**Not:** İlk versiyonda ayrı `api-node/Dockerfile` + `ui/Dockerfile` vardı; sonradan tek kök `Dockerfile`'a birleştirildi (üstteki kayıt).  
**Dosyalar:**
- `kiosk_edge/docker-compose.demo.yml` (demo compose)
- `kiosk_edge/.env.demo` (environment variables)
- `kiosk_edge/README_DEMO_DOCKER.md` (deployment guide)
- `kiosk_edge/ui/.env.example` (VITE_API_BASE konfigürasyonu)
- `kiosk_edge/ui/src/lib/api.js` (API_BASE configurable: `import.meta.env.VITE_API_BASE`)  
**Doküman:** 03-kiosk-edge-api-node.md, 04-kiosk-edge-ui.md güncellenmiş (Docker Deployment bölümü eklendi).  
**Breaking:** Yok.

---

## 2026-06-05

### Danışma Tamamlama Akışı Uygulanması
**Değişiklik:** Backend'e pharmacist-side consultation completion endpoint eklendi. Yeni DB alanları: `danisma_tamamlandi`, `danisma_tamamlanma_tarihi`, `danisma_notu`, `danisma_tamamlayan_eczaci`.  
**Dosyalar:** `backend/apps/analytics/views.py` (OturumLoguCompleteView), `models.py` (4 yeni alan), `serializers.py` (yeni alanlar), `urls.py` (endpoint path); `web_panels/src/views/pharmacist/QrScan.vue` (completion UI), `services/analytics.js` (completeSession helper).  
**Migration:** `0005_oturumlogu_danisma_notu_and_more.py`  
**Endpoint:** `POST /api/analytics/sessions/{id}/complete/` (eczacı-only, pharmacy ownership enforced, idempotent).  
**Doküman:** `07-session-and-analytics.md`, `06-db-and-api-contracts.md` güncellenmiş.  
**Breaking:** Yok.

### İlk Dokümantasyon Seti Oluşturuldu
**Dosyalar:** 00-AI-INDEX.md, 01-backend.md, 02-web-panels.md, 03-kiosk-edge-api-node.md, 04-kiosk-edge-ui.md, 05-cross-project-flows.md, 06-db-and-api-contracts.md  
**Amaç:** Token-ekonomik AI context  
**Kapsam:** Backend/frontend/kiosk modülleri, kritik akışlar, API contract'ları, belirsiz/riskli alanlar

### Optimization Pass — Context Quality
**Güncellenen:** Tüm mevcut dokümanlar  
**Eklenen bölümler:** "When To Read This File", "Important Source Files", "Do Not Change Without Checking"  
**Yeni dosyalar:** 07-session-and-analytics.md, 08-dooh-advertising.md, AI-WORKFLOW.md, AI-RULES.md  
**Etki:** Daha hızlı context bulma, tekrar azaltma, kritik contract koruması

**Önemli bulgular:**
- DOOH v2 playlist mimarisi (60sn pre-computed)
- Offline-first kiosk (SQLite + outbox)
- Dual authentication (App-Key+MAC / IoT Token)
- Legacy Campaign.target_pharmacies + yeni CampaignTarget (belirsiz priority)
- Outbox pressure kontrolü (tam dolunca ne olur belirsiz)
- Session idempotency (backend impl doğrulanmalı)
- QR collision riski (unique constraint yok)
- Media cache placeholder

---

## Gelecek Kayıtlar

**Format örneği (max 10 satır):**

```
## YYYY-MM-DD

### [Modül] — Değişiklik Başlığı
**Değişiklik:** ...  
**Dosyalar:** ...  
**Etki:** ...  
**Breaking:** Var/Yok  
**Doküman:** Güncellendi/Eklendi
```

---

**Not:** Bu dosya AI tarafından otomatik güncellenir.

