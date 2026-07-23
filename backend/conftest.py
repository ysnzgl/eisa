"""Pytest fixture'lari (yeni Turkce model adlari ile)."""
import pytest
from django.contrib.auth import get_user_model

from apps.lookups.seed import seed_lookups
from apps.lookups.models import Il, Ilce
from apps.pharmacies.models import Eczane, Kiosk

Kullanici = get_user_model()


@pytest.fixture(autouse=True)
def _seed_lookups(db):
    """Her test oncesi lookup tablolarini doldur."""
    seed_lookups()


@pytest.fixture
def eczane(db):
    il, _ = Il.objects.get_or_create(ad="Istanbul")
    ilce, _ = Ilce.objects.get_or_create(il=il, ad="Kadikoy")
    return Eczane.objects.create(
        ad="Test Eczanesi",
        il=il,
        ilce=ilce,
    )


@pytest.fixture
def il_ist(db):
    """Istanbul ili fixture."""
    il, _ = Il.objects.get_or_create(ad="Istanbul")
    return il


@pytest.fixture
def ilce_kad(db, il_ist):
    """Kadikoy ilcesi fixture."""
    ilce, _ = Ilce.objects.get_or_create(il=il_ist, ad="Kadikoy")
    return ilce


@pytest.fixture
def eczane_a(db, il_ist, ilce_kad):
    """Istanbul/Kadikoy test eczanesi A."""
    return Eczane.objects.create(
        ad="Test Eczanesi A",
        il=il_ist,
        ilce=ilce_kad,
    )


@pytest.fixture
def eczane_b(db, il_ist, ilce_kad):
    """Istanbul/Kadikoy test eczanesi B."""
    return Eczane.objects.create(
        ad="Test Eczanesi B",
        il=il_ist,
        ilce=ilce_kad,
    )


@pytest.fixture
def superadmin(db):
    return Kullanici.objects.create_user(
        username="superadmin",
        password="Str0ngPass!",
        rol="superadmin",
    )


@pytest.fixture
def eczaci(db, eczane):
    return Kullanici.objects.create_user(
        username="eczaci",
        password="Str0ngPass!",
        rol="pharmacist",
        eczane=eczane,
    )


@pytest.fixture
def kiosk(db, eczane):
    return Kiosk.objects.create(
        eczane=eczane,
        ad="Test Kiosk",
        mac_adresi="AA:BB:CC:DD:EE:FF",
        uygulama_anahtari="test-app-key-secure-48chars-xxxxxxxxxxxxxxxxxxx",
    )


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def admin_client(api_client, superadmin):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(superadmin)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def eczaci_client(api_client, eczaci):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(eczaci)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def kiosk_client(api_client, kiosk):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"AppKey {kiosk.uygulama_anahtari}",
        HTTP_X_KIOSK_MAC=kiosk.mac_adresi,
    )
    return api_client
