"""
Abonelik (Sözleşme) ve Ödeme modelleri.

İş kuralları:
  - `Sozlesme`: Eczane ile yapılan hizmet sözleşmesi. 12/24/36 ay standart süre
    + "Kullanım Bedeli Öteleme Süresi" (grace) ay sayısı. Ötelenen her ay
    sözleşme bitiş tarihine eklenir (vade kaydırma).
  - `CihazOdemePlani`: Cihaz donanım bedelinin peşin fiyat + vade farkı ile
    4 veya 8 taksite bölünmesi.
  - `Fatura`: Cariye borç olarak yansıyan kalem (kullanım bedeli veya cihaz
    taksiti). Ödeme yapılmazsa vade + grace sonrası GECIKTI olur.
  - `Odeme`: Bir faturaya karşılık kaydedilen tahsilat (mock/manuel).

Tarih aritmetiği ay-bazlıdır; `apps.abonelik.services.add_months` kullanılır.
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Sozlesme(BaseModel):
    """Eczane ile yapılan hizmet sözleşmesi (demo veya standart)."""

    class Tur(models.TextChoices):
        DEMO = "DEMO", "Demo"
        STANDART = "STANDART", "Standart"

    class Tip(models.IntegerChoices):
        AY_12 = 12, "12 Ay"
        AY_24 = 24, "24 Ay"
        AY_36 = 36, "36 Ay"

    class Durum(models.TextChoices):
        AKTIF = "AKTIF", "Aktif"
        IPTAL = "IPTAL", "İptal"

    # Demo sözleşmenin toplam süresi (temel + uzatma) bu günü aşamaz.
    DEMO_MAKS_GUN = 30

    eczane = models.ForeignKey(
        "pharmacies.Eczane", on_delete=models.PROTECT, related_name="sozlesmeler"
    )
    tur = models.CharField(
        max_length=10, choices=Tur.choices, default=Tur.STANDART, db_index=True,
        help_text="Sözleşme türü: demo (gün bazlı) veya standart (ay bazlı).",
    )
    sozlesme_tipi_ay = models.PositiveSmallIntegerField(
        choices=Tip.choices, null=True, blank=True,
        help_text="Standart sözleşme süresi (ay). Demo'da boş.",
    )
    demo_gun = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Demo sözleşme süresi (gün, en fazla 30). Standart'ta boş.",
    )
    baslangic_tarihi = models.DateField(help_text="Sözleşme başlangıç tarihi.")
    oteleme_ay = models.PositiveSmallIntegerField(
        default=0,
        help_text="Kullanım bedeli öteleme süresi (ay). Bu süre kadar fatura kesilmez "
                  "ve süre sözleşme sonuna eklenir.",
    )
    ek_ay_toplam = models.PositiveSmallIntegerField(
        default=0, help_text="Uzatmalarla eklenen toplam ay (standart).",
    )
    ek_gun_toplam = models.PositiveSmallIntegerField(
        default=0, help_text="Uzatmalarla eklenen toplam gün (demo).",
    )
    onceki_sozlesme = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="sonraki_sozlesmeler",
        help_text="Bu sözleşme bir öncekinin devamıysa (ör. demo→standart) bağlantı.",
    )
    aylik_kullanim_bedeli = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("3900.00"),
        help_text="Aylık e-İSA kullanım bedeli (TL). Demo'da faturalanmaz.",
    )

    class KdvOrani(models.IntegerChoices):
        KDV_0 = 0, "%0 (KDV Yok)"
        KDV_1 = 1, "%1"
        KDV_10 = 10, "%10"
        KDV_20 = 20, "%20"

    TEVKIFAT_SECENEKLER = [
        ("", "Yok"),
        ("1/10", "1/10"), ("2/10", "2/10"), ("3/10", "3/10"),
        ("4/10", "4/10"), ("5/10", "5/10"), ("6/10", "6/10"),
        ("7/10", "7/10"), ("8/10", "8/10"), ("9/10", "9/10"),
    ]

    class CihazDurum(models.TextChoices):
        SATILIK = "SATILIK", "Satılık"
        KIRALIK = "KIRALIK", "Kiralık"

    cihaz_durumu = models.CharField(
        max_length=12, choices=CihazDurum.choices, default=CihazDurum.SATILIK,
        help_text="Cihaz satılık mı kiralık mı?",
    )
    cihaz_kira_bedeli = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        help_text="Kiralık cihaz için aylık kira bedeli (TL).",
    )
    kdv_orani = models.PositiveSmallIntegerField(
        choices=KdvOrani.choices, default=0,
        help_text="Kullanım bedeli ve cihaz kira üzerindeki KDV oranı (%).",
    )
    tevkifat_orani = models.CharField(
        max_length=4, choices=TEVKIFAT_SECENEKLER, blank=True, default="",
        help_text="KDV tevkifat oranı (ör. '3/10'). Boş = tevkifat yok.",
    )
    iptal_ceza_orani = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("2.00"),
        help_text="Erken iptal ceza katsayısı: ceza = kalan_ay × katsayi × aylık_bedel. Varsayılan 2.",
    )
    eczaci_onay_tarihi = models.DateTimeField(
        null=True, blank=True,
        help_text="Eczacının dijital onay tarihi.",
    )
    eczaci_onay_ip = models.GenericIPAddressField(
        null=True, blank=True, help_text="Onay IP adresi.",
    )

    class ImzaTipi(models.TextChoices):
        DIJITAL = "DIJITAL", "Dijital İmza"
        ISLAK = "ISLAK", "Islak İmza"

    imza_tipi = models.CharField(
        max_length=8, choices=ImzaTipi.choices, default=ImzaTipi.DIJITAL,
        help_text="Dijital (eczacı ekrandan onaylar) veya ıslak (taranıp yüklenir).",
    )
    islak_imza_url = models.CharField(
        max_length=500, blank=True, default="",
        help_text="RustFS/S3 yolu — ıslak imzalı belge (expiring URL değil, kalıcı path).",
    )
    onayli_sozlesme_metni = models.TextField(
        blank=True, default="",
        help_text="Dijital onay anındaki tam sözleşme metni (HTML). Onaylandıktan sonra değişmez.",
    )
    durum = models.CharField(
        max_length=16, choices=Durum.choices, default=Durum.AKTIF, db_index=True
    )
    notlar = models.TextField(blank=True, default="")

    class Meta:
        db_table = "abonelik_sozlesmeler"
        ordering = ("-baslangic_tarihi", "-id")
        verbose_name = "Sözleşme"
        verbose_name_plural = "Sözleşmeler"

    def __str__(self) -> str:  # pragma: no cover
        if self.tur == self.Tur.DEMO:
            return f"{self.eczane_id} — Demo {self.demo_gun or 0} gün"
        return f"{self.eczane_id} — {self.sozlesme_tipi_ay}+{self.oteleme_ay} ay"

    @property
    def is_demo(self) -> bool:
        return self.tur == self.Tur.DEMO

    # ── Türetilen alanlar ───────────────────────────────────────────────
    @property
    def toplam_ay(self) -> int:
        """Standart süre + öteleme + uzatma (vade kaydırma sonrası toplam süre)."""
        if self.is_demo:
            return 0
        return int(self.sozlesme_tipi_ay or 0) + int(self.oteleme_ay) + int(self.ek_ay_toplam)

    @property
    def toplam_gun(self) -> int:
        """Demo için temel + uzatma toplam gün."""
        if not self.is_demo:
            return 0
        return int(self.demo_gun or 0) + int(self.ek_gun_toplam)

    @property
    def kullanim_bedeli_baslangic(self):
        """İlk kullanım bedeli faturasının kesileceği dönem (öteleme sonrası)."""
        from apps.abonelik.services import add_months

        if self.is_demo:
            return None
        return add_months(self.baslangic_tarihi, int(self.oteleme_ay))

    @property
    def bitis_tarihi(self):
        """Toplam süre (uzatma dahil) sonundaki sözleşme bitiş tarihi."""
        import datetime as _dt

        from apps.abonelik.services import add_months

        if self.is_demo:
            return self.baslangic_tarihi + _dt.timedelta(days=self.toplam_gun)
        return add_months(self.baslangic_tarihi, self.toplam_ay)

    @property
    def kalan_gun(self):
        """Bugünden bitişe kalan gün (negatifse süresi dolmuş)."""
        from django.utils import timezone

        return (self.bitis_tarihi - timezone.localdate()).days

    @property
    def suresi_doldu(self) -> bool:
        """Aktif ama bitiş tarihi geçmiş (türetilen 'tamamlandı' durumu)."""
        return self.durum == self.Durum.AKTIF and self.kalan_gun < 0

    @property
    def etkin_durum(self) -> str:
        """Görüntülenecek etkin durum: IPTAL | SURESI_DOLDU | AKTIF (türetilir)."""
        if self.durum == self.Durum.IPTAL:
            return "IPTAL"
        return "SURESI_DOLDU" if self.suresi_doldu else "AKTIF"

    @property
    def kdv_tutari(self) -> Decimal:
        """Aylık kullanım bedeli üzerinden KDV tutarı."""
        if not self.kdv_orani:
            return Decimal("0.00")
        return (self.aylik_kullanim_bedeli * self.kdv_orani / 100).quantize(Decimal("0.01"))

    @property
    def kdv_dahil_aylik(self) -> Decimal:
        """KDV dahil aylık kullanım bedeli."""
        return self.aylik_kullanim_bedeli + self.kdv_tutari

    @property
    def tevkifat_kesri(self) -> Decimal:
        """Tevkifat oranı kesir değeri."""
        if not self.tevkifat_orani:
            return Decimal("0.00")
        parts = self.tevkifat_orani.split("/")
        return Decimal(parts[0]) / Decimal(parts[1])

    @property
    def tevkifat_tutari(self) -> Decimal:
        return (self.kdv_tutari * self.tevkifat_kesri).quantize(Decimal("0.01"))

    @property
    def net_odeme(self) -> Decimal:
        """Alıcının ödeyeceği net tutar (KDV dahil - tevkifat)."""
        return self.kdv_dahil_aylik - self.tevkifat_tutari

    @property
    def iptal_ceza_tutari(self) -> Decimal:
        """Erken iptal ceza: kalan_ay × katsayi × aylık_bedel."""
        if not self.iptal_ceza_orani or self.is_demo:
            return Decimal("0.00")
        from django.utils import timezone
        kalan_gun = max(0, (self.bitis_tarihi - timezone.localdate()).days)
        kalan_ay = Decimal(str(kalan_gun)) / 30
        return (
            self.aylik_kullanim_bedeli * kalan_ay * self.iptal_ceza_orani
        ).quantize(Decimal("0.01"))


class SozlesmeUzatma(BaseModel):
    """Bir sözleşmeye uygulanan uzatma veya iptal kaydı."""

    sozlesme = models.ForeignKey(
        Sozlesme, on_delete=models.CASCADE, related_name="uzatmalar"
    )
    ek_ay = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Eklenen ay (standart sözleşme).",
    )
    ek_gun = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Eklenen gün (demo sözleşme).",
    )
    is_iptal = models.BooleanField(default=False, help_text="Bu satır bir iptal işlemi mi?")
    neden = models.CharField(max_length=255, blank=True, default="")
    iptal_nedeni = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "abonelik_sozlesme_uzatmalari"
        ordering = ("-olusturulma_tarihi", "-id")
        verbose_name = "Sözleşme Uzatma"
        verbose_name_plural = "Sözleşme Uzatmaları"

    def __str__(self) -> str:  # pragma: no cover
        birim = f"{self.ek_gun} gün" if self.ek_gun else f"{self.ek_ay} ay"
        return f"Uzatma #{self.pk} — +{birim}"


class CihazOdemePlani(BaseModel):
    """Cihaz ödeme planı — satılık (peşin+taksit) veya kiralık (aylık kira)."""

    class Tip(models.TextChoices):
        SATILIK = "SATILIK", "Satılık"
        KIRALIK = "KIRALIK", "Kiralık"

    class TaksitSayisi(models.IntegerChoices):
        TAKSIT_1 = 1, "1 Taksit (Peşin)"
        TAKSIT_4 = 4, "4 Taksit"
        TAKSIT_8 = 8, "8 Taksit"
        TAKSIT_12 = 12, "12 Taksit"

    class Durum(models.TextChoices):
        AKTIF = "AKTIF", "Aktif"
        TAMAMLANDI = "TAMAMLANDI", "Tamamlandı"
        IPTAL = "IPTAL", "İptal"

    sozlesme = models.ForeignKey(
        Sozlesme, on_delete=models.CASCADE, related_name="cihaz_planlari"
    )
    tip = models.CharField(
        max_length=8, choices=Tip.choices, default=Tip.SATILIK,
        help_text="Satılık (peşin+taksit) veya kiralık (aylık kira).",
    )
    adet = models.PositiveSmallIntegerField(default=1, help_text="Cihaz adedi.")
    # Satılık alanları
    pesin_fiyat = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Birim peşin fiyat (TL). Satılıkta zorunlu.",
    )
    vade_farki_orani = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("0.00"),
        help_text="Vade farkı yüzde (%).",
    )
    taksit_sayisi = models.PositiveSmallIntegerField(
        default=1, help_text="Taksit sayısı (1–12).",
    )
    # Kiralık alanları
    aylik_kira_bedeli = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Birim aylık kira bedeli (TL). Kiralıkta zorunlu.",
    )
    # Ortak: KDV + tevkifat
    cihaz_kdv_orani = models.PositiveSmallIntegerField(
        choices=Sozlesme.KdvOrani.choices, default=0,
        help_text="KDV oranı (%).",
    )
    tevkifat_orani = models.CharField(
        max_length=4, choices=Sozlesme.TEVKIFAT_SECENEKLER, blank=True, default="",
        help_text="KDV tevkifat oranı.",
    )
    baslangic_tarihi = models.DateField(help_text="İlk faturalandırma ayı.")
    durum = models.CharField(
        max_length=16, choices=Durum.choices, default=Durum.AKTIF, db_index=True
    )

    class Meta:
        db_table = "abonelik_cihaz_odeme_planlari"
        ordering = ("-id",)
        verbose_name = "Cihaz Ödeme Planı"
        verbose_name_plural = "Cihaz Ödeme Planları"

    def __str__(self) -> str:  # pragma: no cover
        return f"Cihaz planı #{self.pk} ({self.tip}, {self.adet} adet)"

    @property
    def toplam_tutar(self) -> Decimal:
        """Satılık: adet × peşin × (1 + vade%). Kiralık: adet × aylık kira."""
        if self.tip == self.Tip.KIRALIK:
            return ((self.aylik_kira_bedeli or Decimal("0.00")) * Decimal(self.adet)).quantize(Decimal("0.01"))
        if not self.pesin_fiyat:
            return Decimal("0.00")
        oran = (Decimal("100.00") + self.vade_farki_orani) / Decimal("100.00")
        return (self.pesin_fiyat * Decimal(self.adet) * oran).quantize(Decimal("0.01"))

    @property
    def taksit_tutari(self) -> Decimal:
        """Satılık: toplam / taksit sayısı. Kiralık: aylık tutar."""
        if self.tip == self.Tip.KIRALIK:
            return self.toplam_tutar
        if not self.taksit_sayisi:
            return Decimal("0.00")
        return (self.toplam_tutar / Decimal(self.taksit_sayisi)).quantize(Decimal("0.01"))

    @property
    def cihaz_kdv_tutari(self) -> Decimal:
        if not self.cihaz_kdv_orani:
            return Decimal("0.00")
        return (self.toplam_tutar * self.cihaz_kdv_orani / 100).quantize(Decimal("0.01"))

    @property
    def tevkifat_kesri(self) -> Decimal:
        if not self.tevkifat_orani:
            return Decimal("0.00")
        parts = self.tevkifat_orani.split("/")
        return Decimal(parts[0]) / Decimal(parts[1])

    @property
    def tevkifat_tutari(self) -> Decimal:
        return (self.cihaz_kdv_tutari * self.tevkifat_kesri).quantize(Decimal("0.01"))

    @property
    def kdv_dahil_toplam(self) -> Decimal:
        return self.toplam_tutar + self.cihaz_kdv_tutari

    @property
    def kdv_dahil_taksit(self) -> Decimal:
        """KDV dahil taksit tutarı."""
        if not self.taksit_sayisi:
            return Decimal("0.00")
        return (self.kdv_dahil_toplam / Decimal(self.taksit_sayisi)).quantize(Decimal("0.01"))

    @property
    def odeme_tipi(self) -> str:
        """Satılık cihaz için peşin mi yoksa taksit mi yansıyacak."""
        if self.tip == self.Tip.KIRALIK:
            return "KIRA"
        return "PESIN" if self.taksit_sayisi == 1 else "TAKSIT"

    @property
    def odeme_tutari(self) -> Decimal:
        """Satılıkta peşin toplamı, taksitli durumda aylık taksit tutarı."""
        if self.tip == self.Tip.KIRALIK:
            return self.toplam_tutar
        if self.taksit_sayisi == 1:
            return self.toplam_tutar
        return self.taksit_tutari

    @property
    def odeme_etiketi(self) -> str:
        """Kullanıcıya gösterilecek kısa ödeme etiketi."""
        if self.tip == self.Tip.KIRALIK:
            return "Aylık kira"
        if self.taksit_sayisi == 1:
            return "Peşin fiyat"
        return f"{self.taksit_sayisi} taksit"


class FiyatTanimi(BaseModel):
    """Global fiyat tanımı (abonelik + cihaz kira bedeli), geçerlilik tarihli.

    Yeni sözleşme oluşturulurken tutarlar o tarihte geçerli tanımdan önerilir;
    sözleşme kendi tutarını kopyalar (tarihsel fiyat korunur). Tarihçe tutulur.
    """

    abonelik_bedeli = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("3900.00"),
        help_text="Aylık e-İSA abonelik (kullanım) bedeli (TL).",
    )
    cihaz_kira_bedeli = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        help_text="Kiralık cihaz için aylık kira bedeli (TL).",
    )
    acma_kapama_bedeli = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        help_text="Hesap açma/kapama bedeli: gecikme sonrası yeniden aktifleştirme ücreti (TL).",
    )
    iptal_ceza_orani = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("2.00"),
        help_text="Erken iptal ceza katsayısı: ceza = kalan_ay × katsayi × aylık_bedel.",
    )
    gecerlilik_baslangic = models.DateField(
        db_index=True, help_text="Bu fiyatın geçerli olmaya başladığı tarih.",
    )
    aciklama = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "abonelik_fiyat_tanimlari"
        ordering = ("-gecerlilik_baslangic", "-id")
        verbose_name = "Fiyat Tanımı"
        verbose_name_plural = "Fiyat Tanımları"

    def __str__(self) -> str:  # pragma: no cover
        return f"Fiyat {self.gecerlilik_baslangic} — abonelik {self.abonelik_bedeli} TL"


class Fatura(BaseModel):
    """Cariye borç olarak yansıyan faturalandırma kalemi."""

    class Tip(models.TextChoices):
        KULLANIM_BEDELI = "KULLANIM_BEDELI", "Kullanım Bedeli"
        CIHAZ_TAKSIT = "CIHAZ_TAKSIT", "Cihaz Taksiti"
        CIHAZ_KIRA = "CIHAZ_KIRA", "Cihaz Kira Bedeli"
        BIRLESIK = "BIRLESIK", "Birleşik Aylık Fatura"
        ACMA_KAPAMA = "ACMA_KAPAMA", "Açma/Kapama Bedeli"

    class Durum(models.TextChoices):
        BEKLIYOR = "BEKLIYOR", "Bekliyor"
        ODENDI = "ODENDI", "Ödendi"
        GECIKTI = "GECIKTI", "Gecikti"
        IPTAL = "IPTAL", "İptal"

    eczane = models.ForeignKey(
        "pharmacies.Eczane", on_delete=models.PROTECT, related_name="faturalar"
    )
    sozlesme = models.ForeignKey(
        Sozlesme, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="faturalar",
    )
    cihaz_plani = models.ForeignKey(
        CihazOdemePlani, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="faturalar",
    )
    tip = models.CharField(max_length=20, choices=Tip.choices, db_index=True)
    donem = models.CharField(
        max_length=7, db_index=True,
        help_text="Faturalama dönemi (YYYY-MM).",
    )
    taksit_no = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Cihaz taksitleri için sıra numarası.",
    )
    tutar = models.DecimalField(max_digits=12, decimal_places=2)
    vade_tarihi = models.DateField(db_index=True)
    durum = models.CharField(
        max_length=16, choices=Durum.choices, default=Durum.BEKLIYOR, db_index=True
    )
    odenme_tarihi = models.DateTimeField(null=True, blank=True)
    aciklama = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "abonelik_faturalar"
        ordering = ("-vade_tarihi", "-id")
        verbose_name = "Fatura"
        verbose_name_plural = "Faturalar"
        constraints = [
            # Cihaz taksitleri: aynı eczane + tip + dönem + taksit için tek fatura.
            models.UniqueConstraint(
                fields=["eczane", "tip", "donem", "taksit_no"],
                condition=models.Q(taksit_no__isnull=False),
                name="uniq_fatura_eczane_tip_donem_taksit",
            ),
            # Kullanım bedeli (taksit_no NULL): NULL'lar benzersiz sayıldığından
            # partial index ile aynı eczane + tip + dönem için tekillik zorlanır.
            models.UniqueConstraint(
                fields=["eczane", "tip", "donem"],
                condition=models.Q(taksit_no__isnull=True),
                name="uniq_fatura_eczane_tip_donem_notaksit",
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.get_tip_display()} {self.donem} — {self.tutar} TL"

    @property
    def acik(self) -> bool:
        """Henüz ödenmemiş (borç) mu?"""
        return self.durum in (self.Durum.BEKLIYOR, self.Durum.GECIKTI)


class Odeme(BaseModel):
    """Bir faturaya karşılık kaydedilen tahsilat (mock/manuel)."""

    class Yontem(models.TextChoices):
        KREDI_KARTI = "KREDI_KARTI", "Kredi Kartı"
        EFT_HAVALE = "EFT_HAVALE", "EFT/Havale"
        OTOMATIK_CEKIM = "OTOMATIK_CEKIM", "Otomatik Çekim"
        MANUEL = "MANUEL", "Manuel"

    fatura = models.ForeignKey(
        Fatura, on_delete=models.CASCADE, related_name="odemeler"
    )
    tutar = models.DecimalField(max_digits=12, decimal_places=2)
    yontem = models.CharField(
        max_length=16, choices=Yontem.choices, default=Yontem.KREDI_KARTI
    )
    aciklama = models.CharField(
        max_length=500, blank=True, default="",
        help_text="Ödeme açıklaması / referans bilgisi. Manuel ödemelerde zorunludur.",
    )
    odeme_tarihi = models.DateTimeField()

    class Meta:
        db_table = "abonelik_odemeler"
        ordering = ("-odeme_tarihi", "-id")
        verbose_name = "Ödeme"
        verbose_name_plural = "Ödemeler"

    def __str__(self) -> str:  # pragma: no cover
        return f"Ödeme #{self.pk} — {self.tutar} TL"



class FaturaKalemi(BaseModel):
    """Aylık birleşik faturanın kalem satırları (abonelik, cihaz taksit, kira, açma-kapama)."""

    class KalemTip(models.TextChoices):
        ABONELIK = "ABONELIK", "Abonelik Bedeli"
        CIHAZ_TAKSIT = "CIHAZ_TAKSIT", "Cihaz Taksiti"
        CIHAZ_KIRA = "CIHAZ_KIRA", "Cihaz Kira"
        ACMA_KAPAMA = "ACMA_KAPAMA", "Açma/Kapama"

    fatura = models.ForeignKey(
        Fatura, on_delete=models.CASCADE, related_name="kalemler"
    )
    tip = models.CharField(max_length=20, choices=KalemTip.choices)
    cihaz_plani = models.ForeignKey(
        CihazOdemePlani, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="fatura_kalemleri",
    )
    taksit_no = models.PositiveSmallIntegerField(null=True, blank=True)
    tutar = models.DecimalField(max_digits=12, decimal_places=2)
    aciklama = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "abonelik_fatura_kalemleri"
        ordering = ("id",)
        verbose_name = "Fatura Kalemi"
        verbose_name_plural = "Fatura Kalemleri"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.get_tip_display()} — {self.tutar} TL"


class SozlesmeTalebi(BaseModel):
    """Eczacının açtığı sözleşme talebi (yeni/uzatma/iptal). Admin onaylar."""

    class Tip(models.TextChoices):
        YENI = "YENI", "Yeni Sözleşme"
        UZATMA = "UZATMA", "Uzatma"
        IPTAL = "IPTAL", "İptal"

    class Durum(models.TextChoices):
        BEKLIYOR = "BEKLIYOR", "Bekliyor"
        ONAYLANDI = "ONAYLANDI", "Onaylandı"
        REDDEDILDI = "REDDEDILDI", "Reddedildi"

    eczane = models.ForeignKey(
        "pharmacies.Eczane", on_delete=models.PROTECT, related_name="sozlesme_talepleri"
    )
    talep_tipi = models.CharField(max_length=10, choices=Tip.choices, db_index=True)
    durum = models.CharField(
        max_length=12, choices=Durum.choices, default=Durum.BEKLIYOR, db_index=True
    )
    hedef_sozlesme = models.ForeignKey(
        Sozlesme, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="talepler", help_text="Uzatma/iptal için ilgili sözleşme.",
    )
    # İstenen parametreler (YENI/UZATMA)
    istenen_tur = models.CharField(
        max_length=10, choices=Sozlesme.Tur.choices, blank=True, default="",
    )
    istenen_tip_ay = models.PositiveSmallIntegerField(null=True, blank=True)
    istenen_demo_gun = models.PositiveSmallIntegerField(null=True, blank=True)
    ek_ay = models.PositiveSmallIntegerField(null=True, blank=True)
    ek_gun = models.PositiveSmallIntegerField(null=True, blank=True)
    aciklama = models.CharField(max_length=500, blank=True, default="")

    # Karar
    red_nedeni = models.CharField(max_length=500, blank=True, default="")
    karar_veren = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )
    karar_tarihi = models.DateTimeField(null=True, blank=True)
    # Onay sonucu oluşan sözleşme (YENI)
    olusan_sozlesme = models.ForeignKey(
        Sozlesme, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )

    class Meta:
        db_table = "abonelik_sozlesme_talepleri"
        ordering = ("-olusturulma_tarihi", "-id")
        verbose_name = "Sözleşme Talebi"
        verbose_name_plural = "Sözleşme Talepleri"

    def __str__(self) -> str:  # pragma: no cover
        return f"Talep #{self.pk} — {self.talep_tipi} ({self.durum})"
