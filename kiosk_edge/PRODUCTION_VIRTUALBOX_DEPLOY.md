# E-ISA Kiosk Production Kurulum (VirtualBox + api.eisa.com.tr)

Bu dokuman, `kiosk_edge` icindeki iki bileseni production'a alir:

- `api-node`: lokal Fastify API + SQLite + scheduler
- `ui`: kiosk ekrani (Svelte, static build)

Hedef: Kiosk cihazinin backend ile `https://api.eisa.com.tr` uzerinden guvenli sekilde senkron calismasi.

## 1) VirtualBox VM Hazirligi

Onerilen VM:

- OS: **Debian 13 (Trixie)** — minimal server kurulum
- CPU: 2 vCPU
- RAM: 2 GB (minimum), 4 GB onerilir
- Disk: 20+ GB
- Network: `Bridged Adapter` (saha aginda IP alabilmesi icin)

Saat/NTP senkronu kritik: playlist ve scheduler icin VM saati dogru olmali.

```bash
# NTP durumu kontrol
timedatectl status
# Gerekirse:
sudo timedatectl set-timezone Europe/Istanbul
```

## 2) Gerekli apt paketleri

```bash
sudo apt update
sudo apt install -y \
  ca-certificates curl gnupg unzip \
  sqlite3 \
  nginx \
  ufw
```

Not: Kiosk runtime icin Python gerekmez. Bu yapi sadece Node.js runtime + SQLite ile calisir.

## 3) Node.js 20 LTS kurulumu

Debian 13 (Trixie) icin NodeSource signed APT repository:

```bash
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
  | sudo gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg

echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] \
https://deb.nodesource.com/node_20.x nodistro main" \
  | sudo tee /etc/apt/sources.list.d/nodesource.list

sudo apt update
sudo apt install -y nodejs
node -v   # v20.x.x olmali
npm  -v
```

## 4) Sistem kullanicisi + dizinler

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin eisa || true
sudo mkdir -p /opt/eisa
sudo mkdir -p /var/lib/eisa/media
sudo mkdir -p /var/log/eisa
sudo mkdir -p /etc/eisa
sudo chown -R eisa:eisa /opt/eisa /var/lib/eisa /var/log/eisa /etc/eisa
```

## 5) Uygulama paketinin cihaza aktarilmasi

Kod cihaza acik olarak gelmez. Gelistirici makinede build alinir,
sifreli arsiv olarak cihaza aktarilir.

### 5a) Gelistirici makinede build olusturma (Windows/Linux)

```bash
# Repo koku
cd kiosk_edge

# API: uretim bagimliliklarini yukle
cd api-node
npm ci --omit=dev
cd ..

# UI: static build
cd ui
npm ci
npm run build
cd ..

# Arsiv olustur (iki parca)
tar -czf eisa-api.tar.gz \
  -C api-node \
  src package.json node_modules

tar -czf eisa-ui.tar.gz \
  -C ui/dist .
```

### 5b) VM'e aktarma (SCP)

```bash
# Gelistirici makineden:
scp eisa-api.tar.gz eisa-ui.tar.gz kullanici@<VM_IP>:/tmp/
```

### 5c) VM uzerinde dizin olusturma ve acma

```bash
sudo mkdir -p /opt/eisa/app/kiosk_edge/api-node
sudo mkdir -p /opt/eisa/app/kiosk_edge/ui/dist
sudo chown -R eisa:eisa /opt/eisa/app

# API
sudo -u eisa tar -xzf /tmp/eisa-api.tar.gz \
  -C /opt/eisa/app/kiosk_edge/api-node

# UI
sudo -u eisa tar -xzf /tmp/eisa-ui.tar.gz \
  -C /opt/eisa/app/kiosk_edge/ui/dist

# Arsifleri temizle
rm /tmp/eisa-api.tar.gz /tmp/eisa-ui.tar.gz
```

## 6) API yapilandirma ve servise alma

Environment dosyasi (`/etc/eisa/kiosk.env`):

```ini
# ── IoT Kimlik Dogrulama ───────────────────────────────────────────────────
# Tum kiosklar ve backend'de AYNI iki deger:
EISA_KIOSK_FLEET_KEY=<FLEET_KEY>              # Fleet kimlik baslik degeri
EISA_KIOSK_PROVISIONING_SECRET=<SECRET>       # HMAC imzasi + App Key provisioning icin

# Kiosk MAC sistemden otomatik okunur; env override yok.

# ── Genel ─────────────────────────────────────────────────────────────────
EISA_SQLITE_PATH=/var/lib/eisa/local.db
EISA_MEDIA_DIR=/var/lib/eisa/media
EISA_CENTRAL_API_BASE=https://api.eisa.com.tr
EISA_PULL_INTERVAL_SEC=900
EISA_PUSH_INTERVAL_SEC=300
EISA_PING_INTERVAL_SEC=60
EISA_VERIFY_TLS=true
EISA_DEV_MODE=false
EISA_HOST=127.0.0.1
EISA_PORT=8765
EISA_LOG_DIR=/var/log/eisa
EISA_LOG_LEVEL=info
EISA_LOG_MAX_SIZE_MB=5
EISA_LOG_MAX_FILES=3
EISA_OUTBOX_MAX_ROWS=10000
```

Ortak deger uretimi (backend .env'ine de ayni degerleri koy):

```bash
openssl rand -hex 32   # FLEET_KEY icin
openssl rand -hex 32   # PROVISIONING_SECRET icin
```

Dosya izinleri:

```bash
sudo chown root:eisa /etc/eisa/kiosk.env
sudo chmod 640 /etc/eisa/kiosk.env
```

Systemd servis kurulumu:

```bash
sudo cp /opt/eisa/app/kiosk_edge/api-node/eisa-api.service /etc/systemd/system/eisa-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now eisa-api
sudo systemctl status eisa-api --no-pager
```

Log izleme:

```bash
sudo journalctl -u eisa-api -f
```

## 7) UI yayina alma

UI dist dosyalari 5. adimda `/opt/eisa/app/kiosk_edge/ui/dist/` altina aktarildi.
Nginx'e serve ettirmek icin kopyala:

```bash
sudo mkdir -p /var/www/eisa-kiosk
sudo rsync -a --delete /opt/eisa/app/kiosk_edge/ui/dist/ /var/www/eisa-kiosk/
```

Nginx site dosyasi (`/etc/nginx/sites-available/eisa-kiosk`):

```nginx
server {
    listen 80;
    server_name _;

    root /var/www/eisa-kiosk;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Aktif et:

```bash
sudo ln -sf /etc/nginx/sites-available/eisa-kiosk /etc/nginx/sites-enabled/eisa-kiosk
sudo nginx -t
sudo systemctl restart nginx
```

## 8) Firewall (minimum)

Kiosk cihazi icin disariya sadece gerekli portlari ac:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 80/tcp
sudo ufw allow 22/tcp
sudo ufw enable
sudo ufw status
```

Lokal API (`127.0.0.1:8765`) dis agdan acilmaz.

## 9) Backend ile guvenli erisim modeli

Kiosk -> Backend tum trafik TLS ile gider (`https://api.eisa.com.tr`).

Uygulanan guvenlikler:

1. **Transport guvenligi**
   - `EISA_VERIFY_TLS=true`
   - Uretimde `http://` endpoint kullanma

2. **App Key provisioning**
   - Her istekte `X-Kiosk-Key: <FLEET_KEY>` — butun cihazlarda ve backend'de ayni
   - Bootstrap akisi:
     - Kiosk MAC'i isletim sisteminden okur
     - `HMAC-SHA256(MAC + timestamp, PROVISIONING_SECRET)` imzalar
     - Backend: HMAC dogrular + timestamp tazelik kontrolu (replay koruma, +/-5 dk)
     - Basarili bootstrap: backend `app_key`, `kiosk_id`, `pharmacy_id` doner
     - App Key SQLite `kiosk_meta`'ya yazilir ve sonraki isteklerde kullanilir

3. **Lokal API korumasi** (eczaci terminali)
   - `/api/oturum/:qr` endpoint'i eczaci tabletinden gelen QR sorgularini korur
   - Gerekli secret ilk acilista kiosk tarafindan otomatik uretilir, SQLite'ta saklanir
   - Manuel yapilandirma gerekmez

4. **Ag ve host sertlestirme**
   - UFW ile sadece gerekli portlar
   - Service non-root user (`eisa`) ile calisir
   - Systemd hardening aktif (`NoNewPrivileges`, `ProtectSystem=strict` vb.)

5. **Veri guvenilirligi**
   - Outbox + idempotency anahtari ile cift gonderim engellenir
   - Offline durumda SQLite outbox'a yazip ag gelince push eder

## 10) Manuel guncelleme (tek cihaz / acil duzeltme)

Gelistirici makinede yeni arsiv olustur (5a adimi) ve cihaza aktar:

```bash
# API guncelleme
scp eisa-api.tar.gz kullanici@<VM_IP>:/tmp/
ssh kullanici@<VM_IP> \
  'sudo -u eisa tar -xzf /tmp/eisa-api.tar.gz \
     -C /opt/eisa/app/kiosk_edge/api-node --overwrite \
   && sudo systemctl restart eisa-api \
   && rm /tmp/eisa-api.tar.gz'

# UI guncelleme
scp eisa-ui.tar.gz kullanici@<VM_IP>:/tmp/
ssh kullanici@<VM_IP> \
  'sudo -u eisa tar -xzf /tmp/eisa-ui.tar.gz \
     -C /opt/eisa/app/kiosk_edge/ui/dist --overwrite \
   && sudo rsync -a --delete \
       /opt/eisa/app/kiosk_edge/ui/dist/ /var/www/eisa-kiosk/ \
   && sudo systemctl reload nginx \
   && rm /tmp/eisa-ui.tar.gz'
```

Cok cihaz icin Mender OTA kullan (asagidaki Bolum 13).

## 11) Dogrulama checklist

- `curl http://127.0.0.1:8765/health` -> `{ "status": "ok" }`
- `journalctl -u eisa-api` icinde pull/push/ping loglari gorunuyor
- `/var/lib/eisa/local.db` olusmus
- UI ana sayfa aciliyor, kategori/soru akisi calisiyor
- Internet kesik durumda akis devam ediyor, internet geri gelince push loglari goruluyor

## 12) Onemli not (SQLite sema hizasi)

`api-node/src/db.js` semasi backend model yapisina hizalanmistir:

- `kategoriler.hedef_cinsiyet_id`
- `sorular.hedef_cinsiyet_id`
- `kategori_hedef_yas_araliklari` (M2M)
- `soru_hedef_yas_araliklari` (M2M)
- `soru_etken_maddeler` (through + `rol`)

Ayrica geri uyumluluk icin eski JSON kolonlari (`hedef_cinsiyetler`, `hedef_yas_araliklari`) korunmustur.

---

## 13) Mender OTA ile cok cihazli dagilim (Open Source)

Mender, kiosk uygulamalarini merkezden OTA (Over-The-Air) guncellemeye yarar.
**Acik kaynak (Community) surumuyle calismaktadir; enterprise ozellikler gerekmez.**

Resmi kaynak: https://github.com/mendersoftware/mender-server

### 13a) Genel mimari

```
Gelistirici makinesi
  └─ mender-artifact CLI → .mender paketi olusturur

Mender Server (ayri sunucu veya Docker)
  └─ Web UI / API → cihazlara dagilim

Kiosk (Debian 13 Trixie)
  └─ mender-client4 → Mender Server'a baglI, guncelleme paketini uygular
```

Kiosk'ta **tam rootfs guncelleme** yapilmaz (A/B partition gerekmez).
Bunun yerine **uygulama duzeyinde Update Module** kullanilir: sadece
`/opt/eisa/app` guncellenip servis yeniden baslatilir.

---

### 13b) Kiosk'a mender-client kurulumu (Debian 13)

```bash
# Mender APT anahtari ve repository (Debian stable uzerinden calisir)
curl -fsSL https://downloads.mender.io/repos/debian/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/mender.gpg

echo "deb [signed-by=/etc/apt/keyrings/mender.gpg] \
https://downloads.mender.io/repos/debian stable main" \
  | sudo tee /etc/apt/sources.list.d/mender.list

sudo apt update
sudo apt install -y mender-client4

# Versiyon kontrol
mender --version
```

Mender servisi:

```bash
sudo systemctl enable --now mender-client
sudo systemctl status mender-client --no-pager
```

---

### 13c) Mender Server kurulumu (Docker Compose, ayri sunucu)

```bash
# Mender server repo
git clone https://github.com/mendersoftware/mender-server.git
cd mender-server

# Minimal uretim config
cp config/enterprise.yml.example config/enterprise.yml  # icerik gereksiz, sadece var olmasi yeterli
docker compose -f docker-compose.yml up -d
```

Varsayilan port: `https://localhost` — DNS/TLS ayarini kendi domain'ine gore yap.
Resmi kurulum rehberi: https://docs.mender.io/server-installation/installation-with-docker-compose

---

### 13d) Kiosk'u Mender Server'a bagla

Mender konfigurasyonu `/etc/mender/mender.conf`:

```json
{
  "ServerURL": "https://mender.eisa.com.tr",
  "TenantToken": "",
  "InventoryPollIntervalSeconds": 1800,
  "UpdatePollIntervalSeconds": 1800,
  "RetryPollIntervalSeconds": 300
}
```

Cihazi server'a onay icin gonder:

```bash
sudo mender bootstrap --forcebootstrap
sudo systemctl restart mender-client
```

Mender Web UI'dan cihazi `Accept` et.

---

### 13e) EISA Update Module olustur

Update Module, guncelleme paketini nasil uygulayacagini tanimlar.
Asagidaki scripti **kiosk'a** yukle:

```bash
sudo mkdir -p /usr/share/mender/modules/v3
sudo tee /usr/share/mender/modules/v3/eisa-app > /dev/null << 'EOF'
#!/bin/bash
set -e
MODULE_DIR="$1"

case "$2" in
  Download)
    ;;
  ArtifactInstall)
    systemctl stop eisa-api || true

    # API paketi
    if [ -f "$MODULE_DIR/eisa-api.tar.gz" ]; then
      tar -xzf "$MODULE_DIR/eisa-api.tar.gz" \
        -C /opt/eisa/app/kiosk_edge/api-node --overwrite
    fi

    # UI paketi
    if [ -f "$MODULE_DIR/eisa-ui.tar.gz" ]; then
      tar -xzf "$MODULE_DIR/eisa-ui.tar.gz" \
        -C /opt/eisa/app/kiosk_edge/ui/dist --overwrite
      rsync -a --delete \
        /opt/eisa/app/kiosk_edge/ui/dist/ /var/www/eisa-kiosk/
      systemctl reload nginx
    fi

    systemctl start eisa-api
    ;;
  ArtifactCommit)
    ;;
  ArtifactRollback)
    systemctl restart eisa-api || true
    ;;
  ArtifactVerifyReboot)
    systemctl is-active --quiet eisa-api
    ;;
esac
exit 0
EOF
sudo chmod +x /usr/share/mender/modules/v3/eisa-app
```

---

### 13f) Gelistirici makinede: mender-artifact CLI kurulumu

```bash
# Linux (veya WSL2)
MENDER_ARTIFACT_VERSION=3.11.1
curl -fsSL \
  "https://downloads.mender.io/mender-artifact/${MENDER_ARTIFACT_VERSION}/linux/mender-artifact" \
  -o /usr/local/bin/mender-artifact
chmod +x /usr/local/bin/mender-artifact
mender-artifact --version
```

---

### 13g) .mender paketi olustur ve dagit

Build + paketleme (gelistirici makinesinde, 5a adimindaki arsivler hazir olmali):

```bash
# Kiosk cihaz tipini tanimla (mender.conf ile eslesmeli)
DEVICE_TYPE="eisa-kiosk"
VERSION="1.2.3"

mender-artifact write module-image \
  --type eisa-app \
  --device-type "${DEVICE_TYPE}" \
  --artifact-name "eisa-app-v${VERSION}" \
  --output-path "eisa-app-v${VERSION}.mender" \
  --file eisa-api.tar.gz \
  --file eisa-ui.tar.gz
```

Mender Server'a yukleme (Web UI veya CLI):

```bash
# CLI ile (mender-cli ayrıca kurulabilir)
mender-cli artifacts upload \
  --server https://mender.eisa.com.tr \
  --username admin@eisa.com.tr \
  --password <SIFRE> \
  eisa-app-v${VERSION}.mender
```

Ardindan Mender Web UI'da:
1. **Releases** → yuklenen paketi gor
2. **Deployments** → `Create deployment`
3. Hedef gruba (veya tek cihaza) dagit
4. Cihazlar otomatik guncelleme alir, servis yeniden baslar

---

### 13h) Mender OTA ozeti

| Adim | Nerede |
|------|--------|
| Build + arsiv olustur | Gelistirici makinesi (Bolum 5a) |
| `.mender` paketi olustur | Gelistirici makinesi (mender-artifact) |
| Paketi Server'a yukle | Mender Web UI / mender-cli |
| Dagilimi tetikle | Mender Web UI |
| Uygulama: servis dur → dosyalar guncelle → servis basla | Kiosk (eisa-app module) |
