import django.core.validators
from django.db import migrations, models


def set_kategori_sira(apps, schema_editor):
    Kategori = apps.get_model("products", "Kategori")
    for index, kategori in enumerate(Kategori.objects.order_by("ad"), start=1):
        kategori.sira = index
        kategori.save(update_fields=["sira"])


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0014_make_metin_en_nullable"),
    ]

    operations = [
        migrations.AddField(
            model_name="kategori",
            name="sira",
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text="Goruntuleme sirasi (kucuk deger once). Eşit sirada ada gore sirala.",
                validators=[django.core.validators.MinValueValidator(1)],
            ),
        ),
        migrations.RunPython(set_kategori_sira, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name="kategori",
            options={
                "ordering": ("bagli_kategori_id", "sira", "ad"),
                "verbose_name": "Kategori",
                "verbose_name_plural": "Kategoriler",
            },
        ),
        migrations.AddConstraint(
            model_name="kategori",
            constraint=models.UniqueConstraint(
                condition=models.Q(bagli_kategori__isnull=False),
                fields=("bagli_kategori", "sira"),
                name="kategori_parent_sira_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="kategori",
            constraint=models.UniqueConstraint(
                condition=models.Q(bagli_kategori__isnull=True),
                fields=("sira",),
                name="kategori_root_sira_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="kategori",
            constraint=models.CheckConstraint(condition=models.Q(sira__gte=1), name="kategori_sira_min_1"),
        ),
    ]