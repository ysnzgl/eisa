import datetime as dt
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.abonelik.models import Fatura, FaturaKalemi, Sozlesme
from apps.announcements.models import Announcement
from apps.campaigns.models import (
    Bolge, BolgeKapsam, Campaign, KatkiHakedis, KioskSponsorship, SponsorTahsilat, SponsorlukTarifesi,
)
from apps.campaigns.services.contributions import hesapla_ve_kaydet
from apps.pharmacies.models import Eczane, Kiosk


@pytest.fixture(autouse=True)
def hesap_gunu(monkeypatch):
    monkeypatch.setattr("apps.campaigns.services.contributions.timezone.localdate", lambda: dt.date(2026, 12, 1))


@pytest.fixture
def bolge(eczane):
    region = Bolge.objects.create(kod="TEST", ad="Test Bölgesi", gecerlilik_baslangic=dt.date(2026, 1, 1))
    BolgeKapsam.objects.create(bolge=region, il=eczane.il, ilce=eczane.ilce)
    return region


@pytest.mark.django_db
@pytest.mark.parametrize("cihaz_sayisi", [7, 14])
def test_yedi_cihazda_havuz_aktif_cihaz_gune_gore_dagilir(eczane, bolge, cihaz_sayisi):
    tariff = SponsorlukTarifesi.objects.create(
        kod="BOLGE-6-15", ad="Bölge 6-15", tur="BOLGE", min_cihaz=6,
        max_cihaz=15, brut_bedel=Decimal("36000.00"),
        gecerlilik_baslangic=dt.date(2026, 1, 1),
    )
    start = timezone.make_aware(dt.datetime(2026, 11, 1))
    campaign = Campaign.objects.create(
        name="Bölge", start_date=start, end_date=start + dt.timedelta(days=30),
        sponsorluk_tarifesi=tariff, bolge=bolge,
    )
    pharmacies = [eczane]
    for i in range(cihaz_sayisi - 1):
        pharmacies.append(Eczane.objects.create(
            ad=f"Eczane {i}", il=eczane.il, ilce=eczane.ilce,
        ))
    for index, pharmacy in enumerate(pharmacies):
        kiosk = Kiosk.objects.create(
            eczane=pharmacy, ad=f"Kiosk {index}",
            mac_adresi=f"02:00:00:00:00:{index:02X}", uygulama_anahtari=f"key-{index}",
        )
        KioskSponsorship.objects.create(
            kiosk=kiosk, campaign=campaign, window_start_minute=0,
            window_end_minute=1440, count=1,
        )
        contract = Sozlesme.objects.create(
            eczane=pharmacy, sozlesme_tipi_ay=24,
            baslangic_tarihi=dt.date(2026, 11, 1), oteleme_ay=0,
        )
        invoice = Fatura.objects.create(
            eczane=pharmacy, sozlesme=contract, tip=Fatura.Tip.KULLANIM_BEDELI,
            donem="2026-11", tutar=Decimal("3900"),
            kesim_tarihi=dt.date(2026, 11, 1), vade_tarihi=dt.date(2026, 11, 10),
        )
        FaturaKalemi.objects.create(
            fatura=invoice, tip=FaturaKalemi.KalemTip.ABONELIK,
            tutar=Decimal("3900"), matrah=Decimal("3900"),
        )
    receipt = SponsorTahsilat.objects.create(
        campaign=campaign, brut_tutar=Decimal("36000"),
        tahsilat_tarihi=dt.date(2026, 12, 1),
        donem_baslangic=dt.date(2026, 11, 1), donem_bitis=dt.date(2026, 12, 1),
    )
    rows = hesapla_ve_kaydet(receipt)
    assert len(rows) == cihaz_sayisi
    assert sum((r.brut_pay for r in rows), Decimal("0")) == Decimal("5400.00")
    assert {r.uygun_cihaz_gun for r in rows} == {Decimal("30")}
    assert max(r.brut_pay for r in rows) - min(r.brut_pay for r in rows) <= Decimal("0.01")
    assert {r.durum for r in rows} == {KatkiHakedis.Durum.BILDIRILDI}
    assert Announcement.objects.filter(
        target_scope=Announcement.TargetScope.PHARMACY,
        title="Sponsorluk katkı payınız hesaplandı",
    ).count() == cihaz_sayisi


@pytest.mark.django_db
def test_oteleme_doneminde_fatura_yoksa_katki_dogmaz(eczane, kiosk, bolge):
    tariff = SponsorlukTarifesi.objects.create(
        kod="BOLGE", ad="Bölge", tur="BOLGE", min_cihaz=1,
        brut_bedel=Decimal("36000"), gecerlilik_baslangic=dt.date(2026, 1, 1),
    )
    start = timezone.make_aware(dt.datetime(2026, 11, 1))
    campaign = Campaign.objects.create(
        name="Ötelemeli", start_date=start, end_date=start + dt.timedelta(days=30),
        sponsorluk_tarifesi=tariff, bolge=bolge,
    )
    KioskSponsorship.objects.create(
        kiosk=kiosk, campaign=campaign, window_start_minute=0,
        window_end_minute=1440, count=1,
    )
    Sozlesme.objects.create(
        eczane=eczane, sozlesme_tipi_ay=24,
        baslangic_tarihi=dt.date(2026, 11, 1), oteleme_ay=2,
    )
    receipt = SponsorTahsilat.objects.create(
        campaign=campaign, brut_tutar=Decimal("36000"),
        tahsilat_tarihi=dt.date(2026, 12, 1),
        donem_baslangic=dt.date(2026, 11, 1), donem_bitis=dt.date(2026, 12, 1),
    )
    assert hesapla_ve_kaydet(receipt) == []
    assert receipt.hakedisler.count() == 0
    receipt.refresh_from_db()
    assert receipt.hesaplanma_tarihi
    with pytest.raises(ValueError, match="daha önce"):
        hesapla_ve_kaydet(receipt)
@pytest.mark.django_db
def test_yeni_kampanya_tarifesiz_kaydedilemez(admin_client):
    start = timezone.now()
    response = admin_client.post("/api/campaigns/v2/campaigns/", {
        "name": "Tarifesiz",
        "start_date": start.isoformat(),
        "end_date": (start + dt.timedelta(days=30)).isoformat(),
        "status": "ACTIVE",
    }, format="json")
    assert response.status_code == 400
    assert "sponsorluk_tarifesi" in response.data


