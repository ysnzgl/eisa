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
    il = Il.objects.get(ad="Istanbul")
    ilce = Ilce.objects.filter(il=il).first()
    return Eczane.objects.create(
        ad="Test Eczanesi",
        il=il,
        ilce=ilce,
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
