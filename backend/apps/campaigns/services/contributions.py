"""Sponsorluk tahsilatından sözleşmeye uygun eczane katkı payı üretimi."""
from __future__ import annotations

import datetime as dt
from collections import defaultdict
from decimal import Decimal, ROUND_DOWN

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.abonelik.models import Fatura, FaturaKalemi, Sozlesme
from apps.announcements.models import Announcement
from apps.pharmacies.models import Kiosk, KioskEczaneAtama

from ..models import KatkiHakedis, SponsorTahsilat


KATKI_ORANI = Decimal("0.15")
KURUS = Decimal("0.01")


def _fatura_gunu_kapsar(fatura, gun):
    if fatura.hizmet_baslangic and fatura.hizmet_bitis:
        return fatura.hizmet_baslangic <= gun < fatura.hizmet_bitis
    # Eski mali kayıtların hizmet aralığı bulunmayabilir.
    return fatura.donem == gun.strftime("%Y-%m")


def _paylari_dagit(havuz, gunler):
    """Kuruş farklarını en büyük kalan yöntemiyle, kimliğe göre deterministik dağıtır."""
    toplam = Decimal(sum(gunler.values()))
    exact = {pk: havuz * Decimal(gun) / toplam for pk, gun in gunler.items()}
    paylar = {pk: tutar.quantize(KURUS, rounding=ROUND_DOWN) for pk, tutar in exact.items()}
    kalan = int((havuz - sum(paylar.values())) / KURUS)
    for pk in sorted(exact, key=lambda pk: (-(exact[pk] - paylar[pk]), pk))[:kalan]:
        paylar[pk] += KURUS
    return paylar


@transaction.atomic
def hesapla_ve_kaydet(tahsilat: SponsorTahsilat) -> list[KatkiHakedis]:
    """Kapanmış dönemi kilit altında hesaplar; sıfır paylı hesap da tekrar açılamaz."""
    tahsilat = SponsorTahsilat.objects.select_for_update().select_related(
        "campaign__sponsorluk_tarifesi", "campaign__bolge",
    ).get(pk=tahsilat.pk)
    if tahsilat.hesaplanma_tarihi or tahsilat.hakedisler.exists():
        raise ValueError("Bu tahsilat için katkı payı daha önce hesaplanmış.")
    today = timezone.localdate()
    if tahsilat.tahsilat_tarihi > today:
        raise ValueError("Gelecek tarihli tahsilattan katkı payı üretilemez.")
    if tahsilat.donem_bitis > today:
        raise ValueError("Dönem tamamlanmadan kesin katkı payı hesaplanamaz.")
    if tahsilat.donem_bitis <= tahsilat.donem_baslangic or tahsilat.brut_tutar <= 0:
        raise ValueError("Tahsilat tutarı ve dönem aralığı geçersiz.")

    campaign = tahsilat.campaign
    assignments = list(campaign.kiosk_sponsorships.filter(is_active=True, kiosk__aktif=True).select_related("kiosk"))
    tariff_kind = (campaign.tarife_snapshot or {}).get("tur") or getattr(campaign.sponsorluk_tarifesi, "tur", None)
    region_pharmacies = set()
    if tariff_kind == "BOLGE":
        if not campaign.bolge_id:
            raise ValueError("Bölge sponsorluğunda dağıtım bölgesi tanımlanmalıdır.")
        scope = Q(pk__in=[])
        for row in campaign.bolge.kapsamlar.all():
            item = Q(eczane__il_id=row.il_id)
            if row.ilce_id:
                item &= Q(eczane__ilce_id=row.ilce_id)
            scope |= item
        # Bölge havuzunun paydası yalnız kampanyaya atanmış cihazlarla daraltılmaz.
        kiosks = list(Kiosk.objects.filter(scope, aktif=True).values_list("id", "eczane_id"))
        regional_history = list(KioskEczaneAtama.objects.filter(scope, kiosk__aktif=True).values_list("kiosk_id", "eczane_id"))
        region_pharmacies = {pharmacy for _, pharmacy in kiosks + regional_history}
        kiosks = list(dict(regional_history + kiosks).items())
    else:
        kiosks = list({(row.kiosk_id, row.kiosk.eczane_id) for row in assignments})

    history = defaultdict(list)
    for row in KioskEczaneAtama.objects.filter(kiosk_id__in=[pk for pk, _ in kiosks]):
        history[row.kiosk_id].append(row)
    membership = []
    for kiosk_id, pharmacy_id in kiosks:
        if history[kiosk_id]:
            for row in history[kiosk_id]:
                if tariff_kind == "BOLGE" and row.eczane_id not in region_pharmacies:
                    continue
                membership.append((kiosk_id, row.eczane_id,
                    timezone.localtime(row.baslangic_zamani).date(),
                    timezone.localtime(row.bitis_zamani).date() if row.bitis_zamani else None))
        else:
            # Eski cihazlarda kurulum/taşıma tarihçesi bulunmayabilir.
            membership.append((kiosk_id, pharmacy_id, None, None))

    contracts = defaultdict(list)
    for s in Sozlesme.objects.filter(
        eczane_id__in={eczane_id for _, eczane_id, _, _ in membership},
        durum=Sozlesme.Durum.AKTIF, tur=Sozlesme.Tur.STANDART,
        baslangic_tarihi__lt=tahsilat.donem_bitis,
    ):
        contracts[s.eczane_id].append(s)
    invoices = defaultdict(list)
    for f in Fatura.objects.filter(
        sozlesme_id__in=[s.pk for rows in contracts.values() for s in rows],
        durum__in=(Fatura.Durum.BEKLIYOR, Fatura.Durum.GECIKTI, Fatura.Durum.ODENDI),
    ).filter(Q(tip=Fatura.Tip.KULLANIM_BEDELI) | Q(kalemler__tip=FaturaKalemi.KalemTip.ABONELIK)).distinct():
        invoices[f.sozlesme_id].append(f)

    gunler = defaultdict(int)
    gun = max(tahsilat.donem_baslangic, timezone.localtime(campaign.start_date).date())
    end = min(tahsilat.donem_bitis, timezone.localtime(campaign.end_date).date())
    while gun < end:
        counted = set()
        for kiosk_id, eczane_id, installed, removed in membership:
            if kiosk_id in counted or (installed and gun < installed) or (removed and gun >= removed):
                continue
            if tariff_kind != "BOLGE" and not any(
                row.kiosk_id == kiosk_id
                and (not row.start_date or row.start_date <= gun)
                and (not row.end_date or gun <= row.end_date)
                and (not row.active_weekdays or gun.isoweekday() in row.active_weekdays)
                for row in assignments
            ):
                continue
            for s in contracts[eczane_id]:
                if s.kullanim_bedeli_baslangic <= gun < s.bitis_tarihi:
                    if not any(_fatura_gunu_kapsar(f, gun) for f in invoices[s.pk]):
                        raise ValueError(f"Eczane #{eczane_id}: {gun:%d.%m.%Y} hizmet gününü kapsayan abonelik faturası eksik.")
                    gunler[eczane_id] += 1
                    counted.add(kiosk_id)
                    break
        gun += dt.timedelta(days=1)

    toplam_gun = sum(gunler.values())
    havuz = (tahsilat.brut_tutar * KATKI_ORANI).quantize(KURUS)
    paylar = _paylari_dagit(havuz, gunler) if toplam_gun else {}
    rows = []
    for eczane_id, cihaz_gun in sorted(gunler.items()):
        pay = paylar[eczane_id]
        row = KatkiHakedis.objects.create(
            tahsilat=tahsilat, eczane_id=eczane_id,
            uygun_cihaz_gun=Decimal(cihaz_gun), toplam_uygun_cihaz_gun=Decimal(toplam_gun),
            brut_havuz=havuz, brut_pay=pay,
            hesap_detayi={"oran": "0.15", "donem_baslangic": str(tahsilat.donem_baslangic),
                          "donem_bitis": str(tahsilat.donem_bitis),
                          "kural": "hizmet_donemini_kapsayan_abonelik_faturasi_ve_cihaz_gun"},
        )
        Announcement.objects.create(
            kind=Announcement.Kind.GENERAL, title="Sponsorluk katkı payınız hesaplandı",
            message=(f"{tahsilat.donem_baslangic:%d.%m.%Y}–{tahsilat.donem_bitis:%d.%m.%Y} "
                     f"dönemine ait brüt katkı payınız {pay:.2f} TL olarak hesaplandı."),
            action_label="Katkı paylarını görüntüle", severity=Announcement.Severity.INFO,
            recurrence=Announcement.Recurrence.ONCE, start_date=today,
            target_scope=Announcement.TargetScope.PHARMACY, target_pharmacy_id=eczane_id,
        )
        row.durum = KatkiHakedis.Durum.BILDIRILDI
        row.bildirim_tarihi = timezone.now()
        row.save(update_fields=("durum", "bildirim_tarihi", "guncellenme_tarihi"))
        rows.append(row)
    tahsilat.hesaplanma_tarihi = timezone.now()
    tahsilat.hesap_ozeti = {
        "brut_havuz": str(havuz), "toplam_uygun_cihaz_gun": toplam_gun,
        "kiosklar": [{"kiosk": pk, "eczane": eczane_id} for pk, eczane_id in sorted(kiosks)],
        "cihaz_tarihcesi": [{"kiosk": pk, "eczane": pharmacy,
                             "baslangic": str(start) if start else None,
                             "bitis": str(end) if end else None}
                            for pk, pharmacy, start, end in membership],
        "dagitilan": str(sum(paylar.values(), Decimal("0.00"))),
        "durum": "HESAPLANDI" if rows else "UYGUN_CIHAZ_GUN_YOK",
    }
    tahsilat.save(update_fields=("hesaplanma_tarihi", "hesap_ozeti", "guncellenme_tarihi"))
    return rows
