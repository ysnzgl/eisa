/**
 * MOCK: `GET /api/website/public/site/` — CONTRACT §9 seed ayarları ve menüleri.
 * Backend kapalıyken `getSite()` için yedek (fallback) olarak da kullanılır.
 */

import type { SiteData } from "../types";

export const mockSite: SiteData = {
  ayarlar: {
    site_adi: "e-isa",
    seo_baslik_sablonu: "%s | e-isa",
    seo_aciklama:
      "e-isa, eczanelerde reçete bekleme süresini yapay zeka destekli sağlık okuryazarlığı ve eczacı kontrollü danışmanlık deneyimine dönüştüren modern kiosk ekosistemidir.",
    og_gorsel: null,
    eposta: "iletisim@eisa.com.tr",
    telefon: "",
    whatsapp: "",
    adres: "",
    firma_unvani: "Eisa Bilişim Teknolojileri A.Ş.",
    footer_aciklama:
      "e-isa; eczanedeki bekleme süresini kategori bazlı sağlık okuryazarlığına dönüştüren, eczacının kontrolünü merkeze alan dijital ön hazırlık asistanıdır. Tıbbi teşhis veya tedavi sistemi değildir; son değerlendirme her zaman eczacıdadır.",
    sosyal_linkler: [
      { platform: "linkedin", url: "https://www.linkedin.com/company/e-isa" },
      { platform: "instagram", url: "https://www.instagram.com/eisa.tr/" },
    ],
  },
  menuler: {
    header: [
      {
        id: 1,
        etiket: "Çözüm",
        href: "/#nasil-calisir",
        yeni_sekme: false,
        cta: false,
        cocuklar: [
          { id: 2, etiket: "Nasıl Çalışır?", href: "/#nasil-calisir", yeni_sekme: false, cta: false, cocuklar: [] },
          { id: 3, etiket: "Eczacı Kontrolü", href: "/#eczaci-kontrolu", yeni_sekme: false, cta: false, cocuklar: [] },
          { id: 4, etiket: "Müşteri Yolculuğu", href: "/#yolculuk", yeni_sekme: false, cta: false, cocuklar: [] },
          { id: 5, etiket: "Kazanç Modeli", href: "/#kazanc", yeni_sekme: false, cta: false, cocuklar: [] },
          { id: 6, etiket: "SSS", href: "/#sss", yeni_sekme: false, cta: false, cocuklar: [] },
        ],
      },
      { id: 7, etiket: "Teknoloji", href: "/teknoloji", yeni_sekme: false, cta: false, cocuklar: [] },
      { id: 8, etiket: "Sponsorlar", href: "/sponsorlar", yeni_sekme: false, cta: false, cocuklar: [] },
      { id: 9, etiket: "Blog", href: "/blog", yeni_sekme: false, cta: false, cocuklar: [] },
      {
        id: 10,
        etiket: "Kurumsal",
        href: "/hakkimizda",
        yeni_sekme: false,
        cta: false,
        cocuklar: [
          { id: 11, etiket: "Hakkımızda", href: "/hakkimizda", yeni_sekme: false, cta: false, cocuklar: [] },
          { id: 12, etiket: "İletişim", href: "/iletisim", yeni_sekme: false, cta: false, cocuklar: [] },
        ],
      },
      { id: 13, etiket: "Ücretsiz Pilot", href: "/#pilot", yeni_sekme: false, cta: true, cocuklar: [] },
    ],
    footer: [
      {
        id: 20,
        etiket: "Ürün",
        href: "/",
        yeni_sekme: false,
        cta: false,
        cocuklar: [
          { id: 21, etiket: "Nasıl Çalışır?", href: "/#nasil-calisir", yeni_sekme: false, cta: false, cocuklar: [] },
          { id: 22, etiket: "Teknoloji", href: "/teknoloji", yeni_sekme: false, cta: false, cocuklar: [] },
          { id: 23, etiket: "Kazanç Modeli", href: "/#kazanc", yeni_sekme: false, cta: false, cocuklar: [] },
          { id: 24, etiket: "SSS", href: "/#sss", yeni_sekme: false, cta: false, cocuklar: [] },
        ],
      },
      {
        id: 25,
        etiket: "Kurumsal",
        href: "/hakkimizda",
        yeni_sekme: false,
        cta: false,
        cocuklar: [
          { id: 26, etiket: "Hakkımızda", href: "/hakkimizda", yeni_sekme: false, cta: false, cocuklar: [] },
          { id: 27, etiket: "Sponsorlar", href: "/sponsorlar", yeni_sekme: false, cta: false, cocuklar: [] },
          { id: 28, etiket: "Blog", href: "/blog", yeni_sekme: false, cta: false, cocuklar: [] },
          { id: 29, etiket: "İletişim", href: "/iletisim", yeni_sekme: false, cta: false, cocuklar: [] },
        ],
      },
    ],
    footer_alt: [
      { id: 30, etiket: "KVKK Aydınlatma Metni", href: "/kvkk", yeni_sekme: false, cta: false, cocuklar: [] },
      { id: 31, etiket: "Çerez Politikası", href: "/cerez-politikasi", yeni_sekme: false, cta: false, cocuklar: [] },
    ],
  },
};
