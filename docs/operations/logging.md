# Logging Operations Guide

**Amaç:** E-İSA uygulamalarının Kubernetes üzerindeki loglama davranışını, hassas veri politikasını ve ileride kurulacak `Alloy → Loki → Grafana` altyapısıyla nasıl entegre olacağını anlatır.

Bu belge yalnızca operasyon dokümanıdır. Loki/Alloy/Grafana kurulumu bu görev kapsamında değildir.

---

## 1. Genel Mimari

```
Uygulamalar (Django, Fastify, Vue, Svelte)
    → JSON stdout / stderr
    → [ileride] Grafana Alloy (node collector)
    → [ileride] Grafana Loki
    → [ileride] Grafana dashboard
```

Kubernetes içinde çalışan hiçbir uygulama operasyonel log dosyası **yazmaz**. Fiziksel kiosk cihazı istisnadır: sınırlı bir SQLite diagnostic outbox tutar; INFO/DEBUG kaydetmez, yalnızca WARNING/ERROR/CRITICAL saklar ve backend'e batch olarak gönderir.

İş kayıtları (`AuditLog`, `OturumLogu`, `PlayLog`, proof-of-play, kiosk provisioning kayıtları) log sistemine dönüştürülmez; PostgreSQL'de durur.

---

## 2. Ortak Ortam Değişkenleri

| Değişken | Değer | Not |
|----------|-------|-----|
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | Prod varsayılan `INFO` |
| `LOG_FORMAT` | `json` \| `console` | Prod `json`, dev `console` |
| `SERVICE_NAME` | `eisa-backend`, `eisa-kiosk-api`, … | Log alanı `service` olarak yazılır |
| `APP_ENV` | `development`, `test`, `staging`, `production` | Log alanı `environment` |
| `APP_VERSION` | Semver / build tag | Log alanı `version` |

Backend ve Fastify aynı env alanlarını okur. Vue/Svelte tarayıcıda çalıştığı için stdout üretmez; kritik hatalarını backend/kiosk API üzerinden JSON logu olarak gönderir.

Eskiden kullanılan `DJANGO_LOG_DIR`, `EISA_LOG_DIR`, dosya rotasyonu env'leri **kaldırıldı**. Kubernetes manifestlerinde log amaçlı `emptyDir` / PVC bulunmuyor.

---

## 3. JSON Log Şeması

Prod ortamında tüm backend + Fastify logları en az şu alanları içerir:

```json
{
  "timestamp": "2026-07-16T12:10:30.123Z",
  "level": "INFO",
  "service": "eisa-backend",
  "environment": "production",
  "version": "1.0.0",
  "logger": "eisa.request",
  "event": "request_completed",
  "message": "request_completed",
  "correlation_id": "5c1cabc47dfa4a5d9c9b6e8b4f7d3a2b",
  "request_method": "POST",
  "request_path": "/api/kiosk/v1/1/sync/",
  "status_code": 200,
  "duration_ms": 42,
  "actor_type": "kiosk"
}
```

Ek alanlar (`kiosk_id`, `event`, `attempt`, `stack`, `exception_type`) mesajı üretenin `extra={...}` bloğundan gelir. Hassas alanlar (`Authorization`, `Cookie`, `token`, `password`, `qr_kodu`, `cevaplar` vb.) yazılırken `***` ile maskelenir. Boş / geçersiz alanlar zorla üretilmez.

Detaylar: [`backend/apps/core/logging/formatters.py`](../../backend/apps/core/logging/formatters.py), [`kiosk_edge/api-node/src/logger.js`](../../kiosk_edge/api-node/src/logger.js).

---

## 4. Korelasyon ID Davranışı

- Her HTTP isteği için `X-Correlation-ID` başlığı taşınır.
- Backend `apps.core.logging.middleware.CorrelationIdMiddleware`:
  - Başlık varsa güvenli değeri kullanır (`^[A-Za-z0-9._-]{1,64}$`), yoksa UUID üretir.
  - Response başlığına aynı ID'yi yazar.
  - Middleware boyunca `contextvars` üzerinden log satırlarına eklenir.
- Fastify tarafında Fastify `req.id` bu ID ile hizalanır; `runWithCorrelation` `AsyncLocalStorage` üzerinden nested async çağrılara aktarır.
- Backend'e giden tüm scheduler istekleri `X-Correlation-ID` başlığını iletir.
- Vue paneli response'daki `x-correlation-id` başlığını `window.__EISA_LAST_CORRELATION_ID__` üzerinde tutar; frontend hata bildirimlerinde kullanır.
- Scheduler'ın her yeni döngüsü `derivedId('pull')` gibi bağımsız fakat izlenebilir bir ID üretir.

---

## 5. Hassas Veri Politikası

Sanitize edilen anahtarlar (büyük-küçük harf duyarsız): `Authorization`, `Cookie`, `X-CSRFToken`, `X-*-Key`, `password`, `secret`, `token`, `access`, `refresh`, `jwt`, `iot_token`, `fleet_key`, `provisioning_secret`, `signature`, `hmac`, `s3_*_key`, `db_password`, `email`, `telefon`, `qr_kodu`, `qr_payload`, `cevaplar`, `onerilen_etken_maddeler`, `raw_body`, `response_body`.

- Request/response body’si loglanmaz; yalnızca güvenli metadata (`payload_size`, `item_count`, `status_code`) yazılabilir.
- Django ORM SQL parametreleri prod'da `django.db.backends` logger'ı `WARNING` seviyesine indirilerek yazılmaz.
- Nginx access log'ları `X-Correlation-ID`, kısa path, status, süre içerir; Authorization/cookie/query değerlerini yazmaz. Health endpoint (`/healthz`) `access_log off`.

---

## 6. Development vs Production Farkı

| Ortam | LOG_FORMAT | LOG_LEVEL | Not |
|-------|-----------|-----------|-----|
| dev  | `console` | `DEBUG`   | Django development server + Fastify pretty (opsiyonel) |
| prod | `json`    | `INFO`    | Tüm satırlar JSON stdout; Alloy/Loki uyumlu |

`DEBUG` seviye yalnızca gerektiğinde açılır; heartbeat / periyodik başarı satırları prod'da `debug`'a indirilir.

---

## 7. Diagnostic Outbox (Yalnızca Fiziksel Kiosk)

- Tablo: `diagnostic_outbox` (SQLite şema v10).
- Yalnızca `WARNING`, `ERROR`, `CRITICAL` seviyeler kabul edilir.
- Sınırlar (config edilebilir):
  - `EISA_DIAG_MAX_ROWS` = 5000
  - `EISA_DIAG_MAX_AGE_DAYS` = 7
  - `EISA_DIAG_BATCH_SIZE` = 100
  - Mesaj ≤ 4 KB, stack ≤ 8 KB, context ≤ 6 KB (aşarsa özet yazılır).
- FIFO trigger: kapasite aşılırsa önce gönderilmiş kayıtlar, sonra en eski düşük öncelikli (INFO/DEBUG için zaten yasak; WARNING sırayla) satırlar silinir.
- Rate limit: aynı event/message 5sn içinde tekrarlanmaz.
- Exponential backoff: retry sayısı 6'yı geçerse kayıt otomatik silinir.
- Scheduler `pushDiagnostics` → `POST /api/analytics/diagnostic-ingest/`
  - Fleet key + IoT token doğrulaması.
  - Batch başına 100 kayıt, payload sınırlı.
  - Backend sanitize eder ve **JSON stdout**'a yazar; DB tablosuna yazmaz.
  - Response: `{ accepted, rejected, errors, accepted_keys }`.

Modül dosyaları: [`kiosk_edge/api-node/src/diagnosticOutbox.js`](../../kiosk_edge/api-node/src/diagnosticOutbox.js), [`backend/apps/analytics/log_ingest.py`](../../backend/apps/analytics/log_ingest.py).

---

## 8. Client Event Endpoint (Vue Paneli)

- `POST /api/analytics/client-events/`
- Auth: JWT httpOnly çerez (`IsAuthenticated`).
- Rate limit: `client_event` scope, varsayılan 30/min.
- Alan allow-list: `level, event, message, stack, component, route, correlation_id, occurred_at, user_agent_brand`.
- Boyutlar: message ≤ 4 KB, stack ≤ 8 KB, route ≤ 256 char.
- Backend sanitize edip stdout'a JSON log yazar; DB'ye yazmaz.
- Frontend logger [`web_panels/src/lib/logger.js`](../../web_panels/src/lib/logger.js): dev'de console, prod'da yalnızca WARNING+; aynı event 30sn içinde tekrar gönderilmez; kendi bildirim hatası tekrar loglanmaz.

Kiosk UI (Svelte) [`kiosk_edge/ui/src/lib/logger.js`](../../kiosk_edge/ui/src/lib/logger.js) yalnızca allow-list edilmiş event kodlarını Fastify'ye gönderir:
`screen_render_failed`, `local_api_unreachable`, `media_playback_failed`, `session_submit_failed`, `playlist_invalid`, `window_error`, `unhandled_rejection`, `wifi_operation_failed`. Kullanıcı verisi, QR içeriği, öneri listesi, cevaplar loglanmaz.

---

## 9. `kubectl logs` Örnekleri

```
kubectl -n eisa-app logs deploy/eisa-api -f | jq
kubectl -n eisa-app logs deploy/eisa-portal -f
kubectl -n eisa-app logs deploy/eisa-kiosk-demo -c kiosk -f | jq
```

Uygulama Loki'ye aktarıldığında Grafana Explore'da tipik LogQL sorguları:

```
{app="eisa-api", environment="production"} |= "request_failed"
{app="eisa-api"} | json | level="ERROR" | line_format "{{.timestamp}} {{.event}} {{.message}}"
{app="eisa-api"} | json | correlation_id="5c1cabc47dfa4a5d9c9b6e8b4f7d3a2b"
```

---

## 10. Sorun Giderme

| Belirti | Kontrol |
|---------|---------|
| Log çıktısı JSON değil | `LOG_FORMAT=json`, `APP_ENV=production` set edilmiş mi? |
| Aynı istek için iki hata satırı | `apps.core.logging.formatters.LOG_HANDLED_MARK` işareti — exception handler bir kez log ediyor mu? |
| `X-Correlation-ID` başlığı yok | `CorrelationIdMiddleware` en üstte mi? Response middleware zinciri kırılmadı mı? |
| Kiosk offline'ken uygulama duruyor | Diagnostic outbox kapasite dolarsa uygulama **durmaz**; FIFO trigger devrede |
| Sensitive değer log'da görünüyor | `apps/core/logging/redaction.py` DEFAULT_SENSITIVE_KEYS listesine ekle; Fastify tarafı `logRedaction.js` |
| Log dizini görünüyor | Kubernetes'te dosya log YAZMAMALI — `EISA_LOG_DIR`, `DJANGO_LOG_DIR`, log volume kaldırıldı |

---

## 11. İleride Kurulacak

Bu doküman uygulamaların hazır olduğunu belirtir. Sonraki adım:

1. Grafana Alloy DaemonSet ile node collector kurulumu.
2. Alloy → Loki push URL yapılandırması.
3. Grafana dashboard'ları ve alerting kuralları.

Uygulamaların standart container `stdout`/`stderr` üretmesi yeterli olduğu için ek annotation veya sidecar gerekmez.
