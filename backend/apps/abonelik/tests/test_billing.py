"""Abonelik faturalandırma ve erişim kilidi testleri."""
import datetime as dt
from decimal import Decimal

import pytest

from apps.abonelik import services
from apps.abonelik.models import CihazOdemePlani, Fatura, Sozlesme, SozlesmeTalebi


# ── Panel kısıtı ─────────────────────────────────────────────────────────────

def test_panel_kisitli_sozlesmesiz(db, eczane):
    kisitli, neden = services.panel_kisitli(eczane.id)
    assert kisitli is True
    assert neden == "SOZLESME_YOK"


def test_panel_acik_aktif_sozlesme(sozlesme, eczane):
    kisitli, _ = services.panel_kisitli(eczane.id)
    assert kisitli is False


def test_panel_kisitli_odeme_gecikti(sozlesme, eczane):
    # Haziran’da Temmuz faturası kesilir (vade 06-30). Gerçek tarih 2026-10-02 → kilitli.
    services.faturala_kullanim_bedeli(bugun=dt.date(2026, 6, 3))
    kisitli, neden = services.panel_kisitli(eczane.id)
    assert kisitli is True
    assert neden == "ODEME_GECIKTI"


# ── Sözleşme talepleri ───────────────────────────────────────────────────────

def test_talep_yeni_onay_sozlesme_olusturur(db, eczane):
    t = SozlesmeTalebi.objects.create(
        eczane=eczane, talep_tipi=SozlesmeTalebi.Tip.YENI,
        istenen_tur=Sozlesme.Tur.STANDART, istenen_tip_ay=24,
    )
    services.karar_ver_talep(t, onayla=True)
    t.refresh_from_db()
    assert t.durum == SozlesmeTalebi.Durum.ONAYLANDI
    assert Sozlesme.objects.filter(eczane=eczane, durum=Sozlesme.Durum.AKTIF).exists()


def test_talep_uzatma_onay(sozlesme, eczane):
    t = SozlesmeTalebi.objects.create(
        eczane=eczane, talep_tipi=SozlesmeTalebi.Tip.UZATMA,
        hedef_sozlesme=sozlesme, ek_ay=6,
    )
    services.karar_ver_talep(t, onayla=True)
    sozlesme.refresh_from_db()
    assert sozlesme.ek_ay_toplam == 6


def test_talep_iptal_onay(sozlesme, eczane):
    t = SozlesmeTalebi.objects.create(
        eczane=eczane, talep_tipi=SozlesmeTalebi.Tip.IPTAL, hedef_sozlesme=sozlesme,
    )
    services.karar_ver_talep(t, onayla=True)
    sozlesme.refresh_from_db()
    assert sozlesme.durum == Sozlesme.Durum.IPTAL


def test_iptal_sozlesme_tarihce_kayit_olusturur(sozlesme):
    services.iptal_sozlesme(sozlesme, neden="Müşteri vazgeçti")
    sozlesme.refresh_from_db()
    assert sozlesme.durum == Sozlesme.Durum.IPTAL
    assert sozlesme.uzatmalar.filter(is_iptal=True, iptal_nedeni='Müşteri vazgeçti').exists()


def test_talep_red(db, eczane):
    t = SozlesmeTalebi.objects.create(
        eczane=eczane, talep_tipi=SozlesmeTalebi.Tip.YENI,
        istenen_tur=Sozlesme.Tur.STANDART, istenen_tip_ay=24,
    )
    services.karar_ver_talep(t, onayla=False, red_nedeni="Uygun değil")
    t.refresh_from_db()
    assert t.durum == SozlesmeTalebi.Durum.REDDEDILDI
    assert t.red_nedeni == "Uygun değil"


# ── Sistem duyurusu koşulları ────────────────────────────────────────────────

def test_sistem_duyuru_odeme_yaklasti(db, eczane):
    from apps.announcements.models import Announcement
    from apps.announcements.services import system_context

    Fatura.objects.create(
        eczane=eczane, tip=Fatura.Tip.KULLANIM_BEDELI, donem="2099-01",
        tutar=Decimal("3900.00"), vade_tarihi=dt.date.today() + dt.timedelta(days=2),
        durum=Fatura.Durum.BEKLIYOR,
    )
    ann = Announcement.objects.get(system_key="PAYMENT_DUE_SOON")
    assert system_context(ann, eczane, dt.date.today()) is not None


def test_sistem_duyuru_sozlesme_bitiyor(db, eczane):
    from apps.announcements.models import Announcement
    from apps.announcements.services import system_context

    Sozlesme.objects.create(
        eczane=eczane, tur=Sozlesme.Tur.DEMO, demo_gun=5,
        baslangic_tarihi=dt.date.today(), durum=Sozlesme.Durum.AKTIF,
    )
    ann = Announcement.objects.get(system_key="CONTRACT_EXPIRING")
    assert system_context(ann, eczane, dt.date.today()) is not None



@pytest.fixture
def sozlesme(db, eczane):
    from django.utils import timezone as tz
    return Sozlesme.objects.create(
        eczane=eczane,
        sozlesme_tipi_ay=Sozlesme.Tip.AY_24,
        baslangic_tarihi=dt.date(2026, 1, 1),
        oteleme_ay=6,
        aylik_kullanim_bedeli=Decimal("3900.00"),
        durum=Sozlesme.Durum.AKTIF,
        eczaci_onay_tarihi=tz.now(),  # dijital onay verilmiş (panel kontrolü geçer)
    )


# ── Vade kaydırma (grace period) ────────────────────────────────────────────

def test_toplam_ay_oteleme_ile_uzar(sozlesme):
    # 24 ay + 6 ay öteleme = 30 ay
    assert sozlesme.toplam_ay == 30


def test_kullanim_bedeli_baslangic_oteleme_sonrasi(sozlesme):
    # 2026-01-01 + 6 ay = 2026-07-01 (7. ay)
    assert sozlesme.kullanim_bedeli_baslangic == dt.date(2026, 7, 1)


def test_bitis_tarihi_30_ay_sonra(sozlesme):
    # 2026-01-01 + 30 ay = 2028-07-01
    assert sozlesme.bitis_tarihi == dt.date(2028, 7, 1)


# ── Kullanım bedeli faturalandırma ──────────────────────────────────────────

def test_oteleme_doneminde_fatura_kesilmez(sozlesme):
    # Mart ayında prox=Nisan; Nisan < Öteleme sonu(Temmuz) → fatura yok
    created = services.faturala_kullanim_bedeli(bugun=dt.date(2026, 3, 5))
    assert created == 0
    assert Fatura.objects.count() == 0


def test_oteleme_sonrasi_fatura_kesilir(sozlesme):
    # Haziran ayında prox=Temmuz; öteleme sona ermiş → Temmuz faturası kesilir
    created = services.faturala_kullanim_bedeli(bugun=dt.date(2026, 6, 3))
    assert created == 1
    f = Fatura.objects.get()
    assert f.tip == Fatura.Tip.KULLANIM_BEDELI
    assert f.tutar == Decimal("3900.00")
    assert f.donem == "2026-07"
    # Vade: sözleşme başlangıç günü (1) Temmuz ayında = 2026-07-01
    assert f.vade_tarihi == dt.date(2026, 7, 1)


def test_kullanim_bedeli_idempotent(sozlesme):
    services.faturala_kullanim_bedeli(bugun=dt.date(2026, 6, 3))
    services.faturala_kullanim_bedeli(bugun=dt.date(2026, 6, 6))
    assert Fatura.objects.filter(tip=Fatura.Tip.KULLANIM_BEDELI, donem="2026-07").count() == 1


def test_sozlesme_bitince_fatura_kesilmez(sozlesme):
    # Bitiş 2028-07-01'den sonra
    created = services.faturala_kullanim_bedeli(bugun=dt.date(2028, 8, 3))
    assert created == 0


# ── Cihaz taksiti ───────────────────────────────────────────────────────────

@pytest.fixture
def cihaz_plani(db, sozlesme):
    return CihazOdemePlani.objects.create(
        sozlesme=sozlesme,
        pesin_fiyat=Decimal("40000.00"),
        vade_farki_orani=Decimal("20.00"),
        taksit_sayisi=CihazOdemePlani.TaksitSayisi.TAKSIT_4,
        baslangic_tarihi=dt.date(2026, 1, 1),
        durum=CihazOdemePlani.Durum.AKTIF,
    )


def test_taksit_tutari_vade_farki_dahil(cihaz_plani):
    # 40000 * 1.20 = 48000 / 4 = 12000
    assert cihaz_plani.toplam_tutar == Decimal("48000.00")
    assert cihaz_plani.taksit_tutari == Decimal("12000.00")


def test_cihaz_taksiti_ardisik_donemler(cihaz_plani):
    c1 = services.faturala_cihaz_taksit(bugun=dt.date(2026, 1, 3))
    c2 = services.faturala_cihaz_taksit(bugun=dt.date(2026, 2, 3))
    assert c1 == 1 and c2 == 1
    faturalar = Fatura.objects.filter(tip=Fatura.Tip.CIHAZ_TAKSIT).order_by("taksit_no")
    assert [f.taksit_no for f in faturalar] == [1, 2]
    assert all(f.tutar == Decimal("12000.00") for f in faturalar)


def test_tek_aylik_fatura_icerisinde_tum_odemeler_toplanir(cihaz_plani, sozlesme):
    created = services.faturala_aylik_birlesik(bugun=dt.date(2026, 6, 3))
    assert created == 1

    f = Fatura.objects.get(tip=Fatura.Tip.BIRLESIK, donem="2026-07")
    assert f.tutar == Decimal("15900.00")
    assert Fatura.objects.filter(
        tip__in=(
            Fatura.Tip.KULLANIM_BEDELI,
            Fatura.Tip.CIHAZ_TAKSIT,
            Fatura.Tip.CIHAZ_KIRA,
        )
    ).count() == 0
    assert f.kalemler.count() == 2


def test_cihaz_taksiti_idempotent_ayni_ay(cihaz_plani):
    services.faturala_cihaz_taksit(bugun=dt.date(2026, 1, 2))
    services.faturala_cihaz_taksit(bugun=dt.date(2026, 1, 5))
    assert Fatura.objects.filter(tip=Fatura.Tip.CIHAZ_TAKSIT, donem="2026-01").count() == 1


def test_cihaz_taksiti_dolunca_plan_tamamlanir(cihaz_plani):
    for ay in range(1, 6):  # 5 ay → 4 taksit + 1 boş
        services.faturala_cihaz_taksit(bugun=dt.date(2026, ay, 3))
    cihaz_plani.refresh_from_db()
    assert cihaz_plani.durum == CihazOdemePlani.Durum.TAMAMLANDI
    assert Fatura.objects.filter(tip=Fatura.Tip.CIHAZ_TAKSIT).count() == 4


# ── Gecikme + erişim kilidi ─────────────────────────────────────────────────

def test_gecikmis_fatura_isaretlenir(sozlesme):
    # Haziran’da Temmuz faturası kesilir; vade Haziran 30.
    services.faturala_kullanim_bedeli(bugun=dt.date(2026, 6, 3))
    f = Fatura.objects.get()
    # Grace 7 gün: vade(06-30) + 7 = 07-07; 07-20 > 07-07 → GECIKMIS
    updated = services.guncelle_gecikmis_faturalar(bugun=dt.date(2026, 7, 20))
    assert updated == 1
    f.refresh_from_db()
    assert f.durum == Fatura.Durum.GECIKTI


def test_erisim_grace_icinde_acik(sozlesme, eczane):
    services.faturala_kullanim_bedeli(bugun=dt.date(2026, 6, 3))  # vade 06-30
    # 07-06: sinir=06-29; 06-30 >= 06-29 → henuz kilitli degil
    assert services.eczane_erisim_kapali(eczane.id, bugun=dt.date(2026, 7, 6)) is False


def test_erisim_grace_sonrasi_kapali(sozlesme, eczane):
    services.faturala_kullanim_bedeli(bugun=dt.date(2026, 6, 3))  # vade 06-30, grace sonu 07-07
    assert services.eczane_erisim_kapali(eczane.id, bugun=dt.date(2026, 7, 20)) is True


def test_odeme_erisimi_acar(sozlesme, eczane):
    services.faturala_kullanim_bedeli(bugun=dt.date(2026, 6, 3))
    f = Fatura.objects.get()
    services.ode_fatura(f)
    f.refresh_from_db()
    assert f.durum == Fatura.Durum.ODENDI
    assert services.eczane_erisim_kapali(eczane.id, bugun=dt.date(2026, 7, 20)) is False


def test_odenmis_fatura_tekrar_odenemez(sozlesme):
    services.faturala_kullanim_bedeli(bugun=dt.date(2026, 6, 3))
    f = Fatura.objects.get()
    services.ode_fatura(f)
    with pytest.raises(ValueError):
        services.ode_fatura(f)


# ── Demo modu (sözleşme türü) ────────────────────────────────────────────────

def test_sozlesmesiz_eczane_demo_degil(db, eczane):
    # Aktif sözleşmesi olmayan eczane demo sayılmaz (durum: YOK).
    assert services.eczane_demo_modunda(eczane.id) is False
    assert services.odeme_durumu(eczane.id) == "YOK"


def test_demo_turu_aktif_sozlesme_demo(db, eczane):
    Sozlesme.objects.create(
        eczane=eczane, tur=Sozlesme.Tur.DEMO, demo_gun=30,
        baslangic_tarihi=dt.date(2026, 1, 1), durum=Sozlesme.Durum.AKTIF,
    )
    assert services.eczane_demo_modunda(eczane.id) is True
    assert services.odeme_durumu(eczane.id) == "DEMO"


def test_standart_aktif_sozlesme_demo_degil(sozlesme, eczane):
    assert services.eczane_demo_modunda(eczane.id) is False


def test_demo_sozlesme_kullanim_bedeli_faturalanmaz(db, eczane):
    Sozlesme.objects.create(
        eczane=eczane, tur=Sozlesme.Tur.DEMO, demo_gun=30,
        baslangic_tarihi=dt.date(2026, 1, 1), durum=Sozlesme.Durum.AKTIF,
    )
    created = services.faturala_kullanim_bedeli(bugun=dt.date(2026, 1, 15))
    assert created == 0
    assert Fatura.objects.count() == 0


def test_demo_bitis_gun_bazli(db, eczane):
    s = Sozlesme.objects.create(
        eczane=eczane, tur=Sozlesme.Tur.DEMO, demo_gun=10,
        baslangic_tarihi=dt.date(2026, 1, 1), durum=Sozlesme.Durum.AKTIF,
    )
    assert s.bitis_tarihi == dt.date(2026, 1, 11)


def test_demo_eczane_erisimi_kilitlenmez(db, eczane):
    Sozlesme.objects.create(
        eczane=eczane, tur=Sozlesme.Tur.DEMO, demo_gun=30,
        baslangic_tarihi=dt.date(2026, 1, 1), durum=Sozlesme.Durum.AKTIF,
    )
    assert services.eczane_erisim_kapali(eczane.id, bugun=dt.date(2026, 3, 1)) is False


# ── Sözleşme uzatma (tarihçe) ────────────────────────────────────────────────

def test_standart_uzatma_ay_ekler(sozlesme):
    services.uzat_sozlesme(sozlesme, ek_ay=6, neden="Vade uzatma")
    sozlesme.refresh_from_db()
    assert sozlesme.ek_ay_toplam == 6
    # 24 + 6 öteleme + 6 uzatma = 36 ay
    assert sozlesme.toplam_ay == 36
    assert sozlesme.uzatmalar.count() == 1


def test_demo_uzatma_gun_ekler(db, eczane):
    s = Sozlesme.objects.create(
        eczane=eczane, tur=Sozlesme.Tur.DEMO, demo_gun=20,
        baslangic_tarihi=dt.date(2026, 1, 1), durum=Sozlesme.Durum.AKTIF,
    )
    services.uzat_sozlesme(s, ek_gun=10)
    s.refresh_from_db()
    assert s.toplam_gun == 30
    assert s.bitis_tarihi == dt.date(2026, 1, 31)


def test_demo_uzatma_30_gun_cap(db, eczane):
    s = Sozlesme.objects.create(
        eczane=eczane, tur=Sozlesme.Tur.DEMO, demo_gun=25,
        baslangic_tarihi=dt.date(2026, 1, 1), durum=Sozlesme.Durum.AKTIF,
    )
    with pytest.raises(ValueError):
        services.uzat_sozlesme(s, ek_gun=10)  # 25 + 10 > 30


def test_standart_uzatma_gun_reddedilir(sozlesme):
    with pytest.raises(ValueError):
        services.uzat_sozlesme(sozlesme, ek_gun=5)


# ── Durum (aktif/iptal + türetilen süresi doldu) ─────────────────────────────

def test_aktif_sozlesme_etkin_durum(sozlesme):
    # baslangic 2026-01-01, 24+6 ay → bitiş 2028; bugün öncesinde aktif
    assert sozlesme.durum == Sozlesme.Durum.AKTIF
    assert sozlesme.etkin_durum in ("AKTIF", "SURESI_DOLDU")


def test_suresi_dolan_sozlesme_turetilir(db, eczane):
    s = Sozlesme.objects.create(
        eczane=eczane, tur=Sozlesme.Tur.DEMO, demo_gun=5,
        baslangic_tarihi=dt.date(2020, 1, 1), durum=Sozlesme.Durum.AKTIF,
    )
    assert s.suresi_doldu is True
    assert s.etkin_durum == "SURESI_DOLDU"


def test_iptal_sozlesme_etkin_durum(db, eczane):
    s = Sozlesme.objects.create(
        eczane=eczane, sozlesme_tipi_ay=24,
        baslangic_tarihi=dt.date(2026, 1, 1), durum=Sozlesme.Durum.IPTAL,
    )
    assert s.suresi_doldu is False
    assert s.etkin_durum == "IPTAL"


def test_iptal_sozlesme_uzatilamaz(db, eczane):
    s = Sozlesme.objects.create(
        eczane=eczane, sozlesme_tipi_ay=24,
        baslangic_tarihi=dt.date(2026, 1, 1), durum=Sozlesme.Durum.IPTAL,
    )
    with pytest.raises(ValueError):
        services.uzat_sozlesme(s, ek_ay=6)




# ── Cihaz planı: taksit 1/4/8/12 + vade farkı zorunluluğu ────────────────────

def test_cihaz_plani_pesin_vade_farksiz_gecerli(db, sozlesme):
    from apps.abonelik.serializers import CihazOdemePlaniSerializer

    ser = CihazOdemePlaniSerializer(data={
        "pesin_fiyat": "40000.00", "vade_farki_orani": "0.00",
        "taksit_sayisi": 1, "baslangic_tarihi": "2026-01-01",
    })
    assert ser.is_valid(), ser.errors


def test_cihaz_plani_taksitli_vade_zorunlu(db, sozlesme):
    from apps.abonelik.serializers import CihazOdemePlaniSerializer

    ser = CihazOdemePlaniSerializer(data={
        "pesin_fiyat": "40000.00", "vade_farki_orani": "0.00",
        "taksit_sayisi": 12, "baslangic_tarihi": "2026-01-01",
    })
    assert not ser.is_valid()
    assert "vade_farki_orani" in ser.errors


def test_cihaz_plani_12_taksit_vade_ile_gecerli(db, sozlesme):
    from apps.abonelik.serializers import CihazOdemePlaniSerializer

    ser = CihazOdemePlaniSerializer(data={
        "pesin_fiyat": "40000.00", "vade_farki_orani": "30.00",
        "taksit_sayisi": 12, "baslangic_tarihi": "2026-01-01",
    })
    assert ser.is_valid(), ser.errors


# ── Fiyat tanımı (parametre) ─────────────────────────────────────────────────

def test_aktif_fiyat_en_guncel_gecerli(db):
    from apps.abonelik.models import FiyatTanimi

    FiyatTanimi.objects.create(
        abonelik_bedeli=Decimal("3900.00"), cihaz_kira_bedeli=Decimal("500.00"),
        gecerlilik_baslangic=dt.date(2026, 1, 1),
    )
    FiyatTanimi.objects.create(
        abonelik_bedeli=Decimal("4200.00"), cihaz_kira_bedeli=Decimal("600.00"),
        gecerlilik_baslangic=dt.date(2026, 6, 1),
    )
    f = services.aktif_fiyat(bugun=dt.date(2026, 7, 1))
    assert f.abonelik_bedeli == Decimal("4200.00")
    # Gelecekteki tarih henüz geçerli değil.
    f2 = services.aktif_fiyat(bugun=dt.date(2026, 3, 1))
    assert f2.abonelik_bedeli == Decimal("3900.00")


def test_aktif_fiyat_yoksa_none(db):
    assert services.aktif_fiyat() is None


# ── Cihaz kira faturalandırma ────────────────────────────────────────────────

def test_cihaz_kira_faturalanir(db, eczane):
    s = Sozlesme.objects.create(
        eczane=eczane, sozlesme_tipi_ay=24,
        baslangic_tarihi=dt.date(2026, 1, 1), durum=Sozlesme.Durum.AKTIF,
        cihaz_durumu=Sozlesme.CihazDurum.KIRALIK, cihaz_kira_bedeli=Decimal("750.00"),
    )
    # Aralık’ta çalıştırılır → Ocak 2026 faturası 1 ay önceden kesilir
    created = services.faturala_cihaz_kira(bugun=dt.date(2025, 12, 3))
    assert created == 1
    f = Fatura.objects.get(tip=Fatura.Tip.CIHAZ_KIRA)
    assert f.tutar == Decimal("750.00")
    assert f.donem == "2026-01"


def test_cihaz_kira_idempotent(db, eczane):
    Sozlesme.objects.create(
        eczane=eczane, sozlesme_tipi_ay=24,
        baslangic_tarihi=dt.date(2026, 1, 1), durum=Sozlesme.Durum.AKTIF,
        cihaz_durumu=Sozlesme.CihazDurum.KIRALIK, cihaz_kira_bedeli=Decimal("750.00"),
    )
    services.faturala_cihaz_kira(bugun=dt.date(2025, 12, 3))
    services.faturala_cihaz_kira(bugun=dt.date(2025, 12, 6))
    assert Fatura.objects.filter(tip=Fatura.Tip.CIHAZ_KIRA, donem="2026-01").count() == 1


def test_satilik_cihaz_kira_faturalanmaz(sozlesme):
    created = services.faturala_cihaz_kira(bugun=dt.date(2026, 1, 3))
    assert created == 0


# ── Talep onayı: tam sözleşme oluşturma ──────────────────────────────────────

def test_talep_yeni_onay_detayli_sozlesme(db, eczane):
    from apps.abonelik.models import CihazOdemePlani, FiyatTanimi

    FiyatTanimi.objects.create(
        abonelik_bedeli=Decimal("4200.00"), cihaz_kira_bedeli=Decimal("0.00"),
        gecerlilik_baslangic=dt.date(2026, 1, 1),
    )
    t = SozlesmeTalebi.objects.create(
        eczane=eczane, talep_tipi=SozlesmeTalebi.Tip.YENI,
        istenen_tur=Sozlesme.Tur.STANDART, istenen_tip_ay=24,
    )
    services.karar_ver_talep(t, onayla=True, detail_data={
        "baslangic_tarihi": dt.date(2026, 2, 1),
        "oteleme_ay": 3,
        "cihaz_durumu": "SATILIK",
        "pesin_fiyat": "40000.00",
        "vade_farki_orani": "20.00",
        "taksit_sayisi": 4,
    })
    s = Sozlesme.objects.get(eczane=eczane, durum=Sozlesme.Durum.AKTIF)
    assert s.oteleme_ay == 3
    assert s.aylik_kullanim_bedeli == Decimal("4200.00")  # aktif fiyattan
    assert CihazOdemePlani.objects.filter(sozlesme=s, taksit_sayisi=4).exists()


def test_talep_yeni_onay_kiralik_cihaz(db, eczane):
    t = SozlesmeTalebi.objects.create(
        eczane=eczane, talep_tipi=SozlesmeTalebi.Tip.YENI,
        istenen_tur=Sozlesme.Tur.STANDART, istenen_tip_ay=12,
    )
    services.karar_ver_talep(t, onayla=True, detail_data={
        "cihaz_durumu": "KIRALIK",
        "cihaz_kira_bedeli": "900.00",
    })
    s = Sozlesme.objects.get(eczane=eczane, durum=Sozlesme.Durum.AKTIF)
    assert s.cihaz_durumu == "KIRALIK"
    assert s.cihaz_kira_bedeli == Decimal("900.00")

