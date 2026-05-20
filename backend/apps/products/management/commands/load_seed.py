"""
Django management komutu: master_seed.json (yeni duz format) dosyasini
Kategori / Soru / EtkenMadde tablolarina yukler.

Yeni master_seed.json formati (duz, satirlik):
  [
    {
      "ana_kategori": "Enerji & Uyku",
      "ana_ikon":     "fa-solid fa-bolt",
      "alt_kategori": "Yorgunluk",
      "alt_ikon":     "fa-solid fa-battery-quarter",
      "soru":         "...",
      "cinsiyet":     "Tuemu",   // "Kadin" | "Erkek" | "Tuemu"
      "yas_grubu":    "18-120",  // e.g. "18-49", "40-120"
      "asil_takviye": "...",
      "destekleyici": "...",
      "tamamlayici":  "..."
    }
  ]

--flush ile mevcut Kategori/Soru/SoruEtkenMadde verileri temizlenir (onerilir).
"""
import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.lookups.models import Cinsiyet, YasAraligi
from apps.products.models import EtkenMadde, Kategori, Soru, SoruEtkenMadde

_TR_MAP = str.maketrans("guesiocIGUSOC", "guesiocigusoc")
_TR_MAP2 = str.maketrans(
    "\u011f\u00fc\u015f\u0131\u00f6\u00e7\u0130\u011e\u00dc\u015e\u00d6\u00c7",
    "gusiocigusoc",
)


def _slugify_tr(text: str) -> str:
    t = text.translate(_TR_MAP2)
    t = t.lower()
    t = re.sub(r"[/\\|]+", "-", t)
    t = re.sub(r"[^\w\s-]", "", t)
    t = re.sub(r"[\s_]+", "-", t)
    t = re.sub(r"-+", "-", t)
    return t.strip("-")


def _yas_araligini_bul(yas_araliklari: list, yas_grubu: str) -> list:
    """'18-49' gibi aralik stringini YasAraligi nesneleri listesine donusturur."""
    parts = yas_grubu.split("-")
    try:
        ymin = int(parts[0])
        ymax = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 9999
    except (ValueError, IndexError):
        return list(yas_araliklari)
    return [
        ya for ya in yas_araliklari
        if ya.alt_sinir <= ymax
        and (ya.ust_sinir is None or ya.ust_sinir >= ymin)
    ]


class Command(BaseCommand):
    help = "Yeni duz format master_seed.json dosyasini veritabanina yukler."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", type=str, default=None,
            help="Seed JSON dosyasi yolu (varsayilan: monorepo koku/master_seed.json).",
        )
        parser.add_argument(
            "--flush", action="store_true", default=False,
            help="Mevcut Kategori/Soru verilerini temizle (onerilir).",
        )

    def handle(self, *args, **options):
        if options["file"]:
            seed_path = Path(options["file"])
        else:
            base = Path(__file__).resolve().parents[5]
            seed_path = base / "master_seed.json"

        if not seed_path.exists():
            raise CommandError(f"Seed dosyasi bulunamadi: {seed_path}")

        with seed_path.open(encoding="utf-8") as f:
            seed_data = json.load(f)

        self.stdout.write(f"Seed: {seed_path}  ({len(seed_data)} satir)")

        cinsiyetler = {c.kod: c for c in Cinsiyet.objects.all()}
        yas_araliklari = list(YasAraligi.objects.all())

        if not cinsiyetler:
            raise CommandError(
                "Cinsiyet lookup tablosu bos. Once 'seed_lookups' calistirin."
            )
        if not yas_araliklari:
            raise CommandError(
                "YasAraligi lookup tablosu bos. Once 'seed_lookups' calistirin."
            )

        if not options["flush"] and Soru.objects.exists():
            raise CommandError(
                "Sorular tablosu dolu. Tekrar yuklemek icin --flush kullanin."
            )

        with transaction.atomic():
            if options["flush"]:
                SoruEtkenMadde.objects.all().delete()
                Soru.objects.all().delete()
                Kategori.objects.all().delete()
                self.stdout.write("  -> Mevcut Kategori/Soru verileri temizlendi.")

            ana_kat_cache: dict = {}   # slug -> Kategori
            alt_kat_cache: dict = {}   # slug -> Kategori
            sira_sayac: dict   = {}    # alt_slug -> int
            kat_yas_ids: dict  = {}    # slug -> set of YasAraligi.pk

            stats = {"ana_kat": 0, "alt_kat": 0, "soru": 0, "em": 0}

            for entry in seed_data:

                # ── Ana kategori ──────────────────────────────────────────
                ana_ad   = entry["ana_kategori"]
                ana_ikon = entry.get("ana_ikon", "fa-circle")
                ana_slug = _slugify_tr(ana_ad)

                if ana_slug not in ana_kat_cache:
                    kat, created = Kategori.objects.get_or_create(
                        slug=ana_slug,
                        defaults={"ad": ana_ad, "ikon": ana_ikon, "aktif": True},
                    )
                    if created:
                        stats["ana_kat"] += 1
                    ana_kat_cache[ana_slug] = kat
                    kat_yas_ids.setdefault(ana_slug, set())

                ana_kat = ana_kat_cache[ana_slug]

                # ── Alt kategori ──────────────────────────────────────────
                alt_ad   = entry["alt_kategori"]
                alt_ikon = entry.get("alt_ikon", "fa-circle")
                alt_slug = _slugify_tr(alt_ad)

                if alt_slug not in alt_kat_cache:
                    kat, created = Kategori.objects.get_or_create(
                        slug=alt_slug,
                        defaults={
                            "ad": alt_ad,
                            "ikon": alt_ikon,
                            "aktif": True,
                            "bagli_kategori": ana_kat,
                        },
                    )
                    if created:
                        stats["alt_kat"] += 1
                    alt_kat_cache[alt_slug] = kat
                    kat_yas_ids.setdefault(alt_slug, set())

                alt_kat = alt_kat_cache[alt_slug]

                # ── Cinsiyet ──────────────────────────────────────────────
                cinsiyet_ad = entry.get("cinsiyet", "Tumu")
                if cinsiyet_ad in ("Kadin", "Kad\u0131n"):
                    soru_cinsiyet = cinsiyetler.get("F")
                elif cinsiyet_ad == "Erkek":
                    soru_cinsiyet = cinsiyetler.get("M")
                else:
                    soru_cinsiyet = None

                # ── Yas araliklari ────────────────────────────────────────
                yas_grubu = entry.get("yas_grubu", "18-120")
                yas_objs  = _yas_araligini_bul(yas_araliklari, yas_grubu)
                yas_ids   = {ya.pk for ya in yas_objs}
                kat_yas_ids[alt_slug].update(yas_ids)
                kat_yas_ids[ana_slug].update(yas_ids)

                # ── Soru ──────────────────────────────────────────────────
                sira_sayac[alt_slug] = sira_sayac.get(alt_slug, 0) + 1
                sira = sira_sayac[alt_slug]

                soru = Soru.objects.create(
                    kategori=alt_kat,
                    metin=entry["soru"],
                    sira=sira,
                    hedef_cinsiyet=soru_cinsiyet,
                )
                if yas_objs:
                    soru.hedef_yas_araliklari.set(yas_objs)
                stats["soru"] += 1

                # ── Etken maddeler ────────────────────────────────────────
                for etken_ad, rol in [
                    (entry.get("asil_takviye"), SoruEtkenMadde.ROL_ANA),
                    (entry.get("destekleyici"), SoruEtkenMadde.ROL_DESTEKLEYICI),
                    (entry.get("tamamlayici"),  SoruEtkenMadde.ROL_TAMAMLAYICI),
                ]:
                    if not etken_ad:
                        continue
                    em, em_created = EtkenMadde.objects.get_or_create(
                        ad=etken_ad, defaults={"aciklama": ""},
                    )
                    if em_created:
                        stats["em"] += 1
                    SoruEtkenMadde.objects.get_or_create(
                        soru=soru, etken_madde=em, defaults={"rol": rol},
                    )

            # ── Kategori yas araliklerini guncelle ────────────────────────
            for slug, ids in kat_yas_ids.items():
                kat_obj = alt_kat_cache.get(slug) or ana_kat_cache.get(slug)
                if kat_obj and ids:
                    kat_obj.hedef_yas_araliklari.set(list(ids))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Seed yukleme tamamlandi:"))
        self.stdout.write(f"  Ana kategoriler : {stats['ana_kat']}")
        self.stdout.write(f"  Alt kategoriler : {stats['alt_kat']}")
        self.stdout.write(f"  Sorular         : {stats['soru']}")
        self.stdout.write(f"  Etken maddeler  : {stats['em']}")
