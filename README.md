# E-İSA Monorepo

Etkileşimli Sağlık Asistanı — eczane içi kiosk platformu.

Mimari anayasa: [mimar.md](../mimar.md) · Vizyon: [project.md](../project.md) · Yığın: [TechStack.md](../TechStack.md)

## Yapı

```text
e-isa-monorepo/
├── docker-compose.yml      # Traefik + PostgreSQL + Backend
├── backend/                # Django REST Framework (Merkezi API)
├── kiosk_edge/             # Cihaz içi: FastAPI (api/) + Svelte (ui/)
└── web_panels/             # Vue 3 (SuperAdmin + Eczacı)
```

## Hızlı Başlangıç (Geliştirme)

### 1. `.env` dosyasını oluştur

```bash
cp .env.example .env
# .env içindeki değerleri düzenle (geliştirme için varsayılanlar yeterli)
```

### 2. Docker ile tüm merkezi servisleri başlat

```bash
# Traefik olmadan, portlar doğrudan expose edilmiş şekilde
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

| Servis | URL |
|--------|-----|
| Django API | http://localhost:8000 |
| Vue Paneller | http://localhost:8080 |
| PostgreSQL | localhost:5432 |

> İlk başlatmada `migrate` ve `createsuperuser` otomatik çalışır.
> Varsayılan kullanıcı: `admin` / `admin1234` (`.env`'den değiştirilebilir)

### 3. Kiosk Edge (isteğe bağlı, lokal geliştirme)

```bash
# Kiosk API (FastAPI)
cd kiosk_edge/api
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8001

# Kiosk UI (Svelte)
cd kiosk_edge/ui && npm install && npm run dev
```

### Servisleri durdur

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

---

## Test Komutları

### Backend (Django)

```bash
cd backend

# Tüm testleri çalıştır
DJANGO_DEBUG=True DJANGO_SECRET_KEY=dev pytest

# Belirli bir app
DJANGO_DEBUG=True DJANGO_SECRET_KEY=dev pytest apps/pharmacies

# Coverage raporu
DJANGO_DEBUG=True DJANGO_SECRET_KEY=dev pytest --cov=apps --cov-report=term-missing
```

### Kiosk API (FastAPI)

```bash
cd kiosk_edge

# Tüm testleri çalıştır (env değişkenleri gerekli)
PYTHONPATH=.. \
EISA_KIOSK_APP_KEY=test-key \
EISA_KIOSK_MAC=AA:BB:CC:DD:EE:FF \
EISA_CENTRAL_API_BASE=http://127.0.0.1 \
pytest

# Sadece validator testleri
pytest api/tests/test_validators.py

# Sadece endpoint testleri
pytest api/tests/test_endpoints.py
```

### Web Panels (Vue 3)

```bash
cd web_panels

# Testleri çalıştır (Vitest)
npm run test

# Tek seferlik (CI modunda)
npm run test -- --run

# Coverage raporu
npm run test:coverage
```

### Kiosk UI (Svelte)

```bash
cd kiosk_edge/ui

# Testleri çalıştır (Vitest)
npm run test

# Tek seferlik (CI modunda)
npm run test -- --run

# Coverage raporu
npm run test:coverage
```

### Tüm testler (özet)

| Bileşen | Komut | Testler |
|---------|-------|---------|
| Backend | `cd backend && DJANGO_DEBUG=True DJANGO_SECRET_KEY=dev pytest` | 76 |
| Kiosk API | `cd kiosk_edge && PYTHONPATH=.. EISA_KIOSK_APP_KEY=x EISA_KIOSK_MAC=AA:BB:CC:DD:EE:FF EISA_CENTRAL_API_BASE=http://127.0.0.1 pytest` | 47 |
| Web Panels | `cd web_panels && npm run test -- --run` | 7 |
| Kiosk UI | `cd kiosk_edge/ui && npm run test -- --run` | 16 |

## Altın Kurallar

- Kiosk UI yalnızca `127.0.0.1` üzerinden lokal FastAPI ile konuşur.
- Kiosk ↔ Merkez iletişimi MAC eşleşmeli **App-Key** ile yapılır (JWT değil).
- Paneller ↔ Merkez iletişimi **JWT** ile yapılır.
- Offline-First: Svelte UI internet olsa da olmasa da yalnızca lokal API'yi bilir.
- Sistem doğrudan marka/ürün önermez, yalnızca etken madde tavsiye eder.
