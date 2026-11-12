"""Fiziksel donanım ile provizyonla tanınan kiosk kaydının tekil eşleştirmesi."""
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.uow import UnitOfWork
from .models import FizikselCihaz, Kiosk


@transaction.atomic
def eslestir_cihaz(cihaz_id, kiosk_id, *, user=None):
    kiosk = Kiosk.objects.select_for_update().get(pk=kiosk_id)
    device = FizikselCihaz.objects.select_for_update().filter(pk=cihaz_id, aktif=True).first()
    if device is None:
        raise ValidationError({"fiziksel_cihaz_id": "Aktif fiziksel cihaz kaydı bulunamadı."})
    if device.kiosk_id not in (None, kiosk.pk):
        raise ValidationError({"fiziksel_cihaz_id": "Bu seri numarası başka bir kiosk ile eşleşmiş."})
    if device.eczane_id not in (None, kiosk.eczane_id):
        raise ValidationError({"fiziksel_cihaz_id": "Cihaz seçilen eczaneye ait değil."})
    if FizikselCihaz.objects.filter(kiosk=kiosk).exclude(pk=device.pk).exists():
        raise ValidationError({"fiziksel_cihaz_id": "Bu kiosk başka bir seri numarasıyla eşleşmiş."})
    if device.kiosk_id == kiosk.pk:
        return device
    device.kiosk = kiosk
    device.eczane_id = kiosk.eczane_id
    with UnitOfWork(user=user) as uow:
        uow.update(device, update_fields=["kiosk", "eczane"])
    return device
