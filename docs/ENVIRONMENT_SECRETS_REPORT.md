# E-İSA Monorepo — Environment & Secret Dosyaları Raporu
**Oluşturulma Tarihi:** 2026-07-14  
**Amaç:** Projedeki tüm environment dosyaları ve secret/credential lokasyonlarını dokümante etmek

---

## 📋 İçindekiler

1. [Environment Dosyaları Listesi](#environment-dosyaları-listesi)
2. [Secret & Credential Lokasyonları](#secret--credential-lokasyonları)
3. [Güvenlik Kontrol Listesi](#güvenlik-kontrol-listesi)
4. [Kullanım Önerileri](#kullanım-önerileri)

---

## Environment Dosyaları Listesi

### 🔹 Root Level (Monorepo)
| Dosya | Amaç | Durum |
|-------|------|-------|
| `.env` | Monorepo genel env (gitignore'da) | ⚠️ Lokal kullanım |

### 🔹 Backend (Django + DRF)
| Dosya | Amaç | Durum |
|-------|------|-------|
| `backend/.env.dev` | Development ortamı | ✅ Aktif |
| `backend/.env.prod` | Production ortamı | ✅ Aktif |

**Secrets:**
- `DJANGO_SECRET_KEY` (50+ karakter)
- `POSTGRES_PASSWORD` (24+ karakter)
- `JWT_AUTH_COOKIE`, `JWT_REFRESH_COOKIE`
- `RUSTFS_ACCESS_KEY`, `RUSTFS_SECRET_KEY`
- `EISA_KIOSK_FLEET_KEY`, `EISA_KIOSK_PROVISIONING_SECRET`

### 🔹 Web Panels (Vue 3 + Vite)
| Dosya | Amaç | Durum |
|-------|------|-------|
| `web_panels/.env` | Genel env (fallback) | ✅ Aktif |
| `web_panels/.env.dev` | Development ortamı | ✅ Aktif |
| `web_panels/.env.prod` | Production ortamı | ✅ Aktif |

**Secrets:**
- `VITE_GOOGLE_ANALYTICS_ID`
- `VITE_SENTRY_DSN`
- `VITE_GOOGLE_MAPS_API_KEY` (opsiyonel)
- `VITE_MAPBOX_TOKEN` (opsiyonel)

### 🔹 Kiosk Edge API Node (Node.js + Fastify)
| Dosya | Amaç | Durum |
|-------|------|-------|
| `kiosk_edge/api-node/.env` | Genel env (fallback) | ✅ Aktif |
| `kiosk_edge/api-node/.env.dev` | Development ortamı | ✅ Aktif |
| `kiosk_edge/api-node/.env.prod` | Production ortamı | ✅ Aktif |

**Secrets:**
- `EISA_KIOSK_FLEET_KEY` (Backend ile aynı)
- `EISA_KIOSK_PROVISIONING_SECRET` (Backend ile aynı)
- `KIOSK_MAC` (Her kiosk için unique)
- `KIOSK_APP_KEY` (Provisioning sırasında alınır)

### 🔹 Kiosk Edge UI (Svelte 5 + Vite)
| Dosya | Amaç | Durum |
|-------|------|-------|
| `kiosk_edge/ui/.env` | Genel env (fallback) | ✅ Aktif |
| `kiosk_edge/ui/.env.dev` | Development ortamı | ✅ Aktif |
| `kiosk_edge/ui/.env.prod` | Production ortamı | ✅ Aktif |

**Secrets:** _Yok_ (API base URL ve feature flags sadece)

### 🔹 Kiosk Edge (Legacy/Demo)
| Dosya | Amaç | Durum |
|-------|------|-------|
| `kiosk_edge/.env.demo` | Demo ortamı | ✅ Mevcut |

---

## Secret & Credential Lokasyonları

### 🔐 Kubernetes/Rancher Secrets

#### 1. Backend Production Secrets
**Dosya:** `deploy/eisa-app-production.yaml`  
**Tip:** Secret reference (`envFrom: secretRef`)  
**Secret Adı:** `eisa-app-secrets`

**Secret'ın içermesi gereken değerler:**
```bash
DJANGO_SECRET_KEY
POSTGRES_PASSWORD
RUSTFS_ACCESS_KEY
RUSTFS_SECRET_KEY
EISA_KIOSK_FLEET_KEY
EISA_KIOSK_PROVISIONING_SECRET
JWT_COOKIE_SAMESITE
JWT_COOKIE_SECURE
```

**Oluşturma komutu:**
```bash
kubectl -n eisa-app create secret generic eisa-app-secrets \
  --from-literal=DJANGO_SECRET_KEY='<50+ karakter>' \
  --from-literal=POSTGRES_PASSWORD='<24+ karakter>' \
  --from-literal=RUSTFS_ACCESS_KEY='<s3-access>' \
  --from-literal=RUSTFS_SECRET_KEY='<s3-secret>' \
  --from-literal=EISA_KIOSK_FLEET_KEY='<fleet-key>' \
  --from-literal=EISA_KIOSK_PROVISIONING_SECRET='<prov-secret>'
```

#### 2. Docker Registry Pull Secret
**Dosya:** `deploy/eisa-app-production.yaml` (imagePullSecrets referansı)  
**Secret Adı:** `eisa-regcred`

**Oluşturma komutu:**
```bash
kubectl -n eisa-app create secret docker-registry eisa-regcred \
  --docker-server=ghcr.io \
  --docker-username=<GITHUB_USER> \
  --docker-password=<GHCR_PAT> \
  --docker-email=<EMAIL>
```

#### 3. ConfigMap (Non-Secret)
**Dosya:** `deploy/eisa-app-production.yaml`  
**ConfigMap Adı:** `eisa-app-config`  
**İçerik:** Public environment variables (DB host, allowed hosts, vs.)

---

### 🔐 Lokal Secret Yönetimi

#### Git Ignore Durumu
Aşağıdaki dosyalar `.gitignore` tarafından korunuyor:
- ✅ Tüm `.env*` dosyaları (dev, prod, local varyasyonları)
- ✅ `backend/.env*`
- ✅ `web_panels/.env*`
- ✅ `kiosk_edge/api-node/.env*`
- ✅ `kiosk_edge/ui/.env*`

**Mevcut Gitignore Pattern:**
```gitignore
# Environment files — gerçek secret'lar repo'ya girmesin
.env
.env.local
.env.dev
.env.prod
backend/.env
backend/.env.dev
backend/.env.prod
web_panels/.env
web_panels/.env.dev
web_panels/.env.prod
kiosk_edge/api-node/.env
kiosk_edge/api-node/.env.dev
kiosk_edge/api-node/.env.prod
kiosk_edge/ui/.env
kiosk_edge/ui/.env.dev
kiosk_edge/ui/.env.prod
```

---

## Secret & Credential İnventory

### 🔑 Kritik Secret'lar (Production)

| Secret Adı | Nerede Kullanılır | Format/Uzunluk | Üretim Komutu |
|------------|-------------------|----------------|---------------|
| `DJANGO_SECRET_KEY` | Backend | 50+ karakter | `python -c "import secrets;print(secrets.token_urlsafe(64))"` |
| `POSTGRES_PASSWORD` | Backend | 24+ karakter | `openssl rand -base64 32` |
| `EISA_KIOSK_FLEET_KEY` | Backend + Kiosk API | 32+ karakter (hex) | `openssl rand -hex 32` |
| `EISA_KIOSK_PROVISIONING_SECRET` | Backend + Kiosk API | 32+ karakter | `openssl rand -base64 32` |
| `RUSTFS_ACCESS_KEY` | Backend (S3) | S3 provider'dan | - |
| `RUSTFS_SECRET_KEY` | Backend (S3) | S3 provider'dan | - |
| `JWT_AUTH_COOKIE` | Backend | Cookie adı | Varsayılan: `eisa_access` |
| `JWT_REFRESH_COOKIE` | Backend | Cookie adı | Varsayılan: `eisa_refresh` |
| `GHCR_PAT` | K8s ImagePullSecret | GitHub PAT | GitHub Settings |
| `KIOSK_MAC` | Her kiosk | MAC adresi (unique) | Cihazın gerçek MAC'i |
| `KIOSK_APP_KEY` | Her kiosk | Provisioning'den | Backend otomatik üretir |

### 🔓 Non-Secret Environment Variables

| Variable | Amaç | Örnek Değer |
|----------|------|-------------|
| `DJANGO_DEBUG` | Debug modu | `0` (prod), `1` (dev) |
| `DJANGO_ALLOWED_HOSTS` | İzin verilen hostlar | `api.eisa.com.tr` |
| `POSTGRES_HOST` | DB hostname | `postgres` (K8s), `localhost` (dev) |
| `POSTGRES_PORT` | DB port | `5432` |
| `VITE_API_BASE` | API base URL | `/api` (prod), `http://localhost:8000` (dev) |
| `LOG_LEVEL` | Log seviyesi | `INFO` (prod), `DEBUG` (dev) |

---

## Güvenlik Kontrol Listesi

### ✅ Yapıldı / Yapılacaklar

- [x] Her modül için dev/prod env dosyaları oluşturuldu
- [x] Tüm `.env` dosyaları `.gitignore`'a eklendi
- [x] Secret üretim komutları dokümante edildi
- [x] K8s secret reference'ları belirlendi
- [x] Kullanılmayan email/celery ayarları kaldırıldı
- [x] QR_SECRET kaldırıldı (bit-packing kullanılıyor, şifreleme yok)
- [ ] Production secret'ları K8s cluster'ına deploy edilmeli
- [ ] Sentry DSN üretimde yapılandırılabilir (web_panels)
- [ ] Google Analytics ID üretimde eklenebilir (web_panels)

### 🔒 Güvenlik Best Practices

1. **Asla git'e commit etme:**
   - `.env` dosyaları
   - Gerçek password/token/key değerleri
   - K8s secret YAML dosyaları (sadece ConfigMap commit edilir)

2. **Secret rotasyon:**
   - `DJANGO_SECRET_KEY`: Yılda 1 kez
   - `POSTGRES_PASSWORD`: 6 ayda 1 kez
   - `JWT_*`: Güvenlik olayı sonrası hemen
   - API keys: Provider önerisine göre

3. **Access control:**
   - Production secret'larına sadece DevOps/Admin erişimi
   - K8s RBAC ile secret'lara erişim kısıtlı
   - CI/CD pipeline'da secret injection (vault/sealed-secrets)

4. **Development vs Production:**
   - Dev ortamında weak secret kullanılabilir (test kolaylığı)
   - Production'da mutlaka güçlü, rastgele secret'lar
   - Dev secret'ları asla production'da kullanma

---

## Kullanım Önerileri

### Development Setup

#### Backend
```bash
cd backend
# .env.dev zaten mevcut; isteğe bağlı olarak .env.local olarak kopyala
cp .env.dev .env.local  # (opsiyonel)
# .env.dev veya .env.local dosyasını düzenle (dev değerleri varsayılan olarak yeterli)
source .venv/bin/activate  # veya Windows: .venv\Scripts\activate
python manage.py migrate
python manage.py runserver
```

#### Web Panels
```bash
cd web_panels
# .env.dev zaten mevcut; isteğe bağlı olarak .env.local olarak kopyala
cp .env.dev .env.local  # (opsiyonel)
# .env.dev veya .env.local dosyasını düzenle (genelde boş bırakılabilir, Vite proxy kullanılır)
npm install
npm run dev
```

#### Kiosk API Node
```bash
cd kiosk_edge/api-node
# .env.dev zaten mevcut; isteğe bağlı olarak .env.local olarak kopyala
cp .env.dev .env.local  # (opsiyonel)
# .env.dev veya .env.local dosyasını düzenle
npm install
npm run dev
```

#### Kiosk UI
```bash
cd kiosk_edge/ui
# .env.dev zaten mevcut; isteğe bağlı olarak .env.local olarak kopyala
cp .env.dev .env.local  # (opsiyonel)
# .env.dev veya .env.local dosyasını düzenle
npm install
npm run dev
```

### Production Deployment

1. **Backend Production Secret Oluşturma:**
```bash
# Secret key üret
python -c "import secrets;print(secrets.token_urlsafe(64))"

# K8s secret oluştur
kubectl -n eisa-app create secret generic eisa-app-secrets \
  --from-literal=DJANGO_SECRET_KEY='<üretilen-key>' \
  --from-literal=POSTGRES_PASSWORD='<db-password>' \
  --from-literal=RUSTFS_ACCESS_KEY='<s3-access>' \
  --from-literal=RUSTFS_SECRET_KEY='<s3-secret>' \
  --from-literal=EISA_KIOSK_FLEET_KEY='<fleet-key>' \
  --from-literal=EISA_KIOSK_PROVISIONING_SECRET='<prov-secret>'
```

2. **Web Panels Production Build:**
```bash
cd web_panels
# .env.prod zaten mevcut; production değerlerini güncelle
cp .env.prod .env.production  # (opsiyonel)
npm run build
# dist/ klasörü nginx ile serve edilir
```

3. **Kiosk Production Provisioning:**
```bash
# Her kiosk cihazında:
cd kiosk_edge/api-node
# .env.prod zaten mevcut; production değerlerini güncelle
cp .env.prod .env  # veya doğrudan .env.prod kullan
# KIOSK_MAC değerini cihazın gerçek MAC adresiyle değiştir
# EISA_KIOSK_FLEET_KEY ve EISA_KIOSK_PROVISIONING_SECRET backend ile aynı olmalı
npm run start
```

---

## 📊 Özet İstatistikler

- **Toplam Environment Dosyası:** 12
  - Root: 0 (kaldırıldı)
  - Backend: 2 (.env.dev, .env.prod)
  - Web Panels: 3 (.env, .env.dev, .env.prod)
  - Kiosk API Node: 3 (.env, .env.dev, .env.prod)
  - Kiosk UI: 3 (.env, .env.dev, .env.prod)
  - Kiosk Edge: 1 (.env.demo)

- **Kritik Secret Sayısı:** 10
  - Backend: 6
  - Web Panels: 2
  - Kiosk: 4
  - K8s: 1 (ImagePullSecret - GHCR_PAT)

- **K8s Secret/ConfigMap:** 2
  - `eisa-app-secrets` (Secret)
  - `eisa-app-config` (ConfigMap)

---

## 🔗 İlgili Dökümanlar

- [Backend README](../backend/README.md)
- [Web Panels README](../web_panels/README.md)
- [Kiosk API Node README](../kiosk_edge/api-node/README.md)
- [Rancher Deployment Guide](rancher-deployment-updated.md)
- [Kiosk Mender Golden Image](kiosk-mender-golden-image.md)

---

**Not:** Bu rapor düzenli olarak güncellenmelidir. Yeni secret/env eklendiğinde bu dosyaya eklenmeli.
