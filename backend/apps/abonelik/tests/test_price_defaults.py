import datetime as dt
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.abonelik.models import FiyatTanimi, Sozlesme
from apps.abonelik.serializers import CihazOdemePlaniSerializer


@pytest.fixture
def price(db):
    return FiyatTanimi.objects.create(abonelik_bedeli=Decimal('5200.00'), abonelik_kdv_orani=20,
        cihaz_kdv_orani=10, gecerlilik_baslangic=timezone.localdate() - dt.timedelta(days=60))


def test_active_price_includes_vat_and_excludes_future(price, admin_client):
    FiyatTanimi.objects.create(abonelik_bedeli=Decimal('9000.00'), abonelik_kdv_orani=1,
        cihaz_kdv_orani=20, gecerlilik_baslangic=timezone.localdate() + dt.timedelta(days=60))
    r = admin_client.get('/api/abonelik/fiyatlar/aktif/')
    assert r.status_code == 200
    assert r.json()['abonelik_bedeli'] == '5200.00'
    assert r.json()['abonelik_kdv_orani'] == 20
    assert r.json()['cihaz_kdv_orani'] == 10


def test_contract_missing_fields_copy_price_and_remain_independent(price, admin_client, eczane):
    r = admin_client.post('/api/abonelik/sozlesmeler/', {
        'eczane': eczane.pk, 'tur': 'STANDART', 'sozlesme_tipi_ay': 24,
        'baslangic_tarihi': str(timezone.localdate()),
    }, format='json')
    assert r.status_code == 201, r.content
    assert r.json()['aylik_kullanim_bedeli'] == '5200.00'
    assert r.json()['kdv_orani'] == 20
    price.abonelik_bedeli = Decimal('7000.00')
    price.abonelik_kdv_orani = 10
    price.save()
    s = Sozlesme.objects.get(pk=r.json()['id'])
    assert s.aylik_kullanim_bedeli == Decimal('5200.00') and s.kdv_orani == 20
    r = admin_client.patch(f'/api/abonelik/sozlesmeler/{s.pk}/', {'notlar': 'Güncelleme'}, format='json')
    assert r.status_code == 200, r.content
    assert r.json()['aylik_kullanim_bedeli'] == '5200.00' and r.json()['kdv_orani'] == 20


def test_explicit_zero_contract_vat_is_not_overridden(price, admin_client, eczane):
    r = admin_client.post('/api/abonelik/sozlesmeler/', {
        'eczane': eczane.pk, 'tur': 'STANDART', 'sozlesme_tipi_ay': 24,
        'baslangic_tarihi': str(timezone.localdate()), 'aylik_kullanim_bedeli': '0.00', 'kdv_orani': 0,
    }, format='json')
    assert r.status_code == 201, r.content
    assert r.json()['aylik_kullanim_bedeli'] == '0.00' and r.json()['kdv_orani'] == 0


@pytest.mark.parametrize('field', ['abonelik_kdv_orani', 'cihaz_kdv_orani'])
def test_price_vat_choices_validated(admin_client, field):
    r = admin_client.post('/api/abonelik/fiyatlar/', {
        'abonelik_bedeli': '5000.00', field: 99, 'gecerlilik_baslangic': str(timezone.localdate()),
    }, format='json')
    assert r.status_code == 400 and field in r.json()


def test_price_vat_can_be_saved_and_read(admin_client):
    r = admin_client.post('/api/abonelik/fiyatlar/', {
        'abonelik_bedeli': '5000.00', 'abonelik_kdv_orani': 20, 'cihaz_kdv_orani': 10,
        'gecerlilik_baslangic': str(timezone.localdate()),
    }, format='json')
    assert r.status_code == 201, r.content
    assert r.json()['abonelik_kdv_orani'] == 20 and r.json()['cihaz_kdv_orani'] == 10


def test_device_plan_vat_default_and_explicit_zero(price):
    data = {'tip': 'SATILIK', 'pesin_fiyat': '1000.00', 'baslangic_tarihi': str(timezone.localdate())}
    ser = CihazOdemePlaniSerializer(data=data)
    assert ser.is_valid(), ser.errors
    assert ser.validated_data['cihaz_kdv_orani'] == 10
    ser = CihazOdemePlaniSerializer(data={**data, 'cihaz_kdv_orani': 0})
    assert ser.is_valid(), ser.errors
    assert ser.validated_data['cihaz_kdv_orani'] == 0
