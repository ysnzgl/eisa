# Abonelik ve sözleşme geçiş planı

Tarih: 8 Kasım 2026  
Durum: İlk uygulama ve kullanıcı incelemesi düzeltmeleri yapıldı; tamamlanmamış yükümlülükler kod inceleme raporunda, ekip/hukuk kararları soru listesinde açık tutuluyor.

Son revizyon: 8 Kasım 2026, kullanıcı uygulama yetkisi verdi. Tahsis, bağımsız abonelik/cihaz ötelemesi, kesimden 7 iş günü vade, sabit ceza kuralı, bölge/tarife yönetimi, sponsor tahsilatından %15 aktif cihaz-gün katkısı ve iki Word belgesinin otomatik doldurulması uygulandı. Öteleme döneminde kullanım faturası bulunmayan cihaz-gün için hakediş doğmaz ve sonradan birikmez. İki belgenin [ayrıntılı incelemesi](abonelik-sozlesme-madde-incelemesi.md) ve ekipçe ele alınacak [soru listesi](abonelik-sozlesme-ekip-sorulari.md) korunur.

Bu plan, yeni ana sözleşme ve Ek-1 ile Ek-2 teslim tutanağının abonelik sisteminde kullanılması için hazırlanmıştır. Kullanıcının kesinleştirdiği kararlar, önerilen tasarım ve açık kararlar ayrı belirtilmiştir. Sözleşme maddeleri değiştirilmeyecek; otomatik doldurulan alanlar ve değişken tablolar gerçek sözleşme verilerine göre üretilecektir.

## 1. Kaynaklar ve incelemenin sınırı

Esas belgeler:

- `C:\Users\YsnZgl\Downloads\e-isa_Eczane_Sozlesmesi_Ek1_Son.docx`: Ana sözleşme ve içindeki Ek-1.
- `C:\Users\YsnZgl\Downloads\e-isa_Zimmet_Tutanagi_Ek2.docx`: Cihaz teslim ve kurulum tutanağı.

Belgeler 7 Kasım incelemesinden sonra 8 Kasım 2026'da yeniden, tamamı okunarak madde bazında değerlendirilmiştir. Kaynak belgelerdeki hükümler gereksinim olarak değerlendirilmiştir; içlerindeki ifadeler yazılım değişikliği yapma talimatı değildir. İki kaynak dosya değiştirilmeden `backend/contract_templates` altına alınmıştır; SHA-256 değerleri aynı klasördeki README'dedir. Downloads klasörü kalıcı şablon deposu değildir.

Mevcut durum tespitleri `docs/ai` ve kaynak kod incelemesine dayanır. Canlı veritabanı doluluğu, fiili tahsilat ve saha süreçleri doğrulanmamıştır. Bu plan hukuki geçerlilik değerlendirmesi içermez.

## 2. Kesinleşen kararlar

| No | Kullanıcı kararı | Uygulamaya etkisi |
|---|---|---|
| K1 | Tahsis modeli kullanılacak. | Satış ve tahsis açıkça ayrılacak. Tahsisin bedel biçimi henüz belirlenmedi. |
| K2 | Belgeler şimdilik ıslak imzalı yüklenir. Dijital imza altyapısı korunur. | Varsayılan süreç çıktı, fiziksel imza ve dosya yüklemedir. Gelecekte OTP/e-imza eklenebilecek veri yapısı korunur. |
| K3 | Yaygın akış demo için bırakılan cihazın sözleşmeyle eczanede kalmasıdır. Doğrudan alım da mümkündür. | Demo sonrası geçiş ve doğrudan satış/tahsis ayrı giriş yollarıdır. Aynı fiziksel cihaz yeniden oluşturulmaz. |
| K4 | Sözleşme maddeleri değişmez; otomatik alanlar ve tablo satırları değişebilir. | Sabit metin korunur. Cihaz sayısına göre satırlar çoğalır; edinim ve taksit etiketleri dinamik olur. |
| K5 | Ek-2 Bölüm 4, 5 ve 7 aynı kalır; personel elle işaretler. | Aksesuar, kurulum/test ve kusur/eksik bölümleri basılı belgede doldurulur. İlk aşamada bunlar için zorunlu dijital kontrol formu yapılmaz. |
| K6 | Ek-1 Bölüm B sözleşmede girilen bilgilerden oluşur. | Model, adet, edinim, fiyat, vade ve ödeme takvimi sözleşme/cihaz planından üretilir. |
| K7 | Aktivasyon tarihi sözleşme başlangıç tarihine eşittir. | Tek ticari başlangıç tarihi esas alınır. Teknik cihaz aktivasyonu ve demo teslimi bu tarihi otomatik değiştirmez. |
| K8 | İl ve ilçelere dayanan bölge kayıt sistemi sözleşmeden bağımsız ayrı yönetilir. | Eczanenin konumundan bölgesi bulunur; yalnız ilgili bölgenin bilgileri Ek-1'e yazılır. Diğer bölgelerin kayıtları gösterilmez. |
| K9 | Sponsorluk tarifeleri başlangıç/bitiş tarihleriyle ayrı yönetim panelinde kaydedilir. Kampanyada tarife ilişkisi zorunludur. | Belge oluşturulan takvimde geçerli ve ilgili kapsamda olan tarifeler alınır. Yeni kampanya geçerli tarife sürümü seçilmeden kaydedilemez. |
| K10 | Sözleşmesel süreçler sözleşme başlangıcını esas alır; imzalı dosyanın yüklenmesi beklenmez. | Hizmet, süre ve garanti sayacı başlangıçtan işler. Kullanım bedelinde varsa sözleşmedeki öteleme uygulanır. İmzalı dosya eksikliği sadece arşiv/takip durumudur; yeni aktivasyon veya saha teyidi kapısı eklenmez. |
| K11 | İlk fatura ilgili ödeme kaleminin ötelemesine bağlıdır; son ödeme fatura tarihinden 7 iş günü sonrasıdır. | Abonelik ilk faturası = başlangıç + abonelik ötelemesi; cihaz ilk faturası = başlangıç + cihaz ödeme ötelemesi. Öteleme 0 ise ilgili kalem sözleşmeyle başlangıçta faturalanır. Ötelemede önceden fatura kesip yalnız vade ileri atılmaz. İmzalı dosya beklenmez; cihazın özel ödeme planı ayrıca korunur. |
| K12 | Depozito, öteleme bedeli ve “öneri/teyit” değerlerinin kararı sonraki hukuki görüşmelere bırakıldı. | Metinler ve mevcut değerler aynen korunur; bu planlamada yeniden karar talep edilmez ve yeni bir değer varsayılmaz. |
| K13 | Otomatik doldurulabilecek alanlar mevcut verilerden doldurulacak. | Eczane/şirket/banka/sözleşme/cihaz planı verileri kullanılır. Bulunmayan seri numarası, garanti süresi veya hukuki parametre uydurulmaz; eksik alan görünür kalır. Ek-2 4, 5 ve 7 elle doldurulur. |
| K14 | Bildirim ve hatırlatmalar yeni son ödeme tarihini esas alacak. | Fatura oluşum bildirimi kesimde; yaklaşan vade/gecikme hatırlatmaları faturada saklanan son ödeme tarihinden hesaplanır. |
| K15 | Ceza genel fiyat tanımındaki katsayıdan değil sözleşmedeki kuraldan alınacak. | Erken fesihte kalan ücretli süre bedeli, 2–12 aylık sınır ve ceza uygulanmayan haller. Sabit olan TL tutarı değil sözleşme sürümüne bağlı hesap kuralıdır. Açma bedelinin %30 tavanı ve gecikme faizi ayrı kavramlardır. |
| K16 | Tahsis ve hukuki/öneri konularındaki sorular iş sonunda ekip görüşmesine saklanacak. | Ayrı soru dosyası tutulur; çözülmüş kararlar tekrar sorulmaz. Belirsiz parasal hüküm kendiliğinden uygulanmaz. |
| K17 | Bölge katkı payı, o dönemdeki uygun Aktif Cihaz-Gün oranına göre değişir. | 6–15 cihaz tarifesinde sponsorun sabit toplam bedeli, eczanenin payını sabitlemez. 7/14 cihaz ve ay içi cihaz ekleme örnekleri kabul senaryosudur. |
| K18 | Abonelik ötelemesi nedeniyle kullanım faturası kesilmeyen dönemde eczane katkı payı alamaz. | Bu döneme hakediş doğmaz, birikmez ve sonradan toplu ödenmez. Eczane ve bölge sponsorluğu birlikte kapsanır; ötelemedeki cihaz-günler bölge dağıtım paydasına girmez. Cihaz faturası tek başına kullanım ötelemesini veya katkı engelini kaldırmaz. |

K4 örnekleri: satışta `0` taksit seçimi belgede **Peşin satış**, `6` seçimi **6 ay vadeli satış / 6 taksit**, tahsis seçimi **Tahsis** olarak görünür. `0` bedelsiz satış anlamına gelmez. Taksit sayısının üst sınırı ayrıca kararlaştırılacaktır.

## 3. Belge üretimi ve saklama

### 3.1 Sabit metin ve değişken alanlar

- Ana sözleşmenin maddeleri ve Ek-2'nin sabit beyanları aynen korunur.
- İlk yazılım çalışmasında bir alan listesi hazırlanır: hangi hücre/etiket değişken, hangi metin sabit açıkça işaretlenir.
- Ek-1 B'deki fiyat/taksit tablosu, Ek-1 G'deki bölge tablosu, Ek-1 H'deki tarife kayıtları ve Ek-2'deki cihaz satırları değişken veriyle doldurulur.
- Ek-2 edinim alanına sözleşmenin gerçek modeli yazılır; tahsis veya 6 ay vadeli satış gibi seçimler otomatik alanda gösterilir.
- Ek-2 Bölüm 4, 5 ve 7'nin içeriği ve işaretleme alanları korunur; sistem bunları tamamlanmış göstermez.
- Kaynaklarda kalan “öneri”, “teyit ediniz” ifadeleri ve belge atıfları aynen korunur. Depozito ve öteleme bedeliyle birlikte sonraki hukuki görüşme gündemine alınmıştır; bu aşamada kesinleştirilmez.

### 3.2 Belge seti ve sürümler

Önerilen arşiv yapısı:

| Kayıt | İçerik |
|---|---|
| Şablon sürümü | Kaynak dosya, sürüm, yürürlük tarihi, sabit metin ve değişken alan tanımı. |
| Oluşturulan belge | Ana sözleşme + Ek-1 veya Ek-2; belge numarası, sürüm, oluşturma tarihi, dosya ve üretimde kullanılan verilerin sabit kopyası. |
| İmzalı belge | İmzalı dosya, belge türü/sürümü, gerçek imza tarihi, yükleyen kişi ve yükleme zamanı. |
| İmza/onay kaydı | Yöntem, taraf/yetkili ve ilgili belge; gelecekte doğrulama/sağlayıcı kanıtları eklenebilir. |

Eczanenin adresi, şirket IBAN'ı, fiyat veya bölge daha sonra değişse bile imzaya sunulmuş belge değişmez. Düzeltme yeni belge sürümü olarak yapılır; önceki dosya ve hareket kaydı korunur. Ana sözleşme + Ek-1 ve Ek-2 ayrı belge türleri olarak izlenir. Tek tarama dosyasının iki belgeyi kapsaması gerekiyorsa aynı dosya iki belgeyle ilişkilendirilebilir; eksik belge gizlenmez.

Islak imzada yükleme zamanı, gerçek imza tarihi ve sözleşme başlangıcı ayrı tutulmalıdır. Dosyanın 10 Kasım'da yüklenmesi, 8 Kasım'da imzalanan sözleşmenin başlangıcını 10 Kasım yapmamalıdır. Önceden üretilen boş form ile elle doldurulmuş imzalı tarama ayrı saklanmalıdır.

Ek-2 Bölüm 4, 5 ve 7 için imzalı tarama esas kanıttır; OCR veya otomatik kutu okuma ilk aşamanın kapsamı değildir. Kurulum fotoğrafları sözleşmedeki teslim maddesine uygun şekilde dosyaya eklenebilmeli veya ilgili belgeyle ilişkilendirilebilmelidir.

### 3.3 Dijital imzanın geleceğe hazırlanması

Mevcut dijital seçenek ve geçmiş dijital onay kayıtları korunur. Yeni akış ıslak imzayı varsayılan seçer. Mevcut butonla onay, OTP veya sağlayıcı e-imzası yapılmış gibi kaydedilmez.

Genişletilebilir yöntem ayrımı önerisi: ıslak imza, mevcut panel onayı, SMS OTP, e-posta OTP, sağlayıcı e-imza/mobil imza. Sağlayıcı eklenene kadar mevcut olmayan yöntemler başarılı işlem üretemez. İleride eklenecek kanıtlar: doğrulayan kişi, doğrulama yöntemi, zaman, IP/cihaz bilgisi, belge özeti, sağlayıcı işlem numarası ve varsa zaman damgası kanıtı. Belge özeti tek başına yetkili sağlayıcı zaman damgası sayılmaz.

## 4. Sözleşme ve teslim akışları

### 4.1 Demo sonrası sözleşme

1. Cihaz mevcut eczanede demo kapsamında çalışır. Fiziksel cihaz kimliği ve demo başlangıcı korunur.
2. Admin standart sözleşmeyi hazırlar; aynı cihazı seçer, satış/tahsis koşullarını girer.
3. Sözleşme başlangıcı aynı zamanda ticari aktivasyon tarihi olur. Önceki demo başlangıcı otomatik devralınmaz.
4. Ana sözleşme + Ek-1 ve Ek-2 aynı ticari verilerle üretilir. Personel Ek-2'nin 4, 5 ve 7. bölümlerini elle doldurur; taraflar imzalar.
5. Standart sözleşme girilen başlangıç tarihinden işler; imzalı belgeler aynı gün veya sonradan yüklenebilir. Demo ve standart sözleşme arasında ilişki kurulur; aynı döneme iki standart borç veya iki hakediş üretilmez.
6. Öteleme yoksa ilk kullanım faturası sözleşmeyle birlikte dönem başında oluşur; varsa ilk kesim başlangıç + abonelik öteleme süresindedir. Sonraki kullanım faturaları ödeme başlangıcına bağlı aylık dönem başlarında oluşur; her kullanım faturasının vadesi kendi kesim tarihini takip eden 7 iş günüdür. Cihazın ilk kesimi kendi ödeme ötelemesine göre ayrıca hesaplanır.

Demo için daha önce yapılan fiziksel teslim geçmişte korunur; standart sözleşmedeki ticari aktivasyon ve garanti sayacı kullanıcının kararıyla sözleşme başlangıcını esas alır. Fiziksel teslim kaydı ile sözleşmesel başlangıç birbirinin yerine yazılmaz. Garanti süresinin kaç ay olacağı ayrıca belirlenecektir.

### 4.2 Doğrudan satış veya tahsis

1. Eczane, yetkili, cihazlar ve ticari şartlar seçilir.
2. Sözleşme başlangıcı ve aktivasyon aynı tarihe ayarlanır.
3. Belgeler oluşturulur; kurulum, teslim ve ıslak imza yürütülür. İmzalı dosyalar aynı gün veya daha sonra yüklenir; sistem girilmiş başlangıç tarihinden işler.

Kurulum gecikmesi ve farklı günlerde fiziksel teslim olayları ayrıca kaydedilir. Bunlar mevcut sözleşmenin başlangıcını kendiliğinden kaydırmaz. İmzalanmış sözleşmenin tarihi sessizce değiştirilmez.

### 4.3 Belge durumu ve hizmet durumu

Önerilen belge durumları: taslak, imzaya hazır, imzalı dosya bekleniyor, belge seti tamamlandı, yeni sürümle değiştirildi. Bunlar mevcut aktif/iptal abonelik durumundan ayrı tutulur.

Kesin karar: hizmet ve mali süreçler başlangıç tarihine göre yürür; dosya yükleme veya ayrıca saha teyidi beklenmez. Belge eksikliği için takip/hatırlatma yapılabilir, bu nedenle hizmet veya fatura durdurulmaz. İleri başlangıçlı sözleşme için başlangıçtan önce ücret üretilmez. Gerçek imza tarihi ve yükleme zamanı korunur; sahte dijital onay oluşturulmaz. Geçmiş dijital kayıtlar ve ileride kullanılacak dijital kanal korunur.

## 5. Otomatik alanların veri kaynakları

| Alan | Kaynak ve yapılacak iş |
|---|---|
| Eczane unvanı, eczacı/sahip, telefon, adres | Mevcut eczane kaydından önerilir. Eksik alanlar sözleşme öncesinde tamamlanır. |
| Teslim alan yetkili | Eczacıdan önerilir; farklı kişi teslim alıyorsa adı, görevi/yetkisi ve telefonu ayrıca alınır. |
| Teslim eden personel | Kullanıcı/personel kaydından seçilir; isim, görev ve telefon belgeye alınır. Kullanıcı hesabı olmayan dış servis ihtiyacı açık karardır. |
| Şirket ve ödeme hesabı | Şirket profili ve seçilen banka hesabı; belge oluşturulurken sabit kopyası alınır. |
| Cihaz modeli/ekran boyutu | Standart cihaz kataloğu; fiziksel cihazın gerçek donanım özellikleriyle eşleştirilir. |
| Adet ve seri numarası | Sözleşmeye bağlanan fiziksel cihazlar. Adet ile seri listesi uyumlu olmalı; MAC/UUID seri no yerine kullanılmaz. |
| Stoktan henüz yazılıma kaydolmamış cihaz | Seri numarasıyla fiziksel cihaz kaydı açılabilmeli; kiosk kaydı daha sonra eşleştirilebilmeli. |
| Edinim, peşin/vadeli fiyat, taksitler | Sözleşme ve cihaz ödeme planı. Ek-1 B ile Ek-2 edinim alanı aynı kaynaktan üretilir. |
| Teklif tarihi | Açık tarih alanı. Mevcut kayıt oluşturma tarihi otomatik teklif tarihi sayılmaz. |
| Başlangıç ve aktivasyon | K7 gereği aynı tarih. Islak imza tarihi ayrıca saklanır. |
| Teslim tarihi/saati | Gerçek olay tarihi/saati; başlangıç tarihiyle varsayılan önerilebilir, sahada doğrulanır. |
| Ödeme başlangıcı | Sözleşme başlangıcı ve onaylı ötelemeden hesaplanır. |
| Tutanak ve sözleşme numarası | Sistem üretir; her belgede ilişkiyi gösterecek numaralar bulunur. |
| Ek-2 onay tarihi/kayıt no alanı | Islak imzada gerçek imza tarihi ve imzalı belge referansı gösterme önerisi; elektronik kayıt uydurulmaz. Alan etiketinin yöntem bazlı biçimi netleştirilecek. |
| Bölge | Eczanenin il/ilçesine göre bölge eşlemesi; belge anındaki adı/kapsamı saklanır. |
| Sponsorluk tarifeleri | Sözleşme oluşturma tarihinde bölgeye uygun geçerli tarife sürümleri. |
| Garanti, depozito, tahsis ve öteleme bedeli | Kararlaştırılmış ticari parametre veya sözleşmeye özel seçim. Boşsa tahmini değer yazılmaz. |
| İmza alanları | İsimler ve gerçek tarihler doldurulur; fiziksel kaşe/imza alanı boş bırakılır. |

Kaynak belgedeki donanım açıklamasıyla gerçek teslim cihazının özellikleri farklıysa bu, otomatik alan doldurarak gizlenmez; cihaz/şablon eşleşmesi tamamlanmadan belge kesinleştirilmez.

İlk uygulama kapsamı otomatik doldurulabilen alanlarla ilerleyecektir. Bölge/tarife gibi henüz bulunmayan yönetim kayıtları hazır olmadan o bilgiler mevcutmuş gibi gösterilmez. Eksik alan listesi belge önizlemesinde görülebilir; imzalı taramanın eksikliğiyle gerçek ticari verinin eksikliği aynı durum değildir. Kaynak metindeki boş/öneri alanlarını otomatik olarak sıfır veya kesin kabul edilmiş değere çevirmek bu kararın kapsamında değildir.

## 6. Edinim, taksit ve tahsis

Önerilen edinim yapısı satış ve tahsisi ayrı tutar. Satışın peşin/vadeli oluşu ödeme planıyla belirlenir. Birden fazla cihazın farklı model veya koşulları olabilmesi için satır düzeyinde veri tutulması önerilir; tek sözleşmede karma edinime izin verilip verilmeyeceği açık karardır.

- Satışta kullanıcı `0` seçerse peşin tutar tek ödemedir. Mevcut kod peşini `1` taksit olarak saklıyor; kullanıcıdaki `0` ile iç hesap eşleştirilmeli, sıfıra bölme veya eski peşin kayıtlarını bozma olmamalı.
- Vadeli satışta taksit sayısı, birim/toplam tutar, varsa vade farkı, KDV ve tarihler açıkça kaydedilir. Yuvarlama farkı son taksitte dengelenir.
- Tahsis, 14.3 gereği cihazın e-isa mülkiyetinde kalması ve eczaneye sözleşme süresince kullanım hakkı verilmesidir. Ek-1 B'de tahsis bedeli alanı vardır; bedelin aylık olduğu veya otomatik satışa dönüşeceği yazmaz. Önceki taslaktaki dönemsel bedel bir tasarım ihtimaliydi; sözleşmede mevcut bir hüküm olarak kabul edilmez. Bu alan tek başına aylık kira faturası üretmeye yetmez.
- Tahsiste satış taksiti üretilmez; aylık platform kullanım bedeli ve tahsis cihazının hasar hesabına esas donanım değeri ayrı tutulur. Tahsis bedelinin sıfır olması donanımın değerinin sıfır olduğu anlamına gelmez.
- Tahsis cihazında teknik yıpranma kaynaklı arıza masrafı 19.1'e göre e-isa'ya aittir. Fesihte cihaz 7 iş gününde iade edilir; 21.5 uyarınca iadeye kadar kullanım bedeli takibi gerekir. Ayrıntılar madde incelemesinde açıklanmıştır.
- Mevcut `KIRALIK` kayıtlar otomatik olarak tahsise çevrilmez; eski koşullar korunarak dönüşüm eşlemesi yapılır.
- Cihaz planının tüm faturalarının kesilmiş olması, tüm taksitlerin ödenmiş olması değildir. Mülkiyet takibi gerçek tahsilata dayanmalı; tahsis cihazı e-isa mülkiyetinde kalmalıdır.
- Cihaz planı ile fiziksel seri numaraları ilişkilendirilir. Değişim/ikame/iade olayları eski teslim belgesini değiştirmeden yeni kayıtla izlenir.

## 7. Bölge kayıt sistemi

Kesinleşen kapsam: bağımsız **Bölge Yönetimi** ekranında bölge adı/kodu ve kapsadığı iller/ilçeler yönetilir. Bölge kaydı oluşturmak için sözleşme gerekmez. Sözleşme, eczanenin konumundan ilgili bölgeyi okuyarak Ek-1 G'de yalnız o bölgenin adı, kapsamı ve ilgili cihaz/sponsor parametrelerini gösterir. İlgisiz bölgeler ve tüm bölge listesi belgeye basılmaz; sabit sözleşme hükümleri korunur.

Önerilen kurallar:

- İl seçimi tüm ilçeleri, ilçe seçimi yalnız seçilen ilçeyi kapsar. Aynı eczanenin hem il hem ilçe seçiminden eşleşmesi mükerrer üyelik oluşturmaz.
- Başlangıç için bir eczane aynı tarihte tek ticari bölgeye ait olsun; çakışan bölgeler kayıt sırasında gösterilsin ve engellensin. Çoklu bölge ihtiyacı varsa dağıtım kuralı ayrıca tasarlanmalıdır.
- Bölge bulunamazsa boş veya tahmini bölgeyle belge kesinleştirilmesin; admin kapsamı tamamlasın.
- Bölge kaydında kapsam, geçerlilik tarihleri ve sözleşmeye basılacak cihaz/sponsor parametreleri tutulabilsin. Planlanan cihaz sayısı hedefi ile kesin sponsor sınırı ayrıştırılsın.
- Bölge değişikliklerinin yürürlük tarihi ve eczane üyelik geçmişi saklansın. Adres veya kapsam değişikliği imzalı sözleşmeyi ve kapanmış hakedişi değiştirmesin; gerekli panel bildirimi ayrı üretilsin.
- Ticari bölgeyle mevcut cihaz bazlı yayın ataması ilişkilendirilsin. Bölgeye sonradan eklenen cihazın kampanyalara otomatik katılıp katılmayacağı ayrıca kararlaştırılsın.

## 8. Sponsorluk paketleri ve tarihli tarifeler

Bağımsız **Sponsorluk Tarifeleri** yönetim ekranı olacaktır. Paket, satılan kapsamı; tarife sürümü, bu kapsamın belirli dönemdeki fiyat ve koşullarını temsil eder. Sözleşme oluşturulurken mevcut takvimde geçerli ve ilgili bölge/kapsama uygun kayıtlar Ek-1 H'yi doldurur; tüm tarihçe veya ilgisiz bölge tarifeleri basılmaz. Kullanıcının istediği zorunlu tarife ilişkisi yeni kampanya kayıtlarına uygulanacaktır.

| Kayıt | Önerilen alanlar |
|---|---|
| Paket | Kod/ad, eczane veya bölge sponsorluğu, kiosk/panel/etken madde sayfası/QR kapsamı, eş zamanlı sponsor sınırı, aktiflik. |
| Tarife sürümü | Paket, bölge veya genel kapsam, geçerlilik başlangıcı/bitişi, tutar, para birimi, KDV, fiyatın KDV dahil/hariç olduğu, cihaz/eczane/sabit/kademeli fiyatlama. |
| Giriş ve devam koşulları | Giriş fiyatı, giriş süresi/taahhüt ayları, devam fiyatı ve ara verip dönen sponsor kuralı. |
| Kampanya ticari kaydı | Sponsor, seçilen paket/tarife sürümü, hedef kapsam, ticari başlangıç/bitiş ve kararlaştırılan bedellerin sabit kopyası. |
| Sözleşmedeki tarife görünümü | Oluşturma tarihinde geçerli, ilgili bölgeye uygulanabilen tarifeler ve paket kapsamlarının sabit kopyası. |

Önerilen işleyiş:

1. Admin paketleri ve tarihli tarife sürümlerini kaydeder.
2. Yeni eczane sözleşmesinde oluşturulma tarihine uygun tarife seti Ek-1 H'ye getirilir. Eczanenin ödediği aylık kullanım bedeli ile sponsorun ödediği tarife ayrı kalır.
3. Yeni kampanyada paket ve geçerli tarife seçimi zorunludur. Uygun kayıt yoksa rastgele fiyat seçilmez.
4. Aynı paket/bölge/dönem için belirsiz tarife çakışması engellenir. Bölgeye özel ve genel tarife birlikte varsa öncelik kuralı kararlaştırılır.
5. Yeni tarife sürümü eski imzalı belgeyi ve sponsor anlaşmasının sabit temel fiyatını kendiliğinden değiştirmez. Ek-1 H'deki özel kural ayrıca modellenir: 15 cihaz üstündeki her ilave cihaz için faturalama günündeki güncel tarife esas alınır. Temel tarife sürümüyle bu ilave birim tarifesi ayrı izlenir. Kampanya yayın süresinin tarife geçerlilik sonunu aşması tek başına genel fiyat değişimi doğurmaz.
6. Paket kapsamı yayın yerleşimleriyle eşleştirilir. Yalnız paketi seçmek panel banner'ı veya QR sponsorluğunun fiilen açıldığı anlamına gelmez; kapsamın yerine getirilmesi izlenir.

Sözleşme oluşturulurken geçerli takvim tarifesi seçilir ve belge sürümünde korunur. Önerilen teknik tarih aralığı başlangıç dahil, bitiş hariçtir; kullanıcıya son geçerli gün anlaşılır gösterilir. Kampanyanın ileri tarihli yayın başlangıcı için istisnai tarife seçimi ve genel/bölgesel tarife önceliği açık iş kuralıdır. Referans tarihler Türkiye yerel takvimine göre saklanmalıdır.

İlk kez gelen/ara verip dönen sponsorun anlaşılabilmesi için serbest firma adı tek başına yeterli değildir. Kalıcı sponsor kaydı ve anlaşma geçmişi önerilir. Mevcut kampanyaların yeni paketlerle eşleştirilmesi geçiş aşamasında ayrıca yapılır.

## 9. Sözleşme ile uygulama farklarının takip listesi

Belge üretimi tamamlanınca aşağıdaki tüm işlevlerin sağlandığı varsayılmayacaktır. İlk yayına hangi maddelerin yazılımla, hangilerinin sorumlu personel tarafından takip edilerek karşılanacağı ayrıca belirlenecektir.

| Konu | Mevcut tespit | Planlanan karşılık |
|---|---|---|
| Şablonlar | Eski 22 maddelik metin ve %10 katkı payı ifadesi var. | Yeni ana sözleşme + Ek-1 ve ayrı Ek-2; eski onaylar korunur. |
| Başlangıç/teslim | Tek başlangıç alanı var; Ek-2 yaşam döngüsü yok. | K7 eşitliği, demo geçmişi, ayrı imza/yükleme tarihleri ve iki belge takibi. |
| Onay kanıtları | Tarih/IP/HTML ve tek ıslak dosya yolu var. | Belge sürümleri, gerçek imza olayları, iki belge ve gelecekteki doğrulama sağlayıcıları. |
| Önemli hükümler | Panelde genel kabul var. | Islak belgede Ek-1 J korunur; gelecekte dijital akışta ayrıca gösterim/kabul kaydı. |
| Süre/yenileme | 12/24/36 ay, manuel uzatma. | Kaynaktaki 24 ay + öteleme, 60 gün bildirim, 12 ay yenileme; farklı sürelerin kullanılma kararı bekliyor. |
| Öteleme | Kullanım ve cihaz ötelemesi ayrı; arayüz sınırı 36 ay. | Kaynaktaki azami 6 ay, varsa bedel, erken sona erdirme ve hakediş dışlama. |
| Fatura ve vade | Birleşik yeni fatura kapatıldı; abonelik ve her cihaz planı ayrı üretiliyor. | Bağımsız öteleme, kesimden 7 iş günü vade ve resmi tatil hesabı uygulandı. |
| KDV ve tahsilat tutarı | Ayrı faturalar kalem bazlı matrah, KDV ve tevkifat snapshot'ı taşıyor. | Gerçek/kısmi tahsilat sağlayıcısı ve mahsup akışı ayrıca tamamlanacak. |
| Gecikme/yeniden açma | Gecikme kilidi ve açma bedeli mevcut. | Faiz, mahsup sırası, %30 sınırı, gerekli ödemeler tamamlanınca yeniden açma. |
| Kiosk kısıtlaması | Panel kısıtı var; kiosk abonelik kısıtı görünmüyor. | Sponsor yayını devam ederken kullanım arayüzünü ayrı kısıtlama. |
| Fiyat güncelleme | Tarihli fiyat tanımları var; tam endeks akışı yok. | Aktivasyondan 12 ay sabit fiyat, endeks, bildirim ve itiraz/fesih süreci. |
| Katkı payı | Yayın/log var; sponsor tahsilatı ve hakediş muhasebesi görünmüyor. | Tahsil edilen KDV dahil tutardan %15, bölge dağıtımı, bildirim, fatura, mahsup, ödeme. |
| Sponsor alacağı ve tahsilatı | Campaign üzerinde firma adı serbest metin; mali anlaşma/ödeme planı yok. | Kalıcı sponsor, kampanya-tarife bağlantısı, sponsor borcu, gerçek/kısmi tahsilat, tahsilat dağıtımı ve bakiye. |
| Sponsor bildirimi | Genel duyuru altyapısı var. | Yayın öncesi sponsor bildirimi, ilişkili taraf bilgisi ve gönderim kaydı. |
| Sponsorluk kapsamı | Kiosk, panel kampanyası ve QR logo bağımsız. | Paket ve gerçek yerleşim eşleşmesi; etken madde sayfası kapsamının geliştirilmesi. |
| İçerik/veri ilkeleri | Marka önermeme mesajı ve analitik kayıtlar var. | Sabit uyarı, bilgilendirme, içerik inceleme ve dış raporlarda asgari yanıt eşiği. |
| Cezai şart | Kalan ay × katsayı × bedel. | Kalan ücretli süre, 2–12 aylık sınırlar ve istisnalar. |
| Garanti/servis/iade | Genel destek talebi altyapısı var. | Garanti tarihi, servis süresi, cihaz değişimi, iade ve fesih sonrası hesaplaşma. |
| Gerçek ödeme/SMS | Tahsilat akışı mock/manuel; SMS tarifesi/bakiye sistemi görünmüyor. | Manuel havale teyidi sınırı ve ileride ödeme/SMS entegrasyonlarının ayrı planı. |

### 9.1 Katkı payının ayrıca tasarlanması

Bölge ve tarife kaydı katkı payı hesabını tek başına çözmez. Gerekli kayıt zinciri:

`Sponsor → anlaşma/kampanya → tahsilat → ilgili dönem ve kapsam → aktif cihaz-gün → hakediş → eczaneye hesap bildirimi → eczane faturası → mahsup/ödeme`

Hesaplar:

- Eczane bazlı: ilgili eczane için tahsil edilen KDV dahil sponsorluk tutarı × %15.
- Bölge havuzu: ilgili dönem/kapsam için tahsil edilen KDV dahil sponsorluk tutarı × %15.
- Eczane bölge payı: havuz × eczanenin uygun aktif cihaz-günü / bölgenin toplam uygun aktif cihaz-günü.
- Abonelik ötelemesi nedeniyle kullanım faturası kesilmeyen dönem için katkı doğmaz, birikmez ve sonradan ödenmez; ilgili cihaz-günler dağıtıma ve paydasına alınmaz. Cihaz faturası tek başına katkı engelini kaldırmaz. Bir cihazın eczane ve bölge sponsorluğu ayrı hesaplanır.
- Bir tahsilat iki kampanya/eczane/bölge için mükerrer hakediş doğuramaz; bedelin kapsama dağılımı kaydedilir.

**6–15 cihaz tarifesi için zorunlu örnekler:** Aynı bölge sponsorluğundan 36.000 TL KDV dahil bedelin tamamı tahsil edilmiş ve katkı oranı %15 ise havuz 5.400 TL'dir. Aşağıdaki örneklerde her eczanede tek cihaz vardır; bütün cihazlar 30 gün katkıya uygun aktiftir ve ötelemede değildir.

| Bölgedeki uygun cihaz | Toplam cihaz-gün | Bir eczanenin cihaz-günü | Bir eczanenin yaklaşık payı |
|---|---|---|---|
| 7 | 210 | 30 | 5.400 × 30 / 210 = 771,43 TL |
| 14 | 420 | 30 | 5.400 × 30 / 420 = 385,71 TL |

Sponsorun ödediği toplam aynı kalsa da 14 cihazlı örnekte tek cihazlı eczanenin payı yarıya iner. İki cihazlı eczanenin payı uygun cihaz-günleri toplamından hesaplanır; eczane başına eşit bölmek doğru değildir.

Ayın ilk 15 günü 7, son 15 günü 14 uygun cihaz varsa toplam `7 × 30 + 7 × 15 = 315` cihaz-gündür. İlk 7 eczanenin her biri yaklaşık `5.400 × 30 / 315 = 514,29 TL`, sonradan gelen 7 eczanenin her biri yaklaşık `5.400 × 15 / 315 = 257,14 TL` pay alır. Ay sonundaki 14 sayısına doğrudan bölmek yanlış olur. Kuruş farkları toplam dağıtımı 5.400 TL'ye eşitleyen deterministik bir yöntemle dengelenmelidir; tablodaki değerler yuvarlanmış örnektir.

Tarife için kullanılan ticari cihaz adedi ile katkı dağıtımındaki uygun cihaz-gün ayrı veridir. Ötelemedeki veya katkıya uygun olmayan bir cihazın tarifedeki cihaz adedini de otomatik azaltacağı varsayılmaz. Kısmi tahsilat halinde havuz yalnız tahsil edilen KDV dahil tutarın %15'idir. Geçmiş dönem, bugünkü cihaz sayısına göre yeniden bölüştürülmez.

Gerekli açık kararlar: kısmi ve geç tahsilatın dönemi, iadeler, peşin çok aylık tahsilat, kısmi gün, kesinti kanıtı ve kusur nedeni, hiç uygun cihaz bulunmaması, kuruş yuvarlaması. Son görülme ve gösterim logu tek başına kesintinin kusurunu kanıtlamaz. Tahsilat olmadan yalnız tarife fiyatından hakediş üretilmez. Bölgesel analiz satış geliri 20.4/g gereği sponsorluk geliriyle karıştırılmaz; Ek-1 F'de aksi yoksa katkı payı doğurmaz.

Sözleşmedeki 10 iş gününde hesap bildirimi, eczane faturası tebliğinden sonra 15 günde ödeme ve mahsup işlemlerinin süreleri ayrı izlenmelidir. Eczaneye ödeme yapılacak banka hesabı, şirketin tahsilat IBAN'ından ayrı bilgidir.

Ay bitmeden tahsilat alındığında 10 iş günlük bildirim süresi dolabilir; buna karşın 25.6'daki aylık toplam Aktif Cihaz-Gün henüz kesinleşmemiş olabilir. Ara bildirim/kesin hesap yönteminin nasıl uygulanacağı açıkça kararlaştırılacak; sırf ay sonunu beklemekle bildirim süresi otomatik ertelenmiş sayılmayacak. 25.1'de bölgenin bir kısmına yayın yapılabilmesi ile 25.6'daki bölge toplamı ifadesinin dağıtım kapsamı ayrıca kaydedilecek; payda kendiliğinden yalnız kampanyaya atanmış cihazlara indirgenmeyecek.

### 9.2 Sponsor tahsilatı ve eczane bildirimleri

Üç ayrı para yönü vardır: eczaneden e-isa'ya kullanım/cihaz bedeli, sponsordan e-isa'ya sponsorluk tahsilatı, e-isa'dan eczaneye katkı payı. Aynı ödeme kaydı bu yönlerin yerine kullanılmaz.

Önerilen ekranlar: **Sponsorlar**, **Sponsor Alacakları ve Tahsilatları**, **Katkı Payı Hesapları**, **Eczacı Paneli Katkı Paylarım ve Bildirimler**. Bunlar bağımsız Bölge Yönetimi ve Sponsorluk Tarifeleri ekranlarının mali devamıdır.

Sponsor tahsilatında firma, kampanya/anlaşma, dönem/kapsam, gerçek ödeme tarihi, KDV dahil tutar, yöntem, referans/dekont, kısmi tahsilat ve kalan bakiye izlenir. İlk aşamada yetkili manuel banka teyidi kullanılabilir; otomatik banka/kart entegrasyonu ayrıca kararlaştırılır. Sponsor ödeme vadesi bu iki eczane belgesinde kesin belirlenmemiştir; sponsor anlaşmasından alınır.

| Olay | Kime / süre / kanal | Gereken kayıt |
|---|---|---|
| Sponsor teklifi (25.4) | Aynı bölgedeki sponsor adaylarına eş zamanlı ve yazılı. | Teklif sürümü, alıcılar, ortak gönderim zamanı ve koşullar. Eczane bildirimiyle karıştırılmaz. |
| Yeni sponsor veya sponsor içeriği (16.5, 25.5, 25.8) | İlgili eczanelere yayın başlamadan önce panel bildirimi; e-posta ek kanal olabilir. | Yayın/içerik sürümü, hedef eczaneler, gönderim zamanı; ilişkili taraf varsa açıklama. Eczacı onayı aranmaz. |
| Bölge kapsamı değişikliği (25.2) | Etkilenen eczanelerin paneline. | Eski/yeni kapsam, yürürlük tarihi, bildirim kaydı. |
| Katkı payı hesap bildirimi (13.2/d, Ek-1 F) | Tahsilattan sonra en geç 10 iş günü içinde eczane paneline. | Tahsil edilen toplam, oran, havuz, bölge/eczane cihaz-günü, pay, varsa mahsup ve net tutar. |
| Hesaba itiraz (Ek-1 F) | Bildirimden 15 gün; kaynakta “öneri” işareti korunur. | İtiraz tarihi, gerekçe, inceleme ve düzeltme geçmişi. |
| Eczane faturası ve katkı ödemesi (13.2/e) | Faturanın e-isa'ya tebliğinden 15 gün içinde ödeme. | Fatura numarası/dosyası, tebliğ tarihi, son ödeme tarihi, gerçek ödeme/dekont. |
| Ödeme gecikmesi ve hizmet kısıtı (13.1/a) | Opsiyon sonrası panel/SMS/e-posta ile bilgi. | Borç/vade, gönderim, kısıt başlangıcı. Sponsor yayınları devam eder. |
| Endeksi aşan fiyat artışı (13.4, Ek-1 C) | 15 gün önceden yazılı bildirim. | Yeni tarife, yürürlük, gönderim; itiraz/fesih kaydı. |
| İhtar ve fesih (14.2, 21, 26.1) | KEP veya noter. | Dışarıda yürütülse bile gönderim/tebliğ belgesi ve işlem tarihi; panel mesajı bunun yerine sayılmaz. |
| Fesih sonrası hesaplaşma (21.6) | Eczaneye son hesap bildirimi. | Kalan borç, tahsil edilmiş katkı payı, mahsup ve ödenecek bakiye. |

Operasyonel bildirimlerde gönderim ve okunma ayrı kaydedilir; 26.1 gönderim anını esas alır. Mevcut tek seferlik duyurunun yalnız ilgili gün görünmesi kalıcı mali bildirim arşivi için yeterli değildir. Hesap ekranı sponsor kimliklerini ve özel sponsor anlaşmasını ifşa etmez (25.7); yayın öncesi bilgilendirme ve ilişkili taraf açıklaması ayrı içerik kurallarına sahiptir.

### 9.3 Uygulanan faturalandırma kararları

- Üretim ve admin çağrıları `faturala_ayri` yolunu kullanır. Eski `faturala_aylik_birlesik` entegrasyon adı geriye uyum için ayrı üretime yönlenir; yeni `BIRLESIK` kaydı oluşturmaz.
- Abonelik ve her cihaz ödeme planı bağımsız faturadır. Aynı ayda birden fazla cihaz planı birbirini engellemez; her planın tekilliği kendi kimliğiyle korunur.
- Abonelik ve cihaz ötelemesi ayrı başlangıç tarihleriyle uygulanır. Öteleme dönemine borç üretilmez; ıslak imzalı dosyanın sonradan yüklenmesi takvimi değiştirmez.
- Kesim/hizmet dönemi ile matrah, KDV, tevkifat ve ödenecek tutar faturada sabitlenir. Vade kesimi takip eden 7 iş günüdür; `GRACE_DAYS` bunun ardından gelen erişim toleransıdır.
- Eski birleşik faturalar bölünmez veya yeniden yazılmaz. Mükerrerlik kontrolü, eski faturada aynı kalem varsa yeni ayrı borç üretmez.
- Gerçek ödeme sağlayıcısı, kısmi tahsilat/mahsup ve bazı sözleşmesel bildirimler halen ayrı tamamlanma konularıdır.

### 9.4 Hedef faturalandırma akışı

Kesin kural: ilk fatura ilgili kalemin ödeme başlangıcında oluşur. `İlk abonelik faturası = sözleşme başlangıcı + abonelik öteleme süresi`; `ilk cihaz faturası = sözleşme başlangıcı + cihaz ödeme öteleme süresi`. Süre 0 ise o kalem sözleşmeyle başlangıçta faturalanır. İki öteleme bağımsızdır: yalnız birinin ötelenmesi diğerinin faturasını bekletmez. Abonelik ve cihaz aynı gün kesilse bile tek faturada birleşmez; abonelik ve her cihaz planı ayrı fatura olur. Her iki kalem de ötelenmişse sözleşme kurulurken bunlara ait fatura oluşmaz. Bu, başlangıçta fatura kesip son ödeme tarihini ileri taşıma değildir. Tahsiste ayrıca kararlaştırılmış bir cihaz bedeli yoksa hayali cihaz faturası üretilmez.

Belge yüklenmesi bu tarihleri değiştirmez. Abonelikte öteleme dönemine kullanım borcu üretilmez; cihaz ötelemesi kararlaştırılmış cihaz borcunu silmez, ilgili planın başlangıcını taşır. Sonraki kullanım faturaları ödeme başlangıcına bağlı aylık dönem başlarında oluşur. Dönem başlangıcı/bitişi, fatura kesim tarihi ve son ödeme tarihi ayrı alanlardır.

Ötelemesiz örnek: sözleşme 8 Kasım'da oluşturulup aynı gün başlıyorsa 8 Kasım–8 Aralık dönemi için ilk kullanım faturası 8 Kasım'da oluşur. Sonraki fatura 8 Aralık'ta, ardından 8 Ocak'ta oluşur. Her birinin son ödeme tarihi kendi gerçek kesim tarihini takip eden 7 iş günüdür. Kesim günü sayılmaz; hafta sonları ve uygulanan resmi tatiller hesaba katılır. Günlük görev aynı dönem için ikinci fatura üretmez; başlangıçta faturalanabilir kalem varsa sözleşme kaydı ve o ilk fatura birlikte başarılı olur veya birlikte geri alınır. Ötelemeli kalemler kendi ödeme başlangıcında üretilir.

| Başlangıç: 8 Kasım 2026 | İlk abonelik faturası | İlk cihaz faturası, cihaz borcu varsa |
|---|---|---|
| İkisinde de öteleme yok | 8 Kasım 2026 | 8 Kasım 2026 |
| Abonelik 2 ay, cihaz 0 ay | 8 Ocak 2027 | 8 Kasım 2026 |
| Abonelik 0 ay, cihaz 3 ay | 8 Kasım 2026 | 8 Şubat 2027 |
| Abonelik 2 ay, cihaz 3 ay | 8 Ocak 2027 | 8 Şubat 2027 |

**Katkı uygunluğu:** Abonelik ötelemesi nedeniyle kullanım faturası kesilmeyen döneme eczane veya bölge katkı payı doğmaz; ödeme yapılmaz, bekleyen alacak birikmez. Yukarıdaki 2 aylık abonelik ötelemesinde 8 Kasım–8 Ocak aralığı katkı dışıdır; 8 Ocak'ta kullanım faturalandırması başladığında yalnız uygun sonraki günler hesaba girer. Öteleme döneminin sponsor tahsilatı sonradan gelse de o günler için geriye dönük hakediş üretilmez. Yalnız cihaz faturası kesilmiş olması kullanım ötelemesindeki eczaneyi katkıya uygun yapmaz. Bu dışlama abonelik ötelemesine dayanır; cihaz ödeme planı ayrı izlenir. Faturalanmış olmak faturanın ödendiği anlamına gelmez; tüm faturaların ödenmiş olmasını yeni hakediş şartı yapmadan sözleşmedeki mahsup hükümleri uygulanır. Teknik hata nedeniyle kullanım faturası üretilmemişse otomatik katkı ödemesi bekletilip faturalandırma düzeltilir; bu hata sözleşmesel öteleme veya hakediş silme olarak kaydedilmez.

İleri/geri tarihli kayıt istisnası ekip soru listesinde tutulur; normal akışın dönem başı kesim kararı tekrar açılmaz. İleri tarihli taslakla fiilen başlayan sözleşme aynı olay sayılmaz; gerçek kesim tarihi geçmişe yazılarak yapay gecikme oluşturulmaz.

Bildirim planı: fatura oluşturulduğunda tutar, dönem, kesim ve son ödeme tarihini içeren bildirim; vade yaklaşırken belirlenen eşiklerde hatırlatma; son ödeme geçince gecikme bildirimi. Mevcut panel uyarıları ve sistem duyuruları tek vade alanını kullanmalıdır. Vade düzeltildiyse bekleyen hatırlatmalar yeniden hesaplanır; ödeme/iptal sonrasında o borç için gelecek hatırlatmalar durur. Vade sonrası hizmet durdurma opsiyonu, 7 iş günlük ödeme süresinden ayrıdır; süresi ekip soru listesinde saklanır.

Cihaz için ayrıca öteleme kararlaştırılmamışsa peşin bedeli imza veya teslimde; vadeli bedeli Ek-1 B'deki takvimde ödenir. Cihaz ötelemesi varsa ilk kesim başlangıç + cihaz ödeme ötelemesidir ve ödeme planı bu başlangıçla tutarlı hazırlanır. Kullanım bedeline ait 7 iş günü kuralı cihazın kararlaştırılmış taksit vadesini otomatik kaydırmaz. Farklı vadeler tek faturada eritilmez; ayrı belge veya açık borç kalemleriyle yönetim tasarlanır.

Ödeme sonrasında kalan borç, varsa faiz/masraf ve mahsuplar izlenir. Yeniden açma bedeli %30 sınırını aşamaz ve gerekli ödeme/eksiklikler tamamlanmadan açılmış sayılmaz. Fesihte e-isa mülkiyetindeki cihaz iade edilmemişse 21.5'teki kullanım bedeli takibi, normal abonelik faturalarının durmasından ayrı devam etmelidir.

### 9.5 Sözleşmeye sabit ceza kuralı

K15 gereği yeni sözleşmelerde eski genel fiyat tanımındaki `iptal_ceza_orani` katsayısı erken fesih hesabını belirlemeyecek. Madde 18.2 ve Ek-1 I esas alınacak: cezaya tabi fesihte kalan ücretli süreye ait kullanım bedeli toplamı, 2 aylık alt ve 12 aylık üst sınır arasında tutulur. Madde 18.3'te ceza uygulanmayan haller ayrıca kontrol edilir; bunlarda tutar sıfırdır. Normal süre sonu ve usulüne uygun yenilememe otomatik cezalı fesih sayılmaz.

Sabit aylık bedelin B olduğu basit örnekte, cezaya tabi fesih için `min(max(kalan ücretli süre bedeli, 2 × B), 12 × B)` uygulanır. Kalan ücretli süre 1 ay ise 2B, 6 ay ise 6B, 18 ay ise 12B; istisna halinde 0. Kısmi ay, fiyat güncellemesi ve öteleme döneminde kalan ücretli sürenin ayrıntıları ekip sorularında korunur. “Sabit” tek bir TL ceza veya tüm iptallere otomatik ceza anlamına gelmez.

İmzalanmış eski sözleşmelerin farklı şartları geriye dönük değiştirilmez. Yeni kural sözleşme/şablon sürümüne bağlanır; fiyat tanımının ileride değişmesi bu sözleşmenin ceza kuralını değiştirmez. Yeniden açma bedeli (%30 üst sınır) ve gecikme faizi erken fesih cezasıyla tek alan altında birleştirilmez.

## 10. Açık kararlar

Bu listedeki öneriler kullanıcı tarafından kabul edilmiş karar değildir. Çözülmemiş konuların iş sonu görüşme kaydı [ekip soru listesinde](abonelik-sozlesme-ekip-sorulari.md) tutulur; bu aşamada tekrar tekrar kullanıcıya sorulmaz. A3, A6 ve A10 çözülmüştür.

| No | Netleşecek konu | Öneri / etkisi |
|---|---|---|
| A1 | Tahsis bedeli alanının ticari kullanımı nedir? | Metin aylık kira veya bedelsizlik zorunluluğu getirmiyor. Donanım değeri, varsa tahsis bedeli ve kullanım bedeli ayrı tutulacak. |
| A2 | Garanti süresi kaç ay? | Başlangıç K10 ile kesinleşti; süre boş alan olarak tamamlanacak. |
| A3 | Çözüldü: dosya yüklemesi başlangıcı etkiler mi? | Hayır. Başlangıç tarihi esas; yükleme veya saha teyidi engeli yok. |
| A4 | Standart süre yalnız 24 ay mı; 12/36 ay ve demo seçenekleri nasıl kullanılacak? | Demo akışını korumak; yeni standart için kaynak belgeyle uyumlu varsayılan kullanmak. Taksit esnekliği, süre esnekliğini kendiliğinden onaylamaz. |
| A5 | Taksit üst sınırı, ilk taksit tarihi ve tahsis/satışın aynı sözleşmede birlikte olması? | Satır bazlı plan; kullanıcıda 0=peşin. Azami taksit için ayrıca ticari karar. |
| A6 | Çözüldü: ilk kullanım faturası ne zaman kesilir? | Başlangıç + abonelik ötelemesi tarihinde; öteleme yoksa sözleşmeyle başlangıçta. Cihazın ötelemesi ayrı uygulanır. Son ödeme kesimden 7 iş günü sonra; sonraki kullanım kesimleri ödeme başlangıcına bağlı aylık dönemlerde. |
| A7 | Bir eczane birden fazla bölgeye girebilir mi? | Başlangıçta tek bölge ve çakışmayı engelleme. Bölgesiz eczanede belgeyi kesinleştirmeme. |
| A8 | Yeni cihaz bölge kampanyalarına kendiliğinden katılır mı? | Ticari kapsam, yayın kapasitesi, sponsor bildirimi ve fiyat kademesi birlikte değerlendirilmeli. |
| A9 | Kampanyanın tarife referans tarihi ve genel/bölgesel öncelik? | Sözleşmede oluşturma tarihi kararı uygulanır. Kampanyada kayıt veya ticari başlangıç ayrıca seçilmeli. |
| A10 | Çözüldü: belgeye hangi takvim tarifesi basılır? | Oluşturma anındaki geçerli tarife; imzalı dosya sonradan yüklendiğinde yeniden fiyatlandırılmaz. |
| A11 | Ertelendi: depozito, öteleme bedeli ve “öneri/teyit” değerleri. | Kullanıcı sonraki hukuki görüşmelerden sonra ele alacak. Şimdiki ifadeler korunacak. |
| A12 | Ek-2'de elektronik onay kayıt no etiketinin ıslak imzadaki gösterimi? | Yönteme göre imza tarihi ve belge kayıt numarası; sahte elektronik onay üretmeme. |
| A13 | Cihaz değişimi/ikame hangi ek kayıtla izlenecek? | Eski imzalı Ek-2 değiştirilmez; yeni cihazın seri ve teslim geçmişi ek kayıtla ilişkilendirilir. Başlangıç K10 ile sabit. |
| A14 | Katkı payında tahsilat/dönem, kesinti, yuvarlama ve sıfır payda kuralları? | 9.1'deki örneklerin ticari olarak kararlaştırılması; ilk hakedişten önce tamamlanması. |
| A15 | İlk sürümde hangi sözleşme yükümlülükleri yazılımla, hangileri operasyonla takip edilecek? | Her açık yükümlülüğe sorumlu ve kayıt yöntemi atamak; belge üretimini tam işlev uyumu gibi sunmamak. |
| A16 | Eski sözleşme ve kampanyalar nasıl geçirilecek? | Yeni kayıtlar yeni şablonla; eski imzalı şartlar korunarak kontrollü eşleme. |
| A17 | 13.1/a'daki hizmet durdurma opsiyon süresi kaç gün? | Ek-1'de açık değer yok. Kodun mevcut 7 takvim günü sözleşmedeki 7 iş günü fatura vadesi yerine kullanılamaz; hukuki karar bekleyen listeye alınır. |
| A18 | Sponsorun kendi ödeme vadesi ve yöntemi nasıl belirlenecek? | Eczane sözleşmesindeki 7 iş günü sponsor borcuna otomatik uygulanmaz. Sponsor anlaşması/ödeme planından alınmalıdır. |

Kaynak metinlerde ayrıca ana sözleşme 2.5'in yalnız Ek-1'i sayması ve Ek-2'nin kendini ayrılmaz parça olarak tanımlaması not edilmiştir. Sabit maddeler değiştirilmeyeceği için bu plan söz konusu atfı düzeltmez. Aktif Cihaz-Gün tanımındaki kesinti ifadeleri ile hesap uygulaması da net bir ticari kurala bağlanmalıdır.

## 11. Önerilen geliştirme sırası

| Aşama | İş | Tamamlanma ölçütü |
|---|---|---|
| 0 | Açık kararlar, sabit/değişken alan listesi, örnek hesaplar. | Ticari kurallar ve ilk yayına dahil kapsam net. |
| 1 | Cihaz/seri kayıtları, tahsis/ödeme planı, tarih ayrımları. | Demo sonrası ve doğrudan işlem için tutarlı veri oluşturulabiliyor. |
| 2 | Bölge, sponsor, paket ve tarihli tarife kayıtları. | Eczane bölgesi ve sözleşme tarifesi belirleniyor; yeni kampanya paketsiz kaydedilemiyor. |
| 3 | İki belge üretimi, imzalı yükleme, sürüm ve arşiv. | Sabit metin korunuyor; dinamik tablolar ve iki imzalı belge izleniyor. |
| 4 | Faturalandırma bulgusu ve sözleşmeye bağlı mali/erişim kuralları. | Dönemler, gerçek ödeme, öteleme, yenileme, mülkiyet ve kısıtlar belirlenen kurala uygun. |
| 5 | Sponsor tahsilatı, katkı payı ve bölge dağıtımı. | Örnek hesaplar, bildirim, eczane faturası, mahsup ve ödeme uçtan uca izleniyor. |
| 6 | Kalan bildirim, servis, içerik/veri ve entegrasyon işleri. | 9. bölümdeki her gereksinimin yazılım veya operasyonel karşılığı doğrulanmış. |

Aşamaların ayrı hazırlanması, sözleşmesel yükümlülüklerin kendiliğinden ertelendiği anlamına gelmez. İlk yayında eksik kalan işlemler için nasıl ve kim tarafından yerine getirileceği A15 ile belirlenir.

Muhtemel etki alanları: `backend/apps/abonelik`, `pharmacies`, `lookups`, `sirket`, `campaigns`, `announcements`, `destek`; panelde `AbonelikYonetimi.vue`, `HesabimOdemeler.vue`, `SozlesmeForm.vue`, `SozlesmeMatbu.vue`, cihaz ve sponsorluk ekranları. Kiosk erişim kısıtı seçilen aşamada `kiosk_api`, edge API ve kiosk UI'yi de etkiler. Yeni model/endpoint adları uygulama aşamasında kesinleştirilecektir.

Uygulama yapıldığında ilgili `docs/ai/01-backend.md`, `02-web-panels.md`, `05-cross-project-flows.md`, `06-db-and-api-contracts.md`, `08-dooh-advertising.md` ve changelog birlikte güncellenecektir.

## 12. Doğrulama ve geçiş ölçütleri

- Aynı demo cihazıyla standart sözleşmeye geçiş ve doğrudan satış/tahsis ayrı doğrulanır; seri kimliği ve geçmiş kaybolmaz.
- Satışta 0=peşin, 6 taksit ve tahsis çıktıları; farklı model/adet ve üçten fazla cihaz; son taksit yuvarlaması doğrulanır.
- Ana sözleşme + Ek-1 ile Ek-2'nin eczane, edinim, cihaz ve başlangıç verileri aynı olur.
- Ek-2 Bölüm 4, 5 ve 7 elle işaretlemeye uygun boş kalır. Sabit maddelerde metin farkı bulunmaz. Üretilen belge sayfaları taşma, kırpılma ve imza alanları açısından görsel olarak incelenir.
- İmza tarihi, başlangıç ve yükleme tarihi farklı olduğunda doğru tarihler korunur; yalnız bir belge yüklendiyse belge seti tamamlandı sayılmaz.
- Belgeler hiç yüklenmemiş olsa bile başlangıç tarihi gelince hizmet ve sözleşmeye uygun faturalandırma yürür; belgesizliği tamamlamak için ayrı aktivasyon şartı eklenmez.
- Eczane, banka, bölge ve tarife güncellense bile eski üretilmiş/imzalı belge değişmez. Dosya değiştirme yeni sürüm yaratır.
- Bölge çakışması/bölgesizlik, il ve ilçe tekrar eşleşmesi, ileri tarihli bölge değişimi doğrulanır.
- Tarife başlangıç/bitiş günü, çakışma, uygun tarife bulunmaması, ileri tarihli kampanya ve eski fiyatın korunması doğrulanır.
- Ötelemesiz ve ötelemeli sözleşmelerin ardışık en az üç dönemi; ay sonu ve iş günü vadesi; mükerrer çalışmada tek fatura doğrulanır.
- Abonelik ile cihaz aynı gün doğduğunda iki ayrı fatura; aynı ayda iki cihaz planı olduğunda plan başına ayrı fatura oluştuğu doğrulanır. Eski birleşik mali kayıtlar korunur ve yeni borçla mükerrerleştirilmez.
- Ötelemesiz kalem için sözleşme oluşturma ilk faturayı üretir; ötelemeli kalem yalnız başlangıç + ilgili öteleme tarihinde faturalanır. İkisi de ötelenmişse başlangıçta bu kalemlerden fatura çıkmaz. Yalnız abonelik, yalnız cihaz ve farklı süreli iki öteleme yukarıdaki tabloyla doğrulanır. Günlük görev mükerrer fatura üretmez. Oluşturma işlemi başarısızsa tek başına fatura veya eksik sözleşme kalmaz; imzalı tarama beklenmez.
- Abonelik ötelemesindeki eczaneye katkı hakedişi/ödemesi oluşmaz, geçmiş dönem payı birikmez. Cihaz faturası bu engeli kaldırmaz. Öteleme sonrasında yalnız uygun günler hesaba katılır; sonradan tahsil edilen sponsor bedeli öteleme günlerine geriye dönük pay kazandırmaz. Ötelemedeki cihaz-günler bölge paydasından çıkarılır. Teknik fatura eksikliği ile öteleme ayrı izlenir.
- KDV/tevkifat kalem bazında faturaya aktarılır; fatura borcu ve tahsilat aynı net ödenecek tutarı kullanır. Fatura kesimi + 7 iş günü, vade sonrası gecikme ve hizmet durdurma opsiyonu ayrı doğrulanır.
- Kesim günü, hafta sonu ve resmi tatil içeren vade örnekleri; vade değiştirme, ödeme ve iptal sonrası hatırlatmaların düzeltilmesi doğrulanır. Panel ve sistem duyurusu farklı son ödeme tarihi göstermez.
- Yeni sözleşmede genel fiyat tanımının ceza katsayısı değiştirilse bile 2–12 aylık sözleşme kuralı korunur; cezasız fesih istisnaları, 1/6/18 ay kalan ücretli süre örnekleri ve eski sözleşme sürümü ayrı doğrulanır.
- Kampanya yayına girmeden ilgili eczanelere bildirim oluşur; bildirim için eczacı kabulü beklenmez. Bölge değişikliği ve her hakediş bildirimi ilgili kişi/kapsam/tarihle kalıcı izlenir.
- Faturalanmış fakat ödenmemiş son taksit, mülkiyet devri olarak kabul edilmez. Gerçek tahsilat teyidi olmadan ödeme tamamlandı sayılmaz.
- Katkı payında kısmi tahsilat, öteleme, ay içi kurulum/çıkarma, birden fazla cihaz, sıfır uygun cihaz, iade ve aynı tahsilatı ikinci kez işleme senaryoları doğrulanır.
- 36.000 TL tam tahsilat ve %15 pay için 7 cihaz/14 cihaz örnekleri; ay ortasında 7'den 14'e çıkış; bir eczanede iki cihaz; öteleme nedeniyle paydadan çıkarma ve kuruş dağılımı doğrulanır. Geçmiş hesap güncel cihaz adedinden türetilmez.
- Dosya erişimi eczane/yetki sınırına uyar. Ek dosya türü ve boyutu, yükleme hatası ve yeniden yükleme kontrol edilir; önceki imzalı belge kaybolmaz.

Geçiş önerisi: yeni tablolar/alanlar önce eklenir; mevcut kayıtlar sessizce yeniden yorumlanmaz. Eski kiralık, peşin, demo, imzalı sözleşme ve kampanyalar için eşleme raporu hazırlanır. Yeni sözleşmeler yeni sürüme geçirilir; geçmiş belgeler korunur. Geri dönüş yeni belge üretimini durdurabilmeli, mevcut arşivi ve mali geçmişi silmemelidir.

## 13. İncelenen başlıca kod kaynakları

- [Abonelik modelleri](../backend/apps/abonelik/models.py)
- [Faturalandırma ve onay servisleri](../backend/apps/abonelik/services.py)
- [Belge ve ıslak imza API akışı](../backend/apps/abonelik/views.py)
- [Günlük faturalandırma işi](../backend/apps/abonelik/jobs.py)
- [Mevcut sözleşme şablonu](../backend/apps/abonelik/contract_template.py)
- [Eczane ve cihaz modelleri](../backend/apps/pharmacies/models.py)
- [İl ve ilçe modelleri](../backend/apps/lookups/models.py)
- [Şirket ve banka hesapları](../backend/apps/sirket/models.py)
- [Kampanya ve paketle ilişkilendirilecek yayın modelleri](../backend/apps/campaigns/models.py)
- [Sözleşme formu](../web_panels/src/components/shared/SozlesmeForm.vue)
- [Sözleşme görüntüleme ve onay bileşeni](../web_panels/src/components/shared/SozlesmeMatbu.vue)

Dosya başlangıçta planlama için oluşturulmuştur. Kullanıcının sonraki uygulama yetkisiyle kod ve yerel migration'lar uygulanmıştır. Kaynak Word belgelerinin sabit metinleri değiştirilmemiştir. Güncel uygulama, test kanıtları ve açık işler `abonelik-sozlesme-kod-inceleme.md` dosyasındadır.
