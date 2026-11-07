/**
 * Web Sitesi (eisa.com.tr CMS) yardım dokümanı.
 * Her konu: ekran içi "Yardım" çekmecesinde (YardimButonu) ve tam yardım sayfasında (Yardim.vue) gösterilir.
 *
 * Konu alanları:
 *  key       — anchor / çekmece anahtarı
 *  baslik, ikon (Font Awesome), ozet
 *  adimlar   — numaralı akış (opsiyonel)
 *  maddeler  — [{ baslik, metin }] "ne işe yarar" listesi (opsiyonel)
 *  ipuclari  — kısa ipuçları (opsiyonel)
 *  rota      — ilgili ekrana kısayol (opsiyonel)
 */

export const YARDIM_KONULARI = [
  {
    key: 'genel',
    baslik: 'Nasıl çalışır?',
    ikon: 'fa-compass',
    ozet:
      'eisa.com.tr tamamen bu modülden yönetilir. Sayfalar bloklardan oluşur; yaptığınız değişiklikler önce taslak olarak kaydedilir, siz "Yayınla" diyene kadar ziyaretçiler eski hâli görür.',
    adimlar: [
      'Sayfalar ekranından düzenlemek istediğiniz sayfayı açın.',
      'Soldaki listeden bir blok seçin, sağdaki formdan metin, görsel ve butonlarını değiştirin. Gerekirse yeni blok ekleyin veya blokları sürükleyerek sıralayın.',
      '"Taslağı Kaydet" ile çalışmanızı kaydedin (Ctrl+S). Bu adım siteyi değiştirmez.',
      '"Önizle" ile taslağı gerçek sitede, yalnızca sizin göreceğiniz şekilde açın ve kontrol edin.',
      'Her şey yolundaysa "Yayınla" deyin. Değişiklik birkaç saniye içinde eisa.com.tr\'de görünür.',
      'Bir hata fark ederseniz "Revizyonlar"dan önceki bir sürüme tek tıkla dönebilirsiniz.',
    ],
    ipuclari: [
      'Her Web Sitesi ekranının sağ üstünde, Yardım butonunun yanındaki "Önizle" siteyi yayınlanmamış taslaklarla birlikte açar; bu görünümü yalnızca siz görürsünüz.',
      'Taslak ile yayındaki sürüm farklıysa listede "Yayınlanmamış değişiklik" etiketi görünür.',
      'Önizleme bağlantısı güvenlik için 1 saat geçerlidir; süresi dolarsa "Önizle"ye yeniden basın.',
      'Aynı sayfayı iki kişi aynı anda düzenlerse, ikinci kaydeden uyarı alır; sayfayı yenileyip tekrar deneyin.',
    ],
  },
  {
    key: 'arama',
    baslik: 'Sitede ara',
    ikon: 'fa-magnifying-glass',
    ozet: 'Bir ifadeyi düzenlemek için sayfa sayfa gezmeniz gerekmez. Web Sitesi menüsündeki "Sitede ara" ile veya Ctrl+K (Mac: ⌘K) kısayoluyla eisa.com.tr\'nin tüm içeriğinde tek seferde arayın.',
    adimlar: [
      'Ctrl+K ile arama penceresini açın ve aradığınız ifadeyi yazın (en az 2 karakter).',
      'Sonuçlar sayfa, blog yazısı, menü ve site ayarlarına göre gruplanır; her sonuç ifadenin hangi blokta ve hangi alanda geçtiğini gösterir (ör. "Hero › Butonlar › 1. öğe › Etiket").',
      'Ok tuşlarıyla gezinip Enter\'a basın veya sonuca tıklayın.',
      'İlgili ekran açılır, alan vurgulanır ve aranan ifade seçili gelir; doğrudan düzenleyebilirsiniz.',
    ],
    maddeler: [
      { baslik: 'Neler aranır?', metin: 'Tek arama her şeyi tarar: sayfa blokları (başlık, metin, alt metin, buton, sayılar; iç içe listeler dahil), bölüm bağlantıları, sayfa başlığı ve SEO bilgileri, blog yazıları (içerik, özet, etiketler) ve kategorileri, menü öğeleri, site ayarları ve medya kütüphanesindeki görsel alternatif metinleri.' },
      { baslik: 'Taslak içerik', metin: 'Arama, düzenlediğiniz taslak hâlde yapılır. Yayınlanmamış değişiklikler de bulunur; gizli bloklar "gizli blok" etiketiyle gösterilir.' },
      { baslik: 'Akıllı eşleşme', metin: 'Büyük/küçük harf ve Türkçe karakter fark etmez: "saglik" yazınca "Sağlık" ve "SAĞLIK" da bulunur.' },
    ],
    ipuclari: ['Kaydetmediğiniz değişiklikler aramada görünmez; önce "Taslağı Kaydet" deyin.'],
  },  {
    key: 'sayfalar',
    baslik: 'Sayfalar',
    ikon: 'fa-file-lines',
    rota: '/admin/web-sitesi',
    ozet: 'Sitedeki tüm sayfaların listesi. Buradan sayfa açabilir, yeni sayfa oluşturabilir ve taslağı önizleyebilirsiniz.',
    maddeler: [
      { baslik: 'Yeni Sayfa', metin: 'Başlık ve adres (ör. "hizmetler" → eisa.com.tr/hizmetler) girerek boş bir sayfa oluşturur. Ardından editörde blok ekleyerek içeriği kurarsınız.' },
      { baslik: 'Durum', metin: '"Yayında" sayfalar sitede görünür. "Taslak" sayfalar yalnızca önizlemede görünür. "Yayınlanmamış değişiklik", taslağın yayındaki sürümden farklı olduğunu gösterir.' },
      { baslik: 'Önizle (göz ikonu)', metin: 'Sayfanın taslağını, yayınlamadan sitede yeni sekmede açar.' },
      { baslik: 'Düzenle (kalem ikonu)', metin: 'Sayfa editörünü açar. Satıra tıklamak da aynı işi yapar.' },
      { baslik: 'Sil', metin: 'Kilit ikonlu sistem sayfaları (Anasayfa, KVKK, Çerez Politikası) ve menüde kullanılan sayfalar silinemez.' },
    ],
  },
  {
    key: 'sayfa-editoru',
    baslik: 'Sayfa Editörü',
    ikon: 'fa-pen-ruler',
    ozet: 'Bir sayfanın bloklarını düzenlediğiniz ekran. Solda blok listesi, sağda seçili bloğun formu bulunur.',
    maddeler: [
      { baslik: 'Blok listesi (sol)', metin: 'Sayfadaki bölümler yukarıdan aşağıya bu sırayla gösterilir. Tutamaçtan sürükleyerek sıralayın; göz ikonuyla bloğu geçici olarak gizleyin, kopyala ile çoğaltın, çöp kutusuyla silin.' },
      { baslik: 'Blok ekle', metin: 'Hazır blok tiplerinden (Hero, Özellik Kartları, SSS, Başvuru Formu…) birini seçip sayfaya ekler.' },
      { baslik: 'Blok formu (sağ)', metin: 'Seçili bloğun alanları. Zorunlu alanlar * ile işaretlidir. Liste alanlarında (kartlar, sorular, adımlar) öğe ekleyip sıralayabilirsiniz.' },
      { baslik: 'Bağlantı kimliği (anchor)', metin: 'Menüden doğrudan bu bloğa gitmek için kullanılır. Ör. "sss" yazarsanız eisa.com.tr/#sss bağlantısı bu bloğa kaydırır.' },
      { baslik: 'Sayfa ve SEO ayarları', metin: 'Başlığın altındaki adrese tıklayın: sayfa başlığı, adresi, Google\'da görünen başlık/açıklama ve paylaşım görseli.' },
      { baslik: 'Taslağı Kaydet', metin: 'Değişiklikleri kaydeder ama siteyi değiştirmez. Kaydedilmemiş değişiklik varken sayfadan çıkmak isterseniz uyarı alırsınız.' },
      { baslik: 'Önizle', metin: 'Önce taslağı kaydeder, sonra sitenin önizleme modunu yeni sekmede açar. Sayfanın üstünde kırmızı "Önizleme modu" bandı görürsünüz; bu görünüm yalnızca sizdedir.' },
      { baslik: 'Yayınla', metin: 'Taslağı canlıya alır. İsterseniz kısa bir not yazın ("Fiyat tablosu güncellendi" gibi); not revizyon geçmişinde görünür.' },
      { baslik: 'Revizyonlar', metin: 'Her yayın bir revizyon olarak saklanır. Eski bir revizyonu seçip "Geri al" derseniz o sürüm hemen yeniden yayınlanır.' },
      { baslik: 'Yayından kaldır', metin: 'Sayfayı siteden kaldırır (ziyaretçiler "sayfa bulunamadı" görür); içerik silinmez, tekrar yayınlanabilir.' },
    ],
    ipuclari: ['Kaydetmek için Ctrl+S kısayolunu kullanabilirsiniz.', 'Hata alırsanız ilgili blok ve alan kırmızı ile işaretlenir.'],
  },
  {
    key: 'bloklar',
    baslik: 'Blok tipleri',
    ikon: 'fa-cubes',
    ozet:
      'Sayfalar aşağıdaki hazır bloklardan kurulur. Tasarım her blokta sabittir; siz yalnızca içeriği doldurursunuz, böylece site her zaman tutarlı görünür.',
    // Blok listesi Yardım sayfasında API'deki blok tiplerinden (ad + açıklama) otomatik doldurulur.
    blokListesi: true,
  },
  {
    key: 'menuler',
    baslik: 'Menüler',
    ikon: 'fa-bars-staggered',
    rota: '/admin/web-sitesi/menuler',
    ozet: 'Sitenin üst menüsü (header), alt bilgi menüsü (footer) ve en alttaki yasal bağlantılar buradan yönetilir.',
    maddeler: [
      { baslik: 'Header', metin: 'Sayfanın üstündeki ana menü. "CTA" işaretli öğe kırmızı buton olarak sağda gösterilir (ör. "1 Ay Ücretsiz Pilot").' },
      { baslik: 'Footer', metin: 'Her üst öğe bir sütundur, altındaki öğeler o sütunun bağlantılarıdır.' },
      { baslik: 'Footer alt', metin: 'En alttaki KVKK, Çerez Politikası gibi yasal bağlantılar.' },
      { baslik: 'Bağlantı türleri', metin: 'Sayfa: sitedeki bir sayfa. Bölüm: bir sayfadaki belirli blok (bağlantı kimliği ile). Blog: blog listesi. Dış bağlantı: başka bir site.' },
      { baslik: 'Sürükle-bırak', metin: 'Öğeleri sürükleyerek sıralayın; bir öğeyi diğerinin altına alt menü olarak taşıyabilirsiniz (en fazla 2 seviye).' },
    ],
    ipuclari: ['Değişiklikler "Kaydet" ile hemen yayına alınır.', 'Yayında olmayan bir sayfaya bağlanan menü öğesi sitede gizlenir.'],
  },
  {
    key: 'blog',
    baslik: 'Blog',
    ikon: 'fa-newspaper',
    rota: '/admin/web-sitesi/blog',
    ozet: 'Haber ve bilgilendirme yazıları. Yazılar eisa.com.tr/blog altında listelenir ve arama motorları için önemli bir kanaldır.',
    maddeler: [
      { baslik: 'Yazı editörü', metin: 'Başlık, özet, kapak görseli ve içerik. İçerikte başlık, liste, alıntı, bağlantı ve medya kütüphanesinden görsel kullanabilirsiniz.' },
      { baslik: 'Adres', metin: 'Başlıktan otomatik üretilir (Türkçe karakterler dönüştürülür); isterseniz değiştirebilirsiniz.' },
      { baslik: 'Durum ve yayın tarihi', metin: '"Yayında" + ileri bir tarih seçerseniz yazı o tarihte otomatik görünür (zamanlanmış yayın).' },
      { baslik: 'Kategoriler', metin: 'Yazıları gruplamak için. Ziyaretçiler blog sayfasında kategoriye göre filtreleyebilir.' },
      { baslik: 'Önizle', metin: 'Yazının taslağını yayınlamadan sitede açar.' },
    ],
  },
  {
    key: 'medya',
    baslik: 'Medya Kütüphanesi',
    ikon: 'fa-photo-film',
    rota: '/admin/web-sitesi/medya',
    ozet: 'Sitede kullanılan tüm görseller. Burada yüklediğiniz görselleri bloklarda, blog yazılarında ve paylaşım görsellerinde seçebilirsiniz.',
    maddeler: [
      { baslik: 'Yükleme', metin: 'Dosyaları sürükleyip bırakın veya seçin. JPEG, PNG, WebP, GIF ve AVIF desteklenir; en fazla 10 MB. Güvenlik nedeniyle SVG kabul edilmez.' },
      { baslik: 'Alternatif metin', metin: 'Görseli tarif eden kısa metin. Görme engelli ziyaretçiler ve arama motorları için önemlidir; mutlaka doldurun.' },
      { baslik: 'Silme', metin: 'Silinen görsel, kullanıldığı yerlerde artık gösterilmez. Silmeden önce kullanılmadığından emin olun.' },
    ],
    ipuclari: ['Büyük fotoğrafları yüklemeden önce 2000 px genişliği geçmeyecek şekilde küçültmek sitenin hızını artırır.'],
  },
  {
    key: 'basvurular',
    baslik: 'Başvurular',
    ikon: 'fa-inbox',
    rota: '/admin/web-sitesi/basvurular',
    ozet: 'Sitedeki formlardan (Pilot, Sponsorluk, İletişim) gelen başvurular. Menüdeki sayı yeni başvuruları gösterir.',
    maddeler: [
      { baslik: 'Durum takibi', metin: 'Yeni → İncelendi → İletişimde → Kapandı. Durumu güncelleyerek ekipçe takip edin.' },
      { baslik: 'Not ve atama', metin: 'Detay panelinde iç notlar yazabilir ve başvuruyu bir ekip arkadaşına atayabilirsiniz.' },
      { baslik: 'Excel', metin: 'Mevcut filtreyle listeyi Excel olarak indirir.' },
    ],
    ipuclari: ['Başvurular kişisel veri içerir (KVKK); işi biten kayıtları saklama süresi sonunda silin.'],
  },
  {
    key: 'ayarlar',
    baslik: 'Site Ayarları',
    ikon: 'fa-sliders',
    rota: '/admin/web-sitesi/ayarlar',
    ozet: 'Sitenin genelini etkileyen bilgiler: iletişim bilgileri, sosyal medya bağlantıları, footer metni ve varsayılan SEO ayarları.',
    maddeler: [
      { baslik: 'İletişim bilgileri', metin: 'E-posta, telefon, WhatsApp ve adres; footer\'da ve formların yanında gösterilir. Boş bırakılan alan sitede gizlenir.' },
      { baslik: 'SEO', metin: 'Sayfa kendi SEO başlığını tanımlamazsa kullanılan varsayılan açıklama ve paylaşım görseli. Başlık şablonundaki %s yerine sayfa başlığı gelir.' },
      { baslik: 'Sosyal bağlantılar', metin: 'LinkedIn, Instagram vb. footer\'daki ikonlar.' },
    ],
    ipuclari: ['Ayarlar kaydedildiği anda tüm sayfalarda güncellenir.'],
  },
  {
    key: 'sss',
    baslik: 'Sık karşılaşılan durumlar',
    ikon: 'fa-life-ring',
    maddeler: [
      { baslik: 'Değişikliğim sitede görünmüyor', metin: '"Taslağı Kaydet" siteyi değiştirmez; "Yayınla" demeniz gerekir. Yayınladıysanız sayfayı birkaç saniye sonra yenileyin.' },
      { baslik: 'Önizleme açılmıyor veya "geçersiz" diyor', metin: 'Önizleme bağlantısı 1 saat geçerlidir. Editörde "Önizle"ye yeniden basın. Tarayıcı açılır pencereyi engellediyse izin verin.' },
      { baslik: 'Önizleme modundan nasıl çıkarım?', metin: 'Sitenin üstündeki kırmızı bantta "Çık" bağlantısına tıklayın.' },
      { baslik: 'Sayfa silinemiyor', metin: 'Sistem sayfaları ve menüde bağlantısı olan sayfalar silinemez. Önce menüden kaldırın.' },
      { baslik: 'Kim neyi yapabilir?', metin: 'Editör rolü yalnızca Web Sitesi modülünü görür. Süper Admin tüm panele erişir. Editör kullanıcıları Kullanıcı Yönetimi\'nden oluşturulur.' },
    ],
  },
];

/** key → konu */
export const YARDIM = Object.fromEntries(YARDIM_KONULARI.map((k) => [k.key, k]));