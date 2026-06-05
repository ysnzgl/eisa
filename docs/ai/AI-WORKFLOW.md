# AI Workflow Protocol

**Amaç:** Gelecekteki AI oturumları için standart çalışma prosedürü.

---

## Before You Start

**Follow AI-RULES.md principles:**
- Code is always truth (Rule 1: Always Open The File)
- Always verify with real code (Rule 2: Never Assume Uncertain Areas)
- Minimal change only (Rule 3: Minimal Change Principle)

**Navigation:**
1. Read 00-AI-INDEX.md first — genel bakış, modül haritası
2. Check relevant module docs — ilgili modül dokümanlarını oku
3. Verify with real code — doküman ile kodu karşılaştır

---

## Yeni Özellik Eklerken

### Adım 1: Context Toplama
```
1. 00-AI-INDEX.md oku → hangi modül(ler) etkileniyor?
2. İlgili modül dokümanını oku (örn: 01-backend.md)
3. "Important Source Files" bölümünü kontrol et
4. İlgili gerçek kod dosyalarını aç ve doğrula
5. Flow dokümanını oku (05-cross-project-flows.md veya 07/08)
6. Contract dokümanını kontrol et (06-db-and-api-contracts.md)
```

### Adım 2: Plan Oluştur
```
1. Etkilenen dosyaları listele
2. Değişecek contract'ları belirle
3. Breaking change var mı kontrol et
4. Test senaryolarını düşün
5. Rollback planı yap
```

### Adım 3: Implementation
```
1. Apply minimal change (AI-RULES.md Rule 3)
2. Check "Do Not Change Without Checking" sections (AI-RULES.md Rule 5)
3. Protect contracts (AI-RULES.md Rule 6)
4. Update docs immediately (AI-RULES.md Rule 3)
5. Update changelog (AI-RULES.md Rule 4)
```

### Adım 4: Doküman Güncelleme
```
1. İlgili modül dokümanını güncelle
2. Contract değiştiyse → 06-db-and-api-contracts.md güncelle
3. Flow değiştiyse → 05-cross-project-flows.md güncelle
4. Yeni risk tespit edildiyse → "Belirsiz/Riskli" bölümüne ekle
5. 99-ai-changelog.md güncelle
```

---

## Bug Düzeltirken

### Adım 1: Diagnose
```
1. İlgili flow dokümanını oku (05/07/08)
2. Contract dokümanını kontrol et (06)
3. "Do Not Change Without Checking" bölümünü oku
4. Gerçek kodu doğrula
5. Root cause'u belirle
```

### Adım 2: Fix
```
1. Apply minimal change (AI-RULES.md Rule 3)
2. Protect contracts (AI-RULES.md Rule 5)
3. Check multi-module impact (AI-RULES.md Rule 6)
4. Test scenarios
```

### Adım 3: Document
```
1. If docs wrong → fix docs (AI-RULES.md Rule 1: Code is Always Truth)
2. If code fixed → update docs (AI-RULES.md Rule 3)
3. Update changelog (AI-RULES.md Rule 4)
```

---

## API Contract Değişikliği

### Kritik Kontrol Listesi
```
□ Backend endpoint değişti mi?
□ Request/response format değişti mi?
□ Kiosk sync payload etkilendi mi?
□ Check "Do Not Change Without Checking" sections (AI-RULES.md Rule 5)
□ Multi-module impact? (AI-RULES.md Rule 6)
```

### Gerekli Güncellemeler
```
1. İlgili backend view/serializer
2. İlgili frontend API client
3. İlgili kiosk edge API handler
4. 06-db-and-api-contracts.md
5. İlgili flow dokümanı (05/07/08)
6. 99-ai-changelog.md
```

---

## DB Migration Eklerken

### Adım 1: Plan
```
1. 06-db-and-api-contracts.md oku → mevcut schema
2. "Do Not Change Without Checking" kontrol et
3. Breaking change var mı belirle
4. Migration rollback planı yap
```

### Adım 2: Implementation
```
1. Django migration oluştur
2. Eğer SQLite etkileniyorsa → kiosk_edge/api-node/src/db.js güncelle
3. Test data migration
4. Rollback test
```

### Adım 3: Document
```
1. 06-db-and-api-contracts.md güncelle
2. İlgili modül dokümanını güncelle
3. Changelog'a ekle
```

---

## Kod Review Yaparken

### Kontrol Listesi
```
□ "Do Not Change Without Checking" listesi kontrol edildi mi?
□ Contract değişiklikleri dokümente edildi mi?
□ Breaking change varsa tüm etkilenen modüller güncellendi mi?
□ Test coverage yeterli mi?
□ Changelog güncellendi mi?
□ Dokümanlar güncel mi?
```

---

## Yasaklar

### ❌ Yapma
```
- Tüm repoyu gereksiz yere tarama
**See AI-RULES.md "Forbidden Actions" section for complete list.**

Key prohibitions:
- No broad workspace scans (use 00-AI-INDEX.md → module docs)
- No large refactors (minimal change only)
- No new dependencies without approval
- No silent contract changes (breaking changes must be documented)
- No assumptions (verify or ask)
## Emergency Hotfix

### Hızlı Prosedür
```
1. İlgili dokümanı hızlıca oku (00-AI-INDEX → modül dokümanı)
2. Gerçek kodu doğrula
3. Minimal fix yap
4. Contract'ları kontrol et
5. Sonradan doküman güncelle (acil değilse)
6. Changelog'a ekle
```

---

## Dokumentasyonu Güncel Tutma

### Her Kod Değişikliğinde
```
1. İlgili modül dokümanını güncelle
2. Contract değiştiyse → 06-db-and-api-contracts.md
3. Flow değiştiyse → 05-cross-project-flows.md
4. 99-ai-changelog.md güncelle
```

### Belirsiz Alan Tespit Edildiğinde
```
1. İlgili dokümanda "Belirsiz / Riskli" bölümüne ekle
2. Gerçek kod ile doküman arasındaki farkı not et
3. Doğrulama gerekliliğini işaretle
```

---

## Debugging Workflow

### 1. Session/Log Problemi
```
→ 07-session-and-analytics.md oku
→ OturumLogu model + outbox flow kontrol et
→ Gerçek kod doğrula
```

### 2. Reklam/Playlist Problemi
```
→ 08-dooh-advertising.md oku
→ Playlist generation + sync flow kontrol et
→ Gerçek kod doğrula
```

### 3. API Contract Problemi
```
→ 06-db-and-api-contracts.md oku
→ Request/response format kontrol et
→ Frontend/backend uyumsuzluk bul
```

### 4. Proje Arası Senkronizasyon
```
→ 05-cross-project-flows.md oku
→ İlgili akış bul
→ Her adımı gerçek kodda doğrula
```

---

**Satır sayısı: ~180**
