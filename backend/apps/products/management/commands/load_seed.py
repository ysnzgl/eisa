"""
Django management komutu: master_seed.json'u Products DB'sine yükler.

Kullanım:
  python manage.py load_seed --file /path/to/master_seed.json

Hassas kategoriler (is_sensitive=True) otomatik olarak sluglarına göre tespit edilir.
Mevcut kayıtlar güncellenir; yeni kayıtlar oluşturulur (upsert).
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.products.models import ActiveIngredient, Category, Question

# Hassas kategori slug'ları (Akış B için otomatik işaretlenir)
SENSITIVE_SLUGS = {"cinsel", "hemoroid", "koku", "mantar", "sac", "ishal"}


class Command(BaseCommand):
    help = "master_seed.json dosyasındaki kategori ve soruları veritabanına yükler."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help="Seed JSON dosyasının yolu. Verilmezse proje kökünde master_seed.json aranır.",
        )

    def handle(self, *args, **options):
        # ── Dosyayı bul ──────────────────────────────────────────────────────
        if options["file"]:
            seed_path = Path(options["file"])
        else:
            # manage.py ile aynı dizinde veya üst dizinde ara
            base = Path(__file__).resolve().parents[5]  # repo kökü
            seed_path = base / "master_seed.json"

        if not seed_path.exists():
            raise CommandError(f"Seed dosyası bulunamadı: {seed_path}")

        with seed_path.open(encoding="utf-8") as f:
            seed_data = json.load(f)

        self.stdout.write(f"Seed dosyası yüklendi: {seed_path}")
        self.stdout.write(f"Toplam kategori: {len(seed_data)}")

        categories_created = 0
        categories_updated = 0
        questions_created = 0
        questions_updated = 0
        ingredients_created = 0

        for entry in seed_data:
            slug = entry["category_slug"]
            name = entry.get("title", slug)
            is_sensitive = slug in SENSITIVE_SLUGS

            # ── Kategori upsert ───────────────────────────────────────────────
            cat, created = Category.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "icon": entry.get("icon", "fa-circle"),
                    "is_sensitive": is_sensitive,
                    "is_active": True,
                },
            )
            if created:
                categories_created += 1
                self.stdout.write(self.style.SUCCESS(f"  [+] Kategori oluşturuldu: {name}"))
            else:
                categories_updated += 1
                self.stdout.write(f"  [~] Kategori güncellendi: {name}")

            # ── Sorular ───────────────────────────────────────────────────────
            for q_data in entry.get("questions", []):
                q_text = q_data["text"]
                q_order = q_data.get("priority", 0)

                q, q_created = Question.objects.update_or_create(
                    category=cat,
                    order=q_order,
                    defaults={
                        "seed_id": q_data.get("id"),
                        "text": q_text,
                        "match_rules": q_data.get("match_rules", []),
                    },
                )
                if q_created:
                    questions_created += 1
                else:
                    questions_updated += 1

                # ── Etken maddeler (match_rules'dan çıkar) ────────────────────
                for rule in q_data.get("match_rules", []):
                    for ingredient_name in [rule.get("primary"), rule.get("supportive")]:
                        if ingredient_name:
                            _, ing_created = ActiveIngredient.objects.get_or_create(
                                name=ingredient_name,
                                defaults={"description": ""},
                            )
                            if ing_created:
                                ingredients_created += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Seed yükleme tamamlandı:"))
        self.stdout.write(f"  Kategoriler — oluşturuldu: {categories_created}, güncellendi: {categories_updated}")
        self.stdout.write(f"  Sorular     — oluşturuldu: {questions_created}, güncellendi: {questions_updated}")
        self.stdout.write(f"  Etken mad.  — oluşturuldu: {ingredients_created}")
