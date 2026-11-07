"""Django admin kayıtları (salt destek amaçlı; asıl yönetim portaldaki Web Sitesi modülündedir)."""
from django.contrib import admin

from .models import Basvuru, BlogKategori, BlogYazisi, Menu, MenuOgesi, Sayfa, SayfaRevizyon, SiteAyarlari, WebsiteMedya


@admin.register(Sayfa)
class SayfaAdmin(admin.ModelAdmin):
    list_display = ("slug", "baslik", "durum", "yayin_tarihi", "surum")
    list_filter = ("durum",)
    search_fields = ("slug", "baslik")
    readonly_fields = ("aktif_revizyon", "surum")


@admin.register(SayfaRevizyon)
class SayfaRevizyonAdmin(admin.ModelAdmin):
    list_display = ("sayfa", "yayin_tarihi", "yayinlayan", "not_metni")
    list_filter = ("sayfa",)


@admin.register(MenuOgesi)
class MenuOgesiAdmin(admin.ModelAdmin):
    list_display = ("etiket", "menu", "ust", "link_tipi", "sira", "aktif")
    list_filter = ("menu",)


@admin.register(BlogYazisi)
class BlogYazisiAdmin(admin.ModelAdmin):
    list_display = ("baslik", "durum", "kategori", "yayin_tarihi")
    list_filter = ("durum", "kategori")
    search_fields = ("baslik", "slug")


@admin.register(Basvuru)
class BasvuruAdmin(admin.ModelAdmin):
    list_display = ("ad_soyad", "tip", "durum", "eposta", "olusturulma_tarihi")
    list_filter = ("tip", "durum")
    search_fields = ("ad_soyad", "eposta", "kurum")
    readonly_fields = ("ip_hash",)


admin.site.register(SiteAyarlari)
admin.site.register(Menu)
admin.site.register(BlogKategori)
admin.site.register(WebsiteMedya)
