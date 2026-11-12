import datetime as dt
import io
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import pytest
from django.utils import timezone

from apps.abonelik.contract_docx import generate_contract_docx
from apps.abonelik.models import Sozlesme
from apps.pharmacies.models import Eczane, FizikselCihaz, Kiosk, KioskProvisioningRequest

pytestmark = pytest.mark.django_db
BASE = "/api/pharmacies/cihazlar/"


def test_seri_numarasiyla_provizyon_oncesi_cihaz_kaydi(admin_client):
    response = admin_client.post(BASE, {"seri_no": " sn-100 ", "marka": "Eisa", "model": "K21"}, format="json")
    assert response.status_code == 201, response.content
    assert response.data["seri_no"] == "SN-100"
    assert response.data["kiosk"] is None
    duplicate = admin_client.post(BASE, {"seri_no": "sn-100", "model": "Diğer"}, format="json")
    assert duplicate.status_code == 400


def test_provizyonda_kayitli_cihaza_eslesme(admin_client, eczane):
    physical = FizikselCihaz.objects.create(seri_no="SN-101", model="K21", eczane=eczane)
    request = KioskProvisioningRequest.objects.create(mac_adresi="AA:BB:CC:DD:11:22", hostname="Eisa")
    url = f"/api/pharmacies/kiosks/provisioning/{request.pk}/approve/"
    payload = {"eczane_id": eczane.pk, "ad": "Kiosk 1", "fiziksel_cihaz_id": physical.pk}
    response = admin_client.post(url, payload, format="json")
    assert response.status_code == 200, response.content
    physical.refresh_from_db()
    request.refresh_from_db()
    assert physical.kiosk_id == request.kiosk_id
    assert physical.kiosk.mac_adresi == "AA:BB:CC:DD:11:22"
    assert physical.seri_no == "SN-101"
    assert admin_client.post(url, payload, format="json").status_code == 200
    assert Kiosk.objects.count() == 1


def test_baska_eczanenin_cihazi_eslestirilemez_ve_yeni_kiosk_geri_alinir(admin_client, eczane):
    other = Eczane.objects.create(ad="Diğer", il=eczane.il, ilce=eczane.ilce)
    physical = FizikselCihaz.objects.create(seri_no="SN-102", model="K21", eczane=other)
    request = KioskProvisioningRequest.objects.create(mac_adresi="AA:BB:CC:DD:11:33")
    response = admin_client.post(f"/api/pharmacies/kiosks/provisioning/{request.pk}/approve/",
        {"eczane_id": eczane.pk, "ad": "Kiosk", "fiziksel_cihaz_id": physical.pk}, format="json")
    assert response.status_code == 400
    assert not Kiosk.objects.exists()
    request.refresh_from_db()
    assert request.status == "PENDING"


def test_mevcut_kioskla_seri_eslestirmesi_tekildir(admin_client, kiosk):
    first = FizikselCihaz.objects.create(seri_no="SN-103", model="K21")
    second = FizikselCihaz.objects.create(seri_no="SN-104", model="K21")
    assert admin_client.post(f"{BASE}{first.pk}/eslestir/", {"kiosk": kiosk.pk}, format="json").status_code == 200
    assert admin_client.post(f"{BASE}{second.pk}/eslestir/", {"kiosk": kiosk.pk}, format="json").status_code == 400


@pytest.mark.parametrize("kind", ["EK1", "EK2"])
def test_sozlesme_onizlemesi_ve_indirme_ayni_dolu_belgeyi_kullanir(admin_client, eczane, kind):
    physical = FizikselCihaz.objects.create(seri_no="SN-555", marka="Eisa", model="K21", garanti_ay=24)
    response = admin_client.post("/api/abonelik/sozlesmeler/", {"eczane": eczane.pk,
        "sozlesme_tipi_ay": 24, "baslangic_tarihi": str(timezone.localdate()),
        "cihaz_planlari": [{"tip": "TAHSIS", "adet": 1, "cihazlar": [physical.pk]}]}, format="json")
    assert response.status_code == 201, response.content
    contract_id = response.data["id"]
    preview = admin_client.get(f"/api/abonelik/sozlesmeler/{contract_id}/metin/?belge_turu={kind}")
    assert preview.status_code == 200, preview.content
    assert "SN-555" in preview.data["html"]
    assert "K21" in preview.data["html"]
    if kind == "EK1":
        assert "Seçilen model: Tahsis" in preview.data["html"]
        assert "Taksit takvimi: Tahsis" in preview.data["html"]
        assert "Paket kapsamı" in preview.data["html"]
        assert "teyit ediniz" in preview.data["html"]
        assert "5.000 TL + KDV" not in preview.data["html"]
        assert "Planlanan azami Cihaz sayısı hedef doygunluk düzeyidir" in preview.data["html"]
    assert ("MADDE 26" in preview.data["html"]) if kind == "EK1" else ("Aktivasyon Tarihi" in preview.data["html"])
    assert "Cihaz seri numaraları" not in preview.data["eksik_alanlar"]
    assert "Gerçek imza tarihi" in preview.data["eksik_alanlar"]
    download = admin_client.get(f"/api/abonelik/sozlesmeler/{contract_id}/belge-olustur/?belge_turu={kind}")
    assert download.status_code == 200
    content = b"".join(download.streaming_content)
    with ZipFile(io.BytesIO(content)) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
        all_text = " ".join(root.itertext())
        assert "SN-555" in all_text and "K21" in all_text
        if kind == "EK1":
            namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            region = root.findall(".//w:tbl", namespace)[6]
            assert all(len(row.findall("./w:tc", namespace)) == 2 for row in region.findall("./w:tr", namespace))
    if kind == "EK2":
        assert "Ödeme Başlangıç Tarihi: #" not in all_text
        assert "Aktivasyon Tarihi: #" not in all_text
    else:
        assert "Garanti süresi" not in preview.data["eksik_alanlar"]


def test_fiziksel_cihaz_adedi_sozlesmeyle_uyusmali(admin_client, eczane):
    physical = FizikselCihaz.objects.create(seri_no="SN-200", model="K21")
    response = admin_client.post("/api/abonelik/sozlesmeler/", {"eczane": eczane.pk,
        "sozlesme_tipi_ay": 24, "baslangic_tarihi": str(timezone.localdate()),
        "cihaz_planlari": [{"tip": "TAHSIS", "adet": 2, "cihazlar": [physical.pk]}]}, format="json")
    assert response.status_code == 400
    assert not Sozlesme.objects.filter(eczane=eczane).exists()


def test_bolge_kodu_ve_tarih_girmeden_kaydedilir(admin_client, eczane):
    response = admin_client.post("/api/campaigns/v2/bolgeler/", {"ad": "Merkez Bölgesi",
        "kapsamlar": [{"il": eczane.il_id, "ilce": None}]}, format="json")
    assert response.status_code == 201, response.content
    assert response.data["ad"] == "Merkez Bölgesi"
    assert response.data["kapsamlar"][0]["ilce"] is None


def test_tarife_kodu_girmeden_kaydedilir(admin_client):
    response = admin_client.post("/api/campaigns/v2/tarifeler/", {"ad": "Bölge 6-15", "tur": "BOLGE",
        "min_cihaz": 6, "max_cihaz": 15, "brut_bedel": "36000", "gecerlilik_baslangic": "2026-01-01"}, format="json")
    assert response.status_code == 201, response.content


def test_eczaci_fiziksel_envanteri_goremez(eczaci_client):
    assert eczaci_client.get(BASE).status_code == 403


def test_eczaci_kendi_yeni_belgesini_indirir_diger_eczaneyi_acamaz(eczaci_client, eczane):
    own = Sozlesme.objects.filter(eczane=eczane).first()
    own.sozlesme_surumu = "2026-EK1"
    own.save(update_fields=["sozlesme_surumu"])
    response = eczaci_client.get(f"/api/abonelik/sozlesmelerim/{own.pk}/belge-olustur/?belge_turu=EK2")
    assert response.status_code == 200
    assert b"".join(response.streaming_content).startswith(b"PK")
    other_pharmacy = Eczane.objects.create(ad="Başka Eczane", il=eczane.il, ilce=eczane.ilce)
    other = Sozlesme.objects.create(eczane=other_pharmacy, sozlesme_tipi_ay=24,
        baslangic_tarihi=timezone.localdate())
    assert eczaci_client.get(f"/api/abonelik/sozlesmelerim/{other.pk}/belge-olustur/").status_code == 404
