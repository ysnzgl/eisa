# Kiosk Idle Ses Kontrol Raporu — 2026-09-13

## Sonuç

Idle ses akışı ilk bekleme ve devam aralığına göre sıralı/döngüsel çalışacak şekilde sağlamlaştırıldı. Mesai içi mod İstanbul saatiyle 08:00–19:00, “Mesai dışı / 24 saat” modu gün boyu çalışır. Nöbet günü istisnası korunmuştur.

## Tespitler ve düzeltmeler

- Idle ekrandaki herhangi bir `pointerdown/keydown`, önceki kodda ses çevrimini aynı idle oturumu boyunca kalıcı bloke ediyordu. Artık ses çalıyorsa keser; bekleme süresini ekran geçişine veya dokunuşa göre değil son QR kayıt zamanına göre korur ve dosya sırasını başa sarmaz.
- İlk ses beklemesi artık idle ekrana dönülen andan değil, lokal DB'deki son QR'lı `oturum_outbox` kaydının `olusturulma_tarihi` alanından hesaplanır. Örneğin ilk bekleme 20 dk ve son QR kaydı 18 dk önceyse idle ekranda sayaç 2 dk kalandan devam eder.
- Idle ekran her açıldığında `/api/oturum/last-qr` yeniden çağrılır. Yeni QR, API yanıtındaki kayıt zamanıyla sayacı anında ilk süreye çeker; ilk süre zaten aşılmışsa eski davranıştaki 1 saniyelik tetik yerine cihazın devam süresi (örneğin 5 dk) kurulur.
- Sonuç ekranındaki “Ana ekrana dön” akışı artık lokal DB uzlaşmasını bekledikten sonra idle ekranını etkinleştirir; böylece eski sayaç tek frame bile gösterilmez. QR oluşturma sırasında başlamış eski polling yanıtlarının yeni zamanı sonradan ezmesi de store sürüm kontrolüyle engellendi.
- Ses çalmıyorken yapılan pointer/klavye etkileşimi mevcut timer'ı artık yeniden kurmaz. Ses çalarken etkileşim sesi keser; sıradaki dosya devam süresi sonunda gelir ve dosya listesi başa sarmaz.
- Tarayıcı ses akışının dosya sonunu güvenilir belirlemesi için lokal `/api/device-audio/:audioId` yanıtına `Content-Length`, `Accept-Ranges`, `206 Partial Content` ve `Content-Range` desteği eklendi.
- Provision onay yanıtındaki `device_config` artık hemen uygulanır; sesler full pull zamanını beklemeden indirilir. Başlangıç pull'u ve `EISA_PULL_INTERVAL_SEC` periyodik pull'u dosya listesini yeniden kontrol eder. İndirme SHA-256 doğrulamalı ve snapshot atomiktir; hata halinde son çalışan eksiksiz liste korunur.
- UI sıra testi 16 dosyanın tamamını `1 → 16` sırasıyla doğrular; son dosyadan sonra liste başa döner.
- Debug modda idle ekranın sağ üstünde "Sese kalan" sayacı görünür. Sayaç sıradaki timer'ı toplam saniye (`120 sn`, `119 sn`, ...) olarak her saniye gösterir; ses kapalı, mesai dışı veya çalıyor durumlarında süre yerine durum metni yazar.

## Local veri kontrolü

Kiosk `25` kayıtlı verisinde ilk/devam sürelerinin ters (`300/120 sn`) olduğu görüldü. Merkezi kayıt `ilk=120 sn`, `devam=300 sn` olarak düzeltildi ve tek seferlik pull ile lokal edge'e uygulandı. Canlı lokal endpoint'te mod `ALL_DAY`, ses açık ve dosya sayısı `16` olarak doğrulandı.

## Doğrulama kapsamı

- Kiosk UI: 79 test geçti; QR sonrası sayaç yenileme, stale polling koruması, ilk süre kalanı, ilk eşik aşılınca devam süresi, döngü, dokunuş, mesai kuralı ve 16 dosya sırası kapsandı.
- API-node: 175 test ve `server.js` sözdizimi kontrolü geçti; cihaz config, provisioning ve ses dosyası tam/range yanıtları kapsandı.
- Backend: 40 hedefli test ve migration tutarlılık kontrolü geçti. Yalnız mevcut Django 6 `CheckConstraint.check` deprecation uyarıları görüldü; ses akışıyla ilgili hata yoktur.
- Kiosk UI ve web panel production build'leri geçti. `git diff --check` whitespace hatası bulmadı; Windows satır sonu dönüşüm uyarıları mevcuttur.

## Beş dakikalık tüm servis izlemesi

`npm run dev:all` ile web panel (`5174`), Django (`8000`), backend scheduler, kiosk API (`8765`) ve kiosk UI (`5173`) birlikte çalıştırıldı. Beş dakika boyunca servis kapanması veya HTTP 4xx/5xx görülmedi; QR üretimi `201`, merkezi session sync `200`, periyodik ping `200`, ses byte-range isteği `206` ve 16 dosyalı başlangıç cache'i başarılıydı.

- Başlangıçta Django henüz hazır değilken edge istekleri kısa süre `fetch failed` ile retry yaptı ve backend açılınca kendiliğinden düzeldi.
- Yerel tarayıcı ilk otomatik sesi kullanıcı etkileşimi olmadığı için bir kez engelledi. Sonraki kullanıcı etkileşiminden sonra ses 1 ve ses 2 istekleri başarılı oldu. Production kiosk Chromium'un `--autoplay-policy=no-user-gesture-required` bayrağıyla başlatılmalıdır.
- Edge API başlangıcında aynı ping'in iki yerden gönderildiği ve katalog pull transaction'ının iki kez çağrıldığı tespit edilip düzeltildi. Hot-restart sonrasında başlangıçta tek ping ve tek katalog işleme doğrulandı.
