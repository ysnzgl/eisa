# AI Changelog — Dokümantasyon ve Kod Değişiklikleri

**Amaç:** AI tarafından yapılan değişikliklerin kısa kaydı.  
**Format:** Tarih — Değişiklik (max 10 satır/kayıt)

---

## 2026-07-01

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

