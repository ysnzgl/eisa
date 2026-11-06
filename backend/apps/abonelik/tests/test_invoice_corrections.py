import datetime as dt
from decimal import Decimal

import pytest
from apps.abonelik import services
from apps.abonelik.invoice_corrections import correct, preview
from apps.abonelik.models import CihazOdemePlani, Fatura, FaturaKalemi, Sozlesme


@pytest.fixture
def invoice(eczane):
    s = Sozlesme.objects.create(eczane=eczane, baslangic_tarihi=dt.date(2026, 1, 1),
                               sozlesme_tipi_ay=24, aylik_kullanim_bedeli=Decimal('150.00'))
    f = Fatura.objects.create(eczane=eczane, sozlesme=s, tip='BIRLESIK', donem='2026-01',
                              tutar=Decimal('100.00'), vade_tarihi=dt.date(2026, 1, 1))
    FaturaKalemi.objects.create(fatura=f, tip='ABONELIK', tutar=f.tutar)
    return f


def change(f, action, user=None, **kwargs):
    return correct(f.pk, islem=action, neden='Hatalı işlem düzeltmesi', surum=f.surum, user=user, **kwargs)


@pytest.mark.parametrize('reason', ['', '   ', None, 'x' * 501])
def test_reason_required(invoice, reason):
    with pytest.raises(ValueError):
        correct(invoice.pk, islem='IPTAL', neden=reason, surum=invoice.surum, user=None)
    invoice.refresh_from_db()
    assert invoice.durum == 'BEKLIYOR'
    assert not invoice.islemler.exists()


def test_cancel_removes_debt_preserves_history_and_scheduler_idempotency(invoice, superadmin):
    assert services.eczane_erisim_kapali(invoice.eczane_id)
    f = change(invoice, 'IPTAL', superadmin)
    assert f.iptal_nedeni == 'Hatalı işlem düzeltmesi'
    assert f.iptal_tarihi
    assert not services.eczane_erisim_kapali(f.eczane_id)
    assert f.kalemler.count() == 1
    event = f.islemler.get()
    assert event.olusturan == superadmin
    assert event.onceki['durum'] == 'BEKLIYOR'
    assert event.sonraki['durum'] == 'IPTAL'
    assert services.faturala_aylik_birlesik(bugun=dt.date(2026, 1, 1)) == 0
    assert Fatura.objects.filter(pk=f.pk).exists()


def test_preview_is_readonly_and_rebuild_keeps_identity_and_period(invoice):
    data = preview(invoice)
    assert data['yeni_tutar'] == '150.00'
    invoice.refresh_from_db()
    assert invoice.tutar == Decimal('100.00')
    f = change(invoice, 'YENIDEN_OLUSTUR', onizleme_anahtari=data['onizleme_anahtari'])
    assert f.pk == invoice.pk and f.donem == '2026-01'
    assert f.vade_tarihi == invoice.vade_tarihi
    assert f.tutar == Decimal('150.00')
    assert f.kalemler.get().tutar == f.tutar
    assert f.islemler.get().onceki['kalemler'][0]['tutar'] == '100.00'


def test_paid_cancel_preserves_payment_and_undo_does_not_reopen_cancelled(invoice):
    payment = services.ode_fatura(invoice)
    invoice.refresh_from_db()
    f = change(invoice, 'IPTAL')
    payment.refresh_from_db()
    assert payment.geri_alinma_tarihi is None
    assert f.odemeler.count() == 1
    f = change(f, 'ODEME_GERI_AL')
    payment.refresh_from_db()
    assert payment.geri_alinma_tarihi and payment.geri_alma_nedeni
    assert f.durum == 'IPTAL'
    assert f.odenme_tarihi is None
    with pytest.raises(ValueError):
        change(f, 'ODEME_GERI_AL')


def test_paid_amount_change_requires_undo_then_rebuild_then_payment(invoice):
    original = services.ode_fatura(invoice)
    invoice.refresh_from_db()
    data = preview(invoice)
    assert data['engel']
    with pytest.raises(ValueError, match='tahsilat'):
        change(invoice, 'YENIDEN_OLUSTUR', onizleme_anahtari=data['onizleme_anahtari'])
    f = change(invoice, 'ODEME_GERI_AL')
    assert f.durum == 'GECIKTI'
    data = preview(f)
    f = change(f, 'YENIDEN_OLUSTUR', onizleme_anahtari=data['onizleme_anahtari'])
    payment = services.ode_fatura(f)
    assert payment.tutar == Decimal('150.00')
    original.refresh_from_db()
    assert original.geri_alinma_tarihi
    assert f.odemeler.count() == 2


def test_paid_same_amount_remains_paid_after_rebuild(invoice):
    invoice.sozlesme.aylik_kullanim_bedeli = invoice.tutar
    invoice.sozlesme.save()
    payment = services.ode_fatura(invoice)
    invoice.refresh_from_db()
    f = change(invoice, 'IPTAL')
    data = preview(f)
    f = change(f, 'YENIDEN_OLUSTUR', onizleme_anahtari=data['onizleme_anahtari'])
    assert f.durum == 'ODENDI'
    assert f.odenme_tarihi == payment.odeme_tarihi
    assert f.odemeler.get().pk == payment.pk
    with pytest.raises(ValueError, match='zaten'):
        services.ode_fatura(f)


def test_stale_preview_and_version_rejected(invoice):
    data = preview(invoice)
    invoice.sozlesme.aylik_kullanim_bedeli = Decimal('250.00')
    invoice.sozlesme.save()
    with pytest.raises(ValueError, match='Hesaplama değişmiş'):
        change(invoice, 'YENIDEN_OLUSTUR', onizleme_anahtari=data['onizleme_anahtari'])
    change(invoice, 'IPTAL')
    with pytest.raises(ValueError, match='Fatura değişmiş'):
        change(invoice, 'IPTAL')


def test_stale_payment_object_cannot_pay_cancelled_invoice(invoice):
    change(invoice, 'IPTAL')
    with pytest.raises(ValueError, match='İptal'):
        services.ode_fatura(invoice)
    assert not invoice.odemeler.exists()


def test_device_installment_number_and_completed_plan_preserved(invoice):
    p = CihazOdemePlani.objects.create(sozlesme=invoice.sozlesme, tip='SATILIK',
        adet=1, pesin_fiyat=Decimal('800.00'), taksit_sayisi=8,
        baslangic_tarihi=dt.date(2026, 1, 1), durum='TAMAMLANDI')
    FaturaKalemi.objects.create(fatura=invoice, tip='CIHAZ_TAKSIT', cihaz_plani=p,
                               taksit_no=8, tutar=Decimal('50.00'))
    data = preview(invoice)
    assert data['yeni_tutar'] == '250.00'
    f = change(invoice, 'YENIDEN_OLUSTUR', onizleme_anahtari=data['onizleme_anahtari'])
    assert f.kalemler.get(cihaz_plani=p).taksit_no == 8
    assert p.fatura_kalemleri.count() == 1


def test_api_required_reason_and_history(invoice, admin_client):
    url = f'/api/abonelik/faturalar/{invoice.pk}/'
    assert admin_client.post(url + 'iptal/', {'neden': ' ', 'surum': 1}, format='json').status_code == 400
    r = admin_client.post(url + 'iptal/', {'neden': 'Yanlış tutar', 'surum': 1}, format='json')
    assert r.status_code == 200, r.content
    assert r.json()['iptal_nedeni'] == 'Yanlış tutar'
    assert r.json()['islemler'][0]['neden'] == 'Yanlış tutar'
    data = admin_client.get(url + 'yeniden-olustur-onizleme/').json()
    r = admin_client.post(url + 'yeniden-olustur/', {
        'neden': 'Güncel bedel', 'surum': data['surum'], 'onizleme_anahtari': data['onizleme_anahtari'],
    }, format='json')
    assert r.status_code == 200, r.content
    assert r.json()['tutar'] == '150.00'
    assert len(r.json()['islemler']) == 2
    assert admin_client.delete(url).status_code == 405


def test_undo_api_retains_payment_in_history(invoice, admin_client):
    payment = services.ode_fatura(invoice)
    invoice.refresh_from_db()
    r = admin_client.post(f'/api/abonelik/faturalar/{invoice.pk}/odemeyi-geri-al/',
        {'neden': 'Yanlış tahsilat', 'surum': invoice.surum}, format='json')
    assert r.status_code == 200, r.content
    assert r.json()['aktif_tahsilat_var'] is False
    payment.refresh_from_db()
    assert payment.geri_alma_nedeni == 'Yanlış tahsilat'
    history = admin_client.get('/api/abonelik/odemeler/').json()
    rows = history if isinstance(history, list) else history['results']
    row = next(o for o in rows if o['id'] == payment.id)
    assert row['geri_alinma_tarihi'] and row['tutar'] == '100.00'


def test_zero_recalculation_does_not_modify_invoice(invoice):
    invoice.sozlesme.aylik_kullanim_bedeli = 0
    invoice.sozlesme.save()
    with pytest.raises(ValueError, match='sıfır'):
        change(invoice, 'YENIDEN_OLUSTUR', onizleme_anahtari='old')
    invoice.refresh_from_db()
    assert invoice.tutar == Decimal('100.00')
    assert invoice.kalemler.get().tutar == Decimal('100.00')
    assert not invoice.islemler.exists()


def test_legacy_single_line_invoice_rebuilds(invoice):
    invoice.kalemler.all().delete()
    invoice.tip = 'KULLANIM_BEDELI'
    invoice.save()
    data = preview(invoice)
    f = change(invoice, 'YENIDEN_OLUSTUR', onizleme_anahtari=data['onizleme_anahtari'])
    assert f.tutar == Decimal('150.00')
    assert f.kalemler.get().tip == 'ABONELIK'


@pytest.mark.parametrize('action', ['iptal', 'yeniden-olustur', 'odemeyi-geri-al'])
def test_pharmacist_cannot_correct(invoice, eczaci_client, action):
    r = eczaci_client.post(f'/api/abonelik/faturalar/{invoice.pk}/{action}/',
                          {'neden': 'Test', 'surum': 1}, format='json')
    assert r.status_code == 403
    invoice.refresh_from_db()
    assert invoice.durum == 'BEKLIYOR'
