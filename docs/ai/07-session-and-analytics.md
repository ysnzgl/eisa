# Session and Analytics System

**Amaç:** Session lifecycle, QR üretimi, analytics toplama mekanizmalarını detaylı dokümante etmek.

---

## When To Read This File

- Session log sorunlarında
- QR lifecycle değişikliklerinde
- Analytics/reporting geliştirmelerinde
- Idempotency problemlerinde
- Session timeout davranışı için

---

## Important Source Files

- `backend/apps/analytics/models.py` — OturumLogu, OturumCevap, OturumOnerilenEtkenMadde models
- `backend/apps/analytics/services.py` — `ingest_session_items()`, `generate_qr_candidate()`
- `kiosk_edge/ui/src/App.svelte` → `INACTIVITY_MS`, `onInactivityTimeout()`, session lifecycle
- `kiosk_edge/ui/src/lib/api.js` → `submitSession()` client function
- `kiosk_edge/api-node/src/db.js` — oturum_outbox table
- `kiosk_edge/api-node/src/server.js` → `POST /api/oturum/gonder` handler
- `kiosk_edge/api-node/src/scheduler.js` → `pushToCentral()` function
- `web_panels/src/views/pharmacist/QrScan.vue` — QR scanning + danışmanlık detayı
- `backend/apps/analytics/management/commands/verify_session_data.py` — Data quality report
- `backend/apps/analytics/management/commands/backfill_session_normalization.py` — JSON backfill

---

## QR Tasarımı (2026-07-20 güncellemesi)

**Authoritative QR:** Backend üretir, istemci almaz.
- Format: 8 karakter `[A-Z0-9]`, kriptografik rastgele (secrets.choice)
- DB: `OturumLogu.qr_kodu` → `CharField(max_length=8, unique=True)` — DB seviyesinde constraint
- Retry: `IntegrityError` yakalanır, yeni aday üretilir (max 5 deneme, her biri savepoint)
- **"QR collision imkansız" değil; DB onu saklar, retry çözüm sağlar**

**Edge:** Tamamlanan oturumlar için backend'i sync olarak çağırır. Response'taki `qr_kodu`'nu kullanır.
- Backend erişilemezse → 503 döner (sahte QR gösterilmez)
- Terk edilen oturumlar (tamamlandi=false) QR gerektirmez

**Geriye dönük:** `qrBitpack` encodeQrCode() hala çalışır ama sadece termal yazıcı metadata'sı için kullanılır.

---

## Session Lifecycle

### 1. Sikayet Session (SIKAYET)
```
Kategori seçimi → Soru akışı → Sonuç ekranı
  → UI: POST /api/oturum/gonder { oturum_tipi: "SIKAYET", kategori_slug, cevaplar, ... }
  → Edge: Backend'e sync ilet, backend QR üret
  → Backend: ingest_session_items() → generate_qr_candidate() + DB insert
  → Response: { results: [{ idempotency_key, status, qr_kodu }] }
  → UI: Backend QR'ı göster (sahte QR yok)
```

### 2. Danışmanlık Session (DANISMANLIK)
```
"Eczacıya Danış" butonu → Danışma kategorisi seçimi
  → UI: POST /api/oturum/gonder { oturum_tipi: "DANISMANLIK", danisma_kategorisi_slug, ... }
  → kategori_slug gönderilmez (nullable)
  → Edge → Backend → QR
  → Eczacı paneli: danisma_kategorisi_detay.ad gösterilir (kategori değil)
```

### 3. Terk Edilen Session (Abandoned)
```
20sn inactivity → tamamlandi=false
  → Edge: outbox'a yaz, QR yok
  → Backend'e async gönder (scheduler)
  → UI'a qr_kodu: null döner
```

---

## Normalizasyon Mimarisi

### JSON vs Relational (Expand/Contract)
- `OturumLogu.cevaplar` JSON ve `OturumLogu.onerilen_etken_maddeler` JSON **backup** olarak korunur
- `OturumCevap` ve `OturumOnerilenEtkenMadde` normalize tablolar (yeni kayıtlar her ikisine de yazılır)
- Eski kayıtlar için: `python manage.py backfill_session_normalization`

### Soru-Cevap Doğrulama
- `cevap.soru_id == soru_id` kontrol edilir
- Uyumsuz cevap: FK null, snapshot'ta `[uyumsuz: ...]` notu

### Deployment Sırası (production)
1. `python manage.py migrate` (0006, 0007, 0008 uygulanır — QR cleanup dahil)
2. `python manage.py verify_session_data` (veri kalitesini raporla)
3. `python manage.py backfill_session_normalization` (JSON → relational backfill)
4. `python manage.py verify_session_data` (tekrar doğrula)

---

## Oturum Tipi Doğrulama

| oturum_tipi | kategori_slug | danisma_kategorisi_slug |
|-------------|--------------|------------------------|
| SIKAYET | zorunlu | opsiyonel / null |
| OZEL_DANISMANLIK | null | zorunlu |

---
  → POST http://localhost:5234/sessions
    { ..., "tamamlandi": false }
  → sessionFinalized = true
  → Ekran idle'a döner
```

**Timeout constant location:**
- File: `kiosk_edge/ui/src/App.svelte`
- Constant: `INACTIVITY_MS = 10_000` (line 30)
- Functions: `onInactivityTimeout()`, `armInactivity()`, `clearInactivity()`

### 5. Danışma Akışı (Soru yok)
```
WelcomeScreen → "Eczacınıza Danışın" butonu
  → ConsultScreen: danışma kategorisi seçimi
  → Direkt QR üretimi (soru akışı atlanır)
  → POST http://localhost:5234/sessions
    { kategori: danisma_kategori_id, tamamlandi: true }
  → ResultScreen: "Eczacınız sizi bekliyor" mesajı
```

---

## QR Üretimi

### Format
```
8 karakter Base36 (0-9A-Z)
Örnek: "A1B2C3D4"
```

### Generation Logic (kiosk_edge/ui)
```js
import QrCreator from 'qr-creator';

const qr_kodu = `EISA-${Date.now()}-${randomHex(8)}`;

QrCreator.render({
  text: qr_kodu,
  radius: 0.5,
  ecLevel: 'H',
  fill: '#000000',
  background: '#ffffff',
  size: 256
}, document.getElementById('qr-canvas'));
```

### Collision Risk
- Timestamp (ms) + 8 hex chars → ~düşük collision riski
- Backend'de `OturumLogu.qr_kodu` indexed ama unique constraint yok (Riskli)

---

## Idempotency Mekanizması

### Purpose
Aynı session'ın iki kez kaydedilmesini engellemek (network retry, double submit vb.)

### Implementation
```
1. Kiosk UI → sessionId = uuid() (kategori seçiminde)
2. Session log payload → idempotency_key = sessionId
3. Lokal API → SQLite oturum_outbox → insert
4. Backend sync → OturumLogu.objects.get_or_create(idempotency_anahtari=idempotency_key)
5. Eğer zaten varsa → skip, yeni kayıt oluşturmaz
```

### DB Constraint
```sql
CREATE UNIQUE INDEX idx_oturum_idempotency 
  ON oturum_loglari(idempotency_anahtari);
```

**Belirsiz:** Backend'de `get_or_create` mi kullanılıyor yoksa sadece unique constraint'e mi güveniliyor? (Doğrulanmalı)

---

## Session Log Outbox Pattern

### Flow
```
1. Kiosk UI → POST http://localhost:5234/sessions → lokal API
2. Lokal API → SQLite oturum_outbox INSERT
   {
     id: autoincrement,
     payload: JSON,
     olusturulma_tarihi: NOW(),
     gonderilme_tarihi: NULL
   }
3. Scheduler (pushOutbox, 1dk interval)
   → SELECT * FROM oturum_outbox WHERE gonderilme_tarihi IS NULL
  → Batch POST /api/kiosk/v1/sessions/ { sessions: [...] }
4. Backend → OturumLogu bulk create
5. Lokal API → UPDATE oturum_outbox SET gonderilme_tarihi = NOW()
```

### Retry Logic
- Exponential backoff: 0ms, 1000ms, 3000ms
- 3 deneme sonunda başarısız → log, next cycle retry
- Backend 500+ error → retry
- Network error → retry

### Outbox Pressure
- `checkOutboxPressure`: MAX 10000 pending kayıt
- Aşılırsa → warning log
- Tam dolunca ne olur? → belirsiz (log kaybı riski)

---

## Analytics Toplama

### OturumLogu Model (Backend)
```python
class OturumLogu(BaseModel):
    idempotency_anahtari = UUIDField(unique=True, db_index=True)
    kiosk = FK(Kiosk)
    yas_araligi = FK(YasAraligi)
    cinsiyet = FK(Cinsiyet)
    kategori = FK(Kategori)
    hassas_akis = BooleanField(default=False)
    qr_kodu = CharField(max_length=64, db_index=True)
    cevaplar = JSONField(default=dict)
    onerilen_etken_maddeler = JSONField(default=list)
    tamamlandi = BooleanField(default=True)
    olusturulma_tarihi = DateTimeField(auto_now_add=True)
```

### Analytics Queries
```python
# Toplam session sayısı
OturumLogu.objects.count()

# Tamamlanan session sayısı
OturumLogu.objects.filter(tamamlandi=True).count()

# Terk edilmiş session oranı
abandoned = OturumLogu.objects.filter(tamamlandi=False).count()
total = OturumLogu.objects.count()
rate = abandoned / total

# Kategori dağılımı
OturumLogu.objects.values('kategori__ad').annotate(count=Count('id'))

# Günlük trend
OturumLogu.objects.filter(
    olusturulma_tarihi__date=date
).count()
```

### API Endpoints
```
GET /api/analytics/oturum-loglari/
  ?kiosk={id}
  &start_date={YYYY-MM-DD}
  &end_date={YYYY-MM-DD}
  &kategori={id}
  &tamamlandi={true/false}
```

---

### QR Tarama ve Danışma Tamamlama (web_panels)

#### Flow
```
1. Eczacı → /pharmacist/qr sayfası
2. Fiziksel barkod okuyucu input'a QR yazar ve Enter gönderir (kamera akışı yok)
3. GET /api/analytics/sessions/?qr_kodu={qr_kodu}
4. Backend → QR format doğrulama + oturum bulma + sahiplik kontrolü
5. Response:
   {
     "id": "uuid",
     "kiosk": { "id": 1, "ad": "Kiosk 1" },
     "yas_araligi": "25-34",
     "cinsiyet": "Kadın",
     "kategori": "Uyku Sorunu",
     "cevaplar": { ... },
     "onerilen_etken_maddeler": ["Melatonin", "Valerian"],
     "tamamlandi": true,
     "olusturulma_tarihi": "2026-06-05T10:30:00Z",
     "danisma_tamamlandi": false,
     "danisma_tamamlanma_tarihi": null,
     "danisma_notu": "",
     "danisma_tamamlayan_eczaci": null
   }
6. Modal gösterimi: Oturum detayı ve "Danışmayı Tamamla" butonu gösterilir.
7. Eczacı not ekler (opsiyonel) ve butona tıklar.
8. POST /api/analytics/sessions/{id}/complete/
  { "note": "Hastaya danışmanlık verildi.", "sale_result": "sold|not_sold" }
9. Backend:
   - OturumLogu'nu bulur ve eczane sahipliğini kontrol eder.
   - `danisma_tamamlandi`, `danisma_tamamlanma_tarihi`, `danisma_notu`, `danisma_tamamlayan_eczaci` alanlarını günceller.
   - Idempotency: Eğer zaten tamamlanmışsa, tekrar güncellemez, mevcut durumu döner.
10. Response: Güncellenmiş oturum objesi döner.
11. Frontend: UI güncellenir, tamamlama formu kaybolur ve tamamlama bilgisi gösterilir.
```

---

## Bilinen Riskler

1. **QR collision:** Unique constraint yok, sadece indexed
2. **Idempotency doğrulanması:** Backend'de `get_or_create` kullanımı belirsiz
3. **Outbox tam dolunca:** Log kaybı riski, overwrite/block mekanizması yok
4. **Session timeout:** 10sn çok kısa olabilir, configurable değil
5. **Abandoned session tracking:** Terk edilmiş session'lar analytics'te görünüyor mu?
- **Satış sonucu kalıcılığı:** Mevcut şemada ayrı satış sonucu kolonu yok; completion response'ta anlık metin üretilebilir, ancak DB'de kalıcı alan bulunmaz.

---

**Satır sayısı: ~250**
