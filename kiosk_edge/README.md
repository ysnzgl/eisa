# Kiosk Edge

Eczane kiosk cihazına kurulan offline-first bileşen. İki alt projeden oluşur:

| Alt Proje | Teknoloji | Port |
|-----------|-----------|------|
| `api/` | FastAPI + SQLite (aiosqlite) | `8765` |
| `ui/` | Svelte 5 + Vite | `5173` (geliştirme) |

Svelte UI yalnızca lokal FastAPI ile konuşur (`localhost:8765`). Merkezi API bağlantısı kesilse bile kiosk çalışmaya devam eder.

---

## Lokal Geliştirme

### Gereksinimler

- Python 3.12+
- Node.js 20+

---

### 1. FastAPI — Kiosk API

#### Ortam Değişkenleri

`kiosk_edge/api/` dizinine `.env` dosyası oluşturun:

```env
EISA_KIOSK_APP_KEY=dev-local-key
EISA_KIOSK_MAC=00:11:22:33:44:55
EISA_SQLITE_PATH=./local.db
EISA_CENTRAL_API_BASE=http://localhost:8000
EISA_LOCAL_API_SECRET=dev-local-secret
EISA_VERIFY_TLS=false
EISA_DEV_MODE=true
```

> `EISA_KIOSK_APP_KEY` ve `EISA_KIOSK_MAC` zorunludur. Merkezi backend çalışmıyorsa scheduler hataları loglanır ama uygulama çalışmaya devam eder.

| Değişken | Açıklama | Varsayılan |
|----------|----------|------------|
| `EISA_KIOSK_APP_KEY` | Django panelinden üretilen API anahtarı | — (zorunlu) |
| `EISA_KIOSK_MAC` | Cihaz MAC adresi | — (zorunlu) |
| `EISA_SQLITE_PATH` | SQLite dosya yolu | `/var/lib/eisa/local.db` |
| `EISA_CENTRAL_API_BASE` | Merkezi Django API adresi | `https://api.e-isa.local` |
| `EISA_LOCAL_API_SECRET` | Eczacı uçbirimi QR sorgu sırrı | — |
| `EISA_PULL_INTERVAL_SEC` | Merkez'den veri çekme aralığı (sn) | `900` |
| `EISA_PUSH_INTERVAL_SEC` | Merkez'e log gönderme aralığı (sn) | `300` |
| `EISA_VERIFY_TLS` | TLS sertifika doğrulaması | `true` |
| `EISA_DEV_MODE` | Swagger UI / ReDoc'u açar | `false` |

#### Kurulum ve Başlatma

```bash
cd kiosk_edge

# Sanal ortam
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Bağımlılıklar
pip install -r api/requirements.txt

# Sunucuyu başlat (kiosk_edge/ dizininden)
uvicorn api.main:app --host 127.0.0.1 --port 8765 --reload
```

> `uvicorn` komutunun `kiosk_edge/` dizininden çalıştırılması gerekir; `api` paketi bu dizinde çözümlenir.

**Windows PowerShell'de ortam değişkenlerini elle geçirme:**

```powershell
$env:EISA_KIOSK_APP_KEY="dev-local-key"
$env:EISA_KIOSK_MAC="00:11:22:33:44:55"
$env:EISA_SQLITE_PATH="./local.db"
$env:EISA_CENTRAL_API_BASE="http://localhost:8000"
$env:EISA_LOCAL_API_SECRET="dev-local-secret"
$env:EISA_VERIFY_TLS="false"
$env:EISA_DEV_MODE="true"
uvicorn api.main:app --host 127.0.0.1 --port 8765 --reload
```

Sunucu başladıktan sonra:

| URL | Açıklama |
|-----|----------|
| `http://127.0.0.1:8765/health` | Sağlık kontrolü |
| `http://127.0.0.1:8765/docs` | Swagger UI (`DEV_MODE=true` gerekir) |
| `http://127.0.0.1:8765/redoc` | ReDoc (`DEV_MODE=true` gerekir) |

#### Seed Verisi (İsteğe Bağlı)

Uygulama başlarken SQLite boşsa `master_seed.json` dosyasından otomatik seed yükler. Dosyanın beklenen konumu: `<monorepo_kök>/master_seed.json`.

Dosya yoksa uyarı loglanır, uygulama yine de çalışır.

---

### 2. Svelte UI

```bash
cd kiosk_edge/ui

npm install
npm run dev
```

UI `http://127.0.0.1:5173` adresinde başlar. `vite.config.js` içinde `/api` yolları `http://127.0.0.1:8765`'e proxy edilir — API ayrıca çalışıyor olmalıdır.

#### Diğer UI Komutları

```bash
# Testleri çalıştır
npm test

# Coverage ile test
npm run test:coverage

# Production build
npm run build

# Build önizleme
npm run preview
```

---

## Testler

Testler in-memory SQLite kullanır; merkezi API veya gerçek `.env` gerekmez.

```bash
cd kiosk_edge

# Sanal ortamı etkinleştir
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # macOS / Linux

# Tüm API testlerini çalıştır
pytest

# Belirli bir test dosyası
pytest api/tests/test_endpoints.py -v
pytest api/tests/test_validators.py -v

# Coverage raporu
pytest --cov=api --cov-report=term-missing
```

> `conftest.py` gerekli ortam değişkenlerini otomatik set eder; ayrıca `.env` gerekmez.

**PYTHONPATH notu:** Testleri monorepo kök dizininden çalıştırıyorsanız:

```bash
# Monorepo kökünden
$env:PYTHONPATH="y:\PrivateProjects\eisa"   # Windows PowerShell
pytest kiosk_edge/api/tests/
```

---

## Üretim Dağıtımı (Linux — systemd)

Kiosk cihazına kurulum için `api/eisa-api.service` systemd servis dosyası kullanılır.

```bash
# Nuitka ile derle (opsiyonel — Python gerekmeden çalışır)
bash compile_nuitka.sh

# Servis dosyasını kopyala
sudo cp api/eisa-api.service /etc/systemd/system/

# Ortam dosyasını oluştur
sudo mkdir -p /etc/eisa
sudo nano /etc/eisa/kiosk.env   # EISA_* değişkenlerini gir

# Servisi etkinleştir ve başlat
sudo systemctl daemon-reload
sudo systemctl enable eisa-api
sudo systemctl start eisa-api

# Durum kontrol
sudo systemctl status eisa-api
sudo journalctl -u eisa-api -f
```

---

## Proje Yapısı

```
kiosk_edge/
├── pytest.ini
├── seed_kiosk_standalone.py   # Config olmadan SQLite seed scripti
├── api/
│   ├── main.py                # FastAPI app + endpoint'ler
│   ├── config.py              # pydantic-settings ile env yönetimi
│   ├── database.py            # SQLAlchemy async engine
│   ├── models_local.py        # SQLite tablo modelleri
│   ├── scheduler.py           # APScheduler pull/push görevleri
│   ├── seed_loader.py         # master_seed.json yükleyici
│   ├── eisa-api.service       # systemd servis dosyası
│   ├── requirements.txt
│   └── tests/
│       ├── conftest.py
│       ├── test_endpoints.py
│       └── test_validators.py
└── ui/
    ├── package.json
    ├── vite.config.js         # Proxy: /api → localhost:8765
    └── src/
        ├── main.js
        ├── App.svelte
        ├── stores/
        └── lib/
```
