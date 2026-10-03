# Backend — e-isa Merkezi API

Django REST Framework tabanlı merkezi API. Kimlik doğrulama, eczane yönetimi, anket/kampanya veri akışı ve kiosk senkronizasyonunu yönetir.

## Teknoloji Yığını

| Katman | Araç |
|--------|------|
| Framework | Django 5 + Django REST Framework |
| Veritabanı (prod) | PostgreSQL 16 |
| Veritabanı (test) | SQLite (in-memory) |
| Auth | JWT — `djangorestframework-simplejwt` |
| API Docs | `drf-spectacular` (Swagger/ReDoc) |
| WSGI (prod) | Gunicorn 4 worker |

---

## Lokal Geliştirme (Docker olmadan)

### Gereksinimler

- Python 3.12+
- SQLite (testler için, gömülü gelir)
- PostgreSQL (isteğe bağlı — SQLite yerine kullanmak istiyorsanız)

### Kurulum

```bash
cd backend

# Sanal ortam oluştur ve etkinleştir
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Bağımlılıkları yükle
pip install -r requirements.txt
```

### Ortam Değişkenleri

```bash
# .env oluştur (geliştirme için asgari)
DJANGO_SECRET_KEY=dev-only-insecure-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL yerine SQLite kullanmak istiyorsanız aşağıdakiler zorunlu değil
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=eisa
POSTGRES_USER=eisa
POSTGRES_PASSWORD=eisa
```

> Değişkenleri doğrudan shell'e aktarabilir ya da `backend/` içine `.env` dosyası olarak kaydedebilirsiniz.

### Migrate + Superuser + Sunucu

```bash
# Ortam değişkenlerini set et (PowerShell)
$env:DJANGO_DEBUG="True"; $env:DJANGO_SECRET_KEY="dev-only-key"

# SQLite ile hızlı başlangıç (PostgreSQL gerekmez)
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Sunucu `http://localhost:8000` adresinde başlar.

| Endpoint | Açıklama |
|----------|----------|
| `http://localhost:8000/admin/` | Django Admin |
| `http://localhost:8000/api/schema/swagger-ui/` | Swagger UI |
| `http://localhost:8000/api/schema/redoc/` | ReDoc |

---

## Docker ile Çalıştırma

### Sadece Backend + PostgreSQL (geliştirme)

```bash
# Repo kökünden çalıştırın
cd ..   # eisa/ kök dizini

# .env dosyasını oluşturun (örnek dosyadan)
cp .env.example .env
# .env içinde DJANGO_SECRET_KEY ve POSTGRES_PASSWORD'ü güncelleyin

# Geliştirme compose'unu başlat (Traefik olmadan, portlar expose)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build backend postgres
```

İlk başlatmada şunlar otomatik çalışır:
1. `python manage.py migrate`
2. `python manage.py createsuperuser` (`.env`'deki `DJANGO_SUPERUSER_*` değerleri)

Backend `http://localhost:8000` adresinde erişilebilir olur.

### Tüm Servisleri Başlat

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

### Servis Loglarını İzle

```bash
docker compose logs -f backend
```

### Container İçinde Komut Çalıştır

```bash
# Shell
docker compose exec backend sh

# Migration
docker compose exec backend python manage.py migrate

# Custom management komutu
docker compose exec backend python manage.py <komut>
```

### Servisleri Durdur

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down

# Veritabanı volume'ünü de silmek için
docker compose -f docker-compose.yml -f docker-compose.dev.yml down -v
```

---

## Testler

Testler PostgreSQL bağlantısı gerektirmez; SQLite in-memory veritabanı kullanır.

```bash
cd backend

# Sanal ortamı etkinleştir
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # macOS / Linux

# Tüm testleri çalıştır
pytest

# Belirli bir app
pytest apps/pharmacies
pytest apps/campaigns

# Coverage raporu ile
pytest --cov=apps --cov-report=term-missing

# Belirli bir test dosyası
pytest apps/pharmacies/tests/test_views.py -v
```

> `pytest.ini` `DJANGO_SETTINGS_MODULE=core_api.test_settings` olarak ayarlıdır; ayrıca ortam değişkeni gerekmez.

---

## Proje Yapısı

```
backend/
├── manage.py
├── requirements.txt
├── pytest.ini
├── Dockerfile
├── core_api/
│   ├── settings.py        # Ana ayarlar (decouple ile env okur)
│   ├── test_settings.py   # Test-only SQLite ayarları
│   └── urls.py
└── apps/
    ├── users/             # Özel kullanıcı modeli + JWT auth
    ├── pharmacies/        # Eczane yönetimi, AppKey, izinler
    ├── products/          # Ürün kataloğu
    ├── campaigns/         # Kampanya + reklam yönetimi
    └── analytics/         # Anonim anket logları
```

---

## Kategori Sıralama ve Kiosk Görünümü

Kategori sıralaması `apps/products/models.py` içinde `Kategori.sira` ile yönetilir.

- `sira` minimum `1` olmalıdır.
- Kök kategoriler (`bagli_kategori_id IS NULL`) için benzersiz sıra, yalnızca aynı seviyedeki kök kategoriler arasında kontrol edilir.
- Alt kategoriler için benzersizlik, aynı `bagli_kategori` altındaki `sira` değeri bazındadır.
- Model `ordering = ("bagli_kategori_id", "sira", "ad")` ile çalışır; böylece kiosk cache'i aynı sırayla gelir.
- Kiosk uygulaması `sira` alanını okuyup `ORDER BY COALESCE(bagli_kategori_id, 0), COALESCE(sira, 1), id` mantığıyla listeler.

Bu nedenle üst kategorilerde tekrar eden `sira` değeri kabul edilmez, ama aynı `sira` değeri farklı parent altında tekrar kullanılabilir; aslında bu gereklidir. Yalnızca aynı hiyerarşi seviyesindeki sibling'lar arasında unique olmalıdır.

Kök kategori sıralama güncellemesi için şablon SQL bulunur: `backend/scripts/update_root_category_order.sql`.

```sql
-- PostgreSQL hedefi: backend/scripts/update_root_category_order.sql
-- Kök kategori sıralarını istenen düzene göre günceller.
```

Script'i canlı veritabanına uygularken önce hedef kayıtların mevcut olduğu kontrol edilir; ardından root `sira` alanları geçici olarak kaydırılır ve istenen düzen uygulanır. Bu, kiosk'taki 3 kolonlu ana liste için gerekli görünümü korur.

---

## Üretim Notu

Üretimde şu değişkenler **zorunludur**:

| Değişken | Açıklama |
|----------|----------|
| `DJANGO_SECRET_KEY` | 50+ karakter rastgele string |
| `DJANGO_DEBUG` | `0` veya `False` |
| `DJANGO_ALLOWED_HOSTS` | Gerçek domain(ler) |
| `DJANGO_CORS_ORIGINS` | Panel domain(leri) — `https://` ile |
| `POSTGRES_PASSWORD` | 24+ karakter güçlü parola |

Üretim imajı Gunicorn ile çalışır (`CMD` Dockerfile'da tanımlıdır). Traefik reverse-proxy ile HTTPS sonlandırması `docker-compose.yml` içinde yapılandırılmıştır.
