"""
Django management komutu: master_seed.json'u Kategori/Soru/EtkenMadde
tablolarina yukler. UoW kullanmaz cunku komut bir kullanici baglami yok;
bootstrap idempotent upsert yapar.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.products.models import EtkenMadde, Kategori, Soru, SoruEtkenMadde

# Hassas kategori slug'lari
HASSAS_SLUGLAR = {"cinsel", "hemoroid", "koku", "mantar", "sac", "ishal"}


class Command(BaseCommand):
    help = "master_seed.json dosyasindaki kategori ve sorulari veritabanina yukler."

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, default=None,
                            help="Seed JSON dosyasi yolu.")

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

        self.stdout.write(f"Seed dosyasi yuklendi: {seed_path}")
        self.stdout.write(f"Toplam kategori: {len(seed_data)}")

        kat_olusan = kat_guncellenen = 0
        soru_olusan = soru_guncellenen = 0
        em_olusan = 0

        for entry in seed_data:
            slug = entry["category_slug"]
            ad = entry.get("title", slug)
            hassas = slug in HASSAS_SLUGLAR

            kat, created = Kategori.objects.update_or_create(
                slug=slug,
                defaults={
                    "ad": ad,
                    "ikon": entry.get("icon", "fa-circle"),
                    "hassas": hassas,
                    "aktif": True,
                },
            )
            if created:
                kat_olusan += 1
            else:
                kat_guncellenen += 1

            for q in entry.get("questions", []):
                soru, q_created = Soru.objects.update_or_create(
                    kategori=kat,
                    sira=q.get("priority", 0),
                    defaults={"metin": q["text"]},
                )
                if q_created:
                    soru_olusan += 1
                else:
                    soru_guncellenen += 1

                # Etken maddeleri match_rules'tan çıkar ve through model ile bağla
                for rule in q.get("match_rules", []):
                    for rol_key, rol_deger in [
                        ("primary", SoruEtkenMadde.ROL_ANA),
                        ("supportive", SoruEtkenMadde.ROL_DESTEKLEYICI),
                    ]:
                        em_ad = rule.get(rol_key)
                        if not em_ad:
                            continue
                        em, em_created = EtkenMadde.objects.get_or_create(
                            ad=em_ad,
                            defaults={"aciklama": ""},
                        )
                        if em_created:
                            em_olusan += 1
                        SoruEtkenMadde.objects.update_or_create(
                            soru=soru,
                            etken_madde=em,
                            defaults={"rol": rol_deger},
                        )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Seed yukleme tamamlandi:"))
        self.stdout.write(f"  Kategoriler   — olusan: {kat_olusan}, guncellenen: {kat_guncellenen}")
        self.stdout.write(f"  Sorular       — olusan: {soru_olusan}, guncellenen: {soru_guncellenen}")
        self.stdout.write(f"  Etken maddeler— olusan: {em_olusan}")
