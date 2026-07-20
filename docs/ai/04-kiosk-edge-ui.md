# Kiosk Edge UI — Svelte 5

**Amaç:** Kiosk kullanıcı arayüzü; demografik seçim → kategori seçim → soru/cevap akışı → QR gösterimi; reklam oynatımı (60sn döngü); offline-first.

---

## When To Read This File

- Kiosk UI değişiklikleri için
- Kategori/soru akışı problemlerinde
- QR üretimi/gösterimi için
- Reklam oynatım sorunlarında
- Session lifecycle değişikliklerinde

---

## Important Source Files

- `kiosk_edge/ui/src/App.svelte` — Main app, session lifecycle + global inaktivite:
  - `INACTIVITY_MS = 20_000` — idle/wifi disindaki HER ekranda 20sn islem yoksa idle'a doner
  - `onInactivityTimeout()`, `armInactivity()`, `clearInactivity()` — timeout yonetimi
  - `finalizeAbandonedSession()` — timeout'ta aktif anket oturumunu sessizce terk edilmis (tamamlandi=false) gonderir (sonuc ekranina YONLENDIRMEZ)
  - Global `pointerdown`/`keydown` dinleyicileri + reaktif ekran-bazli arm/clear
- `kiosk_edge/ui/src/stores/kiosk.js` — State management
- `kiosk_edge/ui/src/lib/api.js` — Lokal API client:
  - `submitSession({ ageRange, gender, oturumTipi, categorySlug, danismaKategorisiSlug, ... })` — session submission; **backend QR döner; sahte QR yok; backend erişilemezse error propagate edilir** (2026-07-20)
  - `logAdImpression({ assetId, assetType, shownAt, durationMs })` (line 166) — impression logging
- `kiosk_edge/ui/src/lib/logger.js` — Frontend hata köprüsü (2026-07-16):
  - Prod'da INFO/DEBUG bastırılır; yalnızca WARNING+ işlenir.
  - `installGlobalHandlers()` `window.onerror` + `unhandledrejection`'ı yakalar (main.js içinde çağrılır).
  - Kritik hatalar yerel Fastify'ye `POST /api/log/client` ile gönderilir; sadece allow-list edilen event kodları kabul edilir (`screen_render_failed`, `local_api_unreachable`, `media_playback_failed`, `session_submit_failed`, `playlist_invalid`, `window_error`, `unhandled_rejection`, `wifi_operation_failed`).
  - Kullanıcı verisi, QR içeriği, cevaplar, öneri listesi GÖNDERİLMEZ. Rate limit (15sn) ile aynı hata yüzlerce kez tetiklenmez. Detay: [docs/operations/logging.md](../operations/logging.md).
- `kiosk_edge/ui/src/lib/ingredients.js` — Etken madde recommendation
- `kiosk_edge/ui/src/components/Logo.svelte` — Tekrar kullanilabilir marka logosu (SVG):
  - `height` + `light` (koyu zeminde beyaz varyant) prop'lari. Tum "e-İSA" yazilari bununla degistirildi.
  - Kaynak: `src/assets/eisa-logo.svg` (koyu metin) + `src/assets/eisa-logo-light.svg` (beyaz metin)
- `kiosk_edge/ui/src/components/ScreenHeader.svelte` — Ortak ekran basligi (Logo + opsiyonel subtitle); 5 ekranda kullanilir
- `kiosk_edge/ui/src/components/MediaView.svelte` — URL uzantisina gore `<video>`/`<img>` render eden ortak bilesen; AdStrip + IdleScreen kullanir
- `kiosk_edge/ui/src/components/AdPromo.svelte` — Reklam YOKKEN gosterilen donen "Bu Alana Reklam Verebilirsiniz" tasarimi (her yerde ortak); `large` prop tam-ekran (attractor) varyanti
- `kiosk_edge/ui/src/components/IdleScreen.svelte` — Cekici (attractor) ekrani; acilista DOGRUDAN gosterilir (normal idle YOK). Reklam varsa MediaView ile doner, yoksa AdPromo
- `kiosk_edge/ui/src/components/AdStrip.svelte` — Reklam oynatim:
  - `logCurrentImpression()` — `asset_type` + `asset_id` ile impression payload olusturur
  - Medya yoksa `<AdPromo />`, medya varsa `<MediaView />` gosterir
- `kiosk_edge/ui/src/components/ResultScreen.svelte` — QR gösterimi
- `kiosk_edge/ui/src/components/CategoryScreen.svelte` — Kategori seçimi
- `kiosk_edge/ui/src/components/QuestionScreen.svelte` — Soru akışı

---

## Kiosk UI Amacı

**Kullanıcı tipi:** Anonim son kullanıcı (eczane ziyaretçisi)

**Ana akış:**
1. Cekici (attractor) ekran — acilista dogrudan gelir: reklam varsa gorseller doner, yoksa donen "Bu Alana Reklam Verebilirsiniz" + logo + "Baslamak icin dokunun"
2. Dokunma → Demografik seçim (yaş aralığı, cinsiyet)
3. Kategori seçimi (şikayet türü: uyku, enerji, bağışıklık, vb.)
4. Soru/cevap akışı (kategori sorularına cevap verme)
5. Sonuç ekranı (önerilen etken maddeler + QR kod)
6. 20sn inaktivite → otomatik idle'a dön (idle/wifi disindaki her ekranda geçerli)

**Alternatif akış:**
- "Eczacınıza Danışın" butonu → Danışma kategorisi seçimi → QR kod (direkt)

**Reklam akışı:**
- Tüm ekranların altında AdStrip component → saatlik slot-hizalı playlist (creative/house_ad)
- Reklam YOKKEN: donen "Bu Alana Reklam Verebilirsiniz" (AdPromo); ekran koruyucuda da ayni promo
- Impression log: `{ asset_id, asset_type, played_at, duration_played }`

**Marka:**
- Tüm "e-İSA" yazilari resmi logo (Logo.svelte / SVG) ile gosterilir; koyu zeminlerde beyaz varyant

---

## Ana Ekran / Component / Page Yapısı

### Entry Point (`src/App.svelte`)

**State management:** Svelte 5 runes ($state, $derived, $effect) + writable stores (`src/stores/kiosk.js`)

**Screen states:**
- `idle`: Cekici (attractor) ekran — acilista dogrudan gelir (normal idle YOK)
- `demographics`: Demografik seçim
- `welcome`: Hoş geldin ekranı
- `category`: Kategori seçim
- `consult`: Danışma kategori seçim
- `question`: Soru/cevap akışı
- `result`: Sonuç + QR
- `wifi_setup`: WiFi kurulum (Linux, nmcli)

**Lifecycle hooks:**
- `onMount`: WiFi durumu kontrol, kategori cache kontrol, global aktivite dinleyicileri
- Global inaktivite: idle/wifi_setup disindaki HER ekranda 20sn islem yoksa idle'a doner; herhangi bir dokunma/tus zamanlayiciyi sifirlar

**Session lifecycle:**
- Kategori seçiminde `sessionId` atanır
- QR üretildiğinde session finalize (`tamamlandi: true`); 20sn inaktivite → `finalizeAbandonedSession()` ile terk edilmis (`tamamlandi: false`) gonderilir, ardindan idle'a donulur
- `sessionFinalized` bayrağı → duplikasyon koruması

---

### Components (`src/components/`)

1. **IdleScreen.svelte** (cekici / attractor ekrani)
   - Uygulama acilir acilmaz DOGRUDAN bu ekran gosterilir; ayri bir "normal idle" bekleme ekrani YOKTUR (kaldirildi).
   - Gercek reklam (playlist/kampanya) varsa gorseller arasinda gecis yapar (`MediaView`); reklam YOKKEN `<AdPromo large />` (donen "Bu Alana Reklam Verebilirsiniz").
   - Ust-orta'da logo (beyaz) + "Baslamak icin dokunun" overlay (`ss-overlay-text`).
   - Dokunma → `demographics` screen.

2. **DemographicsScreen.svelte**
   - Yaş aralığı seçimi (5 buton: 0-17, 18-24, 25-34, 35-49, 50+)
   - Cinsiyet seçimi (3 buton: Kadın, Erkek, Diğer)
   - "Devam Et" butonu → `welcome` screen

3. **WelcomeScreen.svelte**
   - Kısa karşılama mesajı
   - "Kategorilere Git" butonu → kategori yükleme → `category` screen
   - "Eczacınıza Danışın" butonu → danışma kategorileri yükleme → `consult` screen

4. **CategoryScreen.svelte**
   - Kategori grid (ikon + isim)
   - Filtreleme: Kullanıcının yaş/cinsiyet'ine göre `hedef_yas_araliklari` ve `hedef_cinsiyet` kontrolü
   - Kategori tıklama → soru yükleme → `question` screen
   - Loading state (spinner)

5. **ConsultScreen.svelte**
   - Danışma kategori grid (ikon + isim)
   - **Alt kategori navigation:** Ebeveyn kategorilere tıklama → alt kategoriler gösterilir (`activeParent` state, `selectParent()`, `selectChild()`, `backToParents()` fonksiyonları). Alt kategori seçimi → QR üretme.
   - **Visual temizlik (2026-07-07):** Kategori ikonlarının altında gösterilen "X alt konu" badge/text kaldırıldı (lines 63-65). Alt kategori yapısı TAM olarak korundu, sadece sayı gösterimi kaldırıldı.
   - Kategori tıklama → QR üretme → `result` screen (direkt)

6. **QuestionScreen.svelte**
   - Soru metni gösterimi
   - Cevap butonları (soru.cevaplar)
   - Cevap tıklama → `currentAnswers` array'e ekle → sonraki soru
   - Son soru → etken madde önerisi hesaplama → `result` screen

7. **ResultScreen.svelte**
   - Önerilen etken maddeler listesi
   - QR kod gösterimi (qr-creator library)
   - "Eczaciniza Danisin" destek mesajı
   - "Tamamla" butonu → `idle` screen
   - Auto-reset: 30sn sonra otomatik idle'a dön

8. **AdStrip.svelte**
   - Alt strip (kiosk yuksekliginin ~2/5'i)
   - Playlist çekme: `GET http://127.0.0.1:8765/api/playlist/current?hour=<0-23>`
   - Saatlik (3600sn) slot-hizali oynatim: pos = floor(epoch/1000) % 3600 (duvar saatine gore)
   - Her item icin `<MediaView>` (asset_type: creative/house_ad), `duration_seconds`
   - Slot degisince onceki slot icin impression: `POST http://127.0.0.1:8765/api/reklam-gosterim`
     `{ asset_id, asset_type, played_at, duration_played }`
   - Medya/asset YOKKEN → `<AdPromo />` (donen "Bu Alana Reklam Verebilirsiniz")

### Ortak (tekrar kullanilan) bilesenler

9. **Logo.svelte**
   - Marka logosu (SVG). Props: `height`, `light` (koyu zeminde beyaz), `class`. Kaynak: `assets/eisa-logo.svg` + `eisa-logo-light.svg`

10. **AdPromo.svelte**
   - Reklam yokken donen "Bu Alana Reklam Verebilirsiniz" tasarimi (konik isik halkasi + megafon + shimmer baslik + logo). `large` prop tam-ekran (attractor) varyanti

11. **MediaView.svelte**
   - URL uzantisina gore `<video>` veya `<img>` render eder. Props: `src`, `alt`, `loop`, `class`. AdStrip + IdleScreen tarafindan ortak kullanilir

12. **ScreenHeader.svelte**
   - Ortak ekran basligi: `Logo` + opsiyonel `subtitle`. Props: `height`, `subtitle`. Welcome/Demographics/Category/Consult/Question ekranlarinda kullanilir

13. **WifiSetupScreen.svelte**
   - WiFi ağ listesi (`GET http://localhost:5234/wifi-status`)
   - Ağ seçimi + şifre girişi
   - "Bağlan" butonu → `POST http://localhost:5234/wifi-connect` (nmcli)
   - Başarılı bağlantı → `idle` screen

---

## Kategori Gösterimi

**Akış:**
1. `WelcomeScreen` → "Kategorilere Git" butonu
2. `App.svelte` → `loadCategories()` fonksiyonu
3. `GET http://localhost:5234/categories` → lokal API çağrısı
4. Lokal API → SQLite `kategoriler` tablosundan `aktif=1` kayıtları
5. Frontend → `visibleCategories` store'a yaz
6. `CategoryScreen` → grid gösterimi (ikon + ad)

**Filtreleme:**
- Lokal API tarafında: `hedef_cinsiyet_id` ve `hedef_yas_araliklari` JSON kontrolü
- Frontend'de de double-check yapılabilir ama ana filtreleme backend/API node'da

---

## Reklam Gösterimi

**Akış:**
1. `AdStrip.svelte` component mount olduğunda → `onMount`
2. `GET http://localhost:5234/playlist?date=YYYY-MM-DD` → günlük playlist
3. Response:
   ```json
   {
     "id": "uuid",
     "target_date": "2026-06-05",
     "target_hour": 10,
     "version": 42,
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
   ```
4. `AdStrip` → `items` array'i sırayla oynatır
5. Her item için:
   - `playbackOrder` sırasına göre sıralama
   - `duration_seconds` kadar gösterim
   - `<video>` element: `autoplay`, `muted`, `onended` event → sonraki item
   - `<img>` element: `setTimeout(duration_seconds * 1000)` → sonraki item
6. 60sn döngü tamamlanınca başa dön (loop)

**Impression logging:**
- Bir reklam slotu gösterildiğinde → `shownAt` timestamp kaydedilir
- Slot değişince önceki slotun gerçek izlenme süresi (`durationMs`) hesaplanır
- `POST http://127.0.0.1:8765/api/reklam-gosterim`:
  ```json
  {
    "asset_id": "uuid",
    "asset_type": "creative",
    "played_at": "2026-06-05T10:30:00.000Z",
    "duration_played": 15
  }
  ```
- Lokal API → `reklam_gosterim_outbox` tablosuna insert → backend'e batch gönderim

---

## Kullanıcı Interaction / Session Akışı

### Başarılı Akış (Tamamlanmış Session)
1. İdeal → Başla → Demografik seçim (yaş: 25-34, cinsiyet: Kadın)
2. Hoş geldin → Kategorilere git
3. Kategori seçimi (örn: "Uyku Sorunu")
4. Soru 1: "Uykuya dalmakta zorluk çekiyor musunuz?" → Cevap: "Evet"
5. Soru 2: "Gece uyanıyor musunuz?" → Cevap: "Hayır"
6. Soru 3: ... (kategori soru sayısı kadar)
7. Tüm sorular tamamlanınca → etken madde önerileri hesaplanır (`getRecommendations`)
8. Sonuç ekranı: Önerilen etken maddeler + QR kod
9. QR kod üretimi: `qr_kodu = "EISA-" + timestamp + random`
10. Session log: `POST http://localhost:5234/sessions` → `tamamlandi: true`
11. "Tamamla" butonu veya 30sn sonra → idle'a dön

### Terk Edilmiş Akış (Abandoned Session)
1. İdeal → Başla → Demografik seçim
2. Hoş geldin → Kategorilere git
3. Kategori seçimi
4. Soru 1'e cevap verilir
5. **10sn inaktivite** (soru 2'ye cevap verilmez)
6. `onInactivityTimeout` trigger → session log: `POST http://localhost:5234/sessions` → `tamamlandi: false`
7. Ekran otomatik idle'a döner

### Danışma Akışı
1. İdeal → Başla → Demografik seçim
2. Hoş geldin → **"Eczacınıza Danışın"** butonu
3. Danışma kategorisi seçimi (örn: "Reçete Danışma")
4. Direkt QR kod üretimi (soru akışı yok)
5. Session log: `POST http://localhost:5234/sessions` → `kategori: danisma_kategorisi`, `tamamlandi: true`
6. Sonuç ekranı: "Eczacınız sizi bekliyor — QR kodu okutunuz."
7. "Tamamla" butonu → idle'a dön

---

## QR Üretim / Tamamlanma Akışı

### QR Üretimi
1. `App.svelte` → `showFlowAResult` veya `showConsultResult` fonksiyonu
2. QR kodu string üretimi:
   - Format: `"EISA-" + timestamp + "-" + randomHex(8)`
   - Örn: `"EISA-1717592400-A3F8D2E1"`
3. `qr-creator` library kullanımı:
   ```js
   import QrCreator from 'qr-creator';
   QrCreator.render({
     text: qr_kodu,
     radius: 0.5,
     ecLevel: 'H',
     fill: '#000000',
     background: '#ffffff',
     size: 256
   }, document.getElementById('qr-canvas'));
   ```
4. Session log payload:
   ```json
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
   ```
5. `POST http://localhost:5234/sessions` → lokal API → outbox → backend

### QR Tarama (web_panels tarafında)
1. Eczacı → web_panels `/pharmacist/qr` sayfası
2. QR kodu okutulur (kamera veya manuel input)
3. `GET /api/pharmacies/sessions/?qr=EISA-1717592400-A3F8D2E1` → backend API
4. Backend → `OturumLogu.objects.filter(qr_kodu=qr)` → session detayı
5. Modal: Kullanıcı demografisi, kategori, cevaplar, önerilen etken maddeler
6. Eczacı → danışmanlık yapma (backend'de ek akış şu an eksik olabilir)

---

## UI Konfigürasyonu

### API Endpoint Konfigürasyonu

API endpoint'i configurable yapılmıştır (2026-07-01):

**Dosya:** `kiosk_edge/ui/src/lib/api.js`
```javascript
const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8765';
```

**Environment variable:**
- `.env.example` dosyasında `VITE_API_BASE` tanımlı
- Build sırasında Vite tarafından inject edilir
- Default: `http://127.0.0.1:8765` (lokal development)
- Birleşik Docker container'da `""` (relative path → nginx `/api` proxy)
- `??` (nullish) kullanılır ki boş string override edilebilsin

**Kullanım:**
```bash
# Development
VITE_API_BASE=http://127.0.0.1:8765 npm run dev

# Production build (demo için)
VITE_API_BASE=http://kiosk-api:8765 npm run build
```

### IdleScreen Layout Değişikliği

**Dosya:** `kiosk_edge/ui/src/app.css`

**Değişiklik (2026-07-01):**
- `.screen-idle`: `align-items: center` → `align-items: flex-start`
- `.idle-content`: `margin-top: 80px` eklendi

**Etki:**
- Logo ve ana içerik ekranın ortasından yukarıya taşındı
- Daha fazla alan bekleme ekranı alt banner için ayrıldı
- Görsel denge iyileştirildi

---

## Docker Deployment (Demo)

### Birleşik (All-in-One) Container

**Dosya:** `kiosk_edge/Dockerfile` (build context: `kiosk_edge/`)

API Node ve UI **tek container** içinde birlikte çalışır:
- Nginx (:80) → UI static + `/api` proxy
- Node API (127.0.0.1:8765, internal)
- supervisord ile iki process yönetilir

**Özellikler:**
- Multi-stage build (ui-build → api-deps → runner)
- UI build sırasında `VITE_API_BASE=""` (relative path) → nginx `/api` proxy
- Aynı origin → CORS sorunu yok
- Health check: `/healthz` (nginx), `/health` (api proxy)

**Build & Run:**
```powershell
cd kiosk_edge
docker compose -f docker-compose.demo.yml up -d
```

- **UI + API:** http://localhost:8080

**NOT:** Bu Docker yapısı sadece **demo.eisa.com.tr** için hazırlanmıştır. Gerçek kiosk cihazlarında native deployment kullanılır (PRODUCTION_VIRTUALBOX_DEPLOY.md).

Detay: `kiosk_edge/README_DEMO_DOCKER.md`

---

## Belirsiz / Riskli Noktalar

1. **Etken madde önerileri hesaplama:** `getRecommendations` fonksiyonu (`lib/ingredients.js`) mantığı tam açık değil. Hangi kurallara göre öneri yapılıyor? (Belirsiz)
2. **QR kod formatı:** `"EISA-" + timestamp + random` → collision riski düşük ama garantisi yok. Backend'de unique constraint var mı? (Doğrulanmalı)
3. **Session idempotency_key:** UUID nasıl üretiliyor? `uuid()` fonksiyonu nereden geliyor? (Belirsiz)
4. **AdStrip video error handling:** Video yüklenemezse veya oynatılamazsa ne olur? `failure_reason` log'lanıyor ama UI'da fallback? (Belirsiz)
5. **WiFi setup:** `nmcli` çağrıları Linux'a özel, geliştirme ortamında (Windows/macOS) çalışmaz. Fallback mekanizma? (Belirsiz)
6. **Auto-reset timing:** 30sn sonra idle'a dön → kullanıcı QR'ı okutmaya fırsat bulamayabilir. Configurable olmalı? (Doğrulanmalı)
7. **Offline playlist:** Internet kesildiğinde eski playlist oynatılır mı, yoksa reklam strip boş mu kalır? (Belirsiz)

---

**Satır sayısı: ~280**
