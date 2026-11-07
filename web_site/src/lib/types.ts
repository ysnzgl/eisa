/**
 * e-isa site — ortak tipler.
 *
 * BAĞLAYICI KAYNAK: docs/web-sitesi/CONTRACT.md. Alan adları birebir oradaki gibidir;
 * burada bir alan değişecekse önce CONTRACT güncellenir.
 */

/* ------------------------------------------------------------------ */
/* §2 Ortak tipler                                                     */
/* ------------------------------------------------------------------ */

/** Medya referansı. `yol` her zaman `/api/media/website/...` ile başlayan göreli yoldur. */
export interface MediaRef {
  id: number;
  yol: string;
  alt: string;
  genislik: number | null;
  yukseklik: number | null;
  mime: string;
}

export type ButonStil = "birincil" | "ikincil" | "hayalet";

/** `href`: `/` ile başlayan iç yol, `#anchor`, `https://`, `mailto:`, `tel:` veya `https://wa.me/...` */
export interface Buton {
  etiket: string;
  href: string;
  stil: ButonStil;
}

/** CONTRACT §2'deki izinli Phosphor ikon adları (backend `secim` seçenekleri ile birebir). */
export const IKON_ADLARI = [
  "Sparkle",
  "Brain",
  "ShieldCheck",
  "Package",
  "ClockCounterClockwise",
  "Timer",
  "CheckCircle",
  "UserCircle",
  "Users",
  "Storefront",
  "QrCode",
  "Receipt",
  "ChartLineUp",
  "TrendUp",
  "Coins",
  "CurrencyCircleDollar",
  "Devices",
  "DeviceMobile",
  "Monitor",
  "Cloud",
  "CloudArrowUp",
  "WifiSlash",
  "Lightning",
  "Heart",
  "Heartbeat",
  "FirstAidKit",
  "Pill",
  "Flask",
  "Leaf",
  "Moon",
  "Lock",
  "Handshake",
  "Target",
  "Megaphone",
  "Lightbulb",
  "Rocket",
  "Gear",
  "Cpu",
  "Eye",
  "ChatCircleText",
  "Envelope",
  "Phone",
  "MapPin",
  "Star",
  "Medal",
  "ArrowsClockwise",
  "Plant",
  "Smiley",
] as const;

export type IkonAdi = (typeof IKON_ADLARI)[number];

/**
 * API'den gelen ikon alanı. Backend yalnızca izinli adları kabul eder; yine de site
 * bilinmeyen bir ad gelirse `Sparkle` gösterir (bkz. components/ui/Icon.tsx).
 */
export type Ikon = IkonAdi | (string & {});

/** Blok arka planı. Varsayılan `acik`. */
export type ArkaPlan = "acik" | "gri" | "koyu";

/* ------------------------------------------------------------------ */
/* §3 Public API — site                                                */
/* ------------------------------------------------------------------ */

export type SosyalPlatform = "linkedin" | "instagram" | "x" | "youtube" | "facebook";

export interface SosyalLink {
  platform: SosyalPlatform;
  url: string;
}

export interface SiteAyarlari {
  site_adi: string;
  seo_baslik_sablonu: string;
  seo_aciklama: string;
  og_gorsel: MediaRef | null;
  eposta: string;
  telefon: string;
  whatsapp: string;
  adres: string;
  firma_unvani: string;
  footer_aciklama: string;
  sosyal_linkler: SosyalLink[];
}

export interface MenuItem {
  id: number;
  etiket: string;
  /** Backend tarafından çözülmüş href (`/`, `/slug`, `/#anchor`, `/slug#anchor`, `/blog`, dış URL). */
  href: string;
  yeni_sekme: boolean;
  cta: boolean;
  /** Alt menü yalnızca 1 seviye derinliktedir. */
  cocuklar: MenuItem[];
}

export interface Menuler {
  header: MenuItem[];
  footer: MenuItem[];
  footer_alt: MenuItem[];
}

/** `GET /api/website/public/site/` */
export interface SiteData {
  ayarlar: SiteAyarlari;
  menuler: Menuler;
}

/** `GET /api/website/public/sayfalar/` (sitemap için) */
export interface SayfaListeOgesi {
  slug: string;
  guncellenme: string;
}

export interface SeoVeri {
  baslik: string;
  aciklama: string;
  og_gorsel: MediaRef | null;
}

/* ------------------------------------------------------------------ */
/* §8 Blok kataloğu — `veri` şemaları                                  */
/* ------------------------------------------------------------------ */

export interface VurguKarti {
  ikon: Ikon;
  metin: string;
}

/** `hero` — Hero (Anasayfa) */
export interface HeroVeri {
  rozet?: string;
  baslik: string;
  /** `baslik` içinde kırmızı vurgulanacak alt-metin. */
  vurgu?: string;
  alt_metin?: string;
  /** 0-6 */
  vurgu_kartlari: VurguKarti[];
  /** 0-3 */
  butonlar: Buton[];
  /** Varsayılan true */
  kiosk_animasyonu: boolean;
}

/** `sayfa_basligi` — Sayfa Başlığı (iç sayfalar) */
export interface SayfaBasligiVeri {
  rozet?: string;
  baslik: string;
  vurgu?: string;
  alt_metin?: string;
  /** 0-2 */
  butonlar: Buton[];
}

export interface OzellikKarti {
  ikon: Ikon;
  baslik: string;
  metin: string;
}

/** `ozellik_kartlari` — Özellik Kartları */
export interface OzellikKartlariVeri {
  ust_baslik?: string;
  baslik?: string;
  aciklama?: string;
  /** API `secim` olarak string döndürebilir ("3"); bileşen `Number()` ile okumalı. */
  sutun: 2 | 3 | 4 | "2" | "3" | "4";
  /** 1-12 */
  kartlar: OzellikKarti[];
  arka_plan: ArkaPlan;
}

/** `vurgu_bandi` — Vurgu Bandı */
export interface VurguBandiVeri {
  ikon: Ikon;
  baslik: string;
  metin?: string;
  vurgu_cumlesi?: string;
  stil: "kirmizi" | "koyu" | "acik";
}

export interface ScrollHikayeAdimi {
  baslik: string;
  metin: string;
  ekran_baslik: string;
  ekran_metin: string;
}

/** `scroll_hikaye` — Scroll Hikâye (Kiosk) */
export interface ScrollHikayeVeri {
  ust_baslik?: string;
  baslik: string;
  aciklama?: string;
  /** 2-6 */
  adimlar: ScrollHikayeAdimi[];
}

export interface SurecAdimi {
  baslik: string;
  metin: string;
}

/** `surec_adimlari` — Süreç Adımları */
export interface SurecAdimlariVeri {
  ust_baslik?: string;
  baslik: string;
  aciklama?: string;
  /** 2-8 */
  adimlar: SurecAdimi[];
  arka_plan: ArkaPlan;
}

/** `gorsel_metin` — Görsel + Metin */
export interface GorselMetinVeri {
  ust_baslik?: string;
  baslik: string;
  /** uzun_metin: çift satır sonu paragraf ayırır. */
  metin: string;
  /** 0-8 */
  maddeler: VurguKarti[];
  /** Boşsa site dekoratif kiosk/teknoloji illüstrasyonu çizer. */
  gorsel: MediaRef | null;
  gorsel_konumu: "sol" | "sag";
  /** 0-2 */
  butonlar: Buton[];
  arka_plan: ArkaPlan;
}

export interface KazancKademesi {
  etkilesim_min: number;
  etkilesim_max: number;
  gunluk_satis: number;
  aylik_satis: number;
  aylik_ciro: number;
  aylik_kar: number;
}

/** `kazanc_hesaplayici` — Kazanç Hesaplayıcı */
export interface KazancHesaplayiciVeri {
  ust_baslik?: string;
  baslik: string;
  aciklama?: string;
  /** 1-10 */
  kademeler: KazancKademesi[];
  varsayilan_etkilesim: number;
  slider_max: number;
  /** Varsayılan "TL" */
  para_birimi: string;
  uyari_notu: string;
  tablo_goster: boolean;
}

export interface SayacOgesi {
  deger: number;
  onek?: string;
  sonek?: string;
  etiket: string;
}

/** `sayaclar` — Sayaçlar */
export interface SayaclarVeri {
  baslik?: string;
  /** 1-6 */
  ogeler: SayacOgesi[];
  arka_plan: ArkaPlan;
}

export interface LogoOgesi {
  gorsel: MediaRef;
  ad: string;
  url?: string;
}

/** `logo_bandi` — Logo Bandı */
export interface LogoBandiVeri {
  baslik?: string;
  /** 0-30 */
  logolar: LogoOgesi[];
  bos_mesaj?: string;
}

export interface SssSorusu {
  soru: string;
  /** uzun_metin */
  cevap: string;
}

/** `sss` — SSS */
export interface SssVeri {
  ust_baslik?: string;
  baslik: string;
  aciklama?: string;
  /** 1-30 */
  sorular: SssSorusu[];
  arka_plan: ArkaPlan;
}

/** `cta_banner` — CTA Bandı */
export interface CtaBannerVeri {
  rozet?: string;
  baslik: string;
  metin?: string;
  /** 1-2 */
  butonlar: Buton[];
  stil: "koyu" | "kirmizi";
}

export type BasvuruTipi = "pilot" | "sponsor" | "genel";

/** `basvuru_formu` — Başvuru Formu */
export interface BasvuruFormuVeri {
  ust_baslik?: string;
  baslik: string;
  aciklama?: string;
  form_tipi: BasvuruTipi;
  /** 0-6 */
  maddeler: OzellikKarti[];
  basari_mesaji: string;
  /** Varsayılan "kvkk" */
  kvkk_sayfa_slug: string;
  iletisim_bilgisi_goster: boolean;
}

/** `blog_son_yazilar` — Son Blog Yazıları */
export interface BlogSonYazilarVeri {
  baslik?: string;
  aciklama?: string;
  /** 1-6, varsayılan 3 */
  adet: number;
  kategori_slug?: string;
}

export interface EkipKisisi {
  ad_soyad: string;
  unvan: string;
  biyografi?: string;
  foto: MediaRef | null;
  linkedin?: string;
}

/** `ekip` — Ekip */
export interface EkipVeri {
  ust_baslik?: string;
  baslik: string;
  aciklama?: string;
  /** 1-24 */
  kisiler: EkipKisisi[];
}

/** `zengin_metin` — Zengin Metin */
export interface ZenginMetinVeri {
  baslik?: string;
  /** Backend'de nh3 ile sanitize edilmiş HTML. */
  icerik_html: string;
  genislik: "dar" | "genis";
  /** Serbest metin, ör. "7 Kasım 2026" */
  son_guncelleme?: string;
}

/** Tip → veri arayüzü haritası. Yeni blok tipi eklenirken önce buraya eklenir. */
export interface BlokVeriHaritasi {
  hero: HeroVeri;
  sayfa_basligi: SayfaBasligiVeri;
  ozellik_kartlari: OzellikKartlariVeri;
  vurgu_bandi: VurguBandiVeri;
  scroll_hikaye: ScrollHikayeVeri;
  surec_adimlari: SurecAdimlariVeri;
  gorsel_metin: GorselMetinVeri;
  kazanc_hesaplayici: KazancHesaplayiciVeri;
  sayaclar: SayaclarVeri;
  logo_bandi: LogoBandiVeri;
  sss: SssVeri;
  cta_banner: CtaBannerVeri;
  basvuru_formu: BasvuruFormuVeri;
  blog_son_yazilar: BlogSonYazilarVeri;
  ekip: EkipVeri;
  zengin_metin: ZenginMetinVeri;
}

export type BlokTipi = keyof BlokVeriHaritasi;

export const BLOK_TIPLERI: readonly BlokTipi[] = [
  "hero",
  "sayfa_basligi",
  "ozellik_kartlari",
  "vurgu_bandi",
  "scroll_hikaye",
  "surec_adimlari",
  "gorsel_metin",
  "kazanc_hesaplayici",
  "sayaclar",
  "logo_bandi",
  "sss",
  "cta_banner",
  "basvuru_formu",
  "blog_son_yazilar",
  "ekip",
  "zengin_metin",
] as const;

/** Tek bir blok tipinin API biçimi. */
export interface BlokTemel<T extends BlokTipi> {
  /** Kalıcı string anahtar, ör. "b_42". */
  id: string;
  tip: T;
  /** Boş string olabilir. */
  anchor_id: string;
  veri: BlokVeriHaritasi[T];
}

/** Discriminated union: `blok.tip` ile daraltılır. */
export type Blok = { [T in BlokTipi]: BlokTemel<T> }[BlokTipi];

/** API'den gelen ama sitenin henüz tanımadığı blok (BlockRenderer atlar). */
export interface BilinmeyenBlok {
  id: string;
  tip: string;
  anchor_id: string;
  veri: Record<string, unknown>;
}

/* ------------------------------------------------------------------ */
/* §3 Sayfa                                                            */
/* ------------------------------------------------------------------ */

/** `GET /api/website/public/sayfalar/<slug>/` (preview ucu da aynı biçim) */
export interface PageData {
  slug: string;
  baslik: string;
  seo: SeoVeri;
  yayin_tarihi: string | null;
  revizyon_id: number | null;
  bloklar: Array<Blok | BilinmeyenBlok>;
}

/* ------------------------------------------------------------------ */
/* §3 Blog                                                             */
/* ------------------------------------------------------------------ */

export interface BlogKategori {
  ad: string;
  slug: string;
}

export interface BlogOzet {
  slug: string;
  baslik: string;
  ozet: string;
  kapak: MediaRef | null;
  kategori: BlogKategori | null;
  etiketler: string[];
  yazar_adi: string;
  yayin_tarihi: string;
  /** Dakika, tam sayı. */
  okuma_suresi: number;
}

/** `GET /api/website/public/blog/<slug>/` */
export interface BlogDetay extends BlogOzet {
  icerik_html: string;
  seo: SeoVeri;
  /** Aynı kategoriden en fazla 3 yazı. */
  ilgili: BlogOzet[];
}

/** `GET /api/website/public/blog/?kategori=&sayfa=&boyut=` */
export interface BlogListe {
  sonuclar: BlogOzet[];
  toplam: number;
  sayfa: number;
  sayfa_sayisi: number;
  kategoriler: BlogKategori[];
}

/* ------------------------------------------------------------------ */
/* §3 Başvuru                                                          */
/* ------------------------------------------------------------------ */

/** `POST /api/website/public/basvurular/` gövdesi */
export interface BasvuruIstegi {
  tip: BasvuruTipi;
  ad_soyad: string;
  kurum: string;
  eposta: string;
  telefon: string;
  il: string;
  mesaj: string;
  kvkk_onay: boolean;
  kaynak_sayfa: string;
  /** Honeypot — gerçek kullanıcı için her zaman boş. */
  website: string;
}

/** Başvuru server action sonucu (src/app/actions/basvuru.ts). */
export interface BasvuruSonucu {
  ok: boolean;
  /** Alan bazlı hatalar: `{ eposta: ["Geçerli bir e-posta girin."] }` */
  hatalar: Record<string, string[]>;
  /** Genel kullanıcı mesajı (başarı veya hata). */
  mesaj: string;
}
