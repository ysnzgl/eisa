# E-İSA Admin Panel — Kullanım Rehberi

> **Hedef Kitle:** SuperAdmin rolüne sahip sistem yöneticileri  
> **Erişim URL:** `/admin` (ör. `https://panel.eisa.com.tr/admin`)  
> **Versiyon:** Faz 7 (DOOH v2 Canonical)

---

## İçindekiler

1. [Giriş ve Roller](#1-giriş-ve-roller)
2. [Dashboard](#2-dashboard)
3. [Kampanya Oluşturma — Adım Adım](#3-kampanya-oluşturma--adım-adım)
4. [Kampanya Yönetimi](#4-kampanya-yönetimi)
5. [Playlist Kontrolü](#5-playlist-kontrolü)
6. [Frekans Tipleri — Detaylı Açıklama](#6-frekans-tipleri--detaylı-açıklama)
7. [Örnek: 08:00–18:00 arası 100 gösterimli 15 saniyelik kampanya](#7-örnek-senaryo)
8. [Sık Karşılaşılan Hatalar](#8-sık-karşılaşılan-hatalar)

---

## 1. Giriş ve Roller

| Rol | Erişim |
|-----|--------|
| **SuperAdmin** | Tüm panel: Kampanyalar, Playlist, Dashboard, Fiyatlandırma |
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

## 3. Kampanya Oluşturma — Adım Adım

Sol menüden **Kampanyalar** → sağ üstteki **+ Yeni Kampanya** butonuna tıkla.

Wizard 6 adımdan oluşur:

---

### Adım 1 — Bilgiler

| Alan | Zorunlu | Açıklama |
|------|---------|----------|
| Kampanya Adı | ✅ | Dahili takip için isim (ör. `Magnezyum Yaz 2026`) |
| Reklamveren | ❌ | Reklam sahibi firma adı |
| Başlangıç Tarihi | ✅ | Kampanyanın yayına gireceği tarih/saat |
| Bitiş Tarihi | ✅ | Kampanyanın sona ereceği tarih/saat |
| Durum | ✅ | `ACTIVE` / `PAUSED` — başlangıçta genellikle `ACTIVE` seçilir |

> **Not:** Bitiş tarihi, başlangıç tarihinden sonra olmalıdır.

**İleri** butonuna tıkla.

---

### Adım 2 — Medya (Creative)

1. **Dosya Seç** butonuna tıkla
2. Medya dosyasını (video/görsel) yükle
3. Yükleme tamamlanınca **süre** alanını ayarla

| Alan | Kural |
|------|-------|
| Süre (saniye) | Yalnızca **15 / 30 / 45 / 60** saniye kabul edilir |
| Dosya | S3'e yüklenir; URL otomatik set edilir |

> Birden fazla creative eklenebilir. Her creative sırayla loop'ta oynatılır.

**İleri** butonuna tıkla.

---

### Adım 3 — Hedefleme

İki mod vardır:

| Mod | Ne anlama gelir |
|-----|-----------------|
| **ALL** | Sistemdeki tüm aktif kiosklar (eczaneler) |
| **RULES** | Belirli İl / İlçe / Eczane hedeflemesi |

**ALL** seçilirse bu adımda başka bir şey yapman gerekmez.

**RULES** seçilirse:
- Dropdown'dan **İl** seç → **İl Ekle** butonu ile ekle
- İl seçiliyken altındaki **İlçe** dropdown aktif olur → **İlçe Ekle** ile ekle
- **Eczane Ara** alanından tekil eczane ekleyebilirsin
- Eklenen hedefler listede gösterilir; çöp kutusu ile kaldırılabilir

> `RULES` seçildiğinde en az 1 hedef zorunludur.

**İleri** butonuna tıkla.

---

### Adım 4 — Frekans & Pacing

**Pacing Modu** olarak 2 seçenek vardır:

#### A) Frekans Modu (önerilen)

Frekans Tipi seç:

| Tip | Açıklama | Örnek |
|-----|----------|-------|
| **PER_LOOP** | Her 60 saniyelik loop'ta N kez | `2` → 60 sn loop'ta 2 kez = 30 sn aralık |
| **PER_HOUR** | Seçili her saatte N kez | `4` → saatte 4 kez (15 dakikada bir) |
| **PER_DAY** | Gün boyunca toplam N kez | `100` → günde 100 kez, saatlere eşit dağıtılır |

**Hedef Saatler** (isteğe bağlı):  
Saat grid'inden tıklayarak sadece belirli saatlerde yayınlanmasını sağla.  
Seçilmezse 24 saat boyunca yayınlanır.

> **Kapasite uyarısı:** Frekans değeri fiziksel kapasiteyi aşarsa sistem hata gösterir.  
> Örn: 15 sn creative ile PER_LOOP max = `60 ÷ 15 = 4` kez.

#### B) Hedef Gösterim Modu

- **Toplam gösterim hedefi** gir (ör. `1000`)
- Sistem, kampanya süresine bölerek günlük frekansı otomatik hesaplar
- Hesaplanan değerler: Günlük Gösterim, Saatlik Gösterim, Tahmini Toplam görüntülenir

**İleri** butonuna tıkla. *(Bu adımdan sonra kampanya taslak olarak kaydedilir.)*

---

### Adım 5 — Simülasyon

Bu adım **salt okunurdur** — değişiklik yapılmaz.

**Simülasyonu Çalıştır** butonuna tıkla. Sistem şunları hesaplar:

| Bilgi | Açıklama |
|-------|----------|
| Kapsanan Kiosk Sayısı | Hedeflenen eczane/kiosk adedi |
| Toplam Gösterim | Kampanya süresi × günlük gösterim |
| Günlük Gösterim/Kiosk | Kiosk başına ortalama |
| Tahmini Fiyat | Pricing matrix'e göre tahmini maliyet (TRY) |

> Simülasyon yapılmadan aktivasyon mümkün değildir.

---

### Adım 6 — Özet & Aktive Et

Kampanya bilgilerini gözden geçir.

**Kampanyayı Aktive Et** butonuna tıkla → onay popup'ı çıkar → **Evet, Aktive Et**.

Aktivasyon başarılıysa:
- Kampanya `ACTIVE` duruma geçer
- Playlist motoru bir sonraki döngüde bu kampanyayı dahil eder
- Kiosk'lar sync sırasında yeni playlist'i çeker

> **409 Kapasite Hatası** alırsan: Frekans değerini düşür veya hedef saatleri azalt.

---

## 4. Kampanya Yönetimi

Ana kampanya listesinde:

| İşlem | Nasıl |
|-------|-------|
| Arama | Sağ üstteki arama kutusuna kampanya adı / reklamveren yaz |
| Durum filtresi | "Tüm Durumlar" dropdown'u |
| Sıralama | Tablo başlıklarına tıkla (Ad / Reklamveren / Başlangıç / Güncelleme) |
| Düzenle | Satır üzerindeki kalem ikonuna tıkla |
| Sil | Çöp kutusu ikonu → onay popup'ı |
| Toplu işlem | Checkbox ile birden fazla seç → Duraklat / Aktifleştir / Sil |

### Durum Geçişleri

```
DRAFT ──→ ACTIVE ──→ PAUSED
                 ↘
                  COMPLETED
```

- `ACTIVE`: Kiosklara yayınlanıyor
- `PAUSED`: Geçici durduruldu; yeniden aktive edilebilir
- `COMPLETED`: Bitiş tarihi geçti; salt okunur

---

## 5. Playlist Kontrolü

Sol menüden **Playlist Yönetimi** sayfası:

- Mevcut kiosk'ların listesi gösterilir
- Her kiosk için günlük ve saatlik planlar görüntülenir
- Bu sayfa **salt okunurdur** — playlist'ler sistem tarafından otomatik oluşturulur

**DoohControlCenter** (Kontrol Merkezi):

| Bölüm | Açıklama |
|-------|----------|
| Aktif Kampanya | Şu an yayındaki kampanya sayısı |
| Bekleyen İş | Playlist oluşturma kuyruğundaki iş sayısı |
| Son İşler | Son playlist generation job'larının durumu |
| Toplu Yenile | Seçili kampanyaların playlist'lerini zorla yenile |

---

## 6. Frekans Tipleri — Detaylı Açıklama

### PER_LOOP (Loop başına)

- Her kiosk 60 saniyelik bir "loop" döngüsünde çalışır
- `frequency_value = N` → her loop'ta N slot bu kampanyaya ayrılır
- **Kapasite:** 15 sn → max 4 | 30 sn → max 2 | 60 sn → max 1

**Örnek:** 15 sn creative, `PER_LOOP = 2`
- 1 saatte: 60 loop × 2 = **120 gösterim**
- 10 saatte: **1.200 gösterim**

---

### PER_HOUR (Saatte N kez)

- Hedef saatlerin her birinde tam olarak N kez oynatılır
- Slot, scheduler tarafından saat içine dağıtılır
- **Kapasite:** 15 sn → max 240/saat

**Örnek:** 15 sn creative, `PER_HOUR = 4`, hedef saatler 08–18 (10 saat)
- 1 saatte: 4 gösterim
- Günde: 10 saat × 4 = **40 gösterim**
- 10 günlük kampanya: **400 toplam gösterim**

---

### PER_DAY (Günde N kez)

- Gün boyunca toplam N kez oynatılır
- Scheduler, hedef saatler arasında eşit dağıtır
- **Kapasite:** 15 sn, 10 hedef saat → max 2.400/gün

**Örnek:** 15 sn creative, `PER_DAY = 100`, hedef saatler 08–18 (10 saat)
- Saatte: 100 ÷ 10 = **10 gösterim**
- 10 günlük kampanya: **1.000 toplam gösterim**

---

## 7. Örnek Senaryo

### Senaryo: 08:00–18:00 arası, günde 100 kez, 15 saniyelik kampanya

**Adım 1 — Bilgiler:**
```
Kampanya Adı  : Magnezyum Yaz 2026
Reklamveren   : ABC İlaç
Başlangıç     : 2026-08-01 08:00
Bitiş         : 2026-08-11 18:00   ← 10 gün
Durum         : ACTIVE
```

**Adım 2 — Medya:**
```
Dosya         : magnezyum_15sn.mp4
Süre          : 15 saniye
```

**Adım 3 — Hedefleme:**
```
Mod           : ALL   (tüm kiosklara yayınla)
```

**Adım 4 — Frekans:**

> Seçenek A — PER_HOUR kullan (en sezgisel):

```
Frekans Tipi  : PER_HOUR (Saatte N kez)
Frekans Değeri: 10
Hedef Saatler : 08, 09, 10, 11, 12, 13, 14, 15, 16, 17  ← 10 saat seç
```

Bu ayarla:
- Saatte 10 gösterim × 10 hedef saat = **günde 100 gösterim** ✅
- 10 günlük kampanya toplam = **1.000 gösterim**

> Seçenek B — PER_DAY kullan (daha basit):

```
Frekans Tipi  : PER_DAY (Günde N kez)
Frekans Değeri: 100
Hedef Saatler : 08 → 17 arası 10 saati seç
```

Bu ayarla da günde 100 gösterim elde edilir; scheduler 10 saate eşit dağıtır.

**Adım 5 — Simülasyon:**
- "Simülasyonu Çalıştır" tıkla
- Sonuç: `Günde ~100 gösterim, toplam ~1.000 gösterim, X kiosk`

**Adım 6 — Aktive Et:**
- "Kampanyayı Aktive Et" → Onayla

---

## 8. Sık Karşılaşılan Hatalar

| Hata | Nedeni | Çözüm |
|------|--------|-------|
| `duration_seconds 15sn grid ile uyumsuz` | 15/30/45/60 dışında süre girildi | Süreyi 15 sn yap |
| `Loop kapasitesi aşıldı: X × 15 sn > 60 sn` | PER_LOOP değeri çok yüksek | 15 sn creative için max 4 |
| `Simülasyon için önce kampanya kaydedilmelidir` | Adım 4 atlandı / tamamlanmadı | Adım 4'ü tamamlayıp İleri'ye bas |
| `Kapasite/kota hatası: blocking_reasons` | Slot dolu | Frekansı düşür veya tarih aralığını genişlet |
| `RULES hedefleme için en az bir hedef ekleyin` | RULES seçildi ama hedef eklenmedi | İl/İlçe/Eczane hedefi ekle |
| `end_date, start_date'ten sonra olmalıdır` | Tarihler hatalı | Bitiş tarihini kontrol et |
| `impression_goal Faz 7'de kaldırıldı` | Eski API formatı kullanıldı | DeliveryRule kullan (otomatik yapılıyor) |

---

*Son güncelleme: 2026-07-24 — Faz 7 DOOH v2 Canonical*
