# Sözleşme geçişi kod incelemesi — 8 Kasım 2026

Kapsam: yeni Ek-1/Ek-2 belge seti, tahsis, ayrı abonelik/cihaz faturaları, öteleme, bölge ve tarife yönetimi, sponsor tahsilatı ve katkı hakedişleri.

## Kullanıcı incelemesi sonrası ekran ve belge düzeltmeleri

- `docs/abonelik-sozlesme*.md` kararları yeniden incelendi. Birleşik ticari ayar ekranı kaldırıldı. Bölge, tarife ve sponsor tahsilatı ayrı menü ve sayfalardır; eski ayar bağlantısı tarifeye yönlenir.
- Ekranlar `DefinitionPage` / `DefinitionDialog` ortak bileşenleriyle `styles.css` renk ve bileşen kalıplarına taşındı. Uzun modalda kaydırma, mobil alt işlem düğmelerine erişim ve yatay taşma kontrol edildi.
- Bölge adı + il/ilçe kapsamı; boş ilçe tüm ilçeler. Kod/tarih kullanıcıdan istenmez. Tarife kendi geçerlilik tarihlerini alır; dahili kod sunucuda üretilir. Brüt tarife tutarı KDV dahil olarak gösterilir; sözleşmeye yanlışlıkla tekrar `+ KDV` eklenmez.
- Cihaz Tanımları: fiziksel üretici seri numarası, marka/model, ekran, garanti, donanım değeri ve ayrılan eczane. Kiosk provizyonundan önce kayıt mümkündür. Provizyonda eczane ve seri seçilir; mevcut kioskla sonradan eşleştirme de vardır. Kiosk taşıma fiziksel cihazın eczanesini birlikte günceller.
- Sözleşme planı fiziksel cihazlara bağlanır. Adet/seri uyumu, pasif/yabancı cihaz, aynı istekte tekrar ve tekil kiosk eşleştirmesi kontrol edilir. Seri, MAC veya UUID'den üretilmez.
- Yeni sürümün görüntüleme endpoint'i artık kısa uyarı yerine gerçek kaynak Word'den doldurulmuş tam ana sözleşme/Ek-1 veya Ek-2 HTML'ini verir. Ekrandan Word indirme ve yazdır/PDF vardır. Eczacı kendi üretilen belgesini indirebilir; başka eczaneye erişemez. LEGACY metin ve imzalı dosyalar ayrı korunur.
- Ek-1 edinim/taksit seçimi ve tarihleri gerçek plana bağlandı. Bölge tablosu yalnız ilgili ad/kapsamı gösterir. Başlıksız tarife tablosundaki eski ilk fiyat satırı kaldırılırken paket kapsamı, sponsor sınırı/teyit ve süre hükümleri korunur. Gerçek imza tarihi bilinmiyorsa başlangıç tarihiyle sahte imza tarihi üretilmez.
- Ek-2 bölüm 6 aktivasyon/ödeme başlangıcı `#` alanları doldurulur. 4, 5 ve 7. bölümün gerçek XML tablo indeksleri 3/4/5'tir; bölüm 8 imzalar otomatik bilinen taraf bilgilerini alır. Manuel bölümler kaynakla karşılaştırılır.
- Yereldeki 404 nedeni eski URL'leri bellekte tutan `runserver --noreload` süreciydi. Doğrulanan yerel süreç yeniden başlatıldı. Bölge, tarife, envanter ve belge üretim yolları artık kimliksiz istekte beklenen 401'i verir; kimliği doğrulanmış API testlerinde başarılı yanıtlar kontrol edilir.

## Düzeltilen bulgular

| Bulgu | Düzeltme |
|---|---|
| Fatura yeniden hesaplaması KDV ve tevkifatı düşürüyordu. | Kalem ve fatura vergi kırılımı birlikte yeniden hesaplanır; önceki/sonraki işlem geçmişinde korunur. |
| 29/30/31 başlangıç günü kısa aylardan sonra kayabiliyordu. | Her dönem asıl başlangıç gününden hesaplanır; abonelik ve cihaz ötelemesi bu günü kaybettirmez. |
| Geç oluşturulan dönemlerde kesim tarihi geriye yazılıyordu. | Hizmet dönemi geçmişte kalır; kesim gerçek üretim tarihidir ve 7 iş günü vade bundan hesaplanır. |
| Yuvarlanan taksitlerin toplamı plan toplamından farklı olabiliyordu. | Son taksit matrahı kuruş farkını tamamlar. |
| Eczane ile birlikte veya talep onayıyla açılan sözleşmeler ilk fatura ve ticari snapshot işlemlerini atlıyordu. | Üç giriş yolu aynı sözleşme oluşturma servisini kullanır. |
| Formdaki boş sayısal alanlar tahsis planının kaydını engelleyebiliyordu. | Opsiyonel boş tutarlar normalleştirilir; 0 peşin ve 6 taksit desteklenir. |
| Sözleşme ile cihaz planları düzenleme sırasında ayrı isteklerle kaydediliyordu. | Tek atomik güncelleme kullanılır; yabancı/tekrarlı cihaz kimliği reddedilir ve hatada tüm değişiklik geri alınır. |
| Eski kiralama ve ceza şartları yeni kuralla ezilebiliyordu. | LEGACY kayıtlarının kiralama bilgisi ve ceza katsayısı korunur. |
| Yeni dijital sözleşme eski 22 maddelik HTML metnine onay verebiliyordu. | Yeni belge setinde mevcut imza yöntemi ıslaktır; eski dijital onay akışı LEGACY kayıtlarla sınırlandırılır. Dijital alanlar ve altyapı korunur. |
| Eczacı imzalı dosyaları indiremiyordu. | Ana sözleşme/Ek-1 ve Ek-2 indirmede eczane sahipliği doğrulanır; başka eczanenin dosyası açılmaz. |
| Ek-2'nin elle doldurulacak 7. bölümü değiştiriliyordu. | 4, 5 ve 7. bölüm kaynak şablondaki haliyle korunur. Word uyumluluk ad alanları da çıktıdan düşmez. |
| Kampanya sıradan bir düzenlemede güncel tarife fiyatıyla yeniden yazılıyordu. | Seçili tarifenin snapshot'ı korunur; bağlı tarife boşaltılamaz ve pasif tarife yeni seçilemez. |
| Çakışan bölge kapsamları ve tarife dönemleri belirsiz seçim oluşturuyordu. | API doğrulamaları eklenir; kullanılan tanım ve tahsilatlı kampanya silme hataları anlaşılır 400 yanıtına çevrilir. |
| Katkı hesabı hizmet dönemi yerine takvim ayına bakıyordu. | Gerçek abonelik hizmet aralığı kullanılır; teknik fatura eksikliğinde hesap bekletilir, hak sessizce silinmez. |
| Bölge havuzu yalnız yayına atanmış cihazlara bölünebiliyordu. | Bölgenin uygun cihazları paydaya alınır; mevcut kurulum/taşıma tarihçesi gün hesabına uygulanır. |
| Kuruş farkı son eczaneye topluca ekleniyordu. | En büyük kalan yöntemiyle eşit ağırlıklı eczanelerin farkı en fazla bir kuruş olur. 7/14 cihaz örnekleri test edilir. |
| Aynı tahsilat eşzamanlı veya sıfır sonuçtan sonra yeniden hesaplanabiliyordu. | Tahsilat satırı kilitlenir; sıfır sonuç da hesap tarihi ve özetiyle saklanır. Hesaplanmış tahsilat değiştirilemez, mali kayıtlar bu API'lerden silinemez. |
| Eczane faturası tebliği ödeme vadesini üretmiyordu. | Tebliğ + 15 takvim günü vade hesaplanır; fatura numarası ve fiili ödeme tarihi doğrulanır. Yönetim ekranına kayıt alanları eklenir. |
| Eczacı mali hesabı sponsor kampanya adını ve iç kayıtları açıyordu. | Eczacıya yalnız kendi hakediş alanları döner; sponsor kimliği ve iç hesap dökümü gizlenir. |

## Bilinçli olarak açık kalan işler

- Depozito, tahsis/öteleme bedelinin hukuki kullanımı ve kaynak belgelerdeki öneri/teyit değerleri ekip soru listesinde kalır.
- 10 iş günlük ara hesap bildirimi, sponsor yayınından önce bildirim, mahsup, banka/dekont entegrasyonu ve iade senaryoları tamamlanmış kabul edilmez. Dönem kapanmadan kesin katkı üretilmez; bu kontrol ara bildirim yükümlülüğünü erteleme kararı değildir.
- Eski cihazların kurulum/taşıma tarihçesi eksikse tarihsel aktiflik kesin olarak yeniden kurulamaz. Mevcut kayıt kullanılabilir, eksik saha geçmişinin tamamlanması gerekir. Teknik kesintinin kusuru ve kısmi gün kuralları ayrıca kararlaştırılmalıdır.
- Seri ve garanti envanterden alınır; girilmemişse eksik kalır. Teslim personeli, teslim saati ve bilinmeyen gerçek imza tarihi elle tamamlanacak alanlar olarak gösterilir.
- Yeni önizleme mevcut veriden üretilir; üretilen her taslağın değişmez sürümlü arşivi bu düzeltmenin kapsamında tamamlanmış kabul edilmez. İmzalı dosya ayrı saklanır.
- Word paket bütünlüğü ve manuel bölümlerin korunması otomatik test edilir; gerçek Word sayfa düzeninin saha çıktısıyla son görsel kontrolü ayrıca yapılmalıdır.

Yerel migration: `campaigns.0037_review_billing_and_contribution_guards` (tahsilat hesap tarihi ve hesap özeti), `pharmacies.0019_physical_device_inventory` ve `abonelik.0025_physical_device_inventory` (seri envanteri ve plan bağı) uygulandı. Yeni üretimde birleşik fatura oluşturulmaz; geçmiş birleşik faturalar mali tarihçe olarak kalır.

Doğrulama: abonelik, eczane/provizyon ve kampanya modüllerinde migration'lı geniş turda 304 test geçti. Son belge düzeltmeleri ve eczacı belge izolasyonu için 14 odak test ayrıca geçti (son hızlı tur `--nomigrations`; gerçek ORM modelleriyle). Panelde 199 test geçti. İzole headless Edge'de masaüstü/mobil 7 görsel akış testi geçti; ekran görüntüleri açılarak incelendi. Gerçek şablondan tam HTML kullanılır, API kayıtları sentetiktir. Panel production build, Django sistem kontrolü, migration tutarlılık kontrolü ve `git diff --check` başarılı. Word sayfa düzeninin birebir görsel kabulü ve PostgreSQL üzerinde eşzamanlı işlem testi bu yerel test turuna dahil değildir.
