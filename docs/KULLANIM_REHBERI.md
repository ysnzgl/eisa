# e-isa Admin Panel — Kullanım Rehberi

> **Hedef Kitle:** SuperAdmin rolüne sahip sistem yöneticileri  
> **Erişim URL:** `/admin` (ör. `https://panel.eisa.com.tr/admin`)  
> **Versiyon:** Faz 7 (DOOH v2 Canonical)

---

## İçindekiler

1. [Giriş ve Roller](#1-giriş-ve-roller)
2. [Dashboard](#2-dashboard)
3. [Sponsorluk Tanımı (Kampanya + Medya) Oluşturma](#3-sponsorluk-tanımı-kampanya--medya-oluşturma)
4. [Kiosk Sponsorluklarını Yönetme](#4-kiosk-sponsorluklarını-yönetme)
5. [Sponsorluk/Kampanya Yönetimi ve Kontrol Merkezi](#5-sponsorlukkampanya-yönetimi-ve-kontrol-merkezi)
6. [Örnek Senaryo](#6-örnek-senaryo)
7. [Sık Karşılaşılan Hatalar](#7-sık-karşılaşılan-hatalar)

---

## 1. Giriş ve Roller

| Rol | Erişim |
|-----|--------|
| **SuperAdmin** | Tüm panel: Kampanyalar (sponsorluk tanımları), Kiosk Sponsorlukları, Kontrol Merkezi, Dashboard |
| **Pharmacist** | Yalnızca kendi kiosk(lar)ının görünümü (`/pharmacist`) |

SuperAdmin girişi:
1. `https://panel.eisa.com.tr/admin` adresine git
2. Kullanıcı adı ve şifre gir
3. JWT token cookie olarak set edilir; oturum otomatik yenilenir

---

## 2. Dashboard

Dashboard'da görebilecekleriniz:

| Kart | Açıklama |
|------|----------|
| Toplam Eczane | Sistemdeki kayıtlı eczane sayısı |
| Toplam Kampanya | Tüm kampanyalar (ACTIVE + PAUSED + COMPLETED) |
| Aktif Kiosk | Şu an bağlı/aktif kiosk sayısı |
| Aktif Kampanya | Durumu ACTIVE olan kampanya sayısı |

---

## 3. Sponsorluk Tanımı (Kampanya + Medya) Oluşturma

> **2026-10-16 yeni model:** Sponsorluklar artık **kiosk (cihaz) bazlıdır**. İl/ilçe/eczane hedefleme, frekans tipleri (PER_LOOP/PER_HOUR/PER_DAY), hedef gösterim, simülasyon→aktive wizard'ı ve fiyatlandırma matrisi **kaldırıldı**. Akış iki parçadır: önce **sponsorluk tanımı + medya** (bu bölüm), sonra **kiosk ataması + zaman penceresi** (bölüm 4).

Sol menüden **Kampanyalar** (`/admin/campaigns`) → **+ Yeni Kampanya**. Form 3 sekmeden oluşur: **Bilgiler / Medya / Kiosklar**.

---

### Sekme 1 — Bilgiler

| Alan | Zorunlu | Açıklama |
|------|---------|----------|
| Kampanya Adı | ✅ | Dahili takip için isim (ör. `Magnezyum Yaz 2026`) |
| Reklamveren | ❌ | Reklam sahibi firma adı (serbest metin — `advertiser_name`) |
| Başlangıç Tarihi | ✅ | Sponsorluğun yayına gireceği tarih |
| Bitiş Tarihi | ✅ | Sona ereceği tarih (başlangıçtan sonra olmalı) |
| Durum | ✅ | `ACTIVE` / `PAUSED` / `COMPLETED` |

> Başlangıcı gelecekte olan `ACTIVE` kampanya panelde **SCHEDULED** (`effective_state`) olarak görünür.

---

### Sekme 2 — Medya (Creative)

1. **Dosya Seç** ile video/görsel yükle (S3'e yüklenir, URL otomatik set edilir).
2. **Süre** alanını ayarla: yalnızca **15 / 30 / 45 / 60** saniye kabul edilir.
3. Birden fazla creative eklenebilir; sponsorluk penceresinde **sırayla (round-robin)** oynatılır.

---

### Sekme 3 — Kiosklar (atama)

Bu sekmede sponsorluğun yayınlanacağı kiosklar seçilir. Atama ayrıntısı (zaman penceresi + N) bölüm 4'te ayarlanır; burada hızlı toplu atama yapılır:

- Kiosk listesinden tek tek seçebilir ya da **ara** kutusuyla filtreleyebilirsin.
- **Ata** dediğinde seçili kiosklar için sponsorluk kaydı oluşur. Zaten atanmış kiosklar atlanır.
- Kaydet → sponsorluk tanımı oluşturulur.

---

## 4. Kiosk Sponsorluklarını Yönetme

Sol menüden **Kiosk Sponsorlukları** (`/admin/kiosk-sponsorships`). Sayfada 4 sekme vardır: **Sponsorluklar · Takvim · Simülasyon · Kopyala**.

### 4.1 Sponsorluklar (zaman penceresi + N)

Bir kiosk seç → o kioska atanmış tüm kampanya sponsorlukları satır satır listelenir. Her satırda:

| Alan | Açıklama |
|------|----------|
| Kampanya | Atanan sponsorluk kampanyası |
| Başlangıç / Bitiş saati | Gün içi yayın penceresi `[başlangıç, bitiş)` (ör. `08:00`–`19:00`) |
| Adet (N) | Bu pencerede **gün içinde toplam** kaç kez oynatılacağı (`count`) |
| Haftanın günleri | Seçili günler (boş = her gün; ISO Pzt=1 … Paz=7) |
| Başlangıç / Bitiş tarihi | İsteğe bağlı; sponsorluğun geçerli olduğu tarih aralığı |
| Aktif | Kaydın yayında olup olmadığı |

- Pencere ve N girildikçe satırda **max öneri (maxCountHint)** gösterilir: pencereye fiziksel olarak sığan en çok gösterim.
- **PUT** ile kioskun tüm sponsorluk satırları tek seferde kaydedilir.

> **Dağıtım mantığı:** Motor (`sponsorship_engine`) N gösterimi pencereye **homojen ve deterministik** dağıtır: ideal zamanlar eşit aralıklı hesaplanır, en yakın boş slota yerleştirilir, bir gösterim **saat sınırını aşamaz**.

### 4.2 Kapasite bloğu

Pencereye sığandan fazla N istenirse ya da birden çok kampanya aynı slotlarda çakışırsa kayıt **reddedilir**:

```
400 {
  "code": "capacity_exceeded",
  "detail": "...",
  "conflicts": [{ "date", "campaign_id", "campaign_name", "requested", "placed" }]
}
```

Panel bu hatayı satırda gösterir. **Çözüm:** N'i düşür, pencereyi genişlet veya çakışan sponsorluğu azalt.

### 4.3 Takvim — program önizleme

**Takvim** sekmesi seçili kiosk/gün için üretilecek programı **salt okunur** önizler (ısı haritası + saat şeridi). Hiçbir tabloya yazmaz; aynı girdi için deterministik sonuç verir. Hangi saatte hangi kampanyanın kaç kez düşeceğini görmek için kullanılır.

### 4.4 Simülasyon

**Simülasyon** sekmesi iki şey sağlar (DB'ye yazmaz):

- **Pencere probe:** Verilen pencere + creative süresi için **maksimum kapasiteyi** söyler.
- **Senaryo:** Önerilen N/pencere ile programın nasıl görüneceğini, çakışma olup olmayacağını önizler.

Böylece kaydetmeden önce kapasiteyi doğrulayabilirsin.

### 4.5 Kopyala (= ÜZERİNE YAZ)

**Kopyala** sekmesi bir kaynak kioskun tüm sponsorluk ayarlarını bir veya birden çok hedef kioska aktarır.

> ⚠️ **Kopyalama OVERWRITE'tır:** Hedef kioskun mevcut sponsorlukları **tamamen silinip** kaynaktakiyle değiştirilir. Panel, değişecek kampanya adlarını (`diffCampaignNames`) kopyadan önce gösterir. Kapasite aşılırsa yine `capacity_exceeded` döner ve kopya uygulanmaz.

---

## 5. Sponsorluk/Kampanya Yönetimi ve Kontrol Merkezi

### Kampanya listesi (`/admin/campaigns`)

| İşlem | Nasıl |
|-------|-------|
| Arama | Sağ üstteki arama kutusuna kampanya adı / reklamveren yaz |
| Durum filtresi | "Tüm Durumlar" dropdown'u |
| Düzenle | Satırdaki kalem ikonu → Bilgiler/Medya/Kiosklar |
| Sil | Çöp kutusu → onay |
| Toplu işlem | Checkbox ile seç → **Duraklat / Devam Et / Sil** |

### Durum geçişleri

```
ACTIVE ⇄ PAUSED
   ↘
    COMPLETED
```

- `ACTIVE`: Atanan kiosklara yayınlanır (başlangıç gelecekteyse panelde SCHEDULED).
- `PAUSED`: Geçici durduruldu; tekrar devam ettirilebilir.
- `COMPLETED`: Bitti; salt okunur.

### Kontrol Merkezi (DoohControlCenter)

| Bölüm | Açıklama |
|-------|----------|
| Aktif Kampanya | Şu an yayındaki kampanya sayısı |
| Bekleyen İş | Playlist üretim kuyruğundaki iş sayısı |
| Son İşler | Son playlist generation job'larının durumu |
| Toplu Yenile | Seçili kampanyaların playlist'lerini zorla yeniden üret |

> Playlist'ler **otomatik** üretilir (`DOOH_HORIZON_DAYS`, varsayılan 3 gün ufuk). Sponsorluk kaydı değişince ilgili kiosk-gün programı yeniden üretilir; kiosklar sync sırasında yeni playlist'i çeker.

---

## 6. Örnek Senaryo

### Senaryo: Bir kioskta 08:00–19:00 arası günde 100 gösterim, 15 sn creative

**1) Sponsorluk tanımı (Kampanyalar → + Yeni):**
```
Bilgiler → Ad: Magnezyum Yaz 2026 | Reklamveren: ABC İlaç
          Başlangıç: 2026-08-01 | Bitiş: 2026-08-11 | Durum: ACTIVE
Medya    → magnezyum_15sn.mp4 | Süre: 15 sn
Kiosklar → Hedef kiosku ata
```

**2) Kiosk Sponsorlukları → Sponsorluklar sekmesi:** kiosku seç, satırı doldur:
```
Kampanya : Magnezyum Yaz 2026
Pencere  : 08:00 – 19:00        (11 saat)
Adet (N) : 100
Günler   : (boş = her gün)
```
- Satırdaki **max öneri** ile 100'ün pencereye sığdığını gör (11 saat × saat başına kapasite ≫ 100).
- **Simülasyon** sekmesinde probe/senaryo ile doğrula.
- **Takvim** sekmesinde 100 gösterimin güne homojen dağıldığını önizle.
- **Kaydet (PUT).** Kapasite aşılırsa `capacity_exceeded` döner → N'i düşür.

**3) Aynı programı başka kiosklara uygula:** **Kopyala** sekmesi → kaynak = bu kiosk, hedef = diğer kiosklar (OVERWRITE — mevcut ayarları silip yeniler).

---

## 7. Sık Karşılaşılan Hatalar

| Hata | Nedeni | Çözüm |
|------|--------|-------|
| `duration_seconds 15sn grid ile uyumsuz` | 15/30/45/60 dışında süre girildi | Süreyi 15/30/45/60 yap |
| `capacity_exceeded` (`conflicts: [...]`) | Pencereye sığandan fazla N ya da kampanyalar çakışıyor | N'i düşür, pencereyi genişlet veya çakışan sponsorluğu azalt |
| `window_end, window_start'tan büyük olmalı` | Bitiş ≤ başlangıç | Pencereyi düzelt (`[başlangıç, bitiş)`, bitiş hariç) |
| `count ≥ 1 olmalı` | N boş/0 girildi | En az 1 gösterim gir |
| `end_date, start_date'ten sonra olmalıdır` | Kampanya tarihleri hatalı | Bitiş tarihini kontrol et |
| Kopyalama sonrası ayarlar kayboldu | Kopyalama **OVERWRITE**'tır | Kopyalamadan önce hedef kiosk ayarlarını not al |

---

*Son güncelleme: 2026-10-16 — DOOH cihaz (kiosk) bazlı KioskSponsorship*
