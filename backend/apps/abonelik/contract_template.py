"""Eczane İş Ortaklığı ve Dijital Platform Kullanım Sözleşmesi — matbu şablon.

Metin, kaynak Word belgesiyle BİREBİR aynıdır; yalnızca ilgili alanlar (taraf
bilgileri, bedel, tarih) otomatik doldurulur. Yorum/kısaltma yapılmaz.

`render_sozlesme_html(sozlesme)` tam HTML döndürür. Dijital onay sonrası bu çıktı
`Sozlesme.onayli_sozlesme_metni`'ne dondurulur (immutable snapshot).
"""
from __future__ import annotations

import html
from decimal import Decimal


def _tl(v) -> str:
    try:
        d = Decimal(str(v or 0))
    except Exception:
        d = Decimal("0")
    return f"{d:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _esc(v) -> str:
    return html.escape(str(v if v is not None else ""))


def _pct(v) -> str:
    try:
        d = Decimal(str(v or 0)).quantize(Decimal("0.01"))
    except Exception:
        d = Decimal("0.00")
    s = f"{d:.2f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def render_sozlesme_html(sozlesme) -> str:
    """Sözleşme verisini birebir 22 maddelik metne yerleştirip tam HTML döndürür."""
    ec = sozlesme.eczane
    eczane_ad = _esc(getattr(ec, "ad", "") or getattr(ec, "name", ""))
    eczane_adres = _esc(getattr(ec, "adres", "") or getattr(ec, "address", ""))
    vergi_no = _esc(getattr(ec, "vergi_no", ""))

    # İş sağlayan bilgileri merkezi Şirket Tanımı modülünden al. Profil henüz
    # doldurulmadıysa mevcut sözleşme çıktısıyla geriye dönük uyumlu kal.
    try:
        from apps.sirket.models import SirketProfili
        sirket = SirketProfili.objects.first()
    except Exception:
        sirket = None
    sirket_unvan = _esc(getattr(sirket, "ticari_unvan", "") or "e-İSA Yazılım A.Ş.")
    sirket_adres = _esc(getattr(sirket, "adres", "") or "Kayseri / Türkiye")
    sirket_ilce = _esc(getattr(sirket, "ilce", ""))
    sirket_il = _esc(getattr(sirket, "il", ""))
    sirket_adres_tam = sirket_adres
    if sirket_ilce or sirket_il:
        sirket_adres_tam += " / " + " / ".join(filter(None, (sirket_ilce, sirket_il)))
    sirket_vergi = _esc(" / ".join(filter(None, (
        getattr(sirket, "vergi_dairesi", ""), getattr(sirket, "vergi_numarasi", "")
    ))))

    aylik = _tl(sozlesme.aylik_kullanim_bedeli)
    odeme_gun = sozlesme.baslangic_tarihi.day if sozlesme.baslangic_tarihi else 1
    duzenleme = sozlesme.baslangic_tarihi.strftime("%d/%m/%Y") if sozlesme.baslangic_tarihi else "[Gün/Ay/Yıl]"

    aktivasyon_orani = "25"
    try:
        from .services import aktif_fiyat

        _f = aktif_fiyat()
        aylik_bedel = Decimal(str(sozlesme.aylik_kullanim_bedeli or 0))
        if _f and _f.acma_kapama_bedeli and aylik_bedel > 0:
            aktivasyon_orani = _pct((Decimal(str(_f.acma_kapama_bedeli)) * Decimal("100")) / aylik_bedel)
    except Exception:
        pass

    return f"""
<div class="sz-contract">
<p style="text-align:center">e-isa</p>
<h1 style="text-align:center">ECZANE İŞ ORTAKLIĞI VE DİJİTAL PLATFORM KULLANIM SÖZLEŞMESİ</h1>

<h2>MADDE 1 – TARAFLAR</h2>
<p>İŞ SAĞLAYAN: {sirket_unvan}<br>
Adres: {sirket_adres_tam}<br>
Vergi Dairesi / No: {sirket_vergi}</p>
<p>İŞ ORTAĞI : {eczane_ad}<br>
Adres: {eczane_adres}<br>
Vergi Dairesi / No: {vergi_no}</p>

<h2>MADDE 2 - SÖZLEŞMENİN KONUSU</h2>
<p>İşbu sözleşmenin konusu;</p>
<p>Eczane’nin e-isa eczane iş ortaklığı ve dijital platform kullanım yayın ağına katılımı, e-isa tarafından geliştirilen yapay zekâ destekli dijital platformun kullanımına ilişkin esaslar ile tarafların hak, yükümlülük ve sorumluluklarının düzenlenmesidir. Bu sözleşme herhangi bir taşınır mal kiralama sözleşmesi niteliğinde olmayıp; dijital platform hizmeti, yayın altyapısı, yazılım hizmeti ve iş ortaklığı esasları çerçevesinde düzenlenmiştir.</p>
<p>Yürürlük ve Süre; İşbu sözleşme, taraflarca imzalandığı tarihte yürürlüğe girer. Bununla birlikte; sözleşme süresi, hizmet taahhütleri, ücretlendirme periyodu ve cihaza ilişkin tüm mali/hukuki yükümlülükler, söz konusu cihazın eczaneye fiilen teslim edilip kurulumunun eksiksiz tamamlandığı tarihten itibaren başlar.</p>

<h2>MADDE 3 – PLATFORMUN TANIMI</h2>
<p>e-isa; eczanelerde konumlandırılan dijital yayın terminalleri, merkezi yayın yönetim sistemi, yapay zekâ destekli kullanıcı deneyimi, eczacı iletişim ekranları, QR tabanlı yönlendirme sistemleri ve diğer dijital iletişim modüllerinden oluşan bütünleşik bir eczane iş ortaklığı ve dijital kullanım platformudur.</p>
<p>Platform; Uzaktan yönetilebilir, Yazılım güncellenebilir, Yeni modüller eklenebilir, Yapay zekâ algoritmaları geliştirilebilir, Yeni hizmetler sisteme dahil edilebilir, Bu geliştirmeler sözleşmenin ihlali olarak değerlendirilemez.</p>

<h2>MADDE 4 – İŞ ORTAKLIĞININ NİTELİĞİ</h2>
<p>İşbu sözleşme herhangi bir kiosk, ekran veya cihaz kiralama sözleşmesi olmadığını taraflar kabul ve beyan ederler. Eczane; e-isa Platformunun iş ortağı olarak sisteme katılmaktadır.</p>
<p>e-isa ise; platformun işletilmesi, yayınların yönetimi, sponsor ilişkilerinin yürütülmesi, teknik altyapının işletilmesi, yapay zekâ platformunun geliştirilmesi, kampanya yönetimi ve dijital yayın hizmetlerinin sağlanmasından sorumludur.</p>

<h2>MADDE 5 – PLATFORM KULLANIMI</h2>
<p>e-isa; Eczane’nin kullanımına platforma erişim sağlayan dijital yayın terminalini tahsis eder.</p>
<p>Platformun kullanımı kapsamında; yapay zekâ destekli danışmanlık hizmetleri, dijital yayın hizmetleri, merkezi içerik yönetimi, uzaktan yazılım güncellemeleri, teknik destek, performans geliştirmeleri, güvenlik güncellemeleri sunulabilir.</p>
<p>Taraflarca kararlaştırılacak mali şartlar, ayrıca düzenlenecek ticari protokol veya ek belgeler ile belirlenebilir.</p>

<h2>MADDE 6 – e-isa’NIN YÜKÜMLÜLÜKLERİ</h2>
<p>e-isa; Platformun sürekliliğini sağlamak, Yazılımı güncel tutmak, Teknik destek vermek, Dijital yayınları yönetmek, Sponsor kampanyalarını planlamak, Merkezi yayın sistemini işletmek, Donanımın bakım ve güncellemelerini yapmak, Platformun güvenliğini sağlamak için gerekli özeni gösterecektir.</p>

<h2>MADDE 7 – ECZANENİN YÜKÜMLÜLÜKLERİ</h2>
<p>Eczane; Platform terminali için uygun alan tahsis etmeyi, Elektrik bağlantısını sağlamayı, İnternet erişimini mümkün olduğu ölçüde kesintisiz bulundurmayı, Cihaza zarar vermemeyi, Platform üzerinde izinsiz işlem yapmamayı, Yetkisiz kişilerin cihaza müdahale etmesine izin vermemeyi kabul eder. Eczaneye; işbu sözleşme süresi boyunca tahsis edilen dijital yayın terminallerinin mülkiyeti ile içinde kayıtlı olan bilgiler, kodlar, şifreler ve yazılımlar üzerindeki eser sahipliğinden doğan tüm mali ve manevi haklar münhasıran e-isa'ya ait olup, eczane'ye, yalnızca SÖZLEŞME süresi boyunca SÖZLEŞME'nin amacına uygun olarak dijital yayın terminallerinin kullanma hakkı tahsis edilmektedir. Bu kapsamda eczane tarafından, dijital yayın terminallerinin kendisinin ya da içinde yer alan bilgilerin, yazılımların vs her ne surette olursa olsun tahrifi, değiştirilmesi, işlenmesi, çoğaltılması, yayılması, temsili, işaret, ses, data ve/veya görüntü nakline yarayan araçlarla umuma iletimi yasaklanmıştır. Bu yasağı ihlal eden Eczane'nin dijital yayın terminalleri kapatılır.</p>

<h2>MADDE 8 – YAYIN YÖNETİMİ</h2>
<p>Platformda yayınlanacak içeriklerin; belirlenmesi, planlanması, yayın sırası, yayın süresi, sponsor seçimi, kampanya yönetimi, tamamen e-isa’nın yetki ve sorumluluğundadır. Eczane, teknik veya hukuki zorunluluklar dışında yayın içeriklerine müdahale edemez ve etmeyeceğini kabul beyan ve taahhüt eder. Eczane yayın içeriğinin e-isa tarafından uygun hale getirilmesi için gerekli tüm bilgileri, belgeleri ve çalışma şekillerini e-isa’ya bildirmekle yükümlüdür. E-isa yayın içeriğinin daha etkin hale getirilmesi için eczaneden gerekli bilgi ve belgeleri talep edebilir.</p>

<h2>MADDE 9 – TEKNOLOJİK GELİŞİM VE GÜNCELLEMELER</h2>
<p>e-isa; Platformun gelişimi kapsamında; yeni yazılım modülleri, yapay zekâ özellikleri, kullanıcı arayüzleri, raporlama sistemleri, ekran tasarımları, donanım güncellemeleri, yeni dijital hizmetler, üzerinde değişiklik yapabilir.</p>
<p>Bu değişiklikler sözleşmenin esaslı unsurlarında değişiklik oluşturmadığı sürece Eczane tarafından ayrıca onaya tabi değildir.</p>

<h2>MADDE 10 – FİKRİ VE SINAİ MÜLKİYET HAKLARI</h2>
<p>Platforma ait; yazılım, tasarım, algoritmalar, yapay zekâ modelleri, arayüzler, ticari sırlar, markalar, logolar, kaynak kodları, veritabanları ve diğer tüm fikri mülkiyet hakları münhasıran e-isa’ya aittir. Eczane, bunları çoğaltamaz, değiştiremez, üçüncü kişilere kullandıramaz.</p>

<h2>MADDE 11 - KULLANIM YERİ VE SÜRESİ</h2>
<p>Kullanım Yeri: {eczane_ad} - {eczane_adres}</p>
<p>Eczane, dijital yayın terminalini eczane içerisinde, hastaların ve müşterilerin güvenle ulaşabileceği, cihazın devrilme veya elektrik çarpması riski taşımayacağı korunaklı bir alana kurmakla yükümlüdür. Eczaneye uygun dijital yayın terminali kurulduktan sonra İsteğe bağlı olan veya olmayan cihaz değişikliklerin de cihaza ilişkin tüm idari yükümlülükler (IMEI numarası kaydı vb.) Eczane'nin sorumluluğundadır. Cihazların teknik parametrelerinde değişiklik veya standartlara aykırı eklenti ve bağlantı yapılması ve/veya cihazların virüs yayması sonucu şebekede oluşabilecek her türlü erişim, zarar ve ziyandan eczane sorumludur. Bu hallerde e-isa, eczane'yi bilgilendirmek suretiyle eczane'nin dijital yayın platformunu kapatabilir.</p>
<p>Deneme Süresi: Sözleşmenin yürürlüğe girdiği tarihten itibaren ilk 14 gün deneme süresidir. Taraflar bu 14 gün süre içinde, herhangi bir gerekçe göstermeksizin ve hiçbir cezai şart, tazminat veya ek bedel ödemeksizin sözleşmeyi tek taraflı olarak feshedebilir. Fesih durumunda eczane sadece cihazı kullandığı günlerin yazılım ve kullanım bedelini ödemekle yükümlüdür.</p>

<h2>MADDE 12 – E-İSA KULLANIM BEDELİ VE ÖDEME ŞARTLARI</h2>
<p>12.1. Yapay Zekâ ve Yazılım Kullanım Bedeli: {aylik} TL + KDV<br>
Ödeme Günü: Her ayın {odeme_gun}. günü. Ödeme Şekli: e-isa’nin [Banka Adı] hesabına [IBAN No] ile yatırılacaktır. Herhangi bir faturaya ait alacağın tahsili, Eczane'nin önceki dönemlere ait ödenmemiş borçlarının ifa edildiği anlamına gelmez. E-isa, eczane tarafından yapılacak ödemeleri öncelikle geçmiş dönem borçlarına ilişkin faize ve geçmiş dönem borçlarına mahsup etme hakkını saklı tutmaktadır. Borcunu ifa etmeyen eczanelerle ilgili yasal işlemler başlatmadan makul bir süre öncesinde, çeşitli mecralar aracılığı ile eczanenin borcunu ifa etmesi için uyarır, aksi takdirde borcun yasal yollarla tahsil edileceğini bilgilendirir. Ödeme yapılmaması veya ödemelerin geç yapılması durumunda e-isa hizmeti durdurabilir ve aktivasyonu kapatabilir. Ödeme gününden itibaren Eczacı 5 gün içinde ödeme yapmazsa e-isa hizmeti hiçbir bildirimde bulunmadan durdurma hakkına sahiptir. Hizmeti durdurulan Eczane hizmetten faydalanmaya devam etmek isterse, geciken ücretlerin tamamı ödenmek durumunda olup ayrıca aylık kullanım bedelinin %{aktivasyon_orani}'i oranında aktivasyon bedeli ödemek zorundadır. Cihazın işleme kapatılmasından anlaşılması gereken ise; cihaz açık olup sponsorların zararı oluşmaması gösterimler devam edecek ancak yazılım ve eczanenin kullanımı kısıtlanacaktır. Bu durumda eczane cihaz tam kapasite çalışıyormuş gibi ücretlendirilmeye devam edilecektir.</p>
<p>12.2. Eczane Katkı Payı – KDV Dahil %10 ve Hak Ediş Bedeli: Eczanenin kioks ekranlarında yer alan kurumsal bilgilendirme veya sponsorluklarından sağlanan bütçenin %10’nu Eczanenin dijital yazılım, donanım bakım ve lisans katkı payı olarak mahsup edilir ve eczaneye aktarılır. e-isa bu katkı payını sponsor bedelini tahsil ettiği ayın son günü eczaneye aktarır. Kurumsal bilgilendirme ve Sponsor bedeli tahsil edilemezse eczane katkı payı bedelini e-isa’dan talep edemeyecektir. Eczanenin katkı payına hak kazanması için sistemin sürekli açık kalması ve sponsor görsellerinin anlaşma şartlarının sağlayacak ölçüde kesintisiz yayınlanmasına bağlıdır. Eczanenin kusurundan kaynaklı sponsor görsellerinin yayınlanamamasından kaynaklı durumda katkı payı oluşmaz. Eczane elde edilecek katkı payı bedellerine ilişkin fatura düzenlemek zorundadır. E-isa sponsor bedelini tahsil edememesi durumunda eczane e-isa’ya fatura düzenlenmiş ise fatura iade edilecek ve herhangi bir katkı payı doğmayacaktır. Sözleşmenin feshi veya cihazın kullanılamaz hale gelmesi durumunda eczanenin cihaz taşıma bedeli ve cihaz bedeli ödemesi gerektiği durumlarda depozitonun yetersiz kalması haklinde e-isa, eczanenin tahsili yapılmış katkı payı bedelinden mahsup yaparak artan katkı payı olması durumunda eczaneye ödeme yapacaktır.</p>
<p>12.3. Kullanıma Tekrar Açılma Bedeli: Ödeme yapılmaması veya sözleşmeye aykırılık nedeniyle kullanımın durdurulması halinde, şartlar yerine getirildiğinde sistemin tekrar aktif edilmesi durumunda aktivasyon öncesi eczane 'Kullanıma Tekrar Açılma Bedeli' ödeyecektir. Bu bedel e-isa tarafından belirlenecek olup aylık kullanım bedelinin %30 oranını geçmeyecektir. Kullanıma tekrar açma bedelinin ödenmesi ve eksikliklerin giderilmesi sonrası cihaz yeniden kullanıma açılacaktır. Kullanıma kapalı olan cihazlarda sponsorların zararının oluşmaması için sponsor gösterimleri yayınlanmaya devam edecek ve cihaz kullanıma açık kabul edilerek Yapay Zekâ ve Yazılım Kullanım Bedeli eczane tarafından ödenecektir.</p>

<h2>MADDE 13 – DİJİTAL YAYIN TERMİNALİNİN MÜLKİYET DEVRİ VE BAĞLILIK ŞARTLARI</h2>
<p>Eczane’nin talebi ve e-isa’nın yazılı onayı ile, mülkiyeti e-isa’ya ait olan dijital yayın terminalinin (donanımın) satışı Eczane’ye gerçekleştirilebilir. Donanım satış bedeli, ödeme şartları ve cihaza ilişkin diğer detaylar, taraflarca ayrıca akdedilecek yazılı bir Ek Protokol ile belirlenir. Bu satışın gerçekleşmesi halinde aşağıdaki özel şartlar geçerli olacaktır:</p>
<p>13.1 Yayın Akışı ve Ağdan Çıkamazlık Taahhüdü: Dijital yayın terminalinin mülkiyeti Eczane'ye geçse dahi, Eczane işbu sözleşme süresi boyunca terminali e-isa dijital yayın ağından ve yayın akışından çıkaramaz. Cihaz, e-isa'nın merkezi yayın yönetim sistemine bağlı kalmak ve e-isa tarafından gönderilen içerikleri kesintisiz olarak yayınlamak zorundadır.</p>
<p>13.2 Amacı Dışında Kullanım Yasağı: Eczane, mülkiyeti kendisine geçen dijital yayın terminalini hiçbir surette e-isa platformunun amacı dışında bir amaçla kullanamaz, kendi reklam/tanıtım içerikleri dahil olmak üzere sisteme harici müdahalede bulunamaz, televizyon, standart ekran, kişisel bilgisayar vb. amaçlarla çalıştıramaz. Cihazın kullanım amacı münhasıran e-isa sistemidir.</p>
<p>13.3 Yazılım ve Fikri Mülkiyet Sınırı: Satışla yalnızca ilgili donanımın fiziki mülkiyeti Eczane’ye geçecek olup; cihazın içinde yer alan, e-isa tarafından geliştirilen veya gelecekte geliştirilecek olan yapay zekâ modelleri, kaynak kodları, yazılımlar, şifreler, ara yüzler ve fikri/sınai hakların tamamı münhasıran e-isa’ya ait kalmaya devam edecektir.</p>
<p>13.4 Sözleşmenin Aynen Devamı: İşbu sözleşmede düzenlenen; e-isa Dijital Platform Kullanım Bedeli (Madde 12.1), yayın yönetimi ve içerik kontrolü yetkileri (Madde 8), e-isa'nın tek taraflı güncelleme hakları (Madde 9) ile tarafların diğer tüm hak, yükümlülük ve sorumlulukları donanım satışından etkilenmeksizin, hiçbir değişikliğe uğramadan aynen devam edecektir.</p>
<p>13.5 Garanti Şartları: Satışı yapılan donanımın mülkiyet devri tarihindeki yasal üretici/distribütör garantisi, süresi bitene kadar Eczane lehine aynen korunur. Ancak, kullanıcı hatası, kırılma, sıvı teması, voltaj problemleri veya e-isa onayı dışındaki yetkisiz fiziki/yazılımsal müdahaleler garanti kapsamı dışındadır. Bu tür durumlarda teknik servis ve parça değişim hizmetleri e-isa tarafından ayrıca ücretlendirilir.</p>
<p>13.6 İhlal Halinde Cezai Şart ve Kapatma: Eczane'nin cihazı yayın akışından çıkarması, ağ bağlantısını kasıtlı kesmesi veya amacı dışında kullanması durumunda e-isa, Madde 12.1'de düzenlenen cihaz kısıtlama protokolünü uygulama ve eczaneyi tam kapasite ücretlendirmeye devam etme hakkına sahiptir. Ayrıca e-isa'nın bu ihlal nedeniyle uğrayacağı sponsor ve reklam kayıplarının tazmini Eczane'nin sorumluluğundadır.</p>

<h2>MADDE 14- SMS BİLDİRİMLERİ VE TİCARİ ELEKTRONİK İLETİLER</h2>
<p>14.1. Operasyonel ve Sistem Bildirimleri: e-isa, İş Ortağı’na (Eczane) platformun işleyişi, yapay zekâ güncellemeleri, teknik aksaklıklar, sipariş/bakım süreçleri ve sözleşmesel yükümlülüklerle ilgili bilgilendirici SMS, anlık bildirim (push notification) ve e-posta gönderimlerini, herhangi bir pazarlama onayı şartı aramaksızın doğrudan yapabilir.</p>
<p>14.2. Pazarlama ve Kampanya İletileri: e-isa tarafından Eczane’ye yönelik yapılacak tanıtım, kampanya, promosyon ve sponsorluk içerikli ticari elektronik iletilerin gönderimi; 6563 sayılı Elektronik Ticaretin Düzenlenmesi Hakkında Kanun (ETK) ve İleti Yönetim Sistemi (İYS) mevzuatına uygun olarak gerçekleştirilir. Eczane, dilediği zaman bu ticari iletileri almayı reddetme hakkına sahiptir.</p>
<p>14.3. Son Kullanıcı (Hasta/Müşteri) SMS Gönderimleri ve KVKK Sorumluluğu: Platform veya bağlı dijital terminaller (kiosk, QR yönlendirme vb.) üzerinden, Eczane’nin talebiyle veya Eczane adına son kullanıcılara (hastalara/müşterilere) SMS gönderilmesi durumunda;</p>
<p style="padding-left:2rem">14.3.1. Bu gönderimlerin 6698 sayılı Kişisel Verilerin Korunması Kanunu (KVKK) ve ETK mevzuatına uygun olarak yapılmasından, son kullanıcılardan gerekli "Açık Rıza" ve "Ticari İleti Onayı"nın alınmasından bizzat Eczane sorumludur.</p>
<p style="padding-left:2rem">14.3.2. Eczane tarafından platforma yüklenen veya sistem üzerinden toplanan son kullanıcı rehber/iletişim verilerinin hukuka uygunluğundan e-isa sorumlu tutulamaz. İzinsiz veya mevzuata aykırı SMS gönderimleri nedeniyle doğabilecek tüm idari para cezaları, hukuki ve cezai sorumluluk münhasıran Eczane’ye aittir.</p>
<p>14.4. SMS Gönderim ve Altyapı Maliyetleri: Platform ve bağlı tüm modüller üzerinden son kullanıcılara (hastalara/müşterilere) gönderilecek olan her türlü SMS, doğrulama kodu, bilgilendirme ve yönlendirme iletilerinin kontör, tarife ve altyapı maliyetleri münhasıran Eczane'ye aittir. Eczane, sistemde tanımlı güncel SMS tarifesi üzerinden kullanım bedellerini peşinen ödemeyi veya e-isa'nın bu bedelleri Eczane'nin mevcut hak edişlerinden (Madde 12.2) doğrudan mahsup etmeye yetkili olduğunu kabul, beyan ve taahhüt eder. SMS bakiyesinin tükenmesi durumunda e-isa gönderimleri durdurma hakkına sahiptir.</p>

<h2>MADDE 15 - MEVZUAT, SAĞLIK HUKUKU VE KVKK UYUMU</h2>
<p>15.1. KVKK Sorumluluğu: dijital yayın terminali üzerinden eczane müşterilerine/hastalara ait T.C. Kimlik Numarası, reçete bilgisi, sağlık verisi veya kredi kartı gibi kişisel ve özel nitelikli kişisel veriler işleniyorsa; bu verilerin güvenliği, saklanması ve işlenmesi süreçlerindeki yasal sorumluluk (KVKK uyumu, aydınlatma metni ve açık rıza süreçleri) eczacıya aittir. Cihaz yazılımı güncel siber güvenlik protokollerine uygun olmalıdır.</p>
<p>15.2. Eczacılık Mevzuatı: dijital yayın terminali cihazının eczane içindeki faaliyeti, 6197 sayılı Eczacılar ve Eczaneler Hakkında Kanun ve ilgili yönetmeliklere aykırılık teşkil edemez. dijital yayın terminali üzerinden ilaç satışı, özendirici reklam veya mevzuata aykırı yönlendirme yapılamaz. Mevzuata aykırılık nedeniyle doğacak idari para cezalarından kusurlu olan taraf sorumludur.</p>
<p>15.3. Sponsor Firma Sorumluluğu: Sponsor firmaların sağladığı reklam, tanıtım, kampanya, ürün veya hizmet içeriklerinin ilgili sağlık mevzuatına uygunluğundan sponsor firmaların sorumludur. Sponsor sorumluluğu, sponsorlarla yapılan sözleşmelerde iş ve işleyişin durumuna göre daha detaylı şekilde kararlaştırılacaktır. Sponsor firmaların sağladığı reklam, tanıtım, kampanya, ürün veya hizmet içeriklerinin ilgili sağlık mevzuatına uygunluğu için gerekli izinlerin ve onayların alınması, içeriklerinin hukuk ve reklam yasağına dikkat edilerek özenle hazırlanması ve aykırı içerikler olması halinde doğabilecek zarar veya oluşabilecek yaptırımlardan sponsor firma sorumlu olacaktır. Eczacıya sponsorlu içerik hakkında bilgilendirme e-postası gönderilerek, bilgisi dahilinde yayına başlanılacaktır.</p>

<h2>MADDE 16 - HİJYEN VE FİZİKSEL KORUMA</h2>
<p>dijital yayın terminali cihazının günlük temizliği ve hijyeni (özellikle dokunmatik ekran temizliği) halk sağlığı açısından Eczane tarafından düzenli olarak yapılacaktır. Eczane, temizlik esnasında cihaza zarar vermeyecek sıvı temizleyiciler kullanacağını kabul eder. cihazın temizlenmesi sırasında temizlik kaynaklı arızaların olması durumunda eczacı, tamiri mümkünse tamir bedelinin tamamını, tamiri mümkün değilse cihaz bedelinin tamamını e-isa’ya ödemeyi kabul, beyan ve taahhüt eder.</p>

<h2>MADDE 17- DEPOZİTO VE CEZAİ ŞART (Yeni Madde)</h2>
<p>17.1. Depozito: Eczane, cihazın teslimi esnasında hasar, zayi veya ödenmemiş iş ortaklığı bedellerine güvence oluşturmak üzere [Rakam] TL depozito bedeli ödeyecektir. Bu bedel, sözleşme sonunda cihaz eksiksiz, hasarsız ve çalışır durumda teslim edildiğinde eczane’ye aynen iade edilir. Deneme süresi içi fesihlerde de hasar yoksa depozito aynen iade edilir.</p>
<p>17.2. Cezai Şart: 14 günlük deneme süresi geçtikten sonra; taraflardan birinin haklı bir neden olmaksızın ve yasal bildirim sürelerine uymaksızın sözleşmeyi tek taraflı feshetmesi halinde, fesheden taraf diğer tarafa [Örn: 2 Aylık İş Ortaklığı varsa kalan sözleşme süresi olan 10 Aylık iş ortaklığı Bedelini, 10 aylık iş ortaklığı varsa kalan sözleşme süresi olan 2 aylık iş ortaklığı bedelini] özetle kalan sözleşme süresi kadar iş ortaklığı bedelini cezai şart ödemeyi gayrikabili rücu kabul ve taahhüt eder. Ancak cezai şart tutarı 2 aylık iş ortaklığı bedelinden az, 1 yıllık iş ortaklığı bedelinden fazla olamaz. 14 günlük deneme süresinde cayma veya fesih halinde kurulum, teslim/taşıma, söküm ve geri taşıma/lojistik maliyetler eczane tarafından karşılanacaktır.</p>

<h2>MADDE 18 - BAKIM, ONARIM VE ARIZA</h2>
<p>Eczane, cihazda oluşacak herhangi bir arızayı derhal e-isa'ya bildirecektir. Kullanıcı ve eczaneye gelen müşteri-hasta-tüketici veya yakınlarının veya eczaneye gelen toptancı- mümessil gibi cihazı kullananların hatasından kaynaklanmayan veya cihazdaki teknik yıpranmalar nedeniyle oluşacak arızaların tamir masrafları e-isa’ya ait olup, eczane hatasından kaynaklanan hasar ve masraflar eczane’den tahsil edilir. Eczacı; kendisi, çalışanları, müşteriler, hastalar, hasta yakınları, toptancılar, mümessiller ve cihazı kullanan diğer kişilerin hata, ihmal veya kusurundan kaynaklanan zarar ve masraflardan sorumlu olduğunu ve çıkacak tüm masrafları karşılamayı kabul, beyan ve taahhüt eder. cihazda oluşacak zararların tespit edilmesi için cihazların kamera açısı dahilinde konumlandırılması ve kamera kayıtlarının saklanması eczanenin sorumluluğundadır. Kamera kayıtlarına ulaşılamaması durumunda tespit yapılmasının imkansız olması durumlarda tüm bakım, onarım ve arıza masrafları eczane tarafından karşılanacağını kabul, beyan ve taahhüt eder.</p>
<p>18.1 - Bakım Ve Eczane Çalışma Saatleri: e-isa tarafından yapılacak olan teknik servis, yazılım güncellemesi veya yerinde bakım hizmetleri, eczane işleyişini ve hasta mahremiyetini aksatmayacak şekilde, tercihen eczane yoğunluğunun az olduğu saatlerde veya tarafların ortaklaşa belirleyeceği zaman diliminde yapılacaktır.</p>
<p>18.2. Cihazların Donanımsal Garantisi; Cihazların donanımsal olarak zimmet sözleşmesinde belirtilen süre dahilinde garanti kapsamında olacaktır. Garanti süresi cihazın kurulduğu ve çalışır vaziyette teslim edildiği tarihte başlar. Garanti sadece mekanik ve fiziksel parçaları kapsar; virüs, işletim sistemi çökmesi veya yazılım uyuşmazlıkları, kullanıcı kaynaklı arızalar kapsam dışıdır. Garanti kapsamında ki arızalar için Tüketici Kanunu'na uygun olarak 20 iş günü azami tamir süresi ve ücretsiz onarım sağlanacaktır. Yayın ağının durmaması ve sistem işleyişinde aksama olmaması adına, tamir süresinin uzaması ihtimaline karşı opsiyonel bir yedek cihaz (ikame) sağlanacaktır. Cihazlara yetkili servis dışında müdahale edilmesi durumunda cihazın garantisini iptal olacağı ve cihazın garanti dışı bakım, onarım ve tamiri yapılacağı açıkça kabul edilmiştir. Ayrıca her hafta cumartesi günü akşam saatlerinden pazartesi günü mesai başlangıç saatine kadar olan sürede cihazların güncelleme ve yazılımsal işlemlerinin yapılabilmesi adına kapatılmaması gerekmektedir. Ayrıca anlık güncellemelerin yapılabilmesi için cihazlar işyerinin kapalı olduğu saatlerde de hiçbir şekilde kapatılmayacaktır. Cihazların kapatılması halinde güncelleme ve eksik işlemlerin yapılmaması durumunda eczane mesai saatinde güncelleme yapılmak zorunda kalınacaktır.</p>

<h2>MADDE 19 - GİZLİLİK VE VERİ KORUMA</h2>
<p>19.1. Gizli Bilgi Tanımı: Taraflar, işbu sözleşme kapsamında birbirleri hakkında öğrendikleri her türlü ticari, mali, teknik, yazılımsal bilgiyi, yapay zekâ algoritmalarını, kaynak kodlarını, hasta/müşteri verilerini, eczane ciro veya işlem bilgilerini "Gizli Bilgi" olarak kabul ederler.</p>
<p>19.2. Gizlilik Yükümlülüğü: Taraflar, karşı tarafa ait gizli bilgileri sözleşme süresince ve sözleşme herhangi bir nedenle sona erdikten sonra 5 (beş) yıl boyunca üçüncü şahıslarla paylaşmamayı, ifşa etmemeyi ve amacı dışında kullanmamayı taahhüt ederler.</p>
<p>19.3. KVKK Uyumluluğu: Taraflar, sözleşmenin ifası sırasında elde ettikleri kişisel verileri 6698 sayılı Kişisel Verilerin Korunması Kanunu’na (KVKK) uygun olarak işlemek, saklamak ve korumakla yükümlüdür. Eczane, sisteme aktardığı hasta/müşteri verilerinin hukuka uygun elde edildiğini garanti eder.</p>

<h2>MADDE 20 - SÖZLEŞMENİN FESHİ</h2>
<p>20.1. Haklı Nedenle Derhal Fesih: Taraflardan birinin sözleşme yükümlülüklerini ihlal etmesi ve ihlalin giderilmesi için karşı taraftan gelen yazılı ihtara rağmen 7 (yedi) iş günü içinde bu ihlali gidermemesi halinde, sözleşme haklı nedenle derhal feshedilebilir.</p>
<p>20.2. Ödememe Nedeniyle Fesih: Eczane’nin Madde 12.1 uyarınca yapması gereken ödemeleri geciktirmesi ve hizmetin durdurulmasından itibaren 15 (on beş) gün içinde borcun faiziyle birlikte ödenmemesi halinde, e-isa sözleşmeyi tek taraflı ve tazminatsız olarak feshedebilir.</p>
<p>20.3. Fesih Sonrası Yükümlülükler: Sözleşmenin herhangi bir nedenle sona ermesi veya feshi halinde; Eczane, mülkiyeti e-isa’ya ait olan dijital yayın terminallerini, cihazları ve aparatları çalışır durumda, hasarsız ve eksiksiz olarak 7 (yedi) iş günü içinde e-isa’ya iade etmekle yükümlüdür. Cihazların iadesine kadar geçen sürede Eczane'nin kullanım bedeli sorumluluğu devam eder.</p>

<h2>MADDE 21– MÜCBİR SEBEPLER</h2>
<p>21.1. Tanım: Deprem, yangın, sel gibi doğal afetler, savaş, ayaklanma, genel grev, salgın hastalıklar ile hükümet veya resmi makamların platformun çalışmasını engelleyen kararları mücbir sebep olarak kabul edilir.</p>
<p>21.2. Uygulama: Mücbir sebep süresince tarafların edimleri askıya alınır. Mücbir sebebin 30 (otuz) günden uzun sürmesi halinde taraflar sözleşmeyi tazminatsız olarak feshetme hakkına sahiptir.</p>

<h2>MADDE 22 – UYUŞMAZLIKLAR</h2>
<p>İşbu sözleşmenin uygulanmasından doğabilecek uyuşmazlıkların çözümünde Kayseri Mahkemeleri ve İcra Daireleri yetkilidir. İşbu sözleşme 22(yirmi iki) maddeden oluşmuş olup, {duzenleme} tarihinde 2 (iki) nüsha olarak düzenlenmiş ve taraflarca okunarak imza altına alınmıştır.</p>

<table class="sz-table" style="border:none"><tbody>
<tr><td style="border:none"><strong>İŞ SAĞLAYAN</strong></td><td style="border:none"><strong>İŞ ORTAĞI</strong></td></tr>
<tr><td style="border:none">E-İSA</td><td style="border:none">ECZANE</td></tr>
</tbody></table>
</div>
"""


def onay_blogu_html(sozlesme) -> str:
    """Dijital onay bilgisini içeren imza bloğu (çıktıda görünür)."""
    if sozlesme.imza_tipi == "ISLAK":
        return (
            "<div class='sz-imza'>"
            "<p class='sz-imza-not'>Bu sözleşme ıslak imza ile akdedilmiştir.</p>"
            "</div>"
        )
    if sozlesme.eczaci_onay_tarihi:
        onay = sozlesme.eczaci_onay_tarihi.strftime("%d.%m.%Y %H:%M")
        ip = sozlesme.eczaci_onay_ip or "—"
        return (
            "<div class='sz-imza sz-imza--onayli'>"
            "<p class='sz-onay-baslik'>✓ BU SÖZLEŞME DİJİTAL OLARAK ONAYLANMIŞTIR</p>"
            f"<p>Eczacı Dijital Onay Tarihi: <strong>{onay}</strong></p>"
            f"<p>Onay IP Adresi: {_esc(ip)}</p>"
            "<p class='sz-imza-not'>5070 sayılı Elektronik İmza Kanunu ve 6098 sayılı TBK "
            "kapsamında, taraf iş bu sözleşmeyi okuyup elektronik ortamda kabul ve onay vermiştir.</p>"
            "</div>"
        )
    return (
        "<div class='sz-imza'>"
        "<p class='sz-onay-bekliyor'>Bu sözleşme henüz dijital olarak onaylanmamıştır.</p>"
        "</div>"
    )
