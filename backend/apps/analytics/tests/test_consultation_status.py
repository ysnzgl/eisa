import uuid
from datetime import date

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.lookups.models import Cinsiyet, Il, Ilce, YasAraligi
from apps.lookups.seed import seed_lookups
from apps.pharmacies.models import Eczane, Kiosk, KioskEczaneAtama
from apps.products.models import EtkenMadde
from apps.users.models import Kullanici

from ..models import OturumLogu, OturumOnerilenEtkenMadde

pytestmark = pytest.mark.django_db


@pytest.fixture
def context():
    seed_lookups()
    il = Il.objects.create(ad="Status İl")
    ilce = Ilce.objects.create(il=il, ad="Status İlçe")
    pharmacies = [Eczane.objects.create(ad=f"Eczane {i}", il=il, ilce=ilce) for i in range(2)]
    kiosks = [Kiosk.objects.create(
        eczane=p, ad=f"Kiosk {i}", mac_adresi=f"10:20:30:40:50:5{i}",
        device_id=str(uuid.uuid4()), uygulama_anahtari=f"key-{i}", eczane_kiosk_no=1,
    ) for i, p in enumerate(pharmacies)]
    users = [Kullanici.objects.create_user(username=f"eczaci-status-{i}", rol="pharmacist", eczane=p) for i,p in enumerate(pharmacies)]
    admin = Kullanici.objects.create_user(username="admin-status", rol="superadmin")
    def session(index=0):
        return OturumLogu.objects.create(
            kiosk=kiosks[index], eczane=pharmacies[index], yas_araligi=YasAraligi.objects.first(),
            cinsiyet=Cinsiyet.objects.first(), qr_kodu=uuid.uuid4().hex[:8].upper(),
        )
    return pharmacies, kiosks, users, admin, session


def client(user):
    value = APIClient(); value.force_authenticate(user); return value


def test_new_session_waiting_and_review_is_idempotent(context):
    _, _, users, _, make_session = context
    row = make_session()
    assert row.status == OturumLogu.SatisDurumu.BEKLIYOR
    url = f"/api/analytics/sessions/{row.id}/mark-reviewed/"
    assert client(users[0]).post(url).status_code == 200
    assert client(users[0]).post(url).status_code == 200
    row.refresh_from_db()
    assert row.status == OturumLogu.SatisDurumu.INCELENDI
    assert row.result_at is None


def test_review_and_complete_are_historical_pharmacy_scoped(context):
    _, _, users, _, make_session = context
    row = make_session()
    assert client(users[1]).post(f"/api/analytics/sessions/{row.id}/mark-reviewed/").status_code == 404
    assert client(users[1]).post(f"/api/analytics/sessions/{row.id}/complete/", {"sale_result":"not_sold"}, format="json").status_code == 404


def test_sale_transitions_result_time_and_does_not_regress(context):
    _, _, users, _, make_session = context
    row = make_session()
    response = client(users[0]).post(
        f"/api/analytics/sessions/{row.id}/complete/",
        {"sale_result":"sold", "note":"Danışıldı"}, format="json",
    )
    assert response.status_code == 200
    row.refresh_from_db()
    assert row.status == OturumLogu.SatisDurumu.SATIS_YAPILDI and row.result_at is not None
    client(users[0]).post(f"/api/analytics/sessions/{row.id}/mark-reviewed/")
    row.refresh_from_db(); assert row.status == OturumLogu.SatisDurumu.SATIS_YAPILDI


def test_ingredient_validation_duplicate_and_not_sold_conflict(context):
    _, _, users, _, make_session = context
    ingredient = EtkenMadde.objects.create(ad="Status Etken", aktif=True)
    row = make_session()
    response = client(users[0]).post(
        f"/api/analytics/sessions/{row.id}/complete/",
        {"sale_result":"sold", "ingredient_ids":[ingredient.id, ingredient.id]}, format="json",
    )
    assert response.status_code == 200
    assert OturumOnerilenEtkenMadde.objects.filter(oturum=row, etken_madde=ingredient).count() == 1
    other = make_session()
    assert client(users[0]).post(
        f"/api/analytics/sessions/{other.id}/complete/",
        {"sale_result":"not_sold", "ingredient_ids":[ingredient.id]}, format="json",
    ).status_code == 400
    invalid = make_session()
    assert client(users[0]).post(
        f"/api/analytics/sessions/{invalid.id}/complete/",
        {"sale_result":"sold", "ingredient_ids":[999999]}, format="json",
    ).status_code == 400


def test_dashboard_series_full_period_and_scope(context):
    _, _, users, admin, make_session = context
    one = make_session(0); two = make_session(1)
    now = timezone.now()
    OturumLogu.objects.filter(pk=one.pk).update(status=2, result_at=now)
    response = client(users[0]).get("/api/analytics/dashboard-series/")
    assert response.status_code == 200
    assert len(response.data["monthly_interactions"]) in (28,29,30,31)
    assert len(response.data["weekly_interactions"]) == 7
    assert sum(x["value"] for x in response.data["monthly_interactions"]) == 1
    assert sum(x["value"] for x in client(admin).get("/api/analytics/dashboard-series/").data["monthly_interactions"]) == 2


def test_kiosk_transfer_keeps_identity_and_historical_sessions(context):
    pharmacies, kiosks, _, admin, make_session = context
    kiosk = kiosks[0]; old = make_session(0)
    KioskEczaneAtama.objects.create(kiosk=kiosk, eczane=pharmacies[0], baslangic_zamani=kiosk.olusturulma_tarihi)
    identity = (kiosk.mac_adresi, kiosk.device_id, kiosk.uygulama_anahtari)
    response = client(admin).post(f"/api/pharmacies/kiosks/{kiosk.id}/transfer/", {"eczane_id":pharmacies[1].id}, format="json")
    assert response.status_code == 200
    kiosk.refresh_from_db(); old.refresh_from_db()
    assert (kiosk.mac_adresi, kiosk.device_id, kiosk.uygulama_anahtari) == identity
    assert old.eczane_id == pharmacies[0].id
    assert KioskEczaneAtama.objects.filter(kiosk=kiosk, bitis_zamani__isnull=True, eczane=pharmacies[1]).count() == 1
    assert client(admin).post(f"/api/pharmacies/kiosks/{kiosk.id}/transfer/", {"eczane_id":pharmacies[1].id}, format="json").status_code == 409
