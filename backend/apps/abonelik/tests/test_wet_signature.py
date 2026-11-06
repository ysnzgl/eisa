import datetime as dt

import pytest
from django.utils import timezone

from apps.abonelik import services
from apps.abonelik.models import Sozlesme
from apps.abonelik.serializers import SozlesmeSerializer


@pytest.fixture
def wet_contract(eczaci):
    s = Sozlesme.objects.get(eczane=eczaci.eczane)
    s.imza_tipi = 'ISLAK'
    s.eczaci_onay_tarihi = None
    s.save()
    return s


def test_wet_signature_without_timestamp_never_requires_approval(wet_contract):
    assert wet_contract.onay_gerekli is False
    assert SozlesmeSerializer(wet_contract).data['onay_gerekli'] is False
    assert services.panel_kisitli(wet_contract.eczane_id) == (False, '')
    services.sozlesme_onayla(wet_contract, ip_address='1.2.3.4')
    wet_contract.refresh_from_db()
    assert wet_contract.eczaci_onay_tarihi is None
    assert wet_contract.eczaci_onay_ip is None
    assert wet_contract.onayli_sozlesme_metni == ''


def test_account_and_approval_endpoint_skip_wet_signature(wet_contract, eczaci_client):
    r = eczaci_client.get('/api/abonelik/hesabim/')
    assert r.status_code == 200, r.content
    assert r.json()['onay_gerekli'] is False
    assert r.json()['panel_kisitli'] is False
    assert r.json()['sozlesme']['imza_tipi'] == 'ISLAK'
    r = eczaci_client.post(f'/api/abonelik/sozlesmelerim/{wet_contract.pk}/onayla/')
    assert r.status_code == 200, r.content
    assert r.json()['onay_gerekli'] is False
    wet_contract.refresh_from_db()
    assert wet_contract.eczaci_onay_tarihi is None
    assert wet_contract.onayli_sozlesme_metni == ''


def test_admin_approval_count_only_includes_unsigned_digital(wet_contract, admin_client):
    digital = Sozlesme.objects.create(eczane=wet_contract.eczane, baslangic_tarihi=dt.date.today(),
                                     sozlesme_tipi_ay=24, imza_tipi='DIJITAL')
    url = '/api/abonelik/talepler/onay-bekleyen/'
    r = admin_client.get(url)
    assert r.status_code == 200, r.content
    assert r.json()['sayi'] == 1
    digital.eczaci_onay_tarihi = timezone.now()
    digital.save()
    assert admin_client.get(url).json()['sayi'] == 0


def test_digital_approval_still_required(wet_contract):
    wet_contract.imza_tipi = 'DIJITAL'
    wet_contract.save()
    assert wet_contract.onay_gerekli is True
    assert services.panel_kisitli(wet_contract.eczane_id) == (True, 'SOZLESME_ONAYSIZ')
    services.sozlesme_onayla(wet_contract, ip_address='1.2.3.4')
    wet_contract.refresh_from_db()
    assert wet_contract.onay_gerekli is False
    assert wet_contract.eczaci_onay_tarihi is not None
    assert wet_contract.eczaci_onay_ip == '1.2.3.4'
