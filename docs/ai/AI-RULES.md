# AI Rules — Permanent Behavior Guidelines

**Amaç:** Küçük modeller için kalıcı davranış kuralları.

---

## Fundamental Principles

### 1. Code is Always Truth
```
Doküman ≠ Gerçek
Kod = Gerçek

Eğer doküman ile kod çelişirse → KOD DOĞRUDUR
Dokümanı güncelle, kodu değiştirme (bug değilse)
```

### 2. Always Verify
```
❌ Doküman: "X böyle çalışır"
   → Varsay ve devam et

✅ Doküman: "X böyle çalışır"
   → Gerçek kodu aç ve doğrula
   → Eğer farklıysa → dokümanı güncelle
```

### 3. Minimal Change Principle
```
❌ "Bu kodu refactor edeyim, daha temiz olur"
✅ "Sadece istenen değişikliği yap"

Aksini söylemedikçe → minimal değişiklik
```

---

## Code Changes

### Rule 1: Always Open The File
```
❌ "models.py'de X vardır, şöyle değiştireceğim"
✅ models.py dosyasını aç → X'i gör → değiştir

Asla dosyayı açmadan kod değiştirme
```

### Rule 2: Never Assume Uncertain Areas
```
Belirsiz alan görürsen:
1. Dokümanı kontrol et
2. Gerçek kodu oku
3. Hâlâ belirsizse → SORU SOR
4. Varsayımla devam etme
```

### Rule 3: Contract Changes Require Documentation
```
Endpoint değişti → 06-db-and-api-contracts.md güncelle
Model değişti → ilgili modül dokümanını güncelle
Flow değişti → 05-cross-project-flows.md güncelle
```

### Rule 4: Always Update Changelog
```
Her kod değişikliğinde:
99-ai-changelog.md → yeni kayıt ekle

Format:
## YYYY-MM-DD
### [Modül] — Değişiklik başlığı
**Değişiklik:** ...
**Dosyalar:** ...
**Etki:** ...
```

---

## Breaking Changes

### Rule 5: Never Break Contracts Silently
```
Contract değişikliği yapıyorsan:
1. "Do Not Change Without Checking" listesini kontrol et
2. Etkilenen tüm modülleri listele
3. Güncellemeleri yap
4. Dokümanı güncelle
5. Breaking change'i changelog'a işaretle
```

### Rule 6: Multi-Module Impact Check
```
Backend değişikliği yapıyorsan:
□ Frontend etkileniyor mu?
□ Kiosk edge API etkileniyor mu?
□ Kiosk UI etkileniyor mu?
□ SQLite schema değişmeli mi?

Etkilenen her modülü güncelle
```

---

## Documentation

### Rule 7: Keep Docs In Sync
```
Kod değişti → doküman güncelle
Doküman yanlış → düzelt
Yeni risk tespit edildi → "Belirsiz/Riskli" bölümüne ekle
```

### Rule 8: Don't Over-Explain
```
❌ Uzun açıklamalar, gereksiz detaylar
✅ Kompakt, net, işe yarar bilgi

Token ekonomisi önemli
```

---

## Debugging

### Rule 9: Follow The Flow
```
Bug tespit edildi:
1. İlgili flow dokümanını oku (05/07/08)
2. Her adımı gerçek kodda doğrula
3. Farkı bul
4. Minimal fix yap
5. Dokümanı güncelle
```

### Rule 10: Don't Guess Root Cause
```
❌ "Belki X yüzündendir, X'i değiştirelim"
✅ "X'i doğrulayayım, eğer X'se fix'lerim"

Diagnose → Verify → Fix → Document
```

---

## Forbidden Actions

### ❌ Never Do These

1. **Tüm workspace'i gereksiz tarama**
   - 00-AI-INDEX.md → ilgili doküman → ilgili dosyalar

2. **Büyük refactor (aksini söylemedikçe)**
   - Minimal change principle

3. **Yeni dependency ekleme (gerekçesiz)**
   - Mevcut stack'i kullan

4. **Contract'ı sessizce değiştirme**
   - Breaking change → tüm modüller + doküman

5. **Doküman güncellemeden kod değiştirme**
   - Kod + doküman her zaman sync

6. **Varsayımla kod yazmak**
   - Belirsiz → sor, doğrula

7. **"Belki böyledir" diyerek devam**
   - Emin ol veya sor

---

## Best Practices

### ✅ Always Do These

1. **Start with 00-AI-INDEX.md**
   - Hangi doküman → hangi dosya

2. **Verify with real code**
   - Doküman rehber, kod gerçek

3. **Minimal change**
   - Sadece istenen değişiklik

4. **Update docs immediately**
   - Kod + doküman sync

5. **Write changelog**
   - Her değişiklik kayıt altında

6. **Check "Do Not Change" lists**
   - Breaking change'lerden kaçın

7. **Ask when uncertain**
   - Varsayım yapma

---

## Quick Reference

### Yeni Özellik
```
00-AI-INDEX → modül dokümanı → gerçek kod → plan → implement → doküman güncelle → changelog
```

### Bug Fix
```
Flow dokümanı → gerçek kod → diagnose → minimal fix → doküman güncelle → changelog
```

### Contract Değişikliği
```
"Do Not Change" kontrol → etkilenen modüller → hepsini güncelle → doküman → changelog
```

### Belirsiz Alan
```
Doküman kontrol → gerçek kod → hâlâ belirsiz? → SOR
```

---

**Satır sayısı: ~100**
