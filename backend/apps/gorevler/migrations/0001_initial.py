# Generated manually for iş takip module.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Gorev",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("olusturulma_tarihi", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("guncellenme_tarihi", models.DateTimeField(auto_now_add=True)),
                ("surum", models.PositiveIntegerField(default=1, editable=False)),
                ("baslik", models.CharField(max_length=200)),
                ("icerik", models.TextField(max_length=2000)),
                ("durum", models.CharField(choices=[("YENI", "Yeni"), ("INCELENIYOR", "İnceleniyor"), ("YAPILDI", "Yapıldı"), ("YAPILMADI", "Yapılmadı")], db_index=True, default="YENI", max_length=16)),
                ("guncelleyen", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("olusturan", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("atanan_kullanici", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="atanan_gorevler", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "gorevler",
                "ordering": ("-olusturulma_tarihi",),
                "verbose_name": "İş",
                "verbose_name_plural": "İşler",
            },
        ),
    ]
