# AI Changelog — Dokümantasyon ve Kod Değişiklikleri

**Amaç:** AI tarafından yapılan değişikliklerin kısa kaydı.  
**Format:** Tarih — Değişiklik (max 10 satır/kayıt)

---

## 2026-06-05

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

