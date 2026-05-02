"""Proje genelinde paylaşılan pytest fixture'ları."""
import pytest
from django.contrib.auth import get_user_model

from apps.pharmacies.models import Pharmacy, Kiosk

User = get_user_model()


@pytest.fixture
def pharmacy(db):
    return Pharmacy.objects.create(
        name="Test Eczanesi",
        city="İstanbul",
        district="Kadıköy",
    )


@pytest.fixture
def superadmin(db):
    return User.objects.create_user(
        username="superadmin",
        password="Str0ngPass!",
        role="superadmin",
    )


@pytest.fixture
def pharmacist(db, pharmacy):
    return User.objects.create_user(
        username="pharmacist",
        password="Str0ngPass!",
        role="pharmacist",
        pharmacy=pharmacy,
    )


@pytest.fixture
def kiosk(db, pharmacy):
    return Kiosk.objects.create(
        pharmacy=pharmacy,
        mac_address="AA:BB:CC:DD:EE:FF",
        app_key="test-app-key-secure-48chars-xxxxxxxxxxxxxxxxxxx",
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
def pharmacist_client(api_client, pharmacist):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(pharmacist)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def kiosk_client(api_client, kiosk):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"AppKey {kiosk.app_key}",
        HTTP_X_KIOSK_MAC=kiosk.mac_address,
    )
    return api_client
