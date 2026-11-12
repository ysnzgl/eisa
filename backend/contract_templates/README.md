# Onaylı kaynak sözleşmeler

8 Kasım 2026'da kullanıcının sağladığı iki DOCX değiştirilmeden bu klasöre kopyalandı.
Uygulama önce `EISA_CONTRACT_EK1_TEMPLATE` / `EISA_CONTRACT_EK2_TEMPLATE` ortam
değişkenlerine, sonra bu sürümlü kaynaklara bakar. Kaynak dosyaları yerinde değiştirmeyin.

| Dosya | SHA-256 |
|---|---|
| e-isa_Eczane_Sozlesmesi_Ek1_Son.docx | 72CBDF349394D9AAFD070E747DF5C27E6FA55E70BF1467056687A7F3C9661F71 |
| e-isa_Zimmet_Tutanagi_Ek2.docx | 113EC517C0528AB4E73C2AA1E8240877B0502E9B23C02A7EDB23E8C4870D30A2 |

`apps/abonelik/contract_docx.py` değişken alanları doldurur. Ek-2'nin 4, 5 ve 7.
bölümleri (XML'deki 3, 4 ve 5. tablo indeksleri) elle tamamlanmak üzere korunur.
Ekran önizlemesi doldurulan DOCX'teki tam metin ve tablolardan üretilir; Word'ün
sayfalama ve görsel yerleşiminin birebir tarayıcı karşılığı değildir.
