from datetime import date

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.core.uow import UnitOfWork

from .models import PharmacyDutyDay, PharmacyDutyMonth
from .services import istanbul_today, month_start


@transaction.atomic
def save_duty_month(*, pharmacy, month, has_no_duty, dates, user):
    today = istanbul_today()
    if month < month_start(today):
        raise serializers.ValidationError({"month": "Geçmiş ayların nöbet bilgisi değiştirilemez."})
    if has_no_duty and dates:
        raise serializers.ValidationError({"dates": "Nöbetim yok seçiliyken nöbet günü girilemez."})

    duty = PharmacyDutyMonth.objects.select_for_update().filter(pharmacy=pharmacy, month=month).first()
    existing_dates = set(duty.days.values_list("date", flat=True)) if duty else set()
    requested = set(dates)
    protected = {item for item in existing_dates if item < today}
    if {item for item in requested if item < today} != protected:
        raise serializers.ValidationError({"dates": "Geçmiş nöbet günleri değiştirilemez."})
    if has_no_duty and protected:
        raise serializers.ValidationError({"has_no_duty": "Bu ayda geçmiş nöbet günü bulunduğu için nöbetim yok seçilemez."})

    with UnitOfWork(user=user) as uow:
        if duty is None:
            duty = PharmacyDutyMonth(
                pharmacy=pharmacy, month=month, has_no_duty=has_no_duty,
                updated_by=user, updated_at=timezone.now(),
            )
            uow.add(duty)
        else:
            duty.has_no_duty = has_no_duty
            duty.updated_by = user
            duty.updated_at = timezone.now()
            uow.update(duty, update_fields=["has_no_duty", "updated_by_id", "updated_at"])
        removable = duty.days.filter(date__gte=today).exclude(date__in=requested)
        for row in removable:
            uow.delete(row)
        current = set(duty.days.values_list("date", flat=True))
        for item in sorted(requested - current):
            uow.add(PharmacyDutyDay(duty_month=duty, date=item))
    return duty
