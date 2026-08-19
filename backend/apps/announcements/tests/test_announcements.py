from datetime import date
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.lookups.models import Il, Ilce
from apps.pharmacies.models import Eczane
from apps.users.models import Kullanici

from ..models import Announcement, AnnouncementRead, PharmacyDutyMonth
from ..services import is_general_occurrence, system_context


pytestmark = pytest.mark.django_db


@pytest.fixture
def pharmacy_user():
    province = Il.objects.create(ad="Test İl")
    district = Ilce.objects.create(ad="Test İlçe", il=province)
    pharmacy = Eczane.objects.create(ad="Test Eczanesi", il=province, ilce=district)
    user = Kullanici.objects.create_user(
        username="pharmacist", password="secret", rol=Kullanici.Rol.ECZACI, eczane=pharmacy
    )
    return user, pharmacy


def general(**overrides):
    values = {
        "kind": Announcement.Kind.GENERAL,
        "title": "Genel",
        "message": "Mesaj",
        "active": True,
        "start_date": date(2026, 8, 1),
        "target_scope": Announcement.TargetScope.ALL,
    }
    values.update(overrides)
    return Announcement.objects.create(**values)


@pytest.mark.parametrize(
    ("mode", "kwargs", "matching", "not_matching"),
    [
        ("SPECIFIC_DAY", {"monthly_day_start": 15}, date(2026, 8, 15), date(2026, 8, 16)),
        ("DAY_RANGE", {"monthly_day_start": 10, "monthly_day_end": 12}, date(2026, 8, 11), date(2026, 8, 13)),
        ("FIRST_N_DAYS", {"monthly_day_count": 3}, date(2026, 8, 3), date(2026, 8, 4)),
        ("LAST_N_DAYS", {"monthly_day_count": 3}, date(2026, 8, 29), date(2026, 8, 28)),
        ("LAST_WEEK", {}, date(2026, 8, 25), date(2026, 8, 24)),
    ],
)
def test_monthly_occurrence_modes(mode, kwargs, matching, not_matching):
    announcement = general(
        recurrence=Announcement.Recurrence.MONTHLY,
        monthly_mode=mode,
        **kwargs,
    )
    assert is_general_occurrence(announcement, matching)
    assert not is_general_occurrence(announcement, not_matching)


def test_reads_are_unique_per_occurrence_date(pharmacy_user):
    user, _ = pharmacy_user
    announcement = general(recurrence=Announcement.Recurrence.DAILY)
    AnnouncementRead.objects.create(announcement=announcement, user=user, occurrence_date=date(2026, 8, 18))
    AnnouncementRead.objects.create(announcement=announcement, user=user, occurrence_date=date(2026, 8, 19))
    assert announcement.reads.count() == 2


def test_next_month_warning_last_three_days_and_resolves_with_no_duty(pharmacy_user):
    _, pharmacy = pharmacy_user
    announcement = Announcement.objects.get(system_key=Announcement.SystemKey.DUTY_NEXT_MONTH_MISSING)
    assert system_context(announcement, pharmacy, date(2026, 8, 28)) is None
    context = system_context(announcement, pharmacy, date(2026, 8, 29))
    assert context["target_month"] == "2026-09"
    PharmacyDutyMonth.objects.create(pharmacy=pharmacy, month=date(2026, 9, 1), has_no_duty=True)
    assert system_context(announcement, pharmacy, date(2026, 8, 30)) is None


def test_current_month_warning_only_days_1_to_14(pharmacy_user):
    _, pharmacy = pharmacy_user
    announcement = Announcement.objects.get(system_key=Announcement.SystemKey.DUTY_CURRENT_MONTH_MISSING)
    assert system_context(announcement, pharmacy, date(2026, 8, 14)) is not None
    assert system_context(announcement, pharmacy, date(2026, 8, 15)) is None


def test_system_announcement_update_is_whitelisted_and_delete_is_forbidden(pharmacy_user):
    admin = Kullanici.objects.create_user(username="admin", rol=Kullanici.Rol.SUPERADMIN)
    announcement = Announcement.objects.get(system_key=Announcement.SystemKey.DUTY_CURRENT_MONTH_MISSING)
    client = APIClient()
    client.force_authenticate(admin)

    response = client.patch(
        reverse("admin-announcement-detail", args=[announcement.id]),
        {"title": "Yeni başlık", "recurrence": "DAILY"},
        format="json",
    )
    assert response.status_code == 400
    announcement.refresh_from_db()
    assert announcement.title != "Yeni başlık"

    response = client.patch(
        reverse("admin-announcement-detail", args=[announcement.id]),
        {"title": "Yeni başlık", "active": False},
        format="json",
    )
    assert response.status_code == 200
    response = client.delete(reverse("admin-announcement-detail", args=[announcement.id]))
    assert response.status_code == 405


def test_daily_system_read_only_suppresses_same_day(pharmacy_user):
    user, _ = pharmacy_user
    client = APIClient()
    client.force_authenticate(user)
    today = date(2026, 8, 10)
    with patch("apps.announcements.views.istanbul_today", return_value=today):
        active = client.get(reverse("active-announcements"))
        current = next(item for item in active.data if item["system_key"] == "DUTY_CURRENT_MONTH_MISSING")
        assert client.post(reverse("announcement-read", args=[current["id"]])).status_code == 201
        active_after_read = client.get(reverse("active-announcements"))
    assert all(item["id"] != current["id"] for item in active_after_read.data)


def test_active_endpoint_excludes_inactive_out_of_date_and_wrong_target(pharmacy_user):
    user, pharmacy = pharmacy_user
    client = APIClient()
    client.force_authenticate(user)
    today = date(2026, 8, 19)

    visible_all = general(title="Tüm eczaneler", recurrence=Announcement.Recurrence.DAILY)
    visible_province = general(
        title="İl hedefi",
        recurrence=Announcement.Recurrence.DAILY,
        target_scope=Announcement.TargetScope.PROVINCE,
        target_province=pharmacy.il,
    )
    future = general(title="Gelecek", recurrence=Announcement.Recurrence.DAILY, start_date=date(2026, 8, 20))
    expired = general(
        title="Süresi dolmuş",
        recurrence=Announcement.Recurrence.DAILY,
        end_date=date(2026, 8, 18),
    )
    inactive = general(title="Pasif", recurrence=Announcement.Recurrence.DAILY, active=False)
    other_province = Il.objects.create(ad="Başka İl")
    other_district = Ilce.objects.create(ad="Başka İlçe", il=other_province)
    other_pharmacy = Eczane.objects.create(ad="Başka Eczane", il=other_province, ilce=other_district)
    wrong_target = general(
        title="Başka eczane",
        recurrence=Announcement.Recurrence.DAILY,
        target_scope=Announcement.TargetScope.PHARMACY,
        target_pharmacy=other_pharmacy,
    )

    with patch("apps.announcements.views.istanbul_today", return_value=today):
        response = client.get(reverse("active-announcements"))

    assert response.status_code == 200
    returned_ids = {item["id"] for item in response.data}
    assert {visible_all.id, visible_province.id}.issubset(returned_ids)
    assert {future.id, expired.id, inactive.id, wrong_target.id}.isdisjoint(returned_ids)
