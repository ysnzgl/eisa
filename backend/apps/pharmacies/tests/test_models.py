"""Pharmacy ve Kiosk model testleri."""
import pytest
from apps.pharmacies.models import Pharmacy, Kiosk


@pytest.mark.django_db
class TestPharmacyModel:
    def test_create_pharmacy(self):
        p = Pharmacy.objects.create(name="Test", city="Ankara", district="Çankaya")
        assert p.is_active is True
        assert str(p) == "Test"

    def test_db_table_name(self):
        assert Pharmacy._meta.db_table == "pharmacies"


@pytest.mark.django_db
class TestKioskModel:
    def test_create_kiosk(self, pharmacy):
        k = Kiosk.objects.create(
            pharmacy=pharmacy,
            mac_address="11:22:33:44:55:66",
            app_key="unique-key-12345",
        )
        assert k.is_active is True
        assert k.last_seen_at is None
        assert k.pharmacy == pharmacy

    def test_mac_address_unique(self, pharmacy):
        Kiosk.objects.create(pharmacy=pharmacy, mac_address="AA:AA:AA:AA:AA:AA", app_key="key1")
        with pytest.raises(Exception):
            Kiosk.objects.create(pharmacy=pharmacy, mac_address="AA:AA:AA:AA:AA:AA", app_key="key2")

    def test_app_key_unique(self, pharmacy):
        Kiosk.objects.create(pharmacy=pharmacy, mac_address="BB:BB:BB:BB:BB:BB", app_key="duplicate-key")
        with pytest.raises(Exception):
            Kiosk.objects.create(pharmacy=pharmacy, mac_address="CC:CC:CC:CC:CC:CC", app_key="duplicate-key")

    def test_db_table_name(self):
        assert Kiosk._meta.db_table == "kiosks"
