"""
Django management komutu: master_seed.json'u Kategori/Soru/EtkenMadde
tablolarina yukler. UoW kullanmaz cunku komut bir kullanici baglami yok;
bootstrap idempotent upsert yapar.

Yuklenenler:
  - Kategori (hedef_cinsiyet, hedef_yas_araliklari dahil)
  - Soru     (hedef_cinsiyet, hedef_yas_araliklari dahil)
  - EtkenMadde
  - SoruEtkenMadde (through, rol bilgisiyle)
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.lookups.models import Cinsiyet, YasAraligi
from apps.products.models import EtkenMadde, Kategori, Soru, SoruEtkenMadde

# Hassas kategori slug'lari
HASSAS_SLUGLAR = {"cinsel", "hemoroid", "koku", "mantar", "sac", "ishal"}

# Kategori slug → cinsiyet kodu (sadece tek cinsiyet hedefli kategoriler)
KATEGORI_CINSIYET_MAP = {
    "kadin_sagligi": "F",
    "erkek_sagligi": "M",
}


def _yas_araligini_bul(yas_araliklari: list, age_min: int, age_max: int) -> list:
    """age_min..age_max ile kesisen YasAraligi nesnelerini dondurur."""
    sonuc = []
    for ya in yas_araliklari:
        if ya.alt_sinir > age_max:
            continue
        if ya.ust_sinir is not None and ya.ust_sinir < age_min:
            continue
        sonuc.append(ya)
    return sonuc


def _cinsiyet_bul(cinsiyetler: dict, gender_list: list):
    """
    Kural icin tek bir Cinsiyet nesnesi dondurur.
    Birden fazla veya hic cinsiyet yoksa None (= herkese goster).
    """
    kodlar = set(gender_list or [])
    if len(kodlar) == 1:
        kod = next(iter(kodlar))
        return cinsiyetler.get(kod)
    return None


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

        # Lookup tablolarini onceden cek (her dongu adiminda sorgu yapma)
        cinsiyetler = {c.kod: c for c in Cinsiyet.objects.all()}
        yas_araliklari = list(YasAraligi.objects.all())

        if not cinsiyetler:
            raise CommandError(
                "Cinsiyet lookup tablosu bos. Once lookups seed calistirin: "
                "python manage.py seed_lookups"
            )
        if not yas_araliklari:
            raise CommandError(
                "YasAraligi lookup tablosu bos. Once lookups seed calistirin: "
                "python manage.py seed_lookups"
            )

        kat_olusan = kat_guncellenen = 0
        soru_olusan = soru_guncellenen = 0
        em_olusan = 0

        for entry in seed_data:
            slug = entry["category_slug"]
            ad = entry.get("title", slug)
            hassas = slug in HASSAS_SLUGLAR

            # Kategorinin cinsiyet hedefini belirle
            kat_cinsiyet_kod = KATEGORI_CINSIYET_MAP.get(slug)
            kat_cinsiyet = cinsiyetler.get(kat_cinsiyet_kod) if kat_cinsiyet_kod else None

            kat, created = Kategori.objects.update_or_create(
                slug=slug,
                defaults={
                    "ad": ad,
                    "ikon": entry.get("icon", "fa-circle"),
                    "hassas": hassas,
                    "aktif": True,
                    "hedef_cinsiyet": kat_cinsiyet,
                },
            )
            if created:
                kat_olusan += 1
            else:
                kat_guncellenen += 1

            # Kategorinin yas araliklerini tum sorularin union'indan cikart
            kat_yas_ids: set[int] = set()

            for q in entry.get("questions", []):
                rules = q.get("match_rules", [])

                # --- Soru icin cinsiyet ve yas union'i hesapla ---
                tum_cinsiyetler: set[str] = set()
                tum_yas_ids: set[int] = set()

                for rule in rules:
                    gender_list = rule.get("gender", [])
                    tum_cinsiyetler.update(gender_list)

                    age_min = rule.get("age_min", 0)
                    age_max = rule.get("age_max", 120)
                    for ya in _yas_araligini_bul(yas_araliklari, age_min, age_max):
                        tum_yas_ids.add(ya.pk)
                        kat_yas_ids.add(ya.pk)

                # Birden fazla cinsiyet → hedef_cinsiyet = None (herkese goster)
                soru_cinsiyet = None
                if len(tum_cinsiyetler) == 1:
                    soru_cinsiyet = cinsiyetler.get(next(iter(tum_cinsiyetler)))

                soru, q_created = Soru.objects.update_or_create(
                    kategori=kat,
                    sira=q.get("priority", 0),
                    defaults={
                        "metin": q["text"],
                        "hedef_cinsiyet": soru_cinsiyet,
                    },
                )
                if q_created:
                    soru_olusan += 1
                else:
                    soru_guncellenen += 1

                # Soru yas araliklerini set
                if tum_yas_ids:
                    soru.hedef_yas_araliklari.set(list(tum_yas_ids))
                else:
                    soru.hedef_yas_araliklari.clear()

                # Etken maddeleri match_rules'tan cikar ve through model ile bagla
                for rule in rules:
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

            # Kategori yas araliklerini set (tum sorularin union'i)
            if kat_yas_ids:
                kat.hedef_yas_araliklari.set(list(kat_yas_ids))
            else:
                kat.hedef_yas_araliklari.clear()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Seed yukleme tamamlandi:"))
        self.stdout.write(f"  Kategoriler   — olusan: {kat_olusan}, guncellenen: {kat_guncellenen}")
        self.stdout.write(f"  Sorular       — olusan: {soru_olusan}, guncellenen: {soru_guncellenen}")
        self.stdout.write(f"  Etken maddeler— olusan: {em_olusan}")
