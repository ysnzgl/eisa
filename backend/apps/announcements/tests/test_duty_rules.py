from datetime import date
from unittest.mock import patch

import pytest
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

from apps.lookups.models import Il, Ilce
from apps.pharmacies.models import Eczane
from apps.users.models import Kullanici
from ..models import PharmacyDutyDay, PharmacyDutyMonth

pytestmark = pytest.mark.django_db


@pytest.fixture
def duty_context():
    il=Il.objects.create(ad="Duty İl"); ilce=Ilce.objects.create(ad="Duty İlçe",il=il)
    pharmacy=Eczane.objects.create(ad="Duty Eczane",il=il,ilce=ilce)
    user=Kullanici.objects.create_user(username="duty-user",rol="pharmacist",eczane=pharmacy)
    client=APIClient(); client.force_authenticate(user)
    return pharmacy,user,client


def test_duplicate_day_db_constraint(duty_context):
    pharmacy,_,_=duty_context
    month=PharmacyDutyMonth.objects.create(pharmacy=pharmacy,month=date(2026,9,1))
    PharmacyDutyDay.objects.create(duty_month=month,date=date(2026,9,5))
    with pytest.raises(IntegrityError), transaction.atomic():
        PharmacyDutyDay.objects.create(duty_month=month,date=date(2026,9,5))


@patch("apps.announcements.duty.istanbul_today", return_value=date(2026,8,19))
def test_no_duty_conflict_and_past_month_protected(_, duty_context):
    _,_,client=duty_context
    assert client.put("/api/announcements/duty/", {"month":"2026-09","has_no_duty":True,"dates":[]}, format="json").status_code == 200
    assert client.put("/api/announcements/duty/", {"month":"2026-09","has_no_duty":True,"dates":["2026-09-05"]}, format="json").status_code == 400
    assert client.put("/api/announcements/duty/", {"month":"2026-07","has_no_duty":False,"dates":[]}, format="json").status_code == 400
