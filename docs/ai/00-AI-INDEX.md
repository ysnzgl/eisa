# AI Context Index — E-İSA Project

**Son güncelleme:** 2026-06-05  
**Amaç:** Token-ekonomik AI context; kod yapısını hızlı anlamak ve geliştirmelerde doğru noktadan başlamak.

---

## When To Read This File

- İlk kez projeye başlarken (genel bakış)
- Hangi dokümanı okuyacağına karar verirken
- Modüller arası ilişkiyi anlamak için
- Yeni özellik eklemeden önce (başlangıç noktası)

---

## Proje Özeti

**E-İSA (E-İlaç Sepeti Asistanı):** Eczanelerde konumlanmış kiosk'lar üzerinden demografik/anonim kullanıcı danışmanlığı ve DOOH (Digital Out-Of-Home) reklam sistemi.

**Temel akış:**  
Kullanıcı → Demografi seçimi → Kategori seçimi → Sorulara cevap → Etken madde önerileri + QR kod → Eczacıya danışma  
**Reklam akışı:**  
Backend'de kampanya/creative tanımı → Merkezi playlist üretimi → Kiosk'a senkronizasyon → Offline oynatım → Proof-of-play log toplama

---

## Modül Listesi

| Modül | Teknoloji | Rol | Dosya |
|-------|-----------|-----|-------|
| `backend` | Django 5 + DRF + PostgreSQL | Merkezi API, kampanya/creative/playlist yönetimi, kullanıcı/eczane/ürün veritabanı | [01-backend.md](01-backend.md) |
| `web_panels` | Vue 3 + Vite + Pinia + Vue Router | Admin/Pharmacist paneli, kampanya/playlist/fiyat/kullanıcı/cihaz yönetimi | [02-web-panels.md](02-web-panels.md) |
| `kiosk_edge/api-node` | Node.js + Fastify + SQLite | Kiosk'taki lokal API servisi, offline-first, backend senkronizasyonu, QR üretimi | [03-kiosk-edge-api-node.md](03-kiosk-edge-api-node.md) |
| `kiosk_edge/ui` | Svelte 5 | Kiosk kullanıcı arayüzü, kategori/soru akışı, QR gösterimi, reklam oynatımı | [04-kiosk-edge-ui.md](04-kiosk-edge-ui.md) |

---

## Domain-Specific Docs

| Konu | Dosya |
|------|-------|
| **Session/Analytics** | [07-session-and-analytics.md](07-session-and-analytics.md) — Session lifecycle, QR, idempotency, analytics |
| **DOOH Advertising** | [08-dooh-advertising.md](08-dooh-advertising.md) — Campaign, playlist, slot calculation, proof-of-play |
| **Cross-Project Flows** | [05-cross-project-flows.md](05-cross-project-flows.md) — Proje arası veri akışları |
| **API Contracts** | [06-db-and-api-contracts.md](06-db-and-api-contracts.md) — DB schema, API endpoints, frontend/backend contracts |

---

## AI Guidance Docs

| Konu | Dosya |
|------|-------|
| **Workflow** | [AI-WORKFLOW.md](AI-WORKFLOW.md) — Yeni özellik/bug fix prosedürleri |
| **Rules** | [AI-RULES.md](AI-RULES.md) — Kalıcı davranış kuralları |
| **Changelog** | [99-ai-changelog.md](99-ai-changelog.md) — Değişiklik kaydı |

---

## Hangi İş İçin Hangi Dokümana Bakılacağı

| Görev | Doküman |
|-------|---------|
| Yeni kampanya/creative ekleme | 08-dooh-advertising.md + 01-backend.md + 02-web-panels.md |
| Playlist üretim/scheduler mantığı | 08-dooh-advertising.md + 01-backend.md |
| Session/log akışı | 07-session-and-analytics.md + 04-kiosk-edge-ui.md |
| QR kod üretimi/tarama | 07-session-and-analytics.md + 04-kiosk-edge-ui.md + 02-web-panels.md |
| Proof-of-play log toplama | 08-dooh-advertising.md + 03-kiosk-edge-api-node.md |
| Kiosk'a yeni kategori/soru ekleme | 01-backend.md + 03-kiosk-edge-api-node.md |
| Frontend/backend API contract | 06-db-and-api-contracts.md |
| Proje arası veri akışları | 05-cross-project-flows.md |
| Yeni özellik ekleme prosedürü | AI-WORKFLOW.md |
| Bug düzeltme prosedürü | AI-WORKFLOW.md + AI-RULES.md |

---

## Ana Veri Akışları

### 1. Kategori/Soru Akışı
Backend (Kategori/Soru models) → web_panels (MedicalLogic/DanismaYonetimi) → Backend API → kiosk_edge/api-node (sync scheduler) → SQLite (kategoriler/sorular) → kiosk_edge/ui (CategoryScreen/QuestionScreen)

### 2. Reklam Slot/Playlist Akışı
Backend (Campaign/Creative/ScheduleRule) → web_panels (CampaignWizard/PlaylistEditor) → Backend playlist generator → Kiosk ping → kiosk_edge/api-node playlist sync → SQLite (playlists/playlist_items) → kiosk_edge/ui (AdStrip)

### 3. Kullanıcı Session/Log Akışı
kiosk_edge/ui (App.svelte session) → kiosk_edge/api-node (POST /sessions) → oturum_outbox → Backend (POST /api/kiosk/v1/{id}/sync/) → OturumLogu model

### 4. Proof-of-Play Log Akışı
kiosk_edge/ui (AdStrip impressions) → kiosk_edge/api-node (POST /ad-impressions) → reklam_gosterim_outbox → Backend (POST /api/kiosk/v1/{id}/proof-of-play/) → PlayLog model

### 5. QR Tamamlanma Akışı
kiosk_edge/ui (ResultScreen QR) → web_panels (QrScan) → Backend API (GET /api/pharmacies/sessions/) → OturumLogu fetch

---

## Kritik Domain Kavramları

- **Kategori:** Kullanıcının yakındığı şikayet türü (uyku, enerji, bağışıklık vb.)
- **Soru:** Kategoriye bağlı, hedeflenmiş sorular (yaş/cinsiyet/etken madde filtrelenebilir)
- **Danışma:** Eczacıya direkt danışma kategorisi (soru akışı gerektirmez)
- **Campaign:** DOOH reklam kampanyası (başlangıç/bitiş tarihi, durum, öncelik, garanti tipi)
- **Creative:** Kampanyaya ait medya (görsel/video URL + süre)
- **ScheduleRule:** Kampanya frekans matrisi (per_loop/per_hour/per_day, saat hedefleme)
- **Playlist:** Kiosk için üretilmiş 60sn reklam döngüsü (date/hour bazlı)
- **HouseAd:** Filler reklam (slot boşsa oynatılır)
- **OturumLogu:** KVKK uyumlu anonim kullanıcı session (yaş aralığı, cinsiyet, kategori, QR kodu, tamamlanma durumu)
- **PlayLog:** Reklam gösterim kanıtı (creative_id, play_started, play_ended, completed)
- **Kiosk:** Fiziksel cihaz (mac_adresi, uygulama_anahtari, eczane, aktif/online durumu)
- **Eczane:** Kiosk'un bulunduğu fiziksel lokasyon (il/ilçe, sahip, telefon)

---

## Güncel Olmayan / Şüpheli Alanlar

1. **Legacy M2M:** `Campaign.target_pharmacies` (M2M) -> Yeni kampanyalar `CampaignTarget` kullanıyor (Il/Ilce/Eczane hiyerarşisi). Eski kayıtlar varsa ikisi de destekleniyor, belirsiz.
2. **Kiosk authentication:** `KioskAppKeyAuthentication` ve `KioskIoTTokenAuthentication` — iki auth mekanizması mevcut. Hangisinin ne zaman kullanıldığı net değil. (Belirsiz / doğrulanmalı)
3. **Offline outbox pressure:** `reklam_gosterim_outbox` ve `oturum_outbox` tablolarında kapasite kontrolü var ama tam dolunca ne olur? Log kaybı mı, overwrite mi? (Belirsiz)
4. **Playlist generation job:** `GenerationJob` modeli ve async task yapısı mevcut ama `django_apscheduler` kullanımı ve job durumu takibi net değil. (Belirsiz)
5. **WiFi setup:** `kiosk_edge/ui` içinde `WifiSetupScreen` var ama `kiosk_edge/api-node` içinde `nmcli` (NetworkManager CLI) çağrıları yapılıyor. Bu Linux'a özel, geliştirme ortamında çalışmaz. (Belirsiz / doğrulanmalı)
6. **Media cache invalidation:** `Creative.checksum` alanı var ama kiosk tarafında cache invalidation mantığı tam açık değil. (Belirsiz)
7. **Session idempotency:** `OturumLogu.idempotency_anahtari` var ama kiosk_edge/api-node'da bu anahtar nasıl üretiliyor ve duplikasyon kontrolü tam çalışıyor mu? (Belirsiz)

---

## Bundan SoDoküman Okuma Sırası |
|---------|---------------------|
| **İlk kez proje** | 00-AI-INDEX.md → AI-WORKFLOW.md → AI-RULES.md → ilgili modül dokümanı |
| **Yeni kategori eklemek** | 00-AI-INDEX.md → 01-backend.md → 03-kiosk-edge-api-node.md → gerçek kod |
| **Yeni kampanya oluşturmak** | 00-AI-INDEX.md → 08-dooh-advertising.md → 01-backend.md → 02-web-panels.md |
| **Playlist üretimini düzenlemek** | 08-dooh-advertising.md → 01-backend.md (scheduler.py) → 05-cross-project-flows.md |
| **Kiosk senkronizasyonunu debug etmek** | 03-kiosk-edge-api-node.md → 01-backend.md → 05-cross-project-flows.md |
| **QR akışını değiştirmek** | 07-session-and-analytics.md → 04-kiosk-edge-ui.md → 02-web-panels.md |
| **Session log analizini eklemek** | 07-session-and-analytics.md → 01-backend.md → 02-web-panels.md |
| **Proof-of-play raporunu genişletmek** | 08-dooh-advertising.md → 06-db-and-api-contracts.md → 01-backend.md |
| **Offline davranışını ayarlamak** | 03-kiosk-edge-api-node.md → 04-kiosk-edge-ui.md |
| **API contract değiştirmek** | AI-WORKFLOW.md → 06-db-and-api-contracts.md → ilgili modül dokümanları |
| **Bug düzeltmek** | AI-WORKFLOW.md → ilgili flow dokümanı (05/07/08) → gerçek kodashboard analytics) |
| Proof-of-play raporunu genişletmek | 01-backend.md (PlayLog) → 06-db-and-api-contracts.md |
| Offline davranışını ayarlamak | 03-kiosk-edge-api-node.md (SQLite schema/outbox) |

---

**Not:** Bu indeks dosyası maksimum 200 satırlık hedefi aşmamalı. Her modül dosyası 200-250 satır hedefiyle kompakt tutulmalı.
