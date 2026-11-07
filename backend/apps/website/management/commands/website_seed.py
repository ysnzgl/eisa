"""
python manage.py website_seed [--force]

eisa.com.tr CMS başlangıç içeriğini tohumlar (CONTRACT §9):
  - Site ayarları, 7 sayfa (hepsi yayınlanmış revizyonla), header/footer/footer_alt menüleri,
    3 blog kategorisi ve 3 yayınlanmış blog yazısı.
  - Idempotent: slug / konum bazlı upsert. Mevcut içeriğin üzerine yalnızca --force ile yazar.
  - Tüm bloklar registry doğrulamasından geçer; geçmezse komut hata verir.
"""
from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.core.uow import UnitOfWork
from apps.website import seed_icerik as icerik
from apps.website.blocks import bloklari_dogrula
from apps.website.guvenlik import html_temizle
from apps.website.models import BlogKategori, BlogYazisi, Menu, MenuOgesi, Sayfa, SiteAyarlari
from apps.website.services.blog import okuma_suresi_hesapla
from apps.website.services.menu import menu_dogrula, menu_kaydet
from apps.website.services.revalidate import revalidate
from apps.website.services.sayfa import bloklari_kaydet, sayfa_yayinla, sayfa_yeniden_yukle


class Command(BaseCommand):
    help = "eisa.com.tr web sitesi başlangıç içeriğini (sayfalar, menüler, ayarlar, blog) tohumlar."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Mevcut içeriğin üzerine yazar (sayfalar yeni revizyonla yeniden yayınlanır).",
        )

    def handle(self, *args, **options):
        force = options["force"]
        self.ozet = {"olusturulan": 0, "guncellenen": 0, "atlanan": 0}
        with transaction.atomic():
            self._ayarlar(force)
            kategoriler = self._kategoriler(force)
            self._yazilar(force, kategoriler)
            self._sayfalar(force)
            self._menuler(force)
            revalidate("site", "sayfalar", "blog", *[f"sayfa:{s['slug']}" for s in icerik.SAYFALAR])
        self.stdout.write(
            self.style.SUCCESS(
                "website_seed tamamlandı — oluşturulan: {olusturulan}, güncellenen: {guncellenen}, "
                "atlanan: {atlanan}".format(**self.ozet)
            )
        )

    # ── Yardımcılar ────────────────────────────────────────────────────────
    def _say(self, anahtar: str, mesaj: str):
        self.ozet[anahtar] += 1
        stil = {"olusturulan": self.style.SUCCESS, "guncellenen": self.style.WARNING}.get(anahtar, str)
        self.stdout.write(stil(f"  {mesaj}"))

    # ── Ayarlar ────────────────────────────────────────────────────────────
    def _ayarlar(self, force: bool):
        mevcut = SiteAyarlari.objects.filter(pk=SiteAyarlari.TEKIL_PK).first()
        if mevcut and not force:
            self._say("atlanan", "Site ayarları zaten var.")
            return
        ayarlar = mevcut or SiteAyarlari(pk=SiteAyarlari.TEKIL_PK)
        for k, v in icerik.AYARLAR.items():
            setattr(ayarlar, k, v)
        with UnitOfWork() as uow:
            if mevcut:
                uow.update(ayarlar)
                self._say("guncellenen", "Site ayarları güncellendi.")
            else:
                uow.add(ayarlar)
                self._say("olusturulan", "Site ayarları oluşturuldu.")

    # ── Blog ───────────────────────────────────────────────────────────────
    def _kategoriler(self, force: bool) -> dict[str, BlogKategori]:
        sonuc = {}
        for veri in icerik.BLOG_KATEGORILERI:
            kategori = BlogKategori.objects.filter(slug=veri["slug"]).first()
            with UnitOfWork() as uow:
                if kategori is None:
                    kategori = uow.add(BlogKategori(**veri))
                    self._say("olusturulan", f"Blog kategorisi: {veri['ad']}")
                elif force:
                    kategori.ad, kategori.sira = veri["ad"], veri["sira"]
                    uow.update(kategori)
                    self._say("guncellenen", f"Blog kategorisi: {veri['ad']}")
                else:
                    self._say("atlanan", f"Blog kategorisi zaten var: {veri['ad']}")
            sonuc[veri["slug"]] = kategori
        return sonuc

    def _yazilar(self, force: bool, kategoriler: dict[str, BlogKategori]):
        simdi = timezone.now()
        for veri in icerik.BLOG_YAZILARI:
            yazi = BlogYazisi.objects.filter(slug=veri["slug"]).first()
            if yazi is not None and not force:
                self._say("atlanan", f"Blog yazısı zaten var: {veri['slug']}")
                continue
            yeni = yazi is None
            yazi = yazi or BlogYazisi(slug=veri["slug"])
            yazi.baslik = veri["baslik"]
            yazi.ozet = veri["ozet"]
            yazi.kapak = None
            yazi.icerik_html = html_temizle(veri["icerik_html"])
            yazi.kategori = kategoriler.get(veri["kategori"])
            yazi.etiketler = veri["etiketler"]
            yazi.yazar_adi = icerik.BLOG_YAZAR
            yazi.durum = BlogYazisi.Durum.YAYINDA
            yazi.yayin_tarihi = yazi.yayin_tarihi or (simdi - timedelta(days=veri["gun_once"]))
            yazi.seo_baslik = ""
            yazi.seo_aciklama = veri["ozet"]
            yazi.okuma_suresi = okuma_suresi_hesapla(yazi.icerik_html)
            with UnitOfWork() as uow:
                if yeni:
                    uow.add(yazi)
                    self._say("olusturulan", f"Blog yazısı: {veri['slug']}")
                else:
                    uow.update(yazi)
                    self._say("guncellenen", f"Blog yazısı: {veri['slug']}")

    # ── Sayfalar ───────────────────────────────────────────────────────────
    def _sayfalar(self, force: bool):
        for veri in icerik.SAYFALAR:
            temiz, hatalar = bloklari_dogrula(veri["bloklar"])
            if hatalar:
                raise CommandError(f"'{veri['slug']}' sayfasının seed blokları geçersiz: {hatalar}")

            sayfa = Sayfa.objects.filter(slug=veri["slug"]).first()
            if sayfa is not None and not force:
                self._say("atlanan", f"Sayfa zaten var: {veri['slug']}")
                continue
            yeni = sayfa is None
            sayfa = sayfa or Sayfa(slug=veri["slug"])
            sayfa.baslik = veri["baslik"]
            sayfa.seo_baslik = veri["seo_baslik"]
            sayfa.seo_aciklama = veri["seo_aciklama"]
            sayfa.og_gorsel = None
            sayfa.sira = veri["sira"]
            with UnitOfWork() as uow:
                if yeni:
                    uow.add(sayfa)
                else:
                    uow.update(sayfa)
            bloklari_kaydet(sayfa, temiz, user=None, surum=sayfa.surum)
            sayfa_yayinla(
                sayfa_yeniden_yukle(sayfa.pk), user=None, not_metni="website_seed", revalidate_et=False
            )
            self._say("olusturulan" if yeni else "guncellenen", f"Sayfa (yayında): {veri['slug']}")

    # ── Menüler ────────────────────────────────────────────────────────────
    def _menuler(self, force: bool):
        sayfa_idleri = dict(Sayfa.objects.values_list("slug", "pk"))

        def donustur(oge: dict) -> dict:
            return {
                "etiket": oge["etiket"],
                "link_tipi": oge["link_tipi"],
                "sayfa_id": sayfa_idleri.get(oge["sayfa"]) if oge["sayfa"] else None,
                "bolum_anchor": oge["bolum_anchor"],
                "url": oge["url"],
                "yeni_sekme": False,
                "cta": oge["cta"],
                "aktif": True,
                "cocuklar": [donustur(c) for c in oge["cocuklar"]],
            }

        for konum, ogeler in icerik.MENULER.items():
            menu = Menu.objects.filter(konum=konum).first()
            if menu is not None and MenuOgesi.objects.filter(menu=menu).exists() and not force:
                self._say("atlanan", f"Menü zaten dolu: {konum}")
                continue
            temiz, hatalar = menu_dogrula([donustur(o) for o in ogeler])
            if hatalar:
                raise CommandError(f"'{konum}' menüsü geçersiz: {hatalar}")
            # --force: ağaç tamamen yeniden kurulur (id eşleştirmesi yapılmaz).
            menu_kaydet(konum, temiz, user=None, revalidate_et=False)
            self._say("olusturulan" if menu is None else "guncellenen", f"Menü: {konum}")
