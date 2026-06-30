# E-İSA Kiosk Edge — Demo Deployment

Bu klasör, **demo.eisa.com.tr** için hazırlanmış birleşik (all-in-one) Docker yapısını içerir.

> **NOT:** Bu yapı gerçek kiosk cihazlarında kullanılmaz. Fiziksel kiosk'lar native olarak çalışır. Bu sadece web üzerinden demo gösterimi içindir.

---

## Mimari (Tek Container)

API Node ve UI **tek container** içinde birlikte çalışır:

```
┌─────────────────── eisa-kiosk-demo ───────────────────┐
│                                                        │
│   Nginx (:80)                                          │
│     ├── /            → UI static (Svelte dist)         │
│     ├── /api/*       → proxy → 127.0.0.1:8765 (Node)   │
│     └── /health      → proxy → Node /health           │
│                                                        │
│   Node API (127.0.0.1:8765, internal)                  │
│     └── Fastify + better-sqlite3                       │
│                                                        │
│   supervisord → iki process'i yönetir                  │
└────────────────────────────────────────────────────────┘
```

Host'a yalnızca **8080 → 80** portu açılır. UI ve API aynı origin üzerinden servis edilir (CORS sorunu yok).

---

## Hızlı Başlangıç

### 1. Environment Dosyasını Kopyala

```powershell
Copy-Item .env.demo .env
```

### 2. Servisi Başlat

```powershell
docker compose -f docker-compose.demo.yml up -d
```

### 3. Logları İzle

```powershell
docker compose -f docker-compose.demo.yml logs -f
```

### 4. Erişim

- **UI + API:** http://localhost:8080
- **API (relative):** http://localhost:8080/api/...

---

## Production Deployment (demo.eisa.com.tr)

### Nginx Reverse Proxy Konfigürasyonu

```nginx
# demo.eisa.com.tr
server {
    listen 80;
    server_name demo.eisa.com.tr;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name demo.eisa.com.tr;

    ssl_certificate /etc/letsencrypt/live/demo.eisa.com.tr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/demo.eisa.com.tr/privkey.pem;

    # Tek container — UI + API aynı origin (8080)
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Docker Compose Başlatma

```powershell
# Production'da
docker compose -f docker-compose.demo.yml --env-file .env up -d
```

---

## Konfigürasyon

### Backend URL Değiştirme

`.env` dosyasında:

```bash
BACKEND_URL=https://api.eisa.com.tr
```

### UI API Endpoint'i

Birleşik container'da UI, API'ye **relative path** (`/api/...`) ile erişir; nginx bu istekleri container içindeki Node servisine proxy'ler. Bu nedenle `VITE_API_BASE` build sırasında boş string (`""`) olarak ayarlanır (Dockerfile içinde sabit).

Ayrı bir backend'e yönlendirme gerekiyorsa `Dockerfile` içindeki `ENV VITE_API_BASE=""` satırı değiştirilebilir.

---

## Servis Yönetimi

```powershell
# Başlat
docker compose -f docker-compose.demo.yml up -d

# Durdur
docker compose -f docker-compose.demo.yml down

# Yeniden başlat
docker compose -f docker-compose.demo.yml restart

# Logları görüntüle (api + nginx birlikte)
docker compose -f docker-compose.demo.yml logs -f kiosk

# Durumu kontrol et
docker compose -f docker-compose.demo.yml ps
```

---

## Volume Yönetimi

SQLite veritabanı ve medya `kiosk-data` volume'ünde (`/var/lib/eisa`), loglar `kiosk-logs` volume'ünde saklanır:

```powershell
# Volume'leri listele
docker volume ls | Select-String eisa-kiosk

# Volume'ü sil (dikkat: tüm veriler silinir!)
docker volume rm kiosk_edge_kiosk-data
```

---

## Sorun Giderme

### Container başlamıyor

```powershell
docker compose -f docker-compose.demo.yml logs kiosk
```

### Health check başarısız

```powershell
# Birleşik health check (nginx)
curl http://localhost:8080/healthz

# API health check (nginx proxy üzerinden)
curl http://localhost:8080/health
```

### SQLite / process erişim sorunu

Container içine girin:

```powershell
docker exec -it eisa-kiosk-demo sh
ls -la /var/lib/eisa/
supervisorctl status
```

---

## Güvenlik Notları

- Demo kiosk kimlik bilgileri (`KIOSK_MAC`, `KIOSK_APP_KEY`) gerçek production'da kullanılmamalı
- `.env` dosyası git'e commit edilmemeli (`.gitignore`'da ekli)
- Production'da SSL/TLS zorunlu (Let's Encrypt)

---

## Geliştirme Notları

Bu Docker yapısı sadece demo içindir. Gerçek kiosk deployment'ı için:
- [PRODUCTION_VIRTUALBOX_DEPLOY.md](PRODUCTION_VIRTUALBOX_DEPLOY.md)
- [OFFLINE_SYNC_PLAN.md](OFFLINE_SYNC_PLAN.md)

Dokümanlarını inceleyin.
