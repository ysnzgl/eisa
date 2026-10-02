from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="SirketProfili",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("olusturulma_tarihi", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("guncellenme_tarihi", models.DateTimeField(auto_now_add=True)),
                ("surum", models.PositiveIntegerField(default=1, editable=False)),
                ("sabit_anahtar", models.CharField(default="EISA", editable=False, max_length=20, unique=True)),
                ("ticari_unvan", models.CharField(max_length=255)),
                ("marka_adi", models.CharField(blank=True, default="e-İSA", max_length=120)),
                ("vergi_dairesi", models.CharField(max_length=120)),
                ("vergi_numarasi", models.CharField(max_length=10)),
                ("mersis_numarasi", models.CharField(blank=True, default="", max_length=16)),
                ("ticaret_sicil_numarasi", models.CharField(blank=True, default="", max_length=50)),
                ("kep_adresi", models.EmailField(blank=True, default="", max_length=254)),
                ("eposta", models.EmailField(blank=True, default="", max_length=254)),
                ("telefon", models.CharField(blank=True, default="", max_length=30)),
                ("web_sitesi", models.URLField(blank=True, default="")),
                ("adres", models.TextField()),
                ("ilce", models.CharField(blank=True, default="", max_length=100)),
                ("il", models.CharField(blank=True, default="", max_length=100)),
                ("posta_kodu", models.CharField(blank=True, default="", max_length=10)),
                ("yetkili_ad_soyad", models.CharField(blank=True, default="", max_length=150)),
                ("yetkili_unvan", models.CharField(blank=True, default="", max_length=120)),
                ("guncelleyen", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("olusturan", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "sirket_profili", "verbose_name": "Şirket Profili", "verbose_name_plural": "Şirket Profili"},
        ),
        migrations.CreateModel(
            name="BankaHesabi",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("olusturulma_tarihi", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("guncellenme_tarihi", models.DateTimeField(auto_now_add=True)),
                ("surum", models.PositiveIntegerField(default=1, editable=False)),
                ("banka_adi", models.CharField(max_length=120)),
                ("hesap_sahibi", models.CharField(max_length=255)),
                ("iban", models.CharField(max_length=34)),
                ("sube_adi", models.CharField(blank=True, default="", max_length=120)),
                ("sube_kodu", models.CharField(blank=True, default="", max_length=20)),
                ("hesap_numarasi", models.CharField(blank=True, default="", max_length=40)),
                ("para_birimi", models.CharField(choices=[("TRY", "Türk Lirası"), ("USD", "Amerikan Doları"), ("EUR", "Euro"), ("GBP", "İngiliz Sterlini")], default="TRY", max_length=3)),
                ("aciklama", models.CharField(blank=True, default="", max_length=255)),
                ("aktif", models.BooleanField(default=True)),
                ("varsayilan", models.BooleanField(default=False)),
                ("sira", models.PositiveSmallIntegerField(default=0)),
                ("guncelleyen", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("olusturan", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("sirket", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="banka_hesaplari", to="sirket.sirketprofili")),
            ],
            options={"db_table": "sirket_banka_hesaplari", "ordering": ("sira", "banka_adi", "id"), "verbose_name": "Banka Hesabı", "verbose_name_plural": "Banka Hesapları"},
        ),
        migrations.AddConstraint(
            model_name="bankahesabi",
            constraint=models.UniqueConstraint(fields=("sirket", "iban"), name="uniq_sirket_iban"),
        ),
        migrations.AddConstraint(
            model_name="bankahesabi",
            constraint=models.UniqueConstraint(condition=models.Q(("varsayilan", True)), fields=("sirket",), name="uniq_sirket_varsayilan_banka"),
        ),
    ]
