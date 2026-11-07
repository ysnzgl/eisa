"""Web sitesi DRF serileştiricileri (admin + public başvuru)."""
from __future__ import annotations

import re

from rest_framework import serializers

from apps.users.models import Kullanici

from .blocks import Dogrulayici
from .guvenlik import html_temizle
from .models import Basvuru, BlogKategori, BlogYazisi, Sayfa, SiteAyarlari, WebsiteMedya
from .services.sayfa import AYRILMIS_SLUGLAR, KORUNAN_SLUGLAR
from .yardimcilar import SLUG_RE, tr_slugify


class MediaRefField(serializers.Field):
    """MediaRef|null — `id` DB'de doğrulanır, diğer alanlar DB'den tazelenir (CONTRACT §2)."""

    def __init__(self, **kwargs):
        kwargs.setdefault("allow_null", True)
        kwargs.setdefault("required", False)
        super().__init__(**kwargs)

    def validate_empty_values(self, data):
        if data is None or data == "" or data == {}:
            return True, None
        return super().validate_empty_values(data)

    def to_internal_value(self, data):
        temiz, hata = Dogrulayici().medya_ref(data)
        if hata:
            raise serializers.ValidationError(hata)
        return temiz

    def to_representation(self, value):
        return value


def _slug_dogrula(value: str) -> str:
    value = (value or "").strip()
    if not SLUG_RE.match(value):
        raise serializers.ValidationError("Yalnızca küçük harf, rakam ve tire kullanılabilir.")
    return value


# ── Ayarlar ─────────────────────────────────────────────────────────────────

SOSYAL_PLATFORMLAR = ("linkedin", "instagram", "x", "youtube", "facebook")


class SiteAyarlariSerializer(serializers.ModelSerializer):
    og_gorsel = MediaRefField()
    sosyal_linkler = serializers.JSONField(required=False)

    class Meta:
        model = SiteAyarlari
        fields = (
            "site_adi", "seo_baslik_sablonu", "seo_aciklama", "og_gorsel", "eposta", "telefon",
            "whatsapp", "adres", "firma_unvani", "footer_aciklama", "sosyal_linkler",
        )

    def validate_seo_baslik_sablonu(self, value):
        if "%s" not in value:
            raise serializers.ValidationError("Şablon sayfa başlığı için '%s' içermelidir.")
        return value

    def validate_whatsapp(self, value):
        value = (value or "").strip()
        if value and not re.match(r"^\+?[0-9 ()\-]{7,20}$", value):
            raise serializers.ValidationError("Telefon numarası biçiminde olmalıdır (ör. +90 555 000 00 00).")
        return value

    def validate_telefon(self, value):
        return self.validate_whatsapp(value)

    def validate_sosyal_linkler(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Liste olmalıdır.")
        if len(value) > 10:
            raise serializers.ValidationError("En fazla 10 bağlantı eklenebilir.")
        temiz, hatalar = [], {}
        for i, oge in enumerate(value):
            h = {}
            if not isinstance(oge, dict):
                hatalar[str(i)] = {"non_field_errors": ["Geçersiz öğe."]}
                continue
            platform = oge.get("platform")
            url = (oge.get("url") or "").strip() if isinstance(oge.get("url"), str) else ""
            if platform not in SOSYAL_PLATFORMLAR:
                h["platform"] = ["Geçersiz platform."]
            if not url.lower().startswith("https://") or len(url) > 300 or any(c.isspace() for c in url):
                h["url"] = ["Geçerli bir https:// adresi girin."]
            if h:
                hatalar[str(i)] = h
            temiz.append({"platform": platform, "url": url})
        if hatalar:
            raise serializers.ValidationError(hatalar)
        return temiz


# ── Sayfa meta ──────────────────────────────────────────────────────────────


class SayfaMetaSerializer(serializers.ModelSerializer):
    og_gorsel = MediaRefField()

    class Meta:
        model = Sayfa
        fields = ("slug", "baslik", "seo_baslik", "seo_aciklama", "og_gorsel", "sira")
        extra_kwargs = {"slug": {"validators": []}}

    def validate_slug(self, value):
        value = _slug_dogrula(value)
        if value in AYRILMIS_SLUGLAR:
            raise serializers.ValidationError("Bu adres ayrılmıştır, kullanılamaz.")
        qs = Sayfa.objects.filter(slug=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
            if self.instance.slug in KORUNAN_SLUGLAR and value != self.instance.slug:
                raise serializers.ValidationError("Bu sayfanın adresi değiştirilemez.")
        if qs.exists():
            raise serializers.ValidationError("Bu adres başka bir sayfada kullanılıyor.")
        return value


# ── Blog ────────────────────────────────────────────────────────────────────


class BlogKategoriSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(max_length=100, required=False, allow_blank=True)

    class Meta:
        model = BlogKategori
        fields = ("id", "ad", "slug", "sira")
        read_only_fields = ("id",)

    def validate(self, attrs):
        ad = attrs.get("ad", getattr(self.instance, "ad", ""))
        slug = attrs.get("slug")
        if slug is not None or self.instance is None:
            slug = _slug_dogrula(slug) if slug else tr_slugify(ad)
            if not slug:
                raise serializers.ValidationError({"slug": ["Bu alan zorunludur."]})
            qs = BlogKategori.objects.filter(slug=slug)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"slug": ["Bu adres başka bir kategoride kullanılıyor."]})
            attrs["slug"] = slug
        return attrs


class BlogYaziListeSerializer(serializers.ModelSerializer):
    kategori = serializers.SerializerMethodField()

    class Meta:
        model = BlogYazisi
        fields = ("id", "slug", "baslik", "durum", "kategori", "yayin_tarihi", "guncellenme_tarihi")

    def get_kategori(self, obj):
        return {"id": obj.kategori_id, "ad": obj.kategori.ad} if obj.kategori_id else None


class BlogYaziSerializer(serializers.ModelSerializer):
    kapak = MediaRefField()
    kategori_id = serializers.PrimaryKeyRelatedField(
        source="kategori", queryset=BlogKategori.objects.all(), allow_null=True, required=False
    )
    etiketler = serializers.JSONField(required=False)
    slug = serializers.CharField(max_length=160, required=False, allow_blank=True)
    surum = serializers.IntegerField(required=False)

    class Meta:
        model = BlogYazisi
        fields = (
            "id", "slug", "baslik", "ozet", "kapak", "icerik_html", "kategori_id", "etiketler",
            "yazar_adi", "durum", "yayin_tarihi", "seo_baslik", "seo_aciklama", "okuma_suresi", "surum",
        )
        read_only_fields = ("id", "okuma_suresi")

    def validate_icerik_html(self, value):
        return html_temizle(value or "")

    def validate_ozet(self, value):
        value = (value or "").strip()
        if len(value) > 500:
            raise serializers.ValidationError("En fazla 500 karakter olabilir.")
        return value

    def validate_etiketler(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Liste olmalıdır.")
        temiz = []
        for e in value:
            if not isinstance(e, str):
                raise serializers.ValidationError("Etiketler metin olmalıdır.")
            e = " ".join(e.split())
            if not e:
                continue
            if len(e) > 40:
                raise serializers.ValidationError("Bir etiket en fazla 40 karakter olabilir.")
            if e not in temiz:
                temiz.append(e)
        if len(temiz) > 10:
            raise serializers.ValidationError("En fazla 10 etiket eklenebilir.")
        return temiz

    def validate(self, attrs):
        baslik = attrs.get("baslik", getattr(self.instance, "baslik", ""))
        if "slug" in attrs or self.instance is None:
            slug = attrs.get("slug") or ""
            slug = _slug_dogrula(slug) if slug else tr_slugify(baslik)
            if not slug:
                raise serializers.ValidationError({"slug": ["Bu alan zorunludur."]})
            qs = BlogYazisi.objects.filter(slug=slug)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"slug": ["Bu adres başka bir yazıda kullanılıyor."]})
            attrs["slug"] = slug
        return attrs


# ── Medya ───────────────────────────────────────────────────────────────────


class MedyaSerializer(serializers.ModelSerializer):
    yol = serializers.CharField(read_only=True)

    class Meta:
        model = WebsiteMedya
        fields = ("id", "yol", "alt", "genislik", "yukseklik", "mime", "dosya_adi", "boyut", "olusturulma_tarihi")
        read_only_fields = ("id", "yol", "genislik", "yukseklik", "mime", "dosya_adi", "boyut", "olusturulma_tarihi")


# ── Başvuru ─────────────────────────────────────────────────────────────────


class BasvuruPublicSerializer(serializers.Serializer):
    """POST public/basvurular/ (CONTRACT §3). `website` honeypot alanıdır."""

    tip = serializers.ChoiceField(choices=Basvuru.Tip.choices, default=Basvuru.Tip.GENEL)
    ad_soyad = serializers.CharField(max_length=150)
    kurum = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    eposta = serializers.EmailField(max_length=254)
    telefon = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    il = serializers.CharField(max_length=60, required=False, allow_blank=True, default="")
    mesaj = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")
    kvkk_onay = serializers.BooleanField()
    kaynak_sayfa = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")
    website = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_kvkk_onay(self, value):
        if value is not True:
            raise serializers.ValidationError("KVKK aydınlatma metnini onaylamanız gerekmektedir.")
        return value

    def validate_telefon(self, value):
        value = (value or "").strip()
        if value and not re.match(r"^\+?[0-9 ()\-]{0,20}$", value):
            raise serializers.ValidationError("Geçerli bir telefon numarası girin.")
        return value

    def validate_kaynak_sayfa(self, value):
        value = (value or "").strip()
        # Yalnızca site içi yol saklanır.
        return value if value.startswith("/") and not value.startswith("//") else ""


class BasvuruSerializer(serializers.ModelSerializer):
    atanan = serializers.SerializerMethodField()
    atanan_id = serializers.PrimaryKeyRelatedField(
        source="atanan",
        queryset=Kullanici.objects.filter(is_active=True, rol__in=(Kullanici.Rol.SUPERADMIN, Kullanici.Rol.EDITOR)),
        allow_null=True,
        required=False,
        write_only=True,
    )

    class Meta:
        model = Basvuru
        fields = (
            "id", "tip", "ad_soyad", "kurum", "eposta", "telefon", "il", "mesaj", "kvkk_onay",
            "kvkk_metin_versiyonu", "kaynak_sayfa", "durum", "notlar", "atanan", "atanan_id",
            "olusturulma_tarihi",
        )
        read_only_fields = (
            "id", "tip", "ad_soyad", "kurum", "eposta", "telefon", "il", "mesaj", "kvkk_onay",
            "kvkk_metin_versiyonu", "kaynak_sayfa", "olusturulma_tarihi",
        )

    def get_atanan(self, obj):
        if not obj.atanan_id:
            return None
        u = obj.atanan
        return {"id": u.pk, "ad": f"{u.first_name} {u.last_name}".strip() or u.username}

    def validate_notlar(self, value):
        if len(value or "") > 5000:
            raise serializers.ValidationError("En fazla 5000 karakter olabilir.")
        return value
