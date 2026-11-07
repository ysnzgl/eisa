# Web Sitesi — Ortak Sözleşme (Backend ↔ Portal ↔ Site)

> Bu belge `apps/website` (Django), `web_panels` (Vue portal) ve `web_site` (Next.js) arasındaki **bağlayıcı** sözleşmedir.
> Üç taraf da yalnızca burada tanımlanan alan adlarını ve biçimleri kullanır. Değişiklik gerekiyorsa bu belge de güncellenir.
> Genel plan: `PLAN.md`. Bu belge PLAN.md ile çelişirse **bu belge geçerlidir**.

## 0. Plan Güncellemeleri (2026-11-07)

- **SMTP şimdilik yok.** Başvurular yalnızca portal gelen kutusuna düşer. E-posta altyapısı kurulmaz; ileride eklenebilecek şekilde bırakılır.
- **Kiosk fotoğrafı yok.** Hero ve görseller HTML/SVG tabanlı illüstrasyon ve mockup ile yapılır.
- **Spam koruması:** honeypot alanı + IP bazlı throttle. Turnstile yok.
- **KVKK ve çerez metinleri:** genel bir internet sitesi metni olarak tarafımızdan yazılır; CMS sayfası olarak portaldan düzenlenir.
- **Kazanç hesaplayıcı:** mevcut tablodan seed edilir; `kazanc_hesaplayici` bloğu olarak portaldan yönetilir.
- **Hakkımızda:** içerik tarafımızdan yazılır. Ekip: **Yasin ÖZGÜL — Yazılım Mimarı**. `ekip` bloğu olarak portaldan yönetilir.
- **Staging yok.** Lokal test sonrası canlıya çıkılır.

## 1. Lokal Geliştirme Portları ve Ortam Değişkenleri

| Servis | Port | Not |
|--------|------|-----|
| Backend (Django) | 8000 | `DJANGO_SETTINGS_MODULE=core_api.settings_dev_sqlite` ile SQLite |
| Portal (Vite) | 5174 | |
| Site (Next.js) | 3000 | |

**Backend env** (hepsinin lokal varsayılanı olmalı):
- `SITE_PUBLIC_URL`: varsayılan `http://localhost:3000` (önizleme linki ve canonical için)
- `SITE_REVALIDATE_URLS`: virgülle ayrılmış liste, varsayılan `http://localhost:3000/api/revalidate`
- `SITE_REVALIDATE_HEADLESS_HOST`: opsiyonel, `host:port`. Doluysa DNS ile çözülen **tüm** IP'lere `http://<ip>:<port>/api/revalidate` POST edilir (K8s headless service ile pod başına fan-out)
- `REVALIDATE_SECRET`: varsayılan `dev-revalidate-secret`
- `WEBSITE_SERVER_TOKEN`: varsayılan `dev-website-token`. Site sunucusunun API'ye "ben siteyim" demesi için kullanılır

**Site env:**
- `API_INTERNAL_URL`: varsayılan `http://localhost:8000` (sunucu tarafı fetch)
- `MEDIA_BASE_URL`: varsayılan `http://localhost:8000` (medya `yol` alanının önüne eklenir; prod `https://api.eisa.com.tr`)
- `SITE_URL`: varsayılan `http://localhost:3000` (prod `https://eisa.com.tr`)
- `REVALIDATE_SECRET`, `WEBSITE_SERVER_TOKEN`: backend ile aynı değerler

## 2. Ortak Tipler

### MediaRef
```json
{ "id": 12, "yol": "/api/media/website/2026/11/ab12cd.webp", "alt": "Kiosk", "genislik": 1600, "yukseklik": 900, "mime": "image/webp" }
```
- `yol` her zaman `/api/media/website/...` ile başlayan **göreli** yoldur. Site `MEDIA_BASE_URL + yol`, portal `API_BASE + yol` ile tam URL oluşturur.
- İzin verilen tipler: `image/jpeg`, `image/png`, `image/webp`, `image/gif`, `image/avif`. Üst sınır 10 MB. **SVG kabul edilmez** (XSS riski).
- `genislik` ve `yukseklik` yüklemede Pillow ile okunur; okunamazsa `null` olur.
- Blok verisinde ve blog kapağında MediaRef **nesne olarak** saklanır. Kaydederken backend `id`'nin var olduğunu doğrular ve `yol`, `alt`, `genislik`, `yukseklik`, `mime` alanlarını DB'den tazeler. Böylece istemciden gelen `yol`a güvenilmez.

### Buton
```json
{ "etiket": "Pilot Süreci İncele", "href": "/#pilot", "stil": "birincil" }
```
`stil`: `birincil` | `ikincil` | `hayalet`. `href` alanı: `/` ile başlayan iç yol, `#anchor`, `https://`, `mailto:`, `tel:` veya `https://wa.me/...`. Diğer şemalar (`javascript:` vb.) backend'de reddedilir.

### İkon
Phosphor ikon adı (PascalCase). İzin verilen küme (backend `secim` seçenekleri ve site ikon haritası **birebir** bu listedir):
`Sparkle, Brain, ShieldCheck, Package, ClockCounterClockwise, Timer, CheckCircle, UserCircle, Users, Storefront, QrCode, Receipt, ChartLineUp, TrendUp, Coins, CurrencyCircleDollar, Devices, DeviceMobile, Monitor, Cloud, CloudArrowUp, WifiSlash, Lightning, Heart, Heartbeat, FirstAidKit, Pill, Flask, Leaf, Moon, Lock, Handshake, Target, Megaphone, Lightbulb, Rocket, Gear, Cpu, Eye, ChatCircleText, Envelope, Phone, MapPin, Star, Medal, ArrowsClockwise, Plant, Smiley`
Site bilinmeyen bir ikon adı gelirse `Sparkle` gösterir.

### arka_plan
`acik` (beyaz/#F8FAF9) | `gri` (hafif gri-yeşil) | `koyu` (#0B0F14). Varsayılan `acik`.

## 3. Public API (yalnızca site sunucusu) — prefix `/api/website/public/`

> **App-key:** Public ve önizleme (§4) uçları yalnızca site sunucusuna açıktır: her istekte `X-Website-Token: <WEBSITE_SERVER_TOKEN>` zorunludur. Token yoksa veya yanlışsa **404** döner (uçların varlığı sızdırılmaz). Üretimde geliştirme varsayılan token'ı kabul edilmez. Tarayıcı bu uçları hiç çağırmaz; Traefik ingress'i de bu yolları internete kapatır.

Tüm public GET yanıtları `Cache-Control: public, max-age=60` döner. Yalnızca **yayında** içerik görünür.

### `GET site/`
```json
{
  "ayarlar": {
    "site_adi": "e-isa",
    "seo_baslik_sablonu": "%s | e-isa",
    "seo_aciklama": "...",
    "og_gorsel": null,
    "eposta": "iletisim@eisa.com.tr",
    "telefon": "",
    "whatsapp": "",
    "adres": "",
    "firma_unvani": "Eisa Bilişim Teknolojileri A.Ş.",
    "footer_aciklama": "...",
    "sosyal_linkler": [{ "platform": "linkedin", "url": "https://www.linkedin.com/company/e-isa" }]
  },
  "menuler": { "header": [MenuItem], "footer": [MenuItem], "footer_alt": [MenuItem] }
}
```
`platform` değerleri: `linkedin` | `instagram` | `x` | `youtube` | `facebook`.

**MenuItem** (backend, `href`'i çözülmüş olarak döner; yalnızca `aktif=true` öğeler gelir):
```json
{ "id": 3, "etiket": "Çözüm", "href": "/#nasil-calisir", "yeni_sekme": false, "cta": false, "cocuklar": [MenuItem] }
```
`href` çözümü:
- `sayfa` → `/` + slug; `anasayfa` slug'ı için `/`
- `bolum` → `/slug#anchor`; anasayfa için `/#anchor`
- `blog` → `/blog`
- `dis` → `url` olduğu gibi

Yayında olmayan bir sayfaya bağlı öğe public yanıta **dahil edilmez**. Alt menü yalnızca 1 seviye derinliktedir. `cta=true` olan header öğesi site tarafından kırmızı CTA butonu olarak gösterilir. Footer'da her üst öğe bir sütundur; `cocuklar` sütundaki linklerdir.

### `GET sayfalar/`
`[{ "slug": "anasayfa", "guncellenme": "2026-11-07T10:00:00Z" }]` (sitemap için)

### `GET sayfalar/<slug>/`
```json
{
  "slug": "anasayfa", "baslik": "Anasayfa",
  "seo": { "baslik": "...", "aciklama": "...", "og_gorsel": null },
  "yayin_tarihi": "2026-11-07T10:00:00Z", "revizyon_id": 7,
  "bloklar": [{ "id": "b_8f2a", "tip": "hero", "anchor_id": "", "veri": { } }]
}
```
- Sayfa yayında değilse 404 döner.
- `bloklar` yalnızca `gorunur=true` blokları içerir ve aktif revizyonun snapshot'ından okunur.
- `id`: blok için kalıcı string anahtardır (DB pk'den türetilebilir, ör. `"b_" + pk`).

### `GET blog/?kategori=<slug>&sayfa=1&boyut=9`
```json
{ "sonuclar": [BlogOzet], "toplam": 12, "sayfa": 1, "sayfa_sayisi": 2, "kategoriler": [{ "ad": "Sağlık Okuryazarlığı", "slug": "saglik-okuryazarligi" }] }
```
**BlogOzet:** `{ slug, baslik, ozet, kapak: MediaRef|null, kategori: {ad, slug}|null, etiketler: [str], yazar_adi, yayin_tarihi, okuma_suresi }`. `okuma_suresi` dakika cinsinden tam sayıdır.
Yalnızca `durum=yayinda` ve `yayin_tarihi <= now` olan yazılar gösterilir. Sıralama: `-yayin_tarihi`. `boyut` en fazla 24.

### `GET blog/<slug>/`
BlogOzet + `{ "icerik_html": "<p>...</p>", "seo": { baslik, aciklama, og_gorsel }, "ilgili": [BlogOzet] }`. `ilgili` aynı kategoriden en fazla 3 yazıdır.

### `POST basvurular/`
İstek:
```json
{ "tip": "pilot", "ad_soyad": "", "kurum": "", "eposta": "", "telefon": "", "il": "", "mesaj": "", "kvkk_onay": true, "kaynak_sayfa": "/", "website": "" }
```
- `tip`: `pilot` | `sponsor` | `genel`.
- Zorunlu alanlar: `ad_soyad`, `eposta`, `kvkk_onay=true`. `telefon` 0-20 karakter, `mesaj` en fazla 2000 karakter.
- **Honeypot:** `website` doluysa 201 dönülür ama kayıt **oluşturulmaz**.
- Yanıtlar: `201 {"ok": true}` | `400 {"alan": ["mesaj"]}` | `429`.
- **Throttle:** scope `website_basvuru`, `5/hour`, IP başına.
- **İstemci IP'si:** `X-Website-Token` header'ı `WEBSITE_SERVER_TOKEN` ile eşleşirse `X-Website-Client-IP` kullanılır; aksi halde `REMOTE_ADDR`. IP **ham saklanmaz**; `SECRET_KEY` ile tuzlanmış SHA-256 hash olarak saklanır.

## 4. Preview API — prefix `/api/website/preview/`

- `GET sayfalar/<slug>/?token=...` → public sayfa ile **aynı biçim**, ancak taslak bloklardan üretilir (`gorunur=true` olanlar). Sayfa yayında olmasa bile döner.
- `GET blog/<slug>/?token=...` → public blog detayı ile aynı biçim; taslak yazı da döner.
- `token`: `django.core.signing.TimestampSigner(salt="website-preview")` ile imzalı `"<tur>:<slug>"`. Geçerlilik 1 saattir. Geçersiz token → 403.
- Önizleme yanıtları `Cache-Control: no-store` döner.

## 5. Admin API — prefix `/api/website/admin/`

- Yetki: `IsWebsiteEditor` (rol `superadmin` veya `editor`).
- Yazma işlemleri `apps.core.uow.UnitOfWork` üzerinden yapılır.
- Liste uçları **düz dizi** döner. İstisna olarak `medya` ve `basvurular` `{count, results}` biçiminde, `?page=&page_size=` (varsayılan 24, en fazla 100) ile sayfalanır.
- Doğrulama hataları DRF standart biçimindedir (`{"alan": ["mesaj"]}`).

### Ayarlar
- `GET ayarlar/` → public `ayarlar` nesnesindeki alanların tamamı.
- `PATCH ayarlar/` → aynı alanlar. `og_gorsel` MediaRef nesnesi veya `null` olarak gönderilir. Kayıttan sonra `site` tag'i revalidate edilir.

### Blok tipleri
`GET blok-tipleri/` → `[{ "tip": "hero", "ad": "Hero", "aciklama": "...", "ikon": "Sparkle", "alanlar": [Alan] }]`

**Alan:**
```json
{ "ad": "baslik", "etiket": "Başlık", "tur": "metin", "zorunlu": true, "varsayilan": "", "yardim": "", "max_uzunluk": 160,
  "secenekler": [{ "deger": "koyu", "etiket": "Koyu" }], "min": 0, "max": 100,
  "alanlar": [Alan], "min_adet": 0, "max_adet": 8 }
```
`tur` değerleri:
- `metin`, `uzun_metin` (satır sonları korunur; çift satır sonu paragraf ayırır)
- `zengin_metin` (sanitize edilmiş HTML)
- `sayi`, `bool`, `secim`
- `ikon`: §2 listesinden secim
- `medya`: MediaRef|null
- `buton`: Buton nesnesi
- `liste`: `alanlar` alt şemasına uyan nesnelerden oluşan dizi; `min_adet` / `max_adet` ile sınırlanır

Opsiyonel anahtarlar yalnızca ilgili `tur` için gelir.

### Menüler
- `GET menuler/` → `{ "header": [AdminMenuItem], "footer": [...], "footer_alt": [...] }`
- `PUT menuler/<konum>/` → gövde `[AdminMenuItem]` (ağacın tamamı). Mevcut ağacı atomik olarak değiştirir ve yeni ağacı döner. `site` tag'i revalidate edilir.
- **AdminMenuItem:** `{ "id"?: int, "etiket": str, "link_tipi": "sayfa"|"bolum"|"blog"|"dis", "sayfa_id": int|null, "bolum_anchor": str, "url": str, "yeni_sekme": bool, "cta": bool, "aktif": bool, "cocuklar": [AdminMenuItem] }`
- Ağaç en fazla 2 seviyelidir. `sayfa`/`bolum` tipinde `sayfa_id` zorunludur; `dis` tipinde `url` zorunludur (izin verilen şemalar Buton ile aynı).
- Yanıtta her öğede ek olarak salt-okunur `href` (çözülmüş) bulunur.

### Sayfalar
- `GET sayfalar/` → `[{ id, slug, baslik, durum, sira, yayin_tarihi, guncellenme_tarihi, taslak_degisti, surum }]`. `durum`: `taslak` | `yayinda` | `arsiv`. `taslak_degisti`: taslak bloklar veya SEO, aktif revizyondan farklı mı?
- `POST sayfalar/` → `{ slug, baslik, seo_baslik, seo_aciklama, og_gorsel, sira }`. `slug`: `^[a-z0-9-]+$`. Ayrılmış slug'lar kabul edilmez: `blog`, `api`, `_next`, `admin`.
- `GET sayfalar/<id>/` → liste alanları + `{ seo_baslik, seo_aciklama, og_gorsel, bloklar: [{ id, tip, veri, sira, gorunur, anchor_id }] }`
- `PATCH sayfalar/<id>/` → meta alanları + `surum`. Optimistic concurrency: `surum` uyuşmazsa 409 döner.
- `DELETE sayfalar/<id>/` → `anasayfa`, `kvkk`, `cerez-politikasi` silinemez (400). Menüde kullanılan sayfa da silinemez (400, mesajda menü adı belirtilir).
- `PUT sayfalar/<id>/bloklar/` → gövde `{ "surum": int, "bloklar": [{ id?, tip, veri, gorunur, anchor_id }] }`. Dizi sırası `sira`'yı belirler. Taslak blokların tamamını değiştirir; `id`'si gelmeyen eski bloklar silinir. Her `veri` tip şemasına göre doğrulanır; bilinmeyen anahtarlar atılır, eksik opsiyonel alanlar varsayılanla doldurulur. Hata biçimi: `400 { "bloklar": { "2": { "baslik": ["Bu alan zorunludur."] } } }`. Başarıda güncel sayfa detayını döner.
- `POST sayfalar/<id>/yayinla/` → `{ "not": "" }`. Taslaktan `SayfaRevizyon` oluşturur, `aktif_revizyon` olarak atar ve `durum=yayinda` yapar. `sayfa:<slug>`, `sayfalar` ve `site` tag'leri revalidate edilir. Sayfa detayını döner.
- `POST sayfalar/<id>/yayindan-kaldir/` → `durum=taslak`. Aynı tag'ler revalidate edilir.
- `GET sayfalar/<id>/revizyonlar/` → `[{ id, yayinlayan_adi, yayin_tarihi, not, aktif }]`
- `POST sayfalar/<id>/revizyonlar/<rid>/geri-al/` → taslak blokları snapshot'tan yeniden oluşturur ve hemen yeni bir revizyon olarak yayınlar.
- `POST sayfalar/<id>/onizleme/` → `{ "url": "<SITE_PUBLIC_URL>/api/preview?tur=sayfa&slug=<slug>&token=<token>" }`

### Blog
- `GET|POST blog/kategoriler/`, `PATCH|DELETE blog/kategoriler/<id>/` → `{ id, ad, slug, sira }`
- `GET blog/yazilar/` → `[{ id, slug, baslik, durum, kategori: {id, ad}|null, yayin_tarihi, guncellenme_tarihi }]`
- `POST blog/yazilar/`, `GET|PATCH|DELETE blog/yazilar/<id>/` → `{ id, slug, baslik, ozet, kapak: MediaRef|null, icerik_html, kategori_id, etiketler: [str], yazar_adi, durum, yayin_tarihi, seo_baslik, seo_aciklama, okuma_suresi (salt-okunur, otomatik), surum }`
  - `icerik_html` backend'de `nh3` ile sanitize edilir. İzinli etiketler: `p, h2, h3, h4, ul, ol, li, strong, em, u, s, a[href, title, target, rel], blockquote, br, hr, code, pre, img[src, alt, width, height], figure, figcaption, table, thead, tbody, tr, th, td`. `img src` yalnızca `/api/media/website/` ile başlamalıdır. Linklere `rel="noopener noreferrer"` eklenir.
  - `durum=yayinda` ve `yayin_tarihi` boşsa şimdiki zaman atanır.
  - Kayıt/silme sonrası `blog` ve `blog:<slug>` tag'leri revalidate edilir.
- `POST blog/yazilar/<id>/onizleme/` → `{ url }` (`tur=blog`)

### Medya
- `GET medya/?q=&page=&page_size=` → `{ count, results: [MediaRef + { dosya_adi, boyut, olusturulma_tarihi }] }`
- `POST medya/` → multipart `dosya` + opsiyonel `alt` → MediaRef (+ ek alanlar), 201
- `PATCH medya/<id>/` → `{ alt }`
- `DELETE medya/<id>/` → 204. Kullanımda olup olmadığı kontrol edilmez; silinen görsel sitede gösterilmez (v1).
- Depolama: mevcut `StorageService` (RustFS/S3), object key prefix'i `website/YYYY/MM/<uuid>.<ext>`. `apps/core/media_proxy.py` allow-list'ine `website/` eklenir.
- **Lokal geliştirme:** S3 erişilemiyorsa (`WEBSITE_MEDIA_LOCAL=True`, settings_dev_sqlite'ta varsayılan `True`) dosyalar `MEDIA_ROOT/website/...` altına yazılır ve **aynı** `/api/media/website/...` yolundan servis edilir.

### Başvurular
- `GET basvurular/?tip=&durum=&q=&page=&page_size=` → `{ count, results: [Basvuru], yeni_sayisi }`
- **Basvuru:** `{ id, tip, ad_soyad, kurum, eposta, telefon, il, mesaj, kvkk_onay, kvkk_metin_versiyonu, kaynak_sayfa, durum, notlar, atanan: {id, ad}|null, olusturulma_tarihi }`. `durum`: `yeni` | `incelendi` | `iletisimde` | `kapandi`.
- `GET|PATCH|DELETE basvurular/<id>/` → PATCH ile değişebilen alanlar: `durum`, `notlar`, `atanan_id`.
- `GET basvurular/ozet/` → `{ "yeni": 3 }` (portal menü rozeti)

## 6. Revalidation (Backend → Site)

- `POST {url}` ile JSON `{ "tags": ["sayfa:anasayfa", "sayfalar", "site"] }` gönderilir; header `X-Revalidate-Secret: <REVALIDATE_SECRET>`.
- Backend bunu `transaction.on_commit` içinde, kısa timeout (3 sn) ile yapar. Hata loglanır, **istek başarısız sayılmaz**.
- Site tag'leri: `site`, `sayfalar`, `sayfa:<slug>`, `blog`, `blog:<slug>`.
- Site, secret yanlışsa 401 döner; doğruysa her tag için `revalidateTag` çalıştırır ve `{ "revalidated": [...] }` döner.
- Site ayrıca zaman bazlı revalidate kullanır: sayfalar 3600 sn, blog listesi 300 sn (zamanlanmış yazılar için).

## 7. Önizleme (Portal → Site)

1. Portal `onizleme/` ucunu çağırır ve dönen `url`'i yeni sekmede açar.
2. Site `GET /api/preview?tur=&slug=&token=` isteğinde token'ı backend preview ucunu çağırarak doğrular. 200 gelirse `draftMode().enable()` yapar, token'ı httpOnly `eisa_preview` çerezine yazar ve ilgili sayfaya yönlendirir (anasayfa için `/`, blog için `/blog/<slug>`).
3. Draft mode açıkken sayfa preview ucundan `cache: 'no-store'` ile okunur ve üstte "Önizleme modu — Çık" bandı gösterilir. `/api/preview/exit` draft mode'u kapatır.

## 8. Blok Kataloğu — `veri` Şemaları

Kısaltma: `?` opsiyonel alan. Varsayılanlar backend şemasında tanımlıdır.

| Tip | Ad | `veri` |
|-----|----|--------|
| `hero` | Hero (Anasayfa) | `rozet?`, `baslik`, `vurgu?` (baslik içinde kırmızı vurgulanacak alt-metin), `alt_metin?`, `vurgu_kartlari: [{ikon, metin}]` (0-6), `butonlar: [Buton]` (0-3), `kiosk_animasyonu: bool` (varsayılan true) |
| `sayfa_basligi` | Sayfa Başlığı (iç sayfalar) | `rozet?`, `baslik`, `vurgu?`, `alt_metin?`, `butonlar: [Buton]` (0-2) |
| `ozellik_kartlari` | Özellik Kartları | `ust_baslik?`, `baslik?`, `aciklama?`, `sutun: 2|3|4` (secim, varsayılan 3), `kartlar: [{ikon, baslik, metin}]` (1-12), `arka_plan` |
| `vurgu_bandi` | Vurgu Bandı | `ikon`, `baslik`, `metin?`, `vurgu_cumlesi?`, `stil: kirmizi|koyu|acik` |
| `scroll_hikaye` | Scroll Hikâye (Kiosk) | `ust_baslik?`, `baslik`, `aciklama?`, `adimlar: [{baslik, metin, ekran_baslik, ekran_metin}]` (2-6) |
| `surec_adimlari` | Süreç Adımları | `ust_baslik?`, `baslik`, `aciklama?`, `adimlar: [{baslik, metin}]` (2-8), `arka_plan` |
| `gorsel_metin` | Görsel + Metin | `ust_baslik?`, `baslik`, `metin` (uzun_metin), `maddeler: [{ikon, metin}]` (0-8), `gorsel: MediaRef|null` (boşsa site dekoratif kiosk/teknoloji illüstrasyonu çizer), `gorsel_konumu: sol|sag`, `butonlar: [Buton]` (0-2), `arka_plan` |
| `kazanc_hesaplayici` | Kazanç Hesaplayıcı | `ust_baslik?`, `baslik`, `aciklama?`, `kademeler: [{etkilesim_min, etkilesim_max, gunluk_satis, aylik_satis, aylik_ciro, aylik_kar}]` (1-10, sayı), `varsayilan_etkilesim` (sayı), `slider_max` (sayı), `para_birimi` (varsayılan "TL"), `uyari_notu`, `tablo_goster: bool` |
| `sayaclar` | Sayaçlar | `baslik?`, `ogeler: [{deger: sayi, onek?, sonek?, etiket}]` (1-6), `arka_plan` |
| `logo_bandi` | Logo Bandı | `baslik?`, `logolar: [{gorsel: MediaRef, ad, url?}]` (0-30), `bos_mesaj?` |
| `sss` | SSS | `ust_baslik?`, `baslik`, `aciklama?`, `sorular: [{soru, cevap (uzun_metin)}]` (1-30), `arka_plan` |
| `cta_banner` | CTA Bandı | `rozet?`, `baslik`, `metin?`, `butonlar: [Buton]` (1-2), `stil: koyu|kirmizi` |
| `basvuru_formu` | Başvuru Formu | `ust_baslik?`, `baslik`, `aciklama?`, `form_tipi: pilot|sponsor|genel`, `maddeler: [{ikon, baslik, metin}]` (0-6), `basari_mesaji`, `kvkk_sayfa_slug` (varsayılan "kvkk"), `iletisim_bilgisi_goster: bool` |
| `blog_son_yazilar` | Son Blog Yazıları | `baslik?`, `aciklama?`, `adet: sayi` (1-6, varsayılan 3), `kategori_slug?` |
| `ekip` | Ekip | `ust_baslik?`, `baslik`, `aciklama?`, `kisiler: [{ad_soyad, unvan, biyografi?, foto: MediaRef|null, linkedin?}]` (1-24) |
| `zengin_metin` | Zengin Metin | `baslik?`, `icerik_html` (zengin_metin), `genislik: dar|genis`, `son_guncelleme?` (metin, ör. "7 Kasım 2026") |

Kazanç kademeleri seed'i (mevcut tablodan):

| etkileşim | günlük satış | aylık satış | aylık ciro | aylık kâr |
|---|---|---|---|---|
| 1-10 | 1 | 25 | 18000 | 6000 |
| 10-20 | 3 | 75 | 56000 | 18000 |
| 20-30 | 6 | 150 | 110000 | 36000 |
| 30-40 | 10 | 250 | 185000 | 62000 |
| 40-50 | 15 | 375 | 280000 | 94000 |

Kademe seçimi: kaydırıcı değeri `v` için `etkilesim_min <= v <= etkilesim_max` koşulunu sağlayan **ilk** kademe kullanılır. `v` tüm kademelerin üstündeyse son kademe kullanılır.

## 9. Seed İçeriği (`python manage.py website_seed`)

- **Idempotent:** slug veya konum bazlı upsert. Mevcut içeriğin üzerine yalnızca `--force` ile yazar.
- Tüm sayfaları **yayınlanmış** olarak oluşturur.
- Kaynak: mevcut site (`e-isa-company-websit/src/pages/*.tsx`) ve `eisa-website-brief.md`. İçerik tonu: teşhis veya tedavi vaadi yoktur, kazanç "örnek senaryo"dur, kontrol eczacıdadır.

| slug | Bloklar (sırayla; `#` = anchor_id) |
|------|-------------------------------------|
| `anasayfa` | hero · ozellik_kartlari (e-isa nedir, 4 kart) `#nasil-calisir` · vurgu_bandi (dürtme yaklaşımı) · ozellik_kartlari (3 altın kural) `#eczaci-kontrolu` · scroll_hikaye (4 adımlı yolculuk) `#yolculuk` · kazanc_hesaplayici `#kazanc` · ozellik_kartlari (pasif gelir ekosistemi) · sss (5 soru) `#sss` · blog_son_yazilar · basvuru_formu (pilot) `#pilot` |
| `teknoloji` | sayfa_basligi · gorsel_metin (Samsung 24" kiosk) · ozellik_kartlari (kompakt, modern deneyim, QR/dijital sonuç, bulut + çevrimdışı senkron) · sayaclar (60 sn etkileşim, 2-4 soru, 24 inç ekran, 1 ay ücretsiz pilot) · surec_adimlari (kurulum: keşif → kurulum → eğitim → izleme) · cta_banner |
| `sponsorlar` | sayfa_basligi · ozellik_kartlari (neden e-isa, 3 kart) · surec_adimlari (4 adımlı başvuru süreci) · logo_bandi (boş, `bos_mesaj`) · basvuru_formu (sponsor) `#basvuru` |
| `hakkimizda` | sayfa_basligi · gorsel_metin (hikâyemiz) · ozellik_kartlari (değerlerimiz: eczacı merkezli, etik, veri odaklı, sade teknoloji) · ekip (Yasin ÖZGÜL — Yazılım Mimarı) · cta_banner |
| `iletisim` | sayfa_basligi · basvuru_formu (genel, `iletisim_bilgisi_goster=true`) |
| `kvkk` | sayfa_basligi · zengin_metin (genel KVKK aydınlatma metni; veri sorumlusu Eisa Bilişim Teknolojileri A.Ş.; form verileri, amaç, hukuki sebep, saklama, haklar — 6698 sayılı Kanun m.11; başvuru: iletisim@eisa.com.tr) |
| `cerez-politikasi` | sayfa_basligi · zengin_metin (zorunlu ve analitik çerezler, yönetim) |

**Menüler:**
- `header`:
  - Çözüm (`bolum` anasayfa `#nasil-calisir`), alt öğeler: Nasıl Çalışır `#nasil-calisir`, Eczacı Kontrolü `#eczaci-kontrolu`, Müşteri Yolculuğu `#yolculuk`, Kazanç Modeli `#kazanc`, SSS `#sss`
  - Teknoloji, Sponsorlar, Blog
  - Kurumsal (`sayfa` hakkimizda), alt öğeler: Hakkımızda, İletişim
  - **Ücretsiz Pilot** (`bolum` anasayfa `#pilot`, `cta=true`)
- `footer`:
  - Ürün: Nasıl Çalışır, Teknoloji, Kazanç Modeli, SSS
  - Kurumsal: Hakkımızda, Sponsorlar, Blog, İletişim
- `footer_alt`: KVKK Aydınlatma Metni, Çerez Politikası

**Ayarlar:**
- eposta `iletisim@eisa.com.tr`
- linkedin `https://www.linkedin.com/company/e-isa`, instagram `https://www.instagram.com/eisa.tr/`
- telefon, whatsapp ve adres boş (site boş alanları gizler)
- seo_aciklama: brief §7'deki metin

**Blog:**
- Kategoriler: Sağlık Okuryazarlığı, Eczane Yönetimi, Duyurular.
- 3 yayınlanmış yazı (Türkçe, özgün, temkinli dil):
  1. "Reçete bekleme süresi eczane için neden bir fırsat?"
  2. "Dürtme (nudge) yaklaşımı sağlık okuryazarlığına nasıl katkı sağlar?"
  3. "e-isa ücretsiz pilot süreci nasıl işler?"

## 10. Site Tasarım Kuralları (özet)

- **Renk tokenları:** primary `#ED1C24`, primary-hover `#C8141B`, dark `#0B0F14`, ink `#1F2933`, muted `#65736F`, brand-deep `#3F514D`, bg `#F8FAF9`, card `#FFFFFF`, line `#E6ECEA`.
- **Fontlar:** `next/font/google` ile Space Grotesk (başlık) ve Inter (gövde). **`subsets: ['latin', 'latin-ext']`** zorunludur (Türkçe karakterler).
- **Logo:** `public/brand/logo.svg` ve `public/brand/logo-white.svg` (eski repodan kopyalanır). Koyu zeminde beyaz logo kullanılır.
- **Hero:** koyu zemin. Arka planda hafif canvas/SVG "AI ağı" (düşük yoğunluk, `requestAnimationFrame`, görünür değilken durur). Sağda HTML/SVG kiosk mockup; ekranında döngüsel akış oynar: soru → seçenek → kategori önerisi → QR → "Eczacı onayı". Başlık kelime kelime belirir.
- **Animasyon:** `motion` (framer-motion) + `lenis`. `prefers-reduced-motion` açıkken scroll-pin, parallax ve sürekli animasyonlar kapanır, içerik statik gösterilir.
- **Header:** scroll'da daralır ve cam efekti alır. Koyu hero üzerinde açık renk metin kullanılır, scroll sonrası koyu metne geçer. Mobilde tam ekran animasyonlu menü açılır. Anchor linkler sabit header yüksekliği kadar offset ile kayar; başka sayfadan `/#anchor` linkine gelindiğinde de doğru konuma iner.
- **Erişilebilirlik:** semantik başlık hiyerarşisi (sayfa başına tek h1), görünür odak halkaları, ikon butonlarında `aria-label`, AA kontrast.
- **Performans:** bloklar mümkün olduğunca Server Component olarak yazılır; animasyonlu kısımlar küçük client adacıkları olur. İkonlar tek tek import edilir (barrel import yok). Görseller `next/image` ile yüklenir.
## Ek: Backend Notları

> `apps/website` uygulamasını yazarken sözleşmede açık kalan noktalar için verilen kararlar. Portal ve site bu davranışlara güvenebilir.

**Şema / bloklar**
- `[Buton]` listeleri (`butonlar`) blok şemasında `tur: "liste"` + `alanlar: [etiket (metin), href (metin), stil (secim)]` olarak gelir; veri biçimi birebir `[{etiket, href, stil}]`'dir. Portal bağlantı seçicisini `ad === "href"` alanında kullanabilir. Tekil `buton` türü şu an katalogda kullanılmıyor.
- Buton/menü `href` kuralı: `/` ile başlayan iç yol (`//` ve `/\` hariç), `#anchor` (`^#[A-Za-z0-9][A-Za-z0-9_-]*$`), `https://<host>`, `mailto:a@b`, `tel:+905550000000` (**boşluksuz**). Boşluk/kontrol karakteri ve `\` içeren her değer reddedilir; `http://` kabul edilmez.
- `hero` ve `sayfa_basligi` için `vurgu` doluysa `baslik` içinde birebir geçmelidir (aksi 400).
- `kazanc_hesaplayici`: her kademede `etkilesim_min <= etkilesim_max`, ayrıca `varsayilan_etkilesim <= slider_max` zorunludur.
- `anchor_id`: `^[a-z0-9][a-z0-9_-]*$`, en fazla 60 karakter, sayfa içinde tekil; baştaki `#` otomatik atılır. Menüdeki `bolum_anchor` için de aynı kural geçerlidir.
- Admin blok `id`'si tam sayıdır (DB pk). Public/preview `id`'si `"b_<pk>"`'dir. `PUT bloklar/` her iki biçimi de kabul eder; `id`'si eşleşen ve tipi değişmeyen blok güncellenir (pk korunur).
- Revizyon snapshot'ı `gorunur=false` blokları da içerir (geri alma için); public yanıt bunları filtreler.
- Yanıt üretilirken tüm MediaRef'ler (blok verisi, `og_gorsel`, `kapak`) tek sorguyla DB'den tazelenir: `alt` değişikliği anında yansır, silinmiş medya `null` döner.

**Sayfalar**
- `PATCH sayfalar/<id>/` ve `PUT sayfalar/<id>/bloklar/` için `surum` **zorunludur** (yoksa 400). Blog yazısı `PATCH`'inde `surum` opsiyoneldir; gönderilirse kontrol edilir.
- 409 gövdesi: `{"detail": "...", "surum": <güncel surum>}`.
- `yayinla`, `yayindan-kaldir`, `geri-al` sayfanın `surum`'unu artırır; portal yanıttaki `surum`'u kullanmalıdır.
- Sayfa `baslik`/SEO alanları da snapshot'a girer; public `baslik` ve `seo` yalnızca yayınlayınca değişir. **İstisna:** `slug` değişikliği anında etkilidir (eski ve yeni `sayfa:<slug>` tag'leri revalidate edilir). `anasayfa`, `kvkk`, `cerez-politikasi` sluglarının adresi değiştirilemez.
- Public `seo.baslik` = `seo_baslik || baslik`; `seo.aciklama` = `seo_aciklama` (boş olabilir; site `ayarlar.seo_aciklama`'ya düşer). Blogda `seo.aciklama` = `seo_aciklama || ozet`, `seo.og_gorsel` = `kapak`.
- Admin sayfa listesindeki `yayin_tarihi` son yayın anıdır.

**Menüler**
- `PUT menuler/<konum>/` doğrulama hatası kök dizi indeksine göre döner: `400 {"0": {"etiket": ["..."]}, "3": {"cocuklar": {"1": {"url": ["..."]}}}}`. Gövde dizi değilse `{"non_field_errors": [...]}`.
- `bolum` tipinde `bolum_anchor` da zorunludur. Kullanılmayan alanlar tipine göre temizlenir (ör. `blog` için `sayfa_id=null`, `url=""`).
- Ek olarak `GET menuler/<konum>/` tek konumun ağacını döner.

**Blog**
- Public `kategoriler` yalnızca en az bir görünür (yayında ve tarihi gelmiş) yazısı olan kategorileri içerir. `sayfa_sayisi` en az 1'dir; geçersiz `sayfa`/`boyut` varsayılana düşer.
- `slug` boş gönderilirse başlıktan Türkçe karakterler dönüştürülerek üretilir (ör. "Dürtme Yaklaşımı" → `durtme-yaklasimi`). Kategori için de aynısı geçerlidir.
- `okuma_suresi` = ceil(kelime / 200), en az 1. `etiketler` en fazla 10 adet × 40 karakter, tekilleştirilir.
- Admin `GET blog/yazilar/?durum=` filtresi desteklenir.

**Başvurular**
- Public GET uçlarında throttle **yoktur** (site sunucusu tüm istekleri tek pod IP'sinden yapar). Yalnızca `POST basvurular/` `website_basvuru` (5/hour) ile sınırlıdır; sayaç istemci IP'sinin hash'ine göre tutulur.
- `X-Website-Client-IP` yalnızca geçerli bir IP ise ve `X-Website-Token` eşleşirse kullanılır. Üretimde (`DEBUG=False`) token varsayılan `dev-website-token` ise başlık **yok sayılır**.
- `kvkk_metin_versiyonu` = başvuru anındaki yayınlanmış `kvkk` sayfasının aktif revizyonu, `"kvkk-r<revizyon_id>"` (sayfa yayında değilse boş).
- `kaynak_sayfa` yalnızca `/` ile başlayan site içi yol olarak saklanır; aksi hâlde boş kaydedilir. `telefon` yalnızca rakam, boşluk, `+ ( ) -` içerebilir.
- Admin `PATCH basvurular/<id>/` için `atanan_id` aktif bir `superadmin` veya `editor` kullanıcısı olmalıdır. Liste yanıtında `ip_hash` dönmez.

**Medya**
- Tür, istemcinin bildirdiği `content-type`'a değil dosya içeriğine (Pillow) göre belirlenir; uzantı da buna göre verilir. İçeriği `<` ile başlayan veya `<svg` içeren dosyalar reddedilir. Pillow'un açamadığı ama imzası AVIF olan dosyalar `genislik/yukseklik = null` ile kabul edilir.
- `/api/media/website/...` yanıtı `Cache-Control: public, max-age=86400` döner (anahtarlar uuid'li ve değişmez).

**Rol / güvenlik**
- `editor` rolü bir eczaneye bağlanamaz (kullanıcı yönetimi API'si `eczane`'yi `null`'a çeker). Önceden `IsAuthenticated` ile açık olan eczane listesi/detayı, etken madde listesi, katalog senkronu (`/api/products/sync/`) ve destek talepleri artık `superadmin` veya `eczacı` ister; editor bu uçlarda 403 alır.
