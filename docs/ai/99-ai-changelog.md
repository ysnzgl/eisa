# AI Changelog — Dokümantasyon ve Kod Değişiklikleri

**Amaç:** AI tarafından yapılan değişikliklerin kısa kaydı.
**Format:** Tarih — Değişiklik (max 10 satır/kayıt)

---

## 2026-10-16

### [Backend + Web Panel] DOOH sponsorluk sistemi cihaz (kiosk) bazlı yeniden tasarlandı

- **Yeni model `KioskSponsorship`** (`dooh_kiosk_sponsorships`): kiosk + campaign (unique), `window_start_minute` (0..1439), `window_end_minute` (1..1440, >start), `count` (gün içi toplam gösterim), `active_weekdays` (ISO 1-7 JSON; boş = her gün), `start_date`/`end_date`, `is_active`. Hedefleme (il/ilçe/eczane) kaldırıldı; sponsorluk artık doğrudan cihaza atanır.
- **Campaign sadeleştirildi:** `advertiser_name` (serbest metin), `status` (ACTIVE/PAUSED/COMPLETED), `effective_state` (SCHEDULED türetilir). Kaldırılan: advertiser_id, target_scope, follows, priority, target_pharmacies, is_guaranteed, impression_goal, frequency_cap_per_hour.
- **Yeni motor `services/sponsorship_engine.py`:** homojen, deterministik yerleşim (ideal `t_i = S+(i+phase)·(E−S)/N`, round-robin creative, en yakın boş slot, saat sınırını aşamaz). Public: plan_day, plan_kiosk_day, persist_day, validate_kiosk, probe_window, simulate_scenario, regenerate_kiosk_day.
- **Kaldırılan servis/model/uç:** scheduler.py, placement_engine_v2.py, activation_service.py, quota_service.py, follows_service.py; CampaignTarget, ScheduleRule, DeliveryRule, PlanningRun, CampaignTotalAllocation, KioskDayQuota, KioskDesiredBundle, PlaylistTemplate, HourPlan, DayPlan, PricingMatrix; inventory/pricing/simulate/activate/targets/rules uçları. Migration 0033 (veri) + 0034 (şema).
- **Yeni uçlar `/api/campaigns/v2/`:** campaigns/{id}/kiosks/, campaigns/{id}/assign-kiosks/ (dry_run), sponsorship-kiosks/ (liste + arama/unassigned), {kiosk_id}/sponsorships/ GET/PUT, /preview/, /copy/ (OVERWRITE), /simulate/ (probe+senaryo). Kapasite hatası: `400 {code:"capacity_exceeded", conflicts:[...]}`.
- **Panel:** `KioskSponsorship.vue` (/admin/kiosk-sponsorships, sekmeler: sponsorluklar/takvim/simülasyon/kopya), `SponsorshipDefinitions.vue` (/admin/campaigns, sekmeler: Bilgiler/Medya/Kiosklar), composable `useSponsorship.js`. Kaldırılan: CampaignWizard.vue, PlaylistEditor.vue, PricingMatrixConfigurator.vue, /admin/playlists, /admin/pricing.
- **Dokümanlar güncellendi:** 00-AI-INDEX, 01-backend, 02-web-panels, 05-cross-project-flows, 06-db-and-api-contracts, 08-dooh-advertising, KULLANIM_REHBERI; FAZ2_COMPLETE/FAZ2_ONKOSULLAR/implementation-plan-dooh-scheduler tarihsel banner ile işaretlendi.

---

### [Backend + Web Panel] Abonelik & Fatura UX iyileştirmeleri (9 madde)

- **Islak imza → otomatik onay:** `SozlesmeViewSet.islak_imza_yukle` artık `eczaci_onay_tarihi = timezone.now()` set ediyor; admin belge yükleyince onay bekleme durumu oluşmuyor. `from django.utils import timezone` import eklendi.
- **Süre + Öteleme Toplam:** Eczacı sözleşme bilgileri kartındaki "Süre" satırı → "Süre + Öteleme Toplam" olarak güncellendi; `tip_display + öteleme_ay + toplam_ay` birleşik gösterim. Admin tablosu da aynı şekilde değişti.
- **KDV oranı + KDV dahil fiyat:** Eczacı sözleşme bilgileri bölümüne `KDV Oranı (%x)` ve `KDV Dahil Aylık` satırları eklendi; backend'deki `kdv_orani` ve `kdv_dahil_aylik` alanları kullanılıyor.
- **EFT banka bilgisi:** Eczacı ödeme modalında EFT seçildiğinde banka bilgisi hardcoded yerine `getSirketProfili()` çağrısından varsayılan aktif banka hesabı gösteriliyor (`loadBankaBilgisi` fonksiyonu ve `bankaHesabi` ref eklendi).
- **Cihaz planı "-" hatası:** Admin sözleşme tablosundaki Cihaz Planı sütunu `cihazPlanLabel(s)` fonksiyonu ile `cihaz_plani` veya `cihaz_planlari[0]`'dan doğru değeri okuyor.
- **Fatura varsayılan 3 ay:** Admin fatura filtresinde `thisMonthStart()` yerine `lastThreeMonthsStart()` (2 ay öncesi başlangıcı) kullanılıyor; fatura ve ödeme listeleri ekran açılışında son 3 ayı gösteriyor.
- **Syntax fix:** Backend `views.py`'de önceki patchten kalan `@action(...)    def uzat` tek satır birleşimi ayrıldı (sözdizimi hatası düzeltildi).
- 61 test geçti (abonelik + sirket).

---

## 2026-10-03

### [Backend + Web Panel] İş takibi iptal ve silme

- İş takibi durumlarına `IPTAL` eklendi; görevler düzenleme ekranından İptal durumuna alınabilir.
- Yalnız süper adminlerin kullanabildiği `DELETE /api/is-takip/gorevler/{id}/` açıldı; listede kalıcı silme için onay isteyen çöp kutusu aksiyonu eklendi.

### [Kiosk Edge] Idle logo uzun basma bakım menüsü

- Idle e-isa logosuna 10 saniye basılı tutunca açılan bakım menüsü eklendi; basma süresince belirgin halka ilerlemesi, yükleme animasyonu ve kalan saniye gösterilir.
- Uygulamayı yenile; provisioning kimliğini silmeden durumu uzlaştırır, cihaz ayarları/içerik/katalog/medya pull ve playlist/manifest ping işlemlerini hemen çalıştırıp UI'ı yeniden yükler.
- Cihazı yeniden başlat ve kapat seçenekleri ikinci onayla çalışır; güç uçları yalnız loopback isteklerine açıktır.
- Windows (`shutdown.exe`) ve Linux (`systemctl`) güç komutları shell kullanılmadan yürütülür; Linux polkit kuralı yalnız `eisa` kullanıcısının logind reboot/power-off eylemleriyle sınırlandırıldı ve systemd `NoNewPrivileges` koruması korundu.

### [Kiosk Edge + Web Panel] QR fiş alt logosu ve medya CSP düzeltmesi

- Barkod logo rotasyonu fişin üstünde korunurken verilen e-isa logosu QR bilgisinin altında sabit basılacak şekilde çıktı buffer'ı güncellendi.
- Sabit logo asset'i okunamazsa baskının tamamen kaybolmaması için metin fallback'i eklendi.
- Kiosk Docker imajına sabit fiş logo asset klasörü eklendi.
- Panel CSP'sinde `https://api.eisa.com.tr`, görsel ve medya kaynaklarına eklendi; barkod logo önizlemeleri ile sponsorluk videolarının engellenmesi giderildi.
- Eksik favicon isteği, paketlenen e-isa PNG asset'ine yönlendirildi.

### [Backend] Matbu sözleşme metni birebir Word belgesine göre yenilendi

- `apps/abonelik/contract_template.py` tamamen yeniden yazıldı. `render_sozlesme_html(sozlesme)` artık kaynak Word belgesindeki 22 maddelik tam metni **birebir** (yorum/kısaltma yok) üretir.
- Otomatik doldurulan alanlar: İŞ ORTAĞI ad/adres/vergi no (Madde 1, 11), aylık kullanım bedeli (Madde 12.1), ödeme günü (başlangıç tarihi günü), kullanıma tekrar açma/aktivasyon bedeli (aktif fiyat), düzenleme tarihi (Madde 22).
- Birebir korunan boş alanlar: [Banka Adı], [IBAN No], depozito [Rakam] (17.1), cezai şart örneği (17.2).
- `onay_blogu_html()` korundu: dijital onay beyanı (tarih + IP + 5070/6098 atfı), ıslak imza notu, onay bekliyor mesajı.
- Testler: 59 passed (abonelik).

---

## 2026-10-02

### [WebPanel] Admin faturalar: Ödendi fix + fatura görüntüleme

- **Ödendi çalışmama düzeltildi:** Faturalar tablosundaki Ödendi butonu için eksik script fonksiyonları (`openOdemeModal`, `savePaid`) eklendi. Manuel tahsilatta zorunlu açıklama gönderiliyor, kayıt sonrası liste yenileniyor.
- **Yeni admin özellik:** Fatura satırına `Görüntüle` aksiyonu eklendi. `GET /api/abonelik/faturalar/{id}/` ile detay çekilip modalda basit fatura tasarımıyla gösteriliyor (başlık, meta bilgiler, kalem tablosu, toplam).
- **API servis güncellemesi:** `getFaturaAdmin` helper eklendi (`web_panels/src/services/abonelik.js`).
- Doğrulama: frontend `npm run build` -> başarılı.

### [Backend] Aktif sözleşme tarih çakışma engeli

- Aynı eczane için `AKTIF` sözleşmelerde tarih aralığı çakışması artık engelleniyor. Çakışan yeni sözleşme oluşturma denemesi `400` ile reddediliyor.
- Kural sadece admin sözleşme API’sinde değil, talep onayından sözleşme üretiminde de uygulanıyor (tek merkezden kontrol).
- Yeni servis yardımcıları: sözleşme bitiş hesaplama + çakışan aktif sözleşme tespiti.
- Testler eklendi: çakışan sözleşme reddi ve çakışmayan sözleşme kabulü.
- Doğrulama: `pytest apps/abonelik -q` -> 61 passed.

### [Backend+WebPanel] Fiyat tanımına ceza çarpanı + açma/kapama bedeli ve peşin fiyat border fix

- **Fiyat tanımı genişletildi:** `FiyatTanimi` modeline `iptal_ceza_orani` (varsayılan 2.00) eklendi. Migration: `0015_fiyattanimi_iptal_ceza_orani.py`.
- **API alanları eklendi:** `FiyatTanimiSerializer` artık `acma_kapama_bedeli` ve `iptal_ceza_orani` alanlarını doğrulama ile birlikte alır/verir (0 ve üzeri).
- **Talep onayında fiyat fallback:** Yeni sözleşme talebinde admin ceza çarpanı girmezse, aktif fiyat tanımındaki ceza çarpanı otomatik uygulanır.
- **Admin fiyat modalı güncellendi:** Abonelik Yönetimi > Fiyat Tanımları ekranına `Açma/Kapama Bedeli` ve `Ceza Çarpanı` inputları + tarihçede ilgili kolonlar eklendi.
- **Border fix:** `SozlesmeForm.vue` içinde `Birim Peşin Fiyat` textbox grubuna görünür border stili eklendi.
- Doğrulama: `pytest apps/abonelik -q` -> 59 passed, frontend `npm run build` -> başarılı.

### [Backend+WebPanel] Açma/Kapama bedeli yüzde-temelli varsayılan ve sözleşmede oran gösterimi

- **DB saklama biçimi korunuyor:** `acma_kapama_bedeli` alanı tutar (TL) olarak veritabanında saklanmaya devam ediyor.
- **Ekranda varsayılan oran:** Fiyat Tanımları modalında açma/kapama artık oran girişiyle (%), varsayılan `%25.00` olarak geliyor.
- **Otomatik hesap:** Açma/Kapama Bedeli, `abonelik_bedeli × oran / 100` ile otomatik hesaplanıp TL olarak gösteriliyor; kayıtta hesaplanan tutar API’ye gönderiliyor.
- **Mevcut kayıttan oran türetme:** Aktif fiyat açıldığında, mevcut tutardan oran otomatik geri hesaplanıyor (tutar/abonelik).
- **Sözleşme metni güncellemesi:** Matbu sözleşmede aktivasyon ifadesi sabit TL yerine oran olarak yazılıyor (ör. `%25`).
- Doğrulama: `pytest apps/abonelik -q` -> 59 passed, frontend `npm run build` -> başarılı.

### [Backend+WebPanel] Tek fatura tarihi, vergi no, sözleşme tutar düzeltmesi, yazdırma fix

- **Cihaz fatura tarihi kaldırıldı:** Cihaz planlarından ayrı "1. Fatura Ayı" alanı kaldırıldı. Tüm cihaz bedelleri abonelik başlangıç tarihiyle aynı tarihte tek birleşik faturada tahsil edilir (SozlesmeForm watch cihaz tarihini sözleşme başlangıcına senkronlar).
- **Eczane vergi no:** `Eczane.vergi_no` alanı eklendi (migration 0018), serializer + devices.js mapping + DeviceManagement kayıt formu. Sözleşme Madde 1'de görünür.
- **Sözleşme tutar düzeltmesi:** Madde 12.1 artık net kırılım tablosu gösteriyor — Matrah, KDV oranı, KDV tutarı, KDV dahil toplam, (varsa) tevkifat ve net ödeme. Cihaz özet tablosuna tevkifat sütunu ve "tek birleşik fatura" notu eklendi.
- **Yazdırma about:blank fix:** SozlesmeMatbu yazdırma, window.open yerine ana sayfaya geçici print container + `@media print` stylesheet ile yapılıyor; footer'da about:blank yerine gerçek sayfa URL'i görünür.
- Testler: 112 passed (abonelik + pharmacies). Frontend build OK.



- **22 maddelik matbu sözleşme:** `apps/abonelik/contract_template.py` — `render_sozlesme_html(sozlesme)` Eczane İş Ortaklığı ve Dijital Platform Kullanım Sözleşmesi'ni (22 madde) sözleşme verileriyle (eczane, bedel, KDV, cihaz planları, ceza katsayısı) doldurarak tam HTML üretir.
- **Immutable onay snapshot:** `Sozlesme.onayli_sozlesme_metni` (TextField). `sozlesme_onayla()` onay anında tam metni + onay bloğunu dondurur; fiyat sonradan değişse bile metin değişmez. Migration 0014.
- **Dijital onay beyanı:** Onaylı sözleşme çıktısında "✓ BU SÖZLEŞME DİJİTAL OLARAK ONAYLANMIŞTIR" + eczacı onay tarihi + IP + 5070/6098 kanun atfı yazılır.
- **Metin endpoint'leri:** `GET /sozlesmeler/{id}/metin/` (admin) ve `/sozlesmelerim/{id}/metin/` (eczacı) — onaylıysa dondurulmuş, değilse canlı önizleme döner.
- **SozlesmeMatbu.vue yeniden yazıldı:** Backend'den gelen tam HTML'i v-html ile gösterir, ayrı yazdırma penceresinde PDF çıktısı alır. Admin ve eczacı `role` prop ile ayrışır.
- Testler: 59 passed (3 yeni sözleşme metni testi). Frontend build OK.



- **Odeme.aciklama + EFT_HAVALE:** `Odeme` modeline `aciklama` (500 char) ve `EFT_HAVALE` yöntem seçeneği eklendi. `ode_fatura()` servisi `aciklama` parametresi alıyor. Migration 0012.
- **Admin tahsilat modalı:** Admin faturalar tablosundaki "Ödendi" butonu, zorunlu açıklama alanı içeren modal açıyor. Açıklama girilmeden kayıt yapılamıyor. Yöntem MANUEL olarak kaydediliyor.
- **Eczacı ödeme yöntemi seçimi:** `HesabimOdemeler.vue` — Kredi Kartı veya EFT/Havale seçilebiliyor. EFT seçilince banka IBAN bilgileri + "Fatura No yazın" yönlendirmesi gösteriliyor.
- **10 gün uyarısı:** `odemeYakin` 3→10 güne çıkarıldı (sarı banner); `odemeKritik` 3 günde kırmızı banner ayrı eklendi. `_payment_due_context` announcements servisi de 10 güne güncellendi.
- **Sozlesme.imza_tipi + islak_imza_url:** Dijital veya Islak İmza seçimi. Islak imzalıda eczacı dijital onay akışı atlanıyor (`onay_gerekli=False`). Admin formuna RustFS path alanı eklendi (expiring URL değil kalıcı path). Migration 0012.
- **Admin sözleşme görüntüleme:** Sözleşmeler tablosuna "Sözleşmeyi Görüntüle" butonu eklendi — SozlesmeMatbu modalını açıyor.
- Testler: 56 passed. Frontend build: OK.



### [Kiosk UI] Idle ses sayacı görünürlüğü

- `Sese kalan` göstergesi debug koşulundan çıkarıldı; idle ekranda geliştirme ve production modlarında görünür hale getirildi.
- Gösterge sağ üstten sol üste taşındı; boyutu, kontrastı, gölgesi ve boşlukları azaltılarak daha sakin hale getirildi.
- Kiosk ayarlarına varsayılanı kapalı `Ses Süresi Görünür` seçeneği eklendi. `idle_audio_countdown_visible` yalnız açıkça `true` ise sayaç gösterilir; backend sync, edge lokal SQLite cache ve kiosk UI sözleşmesi bu alanı taşır.
- Yönetim panelindeki `Ses Aktif` ve `Ses Süresi Görünür` seçenekleri birbirine giren genel toggle düzeninden çıkarılıp iki kolonlu, açıklamalı ve mobilde tek kolona düşen bağımsız ayar kartlarına dönüştürüldü.

## 2026-10-01

### [Backend+WebPanel] İş takibi uzun içerik desteği

- `Gorev.icerik` alanındaki 2.000 karakter sınırı kaldırıldı; PostgreSQL `text`/Django `TextField` ile uygulama seviyesinde sınırsız uzun metin kabul edilir (`gorevler/0002`).
- İş düzenleme modalı 960 px'e genişletildi; içerik editörü büyütüldü, dikey yeniden boyutlandırma, paragraf/satır sonu koruma, kelime sarma ve canlı karakter sayısı eklendi. Liste kısa önizlemeyi korur.
- 2.000 karakteri aşan içeriğin API ve veritabanında eksiksiz saklandığını doğrulayan regresyon testi eklendi. Doğrulama: görev API testleri 5/5 geçti, migration kontrolü temiz ve web panel production build'i başarılı.

## 2026-10-01

## 2026-10-01

## 2026-10-01

### [Backend+WebPanel] Abonelik: kısıtlı panel, sözleşme talepleri, ödeme/uyarı sistemi

- **Kısıtlı panel (hard-block değil):** login/refresh 403 kaldırıldı. `services.panel_kisitli(eczane_id)→(bool, SOZLESME_YOK|ODEME_GECIKTI)`. Sözleşmesiz/ödemesi gecikmiş eczacı giriş yapar ama yalnız "Hesabım ve Ödemeler"i görür. Backend: `IsEczaciPanelAcik`/`PanelAcikVeyaAdmin` (analytics alias, destek create, duty write). Frontend: AdminLayout nav filtresi + router guard (`auth.panelKisitli`).
- **Sözleşme talepleri:** `SozlesmeTalebi` (YENI/UZATMA/IPTAL, admin onaylı). Eczacı Hesabım'dan talep açar; admin AbonelikYonetimi "Talepler" sekmesinden onay/red (onayda uygulanır). Migration `0005`. Admin nav'ında bekleyen talep badge.
- **Israrlı uyarılar + sistem duyuruları:** Hesabım'da bitiş≤7g / ödeme≤3g kalıcı uyarı bantları. İki yeni `system_key` (`PAYMENT_DUE_SOON`, `CONTRACT_EXPIRING`) `system_context`'te abonelik'e bakar; günlük zorunlu-okuma (ödeme/uzatma yapılana kadar). announcements migration `0003` seed.
- **Ödeme tarihçesi:** eczacı `odemelerim/` + admin `odemeler/` (mevcut `Odeme` + mark-paid). Sözleşme hareketleri `hareketlerim/` (sözleşme/uzatma/talep/ödeme birleşik).
- **Demo flag:** demo sözleşmede sol menüde DEMO rozeti (`hesabim.demo`).
- Testler: abonelik 48; analytics/announcements/destek/pharmacies fixture'larına aktif sözleşme eklendi (panel kısıtı orthogonal — analytics conftest bypass). Tüm suitler yeşil, frontend build yeşil. Docs 01/02/06 güncellendi.

### [Backend+WebPanel] Abonelik: sözleşme durumu AKTIF/IPTAL (tamamlandı türetilir)

- `Sozlesme.Durum` sadeleştirildi: **AKTIF | IPTAL** (TASLAK ve TAMAMLANDI kaldırıldı). Girişte AKTIF, iptalde IPTAL. "Tamamlandı/süresi doldu" artık stored değil; bitiş tarihinden türetilir: `suresi_doldu` (bool) + `etkin_durum` (`AKTIF|SURESI_DOLDU|IPTAL`).
- `uzat_sozlesme`: iptal edilmiş sözleşme uzatılamaz (400); süresi dolmuş AKTIF sözleşme uzatılınca bitiş ileri taşınır (durum değişmez). Reaktivasyon mantığı kaldırıldı.
- Migration `0004`: durum choices alter + legacy TASLAK/TAMAMLANDI → AKTIF veri taşıması. Frontend `SozlesmeForm` durum seçenekleri AKTIF/IPTAL; AbonelikYonetimi tablo/geçmiş `etkin_durum` bazlı renkli rozet (Aktif/Süresi Doldu/İptal).
- Testler: abonelik 39 geçti (etkin_durum, süresi doldu, iptal uzatılamaz). Build yeşil. Docs 01/06 güncellendi.

### [Backend+WebPanel] Abonelik: sözleşme türleri, tarihçe/uzatma ve eczane entegrasyonu

- **Demo artık sözleşme türü** (`Sozlesme.tur = DEMO|STANDART`). Demo gün bazlı (`demo_gun` 1–30), kullanım bedeli faturalanmaz, erişim kilitlenmez. `eczane_demo_modunda()` = aktif sözleşme DEMO. "Sözleşmesiz eczane" ayrı durum (badge kırmızı `Sözleşme yok`).
- **Sözleşmesiz eczane olmayacak:** `POST /api/pharmacies/` gövdesine write-only `sozlesme` nesnesi; `EczaneViewSet.perform_create` Eczane + Sozlesme'yi tek UoW transaction'ında oluşturur. Ortak `SozlesmeForm.vue` bileşeni DeviceManagement "Yeni Eczane" ve AbonelikYonetimi modallarında.
- **Tarihçe + uzatma:** `SozlesmeUzatma` modeli + `ek_ay_toplam/ek_gun_toplam` denormalize birikim + `onceki_sozlesme` zinciri. `POST sozlesmeler/{id}/uzat/` (standart ay / demo gün, demo cap 30), `GET .../gecmis/`. Migration `0003`.
- **Eczane listesi rozetleri:** `EczaneSerializer` `aktif_sozlesme {tur, bitis_tarihi, kalan_gun}` + `odeme_durumu [DEMO/GECIKTI/BEKLEYEN/GUNCEL/YOK]`. DeviceManagement tablosunda tür·kalan gün ve ödeme durumu renkli `eisa-pill` rozetleri + satır "Sözleşmeler" butonu (`/admin/abonelik?eczane=`).
- Kullanım bedeli faturalaması yalnız `tur=STANDART`. Testler: abonelik 35 geçti (demo, uzatma cap, nested oluşturma, badge alanları, uzat/geçmiş API). Frontend build yeşil.
- Docs: `01-backend`, `02-web-panels`, `06-db-and-api-contracts` güncellendi.

### [Backend+WebPanel] Abonelik: demo modu, taksit matrisi ve panel tasarımı

- **Demo aşaması:** `services.eczane_demo_modunda()` — eczanenin AKTIF/TAMAMLANDI sözleşmesi yoksa demo; faturalandırma ve erişim kilidi uygulanmaz. `hesabim` yanıtı `demo` alanı döner; eczacı paneli demo bilgilendirme kartı gösterir.
- **Cihaz taksit matrisi:** `CihazOdemePlani.taksit_sayisi` 1/4/8/12 (migration `0002`). Peşin (1) dışında `vade_farki_orani > 0` zorunlu — serializer validasyonu + frontend guard (kaydet kilidi + uyarı).
- **Panel tasarımı:** `AbonelikYonetimi.vue` ve `HesabimOdemeler.vue` ortak `style.css` sınıflarına taşındı (eisa-page/panel/stats/table/pill/modal/form-grid/field/error-banner); sayfa içi `<style scoped>` kaldırıldı. Modallar `Teleport` ile body'e taşındı.
- Testler: `test_billing.py` 23 geçti (demo modu + taksit/vade validasyonu eklendi). Frontend build yeşil.
- Docs: `01-backend`, `06-db-and-api-contracts` güncellendi.

### [Backend+WebPanel] Abonelik, faturalandırma ve erişim kilidi

- Yeni `apps/abonelik`: `Sozlesme` (12/24/36 ay + kullanım bedeli öteleme/vade kaydırma; öteleme her ay bitişe eklenir), `CihazOdemePlani` (peşin + vade farkı → 4/8 eşit taksit), `Fatura` (KULLANIM_BEDELI/CIHAZ_TAKSIT, dönem/taksit bazlı partial-unique idempotent üretim), `Odeme` (mock tahsilat). Migration `abonelik/0001_initial`.
- `services.py`: `faturala_kullanim_bedeli` (öteleme sonrası → sözleşme bitişine kadar), `faturala_cihaz_taksit` (ayın ilk haftası, ayda tek taksit), `guncelle_gecikmis_faturalar` (vade+GRACE_DAYS=7 → GECIKTI), `ode_fatura`, `eczane_erisim_kapali`. Scheduler `gunluk_faturalandirma` job'ı `run_scheduler.py`'a eklendi (02:00 UTC).
- Erişim kilidi: `core_api/auth_views.py` login (obtain) **ve** token refresh, ödenmemiş fatura vade+7 geçen eczacıyı 403 `_ERISIM_KAPALI_MESAJ` ile bloklar; kiosk cihazları etkilenmez. `Login.vue` 403 `detail` mesajını gösterir.
- API `/api/abonelik/`: admin `sozlesmeler` (CRUD + `cihaz-plani` PUT), `faturalar` (+`ode`); eczacı `hesabim`, `faturalarim` (+`{id}/ode`). Frontend `services/abonelik.js`, admin `AbonelikYonetimi.vue` (`/admin/abonelik`), eczacı `HesabimOdemeler.vue` (`/pharmacist/hesabim`), AdminLayout nav + router kayıtları.
- Testler: `apps/abonelik/tests/test_billing.py` (16 geçti — vade kaydırma, öteleme, cihaz taksit matrisi, idempotency, gecikme, erişim kilidi, ödeme). Frontend build yeşil.
- AI dokümanları güncellendi: `00-AI-INDEX`, `01-backend`, `02-web-panels`, `06-db-and-api-contracts`.

---

## 2026-09-29

### [Backend+Kiosk Edge+WebPanel] Kiosk build numarası takibi

- Kiosk edge merkezi API çağrılarında `X-Kiosk-Build-Number` gönderir. Değer `EISA_BUILD_NUMBER` (fallback: `APP_VERSION`) üzerinden belirlenir ve SQLite `kiosk_meta.kiosk_build_number` içinde tutulur.
- Backend `KioskAppKeyAuthentication` heartbeat güncellemesinde bu header'ı alıp `Kiosk.kiosk_build_number` alanına yazar (migration `pharmacies/0016_kiosk_build_number.py`).
- Admin `DeviceManagement` ekranında kiosk kartı ve detay modalına build numarası eklendi; hangi kioskta hangi sürüm çalışıyor görünür hale geldi.
- AI dokümanları (`00/01/02/03/05/06`) sözleşme ve akış değişiklikleriyle güncellendi.

### [Backend+Kiosk Edge/UI] Kiosk TR/EN çift dil desteği (i18n)

- Kiosk kullanıcı arayüzüne köşe dil butonu (TR/EN) eklendi; seçim `localStorage` (`kiosk_lang`) ile kalıcı. Yeni `kiosk_edge/ui/src/lib/i18n.js` sabit metin sözlüğü (`$t`) ve DB içeriği için dil seçici (`$localize`) sağlar; `components/LanguageToggle.svelte` sabit köşe butonu.
- Tüm kiosk ekranlarındaki sabit metinler i18n'e taşındı (Welcome/Demographics/Category/Consult/Question/Result/IdleCountdown/AdPromo/Wifi). Sonuç başlığı dil değişiminde reaktif; AdPromo idle içeriği dil değişince yeniden daktilo edilir.
- Backend DB düzeyinde çeviri alanları eklendi: `products.Kategori.ad_en`, `products.Danisma.ad_en`, `products.Soru.metin_en`, `products.Cevap.metin_en` (migration 0013); `campaigns.IdleScreenContent.baslik_en/metin_en` (migration 0029). Boş `_en` → kioskta Türkçe alana geri döner. Serializer'lar (catalog/sync + admin) bu alanları yayınlar.
- Kiosk edge SQLite'a additive/idempotent `_en` kolonları eklendi (SCHEMA_VERSION değişmez → cache sıfırlanmaz); scheduler upsert'leri ve read endpoint'leri `_en` taşır. Doğrulama: UI build OK, api-node 175 test OK, backend products/kiosk_api/campaigns testleri OK; idle ekranında TR↔EN görsel test yapıldı.

### [WebPanel+Test] TR/EN içerik editörü ve test kapsamı

- Web panel içerik yönetimine İngilizce alanlar eklendi: `MedicalLogic.vue` (Kategori Adı EN + Soru Metni EN), `DanismaYonetimi.vue` (Kategori Adı EN), `ContentManagement.vue` (Başlık EN + Metin EN). `services/algorithm.js` `_en` alanlarını çift yönlü eşler (name_en↔ad_en, text_en↔metin_en, danisma ad_en). Boş EN → kioskta Türkçe fallback.
- IdleScreenContent serializer'ına `baslik_en`/`metin_en` uzunluk doğrulayıcıları (100/300) eklendi.
- Testler eklendi: kiosk UI `src/lib/i18n.test.js` ($t/$localize/toggle/localStorage), api-node `_en` read endpoint testleri (kategori/soru/danışma/idle), backend `apps/products/tests/test_i18n_translations.py` (catalog + admin serializer _en) ve `test_idle_screen_content.py` IC-10..IC-12 (_en CRUD/sync/limit), web panel `algorithm_i18n.test.js` (_en mapping). Doğrulama: UI 91 test OK, api-node 180 test OK, web_panels 75 test OK, backend hedef testleri 50 OK; tüm build'ler yeşil.


### [Portal] Ses önizlemesi kontrolü

- Yerel 16 aktif ses storage'dan okunup checksum ile doğrulandı; örnek preview yanıtı 200/audio-wav ve dosyayla aynı. Önizleme presigned URL kullanmıyor. Yayın CSP'sine blob medya izni eklendi; eski oynatıcı kaynağının erken iptalinden doğabilecek yanıltıcı hata bildirimi düzeltildi. Yayın CSP değişikliği portal yeniden dağıtıldığında uygulanır.

### [Kiosk UI] Idle heartbeat ve içerik ikon görünürlüğü

- Beyaz idle ekrandaki heartbeat çizgisi, hareketli pulse, halkalar ve glow logo kırmızısına (`#ed1c24`) geçirildi. İçerik ikonları `ikon`/`kategori_ikon` alanlarını ve tam Font Awesome sınıflarını normalize ediyor; kategori atanmamış veya ikonsuz mesajlarda `fa-heart-pulse` fallback'i gösteriliyor. İkon, kontrastlı kırmızı dairesel rozet olarak yeniden biçimlendirildi; iki regresyon testi eklendi.

### [Kiosk UI] Idle ekranı beyaz marka tasarımına geçirildi

- Reklamsız tam ekran idle fallback beyaz/açık zemine alındı; EKG, CTA, karşılama ve sponsor kartı koyu gri + e-isa kırmızısı kontrastla yeniden uyarlandı. Üst logo açık cam kartta koyu varyanta geçti; kampanya oynatımı ve alt banttaki koyu `AdPromo` tasarımı değişmedi. Kiosk UI 67 test ve production build ile doğrulandı.

## 2026-09-13

### [Backend+WebPanel] Admin-only İş Takibi ve ortak form stili düzeltmeleri

- `apps.gorevler` eklendi; Süper Admin erişimli iç iş takibi modeli ve API'si oluşturuldu (`/api/is-takip/gorevler/`). Alanlar: başlık, içerik, durum, atanacak kullanıcı.
- Web panelde `/admin/is-takip` rotası ve `GorevYonetimi.vue` eklendi; görünüm ana dashboard KPI kartlarına yakın tutuldu, edit popup kompaktlaştırıldı.
- Ortak `eisa-field` stiline hafif border eklendi; Eczane & Cihaz ekranındaki eczane düzenleme popup'ı daraltıldı, iş takibi popup'ı da aynı kompakt modal yaklaşımını kullanıyor.

### [Backend+WebPanel+Kiosk Edge/UI] Idle ses sürekliliği ve provision senkronizasyonu

- Mesai içi ses penceresi İstanbul 08:00–19:00 olarak teyit edildi; 24 saat ve nöbet günü istisnası korundu.
- Kiosk UI debug modunda idle ses için sağ üst "Sese kalan" sayacı eklendi (`DEV` veya `VITE_KIOSK_DEBUG=true`).
- Idle ses sayacı her idle ekran açılışında lokal DB'deki son QR zamanını tazeler. İlk süre dolmadıysa kalanını, dolmuşsa 1 saniyelik yanlış tetik yerine cihazın devam süresini bekler; yeni QR oluşunca store anında ilk süreye güncellenir.
- Sonuçtan ana ekrana dönüş, lokal DB uzlaşması tamamlanmadan idle ekranı etkinleştirmez; QR oluşturma öncesinde başlamış eski polling yanıtı da yeni QR zamanını ezemez.
- Idle ekrandaki tekil dokunuşun ses çevrimini kalıcı bloke etmesi giderildi; ses çalmıyorken dokunuş bekleyen timer'ı değiştirmez, çalan sesi kestiğinde devam süresi sonunda sıradaki dosyaya geçer ve liste başa sarmaz.
- Lokal ses endpoint'lerine `Content-Length`/byte-range desteği eklendi. Bootstrap `device_config` manifesti provision anında indirilir; ilk ve periyodik full pull aynı checksum doğrulamalı cache'i günceller.
- Beş dakikalık `npm run dev:all` izlemesinde tüm servisler ayakta kaldı; edge başlangıcındaki yinelenen ping ve katalog pull'undaki çift transaction çağrısı kaldırıldı.
- 16 dosyalı sıra ve API range testleri eklendi. Kiosk 25'te ters kayıtlı `ilk=300/devam=120 sn` verisi `ilk=120/devam=300 sn` olarak düzeltildi; lokal cache'te 16 ses doğrulandı.

## 2026-09-11

### Ses kütüphanesi yükleme ve dinleme

- Yükleme kiosk kaydından ayrıldı; dosyalar önce kütüphaneye kaydedilir, kullanıcı seçip Güncelle ile atar. Portal Dinle kontrolü ve SuperAdmin korumalı preview endpoint'i eklendi.

### [Backend+WebPanel+Kiosk Edge/UI] Cihaz-bazlı zamanlayıcı ve idle ses yönetimi

- `Kiosk` UI zamanlayıcılarına default 20 dk ilk ses ve 5 dk tekrar aralığı eklendi; sıralı çoklu dosyalar `KioskIdleAudio` ile tutulur (`pharmacies.0012` + `0013`).
- DeviceManagement mevcut tasarımını koruyarak çoklu MP3/WAV/OGG seçimi, sıralı liste, tekil kaldırma, ilk/tekrar süreleri ve etkinlik kontrolüyle genişletildi; kampanya/teknik scheduler süreleri kapsam dışıdır.
- Bootstrap/sync sıralı ses manifestini döner; edge tüm listeyi AppKey proxy'sinden checksum doğrulamalı indirir ve ancak eksiksiz snapshot'ı aktive eder. Başarısız yeni listede son çalışan cache korunur.
- Svelte UI ilk sesi kesintisiz idle gecikmesi sonunda, devamını ses bitiminden sonra default 5 dk arayla sıralı/döngüsel çalar. Etkileşim anında akış ve köşe hoparlör göstergesi kapanır.
- Doğrulama: backend 36 test, kiosk UI 64 test ve iki production build geçti; edge iki dosyalı gerçek indirme/checksum/sıra smoke testi geçti. Node 24 native `better-sqlite3` worker kapanış sorunu sürmektedir.

### [Backend+WebPanel] Merkezi ses kütüphanesi ve süre birimi seçimi

- `KioskAudioAsset` ve `pharmacies.0014_kiosk_audio_library` ile yüklenmiş sesler merkezi kütüphanede kalıcı hale getirildi; var olan kiosk ses atamaları migration sırasında kütüphaneye taşınır.
- Cihaz düzenleme modalı, tasarımı koruyarak kütüphaneden sıralı seçim ve “Yeni Ses Ekle” akışını kullanır. Tüm cihaz zamanlamaları Sn/Dk seçicisiyle girilir, backend'e saniye olarak kaydedilir.
- Yerel edge `.env` hedefi `http://localhost:8000`'dır. Provisioning görünmüyorsa ayrıca edge API'nin 8765 portunda çalıştığı doğrulanmalıdır.

### [Kiosk Edge] Node 24 SQLite native sürücü düzeltmesi

- `better-sqlite3` 13.x'e yükseltildi ve minimum Node sürümü 22 yapıldı. Bu, Node 24'te eski 11.x native sürücünün API node'u başlatırken ürettiği assertion ile kapanma sorununu giderir.
- Merkezi backend'in `pharmacies.0014_kiosk_audio_library` migration'ı uygulandı; aksi halde bootstrap, yeni ses ataması alanını okurken 500 dönüyordu.

### [Kiosk UI] Idle dönüşü öncesi işlem devam uyarısı

- İşlem ekranı inaktivite süresi dolduğunda, idle'a geçmeden önce 5 saniyelik geri sayımlı popup eklendi. “Devam Et” sayacı iptal eder ve işlemi bulunduğu ekranda sürdürür; süre bitiminde terk edilmiş oturum kapatılıp idle ekrana dönülür.

### [Backend+WebPanel+Kiosk Edge] Idle ses çalışma zamanı ve nöbet istisnası

- Kiosk ses ayarına 08:00–19:00 İstanbul mesai içi veya 24 saat çalışma modu eklendi. Nöbetlerde çal seçiliyse eczanenin kayıtlı nöbet gününde mesai içi sınırı 24 saat kaldırılır.
- Backend nöbet günlerini sync manifestine taşır; edge bunları lokal SQLite'ta saklar ve ses başlamadan önce zaman denetimini yapar. Migration: `pharmacies.0015_kiosk_idle_audio_schedule`.

## 2026-08-19

### [Backend+WebPanel] Duyuru kuyruğu, etken madde kaynağı, dashboard ve cihaz taşıma düzeltmeleri

- Session etken madde detayına additive `RECOMMENDED|PHARMACIST_ADDED` kaynağı ve snapshot tabanlı dedupe ayrımı eklendi; migration gerekmedi.
- Eczacı layout'u aktif okunmamış genel+sistem duyurularını tekli kuyrukta otomatik açıyor; genel kayıt yalnız başarılı “Okudum” ile kapanıyor.
- Admin duyuru liste/formundan teknik sistem anahtarları kaldırıldı; ortak modal/indigo bilgi stili uygulandı.
- Admin legacy “Kiosk Etkileşimleri” grafiği kaldırıldı; iki rolde ortak dört aylık/haftalık etkileşim+satış grafiği kullanılıyor.
- Admin analytics alanı üç kolona toplandı: aylıklar aynı panelde, kompakt haftalıklar aynı panelde, kategori ve satış yapan eczane donut'ları üçüncü kolonda. Gün tıklamaları QR/Satış sekmesine tarih filtresiyle gider.
- Dönem gezinmesi yalnız FA ikonlarına sıkıştırıldı; değer tipografisi güçlendirildi, satış grafikleri önerilen/satılan çift serisine çevrildi ve boş danışmanlık dilimi kategori donut'ından çıkarıldı.
- Satış seri renkleri tasarım tokenlarına sabitlendi: önerilen `--eisa-turquoise`, satılan `--eisa-red`; haftalık dönem başlığı dar kolonda alta taşmayacak şekilde tek satıra alındı.
- Dashboard analitiği bağımsız async bar/donut bileşenlerine ayrıldı: QR grafikleri Danışma sonucu (Bekleyen/Satış Yapılan/Satış Yapılmayan), satış grafikleri yalnız `SATIS_YAPILDI` oturumlarından Önerilen/Satılan serisini gösterir. Dashboard ilk satırda dört KPI, ikinci satırda ilk 10'luk dört donut ve üçüncü satırda iki kolon aylık/haftalık analitik düzenine sahiptir. Bugünün QR sayacı İstanbul takvim gününe göre hesaplanır.
- Her cihaz kartına “Eczaneye Taşı” aksiyonu ve mevcut/hedef eczane özeti olan standart transfer modalı eklendi; backend kimlik/geçmiş invariant testleri eklendi.
- Backend hedefli testleri, web component testleri, production build ve 1920/1100 gerçek Chrome turu doğrulandı; önce/sonra ekran görüntüleri `docs/qa/` altındadır.

## 2026-08-16

### [Backend+WebPanel+KioskEdge+KioskUI] HouseAd kaldırıldı; İçerik Yönetimi başlık/metin idle içeriğine geçti

**Değişiklik:** DOOH filler (HouseAd) sistemi uçtan uca kaldırıldı; playlist campaign-only oldu (boş playlist geçerli → kiosk idle ekranı). "İçerik Yönetimi" yeni başlık/metin tabanlı idle içeriğine dönüştürüldü.

**Backend:**
- `HouseAd` modeli/tablosu (`dooh_house_ads`), serializer, viewset (`/api/campaigns/v2/house-ads/`), scheduler Pass-4 filler, PlacementEngineV2 `_fill_house_ads`, kiosk sync `house_ads` KALDIRILDI (migration 0027).
- `PlaylistItem.house_ad` + `PlayLog.house_ad` FK'leri kaldırıldı; `PlaylistItem.clean()` creative zorunlu (creative-only).
- YENİ `IdleScreenContent` modeli (app: campaigns, tablo `dooh_idle_screen_contents`: `baslik`≤100, `metin`≤300, `aktif`) + CRUD API `GET/POST/PUT/PATCH/DELETE /api/campaigns/v2/idle-contents/` (JWT SuperAdmin, basename `dooh-idle-content`).
- Kiosk sync artık `house_ads` yerine `idle_contents` (aktif; `KioskIdleContentSyncSerializer`) döner. Proof-of-play `house_ad_id` gelse de yok sayılır.

**Kiosk Edge (api-node):** YENİ SQLite `idle_contents` tablosu; pull sync transaction içinde upsert + reconcile (offline'da son cache korunur); v15 idempotent migration `house_ads` tablosunu düşürür + `media_cache` house_ad satırlarını siler; YENİ salt okunur `GET /api/idle-contents` lokal endpoint.

**Web panel:** "İçerik Yönetimi" (`/admin/content-management`) korundu ama yeni IdleScreenContent CRUD'unu açar (`ContentManagement.vue`; liste, ekle/düzenle/aktif-pasif/silme, 0/100 & 0/300 sayaç, sağlık uyarı notu, 1080×1920 önizleme). Eski `HouseAdManagement.vue` + `dooh.js` house-ad metotları kaldırıldı; yeni `listIdleContents/createIdleContent/updateIdleContent/deleteIdleContent`.

**Kiosk UI:** YENİ `lib/idleContentStore.js` (shuffled-bag rotasyon, dwell 12–20s); `AdPromo` `large` varyantı → başlık (fade) + heartbeat (değişmedi) + metin (tek-seferlik typewriter) + SABİT CTA "Size özel öneriler için DOKUNUN". `small` varyant değişmedi. AdStrip/resolver/edge house_ad öğelerini defansif atlar.

**Migration:** campaigns/0027 (HouseAd drop + IdleScreenContent), edge SQLite v15.

---

### [Kiosk UI] Kalp Atışı Animasyonu Güncelleme — Beyaz 3-Pikli + Smile Curve + Modüler Widget

**Değişiklik:** Sponsor fallback ekranındaki animasyon özelleştirilerek yeni modüler widget olarak ayrıldı.

**Yeni özellikler:**
- **3 pikli kalp atışı:** Küçük-BÜYÜK-küçük ritim (ortadaki 2 kat büyük pik: y:40-160 vs y:80-100)
- **Beyaz renk şeması:** Tüm animasyon beyaz (#fff) - gradient, çizgiler, halkalar, glow
- **Gülen yüz (smile curve):** Kalp atışının altında bezier eğrisi `M220,130 Q260,150 Q300,130`
- **Modüler yapı:** `HeartbeatAnimation.svelte` ayrı component (yeniden kullanılabilir)
- **Daha büyük halkalar:** 140px başlangıç → 460px bitiş (önceki 120-420px)
- **Döngü:** 2.8sn (önceki 2.6sn), yumuşak ve sakin
- Animasyon `prefers-reduced-motion: reduce` durumunda durur

**Dosyalar:**
- `kiosk_edge/ui/src/components/HeartbeatAnimation.svelte` (YENİ - 250 satır)
- `kiosk_edge/ui/src/components/AdPromo.svelte` (eski EKG kodu kaldırıldı, HeartbeatAnimation import)
- `docs/ai/04-kiosk-edge-ui.md` (component #11 eklendi, numaralandırma güncellendi)

**Test:** Build başarılı (93KB bundle), http://127.0.0.1:5173/ → animasyon görünür, dokunma çalışıyor, demographics geçişi OK.

---

## 2026-08-15

### [Kiosk UI] İdeal/Attractor Ekranına Dekoratif EKG Animasyonu

**Değişiklik:** Reklam olmadığında gösterilen sponsor fallback ekranına (AdPromo.svelte large varyant) sağlık teknolojisi temalı dekoratif animasyon eklendi.

**Animasyon özellikleri:**
- Yatay EKG çizgisi (soldan sağa ilerleyen parlak enerji izi, SVG `stroke-dasharray` + `stroke-dashoffset` animasyon)
- İki pikli kalp atışı ritmi (gerçekçi EKG dalga formu, 2.6sn döngü)
- Eş merkezli kırmızı halkalar (merkezden dışa yayılıp saydamlaşma, 3 halka 0s/0.15s/0.3s gecikme)
- Merkez kırmızı glow efekti (`radial-gradient` + pulse)
- e-isa kırmızı (#B1121B), beyaz, koyu lacivert renk paleti
- `clamp(460px, 28vw, 540px)` responsive boyut, ekran ortasında (~%48-52 yükseklik)
- `pointer-events: none`, `aria-hidden="true"` — dokunma engellenmez
- `prefers-reduced-motion: reduce` → animasyonlar durur, statik EKG + halkalar görünür

**Korunan öğeler (DEĞIŞMEDI):**
- Mevcut arka plan, renkler ve gradient
- Üst logo, "Başlamak için dokunun" metni ve el ikonu
- Alt "Bu alana sponsor olabilirsiniz" kartı (megafon + shimmer başlık)
- Tüm öğelerin konumları, ölçüleri, stilleri
- Mevcut dokunma/click davranışı (demographics geçişi)
- Kampanya/house ad medya gösterimi (animasyon YOK, medya tam ekran gösterilir)
- Playlist, MediaView, impression akışları
- Responsive davranış
- `AdPromo` küçük varyantında animasyon YOKTUR (yalnız `large` modda)

**Teknik:** Inline SVG + CSS animasyonlar, harici dependency veya görsel dosya YOK. Chromium kiosk uyumlu, performans optimizasyonlu (küçük öğeler üzerinde glow, ağır filtre yok).

**Dosyalar:** `kiosk_edge/ui/src/components/AdPromo.svelte` (HTML + CSS), `docs/ai/04-kiosk-edge-ui.md` (AdPromo açıklaması güncellendi)

**Test:** Manuel doğrulama (http://127.0.0.1:5173/, idle ekran → sponsor fallback → animasyon görünür, dokunma → demographics ekran). Gerçek kampanya gösterilirken animasyon görünmez.

---

## 2026-08-15

### [Backend/Frontend] Medya Kalıcı URL, Creative/HouseAd İndirme, HouseAd Yönetim Ekranı

**Root cause:** `DOOH_PERSISTENT_MEDIA_URL=False` (default) nedeniyle upload sırasında süreli presigned URL veritabanına yazılıyordu. Süre dolunca medya admin panelde görünmez oluyordu.

**Değişiklikler özeti:**
1. `DOOH_PERSISTENT_MEDIA_URL` default=True yapıldı; yeni yüklemelerde presigned URL DB'ye yazılmıyor.
2. `Creative.active_object_key` modeli ve migration 0026 eklendi.
3. `CreativeSerializer` + `active_object_key`; HouseAd video kısıtlaması kaldırıldı.
4. `CreativeViewSet` ve `HouseAdViewSet`'e `/download/` streaming action eklendi (SuperAdmin, Content-Disposition:attachment).
5. `backfill_media_object_keys` komutu `active_media_url` backfill'ini de destekliyor.
6. `CampaignWizard.vue`: HTML5 video player + görsel thumbnail, Bekleme/İşlem medya ayrımı, `active_object_key` takibi.
7. `HouseAdManagement.vue` yeni sayfa (CRUD + medya önizleme + indirme).
8. Router + AdminLayout güncellendi.

**API (additive):** `GET /api/campaigns/v2/creatives/{id}/download/`, `GET /api/campaigns/v2/house-ads/{id}/download/`
**Test:** 13 yeni test, test_closure C01 + test_house_ad_validation HA08 güncellendi (305 passed).

---

## 2026-08-15

### [Backend/Frontend] Görüş ve Destek (Ticket) Sistemi

**Değişiklik:** Pharmacy ve Admin panellerinde kullanılacak tam kapsamlı destek talebi sistemi eklendi.

**Backend (`apps.destek`):**
- `DestekParametresi` — TALEP_TURU/ALAN/ALT_KONU/DURUM gruplarını yöneten tek parametrik tablo.
- `TalepSayac` — Concurrency-safe yıllık sayaç (`select_for_update`). `count+1` kullanılmadı.
- `DestekTalebi` — Ticket modeli (talep_no: `EISA-YYYY-NNNNNN`, PROTECT FK'lar).
- `DestekYorumu` — Append-only yorum geçmişi; durum otomatik geçişleri (admin→YANITLANDI, eczacı cevabı→INCELENIYOR).
- API: `/api/destek/parametreler/`, `/api/destek/talepler/` (list/create/retrieve + yorum-ekle/durum-degistir/yeni-sayisi).
- Queryset izolasyonu: eczacı yalnız kendi eczanesinin taleplerini görür.
- 40 backend testi; tamamı geçiyor.

**Frontend:**
- `DestekTalepleri.vue` (pharmacist) — Karşılama banner, yeni talep formu, liste, detay modal + konuşma.
- `DestekYonetimi.vue` (admin) — Filtreli liste, detay modal, yorum ekleme, durum değiştirme.
- `AdminLayout.vue` — "Görüş ve Destek Yönetimi" ve "Görüş ve Destek" nav öğeleri; Yeni sayısı badge.
- Router: `/admin/destek`, `/pharmacist/destek`.

**Dosyalar:**
- `backend/apps/destek/` (yeni app — models, serializers, views, urls, migrations, seed, tests)
- `backend/core_api/settings.py`, `core_api/urls.py`
- `web_panels/src/views/admin/DestekYonetimi.vue` (yeni)
- `web_panels/src/views/pharmacist/DestekTalepleri.vue` (yeni)
- `web_panels/src/router/index.js`, `AdminLayout.vue`, `services/api.js`, `styles.css`

---

### [Backend/Frontend] Dashboard Satış İstatistikleri, Kiosk Hareketleri Satış Sekmesi, AutoComplete

**Değişiklik:** Üç özellik birlikte uygulandı:

1. **Dashboard Satış İstatistikleri:**  
   - `AdminDashboardView` ve `EczaciDashboardView` API'lerine `satis_sayisi` ve `en_cok_satilan_etken_madde` eklendi.  
   - Opsiyonel `start_date` / `end_date` query parametreleriyle tarih filtresi.  
   - Eczacı yalnız kendi eczanesine ait veriye erişir (backend queryset scope).  
   - Admin/Eczacı Dashboard UI'larına iki yeni KPI kartı ve tarih filtreli "Satış Özeti" paneli eklendi.

2. **Kiosk Hareketleri Satış Sekmesi:**  
   - `_build_oturum_queryset`'e `?sold=true|false` filtresi eklendi.  
   - `KioskActivityView`, `sold=true` isteklerinde `prefetch_related` uyguluyor (N+1 yok).  
   - `KioskActivityListSerializer`'a `sold` ve `etken_madde_adlari` alanları eklendi.  
   - Admin ve Eczacı KioskActivities panellerine "Satışlar" sekmesi eklendi.

3. **Kiosk/Eczane AutoComplete:**  
   - Admin KioskActivities: il/ilçe/eczane/kiosk 4'lü cascading `<select>` kaldırıldı; yerine "İl/İlçe/Eczane" ve "İl/İlçe/Eczane/Kiosk" birleşik etiketli 2 EisaLookup eklendi.  
   - Eczacı KioskActivities: kiosk `<select>` → EisaLookup (dashboard'dan kiosk listesi).  
   - Tüm seçim sonuçları mevcut kiosk/eczane ID değerini API'ye iletmeye devam eder.

**Yetkilendirme:** Tüm sold filtreleri ve istatistikler backend queryset seviyesinde eczane scope ile korunmaktadır. Frontend seçimlerine güvenilmiyor.

**Dosyalar:**  
- `backend/apps/analytics/views.py` — sold filtresi, AdminDashboard sold stats, KioskActivityView prefetch  
- `backend/apps/analytics/serializers.py` — KioskActivityListSerializer sold + etken_madde_adlari  
- `backend/apps/pharmacies/dashboard.py` — EczaciDashboard sold stats  
- `backend/apps/analytics/tests/test_sold_stats.py` — 13 yeni test (hepsi geçiyor)  
- `web_panels/src/views/admin/Dashboard.vue` — sold KPI kartları, tarih filtresi  
- `web_panels/src/views/pharmacist/Dashboard.vue` — sold KPI kartları, tarih filtresi  
- `web_panels/src/views/admin/KioskActivities.vue` — Satışlar sekmesi, EisaLookup AutoComplete  
- `web_panels/src/views/pharmacist/KioskActivities.vue` — Satışlar sekmesi, EisaLookup kiosk  
- `web_panels/src/services/analytics.js` — getAdminDashboard() eklendi

**API eklenti:** `GET /api/analytics/admin-dashboard/` → `satis_sayisi`, `en_cok_satilan_etken_madde` (mevcut alanlar korundu); `GET /api/pharmacies/me/dashboard/` → aynı. `GET /api/analytics/kiosk-activities/?sold=true|false` yeni filtre.

---

## 2026-08-12

### [Backend/DOOH] Aktivasyon timeout düzeltmesi — queue tabanlı horizon aktivasyon

**Değişiklik:** `POST /api/campaigns/v2/campaigns/{id}/activate/` artık kampanyanın tüm tarih aralığı için senkron playlist üretmiyor. Endpoint doğrulama yapıp üretimi mevcut DB-backed queue'ya (`GenerationJob`) bırakıyor; kapsam yalnız rolling horizon (varsayılan 3 gün).

**Kritik davranışlar:**
- GUARANTEED için horizon pre-check başarısızsa 409 dönüyor ve `campaign_activate` job enqueue edilmiyor (kısmi publish başlamaz).
- Tekrarlı aktivasyonlar mevcut dedupe/coalesce (`kd:{kiosk_id}:{date}`) ile duplicate `PENDING` job üretmiyor.
- `PlacementEngineV2` date filtreleri timezone-aware gün sınırlarıyla düzeltildi; naive datetime RuntimeWarning giderildi.
- `PlaylistItem` persistlerinde `bulk_create(batch_size=500)` kullanıldı.

**Dosyalar:** `backend/apps/campaigns/services/activation_service.py`, `backend/apps/campaigns/views_v2.py`, `backend/apps/campaigns/services/placement_engine_v2.py`, `backend/apps/campaigns/services/scheduler.py`, `backend/apps/campaigns/tests/test_faz3_simulation_activation.py`, `docs/ai/06-db-and-api-contracts.md`, `docs/ai/08-dooh-advertising.md`

---

### [Kiosk Edge UI] WifiSetupScreen — Wi-Fi yanlış-negatif reconciliation düzeltmesi

**Değişiklik:** `/wifi-connect` HTTP isteği hata verdiğinde OS gerçekte bağlanmış olsa bile ekran koşulsuz başarısız sayıyordu. Saha bulgusu: `wlp5s0 wifi bağlandı MedinceAP` iken "Beklenmedik bir hata oluştu" gösterilmesi ve `connected` eventi üretilmemesi.

**Root cause:** `connect()` içinde `catch(err)` → koşulsuz `connectError = ...` ataması. Wi-Fi bağlantı durumu hiç sorgulanmıyordu.

**Çözüm:** `/wifi-connect` hata verirse, `fetchWifiStatus()` ile `/wifi-status` üzerinden kısa ve sınırlı poll (3 deneme × 2 sn). Seçilen SSID aktif bağlı ağ olarak doğrulanırsa `connected` eventi gönderilir, hata gösterilmez. Gerçek başarısızlıklarda orijinal hata gösterilmeye devam eder. `_reconcileId` guard ile duplicate event ve stale poll koruması. `onDestroy` ile pending timer/resolver temizliği.

**Dosyalar:** `kiosk_edge/ui/src/components/WifiSetupScreen.svelte` (tek üretim dosyası), `kiosk_edge/ui/src/__tests__/WifiSetupScreen.test.js` (yeni test dosyası — 7 test, tümü geçti)

**Etki:** Wi-Fi bağlantısı başarılı ancak HTTP yanıtı başarısız olduğunda kullanıcı doğru şekilde ana/idle ekrana yönlendirilir. Yanlış şifre gibi gerçek başarısızlıklar hata olarak gösterilmeye devam eder.

---

## 2026-08-11

### [Backend + Kiosk Edge + Web Panels] Barkod Logo Yönetimi — düzeltmeler (r2)

**Değişiklik:** İlk uygulamadaki 8 açık kapatıldı.

1. **PROTECT FK**: `OturumLogu.barkod_logo` SET_NULL→PROTECT. `0014` migration rollback+fix. Fiziksel logo silme 405.
2. **PNG doğrulama yeniden yazıldı**: stdlib (struct+zlib, Pillow yok). Piksel decode: RGBA opak kabul; alfa<255 red; RGB renkliyse red; tRNS red; palette gri kontrolü. `0002_alter_*` migration eklendi.
3. **Atomik commit**: `commitBasariliBaski(db, logoId, idempotencyKey)` — counter+cursor+outbox tek transaction. Süreç çökmesi dokümante edildi.
4. **Bozuk aday atla**: `buildReceiptBuffer({logoCandidates})` tüm adayları bellekte dener; `sendToTransport` tek seferlik. `getOrderedLogoCandidates(db)` eklendi.
5. **Yetki testleri**: Anonim/eczacı red, superadmin kabul.
6. **Panel**: `npm test` (57 test, 5 dosya) + `npm run build` (✓) çalıştırıldı.
7. **Dokümantasyon**: 01, 02, 03, 05, 06, 07 güncellendi.
8. **Son kontroller**: `manage.py check` ✓, `makemigrations --check` ✓, backend 566 test ✓, edge 170 test ✓.

**Dosyalar:** `apps/barkod_logo/serializers.py`, `apps/barkod_logo/migrations/0002_*`, `apps/analytics/models.py`, `apps/analytics/migrations/0014_*`, `apps/barkod_logo/tests/test_barkod_logo.py`, `kiosk_edge/api-node/src/{barkodLogoService,printer,server}.js`, `kiosk_edge/api-node/tests/{barkodLogo,printerBuffer,offline_handler}.test.js`, `docs/ai/{01,02,03,05,06,07,99}-*.md`

---

### [Backend + Kiosk Edge + Web Panels] Barkod Logo Yönetimi — yeni özellik

**Değişiklik:** Kiosk fiş baskısında sabit `e-ISA` başlığının yerini alacak bağımsız logo rotasyon sistemi.

**Backend:**
- Yeni `apps.barkod_logo` uygulaması: `BarkodLogo` modeli (UUID PK, ad, media_url, object_key, checksum, baslangic/bitis_zamani, aktif, gunluk_baski_limiti, hedef_kiosklar M2M), migration `0001_initial`.
- `/api/barkod-logo/logolar/` (ModelViewSet, SuperAdmin), `/api/barkod-logo/upload-gorsel/` (PNG doğrulama: format, 336×336, ≤1 MB, alfa kanalı).
- `OturumLogu.barkod_logo` FK (SET_NULL), migration `analytics/0014`.
- `KioskCatalogView`: `barkod_logolar` snapshot (aktif + bitis_zamani > now + hedef kiosk).
- Session ingest: opsiyonel `barkod_logo_id` alanı; gecikmiş outbox logo pasifleşmiş olsa bile kabul edilir.

**Kiosk Edge:**
- SQLite: `barkod_logolar`, `barkod_logo_baski_sayaclari` tabloları (SCHEMA_VERSION değişmedi; `CREATE TABLE IF NOT EXISTS`).
- `barkodLogoService.js`: round-robin (`last_barkod_logo_id`), günlük sayaç, cache download.
- `printer.js`: `pngToEscposRaster()` — built-in `node:zlib` ile PNG → ESC/POS GS v 0 raster.
- `server.js`: logo adayı seç → yazdır → başarılıysa sayaç/cursor/outbox_payload güncelle.
- `scheduler.js`: `pullFromCentral`'da `barkod_logolar` snapshot sync.

**Web Panels:** `BarkodLogoYonetimi.vue`, router `/admin/barkod-logolar`, AdminLayout menüsü.

**Testler:** 20 backend + 162 edge (tümü pass). Fiziksel yazıcı testi yapılmadı.

**Dosyalar:** `apps/barkod_logo/**`, `apps/analytics/migrations/0014*`, `apps/analytics/models.py`, `apps/analytics/serializers.py`, `apps/analytics/services.py`, `apps/kiosk_api/views.py`, `core_api/settings.py`, `core_api/urls.py`, `kiosk_edge/api-node/src/{barkodLogoService,printer,server,scheduler,db}.js`, `kiosk_edge/api-node/tests/{barkodLogo,helpers,offline_handler}.js`, `web_panels/src/views/admin/BarkodLogoYonetimi.vue`, `web_panels/src/router/index.js`, `web_panels/src/views/admin/AdminLayout.vue`

---

### [Kiosk Edge] 5 Issue Fix — QR offline, HAYIR butonu, etken madde kutuları, logo, AdPromo konumu

**QR Gerçek Kök Neden:** `server.js`'de `!hasSlot` bloğu senkron backend çağrısı yapıyordu; backend kapalıyken 503 döndürüyor, App.svelte'de `completed=true` için try/catch yoktu → UI çöküyordu.

**Değişiklikler:**
1. **QR offline-first**: `server.js` `!hasSlot` → anında `503 kiosk_no_missing` (eski senkron backend fallback kaldırıldı). Sync-durum polling endpoint `GET /api/oturum/sync-durum/:key` eklendi. `api.js` `submitSession` artık `syncDurum` döner; `fetchSessionSyncStatus` eklendi. App.svelte `doSubmitSession`/`doSubmitConsult` hata yakalamaya alındı; result store'a `syncDurum` ve `idempotencyKey` eklendi. ResultScreen 3s/+8s sonra durum polllar; gönderilmemişse köşede koyu sarı ünlem ikonu gösterir.
2. **HAYIR butonu koyu gri**: QuestionScreen.svelte `.btn-hayir` scoped class → `#4B5563/#374151` gradient.
3. **Etken madde kutuları**: ResultScreen ana/destek/ek ayrımı kaldırıldı; tüm `recs` eşit beyaz kutu (`ingredient-box`) koyu kırmızı (`#7f1d1d`) zemin üzerinde gösterilir.
4. **Logo**: ResultScreen'deki `e-isa` metin logosu kaldırıldı; `<Logo height="40px" />` kullanıldı.
5. **AdPromo konumu**: `.ad-promo` `align-items: center → flex-end`, normal: `padding-bottom:20px`, large: `padding-bottom:48px`.

**Dosyalar:** `kiosk_edge/api-node/src/server.js`, `kiosk_edge/ui/src/lib/api.js`, `kiosk_edge/ui/src/App.svelte`, `kiosk_edge/ui/src/components/ResultScreen.svelte`, `kiosk_edge/ui/src/components/QuestionScreen.svelte`, `kiosk_edge/ui/src/components/AdPromo.svelte`
**Build:** `vite build` ✓ 142 modül, 0 hata.

---

## 2026-08-09


### [Web Panels + Backend] 4 Issue Fix — video aktif medya, job worker, video thumbnail, yayın akışı

**Değişiklik:**
1. **CampaignWizard — active_media_url video desteği**: İşlem ekranı alt alan upload `accept="image/*"` → `accept="image/*,video/mp4,video/webm"`; preview `<img>` → `isVideoUrl()` yardımcısı ile koşullu video/image gösterimi. Backend `Creative.active_media_url` kısıtsız URLField olduğundan değişiklik gerekmedi.
2. **run_scheduler.py — drain_queue job eklendi**: `drain_queue` APScheduler'a `IntervalTrigger(seconds=30)` ile eklendi. Bu eksiklik nedeniyle `invalidation_service` tarafından üretilen PENDING GenerationJob'lar hiç işlenmiyordu; kampanyalar kioskına ulaşmıyordu. Tek gerçek kod kaynağı: scheduler servisi `drain_queue`'yu kaydetmiyordu.
3. **CampaignWizard — video thumbnail**: Kampanya listesinde `<img :src="thumbOf(c)">` → `isVideoUrl()` kontrolüyle video kartı (ikon+etiket) gösterimi; video için `<img>` render edilmez.
4. **KioskActivities — Yayın Akışı sekmesi**: Yeni "Yayın Akışı" tab; kiosk+tarih seçimi; saat-mutlak offset ile "şu an yayında" hesabı; kiosk online/geride/offline uyarısı; MediaView-uyumlu video/image preview; tüm günün saatlik playlist kartları. Backend: `GET /api/campaigns/v2/playlists/day-stream/` (read-only, N+1 yok, `select_related/prefetch_related`).

**Dosyalar:**
- `web_panels/src/views/admin/CampaignWizard.vue` — video accept, isVideoUrl helper, video-thumb-placeholder CSS
- `web_panels/src/views/admin/KioskActivities.vue` — Yayın Akışı tab + state + template + scoped CSS
- `web_panels/src/services/dooh.js` — `getKioskDayStream()` eklendi
- `backend/apps/campaigns/management/commands/run_scheduler.py` — drain_queue job kaydı
- `backend/apps/campaigns/views_v2.py` — `KioskDayStreamView` eklendi (read-only)
- `backend/apps/campaigns/urls.py` — day-stream URL kaydı
- `backend/apps/campaigns/tests/test_issue_fixes_2026_08.py` — 12 yeni test (T01–T10)

**DB migration/schema:** YOK — tüm değişiklikler mevcut şema üzerinde.
**Testler:** 285 passed, 7 skipped (backend); web_panels build ✓ (7.30s).
**Deployment notu:** `scheduler` servisi yeniden başlatılmalıdır: `python manage.py run_scheduler`. Yeni `drain_queue` job kayıtlandıktan sonra PENDING job'lar 30 saniye içinde işlenir.

### [Backend + Web Panels] Yayın Akışı desired/applied düzeltmesi (E2E doğrulama sonrası)

**Değişiklik:** Gerçek E2E + browser doğrulaması sırasında day-stream endpoint'in `desired_version`'ı `KioskDesiredBundle`'dan okuduğu (her zaman boş — Faz 5 stub) tespit edildi. Sistemin canonical alanlarına çevrildi: `desired_version = Kiosk.last_playlist_version`, `applied_version = Kiosk.applied_playlist_version` (+ `applied_horizon_end`, `playlist_applied_at`). Frontend `kioskSyncStatus` custom mantık yerine ortak `calcKioskRolloutStatus` composable'ını kullanır (offline/behind/ack_pending/no_publish/synced). Böylece Control Center ile Yayın Akışı aynı rollout sözleşmesini paylaşır.

**Dosyalar:**
- `backend/apps/campaigns/views_v2.py` — `KioskDayStreamView` canonical desired/applied (KioskDesiredBundle kaldırıldı)
- `web_panels/src/views/admin/KioskActivities.vue` — `calcKioskRolloutStatus` reuse + desired/applied gösterim
- `backend/apps/campaigns/tests/test_issue_fixes_2026_08.py` — 16 test (T01–T10 + T06b param-required, T06c canonical desired/applied, T06d N+1 max-query, T06e offset 0..3599)

**Gerçek E2E doğrulaması (local SQLite + run_scheduler):** Campaign create → 6 PENDING job → drain_queue (30sn interval) → RUNNING → DONE → 144 Playlist / 1440 PlaylistItem → `last_playlist_version` (desired) 6→9. attempt_count=1 (çift işleme yok), 0 FAILED. Browser: 13 senaryo screenshot (`docs/qa/screenshots-2026-08-09/`), console'da kırık image/taşma yok, video hiçbir yerde `<img src="*.mp4">` değil, liste kartlarında autoplay yok.

**DB migration/schema:** YOK.

---

## 2026-08-06

### [Backend+Kiosk+WebPanel] İçerik Yönetimi paneli, Danışma sıralama, Overflow göstergeleri

**Değişiklik:**
- `ContentManagement.vue` (yeni): İçerik Yönetimi admin sayfası; HouseAd CRUD, kiosk overlay önizleme, image-only upload (`media_kind=image`). Menü/başlık/form/bildirimde "HouseAd" terimi yok.
- `dooh.js`: `updateHouseAd`, `deleteHouseAd` eklendi; `uploadMedia(file, mediaKind)` imzası genişletildi.
- `router/index.js` + `AdminLayout.vue`: `/admin/content-management` route + menü kaydı "İçerik Yönetimi".
- `Danisma.sira`: `PositiveSmallIntegerField(default=100)` eklendi; `ordering = ("sira","ad")`; migration `0012_add_danisma_sira`.
- `DanismaSerializer` + `DanismaSyncSerializer`: `sira` alanı eklendi.
- `db.js`: idempotent `ALTER TABLE danisma_kategorileri ADD COLUMN sira` (SCHEMA_VERSION=14 sabit — DB reset yok).
- `scheduler.js` `upsertDanismaKategori()`: `sira ?? 100` eklendi.
- `ConsultScreen.svelte`: `_bySira` sıralaması; alt kategoriler de sıralı; overflow göstergeleri (gradient, rozet, pozisyon çubuğu, ResizeObserver, onDestroy cleanup).
- `DanismaYonetimi.vue`: `sira` form alanı eklendi.
- `CategoryScreen.svelte`: overflow göstergeleri (aynı mantık); `onMount`/`onDestroy` cleanup; alt-kategori gezinmesinde scroll sıfırlama.

**Dosyalar:** `web_panels/src/views/admin/ContentManagement.vue` (yeni), `dooh.js`, `router/index.js`, `AdminLayout.vue`, `DanismaYonetimi.vue`; `backend/apps/products/models.py`, `serializers.py`, `migrations/0012`; `kiosk_edge/api-node/src/{db,scheduler}.js`; `kiosk_edge/ui/src/components/{ConsultScreen,CategoryScreen}.svelte`
**Testler:** Backend 513 passed; kiosk UI build ✓ (854ms); web_panels build ✓ (5.78s)

---

### [Backend+Kiosk UI] HouseAd image-only, IdleScreen paid/HouseAd ayrımı, Soru geri dönüşü, Başka Şikayet Seç

**Değişiklik:**
- `MediaUploadView`: `media_kind=image` parametresiyle image-only mod; `IMAGE_ONLY_TYPES={jpeg,png,webp}`; magic-byte sniff (JPEG/PNG/WebP imza doğrulaması); creative upload'u bozulmadı.
- `HouseAdSerializer.validate_media_url`: video uzantılarını reddeden ikinci savunma katmanı.
- `AdStrip.svelte`: `asset_type === 'creative'` filtresi — house_ad öğeleri işlem ekranında artık gösterilmiyor.
- `IdleScreen.svelte`: `$playlistItems.asset_type` metadata korunarak paid/house_ad/fallback üç mod. Recursive `setTimeout` + genToken video yarış kilidi. `ROTATE_MS` sabit kaldırıldı; per-item `duration_seconds` kullanılıyor. AdPromo hiçbir modda tam ekran arka plan değil.
- `AdPromo.svelte`: `floatCard` prop — `position:relative; background:transparent` ile container konumlandırması.
- `QuestionScreen.svelte`: geri butonu (`currentQIndex > 0`), seçili cevap vurgusu (`btn-answer-selected`), `currentAnswers` store import.
- `App.svelte`: `goBackQuestion()` — cevaplar korunur, sadece farklı cevap verilince sonrakiler temizlenir. `startNewComplaint()` — yaş/cinsiyet korur, kategori+QR temizler, yeni sessionId.
- `ResultScreen.svelte`: "Başka Bir Şikayet Seç" butonu → `dispatch('newComplaint')`.
- Yeni test: `apps/campaigns/tests/test_house_ad_validation.py` (13 test, hepsi geçti).

**Dosyalar:** `backend/apps/campaigns/views.py`, `serializers.py`, `tests/test_house_ad_validation.py`; `kiosk_edge/ui/src/components/{AdStrip,IdleScreen,AdPromo,QuestionScreen,ResultScreen}.svelte`; `kiosk_edge/ui/src/App.svelte`
**Testler:** Backend 513 passed; kiosk UI build ✓ (843ms)

---

### [Backend+Edge+WebPanel] QR/Session akışı offline-first hale getirildi

**Değişiklik:**
- `Kiosk.eczane_kiosk_no` (1-31, eczane-unique) eklendi; bootstrap response'a dahil edildi; mevcut kiosklar backfill edildi (pharmacies migration 0010).
- `OturumLogu.eczane` FK (nullable, SET_NULL) eklendi; `qr_kodu` nullable + max_length=9 yapıldı; global unique kaldırılıp eczane-scoped conditional unique eklendi (analytics migration 0012).
- `ingest_session_items()`: kiosk'tan gelen 9-char Crockford QR doğrulanıp kabul edilir; eski kiosklarda 8-char backend üretimi fallback olarak korunur; tamamlandi=False → qr_kodu=null.
- Eczacı QR sorgusu: önce `eczane_id` scope'lanır, başka eczane kodu 403 yerine 404 döner.
- Edge `qrGen.js`: Crockford Base32 QR üretimi, mantıksal sayaç (monoton), checksum.
- Edge `db.js` v14: `qr_counter` singleton tablosu eklendi.
- Edge `server.js`: tamamlanan oturum QR'ı yerelde üretilir (atomik txn), hemen döner; backend push `setImmediate` ile arka planda çalışır.
- Edge `provisioning.js`: `eczane_kiosk_no` bootstrap response'tan SQLite'a kaydedilir; `settings.eczaneKioskNo` olarak yayılır.
- `QrScan.vue`: 8 ve 9 karakter formatları kabul edilir; Crockford checksum doğrulama; başka eczane mesajı kaldırıldı.
- Hedefli testler: backend 155 passed, edge qrGen 43 passed; server.test.js pre-existing failure (scheduler.js encoding issue, bizim değil).

**Dosyalar:** backend/apps/pharmacies/models.py, migrations/0010; backend/apps/analytics/models.py, services.py, views.py, migrations/0012; backend/apps/kiosk_api/views.py; backend/apps/analytics/tests/test_qr_flow.py, test_session_normalization.py; kiosk_edge/api-node/src/{qrGen.js,db.js,server.js,provisioning.js}; kiosk_edge/api-node/tests/qrGen.test.js; web_panels/src/views/pharmacist/QrScan.vue
**Migration:** pharmacies/0010 (eczane_kiosk_no + backfill), analytics/0012 (eczane FK + qr nullable + constraint)

---

## 2026-08-01

### [Backend+Frontend] Eczacı kampanyası: il/ilçe hedefleme + duration validation + UI düzeltmeleri

**Değişiklik:**
- `PharmacyCampaign.target_iller` + `target_ilceler` M2M eklendi (migration 0024).
- `duration_seconds` default 15; serializer'da yalnız 15/30/60 kabul edilir (eski kayıt aynı değerle güncellenebilir).
- Feed OR mantığı: eczane, il veya ilçe eşleşmesi; hiç hedefi olmayan kampanya feed'e girmez.
- EisaLookup entegrasyonu düzeltildi: eczaneler `/api/pharmacies/` endpoint'inden yüklenir; il/ilçe/eczane seçimi v-model + watch ile çalışır.
- Grid thumbnail: 120×68px, `object-fit: contain`, sabit yükseklik.
- Duration: serbest input → 15/30/60 seçenekli select.
- Backend test sayısı: 19 geçti.

**Dosyalar:** backend/apps/campaigns/{models,serializers,views_v2}.py; migrations/0024; tests/test_pharmacy_campaign.py; web_panels/src/views/admin/PharmacyCampaigns.vue
**Build:** web_panels ✅ (2.45s)

---

## 2026-07-31

### [Backend+Kiosk+Frontend] Kiosk çift medya varyantı + Eczacı paneli kampanyaları

**Değişiklik:**
- `Creative.active_media_url` nullable alan eklendi (migration 0021); bekleme (portrait) ve alt alan (~7:5) ayrı görseller.
- `PharmacyCampaign` modeli eklendi (migration 0022); kiosk sisteminden bağımsız eczacı paneli kampanyaları.
- `KioskCreativeSyncSerializer`, `KioskPlaylistItemSerializer` — `active_media_url` additive eklendi.
- api-node: `db.js` SCHEMA_VERSION 12; creatives kolonu; `scheduler.js` upsert; `mediaCache.js` `_active` suffix cache; `server.js` playlist/current LEFT JOIN ile `active_media_url`.
- `AdStrip.svelte`: `active_media_url` varsa cover, yoksa `media_url` + `object-fit: contain` (letterbox).
- Admin: CampaignWizard step 2 → iki upload alanı (Bekleme/İşlem ekranı); AdminLayout yeni menü.
- Yeni: `PharmacyCampaigns.vue` (admin), `PharmacistCampaignDisplay.vue` (eczacı şerit + 90s idle overlay).
- Feed endpoint: `GET /api/campaigns/v2/pharmacy-campaigns/feed/` — `request.user.eczane_id` ile güvenli filtreleme.

**Dosyalar:** backend/apps/campaigns/{models,serializers,views_v2,urls,migrations/0021-0022}.py; kiosk_edge/api-node/src/{db,scheduler,mediaCache,server}.js; kiosk_edge/ui/src/{components/AdStrip.svelte,app.css}; web_panels/src/{views/admin/{CampaignWizard,PharmacyCampaigns}.vue,components/pharmacist/PharmacistCampaignDisplay.vue,views/admin/AdminLayout.vue,router/index.js,styles.css}
**Testler:** 246 passed, 7 skipped (5 yeni PC-01..05 testi dahil)

---

## 2026-07-24

### [kiosk_edge] Tam ekran portré CSS — 100vw × 100vh

**Değişiklik:** `app.css` — `body` padding/centering kaldırıldı; `.kiosk` `width: 100vw; height: 100vh` yapıldı (`border-radius`, `box-shadow`, sabit 794×1123 px kaldırıldı). 1080×1920 ve 1440×2560 her ikisi de 9:16 oran olduğundan aynı kural ikisini de tam doldurur. Önceki media query (min-width: 1100px) supersede edildiği için kaldırıldı.
**Dosyalar:** `kiosk_edge/ui/src/app.css`
**Etki:** UI build ✅ (765ms). Scrollbar yok, taşma yok.

**Değişiklik:**
- `printer.js`: Fiş içeriği yenilendi — "e-ISA" (bold) + "Saglikli gunler diler." + QR + QR metin değeri. Kategori/kod/açıklama satırları kaldırıldı. ESC/POS QR modül boyutu 6 → 16 (~42 mm @ 203 DPI, ESC/POS maks.).
- `app.css`: `@media (min-width: 1100px) and (orientation: portrait)` kuralı eklendi. 1440 × 2560 ekranda `.kiosk` viewport genişliğini doldurur (794/1123 en-boy oranını koruyarak); 1080 × 1920 görünümü değişmez.

**Dosyalar:** `kiosk_edge/api-node/src/printer.js`, `kiosk_edge/ui/src/app.css`
**Etki:** Kiosk UI build ✅ (1.25s), printer.js syntax ✅. QR formatı/session akışı dokunulmadı.

---

## 2026-08-16

### [Backend+WebPanel+KioskEdge+KioskUI] HouseAd kaldırıldı; İçerik Yönetimi başlık/metin idle içeriğine geçti

**Değişiklik:** DOOH filler (HouseAd) sistemi uçtan uca kaldırıldı; playlist campaign-only oldu (boş playlist geçerli → kiosk idle ekranı). "İçerik Yönetimi" yeni başlık/metin tabanlı idle içeriğine dönüştürüldü.

**Backend:**
- `HouseAd` modeli/tablosu (`dooh_house_ads`), serializer, viewset (`/api/campaigns/v2/house-ads/`), scheduler Pass-4 filler, PlacementEngineV2 `_fill_house_ads`, kiosk sync `house_ads` KALDIRILDI (migration 0027).
- `PlaylistItem.house_ad` + `PlayLog.house_ad` FK'leri kaldırıldı; `PlaylistItem.clean()` creative zorunlu (creative-only).
- YENİ `IdleScreenContent` modeli (app: campaigns, tablo `dooh_idle_screen_contents`: `baslik`≤100, `metin`≤300, `aktif`) + CRUD API `GET/POST/PUT/PATCH/DELETE /api/campaigns/v2/idle-contents/` (JWT SuperAdmin, basename `dooh-idle-content`).
- Kiosk sync artık `house_ads` yerine `idle_contents` (aktif; `KioskIdleContentSyncSerializer`) döner. Proof-of-play `house_ad_id` gelse de yok sayılır.

**Kiosk Edge (api-node):** YENİ SQLite `idle_contents` tablosu; pull sync transaction içinde upsert + reconcile (offline'da son cache korunur); v15 idempotent migration `house_ads` tablosunu düşürür + `media_cache` house_ad satırlarını siler; YENİ salt okunur `GET /api/idle-contents` lokal endpoint.

**Web panel:** "İçerik Yönetimi" (`/admin/content-management`) korundu ama yeni IdleScreenContent CRUD'unu açar (`ContentManagement.vue`; liste, ekle/düzenle/aktif-pasif/silme, 0/100 & 0/300 sayaç, sağlık uyarı notu, 1080×1920 önizleme). Eski `HouseAdManagement.vue` + `dooh.js` house-ad metotları kaldırıldı; yeni `listIdleContents/createIdleContent/updateIdleContent/deleteIdleContent`.

**Kiosk UI:** YENİ `lib/idleContentStore.js` (shuffled-bag rotasyon, dwell 12–20s); `AdPromo` `large` varyantı → başlık (fade) + heartbeat (değişmedi) + metin (tek-seferlik typewriter) + SABİT CTA "Size özel öneriler için DOKUNUN". `small` varyant değişmedi. AdStrip/resolver/edge house_ad öğelerini defansif atlar.

**Migration:** campaigns/0027 (HouseAd drop + IdleScreenContent), edge SQLite v15.

---

### [Kiosk UI] Kalp Atışı Animasyonu Güncelleme — Beyaz 3-Pikli + Smile Curve + Modüler Widget

**Değişiklik:** Sponsor fallback ekranındaki animasyon özelleştirilerek yeni modüler widget olarak ayrıldı.

**Yeni özellikler:**
- **3 pikli kalp atışı:** Küçük-BÜYÜK-küçük ritim (ortadaki 2 kat büyük pik: y:40-160 vs y:80-100)
- **Beyaz renk şeması:** Tüm animasyon beyaz (#fff) - gradient, çizgiler, halkalar, glow
- **Gülen yüz (smile curve):** Kalp atışının altında bezier eğrisi `M220,130 Q260,150 Q300,130`
- **Modüler yapı:** `HeartbeatAnimation.svelte` ayrı component (yeniden kullanılabilir)
- **Daha büyük halkalar:** 140px başlangıç → 460px bitiş (önceki 120-420px)
- **Döngü:** 2.8sn (önceki 2.6sn), yumuşak ve sakin
- Animasyon `prefers-reduced-motion: reduce` durumunda durur

**Dosyalar:**
- `kiosk_edge/ui/src/components/HeartbeatAnimation.svelte` (YENİ - 250 satır)
- `kiosk_edge/ui/src/components/AdPromo.svelte` (eski EKG kodu kaldırıldı, HeartbeatAnimation import)
- `docs/ai/04-kiosk-edge-ui.md` (component #11 eklendi, numaralandırma güncellendi)

**Test:** Build başarılı (93KB bundle), http://127.0.0.1:5173/ → animasyon görünür, dokunma çalışıyor, demographics geçişi OK.

---

## 2026-08-15

### [Kiosk UI] İdeal/Attractor Ekranına Dekoratif EKG Animasyonu

**Değişiklik:** Reklam olmadığında gösterilen sponsor fallback ekranına (AdPromo.svelte large varyant) sağlık teknolojisi temalı dekoratif animasyon eklendi.

**Animasyon özellikleri:**
- Yatay EKG çizgisi (soldan sağa ilerleyen parlak enerji izi, SVG `stroke-dasharray` + `stroke-dashoffset` animasyon)
- İki pikli kalp atışı ritmi (gerçekçi EKG dalga formu, 2.6sn döngü)
- Eş merkezli kırmızı halkalar (merkezden dışa yayılıp saydamlaşma, 3 halka 0s/0.15s/0.3s gecikme)
- Merkez kırmızı glow efekti (`radial-gradient` + pulse)
- e-isa kırmızı (#B1121B), beyaz, koyu lacivert renk paleti
- `clamp(460px, 28vw, 540px)` responsive boyut, ekran ortasında (~%48-52 yükseklik)
- `pointer-events: none`, `aria-hidden="true"` — dokunma engellenmez
- `prefers-reduced-motion: reduce` → animasyonlar durur, statik EKG + halkalar görünür

**Korunan öğeler (DEĞIŞMEDI):**
- Mevcut arka plan, renkler ve gradient
- Üst logo, "Başlamak için dokunun" metni ve el ikonu
- Alt "Bu alana sponsor olabilirsiniz" kartı (megafon + shimmer başlık)
- Tüm öğelerin konumları, ölçüleri, stilleri
- Mevcut dokunma/click davranışı (demographics geçişi)
- Kampanya/house ad medya gösterimi (animasyon YOK, medya tam ekran gösterilir)
- Playlist, MediaView, impression akışları
- Responsive davranış
- `AdPromo` küçük varyantında animasyon YOKTUR (yalnız `large` modda)

**Teknik:** Inline SVG + CSS animasyonlar, harici dependency veya görsel dosya YOK. Chromium kiosk uyumlu, performans optimizasyonlu (küçük öğeler üzerinde glow, ağır filtre yok).

**Dosyalar:** `kiosk_edge/ui/src/components/AdPromo.svelte` (HTML + CSS), `docs/ai/04-kiosk-edge-ui.md` (AdPromo açıklaması güncellendi)

**Test:** Manuel doğrulama (http://127.0.0.1:5173/, idle ekran → sponsor fallback → animasyon görünür, dokunma → demographics ekran). Gerçek kampanya gösterilirken animasyon görünmez.

---

## 2026-08-15

### [Backend/Frontend] Medya Kalıcı URL, Creative/HouseAd İndirme, HouseAd Yönetim Ekranı

**Root cause:** `DOOH_PERSISTENT_MEDIA_URL=False` (default) nedeniyle upload sırasında süreli presigned URL veritabanına yazılıyordu. Süre dolunca medya admin panelde görünmez oluyordu.

**Değişiklikler özeti:**
1. `DOOH_PERSISTENT_MEDIA_URL` default=True yapıldı; yeni yüklemelerde presigned URL DB'ye yazılmıyor.
2. `Creative.active_object_key` modeli ve migration 0026 eklendi.
3. `CreativeSerializer` + `active_object_key`; HouseAd video kısıtlaması kaldırıldı.
4. `CreativeViewSet` ve `HouseAdViewSet`'e `/download/` streaming action eklendi (SuperAdmin, Content-Disposition:attachment).
5. `backfill_media_object_keys` komutu `active_media_url` backfill'ini de destekliyor.
6. `CampaignWizard.vue`: HTML5 video player + görsel thumbnail, Bekleme/İşlem medya ayrımı, `active_object_key` takibi.
7. `HouseAdManagement.vue` yeni sayfa (CRUD + medya önizleme + indirme).
8. Router + AdminLayout güncellendi.

**API (additive):** `GET /api/campaigns/v2/creatives/{id}/download/`, `GET /api/campaigns/v2/house-ads/{id}/download/`
**Test:** 13 yeni test, test_closure C01 + test_house_ad_validation HA08 güncellendi (305 passed).

---

## 2026-08-15

### [Backend/Frontend] Görüş ve Destek (Ticket) Sistemi

**Değişiklik:** Pharmacy ve Admin panellerinde kullanılacak tam kapsamlı destek talebi sistemi eklendi.

**Backend (`apps.destek`):**
- `DestekParametresi` — TALEP_TURU/ALAN/ALT_KONU/DURUM gruplarını yöneten tek parametrik tablo.
- `TalepSayac` — Concurrency-safe yıllık sayaç (`select_for_update`). `count+1` kullanılmadı.
- `DestekTalebi` — Ticket modeli (talep_no: `EISA-YYYY-NNNNNN`, PROTECT FK'lar).
- `DestekYorumu` — Append-only yorum geçmişi; durum otomatik geçişleri (admin→YANITLANDI, eczacı cevabı→INCELENIYOR).
- API: `/api/destek/parametreler/`, `/api/destek/talepler/` (list/create/retrieve + yorum-ekle/durum-degistir/yeni-sayisi).
- Queryset izolasyonu: eczacı yalnız kendi eczanesinin taleplerini görür.
- 40 backend testi; tamamı geçiyor.

**Frontend:**
- `DestekTalepleri.vue` (pharmacist) — Karşılama banner, yeni talep formu, liste, detay modal + konuşma.
- `DestekYonetimi.vue` (admin) — Filtreli liste, detay modal, yorum ekleme, durum değiştirme.
- `AdminLayout.vue` — "Görüş ve Destek Yönetimi" ve "Görüş ve Destek" nav öğeleri; Yeni sayısı badge.
- Router: `/admin/destek`, `/pharmacist/destek`.

**Dosyalar:**
- `backend/apps/destek/` (yeni app — models, serializers, views, urls, migrations, seed, tests)
- `backend/core_api/settings.py`, `core_api/urls.py`
- `web_panels/src/views/admin/DestekYonetimi.vue` (yeni)
- `web_panels/src/views/pharmacist/DestekTalepleri.vue` (yeni)
- `web_panels/src/router/index.js`, `AdminLayout.vue`, `services/api.js`, `styles.css`

---

### [Backend/Frontend] Dashboard Satış İstatistikleri, Kiosk Hareketleri Satış Sekmesi, AutoComplete

**Değişiklik:** Üç özellik birlikte uygulandı:

1. **Dashboard Satış İstatistikleri:**  
   - `AdminDashboardView` ve `EczaciDashboardView` API'lerine `satis_sayisi` ve `en_cok_satilan_etken_madde` eklendi.  
   - Opsiyonel `start_date` / `end_date` query parametreleriyle tarih filtresi.  
   - Eczacı yalnız kendi eczanesine ait veriye erişir (backend queryset scope).  
   - Admin/Eczacı Dashboard UI'larına iki yeni KPI kartı ve tarih filtreli "Satış Özeti" paneli eklendi.

2. **Kiosk Hareketleri Satış Sekmesi:**  
   - `_build_oturum_queryset`'e `?sold=true|false` filtresi eklendi.  
   - `KioskActivityView`, `sold=true` isteklerinde `prefetch_related` uyguluyor (N+1 yok).  
   - `KioskActivityListSerializer`'a `sold` ve `etken_madde_adlari` alanları eklendi.  
   - Admin ve Eczacı KioskActivities panellerine "Satışlar" sekmesi eklendi.

3. **Kiosk/Eczane AutoComplete:**  
   - Admin KioskActivities: il/ilçe/eczane/kiosk 4'lü cascading `<select>` kaldırıldı; yerine "İl/İlçe/Eczane" ve "İl/İlçe/Eczane/Kiosk" birleşik etiketli 2 EisaLookup eklendi.  
   - Eczacı KioskActivities: kiosk `<select>` → EisaLookup (dashboard'dan kiosk listesi).  
   - Tüm seçim sonuçları mevcut kiosk/eczane ID değerini API'ye iletmeye devam eder.

**Yetkilendirme:** Tüm sold filtreleri ve istatistikler backend queryset seviyesinde eczane scope ile korunmaktadır. Frontend seçimlerine güvenilmiyor.

**Dosyalar:**  
- `backend/apps/analytics/views.py` — sold filtresi, AdminDashboard sold stats, KioskActivityView prefetch  
- `backend/apps/analytics/serializers.py` — KioskActivityListSerializer sold + etken_madde_adlari  
- `backend/apps/pharmacies/dashboard.py` — EczaciDashboard sold stats  
- `backend/apps/analytics/tests/test_sold_stats.py` — 13 yeni test (hepsi geçiyor)  
- `web_panels/src/views/admin/Dashboard.vue` — sold KPI kartları, tarih filtresi  
- `web_panels/src/views/pharmacist/Dashboard.vue` — sold KPI kartları, tarih filtresi  
- `web_panels/src/views/admin/KioskActivities.vue` — Satışlar sekmesi, EisaLookup AutoComplete  
- `web_panels/src/views/pharmacist/KioskActivities.vue` — Satışlar sekmesi, EisaLookup kiosk  
- `web_panels/src/services/analytics.js` — getAdminDashboard() eklendi

**API eklenti:** `GET /api/analytics/admin-dashboard/` → `satis_sayisi`, `en_cok_satilan_etken_madde` (mevcut alanlar korundu); `GET /api/pharmacies/me/dashboard/` → aynı. `GET /api/analytics/kiosk-activities/?sold=true|false` yeni filtre.

---

## 2026-08-12

### [Backend/DOOH] Aktivasyon timeout düzeltmesi — queue tabanlı horizon aktivasyon

**Değişiklik:** `POST /api/campaigns/v2/campaigns/{id}/activate/` artık kampanyanın tüm tarih aralığı için senkron playlist üretmiyor. Endpoint doğrulama yapıp üretimi mevcut DB-backed queue'ya (`GenerationJob`) bırakıyor; kapsam yalnız rolling horizon (varsayılan 3 gün).

**Kritik davranışlar:**
- GUARANTEED için horizon pre-check başarısızsa 409 dönüyor ve `campaign_activate` job enqueue edilmiyor (kısmi publish başlamaz).
- Tekrarlı aktivasyonlar mevcut dedupe/coalesce (`kd:{kiosk_id}:{date}`) ile duplicate `PENDING` job üretmiyor.
- `PlacementEngineV2` date filtreleri timezone-aware gün sınırlarıyla düzeltildi; naive datetime RuntimeWarning giderildi.
- `PlaylistItem` persistlerinde `bulk_create(batch_size=500)` kullanıldı.

**Dosyalar:** `backend/apps/campaigns/services/activation_service.py`, `backend/apps/campaigns/views_v2.py`, `backend/apps/campaigns/services/placement_engine_v2.py`, `backend/apps/campaigns/services/scheduler.py`, `backend/apps/campaigns/tests/test_faz3_simulation_activation.py`, `docs/ai/06-db-and-api-contracts.md`, `docs/ai/08-dooh-advertising.md`

---

### [Kiosk Edge UI] WifiSetupScreen — Wi-Fi yanlış-negatif reconciliation düzeltmesi

**Değişiklik:** `/wifi-connect` HTTP isteği hata verdiğinde OS gerçekte bağlanmış olsa bile ekran koşulsuz başarısız sayıyordu. Saha bulgusu: `wlp5s0 wifi bağlandı MedinceAP` iken "Beklenmedik bir hata oluştu" gösterilmesi ve `connected` eventi üretilmemesi.

**Root cause:** `connect()` içinde `catch(err)` → koşulsuz `connectError = ...` ataması. Wi-Fi bağlantı durumu hiç sorgulanmıyordu.

**Çözüm:** `/wifi-connect` hata verirse, `fetchWifiStatus()` ile `/wifi-status` üzerinden kısa ve sınırlı poll (3 deneme × 2 sn). Seçilen SSID aktif bağlı ağ olarak doğrulanırsa `connected` eventi gönderilir, hata gösterilmez. Gerçek başarısızlıklarda orijinal hata gösterilmeye devam eder. `_reconcileId` guard ile duplicate event ve stale poll koruması. `onDestroy` ile pending timer/resolver temizliği.

**Dosyalar:** `kiosk_edge/ui/src/components/WifiSetupScreen.svelte` (tek üretim dosyası), `kiosk_edge/ui/src/__tests__/WifiSetupScreen.test.js` (yeni test dosyası — 7 test, tümü geçti)

**Etki:** Wi-Fi bağlantısı başarılı ancak HTTP yanıtı başarısız olduğunda kullanıcı doğru şekilde ana/idle ekrana yönlendirilir. Yanlış şifre gibi gerçek başarısızlıklar hata olarak gösterilmeye devam eder.

---

## 2026-08-11

### [Backend + Kiosk Edge + Web Panels] Barkod Logo Yönetimi — düzeltmeler (r2)

**Değişiklik:** İlk uygulamadaki 8 açık kapatıldı.

1. **PROTECT FK**: `OturumLogu.barkod_logo` SET_NULL→PROTECT. `0014` migration rollback+fix. Fiziksel logo silme 405.
2. **PNG doğrulama yeniden yazıldı**: stdlib (struct+zlib, Pillow yok). Piksel decode: RGBA opak kabul; alfa<255 red; RGB renkliyse red; tRNS red; palette gri kontrolü. `0002_alter_*` migration eklendi.
3. **Atomik commit**: `commitBasariliBaski(db, logoId, idempotencyKey)` — counter+cursor+outbox tek transaction. Süreç çökmesi dokümante edildi.
4. **Bozuk aday atla**: `buildReceiptBuffer({logoCandidates})` tüm adayları bellekte dener; `sendToTransport` tek seferlik. `getOrderedLogoCandidates(db)` eklendi.
5. **Yetki testleri**: Anonim/eczacı red, superadmin kabul.
6. **Panel**: `npm test` (57 test, 5 dosya) + `npm run build` (✓) çalıştırıldı.
7. **Dokümantasyon**: 01, 02, 03, 05, 06, 07 güncellendi.
8. **Son kontroller**: `manage.py check` ✓, `makemigrations --check` ✓, backend 566 test ✓, edge 170 test ✓.

**Dosyalar:** `apps/barkod_logo/serializers.py`, `apps/barkod_logo/migrations/0002_*`, `apps/analytics/models.py`, `apps/analytics/migrations/0014_*`, `apps/barkod_logo/tests/test_barkod_logo.py`, `kiosk_edge/api-node/src/{barkodLogoService,printer,server}.js`, `kiosk_edge/api-node/tests/{barkodLogo,printerBuffer,offline_handler}.test.js`, `docs/ai/{01,02,03,05,06,07,99}-*.md`

---

### [Backend + Kiosk Edge + Web Panels] Barkod Logo Yönetimi — yeni özellik

**Değişiklik:** Kiosk fiş baskısında sabit `e-ISA` başlığının yerini alacak bağımsız logo rotasyon sistemi.

**Backend:**
- Yeni `apps.barkod_logo` uygulaması: `BarkodLogo` modeli (UUID PK, ad, media_url, object_key, checksum, baslangic/bitis_zamani, aktif, gunluk_baski_limiti, hedef_kiosklar M2M), migration `0001_initial`.
- `/api/barkod-logo/logolar/` (ModelViewSet, SuperAdmin), `/api/barkod-logo/upload-gorsel/` (PNG doğrulama: format, 336×336, ≤1 MB, alfa kanalı).
- `OturumLogu.barkod_logo` FK (SET_NULL), migration `analytics/0014`.
- `KioskCatalogView`: `barkod_logolar` snapshot (aktif + bitis_zamani > now + hedef kiosk).
- Session ingest: opsiyonel `barkod_logo_id` alanı; gecikmiş outbox logo pasifleşmiş olsa bile kabul edilir.

**Kiosk Edge:**
- SQLite: `barkod_logolar`, `barkod_logo_baski_sayaclari` tabloları (SCHEMA_VERSION değişmedi; `CREATE TABLE IF NOT EXISTS`).
- `barkodLogoService.js`: round-robin (`last_barkod_logo_id`), günlük sayaç, cache download.
- `printer.js`: `pngToEscposRaster()` — built-in `node:zlib` ile PNG → ESC/POS GS v 0 raster.
- `server.js`: logo adayı seç → yazdır → başarılıysa sayaç/cursor/outbox_payload güncelle.
- `scheduler.js`: `pullFromCentral`'da `barkod_logolar` snapshot sync.

**Web Panels:** `BarkodLogoYonetimi.vue`, router `/admin/barkod-logolar`, AdminLayout menüsü.

**Testler:** 20 backend + 162 edge (tümü pass). Fiziksel yazıcı testi yapılmadı.

**Dosyalar:** `apps/barkod_logo/**`, `apps/analytics/migrations/0014*`, `apps/analytics/models.py`, `apps/analytics/serializers.py`, `apps/analytics/services.py`, `apps/kiosk_api/views.py`, `core_api/settings.py`, `core_api/urls.py`, `kiosk_edge/api-node/src/{barkodLogoService,printer,server,scheduler,db}.js`, `kiosk_edge/api-node/tests/{barkodLogo,helpers,offline_handler}.js`, `web_panels/src/views/admin/BarkodLogoYonetimi.vue`, `web_panels/src/router/index.js`, `web_panels/src/views/admin/AdminLayout.vue`

---

### [Kiosk Edge] 5 Issue Fix — QR offline, HAYIR butonu, etken madde kutuları, logo, AdPromo konumu

**QR Gerçek Kök Neden:** `server.js`'de `!hasSlot` bloğu senkron backend çağrısı yapıyordu; backend kapalıyken 503 döndürüyor, App.svelte'de `completed=true` için try/catch yoktu → UI çöküyordu.

**Değişiklikler:**
1. **QR offline-first**: `server.js` `!hasSlot` → anında `503 kiosk_no_missing` (eski senkron backend fallback kaldırıldı). Sync-durum polling endpoint `GET /api/oturum/sync-durum/:key` eklendi. `api.js` `submitSession` artık `syncDurum` döner; `fetchSessionSyncStatus` eklendi. App.svelte `doSubmitSession`/`doSubmitConsult` hata yakalamaya alındı; result store'a `syncDurum` ve `idempotencyKey` eklendi. ResultScreen 3s/+8s sonra durum polllar; gönderilmemişse köşede koyu sarı ünlem ikonu gösterir.
2. **HAYIR butonu koyu gri**: QuestionScreen.svelte `.btn-hayir` scoped class → `#4B5563/#374151` gradient.
3. **Etken madde kutuları**: ResultScreen ana/destek/ek ayrımı kaldırıldı; tüm `recs` eşit beyaz kutu (`ingredient-box`) koyu kırmızı (`#7f1d1d`) zemin üzerinde gösterilir.
4. **Logo**: ResultScreen'deki `e-isa` metin logosu kaldırıldı; `<Logo height="40px" />` kullanıldı.
5. **AdPromo konumu**: `.ad-promo` `align-items: center → flex-end`, normal: `padding-bottom:20px`, large: `padding-bottom:48px`.

**Dosyalar:** `kiosk_edge/api-node/src/server.js`, `kiosk_edge/ui/src/lib/api.js`, `kiosk_edge/ui/src/App.svelte`, `kiosk_edge/ui/src/components/ResultScreen.svelte`, `kiosk_edge/ui/src/components/QuestionScreen.svelte`, `kiosk_edge/ui/src/components/AdPromo.svelte`
**Build:** `vite build` ✓ 142 modül, 0 hata.

---

## 2026-08-09


### [Web Panels + Backend] 4 Issue Fix — video aktif medya, job worker, video thumbnail, yayın akışı

**Değişiklik:**
1. **CampaignWizard — active_media_url video desteği**: İşlem ekranı alt alan upload `accept="image/*"` → `accept="image/*,video/mp4,video/webm"`; preview `<img>` → `isVideoUrl()` yardımcısı ile koşullu video/image gösterimi. Backend `Creative.active_media_url` kısıtsız URLField olduğundan değişiklik gerekmedi.
2. **run_scheduler.py — drain_queue job eklendi**: `drain_queue` APScheduler'a `IntervalTrigger(seconds=30)` ile eklendi. Bu eksiklik nedeniyle `invalidation_service` tarafından üretilen PENDING GenerationJob'lar hiç işlenmiyordu; kampanyalar kioskına ulaşmıyordu. Tek gerçek kod kaynağı: scheduler servisi `drain_queue`'yu kaydetmiyordu.
3. **CampaignWizard — video thumbnail**: Kampanya listesinde `<img :src="thumbOf(c)">` → `isVideoUrl()` kontrolüyle video kartı (ikon+etiket) gösterimi; video için `<img>` render edilmez.
4. **KioskActivities — Yayın Akışı sekmesi**: Yeni "Yayın Akışı" tab; kiosk+tarih seçimi; saat-mutlak offset ile "şu an yayında" hesabı; kiosk online/geride/offline uyarısı; MediaView-uyumlu video/image preview; tüm günün saatlik playlist kartları. Backend: `GET /api/campaigns/v2/playlists/day-stream/` (read-only, N+1 yok, `select_related/prefetch_related`).

**Dosyalar:**
- `web_panels/src/views/admin/CampaignWizard.vue` — video accept, isVideoUrl helper, video-thumb-placeholder CSS
- `web_panels/src/views/admin/KioskActivities.vue` — Yayın Akışı tab + state + template + scoped CSS
- `web_panels/src/services/dooh.js` — `getKioskDayStream()` eklendi
- `backend/apps/campaigns/management/commands/run_scheduler.py` — drain_queue job kaydı
- `backend/apps/campaigns/views_v2.py` — `KioskDayStreamView` eklendi (read-only)
- `backend/apps/campaigns/urls.py` — day-stream URL kaydı
- `backend/apps/campaigns/tests/test_issue_fixes_2026_08.py` — 12 yeni test (T01–T10)

**DB migration/schema:** YOK — tüm değişiklikler mevcut şema üzerinde.
**Testler:** 285 passed, 7 skipped (backend); web_panels build ✓ (7.30s).
**Deployment notu:** `scheduler` servisi yeniden başlatılmalıdır: `python manage.py run_scheduler`. Yeni `drain_queue` job kayıtlandıktan sonra PENDING job'lar 30 saniye içinde işlenir.

### [Backend + Web Panels] Yayın Akışı desired/applied düzeltmesi (E2E doğrulama sonrası)

**Değişiklik:** Gerçek E2E + browser doğrulaması sırasında day-stream endpoint'in `desired_version`'ı `KioskDesiredBundle`'dan okuduğu (her zaman boş — Faz 5 stub) tespit edildi. Sistemin canonical alanlarına çevrildi: `desired_version = Kiosk.last_playlist_version`, `applied_version = Kiosk.applied_playlist_version` (+ `applied_horizon_end`, `playlist_applied_at`). Frontend `kioskSyncStatus` custom mantık yerine ortak `calcKioskRolloutStatus` composable'ını kullanır (offline/behind/ack_pending/no_publish/synced). Böylece Control Center ile Yayın Akışı aynı rollout sözleşmesini paylaşır.

**Dosyalar:**
- `backend/apps/campaigns/views_v2.py` — `KioskDayStreamView` canonical desired/applied (KioskDesiredBundle kaldırıldı)
- `web_panels/src/views/admin/KioskActivities.vue` — `calcKioskRolloutStatus` reuse + desired/applied gösterim
- `backend/apps/campaigns/tests/test_issue_fixes_2026_08.py` — 16 test (T01–T10 + T06b param-required, T06c canonical desired/applied, T06d N+1 max-query, T06e offset 0..3599)

**Gerçek E2E doğrulaması (local SQLite + run_scheduler):** Campaign create → 6 PENDING job → drain_queue (30sn interval) → RUNNING → DONE → 144 Playlist / 1440 PlaylistItem → `last_playlist_version` (desired) 6→9. attempt_count=1 (çift işleme yok), 0 FAILED. Browser: 13 senaryo screenshot (`docs/qa/screenshots-2026-08-09/`), console'da kırık image/taşma yok, video hiçbir yerde `<img src="*.mp4">` değil, liste kartlarında autoplay yok.

**DB migration/schema:** YOK.

---

## 2026-08-06

### [Backend+Kiosk+WebPanel] İçerik Yönetimi paneli, Danışma sıralama, Overflow göstergeleri

**Değişiklik:**
- `ContentManagement.vue` (yeni): İçerik Yönetimi admin sayfası; HouseAd CRUD, kiosk overlay önizleme, image-only upload (`media_kind=image`). Menü/başlık/form/bildirimde "HouseAd" terimi yok.
- `dooh.js`: `updateHouseAd`, `deleteHouseAd` eklendi; `uploadMedia(file, mediaKind)` imzası genişletildi.
- `router/index.js` + `AdminLayout.vue`: `/admin/content-management` route + menü kaydı "İçerik Yönetimi".
- `Danisma.sira`: `PositiveSmallIntegerField(default=100)` eklendi; `ordering = ("sira","ad")`; migration `0012_add_danisma_sira`.
- `DanismaSerializer` + `DanismaSyncSerializer`: `sira` alanı eklendi.
- `db.js`: idempotent `ALTER TABLE danisma_kategorileri ADD COLUMN sira` (SCHEMA_VERSION=14 sabit — DB reset yok).
- `scheduler.js` `upsertDanismaKategori()`: `sira ?? 100` eklendi.
- `ConsultScreen.svelte`: `_bySira` sıralaması; alt kategoriler de sıralı; overflow göstergeleri (gradient, rozet, pozisyon çubuğu, ResizeObserver, onDestroy cleanup).
- `DanismaYonetimi.vue`: `sira` form alanı eklendi.
- `CategoryScreen.svelte`: overflow göstergeleri (aynı mantık); `onMount`/`onDestroy` cleanup; alt-kategori gezinmesinde scroll sıfırlama.

**Dosyalar:** `web_panels/src/views/admin/ContentManagement.vue` (yeni), `dooh.js`, `router/index.js`, `AdminLayout.vue`, `DanismaYonetimi.vue`; `backend/apps/products/models.py`, `serializers.py`, `migrations/0012`; `kiosk_edge/api-node/src/{db,scheduler}.js`; `kiosk_edge/ui/src/components/{ConsultScreen,CategoryScreen}.svelte`
**Testler:** Backend 513 passed; kiosk UI build ✓ (854ms); web_panels build ✓ (5.78s)

---

### [Backend+Kiosk UI] HouseAd image-only, IdleScreen paid/HouseAd ayrımı, Soru geri dönüşü, Başka Şikayet Seç

**Değişiklik:**
- `MediaUploadView`: `media_kind=image` parametresiyle image-only mod; `IMAGE_ONLY_TYPES={jpeg,png,webp}`; magic-byte sniff (JPEG/PNG/WebP imza doğrulaması); creative upload'u bozulmadı.
- `HouseAdSerializer.validate_media_url`: video uzantılarını reddeden ikinci savunma katmanı.
- `AdStrip.svelte`: `asset_type === 'creative'` filtresi — house_ad öğeleri işlem ekranında artık gösterilmiyor.
- `IdleScreen.svelte`: `$playlistItems.asset_type` metadata korunarak paid/house_ad/fallback üç mod. Recursive `setTimeout` + genToken video yarış kilidi. `ROTATE_MS` sabit kaldırıldı; per-item `duration_seconds` kullanılıyor. AdPromo hiçbir modda tam ekran arka plan değil.
- `AdPromo.svelte`: `floatCard` prop — `position:relative; background:transparent` ile container konumlandırması.
- `QuestionScreen.svelte`: geri butonu (`currentQIndex > 0`), seçili cevap vurgusu (`btn-answer-selected`), `currentAnswers` store import.
- `App.svelte`: `goBackQuestion()` — cevaplar korunur, sadece farklı cevap verilince sonrakiler temizlenir. `startNewComplaint()` — yaş/cinsiyet korur, kategori+QR temizler, yeni sessionId.
- `ResultScreen.svelte`: "Başka Bir Şikayet Seç" butonu → `dispatch('newComplaint')`.
- Yeni test: `apps/campaigns/tests/test_house_ad_validation.py` (13 test, hepsi geçti).

**Dosyalar:** `backend/apps/campaigns/views.py`, `serializers.py`, `tests/test_house_ad_validation.py`; `kiosk_edge/ui/src/components/{AdStrip,IdleScreen,AdPromo,QuestionScreen,ResultScreen}.svelte`; `kiosk_edge/ui/src/App.svelte`
**Testler:** Backend 513 passed; kiosk UI build ✓ (843ms)

---

### [Backend+Edge+WebPanel] QR/Session akışı offline-first hale getirildi

**Değişiklik:**
- `Kiosk.eczane_kiosk_no` (1-31, eczane-unique) eklendi; bootstrap response'a dahil edildi; mevcut kiosklar backfill edildi (pharmacies migration 0010).
- `OturumLogu.eczane` FK (nullable, SET_NULL) eklendi; `qr_kodu` nullable + max_length=9 yapıldı; global unique kaldırılıp eczane-scoped conditional unique eklendi (analytics migration 0012).
- `ingest_session_items()`: kiosk'tan gelen 9-char Crockford QR doğrulanıp kabul edilir; eski kiosklarda 8-char backend üretimi fallback olarak korunur; tamamlandi=False → qr_kodu=null.
- Eczacı QR sorgusu: önce `eczane_id` scope'lanır, başka eczane kodu 403 yerine 404 döner.
- Edge `qrGen.js`: Crockford Base32 QR üretimi, mantıksal sayaç (monoton), checksum.
- Edge `db.js` v14: `qr_counter` singleton tablosu eklendi.
- Edge `server.js`: tamamlanan oturum QR'ı yerelde üretilir (atomik txn), hemen döner; backend push `setImmediate` ile arka planda çalışır.
- Edge `provisioning.js`: `eczane_kiosk_no` bootstrap response'tan SQLite'a kaydedilir; `settings.eczaneKioskNo` olarak yayılır.
- `QrScan.vue`: 8 ve 9 karakter formatları kabul edilir; Crockford checksum doğrulama; başka eczane mesajı kaldırıldı.
- Hedefli testler: backend 155 passed, edge qrGen 43 passed; server.test.js pre-existing failure (scheduler.js encoding issue, bizim değil).

**Dosyalar:** backend/apps/pharmacies/models.py, migrations/0010; backend/apps/analytics/models.py, services.py, views.py, migrations/0012; backend/apps/kiosk_api/views.py; backend/apps/analytics/tests/test_qr_flow.py, test_session_normalization.py; kiosk_edge/api-node/src/{qrGen.js,db.js,server.js,provisioning.js}; kiosk_edge/api-node/tests/qrGen.test.js; web_panels/src/views/pharmacist/QrScan.vue
**Migration:** pharmacies/0010 (eczane_kiosk_no + backfill), analytics/0012 (eczane FK + qr nullable + constraint)

---

## 2026-08-01

### [Backend+Frontend] Eczacı kampanyası: il/ilçe hedefleme + duration validation + UI düzeltmeleri

**Değişiklik:**
- `PharmacyCampaign.target_iller` + `target_ilceler` M2M eklendi (migration 0024).
- `duration_seconds` default 15; serializer'da yalnız 15/30/60 kabul edilir (eski kayıt aynı değerle güncellenebilir).
- Feed OR mantığı: eczane, il veya ilçe eşleşmesi; hiç hedefi olmayan kampanya feed'e girmez.
- EisaLookup entegrasyonu düzeltildi: eczaneler `/api/pharmacies/` endpoint'inden yüklenir; il/ilçe/eczane seçimi v-model + watch ile çalışır.
- Grid thumbnail: 120×68px, `object-fit: contain`, sabit yükseklik.
- Duration: serbest input → 15/30/60 seçenekli select.
- Backend test sayısı: 19 geçti.

**Dosyalar:** backend/apps/campaigns/{models,serializers,views_v2}.py; migrations/0024; tests/test_pharmacy_campaign.py; web_panels/src/views/admin/PharmacyCampaigns.vue
**Build:** web_panels ✅ (2.45s)

---

## 2026-07-31

### [Backend+Kiosk+Frontend] Kiosk çift medya varyantı + Eczacı paneli kampanyaları

**Değişiklik:**
- `Creative.active_media_url` nullable alan eklendi (migration 0021); bekleme (portrait) ve alt alan (~7:5) ayrı görseller.
- `PharmacyCampaign` modeli eklendi (migration 0022); kiosk sisteminden bağımsız eczacı paneli kampanyaları.
- `KioskCreativeSyncSerializer`, `KioskPlaylistItemSerializer` — `active_media_url` additive eklendi.
- api-node: `db.js` SCHEMA_VERSION 12; creatives kolonu; `scheduler.js` upsert; `mediaCache.js` `_active` suffix cache; `server.js` playlist/current LEFT JOIN ile `active_media_url`.
- `AdStrip.svelte`: `active_media_url` varsa cover, yoksa `media_url` + `object-fit: contain` (letterbox).
- Admin: CampaignWizard step 2 → iki upload alanı (Bekleme/İşlem ekranı); AdminLayout yeni menü.
- Yeni: `PharmacyCampaigns.vue` (admin), `PharmacistCampaignDisplay.vue` (eczacı şerit + 90s idle overlay).
- Feed endpoint: `GET /api/campaigns/v2/pharmacy-campaigns/feed/` — `request.user.eczane_id` ile güvenli filtreleme.

**Dosyalar:** backend/apps/campaigns/{models,serializers,views_v2,urls,migrations/0021-0022}.py; kiosk_edge/api-node/src/{db,scheduler,mediaCache,server}.js; kiosk_edge/ui/src/{components/AdStrip.svelte,app.css}; web_panels/src/{views/admin/{CampaignWizard,PharmacyCampaigns}.vue,components/pharmacist/PharmacistCampaignDisplay.vue,views/admin/AdminLayout.vue,router/index.js,styles.css}
**Testler:** 246 passed, 7 skipped (5 yeni PC-01..05 testi dahil)

---

## 2026-07-24

### [kiosk_edge] Tam ekran portré CSS — 100vw × 100vh

**Değişiklik:** `app.css` — `body` padding/centering kaldırıldı; `.kiosk` `width: 100vw; height: 100vh` yapıldı (`border-radius`, `box-shadow`, sabit 794×1123 px kaldırıldı). 1080×1920 ve 1440×2560 her ikisi de 9:16 oran olduğundan aynı kural ikisini de tam doldurur. Önceki media query (min-width: 1100px) supersede edildiği için kaldırıldı.
**Dosyalar:** `kiosk_edge/ui/src/app.css`
**Etki:** UI build ✅ (765ms). Scrollbar yok, taşma yok.

**Değişiklik:**
- `printer.js`: Fiş içeriği yenilendi — "e-ISA" (bold) + "Saglikli gunler diler." + QR + QR metin değeri. Kategori/kod/açıklama satırları kaldırıldı. ESC/POS QR modül boyutu 6 → 16 (~42 mm @ 203 DPI, ESC/POS maks.).
- `app.css`: `@media (min-width: 1100px) and (orientation: portrait)` kuralı eklendi. 1440 × 2560 ekranda `.kiosk` viewport genişliğini doldurur (794/1123 en-boy oranını koruyarak); 1080 × 1920 görünümü değişmez.

**Dosyalar:** `kiosk_edge/api-node/src/printer.js`, `kiosk_edge/ui/src/app.css`
**Etki:** Kiosk UI build ✅ (1.25s), printer.js syntax ✅. QR formatı/session akışı dokunulmadı.

---

## 2026-08-19

### [Backend/Web/Kiosk/Docs] Oturum status, zorunlu satış, dönem grafikleri ve cihaz taşıma

**Backend:** `OturumLogu.status` (0/1/2/3) authoritative satış durumu ve `result_at` eklendi; legacy `sold` migration/response uyumluluğu korundu. Tarihsel eczane scope'u liste/satış/dashboard'a yayıldı. Idempotent `mark-reviewed`, katalog doğrulamalı merkezi satış service'i ve İstanbul zamanlı 4 dashboard serisi eklendi. `KioskEczaneAtama` geçmişi, partial unique açık atama ve transaction'lı SuperAdmin transfer action eklendi; mevcut campaign invalidation receiver'ı yeniden kullanıldı. Nöbet tabloları audit alanları kazandı, geçmiş gün mutation'ı engellendi.

**Web/Kiosk:** Eczacı QR/list detail modalı sonuçlandırılana kadar kapatılamaz; yeni QR guard ve kullanıcı+eczane sessionStorage restore vardır. Mevcut katalogdan aramalı çoklu diğer etken madde seçimi, ortak 2×2 dönem grafikleri, cihaz taşıma/geçmiş UI'si, üst-orta global toast ve yalnız Yeni Eczane için big modal eklendi. Evet `#0F8F8A`, Hayır e-isa kırmızısı olarak panel/kiosk tokenlarına taşındı.

**Migrationlar:** `analytics.0018_oturum_satis_status`, `pharmacies.0011_kiosk_eczane_atama`, `announcements.0002_duty_audit_fields`.

**Doğrulama:** Yeni backend testleri 8/8; backend tam paket 661 passed, 7 skipped, SQLite'ta PostgreSQL eşzamanlı ACK testine ait 1 bağımsız failure. Web Vitest 60/60, kiosk Vitest 56/56; web ve kiosk production build başarılı; Django check ve migration drift temiz. Browser/screenshot aracı bulunmadığından gerçek viewport görsel testi yapılmadı.

## 2026-08-18

### [Frontend+Backend+Docs] Genel Duyuru ve Sabit Nöbet Uyarıları

**Değişiklik:** `apps.announcements` ile genel recurrence/hedefleme, occurrence bazlı read, ay bazlı nöbet günleri ve iki sabit `system_key` uyarısı eklendi. Admin sistem kayıtlarında yalnız başlık/mesaj/aksiyon etiketi/seviye/aktiflik değiştirebilir; kayıtlar silinemez.
**Frontend:** Admin duyuru yönetimi, eczacı genel duyuruları, ortak layout altında nöbet popup'ı ve hedef aylı nöbet takvimi eklendi; mevcut hassas-session inbox akışı ayrık tutuldu.
**Dosyalar:** `backend/apps/announcements/*`, backend settings/urls, web router/layout ve yeni announcement/duty Vue bileşenleri; `docs/ai/{00,01,02,05,06,07,99}*.md`.
**Etki:** Yeni `/api/announcements/*` contract'ı ve `announcements.0001_initial` migration'ı. Generic condition builder/SQL yok; nöbet koşulları backend kodunda sabit.
**Doğrulama:** Duyuru testleri 10/10, Django check ve migration drift temiz, Vue production build başarılı. Tam backend: 454 passed/7 skipped; duyurudan bağımsız mevcut bir PG concurrency testi SQLite kilidi/fingerprint nedeniyle başarısız. Vitest runner bu ortamda çıktı vermeden timeout oldu.

## 2026-07-23

### [Frontend+Backend] Faz 6+7 Nihai Kapanış Denetimi (Tamamlandı)

**Root cause düzeltmeleri:**
- Login 500: settings_dev_sqlite.py DEFAULT_THROTTLE_RATES={} kaldırıldı; Local dev PG'ye migration uygulandı
- PlaylistEditor gerçek read-only: Tüm mutation fonk. + importlar KALDIRILDI (298 satırlık temiz bileşen)
- CampaignSerializer: deprecated alanlar ANY değer → 400 (True/False/null/0)
- CampaignWizard: target_days state + toggleDay() + DAYS_OF_WEEK KALDIRILDI
- is_enabled/is_active_mode/should_publish helper metodları KALDIRILDI (PlacementEngineV2'den)
- test_c19: hardcoded tarih bağımlılığı düzeltildi (pre-existing flaky test)

**Migration veri etkisi (0020, kanıtlandı):**
- Test PG 0019→0020: is_guaranteed/impression_goal/frequency_cap_per_hour DROP edildi
- SQL: ALTER TABLE dooh_campaigns DROP COLUMN ... CASCADE (3 kolon)
- Kayıt korundu, yalnız kolon silindi. Tüm değerler nullable/default'du.

**Docs güncellendi:**
- 00-AI-INDEX.md, 01-backend.md, 05-cross-project-flows.md, 06-db-and-api-contracts.md

**Test Sonuçları:**
- Backend SQLite: 436 passed | PostgreSQL: 16 passed | Frontend: 57 passed
- Build: exit 0 | git diff --check: exit 0

**Browser (gerçek auth, gerçek PostgreSQL):**
- Login 200 ✓ | Dashboard gerçek verilerle ✓ | CampaignWizard ✓ | DoohControlCenter ✓
- PlaylistEditor salt-okunur ✓ (1 kiosk) | pharmacist → /login redirect ✓
- Backend RBAC: IsSuperAdmin permission → 403 kanıtlandı
- Screenshots: Desktop ✓ | Narrow (375px) ✓

**Production'a hiçbir şey uygulanmadı.**




### [DOOH] Faz 4/5 Kapanış Denetimi — Kritik Düzeltmeler (TAMAMLANDI)

**Düzeltilen açıklar:**
1. **Fingerprint source-of-truth**: `Kiosk.last_v2_fingerprints` stale metadata → gerçek `PlaylistItem` kayıtlarından hesaplama (`ActivationService._compute_playlist_fingerprint()`). Manuel/V1 mutasyon sonrası stale fingerprint "aynı" sayılmaz.
2. **Fingerprint check inside lock**: Önceki `process_job` lock-dışı fingerprint kontrolü yapıyordu → concurrent workers iki kez publish edebilirdi. Düzeltme: `_persist_plan(check_fingerprint=True)` fingerprint'i row-lock altında DB'den hesaplar.
3. **Pending ACK dayanıklılığı**: Max retry → ACK siliniyordu. Düzeltme: capped backoff (30s→1800s), hiçbir zaman silinmez. 409 FUTURE_REJECTED → resync flag + ACK korunur. Conditional clear (`clearPendingAckIfMatches`) eski ACK cevabının yeni pending'i silmesini önler.
4. **Kiosk eczane değişimi**: pre_save ile eski eczane_id capture → post_save'de eski+yeni kapsam invalidation.
5. **Eczane il/ilçe/aktiflik sinyali**: Yeni signal (Eczane post_save) → eczanedeki kiosklar × horizon invalidation.

**Test Sonuçları:**
- SQLite: 430 passed, 0 failed, 0 skipped (exit 0)
- PostgreSQL: 16 passed, 0 failed, 0 skipped (exit 0)
- Node.js: 96 passed, 0 failed (exit 0)

---

### [DOOH] Faz 3 — Simulation / Activation / Reservation (TAMAMLANDI)

**Değişiklik:**
- `activation_service.py` (yeni): `ActivationService.simulate()` (read-only) + `ActivationService.activate()` (atomic, all-or-nothing GUARANTEED, BEST_EFFORT, CAMPAIGN_TOTAL global invariant)
- `views_v2.py`: `CampaignViewSet.simulate` (POST .../simulate/) + `CampaignViewSet.activate` (POST .../activate/) action'ları eklendi
- `serializers.py`: `SimulationResultSerializer`, `ActivationResultSerializer`, `KioskDaySimResultSerializer` eklendi
- `placement_engine_v2.py`: `is_active_mode()` eklendi, `is_enabled()` shadow+active, `should_publish()` active mode
- `settings.py`: `DOOH_ENGINE_V2` comment güncellendi (off/shadow/active)
- `scheduler.py`: trailing whitespace düzeltildi, shadow+active comment güncellendi
- `tests/test_faz3_simulation_activation.py` (yeni): 21 test (FA-01..FA-16)
- `tests/integration/test_faz3_concurrency.py` (yeni): FA-10, FA-11 PostgreSQL race testleri

**Test Sonuçları:** 371 passed, 7 skipped, 0 failed (Exit: 0)
**git diff --check:** Exit 0 (no trailing whitespace)

---

### [DOOH] Faz 2 — PlacementEngine V2 Shadow Mode (TAMAMLANDI)

**Değişiklik:**
- `placement_engine_v2.py` (yeni): DeliveryRule dispatch, HourGrid overlap, follows chain, house_ad filler, SHA-256 fingerprint
- `quota_service.py` (yeni): `GlobalQuotaService.reserve_for_kiosk_day()` + `initialize_allocation()` (parent row locking)
- `follows_service.py` (yeni): `set_campaign_follows()` service, `_targets_overlap()` ile ALL-scope sentinel fix
- `scheduler.py`: V2 shadow mode entegrasyonu (V1 authoritative, V2 loglar)
- Migration 0015-0018: object_key, Faz1 schema, quota constraints, follows unique
- `tests/test_placement_engine_v2.py` (yeni): 13 test (tümü geçti)
- `tests/integration/test_concurrency_postgresql.py` (yeni): 7 PostgreSQL concurrency test

**Bug Düzeltmeleri:**
- `follows_service._targets_overlap`: ALL/None scope için empty kiosk set false-positive hatası → `_ALL_SCOPE` sentinel ile düzeltildi
- `analytics/views.py`: `uow.update()` çağrısında çift audit field (`guncelleyen` + `guncelleyen_id`) → PostgreSQL `multiple assignments to same column` → fazla alanlar kaldırıldı
- `test_golden_master.py` + `test_persistent_media.py`: `timezone.now() - 1 day` → öğleden sonra scheduler noon UTC filtresini geçemiyordu → `_today_start()` sabit TODAY bazlı helper ile düzeltildi
- `tests/conftest.py` (yeni): `disable_campaign_signals` autouse fixture → SQLite table lock sorunu çözüldü

**Local DB Doğrulama:**
- `python manage.py migrate`: tüm migration'lar uygulandı (0001-0018)
- `python manage.py check`: 0 issue
- `python manage.py makemigrations --check`: No changes detected
- PostgreSQL constraint: `placed > quota` → IntegrityError doğrulandı

**Test Sonuçları (Faz 2):** 348 passed, 7 skipped, 0 failed

---

### [DOOH] Faz 2 Başlangıç — PlacementEngine V2 Shadow Mode

**Kapsam:**
PlacementEngine V2 shadow mode. V1 scheduler korunur, değiştirilmez. V2 paralel çalışır (shadow), diff metrikleri toplar. Production cutover yok.

**Önkoşullar (DOOH_ENGINE_V2=shadow açılmadan):**
- PostgreSQL integration testi: select_for_update/MVCC concurrency (A→B race)
- A→B target intersection validation testi (real DB)
- staging migration 0015–0018 apply + smoke test
- files.eisa.com.tr GET/HEAD gerçek bucket policy testi

**Yapılacak:**
- placement_engine_v2.py: DeliveryRule dispatch, target_scope resolver, follows chain, slot allocation
- scheduler.py: shadow mode orchestration (V1 üretir, V2 loglar)
- ShadowRunMetric model + report_shadow_diff management command
- PostgreSQL docker-compose + concurrency testleri
- docs/ai/09-placement-engine-v2.md

### [DOOH] Faz 1 Final Denetimi — Koşullu Kabul

**Durum:** Kod tarafı tamamlandı. Faz 0.5 operasyonel rollout ve PostgreSQL concurrency testleri devam ediyor.

**Değişiklikler:**
- `CampaignSerializer.validate()`: `target_scope` yeni CREATE'te zorunlu (ALL|RULES). `is_guaranteed=True` API gönderilince 400 (açık hata). `follows` read-only (yalnız `set_campaign_follows()` servisi).
- `follows_service.py`: Tarih araligı kesişimi + yayın saati kesişimi (DeliveryRule.active_hours) + CANCELLED kontrol eklendi. Unique predecessor explicit check (select_for_update içinde). Dosya ASCII unicode temizlendi.
- `Campaign` model: `dooh_campaign_follows_unique_predecessor` partial unique index → migration 0018.
- `test_dooh_v2.py::test_admin_create_campaign_201`: target_scope="ALL" eklendi.
- `test_closure.py::test_c07`: `is_guaranteed=True → 400` beklentisine güncellendi.
- `test_golden_master.py::test_gm_kiosk_ping_returns_playlist_version`: TODAY hardcoded → `timezone.now().date()` (tarih-bağımsız).
- Vue `api.test.js login()`: Pre-existing hata düzeltildi; `access/refresh` yerine `role/userId` beklentisine.
- Yeni test dosyası: `test_faz1_final.py` (target_scope, A→B intersection, CAMPAIGN_TOTAL quota, canonical guarantee testleri).
- Yeni Vue test: `dooh_media_flow.test.js` (uploadMedia response → form state → create payload canonical akış).
- Docs güncellendi: 01-backend, 02-web-panels, 03-kiosk-edge, 05-cross-project-flows, 06-db-and-api-contracts, 08-dooh-advertising, implementation-plan.

**Dosyalar:** `campaigns/serializers.py`, `campaigns/services/follows_service.py`, `campaigns/models.py`, `migrations/0018_*.py`, `tests/test_dooh_v2.py`, `tests/test_closure.py`, `tests/test_golden_master.py`, `tests/test_faz1_final.py`, `web_panels/src/services/__tests__/dooh_media_flow.test.js`, `web_panels/src/services/__tests__/api.test.js`, doc dosyaları.
**Testler:** 143/143 backend (exit 0), 80/80 kiosk edge, 14/14 Vue (exit 0), Vue build ✓.
**Migrations:** 0017 (KioskDayQuota constraints), 0018 (follows unique predecessor). Forward/backward ✓.
**SQLite concurrency sınırı:** Belgelenmiş (test_ab06); gerçek MVCC testi PostgreSQL integration gerektirir.

### [DOOH] Faz 0.5 + Faz 1 Kapanış Denetimi

**Faz 0.5 kapanış:**
- `StorageService.public_url()` basitleştirildi: S3_PUBLIC_BASE_URL bucket dahil, sadece `base + "/" + key`. Boşsa ImproperlyConfigured.
- `S3_PUBLIC_BASE_URL` sözleşmesi: `https://files.eisa.com.tr/eisa-files` (bucket dahil) → `media_url = S3_PUBLIC_BASE_URL + "/" + object_key`. Bucket otomatik ekleme kaldırıldı.
- `_derive_object_key_from_url` basitleştirildi: S3_PUBLIC_BASE_URL prefix'ini strip eder; path traversal koruması.
- test_settings.py: `S3_PUBLIC_BASE_URL = "http://localhost:9000/dev"` (bucket dahil).
- `CampaignWizard.vue`: `uploadMedia` response'tan `media_url`, `object_key`, `checksum` canonical olarak alınır; `createCreative` bu 3 alanı gönderir; `data.url` yalnız legacy fallback.

**Faz 1 kapanış:**
- `HouseAdSerializer`: `is_grid_compliant` + `validate_duration_seconds` grid validasyonu eklendi.
- `CreativeSerializer.validate_duration_seconds()`: grid validasyonu (yeni/değişen → 15/30/45/60 zorunlu; legacy aynı değer korunur).
- `CampaignSerializer.is_guaranteed`: `read_only_fields`'e eklendi (canonical kaynak: DeliveryRule.guarantee_mode).
- `DeliveryRuleSerializer.validate()`: `LEGACY_PER_LOOP` yazılmasını reddeder.
- `KioskDayQuota`: `placed>=0`, `quota>=0`, `placed<=quota` CheckConstraint eklendi → migration 0017.
- Yeni `apps/campaigns/services/follows_service.py`: `set_campaign_follows()` — transaction.atomic + select_for_update; self-link, zincir derinliği, döngü koruması.
- Yeni `tests/test_closure.py`: 26 kapanış testi (C01–C19).

**Migration:** 0017 (KioskDayQuota constraints). Forward ✓, backward ✓, check ✓.
**Testler:** 123/123 backend, 80/80 kiosk edge, Vue build ✓.

### [DOOH] Faz 1 — Additive Domain Schema + Legacy Compatibility

**Değişiklik:**
- `Campaign`: `DRAFT`/`CANCELLED` status; `target_scope` (ALL|RULES|null); `follows` FK (self, null); `effective_state` property (SCHEDULED türetilmiş); `is_guaranteed`/`impression_goal`/`frequency_cap_per_hour` deprecate notu eklendi.
- `CampaignTarget`: `KIOSK` target type; `kiosk` FK; `mode` (INCLUDE|EXCLUDE|null).
- `Creative`: `weight` (default=1); `is_grid_compliant` property.
- `HouseAd`: `is_grid_compliant` property.
- `PlayLog`: `play_event_id` (UUID, null=True — K5 adım A).
- Yeni modeller: `DeliveryRule` (delivery_type/count/window/active_hours/guarantee_mode), `PlanningRun`, `CampaignTotalAllocation`, `KioskDayQuota`, `KioskDesiredBundle`.
- Migration 0016 (additive, reversible). Forward/backward ✓. `makemigrations --check` ✓.
- Yeni management command: `report_grid_noncompliant_media`.
- Serializer güncellemeleri: `CreativeSerializer`+weight+is_grid_compliant, `CampaignTargetSerializer`+kiosk+mode, `CampaignSerializer`+effective_state+target_scope+follows, yeni `DeliveryRuleSerializer`.

**Dosyalar:** `campaigns/models.py`, `campaigns/serializers.py`, `campaigns/migrations/0016_faz1_additive_schema.py`, `management/commands/report_grid_noncompliant_media.py`, `campaigns/tests/test_faz1_schema.py`.
**Testler:** 97/97 (44 yeni Faz 1 testi; tüm golden-master ve Faz 0.5 testleri yeşil).
**Not:** ScheduleRule dual-read korunuyor; DeliveryRule eklendi. `DOOH_DELIVERY_RULE_MODEL` feature flag Faz 2'de; Faz 1'de model şeması yeterli.

---

## 2026-07-21

### [DOOH] Faz 0.5 — Kalıcı Medya URL (v2 — tamamlandi)

**Değişiklik:**
- **URL format dogrulandi:** Production `S3_ENDPOINT=files.eisa.com.tr` + `S3_BUCKET=eisa-files` + `S3_FORCE_PATH_STYLE=True` → kalici URL = `https://files.eisa.com.tr/eisa-files/<object_key>`. Bucket adi path'e dahil.
- `StorageService`: `upload_file_with_checksum()` (64KB chunk streaming SHA-256, iki geçis), `public_url()` (bucket-aware, path-style).
- `MediaUploadView`: `DOOH_PERSISTENT_MEDIA_URL` feature flag (False=legacy, True=kalici). Response: `{object_key, media_url, checksum, url, filename, object_name}`.
- `Creative` + `HouseAd`: `object_key (null=True, blank=True)` — K5 additive. Migration 0015.
- `_derive_object_key_from_url`: bucket-aware, path traversal korumasi, presigned/yabanci host reddeder.
- `backfill_media_object_keys`: guvenlik sertlestirme (host whitelist, bucket/path dogrulama, path traversal, URL decode, --apply=HEAD zorunlu, --skip-head-check-DANGEROUS).
- `settings.py`: `S3_PUBLIC_BASE_URL` (opsiyonel override), `DOOH_PERSISTENT_MEDIA_URL` flag.

**Dosyalar:** `storage_service.py`, `campaigns/views.py`, `campaigns/models.py`, `campaigns/serializers.py`, `migrations/0015_*.py`, `management/commands/backfill_media_object_keys.py`, `settings.py`, `test_settings.py`, `web_panels/src/services/dooh.js`. Kiosk: `tests/mediaCache.test.js` (8 yeni test, KC-01..KC-08).
**Testler:** Backend 53/53 (test_persistent_media.py 19 yeni: M01..M15 + 2 integrasyon + 2 golden kontrol), kiosk edge 80/80.
**Etki:** `media_url` kalici URL → kiosk `source_url` stabil → gereksiz yeniden-indirme ortadan kalkar. DOOH_PERSISTENT_MEDIA_URL=True ile aktif; False (varsayilan) legacy rollback.

**Değişiklik:**
- `StorageService`: `upload_file_with_checksum()` (SHA-256 stream + döner `(object_key, checksum)`) ve `public_url()` (stabil `S3_PUBLIC_BASE_URL/object_key`) eklendi.
- `MediaUploadView`: Presigned yerine kalıcı URL döner. Response: `{object_key, media_url, checksum, url, filename, object_name}`. `url`/`object_name` geriye-uyumlu alias.
- `Creative` + `HouseAd` modeline `object_key` (CharField, blank, additive migration).
- `CreativeSerializer` + `HouseAdSerializer`: `object_key` alanı eklendi; `media_url` S3_PUBLIC_BASE_URL ile başlıyorsa `object_key` otomatik türetilir.
- `settings.py`: `S3_PUBLIC_BASE_URL` (prod'da zorunlu, boşsa `ImproperlyConfigured`). `test_settings.py`: varsayılan set edildi.
- Yeni migration: `0015_creative_object_key_housead_object_key.py`.
- Yeni management command: `backfill_media_object_keys` (dry-run varsayılan, --apply, --head-check).

**Dosyalar:** `storage_service.py`, `campaigns/views.py`, `campaigns/models.py`, `campaigns/serializers.py`, `campaigns/migrations/0015_*.py`, `management/commands/backfill_media_object_keys.py`, `settings.py`, `test_settings.py`, `web_panels/src/services/dooh.js`.
**Testler:** `test_persistent_media.py` (14 yeni test: M01–M12 + 2 entegrasyon). 48/48 yeşil.
**Etki:** Kiosk playlist contract `media_url` alanı korunur; değeri kalıcı `https://files.eisa.com.tr/...` URL'si. `mediaCache.js` `source_url` stabileşince gereksiz yeniden-indirme çözülür.

---

### [DOOH] Faz 0 — Golden-Master / Characterization Testleri

### [Backend] — OturumCevap/OturumOnerilenEtkenMadde Veri Kaybı Düzeltmesi

**Doğrulanan sorunlar (canlı shell ile kanıtlandı):**
1. **OturumOnerilenEtkenMadde merge hatası (KRİTİK):** `get_or_create(etken_madde=None, defaults={"snapshot": name})` — FK null iken ikinci ve sonraki string malzeme adları birinci kaydın `defaults`'ını güncellemek yerine onu GET ediyordu. `["Melatonin","Valerian","B12"]` → 3 beklenen kayıt yerine 1 kaydediliyordu. Kiosk recommendation engine string isimler döndürdüğü için her SIKAYET session'ında veri kaybı oluşuyordu.
2. **`cevap_metni_snapshot` format sorunu:** Binary "Y"/"N" değerleri için `cevap_metni_snapshot = "Y"` kaydediliyordu; insan-okunur "Evet"/"Hayır" yerine. `cevap_degeri_snapshot` zaten raw "Y"/"N" değerini saklıyor.

**Düzeltmeler (`backend/apps/analytics/services.py` `_create_child_records`):**
- `OturumOnerilenEtkenMadde`: FK mevcut ise `get_or_create(etken_madde=em)`; FK null ise `get_or_create(etken_madde=None, etken_madde_adi_snapshot=name)` — snapshot isim lookup'a dahil edildi, merge engellendi.
- `cevap_metni_snapshot`: `{"Y": "Evet", "N": "Hayır"}` eşleşmesi ile insan-okunur değer saklanır.

**Değişmeyen davranışlar:**
- OturumCevap: SIKAYET'te soru FK her zaman non-null (raise ile korunuyor) → merge riski yok. ✓
- QR sorgu (`get_cevap_detaylari`): JSON backup `obj.cevaplar`'dan okur → `_answer_text_from_value("Y") = "Evet"` zaten doğru. ✓
- `onerilen_etken_madde_detaylari` QR görünümü: `obj.onerilen_etken_maddeler` JSON'dan okur → tüm adlar görünür. ✓

**Soru 6 (Gerçek Cevap ID'leri):** Daha doğru olur; gereklilikler: kiosk sorular API'ye cevaplar eklenmesi + QuestionScreen'in cevap_id dispatch etmesi + App.svelte'in cevap_id saklaması. Mevcut binary Y/N + snapshot yaklaşımı QR sorgusu için yeterli; analitik normalize tablolar için gelecekte eklenebilir.

**Test:** `apps/analytics/tests/test_session_normalization.py` — 33/33 (2 yeni test: `test_sikayet_multiple_binary_answers_no_merge`, `test_multiple_string_ingredients_all_saved` — regresyon koruma)
**Migration:** Yok (uygulama mantığı değişikliği; DB şeması değişmedi)

, Çift Gönderim Koruması, Scheduler Outbox Fix

**Kök Nedenler:**
1. **207 → 502 hatası:** `server.js` backend 207 döndürdüğünde item `errors[]`'a düşmüşse `resultItem` bulunamıyor, `backendQr = null` → 502.
2. **Çift gönderim:** `api.js` `retry: 1`; Node 502 dönünce `_request` retry yapıyor; her istekte Node yeni UUID üretiyor → 2 farklı Django isteği.
3. **Scheduler outbox bug:** `consumeBulkPushResponse` `body.accepted_keys` arıyordu; backend aslında `body.results[].idempotency_key` döndürüyor → outbox kayıtları hiçbir zaman "gönderildi" işaretlenmiyordu.

**Değişiklikler:**

**`kiosk_edge/api-node/src/server.js`:**
- `tamamlandi=true` akışı tamamen yeniden yazıldı: önce outbox'a kaydet (INSERT OR IGNORE), sonra backend'e gönder.
- 207 + `errors[]` → 422 (`backend_rejected`), outbox'ta kalır, `retry_count=99` (sonsuz retry engeli).
- Backend erişilemez → 503 (`backend_unreachable`/`backend_error`), outbox kaydı korunur; artık yanıltıcı 502 dönmez.
- Idempotent re-delivery: `gonderilme_tarihi` set + `qr_kodu` mevcut → backend çağrısı yapılmadan mevcut QR döner.
- `idempotency_anahtari` artık body'den alınır (UI'dan `sessionId` geliyor); yoksa yeni UUID üretilir.
- `tamamlandi=false` inline path: 207'de sadece `results[]`'dakiler gönderildi işaretlenir.
- Yapısal log eklendi: `event`, `upstream_status`, `kiosk_id`, `batch_size`, `accepted/duplicate/rejected_count`. Secret, QR, kişisel veri loglanmaz.

**`kiosk_edge/api-node/src/scheduler.js`:**
- `OUTBOX_MAX_RETRY = 10` sabiti eklendi.
- `oturum_outbox` query: `retry_count < OUTBOX_MAX_RETRY` filtresi eklendi (kalıcı hatalı kayıtlar atlanır).
- `consumeBulkPushResponse` tamamen yeniden yazıldı: `body.accepted_keys` → `body.results[].idempotency_key` (gerçek backend şeması). Kabul edilenler: `UPDATE gonderilme_tarihi`. Reddedilenler: `retry_count++`, `error_reason` kaydedilir.

**`kiosk_edge/api-node/src/db.js`:**
- `oturum_outbox` tablosuna `retry_count INTEGER NOT NULL DEFAULT 0` ve `error_reason TEXT` eklendi.
- Non-destructive migration: `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` (veri kaybı yok).

**`kiosk_edge/api-node/src/validators.js`:**
- `oturumGonderSchema`'ya `idempotency_anahtari` (optional UUID) eklendi.

**`kiosk_edge/ui/src/lib/api.js`:**
- `submitSession`: `sessionId` parametresi eklendi, `idempotency_anahtari` body'ye dahil edildi.
- `retry: 1` → `retry: 0` (idempotency outbox garantisi; çift kayıt riski ortadan kalktı).

**`kiosk_edge/ui/src/App.svelte`:**
- `sessionSubmitting` flag eklendi (aktif HTTP çağrısı sırasında çift tetikleme engeli).
- `selectConsult`: `sessionSubmitting` guard eklendi; hızlı çift dokunma koruması.
- `doSubmitSession` ve `doSubmitConsult`: `sessionId` (dış scope) `submitSession`'a geçirildi.
- `resetToIdle`: `sessionSubmitting = false` eklendi.

**`kiosk_edge/api-node/tests/server.test.js`:**
- 12 yeni senaryo testi eklendi (vi.mock ile requestWithRetry mock'landı).
- Senaryo 1-12: 200/existing/207-partial/401/403/500/erişilemez/idempotency/double-submit/kabul-işaret/red-işaret/secret log.

**`kiosk_edge/api-node/tests/helpers.js`:**
- `oturum_outbox` şemasına `retry_count`, `error_reason` eklendi.

**Test:** `npm test` → 72/72 geçti (5 test dosyası).
**Breaking:** Yok. `POST /api/oturum/gonder` response'a `sync_durum` alanı eklendi (geriye uyumlu).
**Migration:** Yok (SQLite non-destructive ALTER TABLE).



### [Backend + kiosk_edge + UI] — Device ID, Session Normalization, QR Unique, Consultation Type
**Değişiklik:** Kiosk persistent device identity, session analytics normalization, QR unique constraint, ve consultation session type eklendi.
**Backend:** `Kiosk.device_id` (nullable unique), `KioskProvisioningRequest.device_id` eklendi. Bootstrap HMAC artık `MAC + timestamp + device_id` içeriyor. Auth: `X-Kiosk-Device-ID` header'ı zorunlu (device_id set edildiyse). `OturumLogu`: `oturum_tipi` (SIKAYET/OZEL_DANISMANLIK), `danisma_kategorisi` FK, `kategori` nullable yapıldı, `qr_kodu` unique constraint. Yeni modeller: `OturumCevap` (oturum→soru→cevap normalize, snapshot), `OturumOnerilenEtkenMadde` (oturum→etken_madde normalize, snapshot). `analytics.services.generate_qr_candidate()` (IntegrityError retry + savepoint), `ingest_session_items()` oturum tipi validation (SIKAYET/OZEL_DANISMANLIK) + soru-cevap uyum kontrolü (strict 400) + child record creation + transaction. JSON fieldlar backup olarak korundu (expand/contract pattern). `/api/kiosk/v1/identity/enroll/` endpoint'i (tek-seferlik device_id bağlama). Migration: `0007_kiosk_device_id.py` (pharmacies), `0006_session_normalization.py`, `0007_qr_cleanup.py`, `0008_qr_unique_constraint.py` (analytics).
**Kiosk edge:** `provisioning.js`: `crypto.randomUUID()` ile `device_id` üretimi, SQLite `kiosk_meta`'ya kaydedildi. Bootstrap request'e `device_id` parametresi, HMAC'e dahil edildi. `getAuthHeaders()`: `X-Kiosk-Device-ID` header'ı eklendi. `server.js`: Session payload'a `oturum_tipi`, `kategori_slug` (nullable), `danisma_kategorisi_slug` (nullable) eklendi. `validators.js`: `oturumGonderSchema` güncellendu.
**UI:** `App.svelte` + `api.js`: `submitSession()` parametrelerine `oturumTipi`, `categorySlug`, `danismaKategorisiSlug` eklendi. Consultation flow `oturum_tipi=DANISMANLIK` olarak gönderiliyor.
**Test:** Backend 137/137 (analytics + pharmacies + kiosk_api), kiosk_edge 49/49, UI build başarılı. Duplicate QR fix script ile mevcut collision'lar temizlendi.
**Breaking:** Bootstrap HMAC artık device_id içeriyor (eski kiosk'lar legacy MAC-only ile çalışmaya devam eder ama yeni kiosk'lar device_id set olana kadar auth alamaz). QR unique constraint DB'de enforce edildi.

### [Backend + kiosk_edge] — Kiosk API Facade + Tek App Key Authentication (IoT/dual auth kaldırıldı)
**Değişiklik:** Kioskların Main API ile tüm operasyonel iletişimi tek namespace, tek auth ve tek merkezi client altında toplandı.
**Backend:** Yeni `apps/kiosk_api/` facade uygulaması (authentication/permissions/mixins/views/urls/serializers/tests). Tüm operasyonel kiosk endpoint'leri `/api/kiosk/v1/` altında ve **kiosk ID içermez** (`request.kiosk` auth context'inden gelir): `bootstrap, ping, sync, catalog, playlist, sessions, proof-of-play, diagnostics`. Facade domain mantığını kopyalamaz; mevcut model+serializer'ları ve yeni domain servislerini (`analytics.services.ingest_session_items`, `products.services.build_catalog_payload`, `analytics.log_ingest.ingest_kiosk_diagnostic_items`) yeniden kullanır.
**Auth:** Tek operasyonel sınıf `KioskAppKeyAuthentication` (`Authorization: AppKey <key>` + `X-Kiosk-MAC`); `request.kiosk` atar; **401** (App Key/MAC eksik/geçersiz) ve **403** (kiosk pasif/onaysız/eczanesiz) ayrımı + makine-okunur `code`. `KioskIoTTokenAuthentication`, `create_iot_token`, `verify_iot_token`, `_create_iot_token_for_kiosk`, `KIOSK_IOT_TOKEN_TTL_DAYS` **tamamen kaldırıldı** (fiziksel kolon yok → migration yok). Bootstrap artık `iot_token` yerine **`app_key`** döner (APPROVED/PENDING/REJECTED). Bootstrap `pharmacies` app'inden facade'e taşındı; eski `/api/pharmacies/kiosks/bootstrap/` ve `/api/kiosk/v1/{id}/...` route'ları kaldırıldı (hard cutover). Provisioning admin API'leri (`/api/pharmacies/kiosks/provisioning/*`) ve panel endpoint'leri değişmedi.
**Kiosk edge:** `provisioning.js` App Key'i bootstrap yanıtından SQLite `kiosk_meta`'ya yazar; `getAuthHeaders(db)` her istekte SQLite'tan `kiosk_app_key`+`kiosk_mac` okur (freeze/stale sorunu çözüldü, restart gerekmez); IoT/Bearer/Fleet üretimi kaldırıldı; `handle401Error`/`handle403Error` App Key'i **silmez**, backoff uygular; `cleanupLegacyIotToken` eski `iot_token`'ı bir defalık siler. `config.js` yalnız `EISA_KIOSK_FLEET_KEY`+`EISA_KIOSK_PROVISIONING_SECRET` credential okur (App Key/MAC/ID/pharmacy env fallback kaldırıldı; MAC otomatik tespit + SQLite'ta sabit). `scheduler.js` tüm çağrılar merkezi client'tan yeni `/api/kiosk/v1/` endpoint'lerine; 401+403 ayrı. `server.js` anlık session `/api/kiosk/v1/sessions/`'e, koşul `hasAppKeyCredentials(db)`. `db.js` SQLite dizin `700` / dosya `600` (Linux).
**Migration:** Yok. Mevcut `Kiosk.uygulama_anahtari` kullanıldı; yeni tablo/kolon yok.
**Test:** Backend 153/153 (yeni `apps/kiosk_api/tests` dahil), kiosk-edge 49/49 (yeni `provisioning.test.js`). `conftest.eczane` fixture'ı Il/Ilce için `get_or_create`'e çevrildi (önceden kırık, DOOH testlerini de düzeltti). `server.test.js`'teki iki eski QR beklentisi 8 karakter bitpack QR'a hizalandı (mevcut davranış).
**Breaking:** Operasyonel kiosk auth artık yalnız App Key + MAC; Bearer/IoT/Fleet/JWT reddedilir. `/api/kiosk/v1/{id}/...` ve `/api/pharmacies/kiosks/bootstrap/` kaldırıldı. Bootstrap `iot_token` yerine `app_key` döner.

### [analytics + web_panels + kiosk_edge] — Eczacı QR sorgu düzeltmesi, kamera kaldırma, detay response normalizasyonu
**Değişiklik:** Eczacı QR sorgusunda endpoint/contract uyumsuzlukları düzeltildi. `GET /api/analytics/sessions/` QR parametresi ile çağrıldığında 400/403/404 ayrımı netleşti; eczane sahipliği backend'de zorunlu hale getirildi. Response mevcut alanlar korunarak normalize edildi (`kiosk_detay`, `eczane`, `yas_araligi_detay`, `cinsiyet_detay`, `kategori_detay`, `cevap_detaylari`, `onerilen_etken_madde_detaylari`, `satis_sonucu`).
**Frontend:** `QrScan.vue` ekranından kamera akışı tamamen kaldırıldı (getUserMedia/BarcodeDetector/video state yok). Sayfa input-focus ile açılır; barkod okuyucu Enter ile tek istek tetikler; loading sırasında çift istek engellenir; hata/başarı durumlarında input yeniden focus alır. Hata mesajları ayrıştırıldı: boş, format, bulunamadı, başka eczane.
**Kiosk edge:** `POST /api/oturum/gonder` response ve backend'e gönderilen `qr_kodu` değeri 8 karakter bitpack QR ile hizalandı; QR üretim algoritması değiştirilmedi.
**Danışma tamamlama:** `POST /api/analytics/sessions/{id}/complete/` isteği opsiyonel `sale_result` alır (`sold|not_sold`). Not: satış sonucu için kalıcı DB kolonu yok; mevcut şema korunmuştur (migration yok).
**Test/Build:** Backend `apps/analytics/tests/test_qr_flow.py` eklendi ve geçti. Web build başarılı. Frontend unit testlerinde pre-existing bir `api.test.js` beklenti uyumsuzluğu devam ediyor. Tam backend suite'te pre-existing `campaigns` testlerinde lookup fixture kaynaklı hatalar mevcut.

---

## 2026-07-16

### [Tüm modüller] — Merkezi Loglama: JSON stdout + Correlation ID + Diagnostic Outbox
**Değişiklik:** Kubernetes uyumlu yapısal loglama altyapısı kuruldu. Uygulamalar dosyaya log YAZMIYOR; JSON stdout üretiyor. Loki/Alloy/Grafana bu görevde kurulmadı.
**Backend:** `apps/core/logging/` paketi (JSON formatter + correlation middleware + redaction), settings dosyasında RotatingFileHandler kaldırıldı, `LOG_LEVEL`/`LOG_FORMAT`/`SERVICE_NAME`/`APP_ENV`/`APP_VERSION` env eklendi. Yeni endpoint'ler: `POST /api/analytics/diagnostic-ingest/` (kiosk auth, DB'ye YAZMAZ, JSON stdout), `POST /api/analytics/client-events/` (JWT auth, rate limited). `X-Correlation-ID` her response'a eklenir; exception handler double-log'u engellemek için `_eisa_exception_logged` bayrağı kullanır.
**Fastify:** Pino JSON stdout, `logRedaction.js` (Authorization/token/qr_kodu/cevaplar vb. maskelenir), `correlationId.js` AsyncLocalStorage, `diagnosticOutbox.js` (SQLite v10: max 5000 kayıt, 7 gün, batch 100, exponential backoff, FIFO trigger), scheduler `pushDiagnostics()` + `X-Correlation-ID` propagation. Yeni endpoint: `POST /api/log/client` (Svelte UI hata köprüsü).
**Vue:** `src/lib/logger.js` production-safe wrapper, `app.config.errorHandler` + `window.onerror` + `unhandledrejection`, axios interceptor `X-Correlation-ID` yakalar; kritik hatalar backend'e allow-list ile bildirilir.
**Svelte:** `src/lib/logger.js` yerel Fastify'ye rate-limited hata köprüsü (yalnızca `screen_render_failed`, `local_api_unreachable`, `media_playback_failed`, `session_submit_failed`, `playlist_invalid` + tarayıcı global'leri).
**Docker/K8s:** `EISA_LOG_DIR`, `DJANGO_LOG_DIR`, log emptyDir/PVC, `/app/logs` mount, kiosk `/var/log/eisa` volume kaldırıldı; standart label seti (`app.kubernetes.io/component`, `.../version`) eklendi.
**AuditLog / OturumLogu / PlayLog dokunulmadı** — iş kayıtları PostgreSQL'de kalıyor.
**Testler:** Backend 76/76 (test_logging.py), Fastify 42/42 (12 yeni). web_panels + kiosk_edge/ui build başarılı. Not: `apps/campaigns/tests/test_dooh_v2.py` ve `web_panels api.test.js` pre-existing (bu görev öncesi) hatalar; loglama değişiklikleriyle ilgisi yok.
**Doküman:** `docs/operations/logging.md` (yeni), 01/02/03/04/05 kısaca güncellendi.
**Breaking:** Yok. Eski `error_id` alanı 500 yanıtlarında `correlation_id` ile değişti — panel bunu göstermek istiyorsa alan adına dikkat etmeli.

---


### [kiosk_edge/ui] — Dead Code Temizliği: SensitiveScreen Kaldırıldı
**Değişiklik:** Runtime'da hiçbir yerden çağrılmayan `SensitiveScreen.svelte` silindi. Yalnız bu dosyada kullanılan ölü CSS selector'ları (`.cat-card.sensitive*`, `.sensitive-badge`, `.sensitive-info-box`) temizlendi. `stores/kiosk.js` ekran state yorumu gerçek akışla hizalandı (`sensitive` → `consult`).
**Dosyalar:** `kiosk_edge/ui/src/components/SensitiveScreen.svelte` (silindi), `kiosk_edge/ui/src/app.css`, `kiosk_edge/ui/src/stores/kiosk.js`
**Breaking:** Yok (aktif akış `ConsultScreen` üzerinden devam ediyor).
**Test:** `npm test`, `npm run build` (kiosk_edge/ui)

---

## 2026-07-14

### [kiosk_edge] — Bootstrap İsteğine Cihaz Metadata Eklendi
**Değişiklik:** `provisioning.js`'e `collectDeviceMetadata()` fonksiyonu eklendi. Bootstrap isteği artık `hostname` ve `device_metadata` gönderir.
**Toplanan alanlar:** hostname, os_type, os_platform, os_release, arch, cpu_model, cpu_cores, total_memory_mb, ip_addresses (iface+IPv4), node_version, uptime_seconds.
**Güvenlik:** Her alan `try/catch` içinde; token/secret/hmac içermiyor; `collectDeviceMetadata` export edildi.
**Dosyalar:** `kiosk_edge/api-node/src/provisioning.js`
**Breaking:** Yok (bootstrap body yeni isteğe bağlı alanlar aldı; backend zaten kabul ediyordu).

### [web_panels] — Dashboard Pending Devices Banner + PendingDevices UX İyileştirme
**Değişiklik:** Dashboard'a `pendingCount > 0` olduğunda sarı uyarı banner'ı eklendi (`/admin/devices/pending` linki ile). PendingDevices.vue: eczane seçimi `<select>`'ten `EisaLookup` autocomplete'e çevrildi (ad/il/ilçe arama); metadata detay modalı yapılandırılmış görünüme (insan okunur etiketler, IP listesi, uptime formatlı) geçirildi.
**Dosyalar:** `web_panels/src/views/admin/Dashboard.vue`, `PendingDevices.vue`, `services/devices.js`
**Breaking:** Yok.

---

## 2026-07-14

### [Backend + web_panels + kiosk_edge] — Onay Bekleyen Cihaz Provisioning Akışı
**Değişiklik:** Kayıtsız kiosklar için uçtan uca IoT cihaz kayıt ve onay sistemi eklendi.
**Backend:** `KioskProvisioningRequest` modeli (PENDING/APPROVED/REJECTED lifecycle), migration 0006, `KioskBootstrapView` güncellendi (202 PENDING / 403 REJECTED), admin provisioning API endpoints (`/api/pharmacies/kiosks/provisioning/` list/detail/approve/reject).
**web_panels:** `PendingDevices.vue` yeni view, `/admin/devices/pending` route, AdminLayout nav item, `devices.js` service fonksiyonları eklendi.
**kiosk_edge:** `provisioning.js` durum makinesi (UNREGISTERED→PENDING_APPROVAL→APPROVED/REJECTED), `scheduler.js` bootstrap retry, `getProvisioningState` export edildi.
**Güvenlik:** fleet_key/provision_secret DB/log/UI'da saklanmaz; sabit zaman karşılaştırma korundu; onay transaction+select_for_update ile race condition güvenli; pending cihaz normal API'lere erişemez.
**Dosyalar:** `pharmacies/models.py`, `pharmacies/migrations/0006_*.py`, `pharmacies/serializers.py`, `pharmacies/views.py`, `pharmacies/urls.py`, `pharmacies/tests/test_provisioning.py`, `web_panels/.../PendingDevices.vue`, `devices.js`, `router/index.js`, `AdminLayout.vue`, `kiosk_edge/api-node/src/provisioning.js`, `scheduler.js`. **Doküman:** 00-AI-INDEX, 01-backend, 02-web-panels, 03-kiosk-edge-api-node, 05-cross-project-flows, 06-db-and-api-contracts güncellendi.
**Test:** 24/24 backend testi geçti.
**Breaking:** KioskBootstrapView davranışı değişti: bilinmeyen MAC artık 404 yerine 202 döndürüyor.

---

## 2026-07-07

### Kiosk Edge — SQLite FK Kaldırma + QR Anında Sync + ConsultScreen Visual Temizlik
**Değişiklik:** 3 kiosk iyileştirmesi yapıldı: (1) SQLite foreign key constraint'leri kaldırıldı, (2) QR oluştuğunda session anında backend'e iletilir, (3) Danışma kategori ikonlarının altındaki "X alt konu" yazısı kaldırıldı (alt kategori yapısı korundu).
**Detay:**
1. **SQLite FK kaldırma:** `db.js` schema'sından tüm `REFERENCES` clause'ları kaldırıldı (kategoriler, danisma_kategorileri, sorular, cevaplar, M2M tablolar). Backend zaten veri bütünlüğünü sağladığı için lokal DB'de gereksiz kontroller kaldırıldı. `scheduler.js` PRAGMA foreign_keys komutları temizlendi.
2. **QR anında sync:** `server.js` POST `/api/oturum/gonder` endpoint'i güncellendi → `tamamlandi=true` olduğunda anında backend'e `POST /api/analytics/sessions/` yapılır (exponential backoff retry ile). Başarılı olursa outbox kaydı `gonderilme_tarihi` işaretlenir; başarısız olursa scheduler tekrar dener. `scheduler.js` `requestWithRetry` fonksiyonu export edildi.
3. **ConsultScreen visual temizlik:** `ConsultScreen.svelte` kategori ikonlarının altındaki conditional "X alt konu" badge kaldırıldı (lines 63-65). Alt kategori navigation yapısı (activeParent, selectParent, selectChild, backToParents) tamamen korundu; sadece görsel sayı gösterimi kaldırıldı.
**Dosyalar:** `kiosk_edge/api-node/src/db.js`, `scheduler.js` (export requestWithRetry), `server.js` (immediate sync), `kiosk_edge/ui/src/components/ConsultScreen.svelte`
**Doküman:** 03-kiosk-edge-api-node.md, 04-kiosk-edge-ui.md, 07-session-and-analytics.md güncellendi.
**Test:** Container rebuild, sync success, 41 kategori + 6 danışma + 104 etken madde + 8 lookup başarıyla senkronize edildi.
**Breaking:** Yok.

---

## 2026-07-01

### Kiosk UI — Normal Idle Ekranı Kaldırıldı + Bileşen Refactor
**Değişiklik:** Açılışta gelen "normal idle" bekleme ekranı kaldırıldı; uygulama artık doğrudan çekici (attractor) ekranla açılıyor. Tekrar eden parçalar bileşene çıkarıldı.
**Detay:**
1. `IdleScreen.svelte` artık tek-durumlu attractor: açılışta anında gösterilir (10sn bekleme + iki-durumlu screensaver mantığı kaldırıldı). Reklam varsa görseller döner, yoksa `<AdPromo large />`. Eski `.screen-idle`/`.idle-*` markup ve CSS silindi.
2. `MediaView.svelte` (YENİ) — URL uzantısına göre `<video>`/`<img>` render eden ortak bileşen; AdStrip + IdleScreen kullanıyor (kopyalanan img/video mantığı tekilleştirildi).
3. `ScreenHeader.svelte` (YENİ) — Logo + opsiyonel subtitle; Welcome/Demographics/Category/Consult/Question ekranlarındaki tekrarlanan `kiosk-header` markup'ı bununla değiştirildi.
**Dosyalar:** `IdleScreen.svelte`, `MediaView.svelte` (YENİ), `ScreenHeader.svelte` (YENİ), `AdStrip.svelte`, `Welcome/Category/Consult/Demographics/QuestionScreen.svelte`, `app.css` (ölü idle stilleri temizlendi)
**Doküman:** 04-kiosk-edge-ui.md güncellendi.
**Test:** ui 16/16 geçti; tarayıcıda doğrulandı.
**Breaking:** Yok (idle screen state aynı; sadece görünüm/komponent yapısı değişti).

### Kiosk UI — Marka Logosu, Ortak AdPromo, Ekran Koruyucu Promosu, 20sn Inaktivite
**Değişiklik:** 4 UI iyileştirmesi yapıldı.
**Detay:**
1. `Logo.svelte` (YENİ) + `assets/eisa-logo.svg` & `eisa-logo-light.svg` — tüm "e-İSA" yazıları resmi marka logosu ile değiştirildi (koyu zeminde beyaz varyant).
2. `AdPromo.svelte` (YENİ) — dönen "Bu Alana Reklam Verebilirsiniz" tasarımı ortak bileşene çıkarıldı; AdStrip (reklam yokken) ve IdleScreen ekran koruyucusunda (reklam yokken, `large`) kullanılıyor.
3. IdleScreen `ss-overlay-text` ekranın ÜSTÜNE konumlandırıldı; ekran koruyucu artık stok görseller yerine reklam yoksa AdPromo döndürüyor.
4. App.svelte global inaktivite `10s → 20s`; idle/wifi dışındaki HER ekranda 20sn işlemsizlikte idle'a döner (`finalizeAbandonedSession()` ile terk edilmiş oturum analitiği korunur).
**Dosyalar:** `Logo.svelte`, `AdPromo.svelte`, `IdleScreen.svelte`, `AdStrip.svelte`, `App.svelte`, `Welcome/Category/Consult/Demographics/QuestionScreen.svelte`, `app.css`, `assets/eisa-logo*.svg`
**Doküman:** 04-kiosk-edge-ui.md güncellendi.
**Test:** ui 16/16 geçti.
**Breaking:** Yok.

### Kiosk ↔ Backend DOOH Uyum Denetimi — TZ + Slot + Ölü Endpoint Düzeltmeleri
**Değişiklik:** Reklam gösterim mantığının backend ile uyumu denetlendi; 3 gerçek hata düzeltildi.
**Hatalar:**
1. **Zaman dilimi (TZ):** Kiosk playlist'i UTC saatine göre seçiyordu; backend `target_hour` Istanbul yereli (USE_TZ, Europe/Istanbul) → reklamlar ~3 saat kayıyordu.
2. **Slot ölçeği:** `estimated_start_offset_seconds` saat-mutlak (0..3599) iken AdStrip slot döngüsü 60sn'e göre sarıyordu → sadece ilk dakikanın öğeleri oynuyor, PER_HOUR/PER_DAY reklamlar hiç görünmüyordu.
3. **Ölü endpoint:** `server.js` `/api/lookups/iller*` kaldırılmış SQLite tablolarını (db.js v9) sorguluyordu.
**Dosyalar:**
- `kiosk_edge/api-node/src/timezone.js` (YENİ — `istanbulNow()`)
- `kiosk_edge/api-node/src/server.js` (`/api/playlist/current` Istanbul tarih/saat; ölü iller endpoint'leri kaldırıldı)
- `kiosk_edge/api-node/src/scheduler.js` (playlist çekme Istanbul tarihi)
- `kiosk_edge/ui/src/components/AdStrip.svelte` (slot döngüsü 3600sn; Istanbul saati ile yeniden yükleme; kullanılmayan `loopSeconds` kaldırıldı)
**Doküman:** 08-dooh-advertising.md (Playlist/PlaylistItem/HouseAd/PlayLog modelleri, AdStrip örneği, sync aralıkları, TZ & Slot bölümü, çözülen riskler) gerçek kodla hizalandı.
**Test:** api-node 30/30, ui 16/16 geçti.
**Breaking:** Yok (davranış düzeltmesi; cihaz/konteyner TZ'sinden bağımsız çalışır).

### Kiosk Demo — Rancher/Kubernetes Manifest
**Değişiklik:** Birleşik kiosk container'ı demo.eisa.com.tr üzerinden yayınlamak için K8s manifest eklendi.
**Dosyalar:** `deploy/eisa-kiosk-demo.yaml` (YENİ)
**Kapsam:** Namespace + ConfigMap (EISA_ env'leri) + Deployment (ghcr.io/ysnzgl/eisa-kiosk:1.0.0, port 80) + Service (ClusterIP) + Ingress (traefik + cert-manager, demo.eisa.com.tr TLS).
**Pattern:** `deploy/eisa-app-production.yaml` ile aynı konvansiyon.
**Storage:** emptyDir (demo veri backend'den pull edilir); opsiyonel PVC örneği yorum olarak eklendi.
**Breaking:** Yok.

### Kiosk Docker — Tek Container Birleştirme
**Değişiklik:** API Node ve UI tek container'da birleştirildi (önce ayrı 2 servisti).
**Dosyalar:**
- `kiosk_edge/Dockerfile` (YENİ — birleşik multi-stage: ui-build + api-deps + runner)
- `kiosk_edge/.dockerignore` (YENİ)
- `kiosk_edge/docker-compose.demo.yml` (tek `kiosk` servisi, port 8080→80)
- `kiosk_edge/ui/src/lib/api.js` (`||` → `??` ki boş VITE_API_BASE relative path olsun)
- `kiosk_edge/README_DEMO_DOCKER.md` (birleşik mimari güncellendi)
**Mimari:** Nginx (:80) UI static + `/api` proxy → Node (127.0.0.1:8765); supervisord ile 2 process.
**Doküman:** 03-kiosk-edge-api-node.md, 04-kiosk-edge-ui.md Docker bölümleri güncellendi.
**Breaking:** Yok (ilk versiyondaki ayrı `api-node/Dockerfile` ve `ui/Dockerfile` kaldırıldı; tek kök `Dockerfile` kullanılıyor).

### Kiosk IdleScreen Layout İyileştirmesi
**Değişiklik:** Bekleme ekranındaki logo ve ana içerik ortadan yukarıya taşındı.
**Dosyalar:** `kiosk_edge/ui/src/app.css` (.screen-idle: `align-items: flex-start`, .idle-content: `margin-top: 80px`)
**Etki:** Daha dengeli görsel yerleşim, alt banner için daha fazla alan.

### Kiosk Docker Deployment (Demo)
**Değişiklik:** demo.eisa.com.tr için Docker yapısı oluşturuldu. Gerçek kiosk deployment'ında kullanılmaz.
**Not:** İlk versiyonda ayrı `api-node/Dockerfile` + `ui/Dockerfile` vardı; sonradan tek kök `Dockerfile`'a birleştirildi (üstteki kayıt).
**Dosyalar:**
- `kiosk_edge/docker-compose.demo.yml` (demo compose)
- `kiosk_edge/.env.demo` (environment variables)
- `kiosk_edge/README_DEMO_DOCKER.md` (deployment guide)
- `kiosk_edge/ui/.env.example` (VITE_API_BASE konfigürasyonu)
- `kiosk_edge/ui/src/lib/api.js` (API_BASE configurable: `import.meta.env.VITE_API_BASE`)
**Doküman:** 03-kiosk-edge-api-node.md, 04-kiosk-edge-ui.md güncellenmiş (Docker Deployment bölümü eklendi).
**Breaking:** Yok.

---

## 2026-06-05

### Danışma Tamamlama Akışı Uygulanması
**Değişiklik:** Backend'e pharmacist-side consultation completion endpoint eklendi. Yeni DB alanları: `danisma_tamamlandi`, `danisma_tamamlanma_tarihi`, `danisma_notu`, `danisma_tamamlayan_eczaci`.
**Dosyalar:** `backend/apps/analytics/views.py` (OturumLoguCompleteView), `models.py` (4 yeni alan), `serializers.py` (yeni alanlar), `urls.py` (endpoint path); `web_panels/src/views/pharmacist/QrScan.vue` (completion UI), `services/analytics.js` (completeSession helper).
**Migration:** `0005_oturumlogu_danisma_notu_and_more.py`
**Endpoint:** `POST /api/analytics/sessions/{id}/complete/` (eczacı-only, pharmacy ownership enforced, idempotent).
**Doküman:** `07-session-and-analytics.md`, `06-db-and-api-contracts.md` güncellenmiş.
**Breaking:** Yok.

### İlk Dokümantasyon Seti Oluşturuldu
**Dosyalar:** 00-AI-INDEX.md, 01-backend.md, 02-web-panels.md, 03-kiosk-edge-api-node.md, 04-kiosk-edge-ui.md, 05-cross-project-flows.md, 06-db-and-api-contracts.md
**Amaç:** Token-ekonomik AI context
**Kapsam:** Backend/frontend/kiosk modülleri, kritik akışlar, API contract'ları, belirsiz/riskli alanlar

### Optimization Pass — Context Quality
**Güncellenen:** Tüm mevcut dokümanlar
**Eklenen bölümler:** "When To Read This File", "Important Source Files", "Do Not Change Without Checking"
**Yeni dosyalar:** 07-session-and-analytics.md, 08-dooh-advertising.md, AI-WORKFLOW.md, AI-RULES.md
**Etki:** Daha hızlı context bulma, tekrar azaltma, kritik contract koruması

**Önemli bulgular:**
- DOOH v2 playlist mimarisi (60sn pre-computed)
- Offline-first kiosk (SQLite + outbox)
- Dual authentication (App-Key+MAC / IoT Token)
- Legacy Campaign.target_pharmacies + yeni CampaignTarget (belirsiz priority)
- Outbox pressure kontrolü (tam dolunca ne olur belirsiz)
- Session idempotency (backend impl doğrulanmalı)
- QR collision riski (unique constraint yok)
- Media cache placeholder

---

## Gelecek Kayıtlar

---

## 2026-07-22

### [Frontend] — Faz 6: CampaignWizard + DoohControlCenter
**Değişiklik:** 6 adımlı CampaignWizard (Bilgiler/Medya/Hedefleme/Frekans/Simülasyon/Aktive Et), DoohControlCenter (kampanya/job/kiosk izleme), useKioskRolloutStatus composable
**Dosyalar:** `CampaignWizard.vue`, `DoohControlCenter.vue` (yeni), `useKioskRolloutStatus.js` (yeni), `dooh.js`, `router/index.js`, `AdminLayout.vue`, `PlaylistEditor.vue`, `faz6_campaign_wizard.test.js` (yeni)
**Etki:** DOOH v2 contractlarla uçtan uca wizard; rollout izleme merkezi; 43 frontend test
**Breaking:** Yok — additive değişiklikler
**Doküman:** `02-web-panels.md`, `08-dooh-advertising.md`, `implementation-plan-dooh-scheduler.md` güncellendi

### [Frontend] — Faz 6 Kapanış Denetimi: Bug Düzeltmeleri
**Değişiklik:** (1) `summaryStats.behindKiosks` camelCase key fix, (2) `close()` unsaved changes warning, (3) `target_days` UI disabled, (4) `dooh.js` getIller/getIlceler duplicate kaldırıldı, (5) PlaylistEditor → lookups.js import
**Dosyalar:** `DoohControlCenter.vue`, `CampaignWizard.vue`, `dooh.js`, `PlaylistEditor.vue`
**Etki:** summaryStats doğru; kullanıcıya kayıp uyarısı; misleading UI düzeltildi
**Breaking:** Yok
**Doküman:** Bu changelog

### [Backend] — Faz 4/5 Hardening: Fingerprint + ACK + Sinyaller
**Değişiklik:** Fingerprint kaynağı PlaylistItem DB kayıtlarından hesaplanıyor; ACK capped backoff (30s→1800s); Eczane sinyali; pre_save eski eczane_id yakalama
**Dosyalar:** `activation_service.py`, `queue_worker.py`, `signals.py`, `db.js`, `scheduler.js`
**Etki:** 12 regression test; concurrent worker güvenli; ACK asla silinmiyor (max retry'da)
**Breaking:** Yok
**Doküman:** `implementation-plan-dooh-scheduler.md` Faz 5

### [Backend] — Faz 5: Desired/Applied Version + Kiosk ACK/Manifest
**Değişiklik:** KioskManifestView, KioskAckView, pending_ack SQLite tablosu, clearPendingAckIfMatches
**Dosyalar:** `kiosk_api/views.py`, `pharmacies/models.py`, `kiosk_edge/api-node/src/db.js`, `scheduler.js`
**Etki:** 18 backend test + 15 kiosk edge test
**Breaking:** Yok — flag=false legacy kiosklar etkilenmez
**Doküman:** `08-dooh-advertising.md` Faz 5

### [Backend] — Faz 4: Invalidation / DB Queue / Staged Publish
**Değişiklik:** GenerationJob DB queue, InvalidationService, QueueWorker, Campaign/Kiosk/Eczane sinyalleri
**Dosyalar:** `invalidation_service.py`, `queue_worker.py`, `signals.py`, `models.py` (0019 migration)
**Etki:** 31 + 12 backend test
**Breaking:** Yok
**Doküman:** `implementation-plan-dooh-scheduler.md` Faz 4

### [Backend] — Faz 3: Simulation / Activation
**Değişiklik:** `POST .../simulate/` (read-only), `POST .../activate/` (DOOH_ENGINE_V2=active)
**Dosyalar:** `activation_service.py`, `views_v2.py`, `serializers.py`
**Etki:** 21 test (FA-01..FA-16)
**Breaking:** Yok — DOOH_ENGINE_V2=off durumunda activate 403
**Doküman:** `08-dooh-advertising.md` Faz 3 Endpoint Contract

### [Backend] — Faz 2: PlacementEngine V2 Shadow Mode
**Değişiklik:** PlacementEngineV2, GlobalQuotaService, shadow mod scheduler entegrasyonu
**Dosyalar:** `placement_engine_v2.py`, `quota_service.py`, `scheduler.py`, migrations 0015-0018
**Etki:** 169 + 179 = 348 passed (Faz 2 sonrası)
**Breaking:** Yok — V1 authoritative, V2 shadow
**Doküman:** `implementation-plan-dooh-scheduler.md` Faz 2

**Format örneği (max 10 satır):**

```
## YYYY-MM-DD

### [Modül] — Değişiklik Başlığı
**Değişiklik:** ...
**Dosyalar:** ...
**Etki:** ...
**Breaking:** Var/Yok
**Doküman:** Güncellendi/Eklendi
```

---

**Not:** Bu dosya AI tarafından otomatik güncellenir.

