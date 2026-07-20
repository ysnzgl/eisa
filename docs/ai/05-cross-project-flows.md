# Cross-Project Flows — Backend ↔ web_panels ↔ kiosk_edge

**Amaç:** Proje bileşenleri arasındaki kritik veri akışlarını kompakt şekilde dokümante etmek.

---

## When To Read This File

- Proje arası veri akışı sorunlarında
- End-to-end feature geliştirirken
- Senkronizasyon problemlerinde
- Integration test senaryoları için
- Yeni akış eklerken

---

## 6. Teknik Log Akışı *(2026-07-16)*

Uygulama operasyonel logları PostgreSQL'e yazılmaz; standart JSON stdout üzerinden Kubernetes node collector'a (ileride Alloy/Loki) gider.

### 6.1 Kiosk Diagnostic Outbox → Backend
```
kiosk_edge/api-node (WARN/ERROR/CRITICAL event)
  → SQLite diagnostic_outbox (bounded: 5000 satir, 7 gun, FIFO)
  → scheduler.pushDiagnostics (varsayilan 120 sn)
  → POST /api/kiosk/v1/diagnostics/  { items: [{level, event, message, context, correlation_id, occurred_at}] }
    Header: Authorization: AppKey <app_key> + X-Kiosk-MAC + X-Correlation-ID
  → Backend: kiosk auth + rate limit + allow-list; sanitize eder; DB'ye YAZMAZ
  → Backend: JSON log stdout (`logger=eisa.kiosk.diagnostic`)
  → Response 202 { accepted, rejected, errors, accepted_keys } → outbox kayitlari silinir
```

### 6.2 Vue Panel Kritik Hata → Backend
```
web_panels (app.config.errorHandler / window.onerror / unhandledrejection)
  → src/lib/logger.js: prod'da WARNING+ islenir
  → POST /api/analytics/client-events/  { items: [{level, event, message, stack, component, route, correlation_id}] }
    JWT httpOnly cookie; rate limit 30/min (scope=client_event); allow-list
  → Backend: sanitize; DB'ye YAZMAZ; JSON log stdout (`logger=eisa.client`)
```

### 6.3 Svelte UI Kritik Hata → Fastify → Backend
```
kiosk_edge/ui (window.onerror / unhandledrejection / operational event)
  → src/lib/logger.js: yalnizca izin verilen event kodlari
  → POST http://127.0.0.1:8765/api/log/client
  → Fastify: JSON log stdout + diagnostic_outbox'a ekler
  → (yukaridaki 6.1 akisiyla merkeze iletir)
```

### Correlation ID
Tum akislarda `X-Correlation-ID` basligi tasinir; backend uretir veya guvenli girisi kabul eder, response'a geri yazar. Panel/kiosk axios/fetch response'daki degeri yakalayip sonraki hata bildirimlerine ekler.

---

## 0. Kiosk Provisioning (Onay) Akışı *(2026-07-14)*

### kiosk_edge → Backend → web_panels → Backend → kiosk_edge

**0.1. Kayıtsız Cihaz Bootstrap İsteği**
```
kiosk_edge/api-node (provisioning.js: resolveRuntimeSettings)
  → POST /api/kiosk/v1/bootstrap/
    Header: X-Kiosk-Key: <fleet_key>
    Body: { "mac_adresi": "AA:BB:CC:DD:EE:FF", "timestamp": "...", "hmac": "..." }
  → Backend: fleet_key + HMAC doğrulama
  → Kiosk bulunamadı → KioskProvisioningRequest PENDING kaydı oluştur
  → Response 202: { "status": "PENDING", "registration_id": "uuid", "retry_after_seconds": 30 }
  → kiosk_edge: provisioning_state = 'PENDING_APPROVAL', registration_id kaydedilir
```

**0.2. Admin Onay Ekranı**
```
SuperAdmin (web_panels/PendingDevices.vue)
  → GET /api/pharmacies/kiosks/provisioning/?status=PENDING
  → Backend: KioskProvisioningRequest listesi
  → Admin eczane + kiosk adı seçer
  → POST /api/pharmacies/kiosks/provisioning/{id}/approve/
    { "eczane_id": 1, "ad": "Kiosk 1" }
  → Backend transaction:
    1. SELECT FOR UPDATE (race condition koruması)
    2. Kiosk oluşturulur (uygulama_anahtari otomatik)
    3. KioskProvisioningRequest → APPROVED, kiosk FK bağlanır
  → Response 200: approved request detayı
```

**0.3. Onaylanmış Cihaz Bootstrap**
```
kiosk_edge/api-node (provisioning.js: resolveRuntimeSettings, açılışta/scheduler döngüsünde)
  → POST /api/kiosk/v1/bootstrap/ (aynı credentials)
  → Backend: MAC ile Kiosk bulunur (artık kayıtlı, aktif, eczaneli)
  → Response 200: { "status": "APPROVED", "kiosk_id": 1, "pharmacy_id": 1, "app_key": "..." }
  → kiosk_edge: app_key + kiosk_id + pharmacy_id SQLite kiosk_meta'ya yazılır, provisioning_state = 'APPROVED'
  → Operasyonel çağrılar Authorization: AppKey + X-Kiosk-MAC ile başlar
```

**0.4. Reddedilen Cihaz**
```
SuperAdmin → POST /api/pharmacies/kiosks/provisioning/{id}/reject/
  → Backend: status = REJECTED
  → Cihaz tekrar bootstrap → 403 { "status": "REJECTED" }
  → kiosk_edge: provisioning_state = 'REJECTED', normal API çağrıları engellenir
```

---

## 1. Kategori Akışı

### Backend → web_panels → Backend → kiosk_edge/api-node → kiosk_edge/ui

**1.1. Kategori Tanımlama (SuperAdmin)**
```
SuperAdmin (web_panels)
  → POST /api/products/kategoriler/
    {
      "ad": "Uyku Sorunu",
      "slug": "uyku-sorunu",
      "ikon": "fa-bed",
      "hedef_cinsiyet_id": null,
      "hedef_yas_araliklari": [2, 3, 4],
      "bagli_kategori_id": null,
      "aktif": true
    }
  → Backend: Kategori model kaydı
```

**1.2. Soru Tanımlama (SuperAdmin)**
```
SuperAdmin (web_panels)
  → POST /api/products/sorular/
    {
      "kategori_id": 5,
      "metin": "Uykuya dalmakta zorluk çekiyor musunuz?",
      "sira": 1,
      "hedef_cinsiyet_id": null,
      "hedef_yas_araliklari": [],
      "hedef_etken_maddeler": []
    }
  → Backend: Soru model kaydı
```

**1.3. Kiosk Senkronizasyonu**
```
kiosk_edge/api-node (scheduler: pullFromCentral, her 5dk)
  → GET /api/kiosk/v1/catalog/
  → Backend: Kategori.objects.filter(aktif=True) + Soru + Cevap + EtkenMadde
  → Response JSON:
    {
      "kategoriler": [...],
      "sorular": [...],
      "cevaplar": [...],
      "etken_maddeler": [...]
    }
  → kiosk_edge/api-node: SQLite upsert (kategoriler, sorular, cevaplar, etken_maddeler)
```

**1.4. Kiosk UI Gösterimi**
```
kiosk_edge/ui (CategoryScreen)
  → GET http://localhost:5234/categories
  → kiosk_edge/api-node: SQLite query (hedef_cinsiyet + hedef_yas_araliklari filtreleme)
  → Response JSON: [...kategoriler]
  → kiosk_edge/ui: Grid gösterimi
```

---

## 2. Reklam Slot Akışı

### Backend (Kampanya + Playlist) → kiosk_edge → Backend (Proof-of-Play)

**2.1. Kampanya Oluşturma (SuperAdmin)**
```
SuperAdmin (web_panels/CampaignWizard)
  → POST /api/campaigns/v2/campaigns/
    {
      "name": "Vitamin C Kampanyası",
      "advertiser_name": "XYZ Pharma",
      "start_date": "2026-06-01T00:00:00Z",
      "end_date": "2026-06-30T23:59:59Z",
      "priority": 50,
      "is_guaranteed": false,
      "impression_goal": 10000,
      "frequency_cap_per_hour": 2
    }
  → Backend: Campaign model kaydı
```

**2.2. Creative Upload (SuperAdmin)**
```
SuperAdmin (web_panels/CampaignWizard)
  → POST /api/campaigns/upload-media/ (multipart/form-data: file)
  → Backend: MinIO/S3 upload → media_url
  → POST /api/campaigns/v2/creatives/
    {
      "campaign_id": "uuid",
      "media_url": "https://cdn.example.com/creative.mp4",
      "duration_seconds": 15,
      "name": "Vitamin C 15s"
    }
  → Backend: Creative model kaydı
```

**2.3. ScheduleRule Tanımlama (SuperAdmin)**
```
SuperAdmin (web_panels/CampaignWizard)
  → POST /api/campaigns/v2/campaigns/{id}/rules/
    {
      "frequency_type": "PER_HOUR",
      "frequency_value": 2,
      "target_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
    }
  → Backend: ScheduleRule model kaydı
```

**2.4. Playlist Üretimi (Backend Scheduler)**
```
Backend (django_apscheduler job, her gece veya manuel)
  → services/scheduler.py: generate_for_kiosk(date, kiosk_id)
  → Slot hesaplama: 60sn loop, campaign priority/guaranteed/frequency kontrolü
  → Playlist + PlaylistItem oluşturma
  → Backend DB: Playlist model kaydı (target_date, target_hour, version, items JSON)
```

**2.5. Kiosk Playlist Senkronizasyonu**
```
kiosk_edge/api-node (scheduler: pingAndSyncPlaylist, her 10dk)
  → GET /api/kiosk/v1/ping/
  → Backend: { "playlist_version": 42 }
  → kiosk_edge/api-node: Lokal version kontrolü (SQLite kiosk_meta.playlist_version)
  → Eğer farklıysa:
    → GET /api/kiosk/v1/playlist/?date=2026-06-05
    → Backend: Playlist + PlaylistItem JSON
    → kiosk_edge/api-node: SQLite upsert (playlists, playlist_items)
```

**2.6. Kiosk UI Oynatımı**
```
kiosk_edge/ui (AdStrip component)
  → GET http://localhost:5234/playlist?date=2026-06-05
  → kiosk_edge/api-node: SQLite query
  → Response JSON:
    {
      "id": "uuid",
      "items": [
        {
          "asset_type": "creative",
          "asset_id": "uuid",
          "media_url": "https://cdn.example.com/creative.mp4",
          "duration_seconds": 15,
          "playback_order": 1
        },
        ...
      ]
    }
  → kiosk_edge/ui: 60sn döngü oynatımı (sırayla creative/house_ad)
```

---

## 3. Reklam Impression / Play Log Akışı

### kiosk_edge/ui → kiosk_edge/api-node → Backend

**3.1. Impression Kaydı (Kiosk UI)**
```
kiosk_edge/ui (AdStrip)
  → Reklam slotu gösterilir → shownAt = ISO timestamp
  → Slot değişince → duration_played = (now - shownAt) saniye
  → POST http://127.0.0.1:8765/api/reklam-gosterim
    {
      "asset_id": "uuid",
      "asset_type": "creative",
      "played_at": "2026-06-05T10:30:00.000Z",
      "duration_played": 15
    }
  → kiosk_edge/api-node: SQLite insert (reklam_gosterim_outbox)
```

**3.2. Outbox Push (Kiosk Edge Scheduler)**
```
kiosk_edge/api-node (scheduler: pushToCentral, her ~5dk)
  → SQLite query: SELECT * FROM reklam_gosterim_outbox WHERE gonderilme_tarihi IS NULL
  → Batch payload (asset_type'a göre creative_id / house_ad_id):
    {
      "logs": [
        {
          "creative_id": "uuid",
          "played_at": "2026-06-05T10:30:00.000Z",
          "duration_played": 15
        }
      ]
    }
  → POST /api/kiosk/v1/proof-of-play/
  → Backend: PlayLog bulk insert
  → kiosk_edge/api-node: UPDATE reklam_gosterim_outbox SET gonderilme_tarihi = NOW() WHERE id IN (...)
```

**3.3. Raporlama (SuperAdmin)**
```
SuperAdmin (web_panels/Dashboard)
  → GET /api/analytics/play-logs/?campaign={id}&start_date=2026-06-01&end_date=2026-06-30
  → Backend: PlayLog.objects.filter(...).aggregate(total_impressions, completed_impressions)
  → Response: { "total": 8500, "completed": 8200, "completion_rate": 0.96 }
```

---

## 4. Kullanıcı Interaction / Session Log Akışı

### kiosk_edge/ui → kiosk_edge/api-node → Backend → web_panels

**4.1. Session Başlangıcı (Kiosk UI)**
```
kiosk_edge/ui (App.svelte)
  → Kategori seçimi → sessionId = uuid() (lokal state)
  → Inactivity timer başlat (10sn)
```

**4.2. Session Tamamlanma (Kiosk UI) — Updated 2026-07-20**
```
kiosk_edge/ui (App.svelte)
  → Kullanıcı tüm soruları cevapladı
  → POST http://localhost:5234/api/oturum/gonder
    {
      "idempotency_anahtari": "uuid",   ← edge üretir
      "oturum_tipi": "SIKAYET" | "OZEL_DANISMANLIK",
      "yas_araligi_kod": "26-35",
      "cinsiyet_kod": "M",
      "kategori_slug": "uyku",          ← SIKAYET için
      "danisma_kategorisi_slug": null,   ← DANISMANLIK için
      "hassas_akis": false,
      "cevaplar": { soru_id: cevap_id },
      "onerilen_etken_maddeler": [etken_madde_id],
      "tamamlandi": true
      // qr_kodu gönderilmez — backend üretir
    }
  → kiosk_edge/api-node: backend'e SYNC ilet
  → Backend: QR üret (8 char [A-Z0-9], unique, IntegrityError retry)
  → Backend response: { results: [{ idempotency_key, status, qr_kodu }] }
  → Edge: outbox'a backend QR ile kaydet → UI'a { qr_kodu } döndür
  → UI: Backend QR göster (sahte/fallback QR yok)
  → Backend erişilemez: Edge 503 döner, UI retry gösterir
```

**4.3. Danışmanlık Session (DANISMANLIK) — New 2026-07-20**
```
Akış: CategoryScreen → ConsultScreen → danisma kategorisi seç
  → oturum_tipi=DANISMANLIK, danisma_kategorisi_slug=... , kategori_slug=null
  → Backend: OturumLogu.danisma_kategorisi = Danisma FK; kategori=None
  → Eczacı paneli: danisma_kategorisi_detay.ad gösterilir
```

**4.4. Session Terk Edilmesi (Kiosk UI)**
```
kiosk_edge/ui (App.svelte: onInactivityTimeout)
  → 20sn (INACTIVITY_MS = 20_000) cevap verilmedi → session finalize
  → POST http://localhost:5234/api/oturum/gonder
    { ..., "tamamlandi": false }
  → kiosk_edge/api-node: SQLite insert (outbox, QR yok)
  → Background'da backend'e gönder; hata olursa scheduler tekrar dener
```

**4.5. Outbox Push (Kiosk Edge Scheduler)**
```
kiosk_edge/api-node (scheduler: pushOutbox, her 1dk)
  → SQLite query: SELECT * FROM oturum_outbox WHERE gonderilme_tarihi IS NULL
  → Batch payload:
    {
      "sessions": [
        {
          "idempotency_key": "uuid",
          "yas_araligi_id": 2,
          ...
        },
        ...
      ]
    }
  → POST /api/kiosk/v1/sessions/
  → Backend: OturumLogu bulk get_or_create (idempotency_anahtari ile duplikasyon koruması)
  → kiosk_edge/api-node: UPDATE oturum_outbox SET gonderilme_tarihi = NOW() WHERE id IN (...)
```

**4.5. QR Tarama (Eczacı — web_panels)**
```
Eczacı (web_panels/QrScan)
  → Fiziksel barkod okuyucu ile input'a 8 karakter QR yazılır + Enter
  → GET /api/analytics/sessions/?qr_kodu=A1B2C3D4
  → Backend: QR format doğrulama + sahiplik kontrolü + OturumLogu detay response
  → Response:
    {
      "id": "uuid",
      "kiosk": { ... },
      "yas_araligi": "25-34",
      "cinsiyet": "Kadın",
      "kategori": "Uyku Sorunu",
      "cevaplar": { ... },
      "onerilen_etken_maddeler": ["Melatonin", "Valerian"],
      "tamamlandi": true,
      "olusturulma_tarihi": "2026-06-05T10:30:00Z"
    }
  → web_panels: Modal gösterimi
```

---

## 5. QR Tamamlanma Akışı

### kiosk_edge/ui (QR üretimi) → web_panels (QR tarama)

**5.1. QR Üretimi (Kiosk UI — ResultScreen)**
```
kiosk_edge/ui (ResultScreen.svelte)
  → QR kodu string: 8 karakter Base36 (0-9A-Z)
  → qr-creator library: QR kod canvas'a render
  → Ekranda gösterim: "Eczaciniza bu QR kodu okutunuz"
  → Session log (4.2'deki gibi) → qr_kodu alanı ile kaydedilir
```

**5.2. QR Tarama (Eczacı — web_panels QrScan)**
```
Eczacı (web_panels/QrScan.vue)
  → Kamera kullanılmaz; yalnız input + Enter akışı vardır
  → qr_kodu = "A1B2C3D4" → trim (case dönüştürme yok)
  → GET /api/analytics/sessions/?qr_kodu={qr_kodu}
  → Backend: OturumLogu lookup
  → Modal: Session detayı + önerilen etken maddeler
  → (Belirsiz: Danışmanlık sonuçlandırma endpoint'i yok gibi)
```

**5.3. Danışmanlık Sonuçlandırma (Eczacı)**
```
(Belirsiz / mevcut değil)
Eczacı → session detayı görüntüleme sonrası:
  → Danışmanlık notları ekleyebilir mi?
  → Session durumu güncelleme (completed → consulted)?
  → Backend'de endpoint yok gibi görünüyor, geliştirme gerekebilir.
```

---

## Do Not Change Without Checking

**Critical cross-project data flows:**

1. **Kategori Sync Chain:**
  - Backend models → `/api/kiosk/v1/sync/` → kiosk_edge SQLite → kiosk UI
   - Breaking: kategori filtering/display fails

2. **Playlist Generation Flow:**
   - Campaign/Creative/ScheduleRule → scheduler.py → Playlist/PlaylistItem → kiosk sync
   - Breaking: no ads display

3. **Session Log Chain:**
   - kiosk UI → lokal API → outbox → backend sync → OturumLogu
   - Breaking: session data loss

4. **Proof-of-Play Chain:**
   - kiosk UI AdStrip → lokal API → outbox → backend sync → PlayLog
   - Breaking: impression tracking loss

5. **QR Lifecycle:**
   - kiosk UI (generate) → session log → backend → web_panels QrScan
   - Breaking: QR scanning fails

---

## Kritik Noktalar

1. **Kategori filtreleme:** Backend + kiosk_edge/api-node + kiosk_edge/ui 3 katmanda da hedef_cinsiyet/hedef_yas_araliklari kontrolü yapılıyor. Tutarlılık önemli.
2. **Playlist versioning:** Backend playlist ürettiğinde version artırır, kiosk ping ile kontrol eder. Version mismatch → yeniden indir.
3. **Outbox pattern:** Session ve impression logları lokal toplanır, batch push edilir. Internet kesilirse queue birikir, outbox pressure kontrolü var.
4. **Idempotency:** Session log için `idempotency_anahtari` (UUID), duplikasyon koruması. Backend `get_or_create` kullanmalı.
5. **QR collision riski:** `"EISA-" + timestamp + random` → teorik collision riski düşük ama garantisi yok. Backend unique constraint olmalı.

---

**Satır sayısı: ~250**
