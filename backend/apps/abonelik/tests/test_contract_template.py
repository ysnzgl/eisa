"""Sözleşme matbu metin ve dijital onay dondurma testi."""
import datetime as dt
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.abonelik import services
from apps.abonelik.models import Sozlesme


@pytest.fixture
def sozlesme(db, eczane):
    return Sozlesme.objects.create(
        eczane=eczane, sozlesme_tipi_ay=24,
        baslangic_tarihi=dt.date(2026, 1, 1),
        aylik_kullanim_bedeli=Decimal("3900.00"), kdv_orani=20,
        durum=Sozlesme.Durum.AKTIF,
    )


def test_render_sozlesme_html_icerir(sozlesme):
    from apps.abonelik.contract_template import render_sozlesme_html
    html = render_sozlesme_html(sozlesme)
    assert "MADDE 1" in html
    assert "MADDE 22" in html
    assert "3.900,00" in html  # aylık bedel TR formatı


def test_onay_metni_dondurulur(sozlesme):
    assert sozlesme.onayli_sozlesme_metni == ""
    services.sozlesme_onayla(sozlesme, ip_address="1.2.3.4")
    sozlesme.refresh_from_db()
    assert sozlesme.eczaci_onay_tarihi is not None
    assert "DİJİTAL OLARAK ONAYLANMIŞTIR" in sozlesme.onayli_sozlesme_metni
    assert "1.2.3.4" in sozlesme.onayli_sozlesme_metni


def test_onay_sonrasi_metin_degismez(sozlesme):
    services.sozlesme_onayla(sozlesme, ip_address="1.2.3.4")
    sozlesme.refresh_from_db()
    donmus = sozlesme.onayli_sozlesme_metni
    # Fiyat değişse bile dondurulmuş metin aynı kalmalı
    sozlesme.aylik_kullanim_bedeli = Decimal("9999.00")
    sozlesme.save()
    sozlesme.refresh_from_db()
    assert sozlesme.onayli_sozlesme_metni == donmus
    assert "9.999,00" not in sozlesme.onayli_sozlesme_metni
