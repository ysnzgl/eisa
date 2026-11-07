import io
import logging

from django.apps import AppConfig
from django.core import checks
from django.db.models.signals import post_migrate

logger = logging.getLogger("eisa.website")


def baslangic_icerigini_yukle(sender=None, using="default", verbosity=1, **kwargs):
    """migrate sonrası: site içeriği hiç yoksa (ayar ve sayfa yok) başlangıç içeriğini yükler.

    Mevcut içeriğe asla dokunmaz; sayfalar bilerek silinmişse de (ayarlar durduğu için) geri getirmez.
    WEBSITE_AUTO_SEED=False ile kapatılır (testler).
    """
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connections

    if not getattr(settings, "WEBSITE_AUTO_SEED", True) or using != "default":
        return

    from apps.website.models import Sayfa, SiteAyarlari

    tablolar = connections[using].introspection.table_names()
    if Sayfa._meta.db_table not in tablolar or SiteAyarlari._meta.db_table not in tablolar:
        return  # web sitesi tabloları henüz oluşmadı (kısmi migrate)
    if SiteAyarlari.objects.using(using).exists() or Sayfa.objects.using(using).exists():
        return

    if verbosity:
        print("Web sitesi başlangıç içeriği yükleniyor (website_seed)…")
    call_command("website_seed", stdout=None if verbosity else io.StringIO())
    logger.info("website_baslangic_icerigi_yuklendi")


_DEV_DEGERLER = {"WEBSITE_SERVER_TOKEN": "dev-website-token", "REVALIDATE_SECRET": "dev-revalidate-secret"}


def uretim_anahtarlari_kontrolu(app_configs=None, **kwargs):
    """Üretimde (DEBUG=False) site ↔ API anahtarları varsayılan/boş ise uyarı verir.

    API'yi durdurmaz (kiosk trafiği etkilenmesin); bu durumda site uçları 404 döner (fail-closed).
    """
    from django.conf import settings

    if settings.DEBUG:
        return []
    uyarilar = []
    for ad, dev in _DEV_DEGERLER.items():
        deger = getattr(settings, ad, "") or ""
        if not deger or deger == dev or len(deger) < 32:
            uyarilar.append(
                checks.Warning(
                    f"{ad} üretim için ayarlanmamış (boş, varsayılan veya 32 karakterden kısa).",
                    hint="eisa-app-secrets içinde site ile aynı, rastgele ≥32 karakterlik değer verin.",
                    id=f"website.W00{len(uyarilar) + 1}",
                )
            )
    return uyarilar


class WebsiteConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.website"
    verbose_name = "Web Sitesi"

    def ready(self):
        post_migrate.connect(baslangic_icerigini_yukle, sender=self, dispatch_uid="website-baslangic-icerigi")
        checks.register(uretim_anahtarlari_kontrolu, checks.Tags.security, deploy=False)