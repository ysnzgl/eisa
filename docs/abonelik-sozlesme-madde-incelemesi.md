# Ana sözleşme Ek-1 ve Ek-2 madde incelemesi

İnceleme tarihi: 8 Kasım 2026  
İlişkili çalışma: [Abonelik ve sözleşme geçiş planı](abonelik-sozlesme-gecis-plani.md)

Bu inceleme iki Word belgesinin tamamını, sözleşmenin tarif ettiği süreçleri ve mevcut uygulamanın bunları ne ölçüde karşıladığını ele alır. Sonuç: belge doldurma, abonelik faturası, sponsor tahsilatı ve eczane katkı payı ayrı iş akışlarıdır. Mevcut uygulama bu akışların tamamını karşılamıyor. Özellikle fatura dönemi/vadesi, KDV'nin borca aktarılması, sponsor tahsilatı ve zorunlu bildirimler geliştirme gerektiriyor.

Kaynaklar:

- `C:\Users\YsnZgl\Downloads\e-isa_Eczane_Sozlesmesi_Ek1_Son.docx` — 26 maddelik ana sözleşme ve Ek-1 A–K.
- `C:\Users\YsnZgl\Downloads\e-isa_Zimmet_Tutanagi_Ek2.docx` — 8 bölümlük teslim ve kurulum tutanağı.

8 Kasım'da ana belgenin 359, Ek-2'nin 107 boş olmayan paragrafı tablo içleri dahil yeniden okundu. İncelenen ana XML'de izlenen ekleme/silme yoktu. Sayfa düzeni veya Word çıktısının görsel doğrulaması bu metin/kod incelemesinin konusu değildir. Kaynak Word belgeleri değiştirilmedi.

Buradaki “metne göre” değerlendirmeleri verilen sözleşmenin açıklamasıdır; kanunların güncel yorumu veya hükümlerin hukuki geçerliliği hakkında sonuç değildir. “Mevcut” tespitleri kaynak kod incelemesine dayanır; canlı sistem, veritabanı ve gerçek banka tahsilatı kontrol edilmedi. Test çalıştırılmadı, uygulama kodu değiştirilmedi.

## 1. Son kullanıcı kararları

- Sözleşme başlangıcı aynı zamanda uygulamadaki ticari aktivasyon tarihidir. Hizmet ve sözleşmesel sayaçlar bu tarihten yürür. Kullanım ücretinde varsa sözleşmedeki öteleme uygulanır.
- Islak imzalı dosya aynı gün veya daha sonra yüklenebilir; eksik dosya hizmet/faturayı bekletmez. İmza ve yükleme zamanı ayrı kayıttır; sahte imza olayı üretilmez.
- Bölge ve Sponsorluk Tarifeleri bağımsız yönetim ekranlarıdır. Sözleşme yalnız eczanenin bölgesini ve oluşturma takviminde geçerli ilgili tarifeleri alır.
- Yeni kampanya bir sponsorluk tarifesiyle ilişkilendirilmeden kaydedilemez.
- Sabit sözleşme maddeleri korunur. Dinamik alanlar, cihaz/taksit satırları ve ilgili bölge/tarife tabloları değişken üretilir.
- Ek-2 Bölüm 4, 5 ve 7 personelin elle işaretlemesi için aynı kalır.
- Depozito, öteleme bedeli ve “öneri/teyit” değerleri bu aşamada karara bağlanmayacak; mevcut ifadeleri korunacak. Bunlar tekrar karar istenen aktif gündem değildir.
- İlk abonelik faturası sözleşme başlangıcı + abonelik ötelemesi; ilk cihaz faturası başlangıç + cihaz ödeme ötelemesi tarihinde oluşur. Öteleme 0 ise ilgili kalem sözleşmeyle başlangıçta faturalanır. Öteleme, yalnız vadeyi değil ilk kesimi taşır; iki kalem bağımsızdır. Sonraki kullanım faturaları ödeme başlangıcına bağlı aylık dönemlerdedir. Son ödeme kesimden 7 iş günü sonra; bildirim ve hatırlatmalar kayıtlı vadeye bağlıdır.
- Abonelik ötelemesi nedeniyle kullanım faturası kesilmeyen dönemde katkı payı doğmaz ve ödenmez; sonradan ödeme için birikmez. Cihaz faturası tek başına bu engeli kaldırmaz. Öteleme sonrasında yalnız uygun günler katkıya girer; bu dönemin sponsor tahsilatı geç gelse de geçmiş öteleme günleri hakediş kazanmaz.
- Ceza genel fiyat tanımındaki katsayıdan değil sözleşme sürümündeki kalan ücretli süre, 2–12 aylık sınır ve cezasız fesih istisnalarından hesaplanır. Sabitlenen TL tutarı değil hesap kuralıdır.
- Mevcut verilerden otomatik alan doldurma planlanır; eksik bilgiler uydurulmaz. Tahsis ve ertelenen kararlar [ekip soruları dosyasında](abonelik-sozlesme-ekip-sorulari.md) saklanır. Bu kararlar yalnız planı günceller; uygulama değişikliği yapılmaz.

## 2. Tahsis bu sözleşmede ne anlama geliyor

### 2.1 Temel anlamı

14.3 ve Ek-2 6.2'ye göre cihaz e-isa'nın malı olarak eczanede bırakılır; eczane sözleşme süresince kullanır ve sözleşme sona erince iade eder. Aylık platform ücretinin ödenmesi cihazı satın alma veya mülkiyet devri sayılmaz. Sözleşme 2.2 ve 4.1'de ilişkiyi taşınır mal kiralaması olarak tanımlamadığını özellikle söyler.

Dolayısıyla uygulamadaki mevcut **Kiralık** seçeneği bu metindeki tahsise kendiliğinden eşit değildir. Yeni edinim seçimi **Tahsis** olmalı; varsa ayrı bedelin neyi ifade ettiği ayrıca tutulmalıdır.

| Konu | Peşin satış | Vadeli satış | Tahsis |
|---|---|---|---|
| Donanım mülkiyeti | 14.2'de belirtilen teslim/kurulum ve tutanak imzasıyla eczaneye geçer. | Son taksit eksiksiz ödenene kadar e-isa'da kalır. | Sözleşme boyunca e-isa'da kalır; otomatik devir öngörülmemiştir. |
| Aylık platform bedeli | Devam eder. | Devam eder; cihaz taksitinden ayrıdır. | Devam eder; tahsis bedelinden ayrıdır. |
| Cihaz bedeli | Tek seferlik satış bedeli. | Ek-1 B'deki taksit takvimi. | Ek-1 B'de “Tahsis (bedel: …)” alanı var; ödeme sıklığı açıkça tanımlanmamış. |
| Teknik yıpranma | Garanti içinde garanti kapsamında, sonrasında eczane sorumluluğunda. | Satışa ilişkin aynı kural. | 19.1'e göre e-isa sorumluluğunda. |
| Kullanıcı kusuru/hasar | 17 ve 19 kapsamındaki sorumluluklar devam eder. | Aynı. | Aynı; tahsis cihazın her türlü hasarını e-isa'nın üstlenmesi anlamına gelmez. |
| Sona ermede cihaz | Mülkiyeti geçmiş cihaz için 21.5'te e-isa'nın yazılım/içeriği kaldırma hakkı düzenlenmiş. | Mülkiyeti hâlâ e-isa'daysa iade hükümleri gündeme gelir. | Çalışır, eksiksiz ve hasarsız iade; Ek-1 I'ye göre 7 iş günü. |
| Yayın ağı ve yazılım | Sözleşme süresince bağlılık devam eder; yazılımın mülkiyeti geçmez. | Aynı. | Aynı. |

### 2.2 Bedelle ilgili çıkarılabilecek ve çıkarılamayacak sonuç

Ek-1 B'deki tahsis bedeli boşluğu, tahsisin zorunlu olarak bedelsiz olduğunu söylemez. Ancak aynı alan tahsisin aylık kira olduğu, bedelin aylık tekrar edeceği veya sonunda cihazın eczaneye kalacağı anlamına da gelmez. Önceki plandaki “aylık tahsis bedeli” seçeneği sözleşmede açıkça bulunan bir kural değil, olası tasarım seçeneğiydi; bu incelemeyle bu ayrım düzeltildi.

Üç tutar ayrılmalıdır:

1. **Platform kullanım bedeli:** Ek-1 C'deki aylık yazılım/hizmet bedeli. Öteleme dışında satış veya tahsiste işler.
2. **Varsa tahsis bedeli:** Ek-1 B'de kararlaştırılan tutar. Sıklığı/ödeme takvimi belirlenmeden aylık kira gibi faturalanmamalıdır.
3. **Donanım değeri:** 17.2 ve Ek-1 I'deki hasar/kalan değer hesabında kullanılacak cihaz bedeli. Tahsis bedeli sıfır olsa bile donanım değeri sıfır sayılamaz.

### 2.3 Tahsisin operasyonel sonuçları

- Seri numarasıyla hangi cihazın hangi eczaneye tahsis edildiği bilinmeli; teslim ve iade geçmişi tutulmalı.
- 19.1'deki teknik yıpranma sorumluluğu, yalnız garanti tarihine bakılarak eczaneye yüklenmemeli. Arıza nedeni ve sorumlu taraf ayrı kaydedilmeli.
- 21.5'e göre e-isa mülkiyetindeki cihaz iade edilene kadar kullanım bedeli sorumluluğu sürüyor. Mevcut `IPTAL` durumuna geçince normal faturayı kesme yaklaşımı tek başına bunu karşılamıyor.
- Ek-1 I'deki kalan değer formülü `cihaz bedeli × (kalan ay / 24)`. Yenileme/öteleme ve kalan ayın hangi süreye ait olduğu uygulamada ayrıca netleştirilmeli; tahsis ücretinden veya sınırsız uzayan sözleşme süresinden rastgele türetilmemeli.
- Fiziksel cihazın demo döneminden kalması tahsis/satış seçimini kendiliğinden belirlemez; yeni sözleşmede gerçek edinim modeli seçilir.
- Ek-2 Bölüm 4'te mülkiyet/zimmet etiketi kontrolü bulunur. Personel edinim modeline uygun gerçek durumu elle işaretler; sistem tüm cihazlarda otomatik “yapıldı” demez.

## 3. Ana sözleşmenin madde madde incelemesi

### Madde 1 — İş sağlayan

Şirket unvanı, adres ve vergi bilgileri tanımlanıyor. Şirket profili altyapısı var. Kullanıcı tarafından değişken olduğu kabul edilen alanlar bu kayıttan alınabilir; üretilen belge o anki bilgilerle sabitlenmelidir. Şirket profilinin daha sonra değişmesi eski belgeyi değiştirmemelidir.

### Madde 2 — Konu, tanımlar, yürürlük ve belge önceliği

2.1–2.2 hizmetin konusu ve edinim ayrımını tanımlar. 2.3 onayla kuruluşu ve aktivasyonla süre/mali yükümlülüklerin başlangıcını ayırır. Kullanıcının operasyon kararı gereği uygulamada başlangıç ve aktivasyon eşittir; dosyanın sunucuya yüklenme anı bu olayların yerine geçmez.

2.4'te sponsorluk bedeli **fiilen tahsil edilen KDV dahil tutar** olarak tanımlanır; teklif/fatura tutarı tek başına bu tutar değildir. Aktif Cihaz-Gün, öteleme ve ödeme başlangıcı mali modellerde ayrı anlam taşır. 2.5 parasal/süre parametrelerinde Ek-1'i esas alır; sözleşme öncesi teklif yalnız Ek-1'e aktarılan ticari koşullar ölçüsünde belgeye girer. 2.6 gelir garantisi vermez; panel tahmini geliri kesin hakediş gibi göstermemelidir.

### Madde 3 — Platform

Kiosk, merkezi yayın, eczacı paneli, QR ve geliştirilebilir yazılım tanımlanıyor. Bunların temel teknik altyapısı mevcut. Fiili hizmet kalitesi ve yapay zekâya ilişkin ticari iddiaların karşılandığı yalnız modül bulunmasından çıkarılamaz; bu inceleme performans veya sağlık çıktısı doğrulaması değildir.

### Madde 4 — İş ortaklığının niteliği

Bağımsız işletme ilişkisi ve temsil yetkisinin bulunmaması düzenleniyor. Ek tahsilat veya otomasyon kuralı üretmez. Cihaz tahsisinin mevcut “kiralık” ürün etiketiyle neden birebir eşlenemeyeceği açısından önemlidir.

### Madde 5 — Elektronik onay ve delil kayıtları

5.1–5.3 elektronik onay, IP/cihaz/yöntem bilgileri, yetkili sağlayıcı zaman damgası ve kayıt güvencelerini tarif eder. Kodda tarih/IP ve onay anındaki HTML var; bunlar belirtilen sağlayıcı entegrasyonunun tamamı değildir. Şimdiki süreç ıslak imza; mevcut dijital seçenek korunur, OTP/e-imza ve sağlayıcı kanıtı olmadan yapılmış gibi gösterilmez. Islak yükleme, elektronik imza işlemi sayılarak kaydedilmez.

### Madde 6 — Platform kullanımı

Cihaz satılabilir veya tahsis edilebilir; mali şartlar Ek-1'de belirlenir. Yazılım, yayın, güncelleme ve teknik destek altyapısı var. Yeni belgede edinim ve fiyat satırları gerçek sözleşme verilerinden üretilmeli; model bilgisi serbest açıklamaya bırakılmamalıdır.

### Madde 7 — e-isa'nın yükümlülükleri

Süreklilik, güvenlik/güncelleme, teknik destek, yayın planlama, içerik denetimi ve **katkı payını panelden bildirme/ödeme** yükümlülükleri birlikte düzenleniyor. Yayın ve destek altyapısı mevcut; sponsor tahsilatı, hakediş hesap bildirimi ve eczaneye ödeme akışı görünmüyor. Bu son üçü belge şablonu işinin ötesinde açık geliştirme kapsamıdır.

### Madde 8 — Eczanenin yükümlülükleri

8.1–8.2 yer, elektrik, internet, koruma ve müdahale yasaklarını; 8.3 bilgilendirerek kısıtlama/kapatmayı düzenler. 8.4 uygun termal kâğıdın eczanece teminini ve kâğıt yokluğunun kullanım bedelini etkilememesini söyler. Fiziksel kontroller Ek-2'nin elle doldurulan bölümlerinde kalır. İhlal nedeniyle kısıtlama uygulanırsa sebep/bildirim/başlangıç kaydı gerekir; sıradan kâğıt bitmesi ücretsiz dönem oluşturmaz.

### Madde 9 — Yayın yönetimi ve çalışma sürekliliği

9.1 yayın ve sponsor seçimini e-isa'ya verir; mevcut merkezi yönetim buna temel sağlar. 9.2 bilgi/belge talebini, 9.3 eczanenin aykırılık bildirimini ve inceleme sonucunda kaldırma/düzeltmeyi düzenler. Destek talebi altyapısı kullanılabilir; ilgili içerik ve inceleme süresiyle bağlanması gerekir. Ek-1 I'deki 2 iş günü “öneri” ifadesi şimdilik korunur.

9.4 cihazın 24/7 açık/internete bağlı olmasını ister. Eczane kusuru dışındaki elektrik/internet kesintisinin yalnız Aktif Cihaz-Gün'e yansıması ve başka yaptırım doğurmaması belirtilir. Bu nedenle her offline olayı otomatik kusur/ceza olarak işlenemez; kesinti günü, neden ve değerlendirme gerekir.

### Madde 10 — Geliştirmeler ve esaslı unsurlar

10.1 teknik geliştirmelere izin verir. 10.2 kullanım bedeli, katkı oranı, süre ve içerik güvencelerini esaslı unsurlar olarak ayırır. Adminin kayıt düzenlemesi geçmiş imzalı şartları kendiliğinden değiştirmemeli; fiyat güncelleme ve bölge değişikliği gibi metindeki özel süreçler kendi kurallarıyla yürümelidir.

### Madde 11 — Fikri haklar

11.1–11.2 yazılım ve fikri hakların e-isa'da kalmasını, kullanım hakkının sözleşme amacı/süresiyle sınırlı olmasını düzenler. Donanım satışı yazılım mülkiyetini devretmez. Fesihte donanım sahipliğiyle yazılım erişimi ayrı durumlar olmalıdır.

### Madde 12 — Kullanım yeri ve süre

12.1 adres değişikliğini e-isa onayına bağlar; kiosk eczane atama geçmişi var, adres değişikliği/onayıyla belge ve bölge etkisi ilişkilendirilmeli. 12.2 Ek-1 D'deki 24 ay + öteleme, 60 gün önceden bildirim ve bildirim yoksa 12 ay yenilemeye bağlanır. Kod manuel uzatma sunuyor; otomatik yenileme/yenilememe bildirimi süreci yok. 12.3–12.4 fiziksel güvenlik ve idari yükümlülüklerdir; saha kontrolleri ve gerekirse bilgilendirilmiş kısıtlama gerekir.

### Madde 13 — Kullanım bedeli, katkı payı ve öteleme

| Alt madde | Metindeki işlem | Uygulamada gereken |
|---|---|---|
| 13.1 | Kullanım bedeli ödeme başlangıcından işler; gecikme faizi ve masraf/faiz/en eski borca mahsup sırası var. | Aylık dönem, vergi, vade, bakiye, faiz ve tahsilat dağıtımı. |
| 13.1/a | Vade sonrası opsiyon dolarsa panel/SMS/e-posta bilgilendirmesiyle hizmet durdurulabilir. | Ödeme vadesi ve durdurma opsiyonu ayrı; bildirim/kısıt kaydı. |
| 13.1/b–c | Sponsor yayını sürer, eczane kullanımı kısıtlanır, kullanım bedeli devam eder; dönüşte gecikmiş borç/faiz ve açma bedeli ödenir. | Kiosk yayınıyla kullanıcı erişiminin ayrı yönetimi; yeniden açma koşulu. |
| 13.2/a–c | Fiili KDV dahil tahsilattan %15; eczane ve bölge hesabı ayrı, kısmi tahsilat kadar hakediş, ötelemede hakediş yok. | Sponsor tahsilatı ve dönem/kapsam bağlantısı; cihaz-gün ve uygunluk. |
| 13.2/d | Tahsilattan 10 iş günü içinde panel hesap bildirimi; bildirimden itiraz süresi. | Takvim/süre takibi, kalıcı bildirim, itiraz ve hesap sürümü. |
| 13.2/e | Eczane e-isa'ya KDV dahil fatura keser; e-isa tebliğden 15 gün içinde öder. | Eczaneden gelen fatura, tebliğ tarihi ve e-isa'nın çıkış ödemesi. |
| 13.2/f | Eczane borçları katkı payından mahsup edilebilir; fesihte artan pay ödenir. | Brüt hakediş, mahsup edilen borç kalemleri, net ödeme ve mükerrer tahsilat engeli. |
| 13.3 | Yeniden açılma bedeli kullanım ücretinin %30'unu aşamaz; ödeme/eksikliklerin giderilmesi sonrasında açılır. | Tavan kontrolü ve tahsilat önkoşulu; yalnız yeni fatura açmak yetmez. |
| 13.4 | İlk 12 ay sabit; sonra endeks, aşan artışta bölgesel tarife ve 15 gün önceden yazılı bildirim/itirazla cezasız fesih. | Fiyat sürümü, yürürlük ve bildirim; itiraz süresinin metindeki eksik parametresi hukuki gündemde. |
| 13.5 | Aksi belirtilmedikçe tutarlar KDV hariç. | Fatura ve ödeme hesabına seçilen KDV ve varsa tevkifat aktarılır. |
| 13.6/a | Öteleme talebi ve e-isa onayı Ek-1'e işlenir, azami 6 ay; sonraki değişiklik ayrı onaya bağlı. | Talep/onay kaydı ve sürümlü değişiklik. |
| 13.6/b–c | Öteleme aktivasyondan başlar, sonrasındaki günden ücret işler; süre sözleşmeye eklenir, toplu birikmiş ücret değildir. | Tarih hesabı; ertelenen aylara sonradan kullanım faturası yığılmaz. |
| 13.6/d–e | Hizmet ve sponsor yayını sürer; katkı doğmaz, birikmez, dağıtım paydasına dahil edilmez. | Erişim açık; hakediş uygunluğu ayrı. |
| 13.6/f | Cihaz taksitleri açıkça ayrıca ötelenmedikçe kendi takviminde ödenir. | Abonelik ve cihaz ötelemesi bağımsız. Öteleme bedeli kararı ertelendi. |
| 13.6/g | Öteleme sabit fiyatın 12 aylık sayacını uzatmaz. | Sayacı sözleşme başlangıcından çalıştırma. |
| 13.6/h | Öteleme içindeki fesihte kalan ücretli süre esas alınır. | Ceza hesabında ücretsiz ve ücretli dönemleri ayırma. |
| 13.6/i | Belirli ihlallerde ihtar süresi sonrası öteleme erken bitirilebilir; ek süre fiilen kullanılan ötelemedir. | İhlal/ihtar/sona erme tarihi ve yeni tarih hesabı. |

Mevcut kod ilk altyapıyı sağlıyor; bu bütünün tamamını karşılamıyor. Ayrıntılı faturalandırma karşılaştırması 6. bölümde, sponsor tahsilatı ve bildirimler 7. bölümde.

### Madde 14 — Edinim, mülkiyet ve yayın ağı

14.1–14.3 peşin/vadeli satış ve tahsisi ayırır. 14.2'de son taksidin ödenmesi, yazılı ihtar ve 7 iş günü sonunda bakiye taksitlerin muaccel olması ayrıca izlenmelidir; **son faturanın kesilmesi son ödemenin yapılması değildir**. Sicil işlemi gibi dış işlemler varsa belge/referans olarak saklanabilir; otomatik yapıldığı varsayılmaz.

14.4–14.7 donanım eczaneye geçse de sözleşme boyunca yayın ağına bağlılığı, amaç sınırlarını, yazılımın e-isa'da kalmasını ve kullanım ücretinin devamını söyler. 14.8 garanti/kullanıcı kusuru ayrımı; 14.9 kasıtlı ağdan çıkarma halinde kısıtlama, ücret devamı ve belgelenebilir sponsor kaybını düzenler. Her ağ kesintisine otomatik sponsor kaybı borcu yazılmamalıdır. Tahsis ayrıntıları 2. bölümde.

### Madde 15 — SMS ve ileti izinleri

15.1 operasyonel, 15.2 pazarlama iletilerini ayırır; pazarlama reddi ayrıca yönetilmelidir. 15.3 son kullanıcı SMS'i yapılırsa gerekli izinler ve iletişim verilerinin sorumluluğunu düzenler. 15.4 SMS tarifesi, peşin bakiye/katkı payından mahsup ve bakiye biterse gönderimi durdurma imkânı getirir. SMS özelliğinin varlığı bu maddelerden varsayılamaz; mevcut kodda tam SMS tarife/bakiye/izin akışı görülmedi. Eczane ile son kullanıcı iletişimleri ayrı tutulmalı; son kullanıcı iletişim bilgileri yanıtlarla eşleştirilmemeli.

### Madde 16 — İçerik ve veri ilkeleri

16.1 arayüzde bilgilendirme/gerekli rıza süreçleri ile kimliksiz soru-cevap akışını tarif eder. 16.2 sponsor yayınını kullanıcının yanıtlarından bağımsız kılar. Mevcut cihaz/takvim bazlı yayın buna temel sağlar; dış rapor ve ileride yapılacak hedefleme bu sınırı korumalıdır.

16.3–16.4 için içerik kontrolünün ayrı kaydı gerekir: marka önerisi yerine etken/kategori ve eczacıya yönlendirme; eczacıya sponsor ürünü satma/stoklama zorunluluğu olmaması; cihazda beşeri tıbbi ürün adı/görseli/bilgisi yasağı; sabit yasal uyarı; fiyat/indirim çağrılarının ve profesyonel/ürün görsel birlikteliklerinin belirtilen sınırlara uyması; teşhis/hekim kimliği iddiası olmaması. Her medya yüklemesi teknik olarak başarılı diye içeriğin bu koşullara uygunluğu sağlanmış sayılmaz.

16.5 sponsorun içerik izin/sorumluluğunu belirtirken **her sponsor içeriğinin yayından önce eczaneye bildirilmesini** de ister. Kampanya oluşturma ve medya değişikliği bu bildirime bağlanmalıdır. Yayın bildirimi eczacının ayrıca sponsor kabulü vermesi anlamına gelmez.

### Madde 17 — Hijyen ve hasar

17.1 temizlik eczaneye aittir. 17.2 temizlik kaynaklı hasarda tamir masrafı veya tamir mümkün değilse cihaz kalan değeri düzenlenir. Servis kaydında neden, onarım mümkünlüğü, bedel ve sorumlu taraf bulunmalıdır. Fatura tahsis bedeli ile donanım kalan değeri birbirinin yerine kullanılmamalıdır.

### Madde 18 — Depozito ve cezai şart

18.1 depozito varsa başlangıca kadar ödeme, bitişte/iade veya cihazın tamamen ödenmesinde mahsup sonrası iade düzenler. Kullanıcı bu parametrenin kararını erteledi; belge metni korunur.

18.2 kalan kullanım bedelleri üzerinden 2–12 aylık sınırla ceza; 18.3 belirli fesihlerde ceza istisnası tanımlar. Mevcut kalan ay × katsayı yaklaşımı buna eşit değildir. Ceza koşulu yalnız “iptal” düğmesinden çıkarılamaz; gerekçe ve tarih gerekir.

### Madde 19 — Bakım, arıza ve garanti

19.1 kusur kaynaklı masraf ile teknik yıpranmayı ve tahsis/satış sorumluluğunu ayırır. 19.2 garanti süresi, kapsam dışı sebepler, 20 iş günü azami ücretsiz onarım ve opsiyonel ikameyi düzenler. 19.3 bakımın uygun saatlerde yapılmasını ve haftalık güncelleme dönemini; 19.4 kamera görüş alanını ve 30 gün kayıt saklamayı eczane tarafında düzenler.

Genel destek kaydı mevcut; garanti/servis başlangıcı, sorumluluk, süre ve ikame cihaz geçmişi eksik. Sözleşmedeki kamera şartı platformun kamera kayıtlarını merkezi olarak toplaması gerektiği anlamına gelmez. Kullanıcı kararıyla uygulamada sözleşmesel başlangıç aynı tarihtir; garanti ay sayısı yine doldurulmalıdır.

### Madde 20 — Gizlilik ve bölgesel analiz

20.1–20.3 ticari/mali/teknik bilgilerin gizliliği ve 10 yıllık gizlilik yükümlülüğünü düzenler. Bu ifade tüm ham verilerin 10 yıl tutulması gerektiği anlamına gelmez; erişim ve saklama tasarımı ayrı ele alınır.

20.4/a–h ve 20.5 şu ürün gereksinimlerini doğurur:

- Dışa yalnız il/ilçe/bölge düzeyinde toplulaştırılmış analiz çıkar; tek yanıt, oturum ve QR içeriği sponsorla paylaşılmaz.
- Son kullanıcı adı, telefon/e-posta, kullanıcı cihazı/ağ tanımlayıcısı toplanmaz; iletişim modülündeki veri yanıtlarla eşleştirilmez. Mevcut kiosk kimliği operasyonel cihaz kimliğidir; son kullanıcı cihaz kimliğiyle karıştırılmaz.
- Kaynaktaki 10 yanıt “öneri” eşiği korunur; eşik altı kırılım paylaşımı için filtre tasarlanır. Eczaneyi tek başına tanıtacak kırılım/ciro/satış bilgisi yazılı onay olmadan dış rapora girmez.
- Sponsorun yeniden ilişkilendirme ve üçüncü kişiye devir yasağı, sponsor anlaşmasında da karşılanmalıdır; bu iki belge sponsor tarafı anlaşmasının yerine geçmez.
- Analiz gelirleri, Ek-1 F'de aksi olmadıkça katkı payı matrahına girmez. Sponsorluk tahsilatından ayrı gelir türü olmalıdır.
- Kişinin belirlenebilir hâle geldiği fark edilirse ilgili paylaşım durdurulmalı; arayüz bilgilendirmesi toplulaştırılmış analiz amacını da açıklamalıdır.

Oturum/analitik modelleri mevcut; bu dış paylaşım güvencelerinin tamamı kodda doğrulanamadı. “Anonim” adlı alan veya açıklama tek başına bütün koşulların karşılandığının kanıtı değildir.

### Madde 21 — Fesih ve son hesap

21.1 yazılı ihtar sonrası 7 iş gününde giderilmeyen ihlali; 21.2 hizmet durdurulduktan sonra 15 günde borcun ödenmemesini; 21.3 süre sonu/yenilemeyi düzenler. 21.4 resmi karar halinde 60 günlük uyum ve sonuç alınamazsa cezasız fesih getirir; doğmuş borçlar ve cihaz yükümlülükleri ortadan kalkmaz.

21.5 e-isa mülkiyetindeki cihazların 7 iş gününde iadesini ve iadeye kadar kullanım bedelini; mülkiyeti geçmiş cihazda yazılım/içerik kaldırma hakkını düzenler. 21.6 **son katkı payı hesap bildirimi, mahsup ve kalan tutarın eczaneye ödenmesini** ister. Mevcut iptal işlemi durum/tarihçe güncelliyor; bu son hesap ve iade akışı eksik.

### Madde 22 — Mücbir sebep

22.1 olayları, 22.2 olay süresince edimlerin askıya alınmasını ve 30 gün aşılınca tazminatsız feshi düzenler. Fatura motoru her aktif kaydı kesintisiz borçlandırmakla bunu karşılayamaz; sebep, tarih aralığı ve askıya alınan süreçler kaydedilmelidir. Eczanenin ödeme yapmadığı normal kısıt dönemiyle aynı durum değildir.

### Madde 23 — Dijital onay

Elektronik onay beyanı ve 5. maddeye gönderme var. Şimdiki ıslak süreç nedeniyle metin değiştirilmeyecek; uygulama gerçekleşmeyen elektronik onayı varmış gibi kaydetmeyecek. Sabit beyanla imza yöntemi arasındaki metinsel hususlar sonraki hukuki görüşme notudur.

### Madde 24 — Uyuşmazlıklar

Uygulanacak hukuk, Kayseri yetkisi ve arabuluculuk hükümlerine atıf var. Bunlar için yeni bir günlük yazılım hesabı gerekmiyor; sabit metin korunur. Fesih/ihtar/hesap arşivi uyuşmazlıkta erişilebilir olmalıdır.

### Madde 25 — Sponsorluk, bölge ve katkı paylaşımı

| Alt madde | Gereksinim ve uygulama karşılığı |
|---|---|
| 25.1 | Bölgenin tamamı veya bir kısmında sponsor olabilir. Her sponsor için eczaneden yeniden onay alınmaz. Ticari kapsam ve yayın yapılan cihaz seti saklanmalı. |
| 25.2 | Bölge genişletilebilir/daraltılabilir; esaslı unsurlar korunur; güncel kapsam panelden duyurulur. Bağımsız Bölge Yönetimi ve tarihli üyelik/bildirim gerekir. |
| 25.3 | Sponsor sayısı, süre ve cihaz başı/sabit/kademeli tarife Ek-1 G/H'dedir. Tarife kaydı bu fiyatlama türlerini desteklemeli. |
| 25.4 | Aynı bölgedeki sponsor adaylarına eş zamanlı yazılı teklif ve aynı koşullar. Teklif alıcı/gönderim/sürüm takibi gerekir; yalnız kampanya fiyatı seçmek yeterli değildir. |
| 25.5 | Sponsor yayına başlamadan önce her sponsor için aynı biçimde eczane panel bildirimi. Bildirim, yayın akışına bağlı bir olay olmalıdır. |
| 25.6 | Fiili tahsilattan aylık havuz; uygun Aktif Cihaz-Gün oranıyla dağıtım, ay içi günlük orantı. Tahsilat, dönem, bölge üyeliği ve cihaz günü verisi gerekir. |
| 25.7 | Hesap bildirimi toplam tahsilat, oran, havuz, bölge/eczane günleri ve payı içerir. Sponsor kimliği ve diğer özel ticari koşullar bu hesapta gizli tutulur. |
| 25.8 | İlişkili sponsor varsa yayın öncesi bildirimde ilişki belirtilir, eşit koşullar uygulanır. Sponsor kaydında bu bilgi bulunmalıdır. |
| 25.9 | Sponsor çıkınca ilgili bedelden pay sona erer; yeni sponsor/gelir garantisi yoktur. Tahsilatsız döneme tahmini hakediş yazılmaz. |
| 25.10 | Eczane bazlı sponsor için de yeniden eczacı onayı gerekmez; aykırılık bildirimi mümkündür. |
| 25.11 | Giriş/mevcut paket ve ara verip dönen sponsor ayrımı. Kalıcı sponsor kimliği, anlaşma geçmişi ve giriş taahhüdü gerekir. |
| 25.12 | Eczane bazında birden fazla sponsorun ilgili cihazlar için fiili tahsilatı toplanır; katkı hesaplanır. Kimlik gizliliği korunur. |
| 25.13 | Eşit teklif, ön bildirim, hesap şeffaflığı, ilişkili taraf ve gelir garantisi olmaması eczane sponsorluğunda da uygulanır. Bölge ve eczane payı ayrı hesaplanır, birlikte ödenebilir. |

Mevcut Campaign/KioskSponsorship yayın atamasıdır; sponsor alacağı, tahsilat, bölge havuzu ve ödeme kaydı değildir. Yeni tarifeyi kampanyaya bağlamak gereklidir, fakat tek başına 25. maddeyi karşılamaz.

### Madde 26 — Bildirim ve genel hükümler

26.1 **fesih ve ihtarı KEP/noter**, operasyonel bildirimleri panel/SMS/e-posta olarak ayırır; operasyonel gönderim anını esas alır. Genel duyuru “okundu” kaydı, KEP/noter tebliğ belgesinin yerine geçmez. 26.2 değişiklik onayı; 26.3 alacak/hak devrinde yazılı bildirim ve eczane devrinde e-isa onayı; 26.4 kısmi geçersizlik; 26.5 önemli hükümlerin ayrıca gösterimi; 26.6 belge bütünlüğünü düzenler. Ek-1 J'nin ayrıca gösterilmesi ve belge sürüm arşivi gerekir. Sabit ifadeler değiştirilmez.

## 4. Ek-1 bölüm bölüm inceleme

| Bölüm | Veri ve gereksinim | Planlanan karşılık |
|---|---|---|
| A — Taraflar/cihaz/yer | Eczane/eczacı, tam adres, cihaz model ve özellikleri, adet/seri, teklif ve aktivasyon. | Eczane + fiziksel cihaz + sözleşme verisi; aktivasyon=başlangıç. Gerçek donanım ile sabit teknik açıklama uyumu kontrol edilir. |
| B — Edinim/bedeller | Peşin, vadeli, tahsis; model fiyatı, toplam/taksit ve ilk/sonraki ödeme tarihleri. | Kullanıcının kararıyla dinamik tablo; 0 peşin, N taksit, tahsis. Yalnız seçili cihaz/koşullar; tahsis bedelinden aylık tekrar varsayılmaz. |
| C — Kullanım bedeli | Kaynakta 3.900 TL + KDV; başlangıçtan 12 ay sabit; TÜFE/Yİ-ÜFE 12 aylık değişimden yüksek olan; endeksi aşan artışta 15 gün önce bildirim; açma bedeli en çok %30. | Kullanım fiyatı ve vergi kaydı; tarihli fiyat hareketi, tavan ve bildirim. Güncel endeks değeri bu incelemede belirlenmedi. |
| D — Süre | 24 ay + öteleme, azami 6 ay; cihaz ötelemesi ayrı; 12 ay yenileme, 60 gün bildirim; ötelemede katkı yok. | Tarih hesapları; öteleme bedeli ve “öneri” işareti sonraya bırakıldı. |
| E — Ödeme | Peşin cihaz imza/teslimde, vadeli cihaz kendi takviminde; aylık kullanım faturası kesimden 7 iş günü sonra ödenir; banka ve SMS tarifesi. | Kullanım vadesi ile cihaz vadesi ayrılır; banka hesabı belgeye alınır. |
| F — Katkı | Tahsil edilen KDV dahil bedelden %15; 10 iş gününde hesap bildirimi; itiraz 15 gün (öneri); eczane faturası tebliğinden 15 günde ödeme. | Hakediş defteri, süreler, eczane faturası/mahsup/ödeme. Öneri ifadesi korunur. |
| G — Bölge | Kaynak örneğinde Kayseri kapsamı, 15+ cihaz hedefi ve 3 bölge sponsoru; bölge sponsorluğu 12 ay. | Bağımsız Bölge Yönetimi'nden sadece eczanenin bölgesi basılır. Cihaz hedefi garanti veya katı kapasite sınırı değildir. |
| H — Tarifeler | Giriş/mevcut paket, kapsam ve cihaz/sponsor sınırları; kademeli bölge tarifesi. | Bağımsız Sponsorluk Tarifeleri yönetiminden geçerli ilgili kayıtlar. Ayrıntı aşağıda. |
| I — Diğer parametreler | Süreler, garanti, sarf, ceza/kalan değer, depozito. | Süre envanteri aşağıda; ertelenen parametreler aynen korunur. |
| J — Önemli hükümler | Ayrı dikkat çekme ve kabul kutusu. | Basılı belge aynen; gelecekte dijitalde ayrıca gösterim/kabul kanıtı. |
| K — Onay | Ad/unvan, imza/kaşe, tarih; elektronik durumda kayıtlar. | Yetkili bilgileri otomatik, ıslak imza alanı boş; gerçek tarih/yükleme ayrı. |

### Ek-1 H'nin fiyatlama ayrıntıları

- Eczane bazlı giriş paketi kaynakta aylık 5.000 TL + KDV; ilk ay ve devamı taahhüt edilen aylar için. Devam veya ara verip dönüş kaynakta 8.000 TL + KDV.
- Paket kiosk yayını, panel banner'ı, etken madde sayfası ve QR sponsorluğunu birlikte sayar. Bu dört alanın gerçek teslimi/ataması izlenmelidir.
- Cihaz başı eczane sponsorluğu sınırı kaynakta 15 ve “teyit ediniz” notuyla verilmiş; not korunacak. Bölge tablosundaki 3 ile aynı sponsorluk türü değildir; tek ortak limite indirgenmemeli.
- Bölge 1–5 cihaz: cihaz başına 5.000 TL + KDV. 6–15 cihaz: toplam 36.000 TL **KDV dahil**. Vergi dahil/hariç tabanları karıştırılmamalı.
- 15 üstü: 36.000 TL tabana her ilave cihaz için **faturalama günündeki güncel tarife** eklenir. Bu özel kural önceki plandaki her tutarı tamamen dondurma yaklaşımının istisnasıdır. Temel anlaşma ve ilave cihaz fiyatının sürümü ayrı saklanmalı.
- Genel tarife değişiklikleri yalnız yeni sponsorluk sözleşmelerine uygulanır; mevcut anlaşmanın temel fiyatı sırf tarife kaydı değişti diye güncellenmez.

### Ek-1 I süre envanteri

| Parametre | Belgede yazan değer | Takip |
|---|---|---|
| Açık/internete bağlı kalma | 24/7 | Cihaz izleme; kesinti nedeni ayrı. |
| Termal kâğıt | 80 mm, yazıcıya uygun | Saha/kullanım bilgisi. |
| Aykırılık incelemesi | 2 iş günü (öneri) | Destek/şikâyet süresi; not korunur. |
| Haftalık güncelleme | Cumartesi akşamı–pazartesi mesai başlangıcı | Operasyon zamanlaması. |
| Haklı fesih/taksit ihtarı | 7 iş günü | İhtar tarihi ve dış bildirim kanıtı. |
| Ödememe nedeniyle fesih | Hizmet durdurmadan itibaren 15 gün | Kısıt başlangıcı; karar/işlem ayrı. |
| Resmi karar uyumu | 60 gün | Uyum dosyası ve süre. |
| Mücbir sebep | 30 gün | Askı başlangıcı ve fesih değerlendirmesi. |
| Cihaz iadesi | Fesihten 7 iş günü | İade olayının gerçek tarihi. |
| Garanti | Boş ay alanı | Süre tamamlanacak; başlangıç kullanıcı kararıyla sözleşme başlangıcı. |
| Garanti onarımı | 20 iş günü, ücretsiz; ikame opsiyonel | Servis süresi ve cihaz değişimi. |
| Kamera saklama | 30 gün | Eczanenin saha yükümlülüğü. |
| Gizlilik | Sözleşme + 10 yıl | Yetki ve ticari gizlilik; genel veri saklama süresi diye yorumlanmaz. |
| Analiz eşiği | 10 yanıt (öneri) | Dış paylaşım filtresi; not korunur. |
| Depozito | Yok veya tutar | Karar sonraya bırakıldı. |
| Cezai şart | 2–12 aylık bedel | Kalan ücretli süre ve istisnalar. |
| Cihaz kalan değeri | Cihaz bedeli × kalan ay / 24 | Hasar hesabı; donanım değeri ayrı. |

## 5. Ek-2 bölüm bölüm inceleme

| Bölüm | Gereksinim | Uygulama kararı |
|---|---|---|
| 1 — Tutanak bilgileri | No, onay tarihi/kayıt referansı, teslim tarihi/saati, adres ve edinim. | Sistem numarası, sözleşme ve gerçek teslim bilgileri; edinim dinamik. Islak imzada elektronik kanıt uydurulmaz. |
| 2 — Taraflar | Teslim eden personel, görev/telefon; eczane ve teslim alan yetkili. | Eczane/yetkili kaydından önerilir; gerçek teslim eden/alan seçilir. |
| 3 — Cihazlar | Model/ekran, adet, seri ve teslim durumu. | Cihaz sayısına göre satır; seri listesiyle adet uyumu. “Yeni, hasarsız” otomatik işaretlenmez; demo/hasar gerçek durumu personelce belirtilir. |
| 4 — Aksesuar/belgeler | Güç, stand, yazıcı, ağ, garanti/kılavuz, panel bilgisi, mülkiyet etiketi. | Aynen korunur; personel elle işaretler. Kullanıcı şifresi belgeye basılmaz; metindeki gibi ayrı/gizli iletilir. |
| 5 — Kurulum/test | Fiziksel güvenlik, kamera, bağlantı, merkezi aktivasyon, ekran/QR/yazıcı/barkod okuyucu, sabit uyarı, panel girişi, eğitim, fotoğraf. | Aynen korunur; personel elle işaretler. Yazılımın bir özelliği olması fiziksel testin yapıldığı anlamına gelmez. Fotoğraflar dosyayla ilişkilendirilebilir. |
| 6 — Sonuçlar/beyanlar | 6.1 aktivasyon/ödeme başlangıcı; 6.2 mülkiyet; 6.3 koruma; 6.4 eksikler hariç kabul; 6.5 e-isa mülkiyetindeki cihazın iadesi. | Başlangıç=aktivasyon, varsa öteleme; edinim/mülkiyet verisi ana belgeyle tutarlı. Gerçek imza ve dosya yükleme ayrı olaydır. |
| 7 — Kusur/eksik | Yok/var ve açıklama. | Aynen korunur; personel elle doldurur. Sistem kusursuz teslim varsaymaz. |
| 8 — İmzalar | İki tarafın adı, kaşe/imza, tarihi; iki nüsha ve elektronik kayıt açıklaması. | Adlar doldurulur, fiziksel imza alanları boş bırakılır; imzalı tarama arşivlenir. Geç yükleme başlangıcı kaydırmaz. |

Ek-2 tek başına ücret/cihaz planı üretmez; ana sözleşmenin aynı verilerini kullanır. İlk teslim tutanağı, ileride değiştirilen cihazın geçmişini kaybetmek için yeniden yazılmaz; yeni cihaz/ikame/iade ek kayıtla izlenir.

## 6. Faturalandırma sözleşmeye uygun mu

**Takvim ve ayrı fatura kararı uygulandı; mali sürecin tamamı henüz uygun değil.** Günlük iş ve admin işlemi abonelik ile her cihaz ödeme planını ayrı faturalar. Eski `faturala_aylik_birlesik` adı yalnız geriye uyum için aynı ayrı üretime yönlenir ve yeni birleşik kayıt oluşturmaz. Aşağıdaki tablo ilk incelemedeki farkların güncel durumunu gösterir:

| Bulgu | Mevcut kod | Sonuç / gereken |
|---|---|---|
| Ötelemesiz dönemin ilerlemesi | Ödeme başlangıcından itibaren gün hassasiyetli aylık dönemler üretiliyor. | Ardışık dönem ve mükerrer çalıştırma testleri eklendi. |
| Gerçek kesimden sonra vade | Her ayrı faturada kesim tarihi ve kesimi takip eden 7 iş günü saklanıyor. | Hafta sonu ve kayıtlı resmi tatiller atlanıyor. |
| Gecikme/opsiyon ayrımı | `GRACE_DAYS=7`; vade + 7 takvim günü sonrası gecikme/kilit kontrolü. | Bu sayı, faturayı ödemek için verilen 7 iş günü değildir. Son ödeme, gecikme ve hizmet durdurma opsiyonu ayrı. |
| Başlangıç/öteleme gün hassasiyeti | Abonelik ve cihazın kendi ödeme başlangıç günü esas alınıyor. | Öteleme içinde erken fatura oluşturulmuyor. |
| KDV/tevkifat | Matrah, KDV, tevkifat ve net ödenecek tutar fatura ve kalemde snapshot olarak saklanıyor. | Gerçek e-fatura sağlayıcısı/entegrasyonu ayrıca ele alınacak. |
| Tahsilat | `ode_fatura` doğrudan `fatura.tutar` kadar ödeme kaydı oluşturuyor; kısmi bakiye dağıtımı yok. | Vergi farkı tahsilata da yansır. Gerçek tahsilat, kısmi ödeme ve mahsup gerekir. |
| Gerçek kart/otomatik ödeme | Eczacı ödeme ucu mock olarak kayıt yapıyor. | Kart/otomatik talimat seçeneğinin bulunması para tahsil edildiğinin kanıtı değil. İlk aşamada teyitli manuel havale ya da gerçek sağlayıcı seçilmeli. |
| Kesim/dönem alanları | `donem`, `kesim_tarihi`, `hizmet_baslangic`, `hizmet_bitis` ve `vade_tarihi` ayrı saklanıyor. | API ve panel bu alanları sunabilir; mali belge numarası/sağlayıcı kaydı ayrıca gerekir. |
| Yeniden açma | Gecikmiş ödeme sonrası yeni açma faturası oluşuyor; yeni bedelin vadesi ileri. | Açma bedeli ödenmeden kilidin kalkabilmesi ve %30 tavanının uygulanmaması riski. |
| Fesih ve iade | Normal üretim yalnız AKTIF sözleşmelerden. | 21.5'teki cihaz iadeye kadar bedel ve 21.6 son hesaplaşma ayrı takip edilmiyor. |

KDV örneği yalnız hesap açıklamasıdır: kullanım bedeli 3.900 TL ve sözleşmede seçilmiş KDV %20 ise abonelik faturası 3.900 TL matrah, 780 TL KDV ve tevkifat yoksa 4.680 TL ödenecek tutar taşır. Cihaz bedeli aynı gün doğsa bile kendi vergi kırılımıyla ayrı faturadır. Bu, canlı müşteriye ait fatura tespiti değil kod akışının örneğidir.

### 6.1 Doğru dönem ve son ödeme ayrımı

Kullanıcının kesinleştirdiği yapı:

`Sözleşme başlangıcı → aylık hizmet dönemleri → fatura kesimi → kesimi takip eden 7 iş günü son ödeme → varsa gecikme/opsiyon → bilgilendirme ve kısıt`

Örnek başlangıç 8 Kasım ise dönemler 8 Kasım–8 Aralık, 8 Aralık–8 Ocak şeklinde kurulabilir; aralıklar başlangıç dahil, bitiş hariç tutulur. 29/30/31 başlayan sözleşmeler kısa aylarda ay sonuna kırpılır ama sonraki aylarda orijinal başlangıç günü korunur.

Metin aylık faturalandırma ve 7 iş günü vadesini verir. İlk kesimin dönem başında olması kullanıcının kararıdır: öteleme yoksa 8 Kasım'da oluşturulan ve başlayan sözleşmeyle ilk kullanım faturası oluşur; sonraki kesimler 8 Aralık ve 8 Ocak'tır. Abonelik 2 ay ötelenmişse ilk kullanım faturası 8 Ocak'ta, sonraki 8 Şubat'ta oluşur. Cihaz ödemesi bağımsız olarak 3 ay ötelenmişse cihazın ilk faturası 8 Şubat'ta oluşur. Ötelemede başlangıçta fatura oluşturup yalnız vadeyi ileri atmak bu kararı karşılamaz. İlk kesimin dönem başında mı sonunda mı olduğu artık açık soru değildir.

Son ödeme fatura kesimini takip eden 7 iş günüdür. Kesim günü sayılmaz; hafta sonları ve uygulanacak resmi tatil takvimi hesaba katılır. Bu rapor belirli bir gün için doğrulanmış resmi tatil/vade tarihi ilan etmez. Başlangıçta faturalanabilir kalem varsa sözleşme ve o ilk fatura tutarlı tek işlemle kaydedilmeli; ötelemeli kalem kendi ödeme başlangıcını beklemelidir. Günlük görev aynı faturayı yeniden oluşturmamalıdır.

Fatura oluşum bildirimi kesimde gönderilir. Yaklaşan ödeme ve gecikme hatırlatmaları faturada saklanan son ödeme tarihinden hesaplanır; vade düzeltildiğinde yeniden planlanır, ödenmiş/iptal edilmiş borcun hatırlatması durur. Hatırlatma eşikleri ve hizmet durdurma opsiyonu, 7 iş günlük ödeme vadesiyle karıştırılmaz.

Öteleme varsa kullanım bedeli dönemleri ödeme başlangıcından işler; öteleme ayları sonradan toplu borç olmaz. Cihaz peşin bedeli ve taksit vadeleri kendi Ek-1 B/E koşullarını izler. Kullanım faturası vadesi cihaz peşin/taksit borcunu otomatik 7 iş günü ileri taşımaz.

Geç işleyen görev veya sonradan kaydedilen sözleşmede hizmet dönemi geçmiş olabilir; gerçek fatura kesim tarihi sahte biçimde geriye yazılmaz. Eksik dönem ve kesim/vade politikası ayrı kaydedilmeli; imzalı taramanın geç yüklenmesi ise faturayı etkilememelidir.

## 7. Sponsor tahsilatı ve eczaneye bildirim/ödeme

### 7.1 Üç para akışı

| Yön | Borç/tahsilat konusu | Temel |
|---|---|---|
| Eczane → e-isa | Kullanım, cihaz ve varsa diğer eczane borçları. | Madde 13–14, Ek-1 B–E. |
| Sponsor → e-isa | Sponsorluk anlaşmasından doğan alacak ve fiili tahsilat. | Tarife + ayrı sponsor anlaşması; eczane sözleşmesi ödeme vadesini belirlemiyor. |
| e-isa → Eczane | Katkı payı, eczane faturası, mahsup ve çıkış ödemesi. | 13.2, 25, Ek-1 F. |

Sponsorun ödeme vadesi/peşin veya vadeli ödeyeceği bu iki belgede kesinleştirilmemiştir. Eczanenin 7 iş günü kullanım faturası vadesi sponsora kopyalanamaz. Bunun kaynağı sponsor anlaşması/ödeme planı olmalıdır. Yayının başlaması için mutlaka tahsilat şartı da bu metinlerden çıkarılamaz; metin tahsilatı **katkı payının doğması** için şart koşar.

### 7.2 Önerilen işlem zinciri

1. Sponsor kaydı açılır; firma kimliği, iletişim, ilişkili taraf bilgisi ve giriş/devam geçmişi tutulur.
2. Kampanya geçerli tarife sürümüne bağlanır; bölge/eczane/cihaz kapsamı ve yayın tarihleri belirlenir.
3. Teklif/anlaşma/borç takvimi kaydedilir. Fatura düzenlendiyse referansı tutulur; fatura kesilmesi ödeme alınması sayılmaz.
4. Yayından önce ilgili eczanelere içerik/sponsor bildirimi iletilir. Yeni medya sürümü veya yeni hedef eczane için gerekli bildirim ayrıca oluşur; onay butonu şartı konmaz.
5. Tahsilat gerçekleşince gerçek tarih, KDV dahil tutar, yöntem, banka/dekont referansı, ilgili dönem/kapsam ve kısmi bakiye kaydedilir. İlk aşamada yetkili manuel teyit uygulanabilir; banka entegrasyonu ayrı iştir.
6. Uygun katkı payı hesaplanır; kullanım faturalandırması, öteleme ve cihaz-gün kuralları uygulanır. Abonelik ötelemesinde katkı doğmaz, birikmez, sonradan ödenmez; bu günler dağıtım paydasına girmez. Yalnız cihaz faturası bu engeli kaldırmaz. Teknik hata nedeniyle eksik kullanım faturasında otomatik katkı ödemesi bekletilir ve hata düzeltilir; geçmiş uygun günler öteleme sayılarak silinmez. Bir tahsilat birden çok kampanyaya dağıtılıyorsa toplam dağıtım tahsilatı aşmaz ve aynı tutar iki kez hakediş üretmez.
7. Tahsilattan en geç 10 iş günü içinde panelde hesap bildirimi oluşturulur; eczanenin itiraz süresi kaydedilir.
8. Eczanenin e-isa'ya düzenlediği faturanın numarası/dosyası ve **tebliğ tarihi** alınır; tebliğden 15 gün sonrasına ödeme vadesi konur.
9. Varsa eczane borçları açık kalemlerle mahsup edilir; kalan tutar ödenir. Ödeme tarihi/dekontu saklanır. Fesihte aynı zincir son hesap için yürütülür.

### 7.3 Örnek katkı hesabı

Bu örnek, cihazların katkıya uygun olduğu ve ötelemede bulunmadığı bir dönem içindir:

- Eczane bazında 12.000 TL KDV dahil fiili tahsilat → 1.800 TL katkı payı.
- Bölge için 36.000 TL KDV dahil fiili tahsilat → 5.400 TL havuz.
- Eczanenin uygun cihaz-günü 30, bölgenin toplamı 300 → bölge payı 540 TL.
- Eczanenin iki kaynak toplamı 2.340 TL. İlgili borçlardan 1.000 TL mahsup yapılırsa net çıkış ödemesi 1.340 TL; raporda brüt pay, mahsup ve net ayrı görünür.

Matrah zaten KDV dahil tahsilat olduğu için %15 ile çıkan paya sistem otomatik olarak bir kez daha KDV eklemez. Eczanenin düzenlediği faturada bu toplamın vergi kırılımı, faturanın kendi oranına göre ayrıca izlenir.

**6–15 cihaz tarifesinde 7 ve 14 cihaz:** Sponsorun aynı 36.000 TL brüt bedeli tamamen ödediği, her eczanede bir cihaz bulunduğu ve bütün cihazların 30 gün boyunca katkıya uygun olduğu varsayımıyla havuz her iki durumda da 5.400 TL'dir.

| Katkıya uygun cihaz | Toplam Aktif Cihaz-Gün | Eczane başına cihaz-gün | Eczane payı, yaklaşık |
|---|---|---|---|
| 7 | 210 | 30 | 771,43 TL |
| 14 | 420 | 30 | 385,71 TL |

Formül: `eczane payı = fiilen tahsil edilen brüt bölge bedeli × %15 × eczanenin uygun Aktif Cihaz-Günü / bölgenin uygun toplam Aktif Cihaz-Günü`. Tarifenin cihaz aralığı sabit fiyatı belirler; eczanenin payını sabitlemez. Bir eczanede iki cihaz varsa uygun cihaz-günleri toplanır.

7 cihaz 30 gün, sonradan eklenen 7 cihaz 15 gün uygunsa payda 315 cihaz-gündür: ilk grupta cihaz başına yaklaşık 514,29 TL, yeni grupta 257,14 TL düşer. Bunlar kuruşa yuvarlanmış gösterim örnekleridir; dağıtımda kuruş farkları tutarlı bir yöntemle tamamlanıp toplam tam 5.400 TL'ye eşitlenir. Ötelemedeki cihazlar katkı hesabından çıkarılır; bu durum sponsor tarifesinin kendiliğinden düşmesi anlamına gelmez. Geçmiş hakediş güncel cihaz adediyle yeniden hesaplanmaz.

### 7.4 Bildirim ve süre envanteri

| Olay | Alıcı | Süre/kanal | Ayrıntı |
|---|---|---|---|
| Sponsor teklifleri — 25.4 | Aynı bölgedeki sponsor adayları | Eş zamanlı ve yazılı | Teklif sürümü ve alıcı listesi. |
| Sponsor/içerik yayını — 16.5, 25.5 | İlgili eczaneler | Yayın başlamadan önce panel; e-posta ek olabilir | Aynı biçim, içerik sürümü, ilişkili taraf açıklaması. Eczacı onayı gerekmez. |
| Bölge değişikliği — 25.2 | Etkilenen eczaneler | Panel duyurusu | Yeni kapsam ve yürürlük tarihi. |
| Katkı hesabı — 13.2/d | İlgili eczane | Tahsilattan 10 iş günü içinde panel | Toplam tahsilat, oran, havuz, cihaz-günler, pay. |
| Hesaba itiraz — Ek-1 F | Eczane → e-isa | Bildirimden 15 gün (öneri) | Gerekçe, inceleme, yanıt ve düzeltme sürümü. |
| Katkı ödemesi — 13.2/e | e-isa → eczane | Eczane faturası tebliğinden 15 gün | Tebliğ tarihi, vade, mahsup, net ödeme. Bu süre 15 iş günü olarak yazmıyor. |
| İçerik aykırılığı — 9.3 | Eczane → e-isa | İnceleme 2 iş günü (öneri) | İçerik referansı, değerlendirme ve kaldırma/düzeltme. |
| Ödeme nedeniyle kısıt — 13.1/a | e-isa → eczane | Vade/opsiyon sonrası, panel/SMS/e-posta | Gönderim ve kısıt başlangıcı. |
| Endeksi aşan artış — 13.4 | İlgili bölge eczaneleri | 15 gün önce yazılı | Yeni tarife ve itiraz/fesih takibi. |
| Yenilememe/fesih — 12.2, Ek-1 D | Taraflar | Bitişten en az 60 gün önce; 26.1'deki kanal ayrımıyla | Yenilenmeme kararı ve belge. |
| Taksit/ihlâl ihtarı — 14.2, 21.1 | İlgili taraf | 7 iş günü; KEP/noter | Dış gönderim/tebliğ belgesi, muacceliyet/fesih değerlendirmesi. |
| Ödememe feshi — 21.2 | Eczane | Durdurmadan 15 gün sonra şartları oluşabilir | Otomatik zorunlu fesih değil, metindeki hakkın uygulanma kaydı. |
| Hak/alacak devri — 26.3 | Eczane | Yazılı bildirim | Devir kaydı ve gönderim kanıtı. |
| Fesih sonrası son hesap — 21.6 | Eczane | Fesih hesaplaşmasında | Son pay, borç, mahsup ve kalan ödeme. |

Gönderim, panelde erişilebilir olma, okunma ve işlem onayı ayrı olaylardır. 26.1 operasyonel bildirimde gönderim anını esas alıyor; eczanenin paneli açmaması mali bildirim süresini kendiliğinden durdurmaz. Mevcut genel duyuru modülü temel sağlar, ancak finansal olay ve belgeye bağlı kalıcı gönderim geçmişiyle genişletilmelidir.

Hesap bildiriminde 25.7'nin gizlilik sınırı korunur. Sponsorun özel anlaşmasının tamamı, kimliği veya diğer eczanelerin detaylı cari bilgileri eczanenin mali ekranına dökülmez. Yayın öncesi bilgilendirme/ilişkili taraf açıklaması ayrı amaçtaki bildirimdir; bunun içerik sınırı hesap ekranından farklı tasarlanır.

### 7.5 Hesaplamadan önce netleştirilecek sınır durumları

- Aylık cihaz-gün toplamı ay bitmeden kesinleşmez; erken tahsilatın 10 iş günlük bildirimi ay sonundan önce dolabilir. Ara/kesin hesap yöntemi açıkça kararlaştırılmalı; sessizce ay sonuna erteleme yapılmamalı.
- 25.1 bölgenin bir kısmında yayın yapılmasına izin verir; 25.6 dağıtımda bölge toplamını söyler. Dağıtım kümesi açıkça belirlenmeden payda yalnız seçili kiosklar kabul edilmemeli.
- Çok aylık peşin ödeme, geç tahsilat, kısmi ödeme, iade ve kampanya kapsam değişikliği hangi hesap dönemine yazılacak belirlenmeli.
- Hiç uygun cihaz yoksa sıfıra bölme veya eczanelere hayali pay üretilmemeli; tahsilat ve dağıtılamayan durum ayrıca izlenmeli.
- Günün ne kadarında yayın olması gerektiği, kesinti/öteleme sınır günleri ve kuruş farkı dağıtımı tanımlanmalı. Teknik offline kaydı tek başına eczane kusuru olarak kabul edilmemeli.

## 8. İş sonunda ekip görüşmesine saklanan gündem

Başlangıcın dosya yüklemesinden bağımsız olması, ötelemesiz ilk faturanın sözleşmeyle dönem başında oluşması, ötelemeli kalemin ilk kesiminin başlangıç + ilgili öteleme olması, 7 iş günlük vade, öteleme döneminde katkının doğmaması/birikmemesi, ayrı bölge/tarife yönetimi ve kampanyanın tarifeye bağlanması kesinleşmiştir. Bu kararlar tekrar sorulmayacaktır.

Tahsis bedeli ve donanım değeri, garanti süresi, sponsor ödeme planı, katkı hesabının sınır durumları, eksik hukuki süreler ve belge atıfları [ekip soruları dosyasında](abonelik-sozlesme-ekip-sorulari.md) soru olarak saklanır. Depozito, öteleme bedeli ve “öneri/teyit” metinleri de kullanıcının isteğiyle bu sonraki görüşmeye bırakılmıştır. Mevcut ifadeler değiştirilmez, belirsiz parasal yükümlülük için kendiliğinden değer üretilmez. Bu liste şimdiki plan çalışmasında yeniden cevap talebi değildir.

## 9. Kod kanıtları

- [Ayrı faturalandırma ve ödeme servisleri](../backend/apps/abonelik/services.py): `faturala_ayri`, geriye uyum yönlendirmesi `faturala_aylik_birlesik`, `add_business_days`, `guncelle_gecikmis_faturalar`, `ode_fatura`, `_olustur_acma_kapama_fatura`, `iptal_sozlesme`.
- [Fatura ve sözleşme modelleri](../backend/apps/abonelik/models.py): KDV/tevkifat özellikleri, Fatura/FaturaKalemi, mülkiyet ve teslim için eksik alanlar.
- [Günlük iş](../backend/apps/abonelik/jobs.py): ayrı abonelik/cihaz faturalandırma çağrısı.
- [Abonelik API'si](../backend/apps/abonelik/views.py): admin üretimi, mock ödeme, ıslak dosya yükleme ve indirme.
- [Fatura API alanları](../backend/apps/abonelik/serializers.py): kesim/dönem/vergi kırılımlarının kapsamı.
- [Fatura düzeltmeleri](../backend/apps/abonelik/invoice_corrections.py): yeniden hesaplamada da vergi hariç kalem özellikleri kullanılıyor.
- [Kampanya modelleri](../backend/apps/campaigns/models.py): cihaz bazlı yayın ve serbest sponsor adı; mali anlaşma/tahsilat kaydı yok.
- [Duyuru modelleri](../backend/apps/announcements/models.py) ve [duyuru servisleri](../backend/apps/announcements/services.py): genel hedefleme/okunma ile ödeme/sözleşme hatırlatmaları; sponsor mali olaylarına bağlı bildirim yok.
- [Eczacı hesap ekranı](../web_panels/src/views/pharmacist/HesabimOdemeler.vue): sözleşmede vergili tutar gösterimi ve faturada doğrudan `fatura.tutar` kullanımı.

Yalnız planlama belgeleri oluşturulmuş/güncellenmiştir. Uygulama kodu, veritabanı ve Word kaynakları değiştirilmemiştir.
