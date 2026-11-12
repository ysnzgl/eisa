"""Sözleşme geçişi incelemesinde bulunan mali akış regresyonları."""
import datetime as dt
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.abonelik import services
from apps.abonelik.invoice_corrections import correct, preview
from apps.abonelik.models import CihazOdemePlani, Fatura, Sozlesme, SozlesmeTalebi
from apps.campaigns.models import Bolge, BolgeKapsam, SponsorlukTarifesi


pytestmark = pytest.mark.django_db


def test_ay_sonu_gunu_oteleme_ve_kisa_ay_sonrasi_korunur(eczane):
    contract = Sozlesme.objects.create(eczane=eczane, sozlesme_tipi_ay=12,
        baslangic_tarihi=dt.date(2026, 1, 31), oteleme_ay=1)
    plan = CihazOdemePlani.objects.create(sozlesme=contract, pesin_fiyat=Decimal("100"),
        taksit_sayisi=3, oteleme_ay=1, baslangic_tarihi=dt.date(2026, 2, 28))
    services.faturala_ayri(bugun=dt.date(2026, 2, 28), sozlesme_id=contract.pk)
    assert services.faturala_ayri(bugun=dt.date(2026, 3, 28), sozlesme_id=contract.pk) == 0
    assert services.faturala_ayri(bugun=dt.date(2026, 3, 31), sozlesme_id=contract.pk) == 2
    assert set(Fatura.objects.filter(donem="2026-03").values_list("hizmet_baslangic", flat=True)) == {dt.date(2026, 3, 31)}
    services.faturala_ayri(bugun=dt.date(2026, 4, 30), sozlesme_id=contract.pk)
    assert sum(Fatura.objects.filter(cihaz_plani=plan).values_list("matrah", flat=True)) == Decimal("100.00")


def test_gecmis_donemde_gercek_kesim_ve_vade_bugunden_hesaplanir(eczane):
    contract = Sozlesme.objects.create(eczane=eczane, sozlesme_tipi_ay=12, baslangic_tarihi=dt.date(2026, 1, 8))
    services.faturala_ayri(bugun=dt.date(2026, 3, 10), sozlesme_id=contract.pk)
    invoices = Fatura.objects.filter(sozlesme=contract)
    assert invoices.count() == 3
    assert set(invoices.values_list("kesim_tarihi", flat=True)) == {dt.date(2026, 3, 10)}
    assert set(invoices.values_list("vade_tarihi", flat=True)) == {dt.date(2026, 3, 19)}


def test_yeniden_hesaplamada_vergi_ve_tevkifat_kaybolmaz(eczane):
    contract = Sozlesme.objects.create(eczane=eczane, sozlesme_tipi_ay=12,
        baslangic_tarihi=dt.date(2026, 1, 8), aylik_kullanim_bedeli=Decimal("1000"),
        kdv_orani=20, tevkifat_orani="5/10")
    services.faturala_ayri(bugun=dt.date(2026, 1, 8), sozlesme_id=contract.pk)
    invoice = Fatura.objects.get(sozlesme=contract)
    data = preview(invoice)
    assert data["yeni_tutar"] == "1100.00"
    correct(invoice.pk, islem="YENIDEN_OLUSTUR", neden="Tutar kontrolü", surum=invoice.surum,
            user=None, onizleme_anahtari=data["onizleme_anahtari"])
    invoice.refresh_from_db()
    line = invoice.kalemler.get()
    assert (invoice.matrah, invoice.kdv_tutari, invoice.tevkifat_tutari) == (Decimal("1000"), Decimal("200"), Decimal("100"))
    assert line.kdv_orani == 20 and line.tevkifat_orani == "5/10"
    assert invoice.tutar == line.tutar == Decimal("1100")
    assert invoice.islemler.get().sonraki["kdv_tutari"] == "200.00"


@pytest.mark.parametrize("entry", ["direct", "nested", "request"])
def test_tum_olusturma_yollarinda_tahsis_snapshot_ve_ilk_fatura(admin_client, eczane, entry):
    today = timezone.localdate()
    region = Bolge.objects.create(kod="TR", ad="Test", gecerlilik_baslangic=today)
    BolgeKapsam.objects.create(bolge=region, il=eczane.il)
    SponsorlukTarifesi.objects.create(kod="TR", ad="Test", tur="ECZANE", brut_bedel=100,
        gecerlilik_baslangic=today)
    plan = {"tip": "TAHSIS", "adet": 1, "pesin_fiyat": "", "tahsis_bedeli": "",
            "donanim_degeri": "", "aylik_kira_bedeli": ""}
    payload = {"tur": "STANDART", "sozlesme_tipi_ay": 24, "baslangic_tarihi": str(today),
               "cihaz_planlari": [plan]}
    if entry == "direct":
        r = admin_client.post("/api/abonelik/sozlesmeler/", {**payload, "eczane": eczane.pk}, format="json")
        assert r.status_code == 201, r.content
        contract = Sozlesme.objects.get(pk=r.data["id"])
    elif entry == "nested":
        r = admin_client.post("/api/pharmacies/", {"ad": "Yeni", "il": eczane.il_id,
            "ilce": eczane.ilce_id, "sozlesme": payload}, format="json")
        assert r.status_code == 201, r.content
        contract = Sozlesme.objects.get(eczane_id=r.data["id"])
    else:
        request = SozlesmeTalebi.objects.create(eczane=eczane, talep_tipi="YENI", istenen_tur="STANDART", istenen_tip_ay=24)
        services.karar_ver_talep(request, onayla=True, detail_data=payload)
        contract = Sozlesme.objects.get(eczane=eczane)
    assert contract.bolge_snapshot["id"] == region.pk
    assert contract.sponsorluk_tarifeleri_snapshot[0]["kod"] == "TR"
    assert contract.cihaz_planlari.get().tip == "TAHSIS"
    assert contract.faturalar.get().tip == Fatura.Tip.KULLANIM_BEDELI


def test_hatali_cihaz_guncellemesinde_sozlesme_degisikligi_geri_alinir(admin_client, eczane):
    contract = Sozlesme.objects.create(eczane=eczane, sozlesme_tipi_ay=24, baslangic_tarihi=timezone.localdate())
    r = admin_client.patch(f"/api/abonelik/sozlesmeler/{contract.pk}/", {
        "notlar": "Kaydedilmemeli", "cihaz_planlari": [{"id": 999999, "tip": "TAHSIS"}],
    }, format="json")
    assert r.status_code == 400
    contract.refresh_from_db()
    assert contract.notlar == ""


def test_yeni_dijital_onay_eski_metinle_yapilamaz(admin_client, eczane):
    r = admin_client.post("/api/abonelik/sozlesmeler/", {"eczane": eczane.pk,
        "sozlesme_tipi_ay": 24, "baslangic_tarihi": str(timezone.localdate()),
        "imza_tipi": "DIJITAL", "sozlesme_surumu": "LEGACY"}, format="json")
    assert r.status_code == 400
    assert "imza_tipi" in r.data


def test_eski_sozlesmede_ceza_katsayisi_korunur(eczane, monkeypatch):
    monkeypatch.setattr(timezone, "localdate", lambda: dt.date(2026, 1, 1))
    contract = Sozlesme.objects.create(eczane=eczane, sozlesme_tipi_ay=12,
        baslangic_tarihi=dt.date(2026, 1, 1), aylik_kullanim_bedeli=Decimal("100"),
        sozlesme_surumu="LEGACY", iptal_ceza_orani=Decimal("2"))
    assert contract.iptal_ceza_tutari == Decimal("2433.33")


@pytest.mark.parametrize("taksit", [0, 6])
def test_pesin_ve_alti_taksit_api_destegi(admin_client, eczane, taksit):
    r = admin_client.post("/api/abonelik/sozlesmeler/", {"eczane": eczane.pk,
        "sozlesme_tipi_ay": 24, "baslangic_tarihi": str(timezone.localdate()),
        "cihaz_planlari": [{"tip": "SATILIK", "pesin_fiyat": "1000", "taksit_sayisi": taksit}]}, format="json")
    assert r.status_code == 201, r.content
    assert r.data["cihaz_planlari"][0]["taksit_sayisi"] == (taksit or 1)


@pytest.mark.parametrize("kind", ["SOZLESME_EK1", "EK2"])
def test_eczaci_yalniz_kendi_imzali_belgesini_indirebilir(eczaci_client, eczaci, monkeypatch, kind):
    import io
    from unittest.mock import MagicMock
    contract = Sozlesme.objects.get(eczane=eczaci.eczane)
    contract.islak_imza_url = "sozlesmeler/ek1.pdf"
    contract.ek2_islak_imza_url = "sozlesmeler/ek2.pdf"
    contract.save()
    storage = MagicMock()
    storage.client.get_object.return_value = io.BytesIO(b"%PDF-test")
    monkeypatch.setattr("apps.core.services.storage_service.StorageService", lambda: storage)
    r = eczaci_client.get(f"/api/abonelik/sozlesmeler/{contract.pk}/islak-imza-indir/?belge_turu={kind}")
    assert r.status_code == 200
    assert b"".join(r.streaming_content) == b"%PDF-test"
    storage.client.get_object.assert_called_once_with(storage.bucket_name,
        "sozlesmeler/ek2.pdf" if kind == "EK2" else "sozlesmeler/ek1.pdf")
    other_pharmacy = type(eczaci.eczane).objects.create(ad="Diğer", il=eczaci.eczane.il, ilce=eczaci.eczane.ilce)
    other = Sozlesme.objects.create(eczane=other_pharmacy, sozlesme_tipi_ay=24,
        baslangic_tarihi=timezone.localdate(), islak_imza_url="secret.pdf")
    r = eczaci_client.get(f"/api/abonelik/sozlesmeler/{other.pk}/islak-imza-indir/")
    assert r.status_code == 404
