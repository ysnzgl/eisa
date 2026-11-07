"""migrate sonrası otomatik başlangıç içeriği (post_migrate → website_seed)."""
import pytest
from django.test import override_settings

from apps.website.apps import baslangic_icerigini_yukle
from apps.website.models import BlogYazisi, Menu, MenuOgesi, Sayfa, SiteAyarlari


@pytest.mark.django_db
@override_settings(WEBSITE_AUTO_SEED=True)
def test_bos_veritabaninda_icerik_yuklenir(settings):
    settings.SITE_REVALIDATE_URLS = []
    assert not Sayfa.objects.exists()
    baslangic_icerigini_yukle(verbosity=0)
    assert Sayfa.objects.filter(slug="anasayfa", durum=Sayfa.Durum.YAYINDA).exists()
    assert Sayfa.objects.count() == 7
    assert SiteAyarlari.objects.exists()
    assert Menu.objects.filter(konum="header").exists()
    assert BlogYazisi.objects.count() == 3


@pytest.mark.django_db
@override_settings(WEBSITE_AUTO_SEED=True)
def test_mevcut_icerige_dokunmaz(settings):
    settings.SITE_REVALIDATE_URLS = []
    baslangic_icerigini_yukle(verbosity=0)
    ana = Sayfa.objects.get(slug="anasayfa")
    Sayfa.objects.filter(pk=ana.pk).update(baslik="Elle değiştirildi")
    MenuOgesi.objects.all().delete()  # menü öğeleri sayfaları korur (PROTECT)
    Sayfa.objects.exclude(pk=ana.pk).delete()

    baslangic_icerigini_yukle(verbosity=0)

    assert Sayfa.objects.count() == 1
    assert Sayfa.objects.get(pk=ana.pk).baslik == "Elle değiştirildi"


@pytest.mark.django_db
@override_settings(WEBSITE_AUTO_SEED=False)
def test_ayar_kapaliysa_yuklenmez():
    baslangic_icerigini_yukle(verbosity=0)
    assert not Sayfa.objects.exists()