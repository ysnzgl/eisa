# Sözleşme ve tanım ekranları görsel akış testi

Panel dizininde `npm run test:visual` çalıştırın. Microsoft Edge'in kurulu olması
gerekir. Playwright ayrı ve geçici bir headless tarayıcı açar; mevcut tarayıcıya,
gerçek hesaba veya mali kayıtlara bağlanmaz. Tüm API çağrıları sentetik verilerle
karşılanır. 4175 portunda Vite başlatılır veya mevcut test sunucusu kullanılır.

Kapsam: ayrı bölge/tarife sayfaları, tüm ilçelerle kayıt, fiziksel seri envanteri,
provizyon eşleştirmesi, sözleşme planında seri seçimi, iki tam sözleşme önizlemesi,
indirme düğmesi ve mobil kaydırma/işlem düğmelerine erişim.

`fixtures/contracts.json` kısa bir temsili sözleşme değildir. Gerçek kaynak DOCX'ler
ve backend üreticisiyle oluşturulmuştur. Şablon/üretici değişince repo kökünden:

```powershell
.\.venv\Scripts\python.exe backend/scripts/export_contract_visual_fixture.py
```

Üretim yalnız sentetik nesneler ve taklit banka sorgusu kullanır; veritabanına
okuma/yazma yapmaz. Backend testleri gerçek ORM kayıtlarıyla DOCX içeriğini ve
eczane erişim sınırını ayrıca doğrular. Tarayıcı indirme testi dosya aktarımını
taklit eder; Word dosyasının içeriğini backend testleri doğrular.

Ekran görüntüleri `test-results` altına yazılır ve görsel olarak incelenir.
Kontroller yatay taşmayı, alan/işlem erişimini ve istek gövdelerini doğrular;
piksel bazında eski ekranla kıyaslama veya Word sayfa düzeni testi değildir.
