# eisa.com.tr — Yönetilebilir Web Sitesi Planı

> Durum: Taslak plan · Tarih: 2026-11-07
> Kapsam: Kurumsal sitenin (eisa.com.tr) portal.eisa.com.tr üzerinden yönetilebilir, animasyonlu, SEO dostu yeni sürümü.

---

## 1. Alınan Kararlar

| Konu | Karar |
|------|-------|
| Site teknolojisi | **Next.js (App Router) + ISR**: portalda "Yayınla" denince on-demand revalidation ile saniyeler içinde güncellenir |
| İçerik modeli | **Blok tabanlı**: sayfa = sıralı bloklar; her blok tipinin sabit alan şeması vardır |
| Tasarım tonu | **Koyu hero + açık içerik**: teknolojik açılış, medikal güven veren gövde |
| Kod yeri | **Monorepo `web_site/`**: API + portal + site aynı repoda; eski `e-isa-company-websit` reposu arşivlenir |
| Yönetim yetkisi | **Yeni `editor` rolü**: yalnızca "Web Sitesi" modülünü görür; SuperAdmin de tam yetkili |
| Başvuru bildirimi | **Portal gelen kutusu + SMTP e-posta** |
| v1 ek modüller | Başvuru formu → portal, Etkileşimli kazanç hesaplayıcı, Blog/Haberler |
| v1 sayfalar | Anasayfa, Teknoloji/Kiosk, Markalar & Sponsorlar, Hakkımızda, Blog, İletişim/Pilot, KVKK & Çerez |

---

## 2. Mimari

```
portal.eisa.com.tr (Vue 3)          api.eisa.com.tr (Django/DRF)            eisa.com.tr (Next.js)
┌───────────────────────┐  JWT     ┌──────────────────────────┐  cluster  ┌─────────────────────────┐
│ Web Sitesi modülü     │ ───────► │ apps/website             │ ◄──────── │ Server Components        │
│  Sayfalar / Menüler   │  cookie  │  admin API  (editor+SA)  │  içi HTTP │  fetch(tag) + ISR cache  │
│  Blog / Medya         │          │  public API (AllowAny)   │           │  /api/revalidate         │
│  Başvurular / Ayarlar │          │  preview API (imzalı)    │ ────────► │  /api/preview (draft)    │
└───────────────────────┘          │  MinIO: website/ prefix  │ yayınla → │  Form → server action    │
                                   └──────────────────────────┘ revalidate└─────────────────────────┘
```

- Site, API'ye **cluster içinden** erişir (`http://eisa-api.eisa-app.svc`). CORS gerekmez ve dış trafik oluşmaz.
- **Dayanıklılık:** API erişilemezse Next.js son başarılı önbelleği sunmaya devam eder (ISR stale-while-revalidate). Ek güvenlik ağı olarak zaman bazlı revalidate (ör. 1 saat) da açık olur.
- **Başvuru formu**, Next.js server action üzerinden API'ye iletilir (gerçek istemci IP'si `X-Forwarded-For` ile aktarılır). Böylece tarayıcıdan API'ye doğrudan istek gitmez.
- **Önizleme:** Portaldaki "Önizle" butonu, kısa ömürlü imzalı token ile `eisa.com.tr/api/preview?slug=...&token=...` adresini açar. Next.js draft mode'a geçer ve taslak içeriği gösterir.

---

## 3. Backend — `apps/website`

### 3.1 Veri Modeli

| Model | Alanlar (özet) | Not |
|-------|----------------|-----|
| `SiteAyarlari` (singleton) | site_adi, seo_baslik_sablonu, seo_aciklama, og_gorsel, eposta, telefon, whatsapp, adres, sosyal_linkler (JSON), analytics_id, bildirim_alicilari | Footer, iletişim, varsayılan SEO buradan beslenir |
| `Menu` | konum (`header` / `footer` / `footer_alt`) | Konum başına bir menü |
| `MenuOgesi` | menu, ust (self FK, alt menü), etiket, link_tipi (`sayfa` / `bolum` / `blog` / `dis`), sayfa FK, bolum_anchor, url, yeni_sekme, cta_stili, sira, aktif | Mobil menü header'dan otomatik türetilir; tek kaynak |
| `Sayfa` | slug (unique), baslik, seo_baslik, seo_aciklama, og_gorsel, durum (`taslak` / `yayinda` / `arsiv`), aktif_revizyon FK, sira | `/` için slug = `anasayfa` |
| `Blok` | sayfa, tip, veri (JSON), sira, gorunur, anchor_id | Düzenlenen **taslak** hali |
| `SayfaRevizyon` | sayfa, bloklar_snapshot (JSON), seo_snapshot, yayinlayan, yayin_tarihi, not | Yayınla = taslağın değişmez kopyası. Public API sadece bunu okur (tek sorgu) ve geri alma kolaydır |
| `BlogKategori` | ad, slug, sira | |
| `BlogYazisi` | slug, baslik, ozet, kapak, icerik (sanitize HTML), kategori, etiketler, yazar, durum, yayin_tarihi, seo alanları, okuma_suresi | İçerik sunucuda `nh3` ile sanitize edilir |
| `WebsiteMedya` | object_key (`website/...`), dosya_adi, mime, boyut, genislik, yukseklik, alt_metin | MinIO'daki mevcut altyapı kullanılır |
| `Basvuru` | tip (`pilot` / `sponsor` / `genel`), ad_soyad, kurum, eposta, telefon, il, mesaj, kvkk_onay, kvkk_metin_versiyonu, kaynak_sayfa, ip_hash, durum (`yeni` / `incelendi` / `iletisimde` / `kapandi`), atanan, notlar, bildirim_gonderildi | IP ham değil hash'li saklanır; saklama süresi KVKK politikasına göre belirlenir |

Mevcut `apps/core/uow.py` (`save_new` / `save_update`, `expected_version`) desenleri kullanılır. Böylece iki editör aynı sayfayı düzenlerse çakışma yakalanır. `apps/audit` ile değişiklik kaydı tutulur.

### 3.2 Blok Tipi Kayıt Defteri (Registry)

Her blok tipi için backend'de bir DRF serializer şeması tanımlanır (`website/blocks/<tip>.py`). Bu şemanın görevleri:
1. `Blok.veri` kaydedilirken doğrulama yapmak,
2. `GET /api/website/admin/blok-tipleri/` ile **alan şemasını portala vermek**. Portal, formları bu şemadan otomatik üretir. Böylece yeni bir blok eklemek için portalda ayrı bir form yazmak gerekmez.

### 3.3 Endpoint'ler

**Public** (AllowAny, throttle, `Cache-Control`):
- `GET  /api/website/public/site/`: ayarlar + menüler
- `GET  /api/website/public/sayfalar/<slug>/`: aktif revizyon
- `GET  /api/website/public/sayfalar/`: sitemap için slug + güncellenme tarihi
- `GET  /api/website/public/blog/?kategori=&sayfa=` · `GET /api/website/public/blog/<slug>/`
- `POST /api/website/public/basvurular/`: sıkı throttle, honeypot alanı, (opsiyonel) Turnstile doğrulama

**Preview** (imzalı kısa ömürlü token):
- `GET  /api/website/preview/sayfalar/<slug>/` · `GET /api/website/preview/blog/<slug>/`

**Admin** (`IsWebsiteEditor` = superadmin veya editor):
- CRUD: `ayarlar`, `menuler`, `sayfalar`, `sayfalar/<id>/bloklar` (toplu sıralama), `blog`, `blog-kategoriler`, `medya` (upload), `basvurular`
- Aksiyonlar: `sayfalar/<id>/yayinla`, `sayfalar/<id>/revizyonlar`, `revizyonlar/<id>/geri-al`, `sayfalar/<id>/onizleme-token`, `basvurular/export`

### 3.4 Diğer Backend Değişiklikleri
- `Kullanici.Rol` içine `EDITOR = "editor"` ve migration.
- `IsWebsiteEditor` permission'ı. Mevcut `IsSuperAdmin` (`apps/pharmacies/permissions.py`) bozulmaz.
- `apps/core/media_proxy.py` allow-list'ine `website/` prefix'i eklenir.
- **E-posta:** `EMAIL_*` ayarları (env / `eisa-app-secrets`). Bildirimler mevcut `run_scheduler` (django-apscheduler) ile dakikalık job olarak gönderilir: `bildirim_gonderildi=False` kayıtlar taranır, hata olursa tekrar denenir. Form yanıtı e-postayı beklemez.
- **Yayın webhook'u:** `yayinla` / `geri-al` / ayar-menü-blog değişikliğinde `transaction.on_commit` ile `POST {SITE_INTERNAL_URL}/api/revalidate` çağrılır. İstek `REVALIDATE_SECRET` ve ilgili tag'leri taşır (`site`, `sayfa:<slug>`, `blog`, `blog:<slug>`).
- **Seed komutu:** `python manage.py website_seed`, mevcut sitedeki tüm içeriği (Home, Sponsorlar, SSS, tablo…) bloklara dönüştürür.
- Testler: pytest + factory-boy (mevcut düzen). Şema doğrulama, yetki, throttle, yayın/geri alma, webhook mock'lanarak.

---

## 4. Portal — "Web Sitesi" Modülü (`web_panels`)

| Ekran | İçerik |
|-------|--------|
| **Sayfalar** | Liste (durum, son yayın, yayınlayan) → **Sayfa Editörü**: solda blok listesi (sürükle-bırak sıralama, gizle/göster, kopyala, sil), sağda şemadan üretilen form, üstte *Taslak Kaydet · Önizle · Yayınla · Revizyonlar* |
| **Menüler** | Header / Footer sekmeleri, sürükle-bırak ağaç; link tipi seçiciyle sayfa, bölüm (anchor), blog veya dış link |
| **Blog** | Yazılar (TipTap editör, kapak görseli, SEO alanları, zamanlanmış yayın), Kategoriler |
| **Medya** | Kütüphane: yükle, alt metin, ara; formlarda "medya seç" diyaloğu |
| **Başvurular** | Gelen kutusu: tip/durum filtresi, detay, durum değişikliği, not, atama, Excel export (mevcut `xlsx`); menüde okunmamış sayısı |
| **Site Ayarları** | İletişim, sosyal, varsayılan SEO/OG, bildirim alıcıları |

- Router: `/admin/web-sitesi/*` rotalarına `meta: { roles: ['superadmin', 'editor'] }`. Editor giriş yapınca doğrudan buraya yönlenir. `AdminLayout.vue` menüsü role göre filtrelenir. **Dikkat:** mevcut admin parent route `roles: ['superadmin']` olduğundan web sitesi rotaları ya ayrı parent altına ya da route bazlı meta ile kurulmalı.
- Yeni bağımlılıklar: `vuedraggable` (SortableJS), `@tiptap/vue-3`.
- Ortak alan bileşenleri: metin, uzun metin, ikon seçici (Phosphor isim listesi), medya seçici, link seçici, liste/tekrarlayıcı (kart listeleri için), sayı, toggle.

---

## 5. Site — `web_site/` (Next.js)

### 5.1 Teknik Yığın
- Next.js (App Router, `output: 'standalone'`), TypeScript, Tailwind CSS 4
- Motion (framer-motion) + Lenis (yumuşak scroll). Sabitlenmiş (pinned) scroll anlatımı için gerekirse GSAP ScrollTrigger
- Phosphor ikonlar, `next/image` (remote: `api.eisa.com.tr/api/media/`), `next/og` (dinamik OG görselleri)
- Spark'tan gelen kullanılmayan bağımlılıklar (octokit, d3, three, recharts, @github/spark…) taşınmaz

### 5.2 Yapı
```
web_site/
  app/
    layout.tsx               # tek Layout: Header + Footer (menüler API'den)
    [[...slug]]/page.tsx     # blok tabanlı tüm sayfalar
    blog/page.tsx · blog/[slug]/page.tsx
    api/revalidate/route.ts · api/preview/route.ts
    sitemap.ts · robots.ts · opengraph-image.tsx
  blocks/                    # blok tipi → React bileşeni (registry)
  components/                # Header, Footer, KioskMockup, CookieBanner, ...
  lib/api.ts                 # tipli fetch + cache tag'leri
```
- Eski URL'ler korunur: `/iletisim`, `/sponsorlar`. Değişen olursa 301 yönlendirme yapılır.
- Bilinmeyen blok tipi gelirse sessizce atlanır ve loglanır; site çökmez.

### 5.3 v1 Blok Kataloğu

| Blok | Açıklama |
|------|----------|
| `hero` | Koyu zemin, AI ağı arka planı, başlık (kelime kelime belirme), alt metin, vurgu kartları, CTA'lar, animasyonlu kiosk mockup (aç/kapa) |
| `scroll_hikaye` | 4 adımlı müşteri yolculuğu; bölüm sabitlenir, scroll ilerledikçe kiosk ekranı adım adım değişir |
| `ozellik_kartlari` | İkon + başlık + metin; 2/3/4 sütun; hover efektleri |
| `vurgu_bandi` | Slogan/alıntı (ör. "Satış iklimini e-isa hazırlar…") |
| `kazanc_hesaplayici` | Kaydırıcı ile günlük etkileşim → potansiyel satış/ciro; katsayılar ve "garanti değildir" notu blok verisinde |
| `sayaclar` | Animasyonlu istatistik sayaçları |
| `surec_adimlari` | Genel adım/timeline (ör. sponsorluk başvuru süreci) |
| `gorsel_metin` | Görsel + metin (sol/sağ), parallax |
| `logo_bandi` | Sponsor/partner logoları, kayan marquee |
| `sss` | Accordion + FAQPage JSON-LD |
| `cta_banner` | Güçlü çağrı bandı (ör. Ücretsiz Pilot) |
| `basvuru_formu` | Tip parametreli (pilot/sponsor/genel), KVKK onaylı |
| `blog_son_yazilar` | Son N yazı kartı |
| `ekip` | Hakkımızda için kişi kartları |
| `zengin_metin` | KVKK, çerez politikası, serbest metin |

### 5.4 Tasarım ve Animasyon İlkeleri
- **Tokenlar** (brief'ten): `#ED1C24` primary, `#0B0F14` dark, `#1F2933` ink, `#65736F` muted, `#3F514D` brand-deep, `#F8FAF9` bg. Fontlar: Space Grotesk (başlık), Inter (gövde), self-host.
- **Koyu hero → açık gövde** geçişi yumuşak gradyanla yapılır. Kırmızı her iki zeminde vurgu rengi olarak kullanılır.
- **Kiosk mockup** HTML/SVG tabanlıdır, ağır 3D yoktur. Ekranda döngüsel olarak soru → kategori → QR → eczacı onayı akışı oynar.
- Mikro etkileşimler: mıknatıs etkili CTA, kart tilt/hover, scroll reveal, header'ın scroll'da daralması, sayfa geçişleri.
- **`prefers-reduced-motion`**: tüm büyük animasyonlar statik alternatife düşer.
- **Performans bütçesi:** LCP < 2.5 sn (mobil 4G), CLS < 0.1, anasayfa JS < ~200 KB gz, Lighthouse ≥ 90 (Performance / SEO / A11y). Animasyonlar yalnızca client-component adacıklarında çalışır.
- İçerik tonu brief'teki hassasiyetleri korur: teşhis/tedavi vaadi yok, kazanç "örnek senaryo"dur, kontrol eczacıdadır.

### 5.5 SEO, KVKK, Analitik
- Sayfa bazlı `generateMetadata`, canonical, `sitemap.xml`, `robots.txt`, dinamik OG görselleri
- JSON-LD: Organization, SoftwareApplication/Product, FAQPage, BlogPosting, BreadcrumbList
- `www` → apex (veya tersi) tek yönlü 301
- Çerez onay bandı. Analitik yalnızca onaydan sonra yüklenir
- Form: KVKK aydınlatma linki + açık onay checkbox; onay metni versiyonu kayda yazılır

---

## 6. Deploy

- `web_site/Dockerfile`: Node 22 alpine, standalone çıktı, non-root, port 3000.
- `deploy/` altına `eisa-site` manifesti. Mevcut `eisa-site-production.yaml` mantığı korunur (2 replika, rolling update, probe'lar, Traefik + cert-manager, `eisa.com.tr` / `www.eisa.com.tr`). Değişenler: nginx yerine Node, `API_INTERNAL_URL`, `REVALIDATE_SECRET`, `PREVIEW_SECRET` env'leri.
- ISR önbelleği pod başınadır. 2 replikada revalidate webhook'u **service'e değil, her pod'a** ulaşmalı ya da paylaşımlı cache handler kullanılmalıdır. v1 önerisi: backend, `eisa-site` headless service üzerinden pod IP'lerine fan-out yapar. Alternatif olarak kısa zaman bazlı revalidate yeterli görülebilir.
- API tarafı: `eisa-app-config` / `eisa-app-secrets` içine `SITE_INTERNAL_URL`, `REVALIDATE_SECRET`, `EMAIL_*` eklenir.
- **Geçiş (cutover):** Yeni site staging host'ta (ör. `yeni.eisa.com.tr` veya port-forward) doğrulanır. Ardından mevcut `eisa-site` deployment'ının image/manifesti yenisiyle değiştirilir; DNS değişmez. Rollback = `kubectl rollout undo`.

---

## 7. Fazlar

| Faz | İçerik | Bitti tanımı |
|-----|--------|--------------|
| **0. Hazırlık** | `web_site/` iskeleti, tasarım tokenları, `dev:all`'a site eklenmesi, eski reponun arşiv notu | `npm run dev` ile boş layout API'den menü çekiyor |
| **1. Backend** | `apps/website` modelleri, blok registry, public/preview/admin API, `editor` rolü, media prefix, SMTP + scheduler job, revalidate webhook, `website_seed`, testler | Swagger'da uçlar hazır, testler yeşil, seed ile mevcut içerik DB'de |
| **2. Portal** | Web Sitesi modülü: Sayfalar + blok editörü, Menüler, Medya, Blog, Başvurular, Ayarlar; editor rolü yönlendirmesi | Editör kullanıcı portaldan sayfa düzenleyip önizleyebiliyor |
| **3. Site** | Layout, blok bileşenleri, hero/kiosk mockup, scroll hikâye, hesaplayıcı, blog, form, önizleme, revalidate | Yayınla → site saniyeler içinde güncel; tüm v1 sayfaları çalışıyor |
| **4. Yayına alma** | İçerik gözden geçirme, SEO/JSON-LD, KVKK metinleri, Lighthouse/a11y turu, staging, cutover, eski repo arşivi | eisa.com.tr yeni sistemde, bütçe hedefleri sağlanmış |

Faz 1 ile Faz 3'ün iskelet kısmı paralel ilerleyebilir; blok şemaları netleştikçe ikisi birlikte olgunlaşır.

---

## 8. Açık Konular (Bilgi / Karar Gerekli)

1. **SMTP bilgileri** (host, port, kullanıcı, gönderen adresi) ve bildirim alıcıları
2. **Kiosk'un gerçek fotoğrafı / render'ı** ve kiosk UI ekran görüntüleri (hero mockup için)
3. **Analitik tercihi**: KVKK açısından self-hosted Plausible/Umami önerilir; GA4 de olabilir
4. **Spam koruması**: domain Cloudflare'daysa Turnstile, değilse honeypot + throttle ile başlanır
5. **KVKK aydınlatma ve çerez metinleri** (hukuk onaylı)
6. **Hakkımızda / ekip içerikleri** ve blog için ilk 2-3 yazı
7. **Kazanç hesaplayıcı katsayıları**: mevcut tablodan türetilir, onay gerekir
8. Staging host adı (ör. `yeni.eisa.com.tr`)