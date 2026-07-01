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
  → GET /api/kiosk/v1/{kiosk_id}/sync/
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
  → GET /api/kiosk/v1/{kiosk_id}/ping/
  → Backend: { "playlist_version": 42 }
  → kiosk_edge/api-node: Lokal version kontrolü (SQLite kiosk_meta.playlist_version)
  → Eğer farklıysa:
    → GET /api/kiosk/v1/{kiosk_id}/playlist/?date=2026-06-05
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
  → POST /api/kiosk/v1/{kiosk_id}/proof-of-play/
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

**4.2. Session Tamamlanma (Kiosk UI)**
```
kiosk_edge/ui (ResultScreen)
  → Kullanıcı tüm soruları cevapladı → QR üretildi
  → POST http://localhost:5234/sessions
    {
      "idempotency_key": "uuid",
      "yas_araligi_id": 2,
      "cinsiyet_id": 1,
      "kategori_id": 5,
      "hassas_akis": false,
      "qr_kodu": "EISA-1717592400-A3F8D2E1",
      "cevaplar": { "soru_1": "cevap_1", ... },
      "onerilen_etken_maddeler": ["Melatonin", "Valerian"],
      "tamamlandi": true
    }
  → kiosk_edge/api-node: SQLite insert (oturum_outbox)
```

**4.3. Session Terk Edilmesi (Kiosk UI)**
```
kiosk_edge/ui (App.svelte: onInactivityTimeout)
  → 10sn cevap verilmedi → session finalize
  → POST http://localhost:5234/sessions
    { ..., "tamamlandi": false }
  → kiosk_edge/api-node: SQLite insert (oturum_outbox)
```

**4.4. Outbox Push (Kiosk Edge Scheduler)**
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
  → POST /api/kiosk/v1/{kiosk_id}/sync/
  → Backend: OturumLogu bulk get_or_create (idempotency_anahtari ile duplikasyon koruması)
  → kiosk_edge/api-node: UPDATE oturum_outbox SET gonderilme_tarihi = NOW() WHERE id IN (...)
```

**4.5. QR Tarama (Eczacı — web_panels)**
```
Eczacı (web_panels/QrScan)
  → QR okutma → qr_kodu = "EISA-1717592400-A3F8D2E1"
  → GET /api/pharmacies/sessions/?qr=EISA-1717592400-A3F8D2E1
  → Backend: OturumLogu.objects.filter(qr_kodu=qr)
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
  → QR kodu string: "EISA-" + timestamp + "-" + randomHex(8)
  → qr-creator library: QR kod canvas'a render
  → Ekranda gösterim: "Eczaciniza bu QR kodu okutunuz"
  → Session log (4.2'deki gibi) → qr_kodu alanı ile kaydedilir
```

**5.2. QR Tarama (Eczacı — web_panels QrScan)**
```
Eczacı (web_panels/QrScan.vue)
  → Kamera ile QR okutma (HTML5 getUserMedia + canvas)
  → veya manuel QR kodu girişi (input field)
  → qr_kodu = "EISA-1717592400-A3F8D2E1" → trim, uppercase
  → GET /api/pharmacies/sessions/?qr={qr_kodu}
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
   - Backend models → `/api/kiosk/v1/{id}/sync/` → kiosk_edge SQLite → kiosk UI
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
