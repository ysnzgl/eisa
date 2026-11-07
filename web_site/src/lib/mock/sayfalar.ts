/**
 * MOCK: `GET /api/website/public/sayfalar/<slug>/` — CONTRACT §9 seed planına göre.
 * 16 blok tipinin her biri en az bir sayfada geçer (blok ajanları bu fixture'larla geliştirir).
 *
 * İçerik tonu: e-isa teşhis/tedavi sistemi değildir; marka değil kategori önerir;
 * kazanç rakamları örnek senaryodur; son değerlendirme eczacıdadır.
 */

import type { Blok, BlokTipi, BlokVeriHaritasi, PageData } from "../types";

const YAYIN = "2026-11-07T10:00:00Z";

function blok<T extends BlokTipi>(
  id: string,
  tip: T,
  anchor_id: string,
  veri: BlokVeriHaritasi[T],
): Blok {
  return { id, tip, anchor_id, veri } as Blok;
}

/* ------------------------------------------------------------------ */
/* anasayfa                                                            */
/* ------------------------------------------------------------------ */

const anasayfa: PageData = {
  slug: "anasayfa",
  baslik: "Anasayfa",
  seo: {
    baslik: "Eczaneler için Yapay Zeka Destekli Karar Destek Ekosistemi",
    aciklama:
      "e-isa, eczanelerde reçete bekleme süresini yapay zeka destekli sağlık okuryazarlığı ve eczacı kontrollü danışmanlık deneyimine dönüştüren modern kiosk ekosistemidir.",
    og_gorsel: null,
  },
  yayin_tarihi: YAYIN,
  revizyon_id: 1,
  bloklar: [
    blok("b_1", "hero", "", {
      rozet: "Eczacının Ön Hazırlık Asistanı",
      baslik: "Eczanenizdeki Reçete Bekleme Süresini Kategori Bazlı Sağlık Okuryazarlığına Dönüştürün",
      vurgu: "Sağlık Okuryazarlığına Dönüştürün",
      alt_metin:
        "e-isa, yaşam tarzına ve beyan edilen ihtiyaçlara uygun kategorik sağlık okuryazarlığı rehberliği sunar; eczacının ön hazırlık rolünü merkeze alan güvenli bir dijital deneyim sağlar.",
      vurgu_kartlari: [
        { ikon: "ClockCounterClockwise", metin: "60 saniyede kategorik ön hazırlık" },
        { ikon: "Package", metin: "Marka değil, ihtiyaç kategorisi önerir" },
        { ikon: "ShieldCheck", metin: "Son değerlendirme eczacı kontrolündedir" },
        { ikon: "CheckCircle", metin: "1 ay ücretsiz pilot süreç" },
      ],
      butonlar: [
        { etiket: "Pilot Süreci İncele", href: "/#pilot", stil: "birincil" },
        { etiket: "Nasıl Çalışır?", href: "/#nasil-calisir", stil: "ikincil" },
      ],
      kiosk_animasyonu: true,
    }),
    blok("b_2", "ozellik_kartlari", "nasil-calisir", {
      ust_baslik: "e-isa nedir?",
      baslik: "Eczacının Ön Hazırlık Asistanı",
      aciklama:
        "e-isa; eczane içinde bekleyen kişinin yaşam kalitesini etkileyebilecek yorgunluk, stres, sindirim düzeni, bağışıklık desteği, enerji ve uyku gibi başlıklarda kısa ve sade bir dijital etkileşim yaşamasını sağlar.",
      sutun: 4,
      kartlar: [
        {
          ikon: "Brain",
          baslik: "Kısa Dijital Etkileşim",
          metin: "Yalın sorularla kişiyi karmaşık tıbbi terimlerle yormadan ihtiyacını düşünmeye yönlendirir.",
        },
        {
          ikon: "Package",
          baslik: "Kategori Bazlı Öneri",
          metin: "Verilen yanıtları kategori mantığıyla değerlendirir ve eczacıya ön inceleme olarak sunar.",
        },
        {
          ikon: "ShieldCheck",
          baslik: "Eczacı Onayı",
          metin: "Sistemin ürettiği ön inceleme eczacının mesleki onayına sunulur; son değerlendirme eczacıdadır.",
        },
        {
          ikon: "QrCode",
          baslik: "QR / Fiş Aktarımı",
          metin: "Dijital sonuç QR kod veya fiş ile hızlıca eczacıya iletilir.",
        },
      ],
      arka_plan: "gri",
    }),
    blok("b_3", "vurgu_bandi", "", {
      ikon: "Sparkle",
      baslik: "Ön Hazırlıktan Sonra Farkındalık: Dürtme (Nudge) Yaklaşımı",
      metin:
        "e-isa, davranışsal ekonomiden ilham alan dürtme (nudge) yaklaşımını sağlık okuryazarlığı alanına taşır. Kişiyi karmaşık tıbbi terimlerle yormadan yalın seçenekler üzerinden sağlık ihtiyacını düşünmeye yönlendirir. Bekleme süresinde oluşan bu kısa dijital deneyim, eczacıyla daha bilinçli ve odaklı bir görüşme yapılmasına yardımcı olur.",
      vurgu_cumlesi: "Ön hazırlık iklimini e-isa hazırlar, profesyonel son dokunuşu eczacı yapar.",
      stil: "kirmizi",
    }),
    blok("b_4", "ozellik_kartlari", "eczaci-kontrolu", {
      ust_baslik: "Eczacı için 3 öncelik",
      baslik: "Kontrol Her Zaman Sizde",
      aciklama: "e-isa bir satış terminali değil; eczacının uzmanlığını destekleyen bir ön hazırlık katmanıdır.",
      sutun: 3,
      kartlar: [
        {
          ikon: "Package",
          baslik: "Asla Marka Önermez",
          metin:
            "e-isa, spesifik marka dayatmaz. Yalnızca ihtiyaca yönelik kategori önerir. Hangi ürünün kişiye daha uygun olduğuna karar veren yetkili her zaman eczacıdır.",
        },
        {
          ikon: "UserCircle",
          baslik: "Süreci Eczacı Tamamlar",
          metin:
            "Kiosk bir satış terminali değil, kişiyi görüşmeye hazırlayan dijital bir köprüdür. Son karar, banko başında eczacının uzmanlığıyla verilir.",
        },
        {
          ikon: "CheckCircle",
          baslik: "Stokla Uyumlu Çalışır",
          metin:
            "Sistem, eczanenin mevcut ürün portföyünü destekleyecek rasyonel kategori argümanları üretir. Böylece stok yönetimi ve danışmanlık daha verimli hale gelebilir.",
        },
      ],
      arka_plan: "acik",
    }),
    blok("b_5", "scroll_hikaye", "yolculuk", {
      ust_baslik: "Müşterinin eczane içi yolculuğu",
      baslik: "Beklemeden Etkileşime: 4 Adımlı Yolculuk",
      aciklama: "Reçete teslim edildiği andan eczacıyla görüşmeye kadar geçen süre, kısa ve anlamlı bir hazırlığa dönüşür.",
      adimlar: [
        {
          baslik: "Reçete Teslimi",
          metin: "Reçete teslim edilir ve bekleme süresi başlar.",
          ekran_baslik: "Hoş geldiniz",
          ekran_metin: "Beklerken kısa bir sağlık okuryazarlığı turuna ne dersiniz?",
        },
        {
          baslik: "Dijital Etkileşim",
          metin: "Müşteri e-isa ekranındaki sade arayüzle etkileşime girer.",
          ekran_baslik: "Son zamanlarda en çok neye dikkat ediyorsunuz?",
          ekran_metin: "Enerji · Uyku · Sindirim · Bağışıklık",
        },
        {
          baslik: "Kategori Önerisi",
          metin: "2-4 kısa soruyla kişiselleştirilmiş bir kategori önerisi oluşturulur.",
          ekran_baslik: "Önerilen kategori",
          ekran_metin: "Enerji ve yorgunluk desteği — marka değil, ihtiyaç kategorisi.",
        },
        {
          baslik: "Eczacı Onayı",
          metin: "QR/fiş eczacıya iletilir; eczacı öneriyi uzmanlığıyla değerlendirir.",
          ekran_baslik: "QR kodunuz hazır",
          ekran_metin: "Son değerlendirme eczacınızdadır.",
        },
      ],
    }),
    blok("b_6", "kazanc_hesaplayici", "kazanc", {
      ust_baslik: "Kazanç modeli",
      baslik: "Sepet Büyüten Zeka: Cross-Sell Etkisi",
      aciklama:
        "e-isa, müşterinin yanıtlarına göre yalnızca tek bir ürün kategorisine değil, tamamlayıcı kategori fırsatlarına da dikkat çeker. Bu yapı, eczacının danışmanlık gücünü artırırken sepet ortalamasını büyütme potansiyeli oluşturur.",
      kademeler: [
        { etkilesim_min: 1, etkilesim_max: 10, gunluk_satis: 1, aylik_satis: 25, aylik_ciro: 18000, aylik_kar: 6000 },
        { etkilesim_min: 10, etkilesim_max: 20, gunluk_satis: 3, aylik_satis: 75, aylik_ciro: 56000, aylik_kar: 18000 },
        { etkilesim_min: 20, etkilesim_max: 30, gunluk_satis: 6, aylik_satis: 150, aylik_ciro: 110000, aylik_kar: 36000 },
        { etkilesim_min: 30, etkilesim_max: 40, gunluk_satis: 10, aylik_satis: 250, aylik_ciro: 185000, aylik_kar: 62000 },
        { etkilesim_min: 40, etkilesim_max: 50, gunluk_satis: 15, aylik_satis: 375, aylik_ciro: 280000, aylik_kar: 94000 },
      ],
      varsayilan_etkilesim: 25,
      slider_max: 50,
      para_birimi: "TL",
      uyari_notu:
        "Bu değerler garanti değildir; örnek potansiyel senaryo olarak sunulmuştur. Gerçek sonuçlar eczanenin konumuna, müşteri profiline ve danışmanlık sürecine göre değişir.",
      tablo_goster: true,
    }),
    blok("b_7", "ozellik_kartlari", "", {
      ust_baslik: "Pasif gelir ekosistemi",
      baslik: "e-isa Kendi Kendini Finanse Eden Bir Ekosisteme Dönüşebilir",
      aciklama:
        "e-isa, kiosk ekranını eczane atmosferine uygun dijital bilgilendirme alanı olarak da değerlendirebilir. İçerik yönetimi ve teknik güncellemeler merkezi olarak yürütülür; eczane operasyonel yük almadan ek katkı potansiyeli elde eder.",
      sutun: 4,
      kartlar: [
        {
          ikon: "Megaphone",
          baslik: "Dijital Bilgilendirme",
          metin: "Ekran, eczane atmosferine uygun bilgilendirici içerikler için paylaşımlı bir alan olarak kullanılabilir.",
        },
        {
          ikon: "Coins",
          baslik: "%10 Altyapı Katkısı",
          metin: "Bilgilendirme gelirlerinden altyapı ve lisans maliyetlerine destek olacak bir katkı modeli öngörülür.",
        },
        {
          ikon: "Lightning",
          baslik: "Operasyonel Yük Yok",
          metin: "İçerik planlama, yayın ve teknik güncellemeler merkezi olarak yönetilir.",
        },
        {
          ikon: "ShieldCheck",
          baslik: "Etik İçerik Denetimi",
          metin: "Yayınlanacak içerikler eczane etiğine ve sağlık beyanı kurallarına uygunluk açısından denetlenir.",
        },
      ],
      arka_plan: "gri",
    }),
    blok("b_8", "sss", "sss", {
      ust_baslik: "Sık sorulan sorular",
      baslik: "Merak Ettikleriniz",
      aciklama: "e-isa hakkında eczacıların en sık sorduğu soruları yanıtladık.",
      sorular: [
        {
          soru: "Kiosk iş yerime sığar mı?",
          cevap:
            "Samsung kiosk'un kompakt yapısı, standart bir dergilikten fazla alan kaplamadan eczane ortamına entegre olabilir.",
        },
        {
          soru: "Müşteriler kiosku kullanır mı?",
          cevap:
            "Yalın seçenekler, kısa etkileşim süresi ve dikkat çekici arayüz sayesinde müşterinin bekleme anında ekranla etkileşime girmesi hedeflenir.\n\nPilot süreçte etkileşim verilerini birlikte izleyerek eczanenize özgü tabloyu görebilirsiniz.",
        },
        {
          soru: "Biz zaten satış yapıyoruz, neden e-isa?",
          cevap:
            "e-isa, ihtiyacını dile getirmeyen sessiz müşteriyi farkındalık sürecine dahil eder ve eczacının danışmanlık sürecini destekler.",
        },
        {
          soru: "İçerikler eczacılık etiğine uygun mu?",
          cevap:
            "Yayınlanan içerikler, eczane atmosferine ve ilgili sağlık beyanı kurallarına uygunluk açısından denetlenir. e-isa teşhis koymaz, tedavi önermez ve marka yönlendirmesi yapmaz.",
        },
        {
          soru: "İnternet kesilirse ne olur?",
          cevap:
            "Sistem çevrimdışı senkronizasyon mantığıyla çalışır. Bağlantı kesintilerinde veriler cihazda tutulur ve bağlantı geldiğinde yeniden senkronize edilir.",
        },
      ],
      arka_plan: "acik",
    }),
    blok("b_9", "blog_son_yazilar", "", {
      baslik: "Blogdan Son Yazılar",
      aciklama: "Sağlık okuryazarlığı, eczane yönetimi ve e-isa'dan haberler.",
      adet: 3,
    }),
    blok("b_10", "basvuru_formu", "pilot", {
      ust_baslik: "1 ay ücretsiz",
      baslik: "Pilot Süreç: e-isa Konuşsun, Ön İnceleme Sizde Olsun",
      aciklama:
        "e-isa'yı varsayımlarla değil, eczanenizin kendi verileriyle değerlendirin. 30 günlük pilot süreçte etkileşimi, danışmanlık sürecini ve sepet ortalamasındaki değişimi birlikte gözlemleyelim.",
      form_tipi: "pilot",
      maddeler: [
        { ikon: "Storefront", baslik: "Kompakt Pilot Ünite", metin: "Pratik test için hazır kurulum." },
        { ikon: "Handshake", baslik: "Yakın Saha Desteği", metin: "Pilot süresince profesyonel destek." },
        { ikon: "Target", baslik: "Stratejik Danışmanlık", metin: "Kalıcı süreçte düzenli ziyaret ve değerlendirme." },
      ],
      basari_mesaji:
        "Teşekkürler! Pilot başvurunuz bize ulaştı. Ekibimiz en kısa sürede sizinle iletişime geçecek.",
      kvkk_sayfa_slug: "kvkk",
      iletisim_bilgisi_goster: false,
    }),
  ],
};

/* ------------------------------------------------------------------ */
/* teknoloji                                                           */
/* ------------------------------------------------------------------ */

const teknoloji: PageData = {
  slug: "teknoloji",
  baslik: "Teknoloji",
  seo: {
    baslik: "Teknoloji ve Kiosk",
    aciklama:
      "Samsung 24 inç kiosk, bulut tabanlı yönetim ve çevrimdışı senkronizasyon ile eczane atmosferine uyumlu e-isa deneyimi.",
    og_gorsel: null,
  },
  yayin_tarihi: YAYIN,
  revizyon_id: 1,
  bloklar: [
    blok("b_20", "sayfa_basligi", "", {
      rozet: "Teknoloji",
      baslik: "Eczane Atmosferine Uyumlu Modern Kiosk Deneyimi",
      vurgu: "Modern Kiosk Deneyimi",
      alt_metin:
        "Kompakt donanım, sade arayüz ve merkezi yönetilen yazılım: e-isa, eczanenize teknolojik bir dokunuş katarken operasyonel yük getirmez.",
      butonlar: [
        { etiket: "1 Ay Ücretsiz Pilot", href: "/#pilot", stil: "birincil" },
        { etiket: "Nasıl Çalışır?", href: "/#nasil-calisir", stil: "hayalet" },
      ],
    }),
    blok("b_21", "gorsel_metin", "", {
      ust_baslik: "Donanım",
      baslik: "Samsung 24\" Kiosk ile Kompakt ve Şık Kurulum",
      metin:
        "Samsung kiosk'un 24 inçlik kompakt gövdesi, eczane ortamına modern ve teknolojik bir dokunuş katar. Nötr gri-beyaz tonları ve e-isa logosunun kırmızı vurgusu, eczane mimarisiyle uyumlu, güven veren ve yenilikçi bir algı oluşturur.\n\nKurulum için standart bir dergilikten fazla alan gerekmez. Ekran içerikleri ve yazılım güncellemeleri uzaktan, merkezi olarak yönetilir.",
      maddeler: [
        { ikon: "Monitor", metin: "24 inç dokunmatik ekran" },
        { ikon: "Storefront", metin: "Dergilik kadar alan kaplar" },
        { ikon: "QrCode", metin: "QR / fiş ile dijital sonuç" },
        { ikon: "CloudArrowUp", metin: "Uzaktan içerik ve yazılım güncellemesi" },
      ],
      gorsel: null,
      gorsel_konumu: "sag",
      butonlar: [],
      arka_plan: "acik",
    }),
    blok("b_22", "ozellik_kartlari", "", {
      ust_baslik: "Öne çıkanlar",
      baslik: "Sade Donanım, Akıllı Yazılım",
      sutun: 4,
      kartlar: [
        { ikon: "Devices", baslik: "Kompakt Yapı", metin: "Eczanenin akışını bozmadan bekleme alanına yerleşir." },
        { ikon: "Smiley", baslik: "Modern Deneyim", metin: "Büyük dokunmatik ekranda sade ve anlaşılır bir arayüz." },
        { ikon: "QrCode", baslik: "QR / Dijital Sonuç", metin: "Kategori önerisi QR kod veya fiş ile eczacıya aktarılır." },
        {
          ikon: "ArrowsClockwise",
          baslik: "Bulut + Çevrimdışı Senkron",
          metin: "Bağlantı kesildiğinde çalışmaya devam eder, bağlantı gelince senkronize olur.",
        },
      ],
      arka_plan: "gri",
    }),
    blok("b_23", "sayaclar", "", {
      baslik: "Rakamlarla e-isa",
      ogeler: [
        { deger: 60, sonek: " sn", etiket: "Ortalama etkileşim süresi" },
        { deger: 4, onek: "2-", etiket: "Kısa soruyla kategori önerisi" },
        { deger: 24, sonek: " inç", etiket: "Dokunmatik kiosk ekranı" },
        { deger: 1, sonek: " ay", etiket: "Ücretsiz pilot süreç" },
      ],
      arka_plan: "koyu",
    }),
    blok("b_24", "surec_adimlari", "", {
      ust_baslik: "Kurulum",
      baslik: "Dört Adımda Eczanenizde",
      aciklama: "Pilot kararından canlı kullanıma kadar süreci sizin için yönetiyoruz.",
      adimlar: [
        { baslik: "Keşif", metin: "Eczanenizin bekleme alanını ve müşteri akışını birlikte değerlendiririz." },
        { baslik: "Kurulum", metin: "Kiosk'u en uygun konuma yerleştirir, bağlantı ve ayarları tamamlarız." },
        { baslik: "Eğitim", metin: "Eczane ekibine QR / fiş akışını ve panel kullanımını kısa bir eğitimle anlatırız." },
        { baslik: "İzleme", metin: "Pilot süresince etkileşim verilerini birlikte izler, düzenli geri bildirim paylaşırız." },
      ],
      arka_plan: "acik",
    }),
    blok("b_25", "cta_banner", "", {
      rozet: "1 ay ücretsiz",
      baslik: "e-isa'yı eczanenizde ücretsiz deneyin",
      metin: "Pilot süreçte veriler konuşsun, kararı siz verin.",
      butonlar: [
        { etiket: "Pilot Başvurusu", href: "/#pilot", stil: "birincil" },
        { etiket: "Bize Ulaşın", href: "/iletisim", stil: "ikincil" },
      ],
      stil: "koyu",
    }),
  ],
};

/* ------------------------------------------------------------------ */
/* sponsorlar                                                          */
/* ------------------------------------------------------------------ */

const sponsorlar: PageData = {
  slug: "sponsorlar",
  baslik: "Sponsorlar",
  seo: {
    baslik: "Sponsorluk ve Kurumsal İş Birliği",
    aciklama:
      "Markanızı, etik iletişim ilkelerine uygun olarak eczane noktasında konumlandırın. e-isa sponsorluk ve kurumsal iş birliği süreci.",
    og_gorsel: null,
  },
  yayin_tarihi: YAYIN,
  revizyon_id: 1,
  bloklar: [
    blok("b_30", "sayfa_basligi", "", {
      rozet: "Sponsorluk / Kurumsal İş Birliği",
      baslik: "Geleceğin Eczane Deneyiminde Kurumsal İş Ortağı Olun",
      vurgu: "Kurumsal İş Ortağı",
      alt_metin:
        "Markanızı, tüketicinin sağlık çözümüne en çok ihtiyaç duyduğu ve güven ortamında bulunduğu eczane noktasında, etik iletişim ilkelerine uygun olarak konumlandırın.",
      butonlar: [
        { etiket: "Sponsorluk Başvurusu", href: "#basvuru", stil: "birincil" },
        { etiket: "e-isa Nasıl Çalışır?", href: "/#nasil-calisir", stil: "hayalet" },
      ],
    }),
    blok("b_31", "ozellik_kartlari", "", {
      ust_baslik: "Değer önermesi",
      baslik: "Neden e-isa?",
      aciklama:
        "Eisa Bilişim Teknolojileri A.Ş. olarak geliştirdiğimiz e-isa dijital bilgilendirme ekosistemi, markaların etik iletişim ilkeleriyle doğru noktada konumlanmasını sağlayan yenilikçi bir platformdur.",
      sutun: 3,
      kartlar: [
        {
          ikon: "Sparkle",
          baslik: "Görünürlükten Fazlası",
          metin: "e-isa, markalara yalnızca görünürlük sunmaz; güven ortamında bilgilendirici bir temas noktası oluşturur.",
        },
        {
          ikon: "Storefront",
          baslik: "Seçkin Eczaneler",
          metin: "Yüksek hasta potansiyeline sahip, kurumsal hizmet anlayışıyla öne çıkan eczanelerle başlıyoruz.",
        },
        {
          ikon: "Handshake",
          baslik: "Sınırlı Ortaklık",
          metin: "Yalnızca sınırlı sayıda stratejik iş ortağı ile ilerliyoruz. İlk paydaşlar arasında yerinizi alın.",
        },
      ],
      arka_plan: "gri",
    }),
    blok("b_32", "surec_adimlari", "", {
      ust_baslik: "Süreç",
      baslik: "Sponsorluk Süreci",
      aciklama: "Dört adımda kurumsal iş birliği sürecimizi keşfedin.",
      adimlar: [
        { baslik: "Ön Değerlendirme", metin: "Başvurunuzun ardından ekibimiz, markanıza özel iş birliği çerçevesini paylaşır." },
        { baslik: "Kurumsal Sunum", metin: "Markanıza özel konumlandırma yaklaşımını hazırlar ve sunarız." },
        { baslik: "Etik Uyum Görüşmesi", metin: "Olası iş birliği fırsatlarını etik iletişim ilkeleriyle birlikte değerlendiririz." },
        { baslik: "Ekosisteme Dahil", metin: "Geleceğin eczane deneyiminde doğru temasın değerini birlikte oluştururuz." },
      ],
      arka_plan: "acik",
    }),
    blok("b_33", "logo_bandi", "", {
      baslik: "İş Ortaklarımız",
      logolar: [],
      bos_mesaj: "İlk iş ortaklarımızla görüşmelerimiz sürüyor. Bu alanda yerinizi almak için başvurun.",
    }),
    blok("b_34", "basvuru_formu", "basvuru", {
      ust_baslik: "İlk paydaşlar arasında olun",
      baslik: "Sponsorluk Başvurusu",
      aciklama:
        "Başvurunuzun ardından ekibimiz, markanıza özel hazırlanan iş birliği modelini paylaşır ve süreci başlatır.",
      form_tipi: "sponsor",
      maddeler: [],
      basari_mesaji: "Teşekkürler! Sponsorluk başvurunuz bize ulaştı. Ekibimiz en kısa sürede sizinle iletişime geçecek.",
      kvkk_sayfa_slug: "kvkk",
      iletisim_bilgisi_goster: false,
    }),
  ],
};

/* ------------------------------------------------------------------ */
/* hakkimizda                                                          */
/* ------------------------------------------------------------------ */

const hakkimizda: PageData = {
  slug: "hakkimizda",
  baslik: "Hakkımızda",
  seo: {
    baslik: "Hakkımızda",
    aciklama:
      "Eisa Bilişim Teknolojileri A.Ş., eczacıyı merkeze alan dijital sağlık okuryazarlığı çözümü e-isa'yı geliştirir.",
    og_gorsel: null,
  },
  yayin_tarihi: YAYIN,
  revizyon_id: 1,
  bloklar: [
    blok("b_40", "sayfa_basligi", "", {
      rozet: "Hakkımızda",
      baslik: "Eczacıyı Merkeze Alan Dijital Sağlık Okuryazarlığı",
      vurgu: "Dijital Sağlık Okuryazarlığı",
      alt_metin:
        "Eisa Bilişim Teknolojileri A.Ş. olarak eczane içindeki kısa bekleme anlarını, eczacının uzmanlığını destekleyen anlamlı bir hazırlığa dönüştürüyoruz.",
      butonlar: [],
    }),
    blok("b_41", "gorsel_metin", "", {
      ust_baslik: "Hikâyemiz",
      baslik: "Bekleme Süresini Anlamlı Bir Ana Dönüştürme Fikri",
      metin:
        "Eczaneye gelen pek çok kişi, reçetesi hazırlanırken birkaç dakika bekler. Bu süre çoğu zaman sessizce geçer; oysa kişinin kendi ihtiyaçlarını düşünmesi ve eczacısıyla daha odaklı bir görüşme yapması için değerli bir fırsattır.\n\ne-isa bu fikirden doğdu: kişiyi karmaşık terimlerle yormadan, birkaç kısa soruyla ihtiyacını fark etmesine yardımcı olan ve sonucu eczacının değerlendirmesine sunan sade bir dijital deneyim. Teşhis koymayan, marka önermeyen ve kararı her zaman eczacıya bırakan bir yaklaşım.",
      maddeler: [
        { ikon: "Target", metin: "Eczacının danışmanlık rolünü güçlendirmek" },
        { ikon: "Heart", metin: "Kişinin sağlık okuryazarlığını desteklemek" },
        { ikon: "Lightbulb", metin: "Teknolojiyi sade ve anlaşılır tutmak" },
      ],
      gorsel: null,
      gorsel_konumu: "sol",
      butonlar: [],
      arka_plan: "acik",
    }),
    blok("b_42", "ozellik_kartlari", "", {
      ust_baslik: "Değerlerimiz",
      baslik: "Bizi Yönlendiren İlkeler",
      sutun: 4,
      kartlar: [
        { ikon: "UserCircle", baslik: "Eczacı Merkezli", metin: "Her kararın sahibi eczacıdır; e-isa yalnızca ön hazırlık yapar." },
        { ikon: "ShieldCheck", baslik: "Etik", metin: "Teşhis, tedavi veya marka yönlendirmesi yapmayız; içerikleri denetleriz." },
        { ikon: "ChartLineUp", baslik: "Veri Odaklı", metin: "Varsayımlar yerine pilot verileriyle birlikte değerlendiririz." },
        { ikon: "Lightbulb", baslik: "Sade Teknoloji", metin: "Karmaşık olanı arka planda çözer, ekranda yalın bir deneyim sunarız." },
      ],
      arka_plan: "gri",
    }),
    blok("b_43", "ekip", "", {
      ust_baslik: "Ekip",
      baslik: "e-isa'nın Arkasındakiler",
      aciklama: "Sağlık, yazılım ve saha deneyimini bir araya getiren küçük ve odaklı bir ekibiz.",
      kisiler: [
        {
          ad_soyad: "Yasin ÖZGÜL",
          unvan: "Yazılım Mimarı",
          biyografi:
            "e-isa platformunun yazılım mimarisini, kiosk ve bulut altyapısını tasarlar. Güvenilir, sade ve ölçeklenebilir sistemler kurmaya odaklanır.",
          foto: null,
          linkedin: "",
        },
      ],
    }),
    blok("b_44", "cta_banner", "", {
      baslik: "Birlikte daha bilinçli bir eczane deneyimi kuralım",
      metin: "Pilot süreç, iş birliği veya sorularınız için bize ulaşın.",
      butonlar: [
        { etiket: "İletişime Geçin", href: "/iletisim", stil: "birincil" },
        { etiket: "Pilot Süreci İncele", href: "/#pilot", stil: "hayalet" },
      ],
      stil: "kirmizi",
    }),
  ],
};

/* ------------------------------------------------------------------ */
/* iletisim                                                            */
/* ------------------------------------------------------------------ */

const iletisim: PageData = {
  slug: "iletisim",
  baslik: "İletişim",
  seo: {
    baslik: "İletişim",
    aciklama: "e-isa hakkında bilgi almak, pilot süreç başvurusu yapmak veya sorularınızı iletmek için bize ulaşın.",
    og_gorsel: null,
  },
  yayin_tarihi: YAYIN,
  revizyon_id: 1,
  bloklar: [
    blok("b_50", "sayfa_basligi", "", {
      rozet: "İletişim",
      baslik: "Bizimle İletişime Geçin",
      vurgu: "İletişime Geçin",
      alt_metin:
        "e-isa hakkında daha fazla bilgi almak, pilot süreç başvurusu yapmak veya sorularınızı iletmek için bize yazabilirsiniz.",
      butonlar: [],
    }),
    blok("b_51", "basvuru_formu", "", {
      ust_baslik: "İletişim formu",
      baslik: "Mesajınızı Bırakın",
      aciklama: "Formu doldurun, ekibimiz en kısa sürede size dönüş yapsın.",
      form_tipi: "genel",
      maddeler: [],
      basari_mesaji: "Teşekkürler! Mesajınız bize ulaştı. En kısa sürede size dönüş yapacağız.",
      kvkk_sayfa_slug: "kvkk",
      iletisim_bilgisi_goster: true,
    }),
  ],
};

/* ------------------------------------------------------------------ */
/* kvkk                                                                */
/* ------------------------------------------------------------------ */

const KVKK_HTML = `
<p>Eisa Bilişim Teknolojileri A.Ş. (“Şirket”) olarak kişisel verilerinizin güvenliğine önem veriyoruz. Bu aydınlatma metni, 6698 sayılı Kişisel Verilerin Korunması Kanunu (“KVKK”) m.10 uyarınca, eisa.com.tr internet sitesi üzerinden işlenen kişisel verileriniz hakkında sizi bilgilendirmek amacıyla hazırlanmıştır.</p>
<h2>1. Veri Sorumlusu</h2>
<p>KVKK kapsamında veri sorumlusu Eisa Bilişim Teknolojileri A.Ş.'dir. Bize <a href="mailto:iletisim@eisa.com.tr">iletisim@eisa.com.tr</a> adresinden ulaşabilirsiniz.</p>
<h2>2. İşlenen Kişisel Veriler</h2>
<p>İnternet sitemizdeki pilot başvurusu, sponsorluk başvurusu ve iletişim formları aracılığıyla aşağıdaki veriler işlenebilir:</p>
<ul>
<li><strong>Kimlik bilgileri:</strong> ad, soyad</li>
<li><strong>İletişim bilgileri:</strong> e-posta adresi, telefon numarası, il</li>
<li><strong>Mesleki bilgiler:</strong> kurum / eczane adı</li>
<li><strong>Talep bilgileri:</strong> form aracılığıyla ilettiğiniz mesaj içeriği</li>
<li><strong>İşlem güvenliği bilgileri:</strong> kötüye kullanımı önlemek amacıyla IP adresinden türetilen ve geri döndürülemez biçimde saklanan özet (hash) değeri</li>
</ul>
<p>Formlarımız sağlık verisi toplamak amacıyla tasarlanmamıştır; lütfen mesaj alanına sağlık durumunuza ilişkin bilgi yazmayınız.</p>
<h2>3. İşleme Amaçları</h2>
<ul>
<li>Başvuru ve taleplerinizin alınması, değerlendirilmesi ve size dönüş yapılması,</li>
<li>Pilot süreç ve iş birliği görüşmelerinin yürütülmesi,</li>
<li>İnternet sitesinin güvenliğinin sağlanması ve kötüye kullanımın önlenmesi,</li>
<li>Hukuki yükümlülüklerin yerine getirilmesi.</li>
</ul>
<h2>4. Hukuki Sebepler</h2>
<p>Kişisel verileriniz KVKK m.5/2 uyarınca; bir sözleşmenin kurulması veya ifasıyla doğrudan ilgili olması (c), veri sorumlusunun hukuki yükümlülüğünü yerine getirebilmesi (ç) ve ilgili kişinin temel hak ve özgürlüklerine zarar vermemek kaydıyla veri sorumlusunun meşru menfaati (f) hukuki sebeplerine dayanılarak işlenir.</p>
<h2>5. Aktarım</h2>
<p>Kişisel verileriniz yurt içinde barındırılan sunucularda saklanır. Hukuken yetkili kamu kurum ve kuruluşlarının talepleri dışında üçüncü kişilerle paylaşılmaz.</p>
<h2>6. Toplama Yöntemi</h2>
<p>Kişisel verileriniz, internet sitemizdeki formları doldurmanız yoluyla elektronik ortamda toplanır.</p>
<h2>7. Saklama Süresi</h2>
<p>Başvuru verileri, talebin sonuçlandırılmasından itibaren ilgili mevzuatta öngörülen veya işleme amacının gerektirdiği süre boyunca saklanır; sürenin sonunda silinir, yok edilir veya anonim hale getirilir.</p>
<h2>8. İlgili Kişinin Hakları</h2>
<p>KVKK m.11 uyarınca; kişisel verilerinizin işlenip işlenmediğini öğrenme, işlenmişse buna ilişkin bilgi talep etme, işleme amacını ve amacına uygun kullanılıp kullanılmadığını öğrenme, aktarıldığı üçüncü kişileri bilme, eksik veya yanlış işlenmişse düzeltilmesini, KVKK m.7 çerçevesinde silinmesini veya yok edilmesini isteme, bu işlemlerin aktarıldığı üçüncü kişilere bildirilmesini isteme, münhasıran otomatik sistemlerle analiz edilmesi sonucu aleyhinize bir sonucun ortaya çıkmasına itiraz etme ve kanuna aykırı işleme sebebiyle zarara uğramanız hâlinde zararın giderilmesini talep etme haklarına sahipsiniz.</p>
<h2>9. Başvuru</h2>
<p>Haklarınıza ilişkin taleplerinizi <a href="mailto:iletisim@eisa.com.tr">iletisim@eisa.com.tr</a> adresine iletebilirsiniz. Başvurular en geç otuz gün içinde ücretsiz olarak sonuçlandırılır.</p>
`.trim();

const kvkk: PageData = {
  slug: "kvkk",
  baslik: "KVKK Aydınlatma Metni",
  seo: {
    baslik: "KVKK Aydınlatma Metni",
    aciklama: "6698 sayılı KVKK kapsamında eisa.com.tr üzerinden işlenen kişisel veriler hakkında aydınlatma metni.",
    og_gorsel: null,
  },
  yayin_tarihi: YAYIN,
  revizyon_id: 1,
  bloklar: [
    blok("b_60", "sayfa_basligi", "", {
      rozet: "Yasal",
      baslik: "KVKK Aydınlatma Metni",
      alt_metin: "6698 sayılı Kişisel Verilerin Korunması Kanunu kapsamında bilgilendirme.",
      butonlar: [],
    }),
    blok("b_61", "zengin_metin", "", {
      icerik_html: KVKK_HTML,
      genislik: "dar",
      son_guncelleme: "7 Kasım 2026",
    }),
  ],
};

/* ------------------------------------------------------------------ */
/* cerez-politikasi                                                    */
/* ------------------------------------------------------------------ */

const CEREZ_HTML = `
<p>Bu Çerez Politikası, Eisa Bilişim Teknolojileri A.Ş. tarafından işletilen eisa.com.tr internet sitesinde kullanılan çerezler hakkında sizi bilgilendirmek amacıyla hazırlanmıştır.</p>
<h2>Çerez Nedir?</h2>
<p>Çerezler, bir internet sitesini ziyaret ettiğinizde tarayıcınız aracılığıyla cihazınıza kaydedilen küçük metin dosyalarıdır. Sitenin düzgün çalışmasını, tercihlerinizin hatırlanmasını ve güvenliğin sağlanmasını mümkün kılar.</p>
<h2>Kullandığımız Çerezler</h2>
<h3>Zorunlu çerezler</h3>
<p>Sitenin temel işlevleri için gereklidir ve kapatılamaz. Örneğin çerez bilgilendirme tercihinizin hatırlanması ve form güvenliği bu kapsamdadır. Bu çerezler kişisel tercih veya pazarlama amacıyla kullanılmaz.</p>
<table>
<thead><tr><th>Ad</th><th>Amaç</th><th>Süre</th></tr></thead>
<tbody>
<tr><td>eisa_cerez_bilgi</td><td>Çerez bilgilendirmesini gördüğünüzü hatırlar (tarayıcı yerel depolaması)</td><td>Kalıcı</td></tr>
<tr><td>__prerender_bypass, eisa_preview</td><td>Yalnızca içerik editörlerinin önizleme oturumu</td><td>Oturum</td></tr>
</tbody>
</table>
<h3>Analitik çerezler</h3>
<p>Şu anda sitemizde analitik veya pazarlama çerezi kullanılmamaktadır. İleride ziyaret istatistiklerini anlamak amacıyla analitik çerezler kullanılmaya başlanırsa, bu çerezler yalnızca açık onayınızla etkinleştirilecek ve bu politika güncellenecektir.</p>
<h2>Çerezleri Nasıl Yönetebilirsiniz?</h2>
<p>Tarayıcınızın ayarlarından çerezleri silebilir veya engelleyebilirsiniz. Zorunlu çerezlerin engellenmesi durumunda sitenin bazı bölümleri beklendiği gibi çalışmayabilir.</p>
<h2>İletişim</h2>
<p>Çerezler ve kişisel verileriniz hakkındaki sorularınız için <a href="mailto:iletisim@eisa.com.tr">iletisim@eisa.com.tr</a> adresine yazabilirsiniz. Ayrıntılı bilgi için <a href="/kvkk">KVKK Aydınlatma Metni</a>'ni inceleyebilirsiniz.</p>
`.trim();

const cerezPolitikasi: PageData = {
  slug: "cerez-politikasi",
  baslik: "Çerez Politikası",
  seo: {
    baslik: "Çerez Politikası",
    aciklama: "eisa.com.tr internet sitesinde kullanılan zorunlu ve analitik çerezler ve çerez yönetimi hakkında bilgi.",
    og_gorsel: null,
  },
  yayin_tarihi: YAYIN,
  revizyon_id: 1,
  bloklar: [
    blok("b_70", "sayfa_basligi", "", {
      rozet: "Yasal",
      baslik: "Çerez Politikası",
      alt_metin: "Sitemizde hangi çerezlerin neden kullanıldığını ve nasıl yönetebileceğinizi açıklıyoruz.",
      butonlar: [],
    }),
    blok("b_71", "zengin_metin", "", {
      icerik_html: CEREZ_HTML,
      genislik: "dar",
      son_guncelleme: "7 Kasım 2026",
    }),
  ],
};

/** slug → sayfa */
export const mockSayfalar: Record<string, PageData> = {
  anasayfa,
  teknoloji,
  sponsorlar,
  hakkimizda,
  iletisim,
  kvkk,
  "cerez-politikasi": cerezPolitikasi,
};
