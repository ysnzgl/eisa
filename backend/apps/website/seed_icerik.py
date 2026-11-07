"""
`python manage.py website_seed` içerikleri (CONTRACT §9).

Kaynak: eski site (e-isa-company-websit/src/pages/*.tsx) ve eisa-website-brief.md.
Ton: teşhis/tedavi vaadi yok; kazanç rakamları "örnek senaryo / potansiyel"dir, garanti değildir;
e-isa marka değil kategori önerir; son değerlendirme her zaman eczacıdadır.
"""
from __future__ import annotations

SEO_ACIKLAMA = (
    "e-isa, eczanelerde reçete bekleme süresini yapay zeka destekli sağlık okuryazarlığı ve "
    "eczacı kontrollü danışmanlık deneyimine dönüştüren modern kiosk ekosistemidir."
)

FOOTER_ACIKLAMA = (
    "e-isa (Elektronik İnteraktif Suplement Asistanı) tıbbi bir teşhis, tedavi veya marka yönlendirme "
    "sistemi değildir. Kiosk ekranlarında sunulan içerikler, sağlık okuryazarlığını artırmaya yönelik "
    "kategori bazlı bilgilendirmelerdir. Takviye edici gıdalar ve sağlık ürünleriyle ilgili nihai "
    "değerlendirme, yönlendirme ve tavsiye yetkisi hekiminize ve eczacınıza aittir."
)

AYARLAR = {
    "site_adi": "e-isa",
    "seo_baslik_sablonu": "%s | e-isa",
    "seo_aciklama": SEO_ACIKLAMA,
    "og_gorsel": None,
    "eposta": "iletisim@eisa.com.tr",
    "telefon": "",
    "whatsapp": "",
    "adres": "",
    "firma_unvani": "Eisa Bilişim Teknolojileri A.Ş.",
    "footer_aciklama": FOOTER_ACIKLAMA,
    "sosyal_linkler": [
        {"platform": "linkedin", "url": "https://www.linkedin.com/company/e-isa"},
        {"platform": "instagram", "url": "https://www.instagram.com/eisa.tr/"},
    ],
}


def _buton(etiket, href, stil="birincil"):
    return {"etiket": etiket, "href": href, "stil": stil}


def _blok(tip, veri, anchor_id=""):
    return {"tip": tip, "veri": veri, "anchor_id": anchor_id, "gorunur": True}


UYARI_NOTU = (
    "Bu değerler garanti değildir; örnek senaryo ve potansiyel etki olarak sunulmuştur. "
    "Gerçek sonuçlar eczanenin konumuna, hasta profiline, ürün portföyüne ve eczacının "
    "danışmanlık yaklaşımına göre farklılık gösterebilir."
)

BASARI_MESAJI = "Başvurunuz alındı. Ekibimiz en kısa sürede sizinle iletişime geçecek."

# ── Anasayfa ────────────────────────────────────────────────────────────────

ANASAYFA = [
    _blok("hero", {
        "rozet": "Eczacının Ön Hazırlık Asistanı",
        "baslik": "Eczanenizdeki Reçete Bekleme Süresini Kategori Bazlı Sağlık Okuryazarlığına Dönüştürün",
        "vurgu": "Sağlık Okuryazarlığına Dönüştürün",
        "alt_metin": (
            "e-isa, kişinin yaşam tarzına ve beyan ettiği ihtiyaçlara uygun, kategori bazlı sağlık "
            "okuryazarlığı rehberliği sunar; eczacının ön hazırlık rolünü merkeze alan güvenli bir "
            "dijital deneyim sağlar."
        ),
        "vurgu_kartlari": [
            {"ikon": "ClockCounterClockwise", "metin": "60 saniyede kategorik ön hazırlık"},
            {"ikon": "Package", "metin": "Marka değil, ihtiyaç kategorisi sunar"},
            {"ikon": "ShieldCheck", "metin": "Son değerlendirme eczacı kontrolündedir"},
            {"ikon": "CheckCircle", "metin": "1 ay ücretsiz pilot süreç"},
        ],
        "butonlar": [
            _buton("Pilot Süreci İncele", "/#pilot", "birincil"),
            _buton("Nasıl Çalışır?", "/#nasil-calisir", "ikincil"),
        ],
        "kiosk_animasyonu": True,
    }),
    _blok("ozellik_kartlari", {
        "ust_baslik": "e-isa nedir?",
        "baslik": "Eczacının Ön Hazırlık Asistanı",
        "aciklama": (
            "e-isa; eczanede bekleyen kişinin yorgunluk, stres, sindirim düzeni, bağışıklık desteği, "
            "enerji ve uyku gibi yaşam kalitesi başlıklarında kısa ve sade bir dijital etkileşim "
            "yaşamasını sağlar. Ortaya çıkan ön inceleme, eczacının mesleki değerlendirmesine sunulur."
        ),
        "sutun": 4,
        "kartlar": [
            {"ikon": "Brain", "baslik": "Kısa Dijital Etkileşim",
             "metin": "Yalın sorularla kişiyi karmaşık tıbbi terimlerle yormadan ihtiyacını düşünmeye yönlendirir."},
            {"ikon": "Package", "baslik": "Kategori Bazlı Öneri",
             "metin": "Yanıtları kategori mantığıyla değerlendirir; marka değil, ihtiyaç kategorisi sunar."},
            {"ikon": "ShieldCheck", "baslik": "Eczacı Onayı",
             "metin": "Ön inceleme eczacının mesleki onayına sunulur; son değerlendirme her zaman eczacıdadır."},
            {"ikon": "QrCode", "baslik": "QR / Fiş Aktarımı",
             "metin": "Dijital sonuç QR kod veya fiş ile hızlıca bankoya, eczacıya iletilir."},
        ],
        "arka_plan": "gri",
    }, "nasil-calisir"),
    _blok("vurgu_bandi", {
        "ikon": "Lightbulb",
        "baslik": "Satıştan Önce Farkındalık: Dürtme (Nudge) Yaklaşımı",
        "metin": (
            "e-isa, davranış bilimlerinden ilham alan dürtme (nudge) yaklaşımını eczane ortamına taşır. "
            "Kişiyi karmaşık terimlerle yormadan, yalın seçenekler üzerinden kendi ihtiyacını düşünmeye "
            "davet eder. Bekleme süresindeki bu kısa deneyim, eczacıyla daha bilinçli ve odaklı bir "
            "görüşme yapılmasına yardımcı olur."
        ),
        "vurgu_cumlesi": "Ön hazırlık iklimini e-isa hazırlar, profesyonel son dokunuşu eczacı yapar.",
        "stil": "koyu",
    }),
    _blok("ozellik_kartlari", {
        "ust_baslik": "Eczacı İçin 3 Altın Kural",
        "baslik": "Kontrol Her Zaman Sizde",
        "aciklama": "e-isa eczacının yerini almaz; eczacının danışmanlığını hazırlayan dijital bir köprüdür.",
        "sutun": 3,
        "kartlar": [
            {"ikon": "Package", "baslik": "Asla Marka Önermez",
             "metin": ("e-isa belirli bir marka dayatmaz, yalnızca ihtiyaca yönelik kategori sunar. Hangi ürünün "
                       "kişiye daha uygun olduğuna karar veren yetkili her zaman eczacıdır.")},
            {"ikon": "UserCircle", "baslik": "Satışı Eczacı Tamamlar",
             "metin": ("Kiosk bir satış terminali değil, kişiyi görüşmeye hazırlayan dijital bir köprüdür. Son "
                       "karar banko başında eczacının uzmanlığıyla verilir.")},
            {"ikon": "CheckCircle", "baslik": "Stokla Uyumlu Çalışır",
             "metin": ("Kategori yaklaşımı, eczanenin mevcut ürün portföyüyle uyumlu çalışır; stok yönetimini "
                       "ve danışmanlık sürecini daha verimli hâle getirmeye yardımcı olur.")},
        ],
        "arka_plan": "acik",
    }, "eczaci-kontrolu"),
    _blok("scroll_hikaye", {
        "ust_baslik": "Müşterinin eczane içi yolculuğu",
        "baslik": "Beklemeden Etkileşime: 4 Adımlı Yolculuk",
        "aciklama": "Reçetenin hazırlandığı kısa sürede kişi, eczacıyla daha odaklı bir görüşmeye hazırlanır.",
        "adimlar": [
            {"baslik": "Reçete Teslimi", "metin": "Reçete teslim edilir ve bekleme süresi başlar.",
             "ekran_baslik": "Hoş geldiniz", "ekran_metin": "Beklerken kısa bir değerlendirmeye ne dersiniz?"},
            {"baslik": "Dijital Etkileşim", "metin": "Kişi, e-isa ekranındaki sade arayüzle etkileşime girer.",
             "ekran_baslik": "Son günlerde nasılsınız?", "ekran_metin": "Enerji · Uyku · Sindirim · Bağışıklık"},
            {"baslik": "Kategori Önerisi", "metin": "2-4 kısa soruyla kişiye uygun bir ihtiyaç kategorisi belirlenir.",
             "ekran_baslik": "Önerilen kategori", "ekran_metin": "Enerji ve vitalite desteği — marka değil, kategori."},
            {"baslik": "Eczacı Değerlendirmesi", "metin": "QR veya fiş eczacıya iletilir; eczacı öneriyi uzmanlığıyla değerlendirir.",
             "ekran_baslik": "QR kodunuz hazır", "ekran_metin": "Son değerlendirme eczacınızdadır."},
        ],
    }, "yolculuk"),
    _blok("kazanc_hesaplayici", {
        "ust_baslik": "Kazanç Modeli",
        "baslik": "Sepet Büyüten Zeka: Cross-Sell Etkisi",
        "aciklama": (
            "e-isa, kişinin yanıtlarına göre yalnızca tek bir kategoriye değil, tamamlayıcı kategori "
            "fırsatlarına da dikkat çeker. Kaydırıcıyla günlük etkileşim sayısını seçin ve örnek "
            "senaryodaki potansiyel etkiyi inceleyin."
        ),
        "kademeler": [
            {"etkilesim_min": 1, "etkilesim_max": 10, "gunluk_satis": 1, "aylik_satis": 25, "aylik_ciro": 18000, "aylik_kar": 6000},
            {"etkilesim_min": 10, "etkilesim_max": 20, "gunluk_satis": 3, "aylik_satis": 75, "aylik_ciro": 56000, "aylik_kar": 18000},
            {"etkilesim_min": 20, "etkilesim_max": 30, "gunluk_satis": 6, "aylik_satis": 150, "aylik_ciro": 110000, "aylik_kar": 36000},
            {"etkilesim_min": 30, "etkilesim_max": 40, "gunluk_satis": 10, "aylik_satis": 250, "aylik_ciro": 185000, "aylik_kar": 62000},
            {"etkilesim_min": 40, "etkilesim_max": 50, "gunluk_satis": 15, "aylik_satis": 375, "aylik_ciro": 280000, "aylik_kar": 94000},
        ],
        "varsayilan_etkilesim": 15,
        "slider_max": 50,
        "para_birimi": "TL",
        "uyari_notu": UYARI_NOTU,
        "tablo_goster": True,
    }, "kazanc"),
    _blok("ozellik_kartlari", {
        "ust_baslik": "Pasif Gelir Ekosistemi",
        "baslik": "e-isa Kendi Kendini Finanse Eden Bir Ekosisteme Dönüşebilir",
        "aciklama": (
            "Kiosk ekranı, eczane atmosferine uygun dijital bilgilendirme alanı olarak da "
            "değerlendirilebilir. İçerik yönetimi ve teknik güncellemeler merkezi olarak yürütülür; "
            "eczane operasyonel yük almadan ek katkı potansiyeli elde edebilir."
        ),
        "sutun": 4,
        "kartlar": [
            {"ikon": "Monitor", "baslik": "Dijital Bilgilendirme Paylaşımı",
             "metin": "Bekleme anlarında, eczane ortamına uygun bilgilendirici içerikler gösterilebilir."},
            {"ikon": "Coins", "baslik": "%10 Altyapı / Lisans Desteği",
             "metin": "İçerik paylaşım modelinden eczaneye altyapı ve lisans giderlerine katkı sağlanabilir."},
            {"ikon": "Lightning", "baslik": "Operasyonel Yük Yok",
             "metin": "İçerik planlama ve güncellemeler merkezi olarak yönetilir; eczane ekibine ek iş düşmez."},
            {"ikon": "ShieldCheck", "baslik": "Etik İçerik Denetimi",
             "metin": "Yayınlanacak içerikler eczane etiğine ve ilgili mevzuata uygunluk açısından denetlenir."},
        ],
        "arka_plan": "gri",
    }),
    _blok("sss", {
        "ust_baslik": "SSS",
        "baslik": "Sık Sorulan Sorular",
        "aciklama": "Merak ettiklerinizi yanıtlıyoruz.",
        "sorular": [
            {"soru": "Kiosk iş yerime sığar mı?",
             "cevap": "Samsung kiosk'un kompakt yapısı, standart bir dergilikten fazla alan kaplamadan eczane ortamına yerleşebilecek şekilde tasarlanmıştır."},
            {"soru": "Müşteriler kiosku kullanır mı?",
             "cevap": "Yalın seçenekler, kısa etkileşim süresi ve dikkat çekici arayüz sayesinde kişinin bekleme anında ekranla etkileşime girmesi hedeflenir. Pilot süreç, bunu kendi eczanenizde gözlemlemenizi sağlar."},
            {"soru": "Biz zaten satış yapıyoruz, neden e-isa?",
             "cevap": "e-isa, ihtiyacını dile getirmeyen sessiz müşteriyi farkındalık sürecine dahil eder ve eczacının danışmanlığını destekler. Satışı ve son kararı yine eczacı verir."},
            {"soru": "İçerikler eczacılık etiğine uygun mu?",
             "cevap": "Kiosk'ta yayınlanan içerikler eczane atmosferine ve ilgili sağlık beyanı kurallarına uygunluk açısından denetlenir. e-isa teşhis koymaz, tedavi önermez ve marka yönlendirmesi yapmaz."},
            {"soru": "İnternet bağlantısı kesilirse ne olur?",
             "cevap": "Sistem çevrimdışı çalışabilecek şekilde tasarlanmıştır. Bağlantı geri geldiğinde veriler, kayıp yaşanmaması gözetilerek yeniden senkronize edilir."},
        ],
        "arka_plan": "acik",
    }, "sss"),
    _blok("blog_son_yazilar", {
        "baslik": "Blog'dan",
        "aciklama": "Sağlık okuryazarlığı, eczane yönetimi ve e-isa'dan haberler.",
        "adet": 3,
        "kategori_slug": "",
    }),
    _blok("basvuru_formu", {
        "ust_baslik": "1 Ay Ücretsiz Pilot",
        "baslik": "Pilot Süreç: Veri Konuşsun, Kararı Siz Verin",
        "aciklama": (
            "e-isa'yı varsayımlarla değil, eczanenizin kendi verileriyle değerlendirin. 30 günlük pilot "
            "süreçte kişi etkileşimini, danışmanlık akışını ve sepet ortalamasındaki değişimi gözlemleyin."
        ),
        "form_tipi": "pilot",
        "maddeler": [
            {"ikon": "CheckCircle", "baslik": "Kompakt Pilot Ünite", "metin": "Pratik test için hazır kurulum."},
            {"ikon": "Handshake", "baslik": "Yakın Saha Desteği", "metin": "Pilot süresince ekibimiz yanınızda."},
            {"ikon": "Target", "baslik": "Stratejik Danışmanlık", "metin": "Kalıcı süreçte düzenli ziyaret ve değerlendirme."},
        ],
        "basari_mesaji": "Pilot başvurunuz alındı. Ekibimiz en kısa sürede sizinle iletişime geçerek süreci planlayacak.",
        "kvkk_sayfa_slug": "kvkk",
        "iletisim_bilgisi_goster": False,
    }, "pilot"),
]

# ── Teknoloji ───────────────────────────────────────────────────────────────

TEKNOLOJI = [
    _blok("sayfa_basligi", {
        "rozet": "Teknoloji ve Tasarım",
        "baslik": "Eczane Atmosferine Uyumlu Modern Kiosk Deneyimi",
        "vurgu": "Modern Kiosk Deneyimi",
        "alt_metin": "Kompakt donanım, sade arayüz ve bulut tabanlı yönetim; eczane ekibine ek yük getirmeden.",
        "butonlar": [_buton("Pilot Süreci İncele", "/#pilot", "birincil")],
    }),
    _blok("gorsel_metin", {
        "ust_baslik": "Donanım",
        "baslik": "Samsung 24\" Kiosk ile Kompakt ve Şık Kurulum",
        "metin": (
            "Samsung kiosk'un 24 inçlik kompakt gövdesi, eczane ortamına modern ve teknolojik bir dokunuş "
            "katar. Nötr gri-beyaz tonlar ve e-isa'nın kırmızı vurgusu, eczane mimarisiyle uyumlu ve güven "
            "veren bir görünüm oluşturur.\n\n"
            "Kurulum ve içerik güncellemeleri ekibimiz tarafından yürütülür; eczane ekibinin yalnızca "
            "kiosku kullanıma açık tutması yeterlidir."
        ),
        "maddeler": [
            {"ikon": "Monitor", "metin": "24 inç dokunmatik ekran"},
            {"ikon": "QrCode", "metin": "QR kod veya fiş ile sonuç aktarımı"},
            {"ikon": "Cloud", "metin": "Bulut tabanlı merkezi yönetim"},
            {"ikon": "WifiSlash", "metin": "Bağlantı kesintisinde çevrimdışı çalışma"},
        ],
        "gorsel": None,
        "gorsel_konumu": "sag",
        "butonlar": [],
        "arka_plan": "acik",
    }),
    _blok("ozellik_kartlari", {
        "ust_baslik": "Öne Çıkanlar",
        "baslik": "Eczane İçin Tasarlandı",
        "sutun": 4,
        "kartlar": [
            {"ikon": "Storefront", "baslik": "Kompakt Yapı",
             "metin": "Standart bir dergilik kadar alan kaplar; banko akışını engellemez."},
            {"ikon": "Devices", "baslik": "Modern Deneyim",
             "metin": "Büyük yazılar, yalın seçenekler ve kısa akış ile her yaştan kullanıcıya uygun arayüz."},
            {"ikon": "QrCode", "baslik": "QR / Dijital Sonuç",
             "metin": "Ön inceleme QR kod veya fiş ile saniyeler içinde eczacıya ulaşır."},
            {"ikon": "CloudArrowUp", "baslik": "Bulut + Çevrimdışı Senkron",
             "metin": "İçerik ve ayarlar merkezden yönetilir; bağlantı kesilse de kiosk çalışmaya devam eder."},
        ],
        "arka_plan": "gri",
    }),
    _blok("sayaclar", {
        "baslik": "Rakamlarla e-isa",
        "ogeler": [
            {"deger": 60, "onek": "", "sonek": " sn", "etiket": "Hedeflenen etkileşim süresi"},
            {"deger": 4, "onek": "2-", "sonek": "", "etiket": "Kısa soru"},
            {"deger": 24, "onek": "", "sonek": " inç", "etiket": "Dokunmatik ekran"},
            {"deger": 1, "onek": "", "sonek": " ay", "etiket": "Ücretsiz pilot süreç"},
        ],
        "arka_plan": "koyu",
    }),
    _blok("surec_adimlari", {
        "ust_baslik": "Kurulum",
        "baslik": "Kurulumdan İzlemeye 4 Adım",
        "aciklama": "Pilot sürecin her adımında ekibimiz sizinle birlikte çalışır.",
        "adimlar": [
            {"baslik": "Keşif", "metin": "Eczanenizin yerleşimi, müşteri akışı ve beklentileriniz birlikte değerlendirilir."},
            {"baslik": "Kurulum", "metin": "Kiosk, banko akışını engellemeyecek en uygun noktaya kurulur ve yapılandırılır."},
            {"baslik": "Eğitim", "metin": "Eczane ekibine kısa bir kullanım ve QR/fiş değerlendirme eğitimi verilir."},
            {"baslik": "İzleme", "metin": "Etkileşim verileri düzenli olarak paylaşılır; süreç birlikte değerlendirilir."},
        ],
        "arka_plan": "acik",
    }),
    _blok("cta_banner", {
        "rozet": "1 Ay Ücretsiz",
        "baslik": "e-isa'yı Eczanenizde Deneyin",
        "metin": "30 günlük pilot süreçle e-isa'yı kendi verilerinizle değerlendirin.",
        "butonlar": [_buton("Pilot Başvurusu Yap", "/#pilot", "birincil")],
        "stil": "kirmizi",
    }),
]

# ── Sponsorlar ──────────────────────────────────────────────────────────────

SPONSORLAR = [
    _blok("sayfa_basligi", {
        "rozet": "Sponsorluk / Kurumsal İş Birliği",
        "baslik": "Geleceğin Eczane Deneyiminde Kurumsal İş Ortağı Olun",
        "vurgu": "Kurumsal İş Ortağı",
        "alt_metin": (
            "Markanızı, tüketicinin sağlık çözümüne en çok ihtiyaç duyduğu ve güven ortamında bulunduğu "
            "eczane noktasında, etik iletişim ilkelerine uygun olarak konumlandırın."
        ),
        "butonlar": [_buton("Sponsorluk Başvurusu", "#basvuru", "birincil")],
    }),
    _blok("ozellik_kartlari", {
        "ust_baslik": "Değer Önermesi",
        "baslik": "Neden e-isa?",
        "aciklama": (
            "Eisa Bilişim Teknolojileri A.Ş. olarak geliştirdiğimiz e-isa dijital bilgilendirme ekosistemi, "
            "markaların etik iletişim ilkeleriyle doğru noktada konumlanmasını sağlar."
        ),
        "sutun": 3,
        "kartlar": [
            {"ikon": "Sparkle", "baslik": "Görünürlükten Fazlası",
             "metin": "e-isa markalara yalnızca görünürlük sunmaz; güven ortamında bilgilendirici bir temas noktası oluşturur."},
            {"ikon": "TrendUp", "baslik": "Seçkin Eczaneler",
             "metin": "Kurumsal hizmet anlayışıyla öne çıkan, yüksek kişi trafiğine sahip eczanelerle başlıyoruz."},
            {"ikon": "Users", "baslik": "Sınırlı Ortaklık",
             "metin": "Sınırlı sayıda stratejik iş ortağıyla ilerliyoruz. İlk paydaşlar arasında yerinizi alın."},
        ],
        "arka_plan": "gri",
    }),
    _blok("surec_adimlari", {
        "ust_baslik": "Süreç",
        "baslik": "Sponsorluk Süreci",
        "aciklama": "Dört adımda kurumsal iş birliği sürecimizi keşfedin.",
        "adimlar": [
            {"baslik": "Ön Değerlendirme", "metin": "Başvurunuzun ardından ekibimiz, markanıza özel iş birliği çerçevesini paylaşır."},
            {"baslik": "Kurumsal Sunum", "metin": "Markanıza özel konumlandırma yaklaşımı hazırlanır ve sunulur."},
            {"baslik": "Etik Uyum Görüşmesi", "metin": "Olası iş birliği fırsatları etik iletişim ilkeleriyle birlikte değerlendirilir."},
            {"baslik": "Ekosisteme Katılım", "metin": "Geleceğin eczane deneyiminde doğru temasın değerini birlikte oluştururuz."},
        ],
        "arka_plan": "acik",
    }),
    _blok("logo_bandi", {
        "baslik": "İş Ortaklarımız",
        "logolar": [],
        "bos_mesaj": "İlk iş ortaklarımızla görüşmelerimiz sürüyor. Bu alanda yer almak için başvurabilirsiniz.",
    }),
    _blok("basvuru_formu", {
        "ust_baslik": "İlk Paydaşlar Arasında Olun",
        "baslik": "Sponsorluk Başvurusu",
        "aciklama": "Başvurunuzun ardından ekibimiz, markanıza özel hazırlanan iş birliği modelini paylaşır ve süreci başlatır.",
        "form_tipi": "sponsor",
        "maddeler": [],
        "basari_mesaji": "Sponsorluk başvurunuz alındı. Ekibimiz en kısa sürede sizinle iletişime geçecek.",
        "kvkk_sayfa_slug": "kvkk",
        "iletisim_bilgisi_goster": False,
    }, "basvuru"),
]

# ── Hakkımızda ──────────────────────────────────────────────────────────────

HAKKIMIZDA = [
    _blok("sayfa_basligi", {
        "rozet": "Hakkımızda",
        "baslik": "Eczacıyı Merkeze Alan Teknoloji",
        "vurgu": "Merkeze Alan",
        "alt_metin": (
            "Eisa Bilişim Teknolojileri A.Ş. olarak eczanedeki bekleme anını, eczacının mesleki "
            "değerlendirmesini destekleyen sade bir dijital deneyime dönüştürüyoruz."
        ),
        "butonlar": [],
    }),
    _blok("gorsel_metin", {
        "ust_baslik": "Hikâyemiz",
        "baslik": "Bekleme Anından Bilinçli Bir Görüşmeye",
        "metin": (
            "Eczanede reçete hazırlanırken geçen birkaç dakika çoğu zaman sessizce geçer. Oysa bu kısa "
            "süre, kişinin kendi yaşam kalitesi hakkında düşünmesi ve eczacısına daha doğru sorular "
            "sorması için değerli bir fırsattır.\n\n"
            "e-isa bu fikirden doğdu: eczacının bilgi ve deneyimini merkeze alan, onun yerine karar "
            "vermeyen ama görüşmeye zemin hazırlayan bir yapay zeka karar destek ekosistemi. Sistem teşhis "
            "koymaz, tedavi önermez ve marka yönlendirmesi yapmaz; yalnızca kısa sorularla ihtiyacı bir "
            "kategoriye taşır ve son değerlendirmeyi eczacıya bırakır.\n\n"
            "Ürünü sahada, eczacılarla birlikte geliştiriyor; her adımda veriye, etik ilkelere ve "
            "sadeliğe öncelik veriyoruz."
        ),
        "maddeler": [
            {"ikon": "UserCircle", "metin": "Eczacının mesleki değerlendirmesini destekler, yerini almaz."},
            {"ikon": "Package", "metin": "Marka değil, ihtiyaç kategorisi sunar."},
            {"ikon": "ChartLineUp", "metin": "Kararlar varsayımla değil, pilot verisiyle verilir."},
        ],
        "gorsel": None,
        "gorsel_konumu": "sol",
        "butonlar": [],
        "arka_plan": "acik",
    }),
    _blok("ozellik_kartlari", {
        "ust_baslik": "Değerlerimiz",
        "baslik": "Bizi Yönlendiren İlkeler",
        "sutun": 4,
        "kartlar": [
            {"ikon": "UserCircle", "baslik": "Eczacı Merkezli",
             "metin": "Tasarladığımız her akış, eczacının danışmanlık rolünü güçlendirmek için vardır."},
            {"ikon": "ShieldCheck", "baslik": "Etik",
             "metin": "Teşhis veya tedavi vaadinde bulunmayız; içerikleri sağlık beyanı kurallarına uygunluk açısından denetleriz."},
            {"ikon": "ChartLineUp", "baslik": "Veri Odaklı",
             "metin": "Etkiyi tahminle değil, pilot süreçte toplanan anonim etkileşim verileriyle ölçeriz."},
            {"ikon": "Lightbulb", "baslik": "Sade Teknoloji",
             "metin": "Karmaşık terimler yerine kısa, anlaşılır sorular ve kolay kullanılan bir arayüz."},
        ],
        "arka_plan": "gri",
    }),
    _blok("ekip", {
        "ust_baslik": "Ekip",
        "baslik": "e-isa'yı Geliştirenler",
        "aciklama": "Eczacılarla birlikte, sahadan gelen geri bildirimlerle çalışan küçük ve odaklı bir ekibiz.",
        "kisiler": [
            {
                "ad_soyad": "Yasin ÖZGÜL",
                "unvan": "Yazılım Mimarı",
                "biyografi": (
                    "e-isa'nın kiosk, merkezi API ve yönetim paneli mimarisinden sorumludur. Güvenli, "
                    "çevrimdışı çalışabilen ve sahada kolay yönetilen sistemler tasarlamaya odaklanır; "
                    "teknolojinin eczacının işini kolaylaştıran sade bir araç olması gerektiğine inanır."
                ),
                "foto": None,
                "linkedin": "",
            },
        ],
    }),
    _blok("cta_banner", {
        "rozet": "Birlikte Çalışalım",
        "baslik": "Eczanenizde e-isa'yı Değerlendirmek İster misiniz?",
        "metin": "Pilot süreç veya iş birliği hakkında bilgi almak için bizimle iletişime geçin.",
        "butonlar": [
            _buton("İletişime Geçin", "/iletisim", "birincil"),
            _buton("Pilot Süreci İncele", "/#pilot", "ikincil"),
        ],
        "stil": "koyu",
    }),
]

# ── İletişim ────────────────────────────────────────────────────────────────

ILETISIM = [
    _blok("sayfa_basligi", {
        "rozet": "İletişim",
        "baslik": "Bizimle İletişime Geçin",
        "vurgu": "İletişime Geçin",
        "alt_metin": (
            "e-isa hakkında bilgi almak, pilot süreç başvurusu yapmak veya sorularınızı iletmek için "
            "formu doldurabilirsiniz."
        ),
        "butonlar": [],
    }),
    _blok("basvuru_formu", {
        "ust_baslik": "Mesaj Gönderin",
        "baslik": "Size Nasıl Yardımcı Olabiliriz?",
        "aciklama": "Mesajınızı bırakın, ekibimiz en kısa sürede size dönüş yapsın.",
        "form_tipi": "genel",
        "maddeler": [],
        "basari_mesaji": BASARI_MESAJI,
        "kvkk_sayfa_slug": "kvkk",
        "iletisim_bilgisi_goster": True,
    }, "form"),
]

# ── KVKK ────────────────────────────────────────────────────────────────────

KVKK_HTML = """
<p>Eisa Bilişim Teknolojileri A.Ş. (“Şirket”) olarak, 6698 sayılı Kişisel Verilerin Korunması Kanunu (“KVKK” veya “Kanun”) kapsamında veri sorumlusu sıfatıyla, eisa.com.tr internet sitesi (“Site”) aracılığıyla elde edilen kişisel verilerinizi aşağıda açıklanan çerçevede işlemekteyiz. Bu aydınlatma metni, Kanun’un 10. maddesi uyarınca sizi bilgilendirmek amacıyla hazırlanmıştır.</p>
<h2>1. Veri Sorumlusu</h2>
<p>Veri sorumlusu: <strong>Eisa Bilişim Teknolojileri A.Ş.</strong><br>İletişim: <a href="mailto:iletisim@eisa.com.tr">iletisim@eisa.com.tr</a></p>
<h2>2. İşlenen Kişisel Veriler</h2>
<ul>
<li><strong>Kimlik ve iletişim bilgileri:</strong> Başvuru ve iletişim formlarında paylaştığınız ad soyad, kurum/eczane adı, e-posta adresi, telefon numarası ve il bilgisi.</li>
<li><strong>Talep bilgileri:</strong> Formun mesaj alanına yazdığınız içerik, başvuru türü (pilot, sponsorluk, genel) ve başvurunun yapıldığı sayfa.</li>
<li><strong>Onay kayıtları:</strong> Bu aydınlatma metnini okuduğunuza ilişkin onay bilgisi, onay tarihi ve onay verilen metnin sürümü.</li>
<li><strong>Teknik kayıtlar:</strong> Güvenlik ve kötüye kullanımın önlenmesi amacıyla IP adresinizden tek yönlü olarak türetilen özet (hash) değeri; sunucu erişim kayıtları ve çerez verileri (ayrıntılar için Çerez Politikası’na bakınız).</li>
</ul>
<p>Site üzerinden sağlık verisi talep edilmemektedir. Lütfen form alanlarında sağlık durumunuza ilişkin bilgi paylaşmayınız.</p>
<h2>3. Kişisel Verilerin İşlenme Amaçları</h2>
<ul>
<li>Pilot süreç, sponsorluk ve genel iletişim taleplerinizin alınması, değerlendirilmesi ve size dönüş yapılması,</li>
<li>Talep edilmesi hâlinde ürün ve hizmetlerimize ilişkin bilgi verilmesi ve iş birliği süreçlerinin yürütülmesi,</li>
<li>Site’nin güvenliğinin sağlanması, spam ve kötüye kullanımın önlenmesi,</li>
<li>Hukuki yükümlülüklerin yerine getirilmesi ve yetkili kurumların taleplerinin karşılanması.</li>
</ul>
<h2>4. Hukuki Sebepler ve Toplama Yöntemi</h2>
<p>Kişisel verileriniz, Site’deki formlar ve çerezler aracılığıyla elektronik ortamda toplanmakta ve Kanun’un 5. maddesinin 2. fıkrasında yer alan;</p>
<ul>
<li>(c) bir sözleşmenin kurulması veya ifasıyla doğrudan doğruya ilgili olması kaydıyla, sözleşmenin taraflarına ait kişisel verilerin işlenmesinin gerekli olması,</li>
<li>(ç) veri sorumlusunun hukuki yükümlülüğünü yerine getirebilmesi için zorunlu olması,</li>
<li>(f) ilgili kişinin temel hak ve özgürlüklerine zarar vermemek kaydıyla, veri sorumlusunun meşru menfaatleri için veri işlenmesinin zorunlu olması</li>
</ul>
<p>hukuki sebeplerine dayanılarak işlenmektedir. Zorunlu olmayan (ör. analitik) çerezler yalnızca açık rızanız alınarak kullanılır.</p>
<h2>5. Kişisel Verilerin Aktarılması</h2>
<p>Kişisel verileriniz; yukarıdaki amaçlarla sınırlı olarak, barındırma ve altyapı hizmeti aldığımız tedarikçilerimize ve hukuken yetkili kamu kurum ve kuruluşlarına, Kanun’un 8. ve 9. maddelerinde öngörülen şartlara uygun olarak aktarılabilir. Kişisel verileriniz pazarlama amacıyla üçüncü kişilerle paylaşılmaz.</p>
<h2>6. Saklama Süresi</h2>
<p>Form aracılığıyla iletilen kişisel veriler, talebinizin sonuçlandırılması için gerekli süre boyunca ve her hâlükârda talebin kapatılmasından itibaren en fazla 2 (iki) yıl süreyle saklanır. Daha uzun bir saklama süresi öngören mevzuat hükümleri saklıdır. Süre sona erdiğinde veriler silinir, yok edilir veya anonim hâle getirilir.</p>
<h2>7. KVKK’nın 11. Maddesi Kapsamındaki Haklarınız</h2>
<p>Kanun’un 11. maddesi uyarınca veri sorumlusuna başvurarak;</p>
<ul>
<li>Kişisel verilerinizin işlenip işlenmediğini öğrenme,</li>
<li>Kişisel verileriniz işlenmişse buna ilişkin bilgi talep etme,</li>
<li>Kişisel verilerinizin işlenme amacını ve bunların amacına uygun kullanılıp kullanılmadığını öğrenme,</li>
<li>Yurt içinde veya yurt dışında kişisel verilerinizin aktarıldığı üçüncü kişileri bilme,</li>
<li>Kişisel verilerinizin eksik veya yanlış işlenmiş olması hâlinde bunların düzeltilmesini isteme,</li>
<li>Kanun’un 7. maddesinde öngörülen şartlar çerçevesinde kişisel verilerinizin silinmesini veya yok edilmesini isteme,</li>
<li>Düzeltme, silme veya yok etme işlemlerinin, kişisel verilerinizin aktarıldığı üçüncü kişilere bildirilmesini isteme,</li>
<li>İşlenen verilerin münhasıran otomatik sistemler vasıtasıyla analiz edilmesi suretiyle aleyhinize bir sonucun ortaya çıkmasına itiraz etme,</li>
<li>Kişisel verilerinizin kanuna aykırı olarak işlenmesi sebebiyle zarara uğramanız hâlinde zararın giderilmesini talep etme</li>
</ul>
<p>haklarına sahipsiniz.</p>
<h2>8. Başvuru Yöntemi</h2>
<p>Haklarınıza ilişkin taleplerinizi, Veri Sorumlusuna Başvuru Usul ve Esasları Hakkında Tebliğ’e uygun olarak, kimliğinizi tespit etmeye yarayan bilgilerle birlikte <a href="mailto:iletisim@eisa.com.tr">iletisim@eisa.com.tr</a> adresine iletebilirsiniz. Başvurunuz, talebin niteliğine göre en kısa sürede ve en geç 30 (otuz) gün içinde ücretsiz olarak sonuçlandırılır. İşlemin ayrıca bir maliyet gerektirmesi hâlinde Kişisel Verileri Koruma Kurulu tarafından belirlenen tarifedeki ücret alınabilir.</p>
<p>Şirket, bu aydınlatma metnini mevzuattaki değişikliklere ve veri işleme faaliyetlerine göre güncelleyebilir. Güncel metin her zaman bu sayfada yayımlanır.</p>
"""

KVKK = [
    _blok("sayfa_basligi", {
        "rozet": "KVKK",
        "baslik": "KVKK Aydınlatma Metni",
        "vurgu": "",
        "alt_metin": "6698 sayılı Kişisel Verilerin Korunması Kanunu kapsamında kişisel verilerinizin işlenmesine ilişkin bilgilendirme.",
        "butonlar": [],
    }),
    _blok("zengin_metin", {
        "baslik": "",
        "icerik_html": KVKK_HTML,
        "genislik": "dar",
        "son_guncelleme": "7 Kasım 2026",
    }),
]

# ── Çerez Politikası ────────────────────────────────────────────────────────

CEREZ_HTML = """
<p>Bu Çerez Politikası, Eisa Bilişim Teknolojileri A.Ş. (“Şirket”) tarafından işletilen eisa.com.tr internet sitesinde (“Site”) kullanılan çerezler hakkında sizi bilgilendirmek amacıyla hazırlanmıştır. Çerezler aracılığıyla işlenen kişisel verilere ilişkin ayrıntılı bilgi için <a href="/kvkk">KVKK Aydınlatma Metni</a>’ni inceleyebilirsiniz.</p>
<h2>1. Çerez Nedir?</h2>
<p>Çerezler, bir internet sitesini ziyaret ettiğinizde tarayıcınız aracılığıyla cihazınıza kaydedilen küçük metin dosyalarıdır. Sitenin düzgün çalışmasını, güvenliğinin sağlanmasını ve tercihlerinizin hatırlanmasını sağlarlar.</p>
<h2>2. Kullandığımız Çerez Türleri</h2>
<h3>Zorunlu çerezler</h3>
<p>Site’nin temel işlevlerinin çalışması için gereklidir ve kapatılamaz. Örneğin çerez tercihinizin hatırlanması, form gönderimlerinin güvenliği ve yalnızca içerik editörlerimizin kullandığı önizleme modu (<code>eisa_preview</code>) bu kapsamdadır. Bu çerezler, Kanun’un 5. maddesinin 2. fıkrasının (f) bendindeki meşru menfaat hukuki sebebine dayanır.</p>
<h3>Analitik çerezler</h3>
<p>Site’nin nasıl kullanıldığını anonim veya takma adlı istatistiklerle anlamamıza ve içeriği geliştirmemize yardımcı olur. Analitik çerezler <strong>yalnızca çerez bandı üzerinden onay vermeniz hâlinde</strong> etkinleştirilir; onay vermemeniz Site’yi kullanmanızı engellemez.</p>
<p>Site’de pazarlama veya hedefleme amaçlı çerez kullanılmamaktadır.</p>
<h2>3. Çerezlerin Yönetimi</h2>
<p>Çerez tercihlerinizi Site’nin alt kısmında yer alan çerez bandı üzerinden dilediğiniz zaman değiştirebilirsiniz. Ayrıca tarayıcınızın ayarlarından çerezleri silebilir veya engelleyebilirsiniz. Zorunlu çerezlerin engellenmesi hâlinde Site’nin bazı bölümleri beklendiği gibi çalışmayabilir.</p>
<ul>
<li>Chrome: Ayarlar › Gizlilik ve güvenlik › Çerezler ve diğer site verileri</li>
<li>Firefox: Ayarlar › Gizlilik ve Güvenlik › Çerezler ve Site Verileri</li>
<li>Safari: Tercihler › Gizlilik › Web sitesi verilerini yönet</li>
<li>Edge: Ayarlar › Çerezler ve site izinleri</li>
</ul>
<h2>4. Saklama Süreleri</h2>
<p>Oturum çerezleri tarayıcınızı kapattığınızda silinir. Kalıcı çerezler, işlevlerine göre en fazla 12 ay süreyle cihazınızda kalır; çerez tercihiniz de bu süre boyunca hatırlanır.</p>
<h2>5. Değişiklikler ve İletişim</h2>
<p>Şirket, bu politikayı gerektiğinde güncelleyebilir; güncel metin her zaman bu sayfada yayımlanır. Sorularınız için <a href="mailto:iletisim@eisa.com.tr">iletisim@eisa.com.tr</a> adresinden bize ulaşabilirsiniz.</p>
"""

CEREZ_POLITIKASI = [
    _blok("sayfa_basligi", {
        "rozet": "Çerezler",
        "baslik": "Çerez Politikası",
        "vurgu": "",
        "alt_metin": "eisa.com.tr’de hangi çerezleri neden kullandığımız ve bunları nasıl yönetebileceğiniz.",
        "butonlar": [],
    }),
    _blok("zengin_metin", {
        "baslik": "",
        "icerik_html": CEREZ_HTML,
        "genislik": "dar",
        "son_guncelleme": "7 Kasım 2026",
    }),
]

# ── Sayfa listesi (slug, başlık, seo_baslik, seo_aciklama, sıra, bloklar) ───

SAYFALAR = [
    {
        "slug": "anasayfa", "baslik": "Anasayfa",
        "seo_baslik": "Eczaneler için Yapay Zeka Destekli Karar Destek Ekosistemi",
        "seo_aciklama": SEO_ACIKLAMA, "sira": 0, "bloklar": ANASAYFA,
    },
    {
        "slug": "teknoloji", "baslik": "Teknoloji",
        "seo_baslik": "Teknoloji ve Kiosk Deneyimi",
        "seo_aciklama": "Samsung 24 inç kiosk, sade arayüz, QR ile sonuç aktarımı ve bulut tabanlı yönetim: e-isa'nın teknolojisini tanıyın.",
        "sira": 1, "bloklar": TEKNOLOJI,
    },
    {
        "slug": "sponsorlar", "baslik": "Sponsorlar",
        "seo_baslik": "Sponsorluk ve Kurumsal İş Birliği",
        "seo_aciklama": "Markanızı eczane noktasında, etik iletişim ilkelerine uygun olarak konumlandırın. e-isa sponsorluk sürecini inceleyin.",
        "sira": 2, "bloklar": SPONSORLAR,
    },
    {
        "slug": "hakkimizda", "baslik": "Hakkımızda",
        "seo_baslik": "Hakkımızda",
        "seo_aciklama": "Eisa Bilişim Teknolojileri A.Ş. eczacıyı merkeze alan yapay zeka karar destek ekosistemi e-isa'yı geliştirir.",
        "sira": 3, "bloklar": HAKKIMIZDA,
    },
    {
        "slug": "iletisim", "baslik": "İletişim",
        "seo_baslik": "İletişim",
        "seo_aciklama": "e-isa hakkında bilgi almak, pilot süreç başvurusu yapmak veya sorularınızı iletmek için bize ulaşın.",
        "sira": 4, "bloklar": ILETISIM,
    },
    {
        "slug": "kvkk", "baslik": "KVKK Aydınlatma Metni",
        "seo_baslik": "KVKK Aydınlatma Metni",
        "seo_aciklama": "6698 sayılı KVKK kapsamında eisa.com.tr üzerinden işlenen kişisel verilere ilişkin aydınlatma metni.",
        "sira": 90, "bloklar": KVKK,
    },
    {
        "slug": "cerez-politikasi", "baslik": "Çerez Politikası",
        "seo_baslik": "Çerez Politikası",
        "seo_aciklama": "eisa.com.tr'de kullanılan zorunlu ve analitik çerezler ve çerez tercihlerinin yönetimi.",
        "sira": 91, "bloklar": CEREZ_POLITIKASI,
    },
]

# ── Menüler ─────────────────────────────────────────────────────────────────
# Öğe: (etiket, link_tipi, sayfa_slug|None, bolum_anchor, url, cta, cocuklar)


def _m(etiket, link_tipi, sayfa=None, anchor="", url="", cta=False, cocuklar=None):
    return {
        "etiket": etiket, "link_tipi": link_tipi, "sayfa": sayfa, "bolum_anchor": anchor,
        "url": url, "cta": cta, "cocuklar": cocuklar or [],
    }


MENULER = {
    "header": [
        _m("Çözüm", "bolum", "anasayfa", "nasil-calisir", cocuklar=[
            _m("Nasıl Çalışır", "bolum", "anasayfa", "nasil-calisir"),
            _m("Eczacı Kontrolü", "bolum", "anasayfa", "eczaci-kontrolu"),
            _m("Müşteri Yolculuğu", "bolum", "anasayfa", "yolculuk"),
            _m("Kazanç Modeli", "bolum", "anasayfa", "kazanc"),
            _m("SSS", "bolum", "anasayfa", "sss"),
        ]),
        _m("Teknoloji", "sayfa", "teknoloji"),
        _m("Sponsorlar", "sayfa", "sponsorlar"),
        _m("Blog", "blog"),
        _m("Kurumsal", "sayfa", "hakkimizda", cocuklar=[
            _m("Hakkımızda", "sayfa", "hakkimizda"),
            _m("İletişim", "sayfa", "iletisim"),
        ]),
        _m("1 Ay Ücretsiz Pilot", "bolum", "anasayfa", "pilot", cta=True),
    ],
    "footer": [
        _m("Ürün", "bolum", "anasayfa", "nasil-calisir", cocuklar=[
            _m("Nasıl Çalışır", "bolum", "anasayfa", "nasil-calisir"),
            _m("Teknoloji", "sayfa", "teknoloji"),
            _m("Kazanç Modeli", "bolum", "anasayfa", "kazanc"),
            _m("SSS", "bolum", "anasayfa", "sss"),
        ]),
        _m("Kurumsal", "sayfa", "hakkimizda", cocuklar=[
            _m("Hakkımızda", "sayfa", "hakkimizda"),
            _m("Sponsorlar", "sayfa", "sponsorlar"),
            _m("Blog", "blog"),
            _m("İletişim", "sayfa", "iletisim"),
        ]),
    ],
    "footer_alt": [
        _m("KVKK Aydınlatma Metni", "sayfa", "kvkk"),
        _m("Çerez Politikası", "sayfa", "cerez-politikasi"),
    ],
}

# ── Blog ────────────────────────────────────────────────────────────────────

BLOG_KATEGORILERI = [
    {"ad": "Sağlık Okuryazarlığı", "slug": "saglik-okuryazarligi", "sira": 0},
    {"ad": "Eczane Yönetimi", "slug": "eczane-yonetimi", "sira": 1},
    {"ad": "Duyurular", "slug": "duyurular", "sira": 2},
]

_YAZI_1 = """
<p>Bir reçete eczaneye ulaştığında, ilaçların hazırlanması, sistem kontrolleri ve provizyon işlemleri birkaç dakika sürebilir. Bu süre eczane ekibi için yoğun bir çalışma anıdır; banko önünde bekleyen kişi için ise çoğu zaman pasif geçen bir zamandır.</p>
<h2>Bekleme süresi neden önemli?</h2>
<p>Bekleme anı, kişinin dikkatinin eczane ortamında olduğu nadir zamanlardan biridir. Kişi zaten bir sağlık hizmeti almak için oradadır ve eczacısına güvenmektedir. Ancak çoğu zaman yorgunluk, uyku düzeni veya sindirim gibi yaşam kalitesini etkileyen konuları dile getirmez; ya aklına gelmez ya da eczacının yoğun olduğunu düşünür.</p>
<h2>Sessiz müşteri ve kaçan danışmanlık fırsatı</h2>
<p>Eczacılar, ihtiyacını ifade etmeyen “sessiz müşteri”yi iyi tanır. Bu kişiler için kısa bir soru bile, eczacıyla daha verimli bir görüşmenin kapısını aralayabilir. Sorun, bu soruyu sormanın yoğun saatlerde her zaman mümkün olmamasıdır.</p>
<h2>Bekleme anını değerlendirmenin sade bir yolu</h2>
<p>e-isa, bu kısa süreyi yapılandırılmış bir ön hazırlığa dönüştürmek için tasarlandı. Kişi, kiosk ekranında 2-4 kısa soruyu yanıtlar; sistem yanıtları bir ihtiyaç kategorisiyle eşleştirir ve sonucu QR kod veya fiş ile eczacıya iletir.</p>
<ul>
<li>e-isa teşhis koymaz ve tedavi önermez.</li>
<li>Marka değil, ihtiyaç kategorisi sunar.</li>
<li>Son değerlendirme ve öneri her zaman eczacıya aittir.</li>
</ul>
<h2>Eczane açısından olası kazanımlar</h2>
<p>Ön hazırlıkla gelen kişiyle yapılan görüşme daha kısa ve odaklı olabilir. Tamamlayıcı kategorilere dikkat çekilmesi, eczacının danışmanlık rolünü görünür kılar ve sepet ortalamasına katkı potansiyeli taşır. Bu etkinin büyüklüğü eczanenin konumuna, kişi profiline ve danışmanlık yaklaşımına göre değişir; bu nedenle doğru yöntem, sonuçları kendi eczanenizde ölçmektir.</p>
<p>Bekleme süresi tamamen ortadan kaldırılamaz; ancak daha anlamlı hâle getirilebilir.</p>
"""

_YAZI_2 = """
<p>“Dürtme” (nudge), davranış bilimlerinde kişinin seçim özgürlüğünü kısıtlamadan, karar ortamını daha anlaşılır hâle getirerek daha bilinçli tercihler yapmasını kolaylaştıran yaklaşımların genel adıdır. Kavram, davranışsal ekonomi alanındaki çalışmalarla yaygınlık kazanmıştır.</p>
<h2>Sağlık okuryazarlığı nedir?</h2>
<p>Sağlık okuryazarlığı; kişinin sağlıkla ilgili bilgiye ulaşabilmesi, bu bilgiyi anlayabilmesi, değerlendirebilmesi ve günlük yaşamında kullanabilmesi becerisidir. Karmaşık terimler, uzun metinler ve zaman baskısı bu beceriyi zorlaştırabilir.</p>
<h2>Dürtme yaklaşımı burada nasıl devreye girer?</h2>
<p>İyi tasarlanmış bir dürtme, kişiye “ne yapması gerektiğini” söylemez; düşünmesi gereken soruyu doğru zamanda ve sade bir dille önüne koyar. Eczane ortamında bu, örneğin şu şekilde görünebilir:</p>
<ul>
<li>Uzun bir anket yerine birkaç kısa ve anlaşılır soru,</li>
<li>Tıbbi terimler yerine günlük dil,</li>
<li>Seçenekler arasında baskı kurmayan, tarafsız bir sunum,</li>
<li>Sonucun bir karar değil, eczacıyla konuşulacak bir başlangıç noktası olarak verilmesi.</li>
</ul>
<h2>e-isa bu yaklaşımı nasıl uyguluyor?</h2>
<p>e-isa, bekleme sırasında kişiye yaşam kalitesiyle ilgili birkaç kısa soru sorar ve yanıtları bir ihtiyaç kategorisiyle ilişkilendirir. Amaç, kişinin kendi durumu hakkında farkındalık kazanması ve eczacısına daha doğru soruları sorabilmesidir.</p>
<p>Bu süreçte iki ilke korunur: e-isa teşhis veya tedavi önerisinde bulunmaz ve belirli bir markayı öne çıkarmaz. Kategoriye uygun ürünün olup olmadığına, kişiye neyin uygun olduğuna eczacı karar verir.</p>
<h2>Sınırları bilmek de yaklaşımın parçası</h2>
<p>Dürtme yaklaşımı bir sihirli değnek değildir; etkisi bağlama ve uygulamanın kalitesine bağlıdır. Bu yüzden içeriklerin sade, doğru ve etik ilkelere uygun olması, sonuçların ise sahada ölçülerek değerlendirilmesi gerekir.</p>
"""

_YAZI_3 = """
<p>e-isa’yı eczanenizde varsayımlarla değil, kendi verilerinizle değerlendirebilmeniz için 1 aylık ücretsiz pilot süreç sunuyoruz. Bu yazıda sürecin nasıl işlediğini adım adım özetliyoruz.</p>
<h2>1. Başvuru ve ön görüşme</h2>
<p>Sitedeki pilot başvuru formunu doldurduğunuzda ekibimiz sizinle iletişime geçer. Kısa bir görüşmede eczanenizin yerleşimini, yoğun saatleri ve beklentilerinizi konuşuruz.</p>
<h2>2. Kurulum</h2>
<p>Kompakt pilot ünite, banko akışını engellemeyecek en uygun noktaya kurulur. Kurulum ve yapılandırma ekibimiz tarafından yapılır; eczane ekibine ek iş yükü getirmemesi hedeflenir.</p>
<h2>3. Kısa eğitim</h2>
<p>Eczane ekibine kiosk akışı ve QR/fiş ile gelen ön incelemenin nasıl okunacağı hakkında kısa bir bilgilendirme yapılır. Unutmayın: e-isa yalnızca ihtiyaç kategorisi sunar, son değerlendirme her zaman eczacıdadır.</p>
<h2>4. 30 gün boyunca izleme</h2>
<p>Pilot süresince etkileşim sayıları ve kategori dağılımı gibi anonim veriler düzenli olarak sizinle paylaşılır. Saha ekibimiz süreç boyunca ulaşılabilir durumdadır.</p>
<h2>5. Birlikte değerlendirme</h2>
<p>Pilot sonunda sonuçları birlikte değerlendiririz. Devam etmek isteyip istemediğinize, eczanenizin verilerine bakarak siz karar verirsiniz. Pilot sürecin sonuçları, gelecekteki performans için bir garanti değil, eczanenize özgü bir gözlemdir.</p>
<p>Pilot süreç hakkında sorularınız için <a href="/iletisim">iletişim sayfamızdan</a> bize ulaşabilirsiniz.</p>
"""

BLOG_YAZILARI = [
    {
        "slug": "recete-bekleme-suresi-eczane-icin-neden-bir-firsat",
        "baslik": "Reçete bekleme süresi eczane için neden bir fırsat?",
        "ozet": "Reçetenin hazırlandığı birkaç dakika, doğru kurgulandığında eczacıyla daha odaklı bir görüşmenin başlangıcı olabilir.",
        "kategori": "eczane-yonetimi",
        "etiketler": ["eczane", "bekleme süresi", "danışmanlık"],
        "icerik_html": _YAZI_1,
        "gun_once": 12,
    },
    {
        "slug": "durtme-nudge-yaklasimi-saglik-okuryazarligina-nasil-katki-saglar",
        "baslik": "Dürtme (nudge) yaklaşımı sağlık okuryazarlığına nasıl katkı sağlar?",
        "ozet": "Seçim özgürlüğünü kısıtlamadan doğru soruyu doğru anda sormak: dürtme yaklaşımı ve eczane ortamındaki karşılığı.",
        "kategori": "saglik-okuryazarligi",
        "etiketler": ["sağlık okuryazarlığı", "nudge", "davranış bilimi"],
        "icerik_html": _YAZI_2,
        "gun_once": 6,
    },
    {
        "slug": "e-isa-1-aylik-ucretsiz-pilot-sureci-nasil-isler",
        "baslik": "e-isa 1 aylık ücretsiz pilot süreci nasıl işler?",
        "ozet": "Başvurudan kuruluma, 30 günlük izlemeden ortak değerlendirmeye kadar pilot sürecin adımları.",
        "kategori": "duyurular",
        "etiketler": ["pilot", "duyuru"],
        "icerik_html": _YAZI_3,
        "gun_once": 2,
    },
]

BLOG_YAZAR = "e-isa Ekibi"
