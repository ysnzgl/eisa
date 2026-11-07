"""Web sitesi URL'leri — core_api/urls.py içinde `api/website/` altına bağlanır (CONTRACT §3-§5)."""
from django.urls import path

from .views import admin as a
from .views import preview as p
from .views import public as pub

public_urls = [
    path("public/site/", pub.PublicSiteView.as_view(), name="website-public-site"),
    path("public/sayfalar/", pub.PublicSayfalarView.as_view(), name="website-public-sayfalar"),
    path("public/sayfalar/<slug:slug>/", pub.PublicSayfaDetayView.as_view(), name="website-public-sayfa"),
    path("public/blog/", pub.PublicBlogListeView.as_view(), name="website-public-blog"),
    path("public/blog/<slug:slug>/", pub.PublicBlogDetayView.as_view(), name="website-public-blog-detay"),
    path("public/basvurular/", pub.PublicBasvuruView.as_view(), name="website-public-basvuru"),
]

preview_urls = [
    path("preview/sayfalar/<slug:slug>/", p.PreviewSayfaView.as_view(), name="website-preview-sayfa"),
    path("preview/blog/<slug:slug>/", p.PreviewBlogView.as_view(), name="website-preview-blog"),
]

admin_urls = [
    path("admin/ayarlar/", a.AyarlarView.as_view(), name="website-admin-ayarlar"),
    path("admin/blok-tipleri/", a.BlokTipleriView.as_view(), name="website-admin-blok-tipleri"),
    path("admin/arama/", a.AramaView.as_view(), name="website-admin-arama"),
    path("admin/menuler/", a.MenulerView.as_view(), name="website-admin-menuler"),
    path("admin/menuler/<str:konum>/", a.MenuKonumView.as_view(), name="website-admin-menu"),
    path("admin/sayfalar/", a.SayfalarView.as_view(), name="website-admin-sayfalar"),
    path("admin/sayfalar/<int:pk>/", a.SayfaDetayView.as_view(), name="website-admin-sayfa"),
    path("admin/sayfalar/<int:pk>/bloklar/", a.SayfaBloklarView.as_view(), name="website-admin-sayfa-bloklar"),
    path("admin/sayfalar/<int:pk>/yayinla/", a.SayfaYayinlaView.as_view(), name="website-admin-sayfa-yayinla"),
    path("admin/sayfalar/<int:pk>/yayindan-kaldir/", a.SayfaYayindanKaldirView.as_view(), name="website-admin-sayfa-yayindan-kaldir"),
    path("admin/sayfalar/<int:pk>/revizyonlar/", a.SayfaRevizyonlarView.as_view(), name="website-admin-sayfa-revizyonlar"),
    path(
        "admin/sayfalar/<int:pk>/revizyonlar/<int:rid>/geri-al/",
        a.RevizyonGeriAlView.as_view(),
        name="website-admin-revizyon-geri-al",
    ),
    path("admin/sayfalar/<int:pk>/onizleme/", a.SayfaOnizlemeView.as_view(), name="website-admin-sayfa-onizleme"),
    path("admin/blog/kategoriler/", a.BlogKategorilerView.as_view(), name="website-admin-blog-kategoriler"),
    path("admin/blog/kategoriler/<int:pk>/", a.BlogKategoriDetayView.as_view(), name="website-admin-blog-kategori"),
    path("admin/blog/yazilar/", a.BlogYazilarView.as_view(), name="website-admin-blog-yazilar"),
    path("admin/blog/yazilar/<int:pk>/", a.BlogYaziDetayView.as_view(), name="website-admin-blog-yazi"),
    path("admin/blog/yazilar/<int:pk>/onizleme/", a.BlogYaziOnizlemeView.as_view(), name="website-admin-blog-yazi-onizleme"),
    path("admin/medya/", a.MedyaView.as_view(), name="website-admin-medya"),
    path("admin/medya/<int:pk>/", a.MedyaDetayView.as_view(), name="website-admin-medya-detay"),
    path("admin/basvurular/", a.BasvurularView.as_view(), name="website-admin-basvurular"),
    path("admin/basvurular/ozet/", a.BasvuruOzetView.as_view(), name="website-admin-basvurular-ozet"),
    path("admin/basvurular/<int:pk>/", a.BasvuruDetayView.as_view(), name="website-admin-basvuru"),
]

urlpatterns = public_urls + preview_urls + admin_urls
