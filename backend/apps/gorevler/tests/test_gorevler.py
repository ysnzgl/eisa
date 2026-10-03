"""İş takip API testleri."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.gorevler.models import Gorev

Kullanici = get_user_model()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def admin(db):
    return Kullanici.objects.create_user(username="admin", password="Pass1!", rol="superadmin")


@pytest.fixture
def ikinci_admin(db):
    return Kullanici.objects.create_user(username="admin2", password="Pass1!", rol="superadmin")


@pytest.fixture
def eczaci(db):
    return Kullanici.objects.create_user(username="eczaci", password="Pass1!", rol="pharmacist")


def _post(api, user, payload):
    api.force_authenticate(user=user)
    return api.post("/api/is-takip/gorevler/", payload, format="json")


def _patch(api, user, gorev_id, payload):
    api.force_authenticate(user=user)
    return api.patch(f"/api/is-takip/gorevler/{gorev_id}/", payload, format="json")


def _delete(api, user, gorev_id):
    api.force_authenticate(user=user)
    return api.delete(f"/api/is-takip/gorevler/{gorev_id}/")


def test_superadmin_gorev_olusturabilir(api, admin, ikinci_admin):
    r = _post(api, admin, {
        "baslik": "Sunucu kontrolü",
        "icerik": "Yedekleme tamamlandı mı kontrol et.",
        "durum": "INCELENIYOR",
        "atanan_kullanici_id": ikinci_admin.pk,
    })
    assert r.status_code == 201
    assert r.data["baslik"] == "Sunucu kontrolü"
    assert r.data["durum"] == "INCELENIYOR"
    assert r.data["atanan_kullanici_id"] == ikinci_admin.pk
    assert r.data["atanan_kullanici_adi"] == (ikinci_admin.get_full_name() or ikinci_admin.username)


def test_icerik_iki_bin_karakterden_uzun_olabilir(api, admin):
    uzun_icerik = ("Uzun iş notu ve uygulama ayrıntıları.\n" * 150).strip()

    r = _post(api, admin, {
        "baslik": "Uzun içerikli iş",
        "icerik": uzun_icerik,
    })

    assert len(uzun_icerik) > 2000
    assert r.status_code == 201
    assert r.data["icerik"] == uzun_icerik
    assert Gorev.objects.get(pk=r.data["id"]).icerik == uzun_icerik


def test_pharmacist_erisim_aldirilir(api, eczaci):
    r = _post(api, eczaci, {
        "baslik": "Yetkisiz",
        "icerik": "Bu kayıt oluşturulmamalı.",
    })
    assert r.status_code == 403


def test_eczaci_atanan_kullanici_olamaz(api, admin, eczaci):
    r = _post(api, admin, {
        "baslik": "Kısıt",
        "icerik": "Eczacı atanamamalı.",
        "atanan_kullanici_id": eczaci.pk,
    })
    assert r.status_code == 400


def test_status_guncellenebilir(api, admin):
    gorev = Gorev.objects.create(
        baslik="Kontrol",
        icerik="Durum güncelleme testi.",
        durum=Gorev.Durum.YENI,
        olusturan=admin,
        guncelleyen=admin,
    )

    r = _patch(api, admin, gorev.pk, {"durum": "YAPILDI"})
    assert r.status_code == 200
    assert r.data["durum"] == "YAPILDI"


def test_gorev_iptal_durumuna_alinabilir(api, admin):
    gorev = Gorev.objects.create(
        baslik="İptal edilecek iş",
        icerik="Bu iş artık yapılmayacak.",
        durum=Gorev.Durum.YENI,
        olusturan=admin,
        guncelleyen=admin,
    )

    r = _patch(api, admin, gorev.pk, {"durum": "IPTAL"})

    assert r.status_code == 200
    assert r.data["durum"] == "IPTAL"
    assert r.data["durum_ad"] == "İptal"
    gorev.refresh_from_db()
    assert gorev.durum == Gorev.Durum.IPTAL


def test_superadmin_gorev_silebilir(api, admin):
    gorev = Gorev.objects.create(
        baslik="Silinecek iş",
        icerik="Bu kayıt silinecek.",
        olusturan=admin,
        guncelleyen=admin,
    )

    r = _delete(api, admin, gorev.pk)

    assert r.status_code == 204
    assert not Gorev.objects.filter(pk=gorev.pk).exists()


def test_pharmacist_gorev_silemez(api, admin, eczaci):
    gorev = Gorev.objects.create(
        baslik="Korunan iş",
        icerik="Yetkisiz kullanıcı silememeli.",
        olusturan=admin,
        guncelleyen=admin,
    )

    r = _delete(api, eczaci, gorev.pk)

    assert r.status_code == 403
    assert Gorev.objects.filter(pk=gorev.pk).exists()
