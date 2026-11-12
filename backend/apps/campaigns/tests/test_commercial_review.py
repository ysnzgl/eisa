import datetime as dt
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.abonelik import services
from apps.abonelik.models import Fatura, Sozlesme
from apps.campaigns.models import Bolge, BolgeKapsam, Campaign, KatkiHakedis, KioskSponsorship, SponsorTahsilat, SponsorlukTarifesi
from apps.campaigns.serializers import CampaignSerializer, SponsorTahsilatSerializer, KatkiHakedisSerializer
from apps.campaigns.services.contributions import hesapla_ve_kaydet
from apps.pharmacies.models import Eczane, Kiosk, KioskEczaneAtama


pytestmark = pytest.mark.django_db


@pytest.fixture
def receipt(eczane, kiosk, monkeypatch):
    monkeypatch.setattr(timezone, "localdate", lambda: dt.date(2026, 11, 8))
    tariff = SponsorlukTarifesi.objects.create(kod="T", ad="Test", tur="ECZANE",
        brut_bedel=Decimal("1000"), gecerlilik_baslangic=dt.date(2026, 1, 1))
    campaign = Campaign.objects.create(name="Gizli sponsor", sponsorluk_tarifesi=tariff,
        start_date=timezone.make_aware(dt.datetime(2026, 10, 1)),
        end_date=timezone.make_aware(dt.datetime(2026, 11, 1)))
    KioskSponsorship.objects.create(kiosk=kiosk, campaign=campaign,
        window_start_minute=0, window_end_minute=1440, count=1)
    contract = Sozlesme.objects.create(eczane=eczane, sozlesme_tipi_ay=24,
        baslangic_tarihi=dt.date(2026, 9, 8))
    services.faturala_ayri(bugun=dt.date(2026, 10, 8), sozlesme_id=contract.pk)
    return SponsorTahsilat.objects.create(campaign=campaign, brut_tutar=Decimal("1000"),
        tahsilat_tarihi=dt.date(2026, 11, 1), donem_baslangic=dt.date(2026, 10, 1), donem_bitis=dt.date(2026, 11, 1))


def test_katki_takvim_ayi_yerine_hizmet_donemi_ile_hesaplanir(receipt):
    rows = hesapla_ve_kaydet(receipt)
    assert rows[0].uygun_cihaz_gun == 31
    assert rows[0].brut_pay == Decimal("150.00")
    with pytest.raises(ValueError, match="daha önce"):
        hesapla_ve_kaydet(receipt)


def test_eksik_abonelik_faturasi_sessizce_pay_silmez(receipt):
    Fatura.objects.filter(donem="2026-09").delete()
    with pytest.raises(ValueError, match="faturası eksik"):
        hesapla_ve_kaydet(receipt)
    receipt.refresh_from_db()
    assert receipt.hesaplanma_tarihi is None
    assert not receipt.hakedisler.exists()


def test_henuz_tamamlanmamis_doneme_kesin_pay_olusturulmaz(receipt):
    receipt.donem_bitis = dt.date(2026, 12, 1)
    receipt.save()
    with pytest.raises(ValueError, match="tamamlanmadan"):
        hesapla_ve_kaydet(receipt)


def test_ay_ortasinda_kurulan_cihaz_kurulum_oncesi_gunleri_kazanmaz(receipt):
    kiosk = receipt.campaign.kiosk_sponsorships.get().kiosk
    KioskEczaneAtama.objects.create(kiosk=kiosk, eczane=kiosk.eczane,
        baslangic_zamani=timezone.make_aware(dt.datetime(2026, 10, 15)))
    rows = hesapla_ve_kaydet(receipt)
    assert rows[0].uygun_cihaz_gun == 17


def test_bolge_havuzu_atanmamis_uygun_cihazi_da_icerir(receipt, eczane):
    region = Bolge.objects.create(kod="B", ad="Bölge", gecerlilik_baslangic=dt.date(2026, 1, 1))
    BolgeKapsam.objects.create(bolge=region, il=eczane.il)
    campaign = receipt.campaign
    campaign.bolge = region
    campaign.tarife_snapshot = {"tur": "BOLGE"}
    campaign.save()
    other = Eczane.objects.create(ad="Diğer", il=eczane.il, ilce=eczane.ilce)
    Kiosk.objects.create(eczane=other, ad="Diğer", mac_adresi="00:00:00:00:00:22", uygulama_anahtari="other")
    contract = Sozlesme.objects.create(eczane=other, sozlesme_tipi_ay=24, baslangic_tarihi=dt.date(2026, 9, 1))
    services.faturala_ayri(bugun=dt.date(2026, 10, 1), sozlesme_id=contract.pk)
    rows = hesapla_ve_kaydet(receipt)
    assert len(rows) == 2
    assert {row.brut_pay for row in rows} == {Decimal("75.00")}


def test_hesaplanmis_tahsilat_degistirilemez_silinemez(receipt, admin_client):
    hesapla_ve_kaydet(receipt)
    url = f"/api/campaigns/v2/tahsilatlar/{receipt.pk}/"
    assert admin_client.patch(url, {"brut_tutar": "5000"}, format="json").status_code == 400
    assert admin_client.delete(url).status_code == 405
    assert admin_client.post("/api/campaigns/v2/katki-hakedisleri/", {}, format="json").status_code == 405


def test_tahsilat_partial_guncellemesinde_tutar_ve_tarihler_instance_uzerinden_okunur(receipt):
    serializer = SponsorTahsilatSerializer(receipt, data={"referans": "BANKA-123"}, partial=True)
    assert serializer.is_valid(), serializer.errors
    serializer = SponsorTahsilatSerializer(receipt, data={"donem_baslangic": dt.date(2026, 12, 1)}, partial=True)
    assert not serializer.is_valid()


def test_hakedis_fatura_tebligi_15_gun_vade_ve_odeme_dogrulamasi(receipt):
    row = hesapla_ve_kaydet(receipt)[0]
    serializer = KatkiHakedisSerializer(row, data={"eczane_fatura_no": "EF-123",
        "eczane_fatura_teblig_tarihi": "2026-11-01"}, partial=True)
    assert serializer.is_valid(), serializer.errors
    row = serializer.save()
    assert row.odeme_son_tarihi == dt.date(2026, 11, 16)
    serializer = KatkiHakedisSerializer(row, data={"durum": "ODENDI"}, partial=True)
    assert not serializer.is_valid()


def test_eczaci_hesabinda_sponsor_kimligi_ve_ic_hesaplar_gosterilmez(receipt, eczaci_client):
    hesapla_ve_kaydet(receipt)
    response = eczaci_client.get("/api/campaigns/v2/katki-hakedislerim/")
    assert response.status_code == 200
    assert len(response.data) == 1
    assert not {"campaign_ad", "tahsilat", "hesap_detayi", "eczane"} & response.data[0].keys()


def test_kampanya_tarife_snapshot_siradan_duzenlemede_ezilmez(receipt):
    campaign = receipt.campaign
    serializer = CampaignSerializer(campaign, data={"sponsorluk_tarifesi": campaign.sponsorluk_tarifesi_id}, partial=True)
    assert serializer.is_valid(), serializer.errors
    serializer.save()
    snapshot = dict(campaign.tarife_snapshot)
    tariff = campaign.sponsorluk_tarifesi
    tariff.brut_bedel = Decimal("9999")
    tariff.aktif = False
    tariff.save()
    serializer = CampaignSerializer(campaign, data={"name": "Yeni ad"}, partial=True)
    assert serializer.is_valid(), serializer.errors
    serializer.save()
    assert campaign.tarife_snapshot == snapshot
    serializer = CampaignSerializer(campaign, data={"sponsorluk_tarifesi": None}, partial=True)
    assert not serializer.is_valid()


def test_bolge_kapsami_cakismasi_ve_tekrari_400_ile_reddedilir(admin_client, eczane):
    payload = {"kod": "B1", "ad": "Bölge", "gecerlilik_baslangic": "2026-01-01",
               "kapsamlar": [{"il": eczane.il_id, "ilce": None}]}
    url = "/api/campaigns/v2/bolgeler/"
    assert admin_client.post(url, payload, format="json").status_code == 201
    response = admin_client.post(url, {**payload, "kod": "B2"}, format="json")
    assert response.status_code == 400 and "kapsamlar" in response.data
    assert admin_client.patch(url + "999999/", {"ad": "Yok"}, format="json").status_code == 404


def test_kullanilan_tarifeyi_silmek_500_yerine_acik_hata_verir(receipt, admin_client):
    response = admin_client.delete(f"/api/campaigns/v2/tarifeler/{receipt.campaign.sponsorluk_tarifesi_id}/")
    assert response.status_code == 400


@pytest.mark.parametrize("bulk", [False, True])
def test_tahsilatli_kampanya_silinirken_anlasilir_hata_doner(receipt, admin_client, bulk):
    if bulk:
        response = admin_client.post("/api/campaigns/v2/campaigns/bulk-action/",
            {"action": "delete", "ids": [str(receipt.campaign_id)]}, format="json")
    else:
        response = admin_client.delete(f"/api/campaigns/v2/campaigns/{receipt.campaign_id}/")
    assert response.status_code == 400
    assert Campaign.objects.filter(pk=receipt.campaign_id).exists()


def test_tarife_gecerlilik_cakismasi_engellenir(admin_client):
    payload = {"kod": "2026", "ad": "Test", "tur": "ECZANE", "min_cihaz": 1,
        "brut_bedel": "1000", "gecerlilik_baslangic": "2026-01-01", "gecerlilik_bitis": "2026-06-30"}
    url = "/api/campaigns/v2/tarifeler/"
    assert admin_client.post(url, payload, format="json").status_code == 201
    response = admin_client.post(url, {**payload, "gecerlilik_baslangic": "2026-06-01"}, format="json")
    assert response.status_code == 400
    assert admin_client.post(url, {**payload, "gecerlilik_baslangic": "2026-07-01", "gecerlilik_bitis": None}, format="json").status_code == 201
