import calendar
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone

from .models import Announcement, PharmacyDutyMonth

ISTANBUL = ZoneInfo("Europe/Istanbul")


def istanbul_today() -> date:
    return timezone.now().astimezone(ISTANBUL).date()


def month_start(value: date) -> date:
    return value.replace(day=1)


def add_month(value: date) -> date:
    return (value.replace(day=28) + timedelta(days=4)).replace(day=1)


def is_general_occurrence(announcement: Announcement, on_date: date) -> bool:
    if announcement.kind != Announcement.Kind.GENERAL or not announcement.active:
        return False
    if not announcement.start_date or on_date < announcement.start_date:
        return False
    if announcement.end_date and on_date > announcement.end_date:
        return False
    if announcement.recurrence == Announcement.Recurrence.ONCE:
        return on_date == announcement.start_date
    if announcement.recurrence == Announcement.Recurrence.DAILY:
        return True
    if announcement.recurrence == Announcement.Recurrence.WEEKLY:
        return on_date.weekday() in announcement.weekdays
    if announcement.recurrence != Announcement.Recurrence.MONTHLY:
        return False

    day = on_date.day
    last_day = calendar.monthrange(on_date.year, on_date.month)[1]
    mode = announcement.monthly_mode
    if mode == Announcement.MonthlyMode.SPECIFIC_DAY:
        return day == announcement.monthly_day_start
    if mode == Announcement.MonthlyMode.DAY_RANGE:
        return announcement.monthly_day_start <= day <= min(announcement.monthly_day_end, last_day)
    if mode == Announcement.MonthlyMode.FIRST_N_DAYS:
        return day <= min(announcement.monthly_day_count, last_day)
    if mode == Announcement.MonthlyMode.LAST_N_DAYS:
        return day >= max(1, last_day - announcement.monthly_day_count + 1)
    if mode == Announcement.MonthlyMode.LAST_WEEK:
        return day >= max(1, last_day - 6)
    return False


def applies_to_pharmacy(announcement: Announcement, pharmacy) -> bool:
    if not pharmacy:
        return False
    scope = announcement.target_scope
    if scope == Announcement.TargetScope.ALL:
        return True
    if scope == Announcement.TargetScope.PROVINCE:
        return pharmacy.il_id == announcement.target_province_id
    if scope == Announcement.TargetScope.DISTRICT:
        return pharmacy.ilce_id == announcement.target_district_id
    if scope == Announcement.TargetScope.PHARMACY:
        return pharmacy.id == announcement.target_pharmacy_id
    return False


def system_context(announcement: Announcement, pharmacy, today: date):
    if announcement.kind != Announcement.Kind.SYSTEM or not announcement.active or not pharmacy:
        return None
    if announcement.system_key == Announcement.SystemKey.DUTY_NEXT_MONTH_MISSING:
        last_day = calendar.monthrange(today.year, today.month)[1]
        if today.day < last_day - 2:
            return None
        target_month = add_month(month_start(today))
    elif announcement.system_key == Announcement.SystemKey.DUTY_CURRENT_MONTH_MISSING:
        if today.day > 14:
            return None
        target_month = month_start(today)
    else:
        return None

    duty = PharmacyDutyMonth.objects.filter(pharmacy=pharmacy, month=target_month).prefetch_related("days").first()
    if duty and (duty.has_no_duty or duty.days.exists()):
        return None
    return {
        "target_month": target_month.strftime("%Y-%m"),
        "action_url": f"/pharmacist/duty?month={target_month:%Y-%m}",
    }
