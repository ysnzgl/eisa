"""Fatura düzeltmeleri: aynı kimlik/dönem, gerekçeli ve sürümlü işlem geçmişi."""
import datetime as dt
import hashlib
import json
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.core.uow import UnitOfWork
from . import services
from .models import CihazOdemePlani, Fatura, FaturaIslem, FaturaKalemi


def snapshot(fatura):
    return {
        "surum": fatura.surum, "durum": fatura.durum, "tutar": str(fatura.tutar),
        "matrah": str(fatura.matrah), "kdv_tutari": str(fatura.kdv_tutari),
        "tevkifat_tutari": str(fatura.tevkifat_tutari),
        "kesim_tarihi": str(fatura.kesim_tarihi) if fatura.kesim_tarihi else None,
        "hizmet_baslangic": str(fatura.hizmet_baslangic) if fatura.hizmet_baslangic else None,
        "hizmet_bitis": str(fatura.hizmet_bitis) if fatura.hizmet_bitis else None,
        "vade_tarihi": str(fatura.vade_tarihi), "iptal_nedeni": fatura.iptal_nedeni,
        "aciklama": fatura.aciklama,
        "odenme_tarihi": fatura.odenme_tarihi.isoformat() if fatura.odenme_tarihi else None,
        "kalemler": [dict(id=k.id, tip=k.tip, cihaz_plani=k.cihaz_plani_id,
                          taksit_no=k.taksit_no, tutar=str(k.tutar), aciklama=k.aciklama,
                          matrah=str(k.matrah), kdv_orani=k.kdv_orani, kdv_tutari=str(k.kdv_tutari),
                          tevkifat_orani=k.tevkifat_orani, tevkifat_tutari=str(k.tevkifat_tutari))
                     for k in fatura.kalemler.all()],
        "odemeler": [dict(id=o.id, tutar=str(o.tutar),
                          geri_alinma_tarihi=o.geri_alinma_tarihi.isoformat() if o.geri_alinma_tarihi else None)
                     for o in fatura.odemeler.all()],
    }


def preview(fatura):
    """Mevcut kalemlerin bedellerini günceller; dönem/taksit dağılımını korur."""
    kalemler = list(fatura.kalemler.select_related("cihaz_plani"))
    # Eski tek kalemli faturalar da aynı düzeltme akışına girer.
    if not kalemler:
        mapping = {
            Fatura.Tip.KULLANIM_BEDELI: FaturaKalemi.KalemTip.ABONELIK,
            Fatura.Tip.CIHAZ_TAKSIT: FaturaKalemi.KalemTip.CIHAZ_TAKSIT,
            Fatura.Tip.CIHAZ_KIRA: FaturaKalemi.KalemTip.CIHAZ_KIRA,
            Fatura.Tip.ACMA_KAPAMA: FaturaKalemi.KalemTip.ACMA_KAPAMA,
        }
        if fatura.tip not in mapping:
            raise ValueError("Faturanın yeniden hesaplanacak kalemleri bulunamadı.")
        kalemler = [FaturaKalemi(tip=mapping[fatura.tip], cihaz_plani=fatura.cihaz_plani,
                                taksit_no=fatura.taksit_no, aciklama=fatura.aciklama)]
    sonuc = []
    for k in kalemler:
        kdv_orani, tevkifat_orani = k.kdv_orani, k.tevkifat_orani
        if k.tip == FaturaKalemi.KalemTip.ABONELIK:
            s = fatura.sozlesme
            if not s or s.is_demo:
                raise ValueError("Standart sözleşme bulunamadı; faturayı iptal edebilirsiniz.")
            if not (s.kullanim_bedeli_baslangic.strftime('%Y-%m') <= fatura.donem <= s.bitis_tarihi.strftime('%Y-%m')):
                continue
            tutar = s.aylik_kullanim_bedeli
            kdv_orani, tevkifat_orani = s.kdv_orani, s.tevkifat_orani
        elif k.tip in (FaturaKalemi.KalemTip.CIHAZ_TAKSIT, FaturaKalemi.KalemTip.CIHAZ_KIRA):
            p = k.cihaz_plani
            if not p:
                raise ValueError("Cihaz planı silinmiş; fatura otomatik hesaplanamaz.")
            if p.durum == CihazOdemePlani.Durum.IPTAL:
                continue
            if k.tip == FaturaKalemi.KalemTip.CIHAZ_KIRA:
                if p.tip != CihazOdemePlani.Tip.KIRALIK:
                    raise ValueError("Cihaz planı türü değişmiş; faturayı iptal edin.")
                tutar = p.toplam_tutar
            else:
                if p.tip != CihazOdemePlani.Tip.SATILIK or not k.taksit_no or k.taksit_no > p.taksit_sayisi:
                    raise ValueError("Cihaz taksit planı değişmiş; faturayı iptal edin.")
                tutar = services.cihaz_taksit_matrahi(p, k.taksit_no)
            kdv_orani, tevkifat_orani = p.cihaz_kdv_orani, p.tevkifat_orani
        elif k.tip == FaturaKalemi.KalemTip.ACMA_KAPAMA:
            fiyat = services.aktif_fiyat()
            if not fiyat:
                raise ValueError("Aktif açma/kapama fiyatı bulunamadı.")
            tutar = fiyat.acma_kapama_bedeli
        else:
            raise ValueError("Bu fatura kalemi yeniden hesaplanamıyor.")
        vergi = services._vergi_kalemi(
            tip=k.tip, matrah=tutar, kdv_orani=kdv_orani, tevkifat_orani=tevkifat_orani,
            cihaz_plani=k.cihaz_plani, taksit_no=k.taksit_no, aciklama=k.aciklama,
        )
        vergi["cihaz_plani"] = k.cihaz_plani_id
        sonuc.append({key: str(value) if isinstance(value, Decimal) else value
                      for key, value in vergi.items()})
    toplam = sum((Decimal(k["tutar"]) for k in sonuc), Decimal("0.00"))
    if toplam <= 0:
        raise ValueError("Yeni tutar sıfır veya negatif; faturayı iptal edin.")
    odeme = fatura.odemeler.filter(geri_alinma_tarihi__isnull=True).aggregate(t=Sum("tutar"))["t"] or Decimal("0.00")
    engel = ""
    if odeme and odeme != toplam:
        engel = "Yeni tutar mevcut tahsilattan farklı. Önce tahsilat kaydını gerekçeyle geri alın."
    data = dict(surum=fatura.surum, eski_tutar=str(fatura.tutar), yeni_tutar=str(toplam),
                matrah=str(sum((Decimal(k["matrah"]) for k in sonuc), Decimal("0.00"))),
                kdv_tutari=str(sum((Decimal(k["kdv_tutari"]) for k in sonuc), Decimal("0.00"))),
                tevkifat_tutari=str(sum((Decimal(k["tevkifat_tutari"]) for k in sonuc), Decimal("0.00"))),
                tahsilat=str(odeme), vade_tarihi=str(fatura.vade_tarihi), kalemler=sonuc,
                engel=engel, onceki=snapshot(fatura))
    data["onizleme_anahtari"] = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    return data


@transaction.atomic
def correct(fatura_id, *, islem, neden, surum, user, onizleme_anahtari=""):
    fatura = Fatura.objects.select_for_update().get(pk=fatura_id)
    if not isinstance(neden, str) or not neden.strip() or len(neden.strip()) > 500:
        raise ValueError("İşlem nedeni zorunludur (en fazla 500 karakter).")
    if fatura.surum != surum:
        raise ValueError("Fatura değişmiş. Güncel faturayı açıp tekrar deneyin.")
    onceki = snapshot(fatura)
    with UnitOfWork(user=user) as uow:
        if islem == "IPTAL":
            if fatura.durum == Fatura.Durum.IPTAL:
                raise ValueError("Fatura zaten iptal edilmiş.")
            fatura.durum = Fatura.Durum.IPTAL
            fatura.iptal_nedeni = neden.strip()
            fatura.iptal_tarihi = timezone.now()
        elif islem == "ODEME_GERI_AL":
            odemeler = list(fatura.odemeler.filter(geri_alinma_tarihi__isnull=True))
            if not odemeler:
                raise ValueError("Geri alınacak tahsilat kaydı bulunamadı.")
            for odeme in odemeler:
                odeme.geri_alinma_tarihi = timezone.now()
                odeme.geri_alma_nedeni = neden.strip()
                uow.update(odeme, update_fields=["geri_alinma_tarihi", "geri_alma_nedeni"])
            fatura.odenme_tarihi = None
            if fatura.durum != Fatura.Durum.IPTAL:
                fatura.durum = _unpaid_status(fatura)
        elif islem == "YENIDEN_OLUSTUR":
            data = preview(fatura)
            if not onizleme_anahtari or data["onizleme_anahtari"] != onizleme_anahtari:
                raise ValueError("Hesaplama değişmiş. Önizlemeyi yenileyip tekrar onaylayın.")
            if data["engel"]:
                raise ValueError(data["engel"])
            for kalem in fatura.kalemler.all():
                uow.delete(kalem)
            for k in data["kalemler"]:
                uow.add(FaturaKalemi(fatura=fatura, tip=k["tip"], cihaz_plani_id=k["cihaz_plani"],
                                    taksit_no=k["taksit_no"], tutar=k["tutar"], aciklama=k["aciklama"],
                                    matrah=k["matrah"], kdv_orani=k["kdv_orani"], kdv_tutari=k["kdv_tutari"],
                                    tevkifat_orani=k["tevkifat_orani"], tevkifat_tutari=k["tevkifat_tutari"]))
            fatura.tutar = Decimal(data["yeni_tutar"])
            for field in ("matrah", "kdv_tutari", "tevkifat_tutari"):
                setattr(fatura, field, Decimal(data[field]))
            fatura.aciklama = "; ".join(k["aciklama"] for k in data["kalemler"])[:255]
            fatura.durum = Fatura.Durum.ODENDI if Decimal(data["tahsilat"]) else _unpaid_status(fatura)
            fatura.iptal_nedeni = ""
            fatura.iptal_tarihi = None
        else:
            raise ValueError("Geçersiz fatura işlemi.")
        uow.update(fatura, update_fields=["durum", "tutar", "matrah", "kdv_tutari", "tevkifat_tutari",
                                         "odenme_tarihi", "iptal_nedeni", "iptal_tarihi", "aciklama"])
        uow.add(FaturaIslem(fatura=fatura, islem=islem, neden=neden.strip(), onceki=onceki, sonraki=snapshot(fatura)))
    return fatura


def _unpaid_status(fatura):
    return (Fatura.Durum.GECIKTI if fatura.vade_tarihi < timezone.localdate() - dt.timedelta(days=services.GRACE_DAYS)
            else Fatura.Durum.BEKLIYOR)
