import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.abonelik.contract_template import render_sozlesme_html
from apps.lookups.models import Il, Ilce
from apps.pharmacies.models import Eczane
from apps.users.models import Kullanici

from ..models import BankaHesabi, SirketProfili


pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client():
    user = Kullanici.objects.create_user(
        username="company-admin", password="strong-secret", rol=Kullanici.Rol.SUPERADMIN
    )
    client = APIClient()
    client.force_authenticate(user)
    return client


def company_payload(**overrides):
    payload = {
        "ticari_unvan": "E-İSA Teknoloji A.Ş.", "marka_adi": "e-İSA",
        "vergi_dairesi": "Mimarsinan", "vergi_numarasi": "1234567890",
        "mersis_numarasi": "0123456789012345", "ticaret_sicil_numarasi": "12345",
        "kep_adresi": "eisa@hs01.kep.tr", "eposta": "muhasebe@eisa.test",
        "telefon": "+90 352 000 00 00", "web_sitesi": "https://eisa.test",
        "adres": "Teknoloji Caddesi No: 1", "ilce": "Melikgazi", "il": "Kayseri",
        "posta_kodu": "38000", "yetkili_ad_soyad": "Eisa Yetkili",
        "yetkili_unvan": "Genel Müdür",
    }
    payload.update(overrides)
    return payload


def test_admin_can_update_single_company_profile(admin_client):
    initial = admin_client.get(reverse("sirket-profili"))
    assert initial.status_code == 200
    assert SirketProfili.objects.count() == 1

    response = admin_client.put(reverse("sirket-profili"), company_payload(), format="json")
    assert response.status_code == 200
    assert response.data["ticari_unvan"] == "E-İSA Teknoloji A.Ş."
    assert SirketProfili.objects.count() == 1


def test_company_profile_validates_tax_and_mersis_numbers(admin_client):
    response = admin_client.put(
        reverse("sirket-profili"), company_payload(vergi_numarasi="123", mersis_numarasi="ABC"), format="json"
    )
    assert response.status_code == 400
    assert "vergi_numarasi" in response.data
    assert "mersis_numarasi" in response.data


def test_multiple_bank_accounts_and_single_default(admin_client):
    admin_client.put(reverse("sirket-profili"), company_payload(), format="json")
    first = admin_client.post(reverse("sirket-banka-hesabi-list"), {
        "banka_adi": "Birinci Banka", "hesap_sahibi": "E-İSA Teknoloji A.Ş.",
        "iban": "TR330006100519786457841326", "para_birimi": "TRY",
        "aktif": True, "varsayilan": True, "sira": 1,
    }, format="json")
    second = admin_client.post(reverse("sirket-banka-hesabi-list"), {
        "banka_adi": "İkinci Banka", "hesap_sahibi": "E-İSA Teknoloji A.Ş.",
        "iban": "GB82WEST12345698765432", "para_birimi": "EUR",
        "aktif": True, "varsayilan": True, "sira": 2,
    }, format="json")
    assert first.status_code == 201
    assert second.status_code == 201
    assert BankaHesabi.objects.count() == 2
    assert BankaHesabi.objects.filter(varsayilan=True).count() == 1
    assert BankaHesabi.objects.get(pk=second.data["id"]).varsayilan


def test_invalid_iban_is_rejected(admin_client):
    response = admin_client.post(reverse("sirket-banka-hesabi-list"), {
        "banka_adi": "Banka", "hesap_sahibi": "E-İSA", "iban": "TR00 HATALI",
    }, format="json")
    assert response.status_code == 400
    assert "iban" in response.data


def test_pharmacist_cannot_manage_company_profile():
    province = Il.objects.create(ad="Kayseri")
    district = Ilce.objects.create(ad="Melikgazi", il=province)
    pharmacy = Eczane.objects.create(ad="Test Eczanesi", il=province, ilce=district)
    user = Kullanici.objects.create_user(
        username="company-pharmacist", password="strong-secret",
        rol=Kullanici.Rol.ECZACI, eczane=pharmacy,
    )
    client = APIClient()
    client.force_authenticate(user)
    assert client.get(reverse("sirket-profili")).status_code == 403


def test_contract_uses_company_definition():
    SirketProfili.objects.create(**company_payload())
    province = Il.objects.create(ad="Kayseri")
    district = Ilce.objects.create(ad="Kocasinan", il=province)
    pharmacy = Eczane.objects.create(ad="Örnek Eczanesi", adres="Eczane adresi", il=province, ilce=district)

    class Contract:
        eczane = pharmacy
        aylik_kullanim_bedeli = 3900
        baslangic_tarihi = None

    html = render_sozlesme_html(Contract())
    assert "E-İSA Teknoloji A.Ş." in html
    assert "Teknoloji Caddesi No: 1 / Melikgazi / Kayseri" in html
    assert "Mimarsinan / 1234567890" in html
