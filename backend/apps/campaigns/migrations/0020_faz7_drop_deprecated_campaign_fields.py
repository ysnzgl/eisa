"""
Faz 7 — Deprecated Campaign alanlarını kaldır.

Kaldırılan alanlar:
  - is_guaranteed   (BooleanField, default=False) — canonical: DeliveryRule.guarantee_mode
  - impression_goal (PositiveIntegerField, nullable) — canonical: DeliveryRule(CAMPAIGN_TOTAL)
  - frequency_cap_per_hour (PositiveSmallIntegerField, nullable) — canonical: DeliveryRule.max_per_hour

Korunan alan:
  - target_pharmacies (ManyToManyField) — fiziksel tablo korunuyor (legacy data compat);
    aktif API path temizlendi ama M2M tablo silinmedi.

Veri etkisi: Bu alanlar mevcut kayıtlarda NULL/False değerler taşıyordu.
Canonical değerler DeliveryRule'da. Veri kaybı riski yok.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0019_faz4_generation_queue_fields"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="campaign",
            name="is_guaranteed",
        ),
        migrations.RemoveField(
            model_name="campaign",
            name="impression_goal",
        ),
        migrations.RemoveField(
            model_name="campaign",
            name="frequency_cap_per_hour",
        ),
    ]
