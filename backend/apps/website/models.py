"""
Web sitesi (eisa.com.tr) CMS modelleri.

Sözleşme: docs/web-sitesi/CONTRACT.md. Tüm tablolar `website_*` önekiyle
BaseModel'den türer; yazmalar `apps.core.uow.UnitOfWork` üzerinden yapılır.

Önemli tasarım notları:
  - `Blok` kayıtları sayfanın düzenlenen TASLAK hâlidir.
  - "Yayınla" taslağın değişmez kopyasını `SayfaRevizyon.bloklar_snapshot`
    içine yazar; public API yalnızca aktif revizyonu okur.
  - MediaRef (`og_gorsel`, `kapak`, blok içi görseller) JSON nesne olarak saklanır;
    kayıt sırasında `id` doğrulanır ve diğer alanlar DB'den tazelenir.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class SiteAyarlari(BaseModel):
    """Singleton site ayarları (pk=1). Footer, iletişim ve varsayılan SEO buradan beslenir."""

    TEKIL_PK = 1

    site_adi = models.CharField(max_length=100, default="e-isa")
    seo_baslik_sablonu = models.CharField(max_length=160, default="%s | e-isa")
    seo_aciklama = models.TextField(blank=True, default="")
    og_gorsel = models.JSONField(null=True, blank=True)
    eposta = models.EmailField(blank=True, default="")
    telefon = models.CharField(max_length=30, blank=True, default="")
    whatsapp = models.CharField(max_length=30, blank=True, default="")
    adres = models.TextField(blank=True, default="")
    firma_unvani = models.CharField(max_length=200, blank=True, default="")
    footer_aciklama = models.TextField(blank=True, default="")
    sosyal_linkler = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "website_site_ayarlari"
        verbose_name = "Site Ayarları"
        verbose_name_plural = "Site Ayarları"

    def __str__(self) -> str:  # pragma: no cover
        return self.site_adi

    @classmethod
    def getir(cls) -> "SiteAyarlari":
        """Singleton kaydı döndürür; yoksa (kaydetmeden) varsayılanlarla üretir."""
        obj = cls.objects.filter(pk=cls.TEKIL_PK).first()
        return obj or cls(pk=cls.TEKIL_PK)


class Sayfa(BaseModel):
    class Durum(models.TextChoices):
        TASLAK = "taslak", "Taslak"
        YAYINDA = "yayinda", "Yayında"
        ARSIV = "arsiv", "Arşiv"

    slug = models.SlugField(max_length=100, unique=True)
    baslik = models.CharField(max_length=200)
    seo_baslik = models.CharField(max_length=200, blank=True, default="")
    seo_aciklama = models.TextField(blank=True, default="")
    og_gorsel = models.JSONField(null=True, blank=True)
    durum = models.CharField(max_length=16, choices=Durum.choices, default=Durum.TASLAK, db_index=True)
    aktif_revizyon = models.ForeignKey(
        "website.SayfaRevizyon",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    yayin_tarihi = models.DateTimeField(null=True, blank=True)
    sira = models.IntegerField(default=0)

    class Meta:
        db_table = "website_sayfalar"
        ordering = ("sira", "id")
        verbose_name = "Sayfa"
        verbose_name_plural = "Sayfalar"

    def __str__(self) -> str:  # pragma: no cover
        return self.slug


class Blok(BaseModel):
    """Sayfanın taslak blokları. `veri` blok tipi şemasına göre normalize edilmiş JSON'dur."""

    sayfa = models.ForeignKey(Sayfa, on_delete=models.CASCADE, related_name="bloklar")
    tip = models.CharField(max_length=40)
    veri = models.JSONField(default=dict, blank=True)
    sira = models.IntegerField(default=0)
    gorunur = models.BooleanField(default=True)
    anchor_id = models.CharField(max_length=60, blank=True, default="")

    class Meta:
        db_table = "website_bloklar"
        ordering = ("sira", "id")
        verbose_name = "Blok"
        verbose_name_plural = "Bloklar"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.sayfa_id}:{self.tip}#{self.sira}"


class SayfaRevizyon(BaseModel):
    """Yayınlanmış sayfa anlık görüntüsü (değişmez)."""

    sayfa = models.ForeignKey(Sayfa, on_delete=models.CASCADE, related_name="revizyonlar")
    # [{"id": "b_12", "tip", "anchor_id", "veri", "gorunur", "sira"}]
    bloklar_snapshot = models.JSONField(default=list)
    # {"baslik", "seo_baslik", "seo_aciklama", "og_gorsel"}
    seo_snapshot = models.JSONField(default=dict)
    yayinlayan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    yayin_tarihi = models.DateTimeField()
    not_metni = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        db_table = "website_sayfa_revizyonlari"
        ordering = ("-yayin_tarihi", "-id")
        verbose_name = "Sayfa Revizyonu"
        verbose_name_plural = "Sayfa Revizyonları"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.sayfa_id}@{self.yayin_tarihi:%Y-%m-%d %H:%M}"


class Menu(BaseModel):
    class Konum(models.TextChoices):
        HEADER = "header", "Header"
        FOOTER = "footer", "Footer"
        FOOTER_ALT = "footer_alt", "Footer Alt"

    konum = models.CharField(max_length=20, choices=Konum.choices, unique=True)

    class Meta:
        db_table = "website_menuler"
        verbose_name = "Menü"
        verbose_name_plural = "Menüler"

    def __str__(self) -> str:  # pragma: no cover
        return self.konum


class MenuOgesi(BaseModel):
    class LinkTipi(models.TextChoices):
        SAYFA = "sayfa", "Sayfa"
        BOLUM = "bolum", "Bölüm"
        BLOG = "blog", "Blog"
        DIS = "dis", "Dış Link"

    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name="ogeler")
    ust = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="cocuklar")
    etiket = models.CharField(max_length=100)
    link_tipi = models.CharField(max_length=10, choices=LinkTipi.choices)
    # Menüde kullanılan sayfa silinemez (API 400 döner; PROTECT son savunma hattı).
    sayfa = models.ForeignKey(Sayfa, null=True, blank=True, on_delete=models.PROTECT, related_name="menu_ogeleri")
    bolum_anchor = models.CharField(max_length=60, blank=True, default="")
    url = models.CharField(max_length=500, blank=True, default="")
    yeni_sekme = models.BooleanField(default=False)
    cta = models.BooleanField(default=False)
    sira = models.IntegerField(default=0)
    aktif = models.BooleanField(default=True)

    class Meta:
        db_table = "website_menu_ogeleri"
        ordering = ("sira", "id")
        verbose_name = "Menü Öğesi"
        verbose_name_plural = "Menü Öğeleri"

    def __str__(self) -> str:  # pragma: no cover
        return self.etiket


class BlogKategori(BaseModel):
    ad = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    sira = models.IntegerField(default=0)

    class Meta:
        db_table = "website_blog_kategorileri"
        ordering = ("sira", "ad")
        verbose_name = "Blog Kategorisi"
        verbose_name_plural = "Blog Kategorileri"

    def __str__(self) -> str:  # pragma: no cover
        return self.ad


class BlogYazisi(BaseModel):
    class Durum(models.TextChoices):
        TASLAK = "taslak", "Taslak"
        YAYINDA = "yayinda", "Yayında"
        ARSIV = "arsiv", "Arşiv"

    slug = models.SlugField(max_length=160, unique=True)
    baslik = models.CharField(max_length=200)
    ozet = models.TextField(blank=True, default="")
    kapak = models.JSONField(null=True, blank=True)
    icerik_html = models.TextField(blank=True, default="")
    kategori = models.ForeignKey(
        BlogKategori, null=True, blank=True, on_delete=models.SET_NULL, related_name="yazilar"
    )
    etiketler = models.JSONField(default=list, blank=True)
    yazar_adi = models.CharField(max_length=100, blank=True, default="")
    durum = models.CharField(max_length=16, choices=Durum.choices, default=Durum.TASLAK, db_index=True)
    yayin_tarihi = models.DateTimeField(null=True, blank=True, db_index=True)
    seo_baslik = models.CharField(max_length=200, blank=True, default="")
    seo_aciklama = models.TextField(blank=True, default="")
    okuma_suresi = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "website_blog_yazilari"
        ordering = ("-yayin_tarihi", "-id")
        verbose_name = "Blog Yazısı"
        verbose_name_plural = "Blog Yazıları"

    def __str__(self) -> str:  # pragma: no cover
        return self.baslik


class WebsiteMedya(BaseModel):
    """Site görselleri. Nesne anahtarı: website/YYYY/MM/<uuid>.<ext>"""

    object_key = models.CharField(max_length=255, unique=True)
    dosya_adi = models.CharField(max_length=255, blank=True, default="")
    mime = models.CharField(max_length=50)
    boyut = models.PositiveIntegerField(default=0)
    genislik = models.PositiveIntegerField(null=True, blank=True)
    yukseklik = models.PositiveIntegerField(null=True, blank=True)
    alt = models.CharField(max_length=300, blank=True, default="")

    class Meta:
        db_table = "website_medya"
        ordering = ("-olusturulma_tarihi", "-id")
        verbose_name = "Web Sitesi Medyası"
        verbose_name_plural = "Web Sitesi Medyaları"

    def __str__(self) -> str:  # pragma: no cover
        return self.object_key

    @property
    def yol(self) -> str:
        return f"/api/media/{self.object_key}"

    def media_ref(self) -> dict:
        return {
            "id": self.pk,
            "yol": self.yol,
            "alt": self.alt,
            "genislik": self.genislik,
            "yukseklik": self.yukseklik,
            "mime": self.mime,
        }


class Basvuru(BaseModel):
    """Site formlarından gelen başvurular (pilot / sponsor / genel). IP ham saklanmaz."""

    class Tip(models.TextChoices):
        PILOT = "pilot", "Pilot"
        SPONSOR = "sponsor", "Sponsor"
        GENEL = "genel", "Genel"

    class Durum(models.TextChoices):
        YENI = "yeni", "Yeni"
        INCELENDI = "incelendi", "İncelendi"
        ILETISIMDE = "iletisimde", "İletişimde"
        KAPANDI = "kapandi", "Kapandı"

    tip = models.CharField(max_length=16, choices=Tip.choices, default=Tip.GENEL, db_index=True)
    ad_soyad = models.CharField(max_length=150)
    kurum = models.CharField(max_length=200, blank=True, default="")
    eposta = models.EmailField()
    telefon = models.CharField(max_length=20, blank=True, default="")
    il = models.CharField(max_length=60, blank=True, default="")
    mesaj = models.TextField(blank=True, default="")
    kvkk_onay = models.BooleanField(default=False)
    kvkk_metin_versiyonu = models.CharField(max_length=60, blank=True, default="")
    kaynak_sayfa = models.CharField(max_length=300, blank=True, default="")
    ip_hash = models.CharField(max_length=64, blank=True, default="")
    durum = models.CharField(max_length=16, choices=Durum.choices, default=Durum.YENI, db_index=True)
    atanan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="website_basvurulari",
    )
    notlar = models.TextField(blank=True, default="")
    # İleride SMTP bildirimi eklendiğinde kullanılacak (CONTRACT §0: şimdilik SMTP yok).
    bildirim_gonderildi = models.BooleanField(default=False)

    class Meta:
        db_table = "website_basvurular"
        ordering = ("-olusturulma_tarihi", "-id")
        verbose_name = "Başvuru"
        verbose_name_plural = "Başvurular"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tip}: {self.ad_soyad}"
