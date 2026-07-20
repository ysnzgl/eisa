# E-ISA Kiosk — Mender Convert, Debian 13 Kurulum ve Golden Image Rehberi

> **Kapsam**: Bu belge, `kiosk_edge/` altındaki Node.js/Fastify API ve Svelte UI'nin bir Debian 13 (Trixie) tabanlı kiosk cihazına nasıl paketleneceğini, **mender-convert** ile A/B OTA güncellemesi destekli bir disk imajına nasıl dönüştürüleceğini ve **Golden Image** olarak nasıl arşivleneceğini açıklar.  
> **Build makinesi**: Intel Core i7, x86-64, Linux (Ubuntu 22.04+)  
> **Hedef kiosk donanımı**: Intel Core i5, x86-64, endüstriyel mini-PC / kiosk kasası  
> Her iki taraf da aynı ISA'yı (amd64) paylaştığından çapraz derleme (cross-compile) gerekmez.

---

## İçindekiler

1. [Mimari Genel Bakış](#1-mimari-genel-bakış)
2. [Gereksinimler](#2-gereksinimler)
3. [Taban Debian 13 İmajının Hazırlanması](#3-taban-debian-13-i̇majının-hazırlanması)
4. [Kiosk Yazılımının Build Edilmesi](#4-kiosk-yazılımının-build-edilmesi)
5. [mender-convert ile OTA İmajı Oluşturma](#5-mender-convert-ile-ota-i̇majı-oluşturma)
6. [Golden Image Oluşturma ve Arşivleme](#6-golden-image-oluşturma-ve-arşivleme)
7. [Provision Script — Kiosk Kimlik Bilgileri](#7-provision-script--kiosk-kimlik-bilgileri)
8. [OTA Güncelleme Akışı](#8-ota-güncelleme-akışı)
9. [Dizin Yapısı Referansı](#9-dizin-yapısı-referansı)
10. [On-Prem Mender Server — k3s Kurulumu](#10-on-prem-mender-server--k3s-kurulumu)

---

## 1. Mimari Genel Bakış

```
┌─────────────────────────────────────────────────────────────────┐
│  KIOSK CİHAZI (Debian 13, Mender A/B)                          │
│                                                                 │
│  ┌─────────────────────┐    ┌──────────────────────────────┐   │
│  │  Svelte UI           │    │  eisa-api  (systemd)         │   │
│  │  (statik dosyalar,   │◄──►│  Fastify  :8765              │   │
│  │   Chromium kiosk)   │    │  better-sqlite3  (offline)   │   │
│  └─────────────────────┘    └──────────┬─────────────────┘   │
│                                         │ HTTPS (pull/push)    │
│  ┌──────────────────────────────────┐   │                      │
│  │  Mender Client (mender-updated) │   │                      │
│  │  A/B rootfs • data partition    │   │                      │
│  └──────────────────────────────────┘   │                      │
└─────────────────────────────────────────┼───────────────────────┘
                                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  CLOUD / ON-PREM (Docker Compose)                               │
│  Traefik → Django DRF  →  PostgreSQL                            │
│             (backend/)                                          │
│  Vue3 Admin Panel  (web_panels/)                                │
│  Mender Server  (on-prem)               │
└─────────────────────────────────────────────────────────────────┘
```

### Kiosk İçindeki Disk Bölümleri (Mender A/B)

| Bölüm     | Boyut   | Açıklama                                    |
|-----------|---------|---------------------------------------------|
| `boot`    | ~256 MB | U-Boot / GRUB, zaman içinde değişmez        |
| `rootfs-A`| ~4 GB   | Aktif rootfs (çalışan sistem)               |
| `rootfs-B`| ~4 GB   | Pasif rootfs (OTA hedef bölümü)             |
| `data`    | Kalan   | `/var/lib/eisa` (SQLite, medya cache) — OTA |
|           |         | güncellemelerinden etkilenmez               |

---

## 2. Gereksinimler

### Build Makinesi (Intel Core i7, x86-64)

```bash
# Ubuntu 22.04 LTS veya Debian 12+ (native x86-64 — cross-compile gerekmez)
sudo apt-get install --no-install-recommends \
  bmap-tools mount util-linux xz-utils \
  parted kpartx dosfstools e2fsprogs   # imaj bölümleme araçları

# Node.js 20 LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# mender-convert (Docker ile çalışır — Docker Engine gerekli)
git clone https://github.com/mendersoftware/mender-convert.git
cd mender-convert
```

> **Not**: Build makinesi (i7) ve hedef (i5) her ikisi de `x86-64 (amd64)` olduğundan `qemu-user-static` veya başka cross-compile araçlarına gerek yoktur. `npm ci` komutu doğrudan hedef uyumlu native binary üretir.

### Mender Sunucusu

- **On-prem Mender** — `docker-compose` ile aynı sunucuya kurulabilir.
  ```
  git clone https://github.com/mendersoftware/mender-server
  cd mender-server && ./run up -d
  ```

> **Not**: Mender Sunucu adresini ileride `MENDER_SERVER_URL` ortam değişkeni ile sağlayacaksınız.

### Kiosk Çevre Birimleri (USB)

| Cihaz | Arayüz | Protokol / Sınıf | Sürücü |
|-------|--------|-------------------|--------|
| Termal yazıcı | USB 2.0 Type-B | ESC/POS — USB Printer Class `07` | Sürücüsüz (`libusb`) |
| Barkod okuyucu | USB 2.0 HID | HID Keyboard Emulation | Plug-and-play (HID) |

**Termal Yazıcı Minimum Özellikleri:**

| Özellik | Değer |
|---------|-------|
| Kağıt genişliği | 80 mm |
| Çözünürlük | ≥ 203 DPI |
| Hız | ≥ 150 mm/s |
| Protokol | ESC/POS (Epson uyumlu) |
| USB Sınıfı | `bDeviceClass=07` (Printer Class) veya CDC-ACM |
| Güç | Bus-powered (500 mA) veya adaptörlü |

> Test edilen modeller: **Epson TM-T20III** (USB, `04b8:0e1f`), **Bixolon SRP-350V** (`1504:0006`), **Star TSP143III** (`0519:0003`)  
> Node.js tarafı: [`@node-escpos/core`](https://github.com/node-escpos/driver) + `@node-escpos/usb-adapter` (libusb üzerinden doğrudan USB — CUPS kurulumu gerekmez)

**Barkod Okuyucu Minimum Özellikleri:**

| Özellik | Değer |
|---------|-------|
| Okuma tipi | 1D: Code 128, EAN-13, EAN-8 — 2D: QR Code, Data Matrix tercih edilir |
| Mod | **HID Keyboard Emulation** (plug-and-play, kernel sürücüsü gerekmez) |
| Tetikleyici | Auto-sense / sürekli tarama veya tuşlu |
| USB Sınıfı | `bInterfaceClass=03` (HID) |

> Test edilen modeller: **Honeywell Voyager 1250g**, **Zebra DS2208**, **Datalogic QuickScan QD2430**  
> Chromium kiosk modunda barkod okuyucu tuş basımı olarak alınır; Svelte UI `document.addEventListener('keydown', ...)` ile yakalar. Node.js doğrudan okuma gerekirse `hidraw` veya `evdev` arabirimi kullanılır (bkz. §5.2 udev kuralları).

---

## 3. Taban Debian 13 İmajının Hazırlanması

> Taban imaj, **VirtualBox'ta elle kurulan Debian 13**'ten türetilir. Cloud imaj + chroot yerine gerçek kurulum → VDI export iş akışı kullanılır; kurulumun gerçek donanım konfigürasyonunu yansıtması sağlanır.

### 3a. VirtualBox VM Ayarları

VirtualBox'ta aşağıdaki ayarlarla yeni bir VM oluşturun:

| Ayar | Değer |
|------|-------|
| Ad | `eisa-kiosk-base` |
| Tür / Sürüm | Linux / Debian (64-bit) |
| RAM | 2048 MB |
| Disk | VDI, Dinamik, **12 GB** |
| Firmware | **EFI (UEFI) — zorunlu** |
| Ağ Adaptörü | NAT (paket indirme için) |

> **⚠️ UEFI zorunlu**: VM Ayarları → Sistem → Anakart → **EFI'yi Etkinleştir** seçeneğini işaretleyin.  
> mender-convert `MENDER_GRUB_EFI_INTEGRATION=y` ile UEFI önyükleme bekler; legacy BIOS ile üretilen imaj kiosk donanımında boot etmez.

**Debian 13 Trixie Netinstall ISO:**

```
https://cdimage.debian.org/cdimage/trixie_di_rc1/amd64/iso-cd/
# → debian-trixie-DI-rc1-amd64-netinst.iso
```

**Kurulum sihirbazı adımları:**

1. ISO'yu VirtualBox optik sürücüsüne ekleyin, VM'i başlatın.
2. Dil / Bölge / Klavye: sisteme göre seçin.
3. Ağ: DHCP (NAT ile otomatik).
4. Kullanıcı: `eisa-admin` (sudo yetkili) oluşturun — root şifresi **devre dışı** bırakın.
5. Disk bölümlendirme: **Guided — use entire disk** (LVM ve şifreleme yok).
6. Yazılım seçimi (tasksel):
   - ☑ `SSH server`
   - ☑ `standard system utilities`
   - ✗ Masaüstü ortamı **seçmeyin** (X11 ve Openbox'ı biz elle kuracağız)
7. Kurulum tamamlanınca ISO'yu çıkarın, VM'i yeniden başlatın.

### 3b. Gerekli Paketlerin Kurulumu (VM İçinde)

VM'in IP adresini öğrenin ve SSH ile bağlanıp root'a geçin:

```bash
# VM konsolunda IP'yi öğrenmek için:
ip addr show

# Build makinesinden SSH:
ssh eisa-admin@<VM_IP>
sudo -i
```

Ardından aşağıdaki komutları **sırayla root olarak** çalıştırın:

```bash
# ── Temel sistem güncellemesi ───────────────────────────────────
apt-get update && apt-get upgrade -y

# ── Temel araçlar (SSH server + utilities kurulumundan eksik) ─────
apt-get install -y --no-install-recommends \
  sudo \
  curl wget ca-certificates gnupg lsb-release \
  apt-transport-https \
  dbus dbus-x11 \
  ufw \
  systemd-timesyncd \
  logrotate \
  cron \
  rsyslog

# ── Network Manager (WiFi yönetimi + polkit kuralı) ───────────────
apt-get install -y --no-install-recommends \
  network-manager \
  wpasupplicant

# ── Node.js 20 LTS (nodesource deposu) ────────────────────────────
# Debian minimal kurulumda Node.js yoktur; resmi depodan yükleyin.
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs
npm install -g npm@latest

# ── X11 / Xorg (minimal, GPU sürücüsüyle) ────────────────────────
apt-get install -y --no-install-recommends \
  xorg \
  xinit \
  x11-xserver-utils \
  xserver-xorg-video-intel \
  xserver-xorg-input-libinput \
  xserver-xorg-input-evdev

# ── Openbox pencere yöneticisi ve yardımcı araçlar ────────────────
apt-get install -y --no-install-recommends \
  openbox \
  obconf \
  unclutter \
  xdotool \
  xdg-utils

# ── Chromium ve render bağımlılıkları ─────────────────────────────
apt-get install -y --no-install-recommends \
  chromium \
  chromium-sandbox \
  fonts-liberation \
  fonts-noto-core \
  libnss3 \
  libatk1.0-0 \
  libatk-bridge2.0-0 \
  libdrm2 \
  libxkbcommon0 \
  libgbm1 \
  libxss1 \
  libasound2

# ── Intel i5 donanım ve mikrokod ──────────────────────────────────
apt-get install -y --no-install-recommends \
  intel-microcode \
  firmware-misc-nonfree \
  i965-va-driver \
  vainfo

# ── Yazıcı ve USB çevre birimi desteği ───────────────────────────
# Termal yazıcı: libusb ile doğrudan USB erişimi (ESC/POS over USB, CUPS gerekmez)
# Barkod okuyucu: HID keyboard emulation — X11 üzerinden otomatik tanınır
apt-get install -y --no-install-recommends \
  libusb-1.0-0 \
  libcups2

# ── Güvenlik araçları ─────────────────────────────────────────────
apt-get install -y --no-install-recommends \
  fail2ban \
  apt-listchanges \
  debsums

# Gereksiz önerilenleri temizle
apt-get autoremove -y && apt-get clean

# Node.js sürüm kontrolü (>=20 gerekli)
node --version

# ── Uygulama kullanıcısı ve dizin yapısı ──────────────────────
# Ayrı bir sistem kullanıcısı (eisaapp) oluşturulur çünkü:
#   • Principle of least privilege: API süreci root yetkisiyle çalışmaz.
#   • Servis izolasyonu: bir güvenlik açığı root erişimi vermez.
#   • Dosya sahipliği: /opt/eisa ve /data/eisa yalnızca eisaapp'e aittir.
# "eisa" proje adıdır; "eisaapp" ise sadece bu servise özgü OS kullanıcısıdır.
useradd -r -m -d /opt/eisa -s /usr/sbin/nologin eisaapp
install -d -o eisaapp -g eisaapp -m 0750 /opt/eisa/api
install -d -o eisaapp -g eisaapp -m 0755 /opt/eisa/ui
install -d -o eisaapp -g eisaapp -m 0750 /var/lib/eisa
install -d -o root    -g root    -m 0750 /etc/eisa
install -d -o root    -g root    -m 0755 /var/log/eisa

# eisaapp kullanıcısını USB yazıcı (lp) ve giriş aygıtı (input) gruplarına ekle
usermod -aG lp,input eisaapp

# ── E-ISA API dosyalarını kopyala (önceki build'den) ─────────────
# Bu adım overlay script'te yapılır (§5.2'ye bakın)

# ── Güvenlik duvarı ───────────────────────────────────────────
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH (golden image sonrası kaldırılabilir)
ufw allow 8765/tcp  # Lokal API (yalnızca 127.0.0.1'e kısıtlı — config.js)
ufw --force enable

# ── Gereksiz servisleri devre dışı bırak ──────────────────────────
systemctl disable bluetooth 2>/dev/null || true
systemctl disable avahi-daemon 2>/dev/null || true
systemctl disable cups 2>/dev/null || true
systemctl disable ModemManager 2>/dev/null || true
```

### 3c. Mender Client Kurulumu (VM İçinde)

Mender client **imaj içine** kurulur. Cihaz açılışta Mender sunucusuna otomatik bağlanır.

```bash
# §3b ile aynı SSH oturumunda (root olarak) çalıştırın:

# Mender apt deposunu ekle (doğrudan .deb indirme 403 döner — resmi yol apt repo)
curl -fsSL https://downloads.mender.io/repos/debian/gpg \
  | gpg --dearmor -o /usr/share/keyrings/mender-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/mender-archive-keyring.gpg] \
  https://downloads.mender.io/repos/debian stable main" \
  > /etc/apt/sources.list.d/mender.list
apt-get update

# Sabit sürümü kur (4.0.4 — production-tested)
apt-get install -y mender-client4=4.0.4-1

# Mender konfigürasyon şablonu oluştur
# Gerçek Server URL ve Tenant Token provision sırasında inject edilir (§7)
cat > /etc/mender/mender.conf << 'MENDER_CONF'
{
  "ServerURL": "MENDER_SERVER_URL_PLACEHOLDER",
  "TenantToken": "MENDER_TENANT_TOKEN_PLACEHOLDER",
  "DeviceTypeFile": "/var/lib/mender/device_type",
  "ArtifactInfoFile": "/etc/mender/artifact_info",
  "UpdatePollIntervalSeconds": 1800,
  "InventoryPollIntervalSeconds": 28800,
  "RetryPollIntervalSeconds": 300,
  "StateScriptTimeout": 120,
  "StateScriptRetryTimeout": 300
}
MENDER_CONF

# Cihaz tipi tanımla
mkdir -p /var/lib/mender
echo "device_type=eisa-kiosk" > /var/lib/mender/device_type
```

### 3d. VDI → Raw İmaj Aktarımı (mender-convert için)

Tüm adımlar VM'de tamamlandıktan sonra VM'i **kapatın**:

```bash
# VM içinde:
shutdown -h now
```

VirtualBox VDI dosyasını raw `.img` formatına dönüştürün:

**Windows'ta (PowerShell — build makinesi):**

```powershell
# VDI yolu: VirtualBox VMs dizinine göre değiştirin
& "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" clonemedium disk `
    "$env:USERPROFILE\VirtualBox VMs\eisa-kiosk-base\eisa-kiosk-base.vdi" `
    "debian-13-base.img" `
    --format RAW

# Dosya boyutu kontrolü (12 GB civarı olmalı)
Get-Item .\debian-13-base.img | Select-Object Name, @{N='GB';E={[math]::Round($_.Length/1GB,1)}}
```

**Linux'ta (Ubuntu build makinesi):**

```bash
VBoxManage clonemedium disk \
  ~/VirtualBox\ VMs/eisa-kiosk-base/eisa-kiosk-base.vdi \
  debian-13-base.img --format RAW

ls -lh debian-13-base.img
```

> `debian-13-base.img` artık §5.3'teki `docker-mender-convert` komutuna doğrudan girdi olarak verilir. VDI → raw dönüşüm disk boyutu kadar alan kaplar (~12 GB); build makinesinde yeterli yer olduğundan emin olun.

---

## 4. Kiosk Yazılımının Build Edilmesi

Build adımları `kiosk_edge/` klasöründe gerçekleştirilir. Sonuç dosyaları geçici bir `dist/` klasörüne toplanır.

```bash
# Depo kökünden başlayın
REPO_ROOT=$(pwd)
DIST_DIR="$REPO_ROOT/kiosk_edge/.build"
mkdir -p "$DIST_DIR"

# ── 1. Svelte UI production build ────────────────────────────────
cd "$REPO_ROOT/kiosk_edge/ui"
npm ci
npm run build
# Çıktı: kiosk_edge/ui/dist/  (statik HTML/JS/CSS)
cp -r dist "$DIST_DIR/ui-static"

# ── 2. Node.js API hazırlama ──────────────────────────────────
cd "$REPO_ROOT/kiosk_edge/api-node"
npm ci --omit=dev          # devDependencies hariç
# Kaynak dosyaları ve node_modules'ı dist'e kopyala
mkdir -p "$DIST_DIR/api"
cp -r src node_modules package.json "$DIST_DIR/api/"

# ── 3. systemd servis dosyasını kopyala ───────────────────────────
cp "$REPO_ROOT/kiosk_edge/api-node/eisa-api.service" "$DIST_DIR/"

echo "Build tamamlandı: $DIST_DIR"
```

> **Not**: `better-sqlite3` native C++ addon içerir. Build makinesi (i7) ve hedef (i5) aynı `linux-x64` mimarisinde olduğundan `npm ci` ile üretilen binary **doğrudan çalışır**; ayrıca rebuild gerekmez. Kurulum sonrası hızlı doğrulama:
> ```bash
> node -e "require('better-sqlite3')(':memory:').close(); console.log('OK')"
> ```

---

## 5. mender-convert ile OTA İmajı Oluşturma

`mender-convert`, mevcut bir Debian imajını alıp A/B bölümlü Mender-uyumlu imaja dönüştürür.

### 5.1 Yapılandırma Dosyaları

```
mender-convert/
└── configs/
    └── eisa-kiosk.cfg          ← kiosk özel config
└── scripts/
    └── eisa-overlay.sh         ← kiosk yazılımı inject scripti
```

**`mender-convert/configs/eisa-kiosk.cfg`**:

```bash
# E-ISA Kiosk — mender-convert konfigürasyonu (Intel i5 x86-64 / amd64)
MENDER_ARTIFACT_NAME="eisa-kiosk-$(date +%Y%m%d)-v1.0.0"

# Hedef: Intel i5 x86-64, UEFI GRUB bootloader
MENDER_GRUB_EFI_INTEGRATION=y

# Bölüm boyutları (MB) — NVMe/SSD kiosk depolama
MENDER_STORAGE_TOTAL_SIZE_MB=32768    # 32 GB SSD (i5 mini-PC standart)
MENDER_DATA_PART_SIZE_MB=16384        # /data bölümü (SQLite + medya cache)
MENDER_BOOT_PART_SIZE_MB=512          # EFI bölümü (x86-64 UEFI gereksinimi)

# Dosya sistemi
MENDER_ROOT_PART_FSTYPE="ext4"
MENDER_DATA_PART_FSTYPE="ext4"

# Data bölümü mount point'i
MENDER_DATA_PART_MOUNT_POINT="/data"

# SQLite ve loglar kalıcı data bölümünde duracak
# Bunun için imaj içinde bind-mount kurarız (overlay script'te)

# OTA güncelleme state script'leri
MENDER_STATE_SCRIPTS_DIR="/etc/mender/scripts"
```

### 5.2 Overlay Script

**`mender-convert/scripts/eisa-overlay.sh`**:

```bash
#!/bin/bash
# Bu script mender-convert tarafından rootfs mount ediliyken çağrılır.
# $1 = rootfs mount point (örn: /tmp/mender-convert-rootfs)

set -euo pipefail
ROOT="$1"
DIST_DIR="$(dirname "$0")/../../kiosk_edge/.build"

# ── E-ISA API dosyalarını kopyala ──────────────────────────────────
cp -r "$DIST_DIR/api/"* "$ROOT/opt/eisa/api/"
chown -R eisaapp:eisaapp "$ROOT/opt/eisa/api"

# ── Svelte UI statik dosyalarını kopyala ───────────────────────────
cp -r "$DIST_DIR/ui-static/"* "$ROOT/opt/eisa/ui/"
chown -R eisaapp:eisaapp "$ROOT/opt/eisa/ui"

# ── systemd servis dosyasını kopyala ──────────────────────────────
cp "$DIST_DIR/eisa-api.service" "$ROOT/etc/systemd/system/"
ln -sf /etc/systemd/system/eisa-api.service \
       "$ROOT/etc/systemd/system/multi-user.target.wants/eisa-api.service"

# ── /var/lib/eisa → /data/eisa semlink (data bölümü kalıcı) ───────
# Bu bind-mount fstab ile sağlanır
cat >> "$ROOT/etc/fstab" << 'FSTAB'
/data/eisa    /var/lib/eisa  none  bind,x-systemd.requires=/data  0  0
/data/log     /var/log/eisa  none  bind,x-systemd.requires=/data  0  0
FSTAB

# ── data bölümü ilk açılış init scripti ───────────────────────────
cat > "$ROOT/usr/local/bin/eisa-data-init.sh" << 'INIT_SCRIPT'
#!/bin/bash
# /data bölümü ilk açılışta boşsa dizinleri oluştur
set -e
[ -d /data/eisa ] || install -d -o eisaapp -g eisaapp -m 0750 /data/eisa
[ -d /data/log  ] || install -d -o eisaapp -g eisaapp -m 0755 /data/log
INIT_SCRIPT
chmod +x "$ROOT/usr/local/bin/eisa-data-init.sh"

cat > "$ROOT/etc/systemd/system/eisa-data-init.service" << 'SYSDSVC'
[Unit]
Description=E-ISA Data Partition Init
After=data.mount
Before=eisa-api.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/eisa-data-init.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
SYSDSVC
ln -sf /etc/systemd/system/eisa-data-init.service \
       "$ROOT/etc/systemd/system/multi-user.target.wants/eisa-data-init.service"

# ── Chromium kiosk modu başlatıcı ─────────────────────────────────
mkdir -p "$ROOT/etc/xdg/openbox"
cat > "$ROOT/etc/xdg/openbox/autostart" << 'OB_AUTOSTART'
# Fare imlecini gizle
unclutter -idle 0.1 -root &

# ── DİKEY (PORTRAIT) EKRAN ROTASYONU ────────────────────────────
# Kiosk ekranı fiziksel olarak 90° saat yönünde döndürülmüş montajda.
# xrandr ile yazılımsal rotasyon: 'right' = saat yönü 90° (portrait).
# Ekran çıkışını otomatik bul (HDMI-1, DP-1, eDP-1 vb.)
DISP=$(xrandr 2>/dev/null | awk '/ connected/{print $1; exit}')
if [ -n "$DISP" ]; then
  xrandr --output "${DISP}" --rotate right
fi

# Dokunmatik ekran varsa koordinat matrisini de döndür (90° CW)
# Matrisi: [ 0  1  0 | -1  0  1 | 0  0  1 ]  (90° saat yönü)
xinput --list --name-only 2>/dev/null | while IFS= read -r dev; do
  case "$dev" in
    *[Tt]ouch*|*[Tt]ouch[Ss]creen*|*ELAN*|*Goodix*)
      xinput set-prop "$dev" 'Coordinate Transformation Matrix' \
        0 1 0 -1 0 1 0 0 1 2>/dev/null && \
        echo "[eisa] touch rotated: $dev" ;;
  esac
done

# E-ISA API hazır olana kadar bekle
until curl -sf http://127.0.0.1:8765/health > /dev/null 2>&1; do
  sleep 1
done

# Chromium kiosk modunda Svelte UI'yi aç (portrait çözünürlük: 1080×1920)
chromium \
  --kiosk \
  --no-sandbox \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-features=TranslateUI \
  --window-size=1080,1920 \
  --app=file:///opt/eisa/ui/index.html \
  &
OB_AUTOSTART

# .xinitrc (eisaapp uygulama kullanıcısı için)
cat > "$ROOT/opt/eisa/.xinitrc" << 'XINITRC'
exec openbox-session
XINITRC
chown eisaapp:eisaapp "$ROOT/opt/eisa/.xinitrc"

# ── WiFi yönetimi — polkit kuralı ─────────────────────────────────
# eisaapp kullanıcısının nmcli aracılığıyla NetworkManager'ı kullanabilmesi
# için gereklidir. Kiosk ilk açılışta internet yoksa WiFi kurulum ekranı
# gösterilir; nmcli yetkisi olmadan WiFi bağlanamaz.
mkdir -p "$ROOT/etc/polkit-1/rules.d"
cat > "$ROOT/etc/polkit-1/rules.d/60-eisa-wifi.rules" << 'POLKIT_RULES'
polkit.addRule(function(action, subject) {
  if (action.id.indexOf("org.freedesktop.NetworkManager") === 0 &&
      subject.user === "eisaapp") {
    return polkit.Result.YES;
  }
});
POLKIT_RULES
chmod 644 "$ROOT/etc/polkit-1/rules.d/60-eisa-wifi.rules"

# NetworkManager'ın kiosk başlamadan önce hazır olduğundan emin ol
ln -sf /lib/systemd/system/NetworkManager.service \
       "$ROOT/etc/systemd/system/multi-user.target.wants/NetworkManager.service" 2>/dev/null || true


cat > "$ROOT/etc/eisa/kiosk.env" << 'KIOSK_ENV'
# Bu dosya provision scripti tarafından cihaza özgü değerlerle doldurulur.
# Asla boş değerlerle bırakmayın!
EISA_KIOSK_FLEET_KEY=PROVISION_REQUIRED
EISA_KIOSK_PROVISIONING_SECRET=PROVISION_REQUIRED
EISA_SQLITE_PATH=/data/eisa/local.db
EISA_CENTRAL_API_BASE=PROVISION_REQUIRED
EISA_PULL_INTERVAL_SEC=900
EISA_PUSH_INTERVAL_SEC=300
EISA_PING_INTERVAL_SEC=60
EISA_VERIFY_TLS=true
EISA_DEV_MODE=false
EISA_HOST=127.0.0.1
EISA_PORT=8765
EISA_LOG_DIR=/data/log
EISA_LOG_LEVEL=info
KIOSK_ENV
chmod 640 "$ROOT/etc/eisa/kiosk.env"
chown root:eisaapp "$ROOT/etc/eisa/kiosk.env"

# ── USB çevre birimi udev kuralları ───────────────────────────────
# eisaapp kullanıcısı lp ve input grupları üzerinden erişim sağlar.
mkdir -p "$ROOT/etc/udev/rules.d"
cat > "$ROOT/etc/udev/rules.d/99-eisa-usb-peripherals.rules" << 'UDEV_RULES'
# ── Termal yazıcı — USB Printer Class 07 ─────────────────────────
# Genel ESC/POS uyumlu USB yazıcılar
SUBSYSTEM=="usb", ATTR{bDeviceClass}=="07", GROUP="lp", MODE="0664"
SUBSYSTEM=="usbmisc", KERNEL=="lp[0-9]*", GROUP="lp", MODE="0664"

# Epson TM serisi (vendorId: 04b8)
SUBSYSTEM=="usb", ATTRS{idVendor}=="04b8", GROUP="lp", MODE="0664"
# Bixolon (vendorId: 1504)
SUBSYSTEM=="usb", ATTRS{idVendor}=="1504", GROUP="lp", MODE="0664"
# Star Micronics (vendorId: 0519)
SUBSYSTEM=="usb", ATTRS{idVendor}=="0519", GROUP="lp", MODE="0664"

# ── Barkod okuyucu — USB HID ──────────────────────────────────────
# hidraw arabirimi — Node.js doğrudan HID okuma için (opsiyonel)
SUBSYSTEM=="hidraw", GROUP="input", MODE="0664"
# input event arabirimi — evdev ile okuma için
SUBSYSTEM=="input", KERNEL=="event[0-9]*", GROUP="input", MODE="0664"
UDEV_RULES
chmod 644 "$ROOT/etc/udev/rules.d/99-eisa-usb-peripherals.rules"

echo "[eisa-overlay] Tamamlandı."
```

### 5.3 mender-convert Çalıştırma

> Build makinesi **i7 (amd64)**, hedef **i5 (amd64)** — tek komut yeterlidir.

```bash
cd mender-convert

# Build artefaktını hazırla (§4)
cd ../e-isa-monorepo && ./build-kiosk.sh && cd ../mender-convert

# Intel i5 x86-64 (amd64) — UEFI GRUB:
MENDER_ARTIFACT_NAME="eisa-kiosk-$(date +%Y%m%d)-v1.0.0" \
MENDER_DEVICE_TYPE="eisa-kiosk-i5-amd64" \
./docker-mender-convert \
  --disk-image ../debian-13-base.img \
  --config configs/eisa-kiosk.cfg \
  --overlay scripts/eisa-overlay.sh \
  --output-dir /output
```

> **i7 → i5 uyumluluğu**: Her iki işlemci de `x86-64 (amd64)` ISA'sını destekler. i7'de derlenen binary'ler i5'te sorunsuz çalışır; ekstra optimize flag (`-march=native` gibi) kullanılmadığı sürece herhangi bir uyumluluk sorunu çıkmaz. `npm ci` ve Node.js bu konuda güvenlidir.

**Çıktı dosyaları** (`/output/`):

```
eisa-kiosk-20261123-v1.0.0.img         ← Cihaza flash edilecek ham imaj
eisa-kiosk-20261123-v1.0.0.mender      ← OTA güncelleme artefaktı
eisa-kiosk-20261123-v1.0.0.img.bmap    ← bmap-tools hızlı flash için
```

---

## 6. Golden Image Oluşturma ve Arşivleme

**Golden Image**, provision edilmemiş (kimlik bilgileri placeholder), production-ready, test edilmiş, belirli bir yazılım versiyonunu temsil eden referans disk imajıdır. Tüm yeni kiosk cihazları bu imajdan klonlanır.

### 6.1 Golden Image Kriterleri (Checklist)

```
[ ] mender-convert başarıyla tamamlandı (çıktı imaj hata yok)
[ ] İmaj QEMU'da boot testi yapıldı
[ ] eisa-api.service systemd'de active/running
[ ] /health endpoint'i 200 dönüyor
[ ] Chromium kiosk modunda açılıyor
[ ] Mender client bağlanıyor (mender-updated aktif)
[ ] /etc/eisa/kiosk.env tüm değerler PROVISION_REQUIRED (cihaza özgü yok)
[ ] SSH yetkisiz erişim mevcut değil (root şifre disabled)
[ ] ufw aktif, sadece port 22 ve 8765 açık
[ ] node_modules içinde güvenlik açığı taraması yapıldı (npm audit)
[ ] .env dosyaları imaj içinde yok
```

### 6.2 İmajı SHA256 ile İmzalama ve Arşivleme

```bash
VERSION="v1.0.0"
DATE=$(date +%Y%m%d)
ARTIFACT_NAME="eisa-kiosk-${DATE}-${VERSION}"
OUTPUT_DIR="./golden-images/${VERSION}"

mkdir -p "$OUTPUT_DIR"

# Ham imajı sıkıştır
xz -9 -k "/output/${ARTIFACT_NAME}.img" -o "${OUTPUT_DIR}/${ARTIFACT_NAME}.img.xz"

# Mender artefaktını kopyala
cp "/output/${ARTIFACT_NAME}.mender" "${OUTPUT_DIR}/"

# SHA256 checksum'ları üret
sha256sum \
  "${OUTPUT_DIR}/${ARTIFACT_NAME}.img.xz" \
  "${OUTPUT_DIR}/${ARTIFACT_NAME}.mender" \
  > "${OUTPUT_DIR}/SHA256SUMS"

# GPG ile imzala (opsiyonel ama önerilir)
gpg --armor --detach-sign "${OUTPUT_DIR}/SHA256SUMS"

# Metadata dosyası
cat > "${OUTPUT_DIR}/RELEASE.md" << RELEASE_META
# E-ISA Kiosk Golden Image ${VERSION}

| Alan              | Değer                         |
|-------------------|-------------------------------|
| Sürüm             | ${VERSION}                    |
| Oluşturulma Tarihi| ${DATE}                       |
| Taban OS          | Debian 13 (Trixie) amd64      |
| Node.js           | 20 LTS                        |
| Svelte UI         | 5.x                           |
| Fastify API       | 5.x                           |
| Mender Client     | 4.x                           |
| Build Donanımı    | Intel Core i7, x86-64         |
| Hedef Donanım     | Intel Core i5, x86-64 Mini-PC |

## Bileşenler
- \`/opt/eisa/api/\`  → Node.js Fastify API (eMMC rootfs-A/B)
- \`/opt/eisa/ui/\`   → Svelte build statik dosyaları
- \`/data/eisa/\`     → SQLite DB (data partition — OTA'dan etkilenmez)
- \`/data/log/\`      → Rotasyon logları (data partition)

## Flash Komutu
\`\`\`bash
# bmap-tools ile hızlı flash (önerilir):
bmaptool copy ${ARTIFACT_NAME}.img.xz /dev/sdX

# dd ile (yavaş):
xz -d ${ARTIFACT_NAME}.img.xz | dd of=/dev/sdX bs=4M status=progress
\`\`\`

## Provision Adımı
Flash sonrası mutlaka ./provision-kiosk.sh çalıştırın.
RELEASE_META

echo "Golden Image arşivlendi: ${OUTPUT_DIR}/"
ls -lh "${OUTPUT_DIR}/"
```

### 6.3 Önerilen Dizin Yapısı

```
golden-images/
├── v1.0.0/
│   ├── eisa-kiosk-20261123-v1.0.0.img.xz        ← Flash imajı
│   ├── eisa-kiosk-20261123-v1.0.0.mender         ← OTA artefaktı
│   ├── SHA256SUMS                                 ← Checksum'lar
│   ├── SHA256SUMS.asc                             ← GPG imzası
│   └── RELEASE.md                                 ← Sürüm notları
├── v1.1.0/
│   └── ...
└── latest → v1.1.0/                               ← Semlink (en güncel)
```

---

## 7. Provision Script — Kiosk Kimlik Bilgileri

Her kiosk, kurulumdan sonra cihaza özgü kimlik bilgileriyle **provision** edilir.  
Bu adım golden image flashing'inden **sonra** ve network'e ilk bağlanmadan **önce** yapılır.

```bash
#!/bin/bash
# provision-kiosk.sh — Saha teknisyeni tarafından çalıştırılır.
# Kullanım: ./provision-kiosk.sh <fleet_key> <provisioning_secret> <api_base>

set -euo pipefail

FLEET_KEY="$1"
PROVISIONING_SECRET="$2"
API_BASE="$3"
MAC=$(cat /sys/class/net/eth0/address 2>/dev/null || \
      cat /sys/class/net/wlan0/address 2>/dev/null)

cat > /etc/eisa/kiosk.env << EOF
EISA_KIOSK_FLEET_KEY=${FLEET_KEY}
EISA_KIOSK_PROVISIONING_SECRET=${PROVISIONING_SECRET}
EISA_SQLITE_PATH=/data/eisa/local.db
EISA_CENTRAL_API_BASE=${API_BASE}
EISA_PULL_INTERVAL_SEC=900
EISA_PUSH_INTERVAL_SEC=300
EISA_PING_INTERVAL_SEC=60
EISA_VERIFY_TLS=true
EISA_DEV_MODE=false
EISA_HOST=127.0.0.1
EISA_PORT=8765
EISA_LOG_DIR=/data/log
EISA_LOG_LEVEL=info
EOF

chmod 640 /etc/eisa/kiosk.env
chown root:eisaapp /etc/eisa/kiosk.env

# Mender tenant token ve server URL'ini de yaz
sed -i \
  -e "s|MENDER_SERVER_URL_PLACEHOLDER|${MENDER_SERVER:-https://hosted.mender.io}|g" \
  -e "s|MENDER_TENANT_TOKEN_PLACEHOLDER|${MENDER_TENANT_TOKEN:-}|g" \
  /etc/mender/mender.conf

systemctl restart eisa-api mender-updated

echo "Kiosk provision tamamlandı (MAC: ${MAC})"
echo "Kiosk ilk açılışta HMAC-imzalı provision ile App Key alacak."
```

> **Not**: `EISA_KIOSK_PROVISIONING_SECRET` hem App Key provisioning imzası hem de eczacı terminali QR sorgusu için kullanılır. Tek bir secret yönetilir.

---

## 8. OTA Güncelleme Akışı

```
Geliştirici                  Mender Server              Kiosk Cihazı
    │                              │                          │
    │  1. mender-convert çalıştır  │                          │
    │  2. .mender artefaktını      │                          │
    │     Mender'a yükle           │                          │
    │─────── mender-cli upload ───►│                          │
    │                              │                          │
    │  3. Deployment oluştur       │                          │
    │─────── deployment create ───►│                          │
    │                              │                          │
    │                              │◄── 4. Poll (1800s) ──────│
    │                              │                          │
    │                              │──── 5. Artefakt URL ────►│
    │                              │                          │
    │                              │   6. rootfs-B'ye yaz     │
    │                              │      (aktif sistem       │
    │                              │       çalışmaya devam)   │
    │                              │                          │
    │                              │   7. Reboot              │
    │                              │      rootfs-B aktif      │
    │                              │                          │
    │                              │◄── 8. Commit / Rollback ─│
    │                              │      (30s boot test)     │
```

### Yeni Sürüm Yayınlama

```bash
# 1. Yeni build
cd e-isa-monorepo
# ... kiosk_edge'de değişiklikler ...
git tag v1.1.0
./build-kiosk.sh   # dist güncellenir

# 2. mender-convert (i5 amd64 hedef)
cd mender-convert
MENDER_ARTIFACT_NAME="eisa-kiosk-$(date +%Y%m%d)-v1.1.0" \
MENDER_DEVICE_TYPE="eisa-kiosk-i5-amd64" \
./docker-mender-convert \
  --disk-image ../debian-13-base.img \
  --config configs/eisa-kiosk.cfg \
  --overlay scripts/eisa-overlay.sh \
  --output-dir /output

# 3. Mender'a yükle
mender-cli artifacts upload /output/eisa-kiosk-*-v1.1.0.mender \
  --server https://hosted.mender.io \
  --token "$MENDER_CLI_TOKEN"

# 4. Deployment (tüm kiosklara veya belirli gruba)
mender-cli deployments create \
  --name "eisa-kiosk-v1.1.0-rollout" \
  --artifact "eisa-kiosk-$(date +%Y%m%d)-v1.1.0" \
  --device-group "production-kiosks"
```

---

## 9. Dizin Yapısı Referansı

### Kiosk Cihazı Üzerindeki Dosya Sistemi

```
/
├── opt/
│   └── eisa/
│       ├── api/                    # Node.js Fastify kaynak kodu
│       │   ├── src/
│       │   │   ├── index.js        # Giriş noktası
│       │   │   ├── server.js       # Fastify app factory
│       │   │   ├── config.js       # Ortam değişkenleri
│       │   │   ├── db.js           # SQLite bağlantısı
│       │   │   ├── scheduler.js    # Pull/Push scheduler
│       │   │   ├── auth.js         # Local API Bearer auth
│       │   │   ├── qrBitpack.js    # QR payload encoder
│       │   │   └── printer.js      # Termal yazıcı
│       │   └── node_modules/
│       └── ui/                     # Svelte build (statik)
│           ├── index.html
│           └── assets/
├── etc/
│   ├── eisa/
│   │   └── kiosk.env              # Kimlik bilgileri (640 root:eisaapp)
│   ├── mender/
│   │   └── mender.conf            # Mender client config
│   ├── udev/rules.d/
│   │   └── 99-eisa-usb-peripherals.rules  # Termal yazıcı + barkod okuyucu
│   └── systemd/system/
│       ├── eisa-api.service
│       └── eisa-data-init.service
├── var/
│   ├── lib/
│   │   └── eisa/                  # → bind mount: /data/eisa/
│   └── log/
│       └── eisa/                  # → bind mount: /data/log/
└── data/                          # Kalıcı data bölümü (OTA'dan etkilenmez)
    ├── eisa/
    │   └── local.db               # SQLite (offline-first veri)
    └── log/
        └── eisa-*.log             # Pino rotasyon logları
```

### Build Makinesi Çıktı Yapısı

```
e-isa-monorepo/
├── kiosk_edge/
│   └── .build/                    # Geçici build artefaktları (git ignore)
│       ├── api/                   # Node.js + node_modules
│       ├── ui-static/             # Svelte dist
│       └── eisa-api.service
├── docs/
│   └── kiosk-mender-golden-image.md    ← bu belge
└── golden-images/
    └── v1.0.0/
        ├── *.img.xz
        ├── *.mender
        ├── SHA256SUMS
        └── RELEASE.md
```

---

## Hızlı Başlangıç Özeti

```bash
# 1. Build (i7 build makinesinde — native amd64, cross-compile gerekmez)
cd kiosk_edge/ui && npm ci && npm run build
cd ../api-node && npm ci --omit=dev
# better-sqlite3 native amd64 binary — hedef i5 ile uyumlu, rebuild gerekmez

# 2. Taban imajı indir (Debian 13 amd64)
wget https://cloud.debian.org/images/cloud/trixie/daily/latest/debian-13-genericcloud-amd64.qcow2
qemu-img convert -f qcow2 -O raw debian-13-genericcloud-amd64.qcow2 debian-13-base.img

# 3. mender-convert (Intel i5 x86-64 / amd64)
cd mender-convert
MENDER_DEVICE_TYPE="eisa-kiosk-i5-amd64" \
./docker-mender-convert \
  --disk-image ../debian-13-base.img \
  --config configs/eisa-kiosk.cfg \
  --overlay scripts/eisa-overlay.sh

# 4. Flash
bmaptool copy /output/eisa-kiosk-*.img.xz /dev/sdX

# 5. Provision (cihaz üzerinde)
./provision-kiosk.sh 42 7 "your-app-key" "https://api.e-isa.example.com"
```

---

---

## 10. On-Prem Mender Server — k3s Kurulumu

> Bu bölüm, Mender Community Edition'ın (açık kaynak) **k3s** üzerinde **tek sunuculu** (single-node) kurulumunu ve güvenliğini anlatır. Mender Enterprise lisansı gerekmez.

### 10.1 Sunucu Gereksinimleri

| Kaynak      | Minimum      | Önerilen      |
|-------------|--------------|---------------|
| OS          | Debian 13 (Trixie) amd64 | Ubuntu 22.04 LTS amd64 |
| CPU         | 4 vCPU       | 8 vCPU        |
| RAM         | 8 GB         | 16 GB         |
| Disk        | 100 GB SSD   | 500 GB SSD    |
| Ağ          | Statik IP + FQDN (TLS zorunlu) | — |
| Açık portlar| 80, 443 (ingress) | 6443 sadece yönetim ağında |

> **Güvenlik**: Port 6443 (k3s API) internete asla açılmamalıdır. VPN veya jump host üzerinden erişin.

---

### 10.2 Sunucu Temel Hazırlığı

```bash
# Sunucu üzerinde (root veya sudo)
apt-get update && apt-get upgrade -y
apt-get install -y curl wget gnupg ufw fail2ban

# Güvenlik duvarı
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp     # SSH — sonra IP kısıtlaması ekleyin
ufw allow 80/tcp     # HTTP (TLS yönlendirme)
ufw allow 443/tcp    # HTTPS (Mender UI + API)
ufw --force enable

# fail2ban — SSH kaba kuvvet koruması
systemctl enable --now fail2ban

# Swap (k3s için önerilir, yoksa ekleyin)
fallocate -l 4G /swapfile && chmod 600 /swapfile
mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

---

### 10.3 k3s Kurulumu

```bash
# Traefik devre dışı — kendi nginx-ingress kullanacağız
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="
  --disable traefik
  --write-kubeconfig-mode 644
  --tls-san $(hostname -f)
  --tls-san $(curl -s https://ifconfig.me)
" sh -

# kubectl erişimi
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
echo 'export KUBECONFIG=/etc/rancher/k3s/k3s.yaml' >> ~/.bashrc

# Durum kontrolü
kubectl get nodes
# Çıktı: Ready
```

---

### 10.4 Helm ve Temel Bileşenler

```bash
# Helm 3 kurulumu
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# nginx-ingress controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace \
  --set controller.service.type=LoadBalancer \
  --set controller.config.use-forwarded-headers=true \
  --set controller.config.proxy-real-ip-cidr="0.0.0.0/0" \
  --set controller.config.ssl-protocols="TLSv1.2 TLSv1.3" \
  --set controller.config.ssl-ciphers="ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384" \
  --wait

# cert-manager (otomatik TLS — Let's Encrypt)
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set installCRDs=true \
  --wait

# ClusterIssuer — Let's Encrypt production
cat <<'EOF' | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@e-isa.example.com   # ← gerçek e-posta
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

---

### 10.5 Mender Server Helm Chart Kurulumu

```bash
# Mender Helm deposu
helm repo add mender https://charts.mender.io
helm repo update

# Değerler dosyası oluştur
MENDER_DOMAIN="mender.e-isa.example.com"   # ← kendi FQDN'iniz
MENDER_STORAGE_ACCESS_KEY=$(openssl rand -hex 20)
MENDER_STORAGE_SECRET_KEY=$(openssl rand -hex 32)
MENDER_MONGO_PWD=$(openssl rand -hex 24)

cat > mender-values.yaml << HELM_VALUES
global:
  enterprise: false            # Community Edition
  image:
    tag: "3.7"

# ── Mender yönetim arayüzü (GUI) ─────────────────────────────────
gui:
  enabled: true
  replicaCount: 1

# ── Mender API Gateway ───────────────────────────────────────────
api_gateway:
  enabled: true
  env:
    SSL: "false"               # TLS ingress'te sonlandırılır

# ── Dahili MongoDB ───────────────────────────────────────────────
mongodb:
  enabled: true
  auth:
    rootPassword: "${MENDER_MONGO_PWD}"
    usernames: ["mender"]
    passwords: ["${MENDER_MONGO_PWD}"]
    databases: ["mender"]
  persistence:
    size: 50Gi
    storageClass: local-path   # k3s varsayılan storage class

# ── MinIO (artefakt deposu) ───────────────────────────────────────
minio:
  enabled: true
  rootUser: "mender-access"
  rootPassword: "${MENDER_STORAGE_SECRET_KEY}"
  persistence:
    size: 100Gi
    storageClass: local-path
  # MinIO yönetim UI'si sadece cluster içinde erişilebilir olmalı
  service:
    type: ClusterIP

# ── Ingress ───────────────────────────────────────────────────────
api_gateway:
  env:
    ALLOWED_HOSTS: "${MENDER_DOMAIN}"

ingress:
  enabled: true
  ingressClassName: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-body-size: "0"          # büyük artefakt yükleme
    nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "600"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    # Güvenlik başlıkları
    nginx.ingress.kubernetes.io/configuration-snippet: |
      more_set_headers "Strict-Transport-Security: max-age=31536000; includeSubDomains; preload";
      more_set_headers "X-Frame-Options: DENY";
      more_set_headers "X-Content-Type-Options: nosniff";
      more_set_headers "Referrer-Policy: strict-origin-when-cross-origin";
  hosts:
  - host: "${MENDER_DOMAIN}"
    paths:
    - path: /
      pathType: Prefix
  tls:
  - hosts:
    - "${MENDER_DOMAIN}"
    secretName: mender-tls-cert
HELM_VALUES

# Namespace oluştur
kubectl create namespace mender

# Helm ile kur
helm upgrade --install mender mender/mender \
  --namespace mender \
  --values mender-values.yaml \
  --timeout 15m \
  --wait

# Pod durumlarını kontrol et
kubectl get pods -n mender
```

> **Not**: `mender-values.yaml` dosyasını git'e commit etmeyin. Şifreler için [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets) veya External Secrets Operator kullanın.

---

### 10.6 İlk Admin Kullanıcısı Oluşturma

```bash
# useradm pod'u üzerinden admin kullanıcısı oluştur
USERADM_POD=$(kubectl get pods -n mender -l app.kubernetes.io/component=useradm \
  -o jsonpath='{.items[0].metadata.name}')

kubectl exec -n mender "$USERADM_POD" -- \
  useradm create-user \
    --username admin@e-isa.example.com \
    --password "$(openssl rand -base64 20)"

# Oluşturulan şifreyi güvenli bir yere saklayın (örn: Bitwarden/Vault)
```

### 10.7 Yönetim Arayüzüne Erişim

Tarayıcıdan `https://mender.e-isa.example.com` adresine gidin.  
Arayüzde şunları yapabilirsiniz:

| İşlem | Yol |
|-------|-----|
| Artefakt yükleme | Releases → Upload Artifact |
| Deployment oluşturma | Deployments → Create |
| Cihaz listesi | Devices → All devices |
| Cihaz gruplama | Devices → Groups |
| RBAC (role tabanlı erişim) | Settings → User Management |

---

### 10.8 Güvenlik Sertleştirme

#### TLS ve Erişim Kontrolü

```bash
# k3s API sunucusunu yalnızca localhost + VPN subnet'inden erişilebilir yap
# /etc/rancher/k3s/config.yaml dosyasına ekle:
cat > /etc/rancher/k3s/config.yaml << 'K3S_CFG'
write-kubeconfig-mode: "600"
bind-address: "127.0.0.1"        # API sadece localhost'ta
tls-san:
  - "127.0.0.1"
  - "10.0.0.1"                   # ← VPN/yönetim ağı IP'si
kube-apiserver-arg:
  - "audit-log-path=/var/log/k3s/audit.log"
  - "audit-log-maxage=30"
  - "audit-log-maxbackup=5"
  - "audit-log-maxsize=100"
K3S_CFG

systemctl restart k3s
```

#### Pod Security ve NetworkPolicy

```yaml
# mender namespace'e NetworkPolicy — sadece ingress'ten gelen trafiğe izin ver
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mender-default-deny
  namespace: mender
spec:
  podSelector: {}                # tüm pod'lar
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: ingress-nginx
  - from:
    - podSelector: {}            # namespace içi pod'lar arası
  egress:
  - to:
    - podSelector: {}            # namespace içi
  - to:
    - namespaceSelector:         # DNS
        matchLabels:
          kubernetes.io/metadata.name: kube-system
    ports:
    - port: 53
      protocol: UDP
  - to: [{}]                     # dış dünya (artefakt indirme vb.)
    ports:
    - port: 443
    - port: 80
```

```bash
kubectl apply -f mender-netpol.yaml
```

#### Secret Yönetimi

```bash
# Mevcut Helm secret'larını listele
kubectl get secrets -n mender

# Sealed Secrets kurulumu (secret'ları git'e güvenli commit için)
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm upgrade --install sealed-secrets sealed-secrets/sealed-secrets \
  --namespace kube-system

# kubeseal CLI
curl -sL https://github.com/bitnami-labs/sealed-secrets/releases/latest/download/kubeseal-linux-amd64 \
  -o /usr/local/bin/kubeseal && chmod +x /usr/local/bin/kubeseal

# Mevcut secret'ı seal'le
kubectl get secret mender-mongo -n mender -o yaml | \
  kubeseal --format yaml > mender-mongo-sealed.yaml
# mender-mongo-sealed.yaml git'e commit edilebilir
```

#### Düzenli Yedekleme

```bash
# MongoDB yedeği (cron ile günlük)
cat > /etc/cron.daily/mender-mongo-backup << 'CRON'
#!/bin/bash
POD=$(kubectl get pods -n mender -l app.kubernetes.io/component=mongodb \
  -o jsonpath='{.items[0].metadata.name}')
DATESTR=$(date +%Y%m%d)
kubectl exec -n mender "$POD" -- \
  mongodump --username mender --password "$MONGO_PWD" \
  --authenticationDatabase admin --archive \
  > /backup/mender-mongo-${DATESTR}.archive
# 30 günden eski yedekleri sil
find /backup -name 'mender-mongo-*.archive' -mtime +30 -delete
CRON
chmod +x /etc/cron.daily/mender-mongo-backup
mkdir -p /backup
```

#### RBAC — Mender UI Kullanıcı Rolleri

Mender'da roller Admin panelinden yönetilir:

| Rol | İzinler |
|-----|---------|
| `admin` | Tüm işlemler (kullanıcı yönetimi dahil) |
| `deployments_manager` | Deployment oluşturma/takip, release yükleme |
| `readonly` | Yalnızca görüntüleme (audit için) |

**Üretimde**: Her operatöre ayrı kullanıcı tanımlayın. Paylaşılan `admin` hesabı kullanmayın.

---

### 10.9 Kiosk Cihazını On-Prem Mender'a Bağlama

Provision scriptinde (`§7`) şu değerleri kullanın:

```bash
# On-prem Mender kullanan kiosk provision'ı
export MENDER_SERVER="https://mender.e-isa.example.com"
export MENDER_TENANT_TOKEN=""   # Community Edition'da boş bırakılır

./provision-kiosk.sh 42 7 "your-app-key" "https://api.e-isa.example.com"
```

Provision sonrası cihaz `https://mender.e-isa.example.com` → **Devices → Pending** altında görünür. **Accept** butonuyla onaylayın.

---

*Son güncelleme: 2026-05-23 | E-ISA Kiosk Edge v1.0.0 — Build: Intel Core i7 (amd64) → Hedef: Intel Core i5 (amd64)*
