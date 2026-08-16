"""Görüş ve Destek — backend testleri."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.destek.models import DestekParametresi, DestekTalebi, DestekYorumu
from apps.destek.seed import seed_destek_parametreleri
from apps.lookups.models import Il, Ilce
from apps.pharmacies.models import Eczane, Kiosk

Kullanici = get_user_model()


# ─── Seed helper ──────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _seed_destek(db):
    """Her test öncesi destek parametrelerini doldur."""
    seed_destek_parametreleri()


# ─── Yardımcı fixture'lar ─────────────────────────────────────────────────────

@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def eczane_a(db):
    il, _ = Il.objects.get_or_create(ad="Istanbul")
    ilce, _ = Ilce.objects.get_or_create(il=il, ad="Kadikoy")
    return Eczane.objects.create(ad="Eczane A", il=il, ilce=ilce)


@pytest.fixture
def eczane_b(db):
    il, _ = Il.objects.get_or_create(ad="Istanbul")
    ilce, _ = Ilce.objects.get_or_create(il=il, ad="Kadikoy")
    return Eczane.objects.create(ad="Eczane B", il=il, ilce=ilce)


@pytest.fixture
def eczaci_a(db, eczane_a):
    return Kullanici.objects.create_user(
        username="eczaci_a", password="Pass1!", rol="pharmacist", eczane=eczane_a
    )


@pytest.fixture
def eczaci_b(db, eczane_b):
    return Kullanici.objects.create_user(
        username="eczaci_b", password="Pass1!", rol="pharmacist", eczane=eczane_b
    )


@pytest.fixture
def admin(db):
    return Kullanici.objects.create_user(
        username="admin", password="Pass1!", rol="superadmin"
    )


@pytest.fixture
def kiosk_a(db, eczane_a):
    return Kiosk.objects.create(
        eczane=eczane_a, ad="Kiosk-A1", mac_adresi="AA:BB:CC:DD:EE:01",
        uygulama_anahtari="key-a1", aktif=True,
    )


@pytest.fixture
def kiosk_b(db, eczane_b):
    return Kiosk.objects.create(
        eczane=eczane_b, ad="Kiosk-B1", mac_adresi="AA:BB:CC:DD:EE:02",
        uygulama_anahtari="key-b1", aktif=True,
    )


def _param(kod):
    return DestekParametresi.objects.get(kod=kod)


def _talep(eczane, kullanici, alan_kod="KIOSK", alt_konu_kod="KIOSK_SORU",
           talep_turu_kod="ONERI", durum_kod="YENI", aciklama="Test açıklaması."):
    return DestekTalebi.objects.create(
        talep_no=f"EISA-2026-{DestekTalebi.objects.count() + 1:06d}",
        eczane=eczane,
        olusturan_kullanici=kullanici,
        talep_turu=_param(talep_turu_kod),
        alan=_param(alan_kod),
        alt_konu=_param(alt_konu_kod),
        durum=_param(durum_kod),
        aciklama=aciklama,
    )


# ─── 1. Parametre seed ve hiyerarşi ───────────────────────────────────────────

class TestParametreSeed:
    def test_talep_turu_grubu_var(self, db, _seed_destek):
        kodlar = set(DestekParametresi.objects.filter(grup="TALEP_TURU").values_list("kod", flat=True))
        assert {"ONERI", "SIKAYET"} == kodlar

    def test_alan_grubu_var(self, db, _seed_destek):
        kodlar = set(DestekParametresi.objects.filter(grup="ALAN").values_list("kod", flat=True))
        assert {"KIOSK", "PORTAL"} == kodlar

    def test_durum_grubu_var(self, db, _seed_destek):
        kodlar = set(DestekParametresi.objects.filter(grup="DURUM").values_list("kod", flat=True))
        assert {"YENI", "INCELENIYOR", "YANITLANDI", "KAPATILDI"} == kodlar

    def test_kiosk_alt_konulari_ust_parametreye_bagli(self, db, _seed_destek):
        kiosk = _param("KIOSK")
        alt_konular = DestekParametresi.objects.filter(grup="ALT_KONU", ust_parametre=kiosk)
        kodlar = set(alt_konular.values_list("kod", flat=True))
        assert "KIOSK_CIHAZ" in kodlar
        assert "KIOSK_DIGER" in kodlar
        assert all(k.startswith("KIOSK_") for k in kodlar)

    def test_portal_alt_konulari_ust_parametreye_bagli(self, db, _seed_destek):
        portal = _param("PORTAL")
        alt_konular = DestekParametresi.objects.filter(grup="ALT_KONU", ust_parametre=portal)
        kodlar = set(alt_konular.values_list("kod", flat=True))
        assert "PORTAL_DASHBOARD" in kodlar
        assert all(k.startswith("PORTAL_") for k in kodlar)

    def test_seed_idempotent(self, db, _seed_destek):
        ilk_sayi = DestekParametresi.objects.count()
        seed_destek_parametreleri()
        assert DestekParametresi.objects.count() == ilk_sayi


# ─── 2. Ticket oluşturma ──────────────────────────────────────────────────────

class TestTalepOlusturma:
    def _post(self, api, kullanici, payload):
        api.force_authenticate(user=kullanici)
        return api.post("/api/destek/talepler/", payload, format="json")

    def test_eczaci_talep_olusturabilir(self, api, eczaci_a):
        r = self._post(api, eczaci_a, {
            "talep_turu_id": _param("ONERI").pk,
            "alan_id": _param("PORTAL").pk,
            "alt_konu_id": _param("PORTAL_DASHBOARD").pk,
            "aciklama": "Test öneri açıklaması.",
        })
        assert r.status_code == 201
        assert r.data["talep_no"].startswith("EISA-")
        assert r.data["durum_kod"] == "YENI"
        assert r.data["eczane_adi"] == eczaci_a.eczane.ad

    def test_admin_talep_olusturamaz(self, api, admin):
        r = self._post(api, admin, {
            "talep_turu_id": _param("ONERI").pk,
            "alan_id": _param("PORTAL").pk,
            "alt_konu_id": _param("PORTAL_DASHBOARD").pk,
            "aciklama": "Admin ticket.",
        })
        assert r.status_code == 403

    def test_pasif_parametre_ile_olusturulamaz(self, api, eczaci_a):
        p = _param("ONERI")
        p.aktif = False
        p.save()
        r = self._post(api, eczaci_a, {
            "talep_turu_id": p.pk,
            "alan_id": _param("PORTAL").pk,
            "alt_konu_id": _param("PORTAL_DASHBOARD").pk,
            "aciklama": "Test.",
        })
        assert r.status_code == 400

    def test_yanlis_gruptaki_parametre_ile_olusturulamaz(self, api, eczaci_a):
        # alan_id alanına TALEP_TURU grubundan parametre gönder
        r = self._post(api, eczaci_a, {
            "talep_turu_id": _param("ONERI").pk,
            "alan_id": _param("ONERI").pk,  # yanlış grup
            "alt_konu_id": _param("PORTAL_DASHBOARD").pk,
            "aciklama": "Test.",
        })
        assert r.status_code == 400

    def test_alt_konu_alan_eslesmesi_kontrol_edilir(self, api, eczaci_a):
        # Kiosk alanı seçilip Portal alt konusu gönderilirse hata vermeli
        r = self._post(api, eczaci_a, {
            "talep_turu_id": _param("ONERI").pk,
            "alan_id": _param("KIOSK").pk,
            "alt_konu_id": _param("PORTAL_DASHBOARD").pk,  # yanlış
            "aciklama": "Test.",
        })
        assert r.status_code == 400

    def test_portal_seciminde_kiosk_bos_olmali(self, api, eczaci_a, kiosk_a):
        r = self._post(api, eczaci_a, {
            "talep_turu_id": _param("ONERI").pk,
            "alan_id": _param("PORTAL").pk,
            "alt_konu_id": _param("PORTAL_DASHBOARD").pk,
            "kiosk_id": kiosk_a.pk,
            "aciklama": "Test.",
        })
        assert r.status_code == 400

    def test_baska_eczanenin_kiosku_secilememez(self, api, eczaci_a, kiosk_b):
        r = self._post(api, eczaci_a, {
            "talep_turu_id": _param("ONERI").pk,
            "alan_id": _param("KIOSK").pk,
            "alt_konu_id": _param("KIOSK_SORU").pk,
            "kiosk_id": kiosk_b.pk,  # Eczane B'nin kiosku
            "aciklama": "Test.",
        })
        assert r.status_code == 400

    def test_talep_no_benzersiz(self, api, eczaci_a):
        r1 = self._post(api, eczaci_a, {
            "talep_turu_id": _param("ONERI").pk,
            "alan_id": _param("PORTAL").pk,
            "alt_konu_id": _param("PORTAL_DASHBOARD").pk,
            "aciklama": "Birinci.",
        })
        r2 = self._post(api, eczaci_a, {
            "talep_turu_id": _param("SIKAYET").pk,
            "alan_id": _param("PORTAL").pk,
            "alt_konu_id": _param("PORTAL_DIGER").pk,
            "aciklama": "İkinci.",
        })
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.data["talep_no"] != r2.data["talep_no"]

    def test_aciklama_1000_karakter_siniri(self, api, eczaci_a):
        r = self._post(api, eczaci_a, {
            "talep_turu_id": _param("ONERI").pk,
            "alan_id": _param("PORTAL").pk,
            "alt_konu_id": _param("PORTAL_DASHBOARD").pk,
            "aciklama": "x" * 1001,
        })
        assert r.status_code == 400

    def test_eczane_backend_tarafindan_atanir(self, api, eczaci_a):
        r = self._post(api, eczaci_a, {
            "talep_turu_id": _param("ONERI").pk,
            "alan_id": _param("PORTAL").pk,
            "alt_konu_id": _param("PORTAL_DASHBOARD").pk,
            "aciklama": "Test.",
        })
        assert r.status_code == 201
        talep = DestekTalebi.objects.get(talep_no=r.data["talep_no"])
        assert talep.eczane_id == eczaci_a.eczane_id
        assert talep.olusturan_kullanici_id == eczaci_a.pk
        assert talep.durum.kod == "YENI"


# ─── 3. Ticket listeleme ve izolasyon ─────────────────────────────────────────

class TestTalepListeIzolasyon:
    def test_eczaci_sadece_kendi_eczanesini_gorur(self, api, eczaci_a, eczaci_b, eczane_a, eczane_b):
        _talep(eczane_a, eczaci_a)
        _talep(eczane_b, eczaci_b)

        api.force_authenticate(user=eczaci_a)
        r = api.get("/api/destek/talepler/")
        assert r.status_code == 200
        ids = [t["eczane_adi"] for t in r.data["results"]]
        assert all(name == eczane_a.ad for name in ids)

    def test_eczaci_baska_eczane_detayina_erisemez(self, api, eczaci_a, eczane_b, eczaci_b):
        t = _talep(eczane_b, eczaci_b)
        api.force_authenticate(user=eczaci_a)
        r = api.get(f"/api/destek/talepler/{t.pk}/")
        assert r.status_code == 404

    def test_admin_tum_talepleri_gorur(self, api, admin, eczaci_a, eczaci_b, eczane_a, eczane_b):
        _talep(eczane_a, eczaci_a)
        _talep(eczane_b, eczaci_b)
        api.force_authenticate(user=admin)
        r = api.get("/api/destek/talepler/")
        assert r.status_code == 200
        assert r.data["count"] == 2

    def test_admin_herhangi_talep_detayini_gorur(self, api, admin, eczane_a, eczaci_a):
        t = _talep(eczane_a, eczaci_a)
        api.force_authenticate(user=admin)
        r = api.get(f"/api/destek/talepler/{t.pk}/")
        assert r.status_code == 200
        assert r.data["talep_no"] == t.talep_no

    def test_liste_sayfalama_calisiyor(self, api, admin, eczane_a, eczaci_a):
        for _ in range(5):
            _talep(eczane_a, eczaci_a)
        api.force_authenticate(user=admin)
        r = api.get("/api/destek/talepler/?page_size=3")
        assert r.status_code == 200
        assert len(r.data["results"]) == 3
        assert r.data["count"] == 5


# ─── 4. Yorum akışı ───────────────────────────────────────────────────────────

class TestYorumAkisi:
    def _yorum_ekle(self, api, kullanici, talep, metin):
        api.force_authenticate(user=kullanici)
        return api.post(f"/api/destek/talepler/{talep.pk}/yorum-ekle/",
                        {"yorum_metni": metin}, format="json")

    def test_eczaci_yorumu_yeni_sayilir(self, api, eczaci_a, eczane_a):
        t = _talep(eczane_a, eczaci_a)
        r = self._yorum_ekle(api, eczaci_a, t, "Eczacı yorumu.")
        assert r.status_code == 201

    def test_admin_yorum_yazip_durum_yanitlandi_olur(self, api, admin, eczaci_a, eczane_a):
        t = _talep(eczane_a, eczaci_a)
        self._yorum_ekle(api, admin, t, "Admin yorumu.")
        t.refresh_from_db()
        assert t.durum.kod == "YANITLANDI"

    def test_eczaci_yanitlandi_durumuna_cevap_yazarsa_inceleniyor(self, api, admin, eczaci_a, eczane_a):
        t = _talep(eczane_a, eczaci_a, durum_kod="YANITLANDI")
        self._yorum_ekle(api, eczaci_a, t, "Eczacı cevabı.")
        t.refresh_from_db()
        assert t.durum.kod == "INCELENIYOR"

    def test_kapali_talebe_yorum_eklenemez(self, api, eczaci_a, eczane_a):
        t = _talep(eczane_a, eczaci_a, durum_kod="KAPATILDI")
        r = self._yorum_ekle(api, eczaci_a, t, "Kapalı ticket yorumu.")
        assert r.status_code == 400

    def test_baska_eczane_talep_yorumu_yapamaz(self, api, eczaci_b, eczane_a, eczaci_a):
        t = _talep(eczane_a, eczaci_a)
        r = self._yorum_ekle(api, eczaci_b, t, "Farklı eczacı.")
        assert r.status_code == 404

    def test_yorum_1000_karakter_siniri(self, api, eczaci_a, eczane_a):
        t = _talep(eczane_a, eczaci_a)
        r = self._yorum_ekle(api, eczaci_a, t, "y" * 1001)
        assert r.status_code == 400

    def test_yorumlar_detail_ile_gelir(self, api, admin, eczaci_a, eczane_a):
        t = _talep(eczane_a, eczaci_a)
        DestekYorumu.objects.create(
            talep=t, yorum_metni="İlk yorum.",
            olusturan=eczaci_a, guncelleyen=eczaci_a, surum=1,
        )
        api.force_authenticate(user=admin)
        r = api.get(f"/api/destek/talepler/{t.pk}/")
        assert r.status_code == 200
        assert len(r.data["yorumlar"]) == 1

    def test_son_hareket_tarihi_yorum_sonrasi_guncellenir(self, api, eczaci_a, eczane_a):
        from django.utils import timezone
        t = _talep(eczane_a, eczaci_a)
        once = t.son_hareket_tarihi
        import time; time.sleep(0.05)
        self._yorum_ekle(api, eczaci_a, t, "Güncelleme yorumu.")
        t.refresh_from_db()
        assert t.son_hareket_tarihi > once


# ─── 5. Durum geçişleri ───────────────────────────────────────────────────────

class TestDurumGecisleri:
    def test_admin_durum_degistirebilir(self, api, admin, eczaci_a, eczane_a):
        t = _talep(eczane_a, eczaci_a)
        api.force_authenticate(user=admin)
        r = api.patch(f"/api/destek/talepler/{t.pk}/durum-degistir/",
                      {"durum_kod": "INCELENIYOR"}, format="json")
        assert r.status_code == 200
        t.refresh_from_db()
        assert t.durum.kod == "INCELENIYOR"

    def test_eczaci_durum_degistiremez(self, api, eczaci_a, eczane_a):
        t = _talep(eczane_a, eczaci_a)
        api.force_authenticate(user=eczaci_a)
        r = api.patch(f"/api/destek/talepler/{t.pk}/durum-degistir/",
                      {"durum_kod": "KAPATILDI"}, format="json")
        assert r.status_code == 403

    def test_gecersiz_durum_kodu_hata_verir(self, api, admin, eczaci_a, eczane_a):
        t = _talep(eczane_a, eczaci_a)
        api.force_authenticate(user=admin)
        r = api.patch(f"/api/destek/talepler/{t.pk}/durum-degistir/",
                      {"durum_kod": "YANLIS_DURUM"}, format="json")
        assert r.status_code == 400


# ─── 6. Admin badge ───────────────────────────────────────────────────────────

class TestYeniSayisi:
    def test_admin_yeni_sayisi_endpoint(self, api, admin, eczaci_a, eczane_a):
        _talep(eczane_a, eczaci_a, durum_kod="YENI")
        _talep(eczane_a, eczaci_a, durum_kod="KAPATILDI")
        api.force_authenticate(user=admin)
        r = api.get("/api/destek/talepler/yeni-sayisi/")
        assert r.status_code == 200
        assert r.data["sayi"] == 1

    def test_eczaci_yeni_sayisi_erisemez(self, api, eczaci_a):
        api.force_authenticate(user=eczaci_a)
        r = api.get("/api/destek/talepler/yeni-sayisi/")
        assert r.status_code == 403


# ─── 7. Filtreler ve N+1 ──────────────────────────────────────────────────────

class TestFiltrelerVePerformans:
    def test_durum_filtresi(self, api, admin, eczaci_a, eczane_a):
        _talep(eczane_a, eczaci_a, durum_kod="YENI")
        _talep(eczane_a, eczaci_a, durum_kod="KAPATILDI")
        api.force_authenticate(user=admin)
        r = api.get("/api/destek/talepler/?durum_kod=YENI")
        assert r.data["count"] == 1

    def test_acik_kategori_filtresi(self, api, eczaci_a, eczane_a):
        _talep(eczane_a, eczaci_a, durum_kod="YENI")
        _talep(eczane_a, eczaci_a, durum_kod="YANITLANDI")
        _talep(eczane_a, eczaci_a, durum_kod="KAPATILDI")
        api.force_authenticate(user=eczaci_a)
        r = api.get("/api/destek/talepler/?durum_kategori=acik")
        assert r.data["count"] == 2

    def test_talep_turu_filtresi(self, api, admin, eczaci_a, eczane_a):
        _talep(eczane_a, eczaci_a, talep_turu_kod="ONERI")
        _talep(eczane_a, eczaci_a, talep_turu_kod="SIKAYET")
        api.force_authenticate(user=admin)
        r = api.get("/api/destek/talepler/?talep_turu_kod=SIKAYET")
        assert r.data["count"] == 1

    def test_liste_n_plus_1_yok(self, api, admin, eczaci_a, eczane_a):
        # select_related ile N+1 olmamalı; 5 kayıt için sabit sayıda sorgu yapılmalı.
        for _ in range(5):
            _talep(eczane_a, eczaci_a)
        api.force_authenticate(user=admin)
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        with CaptureQueriesContext(connection) as ctx5:
            api.get("/api/destek/talepler/?page_size=5")
        count_5 = len(ctx5)
        # 5 kayıt daha ekle — sorgu sayısı artmamalı (N+1 yok)
        for _ in range(5):
            _talep(eczane_a, eczaci_a)
        api.force_authenticate(user=admin)
        with CaptureQueriesContext(connection) as ctx10:
            api.get("/api/destek/talepler/?page_size=10")
        count_10 = len(ctx10)
        assert count_10 == count_5, f"N+1 şüphesi: 5 kayıt={count_5}, 10 kayıt={count_10}"


# ─── 8. Parametre endpoint ────────────────────────────────────────────────────

class TestParametreEndpoint:
    def test_aktif_parametreler_geliyor(self, api, eczaci_a):
        api.force_authenticate(user=eczaci_a)
        r = api.get("/api/destek/parametreler/")
        assert r.status_code == 200
        gruplar = {p["grup"] for p in r.data}
        assert "TALEP_TURU" in gruplar
        assert "ALAN" in gruplar
        assert "ALT_KONU" in gruplar
        assert "DURUM" in gruplar

    def test_pasif_parametre_gelmiyor(self, api, eczaci_a):
        p = _param("KIOSK_DIGER")
        p.aktif = False
        p.save()
        api.force_authenticate(user=eczaci_a)
        r = api.get("/api/destek/parametreler/")
        kodlar = [p["kod"] for p in r.data]
        assert "KIOSK_DIGER" not in kodlar
