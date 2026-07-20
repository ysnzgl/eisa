import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.analytics.models import OturumLogu
from apps.lookups.models import Cinsiyet, Il, Ilce, YasAraligi
from apps.lookups.seed import seed_lookups
from apps.pharmacies.models import Eczane, Kiosk
from apps.products.models import Cevap, EtkenMadde, Kategori, Soru

SESSIONS_URL = "/api/analytics/sessions/"


@pytest.fixture
def eczane(db):
    seed_lookups()
    il = Il.objects.first() or Il.objects.create(ad="Istanbul")
    ilce = Ilce.objects.filter(il=il).first() or Ilce.objects.create(il=il, ad="Merkez")
    return Eczane.objects.create(ad="Test Eczanesi Analytics", il=il, ilce=ilce)


def _auth_client_for(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


def _create_session(*, kiosk, qr_kodu="A1B2C3D4", cevaplar=None, onerilen=None):
    age = YasAraligi.objects.first()
    gender = Cinsiyet.objects.first()
    category = Kategori.objects.create(ad="Uyku", slug="uyku")
    return OturumLogu.objects.create(
        kiosk=kiosk,
        yas_araligi=age,
        cinsiyet=gender,
        kategori=category,
        hassas_akis=False,
        qr_kodu=qr_kodu,
        cevaplar=cevaplar or {},
        onerilen_etken_maddeler=onerilen or [],
        tamamlandi=True,
    )


def test_qr_lookup_success_same_pharmacy(eczaci_client, kiosk):
    oturum = _create_session(kiosk=kiosk, qr_kodu="A1B2C3D4")

    res = eczaci_client.get(SESSIONS_URL, {"qr_kodu": "A1B2C3D4"})

    assert res.status_code == 200
    assert res.data["id"] == oturum.id
    assert res.data["qr_kodu"] == "A1B2C3D4"


def test_qr_lookup_invalid_format_returns_400(eczaci_client):
    res = eczaci_client.get(SESSIONS_URL, {"qr_kodu": "abc"})

    assert res.status_code == 400
    assert "Geçersiz QR kodu" in res.data["detail"]


def test_qr_lookup_not_found_returns_404(eczaci_client):
    res = eczaci_client.get(SESSIONS_URL, {"qr_kodu": "Z9Y8X7W6"})

    assert res.status_code == 404
    assert "bulunamadı" in res.data["detail"]


def test_qr_lookup_other_pharmacy_returns_403(eczaci_client, db):
    il = Il.objects.first() or Il.objects.create(ad="Istanbul")
    ilce = Ilce.objects.filter(il=il).first() or Ilce.objects.create(il=il, ad="Merkez")
    other_pharmacy = Eczane.objects.create(ad="Diger Eczane", il=il, ilce=ilce)
    other_kiosk = Kiosk.objects.create(
        eczane=other_pharmacy,
        mac_adresi="AA:BB:CC:DD:EE:11",
        uygulama_anahtari="test-app-key-secure-48chars-other-xxxxxxxxxxx",
    )
    _create_session(kiosk=other_kiosk, qr_kodu="Q1W2E3R4")

    res = eczaci_client.get(SESSIONS_URL, {"qr_kodu": "Q1W2E3R4"})

    assert res.status_code == 403
    assert "eczanenize ait değildir" in res.data["detail"]


def test_qr_lookup_pharmacist_without_pharmacy_returns_403(db):
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username="noeczane",
        password="Str0ngPass!",
        rol="pharmacist",
        eczane=None,
    )
    client = _auth_client_for(user)

    res = client.get(SESSIONS_URL, {"qr_kodu": "A1B2C3D4"})

    assert res.status_code == 403
    assert "eczaneye bağlı" in res.data["detail"]


def test_qr_lookup_resolves_answers_and_ingredients(eczaci_client, kiosk):
    category = Kategori.objects.create(ad="Enerji", slug="enerji")
    question = Soru.objects.create(kategori=category, metin="Uykuya dalmak zor mu?", sira=1)
    answer = Cevap.objects.create(soru=question, metin="Evet", agirlik=10)
    ingredient = EtkenMadde.objects.create(ad="Melatonin")

    age = YasAraligi.objects.first()
    gender = Cinsiyet.objects.first()
    OturumLogu.objects.create(
        kiosk=kiosk,
        yas_araligi=age,
        cinsiyet=gender,
        kategori=category,
        qr_kodu="M1N2B3V4",
        cevaplar={str(question.id): answer.id, f"q_{question.id}": "Y", "999": 777},
        onerilen_etken_maddeler=[ingredient.id, "Valerian"],
        tamamlandi=True,
    )

    res = eczaci_client.get(SESSIONS_URL, {"qr_kodu": "M1N2B3V4"})

    assert res.status_code == 200
    assert len(res.data["cevap_detaylari"]) >= 2
    assert any(item["soru_metni"] == "Uykuya dalmak zor mu?" for item in res.data["cevap_detaylari"])
    assert any(item["cevap_metni"] == "Evet" for item in res.data["cevap_detaylari"])
    assert any(item["ad"] == "Melatonin" for item in res.data["onerilen_etken_madde_detaylari"])


def test_complete_session_accepts_sale_result(eczaci_client, kiosk):
    oturum = _create_session(kiosk=kiosk, qr_kodu="T1Y2U3I4")

    res = eczaci_client.post(
        f"/api/analytics/sessions/{oturum.id}/complete/",
        {"note": "Danışma tamamlandı", "sale_result": "sold"},
        format="json",
    )

    assert res.status_code == 200
    assert res.data["danisma_tamamlandi"] is True
    assert res.data["satis_sonucu"] == "Satış yapıldı"


def test_complete_session_invalid_sale_result_returns_400(eczaci_client, kiosk):
    oturum = _create_session(kiosk=kiosk, qr_kodu="L1K2J3H4")

    res = eczaci_client.post(
        f"/api/analytics/sessions/{oturum.id}/complete/",
        {"sale_result": "maybe"},
        format="json",
    )

    assert res.status_code == 400


def test_complete_session_blocks_other_pharmacy(eczaci_client, db):
    il = Il.objects.first() or Il.objects.create(ad="Istanbul")
    ilce = Ilce.objects.filter(il=il).first() or Ilce.objects.create(il=il, ad="Merkez")
    other_pharmacy = Eczane.objects.create(ad="Diger Eczane 2", il=il, ilce=ilce)
    other_kiosk = Kiosk.objects.create(
        eczane=other_pharmacy,
        mac_adresi="AA:BB:CC:DD:EE:22",
        uygulama_anahtari="test-app-key-secure-48chars-other2-xxxxxxxxxx",
    )
    oturum = _create_session(kiosk=other_kiosk, qr_kodu="P1O2I3U4")

    res = eczaci_client.post(
        f"/api/analytics/sessions/{oturum.id}/complete/",
        {"note": "test"},
        format="json",
    )

    assert res.status_code == 404
