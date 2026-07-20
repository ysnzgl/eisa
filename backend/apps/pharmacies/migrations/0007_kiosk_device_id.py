# 2026-07-20 — Persistent device identity fields.
#
# Kiosk.device_id       : globally unique UUID (NULL until first enrollment).
# KioskProvisioningRequest.device_id : stored for HMAC verification and
#                                      transferred to Kiosk on approval.
#
# KioskProvisioningRequest.device_id uses a *partial* unique constraint
# (non-empty values only). Empty strings represent legacy devices that
# haven't generated a device_id yet — they may have multiple pending requests.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacies', '0006_kioskprovisioningrequest'),
    ]

    operations = [
        # Kiosk.device_id — globally unique persistent UUID (NULL = not yet bound)
        migrations.AddField(
            model_name='kiosk',
            name='device_id',
            field=models.CharField(
                blank=True,
                help_text='Kalici cihaz UUID; bootstrap sirasinda kilit (spoofing onlenir).',
                max_length=36,
                null=True,
                unique=True,
            ),
        ),
        # KioskProvisioningRequest.device_id — stored for HMAC + approval transfer
        migrations.AddField(
            model_name='kioskprovisioningrequest',
            name='device_id',
            field=models.CharField(
                blank=True,
                default='',
                help_text="Kalici cihaz UUID (bootstrap HMAC'e dahil edilir).",
                max_length=36,
            ),
        ),
        # Partial unique index: non-empty device_id values must be globally unique
        # across all provisioning requests (prevents device_id squatting).
        migrations.AddConstraint(
            model_name='kioskprovisioningrequest',
            constraint=models.UniqueConstraint(
                condition=~models.Q(device_id=''),
                fields=['device_id'],
                name='uniq_provisioning_device_id_nonempty',
            ),
        ),
    ]
