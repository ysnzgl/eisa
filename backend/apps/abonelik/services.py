"""
Abonelik iş mantığı servisleri.

Faturalandırma üretimi (kullanım bedeli + cihaz taksiti), ödeme kaydı,
gecikmiş fatura güncellemesi ve eczane erişim kilidi kontrolü burada toplanır.
Scheduler job'ları (`apps.abonelik.jobs`) ve API view'leri bu fonksiyonları
çağırır; böylece iş kuralları tek yerde tutulur ve test edilebilir.
"""
from __future__ import annotations

import calendar
import datetime as _dt
import logging
from decimal import Decimal

from django.db import IntegrityError, models, transaction
from django.utils import timezone

from apps.core.uow import UnitOfWork

from .models import CihazOdemePlani, Fatura, FiyatTanimi, Odeme, ResmiTatil, Sozlesme

logger = logging.getLogger(__name__)

# Fatura vadesi geçtikten sonra eczane erişiminin kilitlenmesine kadar tanınan süre.
GRACE_DAYS = 7

# Cihaz taksitinin faturalandığı ayın son günü (ilk hafta penceresi).
CIHAZ_TAKSIT_SON_GUN = 7


def add_months(d: _dt.date, months: int) -> _dt.date:
    """`d` tarihine `months` ay ekler; ay sonu taşmalarını güvenli kırpar."""
    month_index = d.month - 1 + int(months)
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return _dt.date(year, month, min(d.day, last_day))


def donem_str(d: _dt.date) -> str:
    """Tarihi 'YYYY-MM' dönem anahtarına çevirir."""
    return f"{d.year:04d}-{d.month:02d}"


def add_days(d: _dt.date, days: int) -> _dt.date:
    """`d` tarihine `days` gün ekler."""
    return d + _dt.timedelta(days=int(days))


def add_business_days(d: _dt.date, days: int) -> _dt.date:
    """Kesim gününü saymadan hafta sonu ve kayıtlı resmi tatilleri atlar."""
    remaining = int(days)
    current = d
    if remaining < 0:
        raise ValueError("İş günü sayısı negatif olamaz.")
    if remaining == 0:
        return current
    # Aralık küçük olsa da tek tek sorgu üretmemek için geniş bir tatil kümesi al.
    window_end = d + _dt.timedelta(days=remaining * 3 + 14)
    holidays = set(
        ResmiTatil.objects.filter(tarih__gt=d, tarih__lte=window_end)
        .values_list("tarih", flat=True)
    )
    while remaining:
        current += _dt.timedelta(days=1)
        if current.weekday() >= 5 or current in holidays:
            continue
        remaining -= 1
    return current


# ── Fiyat tanımı (parametre) ─────────────────────────────────────────────────

def aktif_fiyat(*, bugun: _dt.date | None = None) -> FiyatTanimi | None:
    """Verilen tarihte geçerli en güncel fiyat tanımını döner (yoksa None)."""
    bugun = bugun or timezone.localdate()
    return (
        FiyatTanimi.objects.filter(gecerlilik_baslangic__lte=bugun)
        .order_by("-gecerlilik_baslangic", "-id")
        .first()
    )


def sozlesme_ticari_snapshot(eczane, *, belge_tarihi: _dt.date) -> tuple[dict, list]:
    """Eczanenin ilgili bölgesini ve tarihte geçerli tarifeleri dondurur."""
    from django.db.models import Q
    from apps.campaigns.models import BolgeKapsam, SponsorlukTarifesi

    kapsam = (
        BolgeKapsam.objects.filter(
            bolge__aktif=True,
            bolge__gecerlilik_baslangic__lte=belge_tarihi,
            il_id=eczane.il_id,
        )
        .filter(Q(bolge__gecerlilik_bitis__isnull=True) |
                Q(bolge__gecerlilik_bitis__gte=belge_tarihi))
        .filter(Q(ilce_id=eczane.ilce_id) | Q(ilce__isnull=True))
        .select_related("bolge", "il", "ilce")
        .order_by(models.Case(
            models.When(ilce_id=eczane.ilce_id, then=models.Value(0)),
            default=models.Value(1), output_field=models.IntegerField(),
        ), "bolge_id")
        .first()
    )
    bolge = {}
    if kapsam:
        bolge = {
            "id": kapsam.bolge_id, "kod": kapsam.bolge.kod, "ad": kapsam.bolge.ad,
            "il": kapsam.il.ad, "ilce": kapsam.ilce.ad if kapsam.ilce else None,
            "gecerlilik_baslangic": str(kapsam.bolge.gecerlilik_baslangic),
            "gecerlilik_bitis": str(kapsam.bolge.gecerlilik_bitis) if kapsam.bolge.gecerlilik_bitis else None,
        }
    tarifeler = SponsorlukTarifesi.objects.filter(
        aktif=True, gecerlilik_baslangic__lte=belge_tarihi,
    ).filter(Q(gecerlilik_bitis__isnull=True) | Q(gecerlilik_bitis__gte=belge_tarihi))
    snapshots = [{
        "id": t.id, "kod": t.kod, "ad": t.ad, "tur": t.tur,
        "min_cihaz": t.min_cihaz, "max_cihaz": t.max_cihaz,
        "brut_bedel": str(t.brut_bedel), "kdv_orani": t.kdv_orani,
        "gecerlilik_baslangic": str(t.gecerlilik_baslangic),
        "gecerlilik_bitis": str(t.gecerlilik_bitis) if t.gecerlilik_bitis else None,
    } for t in tarifeler]
    return bolge, snapshots


@transaction.atomic
def sozlesme_olustur(validated_data, *, planlar=None, user=None):
    """Tüm giriş yollarında sözleşme, ticari snapshot ve ilk borçlar birlikte yazılır."""
    from rest_framework.exceptions import ValidationError

    if planlar is not None and not isinstance(planlar, list):
        raise ValidationError({"cihaz_planlari": "Liste bekleniyor."})
    data = dict(validated_data)
    bolge, tarifeler = sozlesme_ticari_snapshot(data["eczane"], belge_tarihi=timezone.localdate())
    data.update(bolge_snapshot=bolge, sponsorluk_tarifeleri_snapshot=tarifeler)
    with UnitOfWork(user=user) as uow:
        sozlesme = uow.add(Sozlesme(**data))
        if planlar is not None:
            kaydet_cihaz_planlari(sozlesme, planlar, user=user)
        faturala_ayri(bugun=timezone.localdate(), sozlesme_id=sozlesme.pk)
    return sozlesme


@transaction.atomic
def kaydet_cihaz_planlari(sozlesme, planlar, *, user=None):
    """Planları kimliklerini koruyarak kaydeder; faturalanmış planlar silinmez."""
    from rest_framework.exceptions import ValidationError
    from .models import FaturaKalemi
    from .serializers import CihazOdemePlaniSerializer

    existing = {p.id: p for p in sozlesme.cihaz_planlari.all()}
    incoming = set()
    selected_devices = set()
    with UnitOfWork(user=user) as uow:
        for raw in planlar:
            if not isinstance(raw, dict):
                raise ValidationError({"cihaz_planlari": "Her cihaz planı nesne olmalıdır."})
            item = dict(raw)
            plan_id = item.get("id")
            if plan_id is not None:
                try:
                    plan_id = int(plan_id)
                except (TypeError, ValueError):
                    raise ValidationError({"cihaz_planlari": "Geçersiz cihaz planı kimliği."})
                if plan_id not in existing or plan_id in incoming:
                    raise ValidationError({"cihaz_planlari": "Cihaz planı bu sözleşmeye ait değil veya tekrarlanmış."})
                incoming.add(plan_id)
            instance = existing.get(plan_id)
            item.setdefault("baslangic_tarihi", sozlesme.baslangic_tarihi)
            ser = CihazOdemePlaniSerializer(instance=instance, data=item, partial=instance is not None)
            ser.is_valid(raise_exception=True)
            data = dict(ser.validated_data)
            devices = data.pop("cihazlar", None)
            if devices is not None:
                from apps.pharmacies.models import FizikselCihaz
                for device in FizikselCihaz.objects.select_for_update().filter(pk__in=[d.pk for d in devices]):
                    if device.pk in selected_devices:
                        raise ValidationError({"cihazlar": "Aynı seri numarası birden fazla planda seçilemez."})
                    if not device.aktif or device.eczane_id not in (None, sozlesme.eczane_id):
                        raise ValidationError({"cihazlar": f"{device.seri_no} başka bir eczaneye ait veya pasif."})
                    selected_devices.add(device.pk)
                    device.eczane_id = sozlesme.eczane_id
                    uow.update(device, update_fields=["eczane"])
                if devices and not data.get("cihaz_bilgisi"):
                    data["cihaz_bilgisi"] = "; ".join(dict.fromkeys(f"{d.marka} {d.model}".strip() for d in devices))
            oteleme = data.get("oteleme_ay", getattr(instance, "oteleme_ay", 0))
            data["baslangic_tarihi"] = add_months(sozlesme.baslangic_tarihi, oteleme)
            if instance:
                for field, value in data.items():
                    setattr(instance, field, value)
                uow.update(instance)
            else:
                instance = uow.add(CihazOdemePlani(sozlesme=sozlesme, **data))
            if devices is not None:
                instance.cihazlar.set(devices)
        for plan_id, plan in existing.items():
            if plan_id not in incoming:
                if Fatura.objects.filter(cihaz_plani=plan).exists() or FaturaKalemi.objects.filter(cihaz_plani=plan).exists():
                    plan.durum = CihazOdemePlani.Durum.IPTAL
                    uow.update(plan, update_fields=["durum"])
                else:
                    uow.delete(plan)


def sozlesme_bitis_hesapla(
    *,
    tur: str,
    baslangic_tarihi: _dt.date,
    sozlesme_tipi_ay: int | None = None,
    demo_gun: int | None = None,
    oteleme_ay: int = 0,
    ek_ay_toplam: int = 0,
    ek_gun_toplam: int = 0,
) -> _dt.date:
    """Verilen sözleşme parametrelerine göre bitiş tarihini hesaplar."""
    if tur == Sozlesme.Tur.DEMO:
        toplam_gun = int(demo_gun or 0) + int(ek_gun_toplam or 0)
        return baslangic_tarihi + _dt.timedelta(days=toplam_gun)
    toplam_ay = int(sozlesme_tipi_ay or 0) + int(oteleme_ay or 0) + int(ek_ay_toplam or 0)
    return add_months(baslangic_tarihi, toplam_ay)


def cakisan_aktif_sozlesme(
    *,
    eczane_id: int,
    tur: str,
    baslangic_tarihi: _dt.date,
    sozlesme_tipi_ay: int | None = None,
    demo_gun: int | None = None,
    oteleme_ay: int = 0,
    ek_ay_toplam: int = 0,
    ek_gun_toplam: int = 0,
    exclude_id: int | None = None,
) -> Sozlesme | None:
    """Çakışan AKTIF sözleşme varsa onu döner; yoksa None.

    Çakışma kuralı: [yeni_baslangic, yeni_bitis] ile mevcut aktif sözleşmenin
    [baslangic, bitis] aralıkları kesişiyorsa çakışma vardır.
    """
    yeni_bitis = sozlesme_bitis_hesapla(
        tur=tur,
        baslangic_tarihi=baslangic_tarihi,
        sozlesme_tipi_ay=sozlesme_tipi_ay,
        demo_gun=demo_gun,
        oteleme_ay=oteleme_ay,
        ek_ay_toplam=ek_ay_toplam,
        ek_gun_toplam=ek_gun_toplam,
    )

    qs = Sozlesme.objects.filter(eczane_id=eczane_id, durum=Sozlesme.Durum.AKTIF)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)

    for mevcut in qs:
        mevcut_bitis = mevcut.bitis_tarihi
        if baslangic_tarihi <= mevcut_bitis and mevcut.baslangic_tarihi <= yeni_bitis:
            return mevcut
    return None


# ── Kullanım bedeli faturalandırma ──────────────────────────────────────────

def faturala_kullanim_bedeli(*, bugun: _dt.date | None = None) -> int:
    """Aktif sözleşmeler için içinde bulunulan dönemin kullanım bedeli faturasını üretir.

    Öteleme (grace) dönemi ve sözleşme bitişi kontrol edilir. İdempotenttir:
    aynı eczane + dönem için ikinci fatura oluşmaz.

    Dönüş: oluşturulan fatura sayısı.
    """
    bugun = bugun or timezone.localdate()
    # 1 ay önceden: bu ayki job, gelecek ayın faturasını keser.
    prox = add_months(bugun, 1)
    donem = donem_str(prox)
    prox_ay = _dt.date(prox.year, prox.month, 1)
    olusturulan = 0

    # Demo sözleşmelerde kullanım bedeli faturalanmaz.
    sozlesmeler = Sozlesme.objects.filter(
        durum=Sozlesme.Durum.AKTIF, tur=Sozlesme.Tur.STANDART
    ).select_related("eczane")
    for sozlesme in sozlesmeler:
        baslangic = sozlesme.kullanim_bedeli_baslangic
        bitis = sozlesme.bitis_tarihi
        # Gelecek ay öteleme dönemi içindeyse veya sözleşme sona ermişse kesme.
        if prox_ay < baslangic or prox_ay > bitis:
            continue
        if _fatura_var(sozlesme.eczane_id, Fatura.Tip.KULLANIM_BEDELI, donem, None):
            continue

        # Vade: sözleşme başlangıç gününü fatura ayında kullan (~30 gün ödeme süresi).
        vade = _vade_sozlesme_gun(sozlesme.baslangic_tarihi.day, prox)
        try:
            with UnitOfWork() as uow:
                uow.add(Fatura(
                    eczane_id=sozlesme.eczane_id,
                    sozlesme=sozlesme,
                    tip=Fatura.Tip.KULLANIM_BEDELI,
                    donem=donem,
                    taksit_no=None,
                    tutar=sozlesme.aylik_kullanim_bedeli,
                    vade_tarihi=vade,
                    durum=Fatura.Durum.BEKLIYOR,
                    aciklama=f"{donem} dönemi e-İSA kullanım bedeli",
                ))
            olusturulan += 1
        except IntegrityError:
            # Yarış durumu: eşzamanlı üretim aynı faturayı eklemiş.
            continue

    if olusturulan:
        logger.info("faturala_kullanim_bedeli: %d fatura üretildi (dönem=%s)", olusturulan, donem)
    return olusturulan


# ── Cihaz kira faturalandırma (kiralık cihaz) ───────────────────────────────

def faturala_cihaz_kira(*, bugun: _dt.date | None = None) -> int:
    """Kiralık cihazlı aktif standart sözleşmeler için aylık kira faturası üretir.

    Kira, sözleşme başlangıcından bitişine kadar her dönem faturalanır (öteleme
    kira bedelini etkilemez). İdempotenttir: aynı eczane + dönem için tek fatura.

    Dönüş: oluşturulan fatura sayısı.
    """
    bugun = bugun or timezone.localdate()
    prox = add_months(bugun, 1)
    donem = donem_str(prox)
    prox_ay = _dt.date(prox.year, prox.month, 1)
    olusturulan = 0

    sozlesmeler = Sozlesme.objects.filter(
        durum=Sozlesme.Durum.AKTIF,
        tur=Sozlesme.Tur.STANDART,
        cihaz_durumu=Sozlesme.CihazDurum.KIRALIK,
    ).select_related("eczane")
    for sozlesme in sozlesmeler:
        if not sozlesme.cihaz_kira_bedeli or sozlesme.cihaz_kira_bedeli <= 0:
            continue
        bitis_ay = _dt.date(sozlesme.bitis_tarihi.year, sozlesme.bitis_tarihi.month, 1)
        bas_ay = _dt.date(sozlesme.baslangic_tarihi.year, sozlesme.baslangic_tarihi.month, 1)
        if prox_ay < bas_ay or prox_ay > bitis_ay:
            continue
        if _fatura_var(sozlesme.eczane_id, Fatura.Tip.CIHAZ_KIRA, donem, None):
            continue

        vade = _son_gun_ay(bugun)  # bu ayın son günü
        try:
            with UnitOfWork() as uow:
                uow.add(Fatura(
                    eczane_id=sozlesme.eczane_id,
                    sozlesme=sozlesme,
                    tip=Fatura.Tip.CIHAZ_KIRA,
                    donem=donem,
                    taksit_no=None,
                    tutar=sozlesme.cihaz_kira_bedeli,
                    vade_tarihi=vade,
                    durum=Fatura.Durum.BEKLIYOR,
                    aciklama=f"{donem} dönemi cihaz kira bedeli",
                ))
            olusturulan += 1
        except IntegrityError:
            continue

    # Yeni yapı: CihazOdemePlani tip=KIRALIK planları.
    kiralik_planlar = CihazOdemePlani.objects.filter(
        durum=CihazOdemePlani.Durum.AKTIF,
        tip=CihazOdemePlani.Tip.KIRALIK,
        sozlesme__durum=Sozlesme.Durum.AKTIF,
    ).select_related("sozlesme")
    for plan in kiralik_planlar:
        if not plan.aylik_kira_bedeli or plan.aylik_kira_bedeli <= 0:
            continue
        soz = plan.sozlesme
        prox_plan = add_months(bugun, 1)
        prox_ay_plan = _dt.date(prox_plan.year, prox_plan.month, 1)
        bas_ay = _dt.date(plan.baslangic_tarihi.year, plan.baslangic_tarihi.month, 1)
        bitis_ay = _dt.date(soz.bitis_tarihi.year, soz.bitis_tarihi.month, 1)
        if prox_ay_plan < bas_ay or prox_ay_plan > bitis_ay:
            continue
        donem_plan = donem_str(prox_plan)
        if _fatura_var(soz.eczane_id, Fatura.Tip.CIHAZ_KIRA, donem_plan, None):
            continue
        vade_plan = _vade_sozlesme_gun(plan.baslangic_tarihi.day, prox_plan)
        try:
            with UnitOfWork() as uow:
                uow.add(Fatura(
                    eczane_id=soz.eczane_id,
                    sozlesme=soz,
                    tip=Fatura.Tip.CIHAZ_KIRA,
                    donem=donem_plan,
                    taksit_no=None,
                    tutar=plan.toplam_tutar,
                    vade_tarihi=vade_plan,
                    durum=Fatura.Durum.BEKLIYOR,
                    aciklama=f"{donem_plan} dönemi cihaz kira ({plan.adet} adet)",
                ))
            olusturulan += 1
        except IntegrityError:
            continue

    if olusturulan:
        logger.info("faturala_cihaz_kira: %d fatura üretildi (dönem=%s)", olusturulan, donem)
    return olusturulan


# ── Cihaz taksiti faturalandırma ────────────────────────────────────────────

def faturala_cihaz_taksit(*, bugun: _dt.date | None = None) -> int:
    """Her ayın ilk haftasında aktif cihaz planları için sıradaki taksiti üretir.

    İdempotenttir (eczane + dönem + taksit_no benzersiz). Taksit sayısı dolan
    plan TAMAMLANDI'ya çekilir.

    Dönüş: oluşturulan fatura sayısı.
    """
    bugun = bugun or timezone.localdate()
    donem = donem_str(bugun)
    olusturulan = 0

    planlar = CihazOdemePlani.objects.filter(
        durum=CihazOdemePlani.Durum.AKTIF
    ).select_related("sozlesme")
    for plan in planlar:
        if bugun < plan.baslangic_tarihi:
            continue
        kesilmis = Fatura.objects.filter(
            cihaz_plani=plan, tip=Fatura.Tip.CIHAZ_TAKSIT
        ).exclude(durum=Fatura.Durum.IPTAL).count()
        if kesilmis >= plan.taksit_sayisi:
            _tamamla_plan(plan)
            continue

        # Ayda tek taksit: bu dönem için zaten taksit kesilmişse atla (idempotent).
        if Fatura.objects.filter(
            cihaz_plani=plan, tip=Fatura.Tip.CIHAZ_TAKSIT, donem=donem
        ).exclude(durum=Fatura.Durum.IPTAL).exists():
            continue

        taksit_no = kesilmis + 1
        eczane_id = plan.sozlesme.eczane_id
        if _fatura_var(eczane_id, Fatura.Tip.CIHAZ_TAKSIT, donem, taksit_no):
            continue

        vade = _vade_ay_ici(bugun, gun=CIHAZ_TAKSIT_SON_GUN)
        try:
            with UnitOfWork() as uow:
                uow.add(Fatura(
                    eczane_id=eczane_id,
                    sozlesme=plan.sozlesme,
                    cihaz_plani=plan,
                    tip=Fatura.Tip.CIHAZ_TAKSIT,
                    donem=donem,
                    taksit_no=taksit_no,
                    tutar=plan.taksit_tutari,
                    vade_tarihi=vade,
                    durum=Fatura.Durum.BEKLIYOR,
                    aciklama=f"Cihaz taksiti {taksit_no}/{plan.taksit_sayisi}",
                ))
            olusturulan += 1
            if taksit_no >= plan.taksit_sayisi:
                _tamamla_plan(plan)
        except IntegrityError:
            continue

    if olusturulan:
        logger.info("faturala_cihaz_taksit: %d fatura üretildi (dönem=%s)", olusturulan, donem)
    return olusturulan


# ── Gecikmiş fatura güncellemesi ────────────────────────────────────────────

def guncelle_gecikmis_faturalar(*, bugun: _dt.date | None = None) -> int:
    """Vadesi + grace süresi geçmiş BEKLIYOR faturaları GECIKTI yapar.

    Dönüş: güncellenen fatura sayısı.
    """
    bugun = bugun or timezone.localdate()
    sinir = bugun - _dt.timedelta(days=GRACE_DAYS)
    updated = Fatura.objects.filter(
        durum=Fatura.Durum.BEKLIYOR, vade_tarihi__lt=sinir
    ).update(durum=Fatura.Durum.GECIKTI, guncellenme_tarihi=timezone.now())
    if updated:
        logger.info("guncelle_gecikmis_faturalar: %d fatura GECIKTI", updated)
    return updated


# ── Ödeme ───────────────────────────────────────────────────────────────────

@transaction.atomic
def ode_fatura(fatura: Fatura, *, yontem: str = Odeme.Yontem.KREDI_KARTI,
              aciklama: str = "", user=None) -> Odeme:
    """Faturaya karşılık tahsilat kaydı oluşturur ve faturasıyı ÖDENDİ yapar."""
    fatura = Fatura.objects.select_for_update().get(pk=fatura.pk)
    if fatura.durum == Fatura.Durum.ODENDI:
        raise ValueError("Fatura zaten ödenmiş.")
    if fatura.durum == Fatura.Durum.IPTAL:
        raise ValueError("İptal edilmiş fatura ödenemez.")

    now = timezone.now()
    was_gecikti = (fatura.durum == Fatura.Durum.GECIKTI)
    with UnitOfWork(user=user) as uow:
        odeme = Odeme(fatura=fatura, tutar=fatura.tutar, yontem=yontem,
                      aciklama=aciklama, odeme_tarihi=now)
        uow.add(odeme)
        fatura.durum = Fatura.Durum.ODENDI
        fatura.odenme_tarihi = now
        uow.update(fatura, update_fields=["durum", "odenme_tarihi"])

    # Gecikmiş fatura ödenince açma/kapama bedeli faturası oluştur.
    if was_gecikti:
        _olustur_acma_kapama_fatura(fatura, user=user)
    return odeme


# ── Erişim kilidi ────────────────────────────────────────────────────────────

def eczane_erisim_kapali(eczane_id: int, *, bugun: _dt.date | None = None) -> bool:
    """Eczanenin vadesi + grace süresi geçmiş ödenmemiş faturası var mı?

    True ise eczacı panel erişimi kilitlenir. Fatura durumu GECIKTI'ye
    güncellenmemiş olsa bile canlı hesaplanır (scheduler gecikmesine dayanıklı).
    Demo modundaki eczane (gerçek sözleşmesi yok) hiçbir zaman kilitlenmez.
    """
    if not eczane_id:
        return False
    if eczane_demo_modunda(eczane_id):
        return False
    bugun = bugun or timezone.localdate()
    sinir = bugun - _dt.timedelta(days=GRACE_DAYS)
    return Fatura.objects.filter(
        eczane_id=eczane_id,
        durum__in=(Fatura.Durum.BEKLIYOR, Fatura.Durum.GECIKTI),
        vade_tarihi__lt=sinir,
    ).exists()


def eczane_demo_modunda(eczane_id: int) -> bool:
    """Eczanenin aktif sözleşmesi DEMO türündeyse demo aşamasındadır.

    Demo aşamasında kullanım bedeli faturalanmaz ve erişim kilidi uygulanmaz.
    Aktif sözleşme yoksa (sözleşmesiz eczane) demo sayılmaz — ayrı durumdur.
    """
    sozlesme = eczane_aktif_sozlesme(eczane_id)
    return bool(sozlesme) and sozlesme.tur == Sozlesme.Tur.DEMO


def eczane_aktif_sozlesme(eczane_id: int):
    """Eczanenin geçerli (AKTIF) sözleşmesini döner; yoksa None.

    Birden çok AKTIF varsa en yeni başlangıçlı seçilir.
    """
    if not eczane_id:
        return None
    return (
        Sozlesme.objects.filter(eczane_id=eczane_id, durum=Sozlesme.Durum.AKTIF)
        .order_by("-baslangic_tarihi", "-id")
        .first()
    )


def odeme_durumu(eczane_id: int, *, bugun: _dt.date | None = None) -> str:
    """Eczanenin ödeme durumu: DEMO | GECIKTI | BEKLEYEN | GUNCEL | YOK."""
    sozlesme = eczane_aktif_sozlesme(eczane_id)
    if sozlesme is None:
        return "YOK"
    if sozlesme.tur == Sozlesme.Tur.DEMO:
        return "DEMO"
    if eczane_erisim_kapali(eczane_id, bugun=bugun):
        return "GECIKTI"
    acik = Fatura.objects.filter(
        eczane_id=eczane_id,
        durum__in=(Fatura.Durum.BEKLIYOR, Fatura.Durum.GECIKTI),
    ).exists()
    return "BEKLEYEN" if acik else "GUNCEL"


def _olustur_acma_kapama_fatura(fatura: Fatura, *, user=None) -> None:
    """Gecikmiş fatura ödendikten sonra açma/kapama bedeli faturası oluşturur."""
    fiyat = aktif_fiyat()
    if not fiyat or not fiyat.acma_kapama_bedeli or fiyat.acma_kapama_bedeli <= 0:
        return
    # Aynı döneme zaten açma/kapama faturası varsa oluşturma.
    donem = donem_str(timezone.localdate())
    if Fatura.objects.filter(
        eczane_id=fatura.eczane_id,
        tip=Fatura.Tip.ACMA_KAPAMA,
        donem=donem,
    ).exists():
        return
    try:
        with UnitOfWork(user=user) as uow:
            uow.add(Fatura(
                eczane_id=fatura.eczane_id,
                sozlesme=fatura.sozlesme,
                tip=Fatura.Tip.ACMA_KAPAMA,
                donem=donem,
                taksit_no=None,
                tutar=fiyat.acma_kapama_bedeli,
                vade_tarihi=timezone.localdate() + _dt.timedelta(days=GRACE_DAYS),
                durum=Fatura.Durum.BEKLIYOR,
                aciklama=f"Hesap açma/kapama bedeli ({donem})",
            ))
    except IntegrityError:
        pass


def faturala_ayri(*, bugun: _dt.date | None = None,
                  sozlesme_id: int | None = None) -> int:
    """Abonelik ve her cihaz planı için bağımsız faturalar üretir.

    Gelecek dönem peşinen kesilmez. Abonelik ve cihaz ötelemeleri ayrıdır;
    her faturanın vadesi kendi kesim tarihinden 7 iş günü sonradır.
    Eski birleşik faturada aynı kalem varsa ikinci kez borç doğurmaz.
    """
    from .models import CihazOdemePlani, FaturaKalemi

    bugun = bugun or timezone.localdate()
    olusturulan = 0
    sozlesmeler = (
        Sozlesme.objects.filter(durum=Sozlesme.Durum.AKTIF, tur=Sozlesme.Tur.STANDART)
        .prefetch_related("cihaz_planlari")
    )
    if sozlesme_id is not None:
        sozlesmeler = sozlesmeler.filter(pk=sozlesme_id)

    for sozlesme in sozlesmeler:
        offset = 0
        period = sozlesme.kullanim_bedeli_baslangic
        while period <= bugun and period < sozlesme.bitis_tarihi:
            donem = donem_str(period)
            if not _kalem_faturalanmis(
                sozlesme, donem, FaturaKalemi.KalemTip.ABONELIK,
            ):
                kalem = _vergi_kalemi(
                    tip=FaturaKalemi.KalemTip.ABONELIK,
                    matrah=sozlesme.aylik_kullanim_bedeli,
                    kdv_orani=sozlesme.kdv_orani,
                    tevkifat_orani=sozlesme.tevkifat_orani,
                    cihaz_plani=None, taksit_no=None,
                    aciklama=f"{donem} abonelik bedeli",
                )
                olusturulan += int(_ayri_fatura_olustur(
                    sozlesme, period, Fatura.Tip.KULLANIM_BEDELI, kalem,
                    kesim_tarihi=bugun,
                    hizmet_bitis=min(add_months(sozlesme.baslangic_tarihi, sozlesme.oteleme_ay + offset + 1), sozlesme.bitis_tarihi),
                ))
            offset += 1
            period = add_months(sozlesme.baslangic_tarihi, sozlesme.oteleme_ay + offset)

        for plan in sozlesme.cihaz_planlari.all():
            if plan.durum != CihazOdemePlani.Durum.AKTIF:
                continue
            if plan.tip == CihazOdemePlani.Tip.TAHSIS:
                continue
            offset = 0
            period = plan.baslangic_tarihi
            while period <= bugun and period < sozlesme.bitis_tarihi:
                donem = donem_str(period)
                if plan.tip == CihazOdemePlani.Tip.KIRALIK:
                    if plan.aylik_kira_bedeli and not _kalem_faturalanmis(
                        sozlesme, donem, FaturaKalemi.KalemTip.CIHAZ_KIRA,
                        cihaz_plani=plan,
                    ):
                        kalem = _vergi_kalemi(
                            tip=FaturaKalemi.KalemTip.CIHAZ_KIRA,
                            matrah=plan.toplam_tutar,
                            kdv_orani=plan.cihaz_kdv_orani,
                            tevkifat_orani=plan.tevkifat_orani,
                            cihaz_plani=plan, taksit_no=None,
                            aciklama=f"{donem} cihaz kira ({plan.adet} adet)",
                        )
                        olusturulan += int(_ayri_fatura_olustur(
                            sozlesme, period, Fatura.Tip.CIHAZ_KIRA,
                            kalem, plan=plan, kesim_tarihi=bugun,
                            hizmet_bitis=min(cihaz_donem_tarihi(plan, offset + 1), sozlesme.bitis_tarihi),
                        ))
                    offset += 1
                    period = cihaz_donem_tarihi(plan, offset)
                    continue

                if plan.tip != CihazOdemePlani.Tip.SATILIK or not plan.pesin_fiyat:
                    break
                taksit_no = offset + 1
                if taksit_no > int(plan.taksit_sayisi or 1):
                    break
                if not _kalem_faturalanmis(
                    sozlesme, donem, FaturaKalemi.KalemTip.CIHAZ_TAKSIT,
                    cihaz_plani=plan, taksit_no=taksit_no,
                ):
                    matrah = cihaz_taksit_matrahi(plan, taksit_no)
                    kalem = _vergi_kalemi(
                        tip=FaturaKalemi.KalemTip.CIHAZ_TAKSIT,
                        matrah=matrah, kdv_orani=plan.cihaz_kdv_orani,
                        tevkifat_orani=plan.tevkifat_orani,
                        cihaz_plani=plan, taksit_no=taksit_no,
                        aciklama=(f"Cihaz satışı peşin ({plan.adet} adet)" if plan.taksit_sayisi == 1
                                  else f"Cihaz taksit {taksit_no}/{plan.taksit_sayisi}"),
                    )
                    olusturulan += int(_ayri_fatura_olustur(
                        sozlesme, period, Fatura.Tip.CIHAZ_TAKSIT,
                        kalem, plan=plan, taksit_no=taksit_no, kesim_tarihi=bugun,
                        hizmet_bitis=min(cihaz_donem_tarihi(plan, offset + 1), sozlesme.bitis_tarihi),
                    ))
                offset += 1
                period = cihaz_donem_tarihi(plan, offset)

            if plan.tip == CihazOdemePlani.Tip.SATILIK:
                taksit_sayisi = int(plan.taksit_sayisi or 1)
                tum_taksitler_faturalandi = all(
                    _kalem_faturalanmis(
                        sozlesme,
                        donem_str(cihaz_donem_tarihi(plan, sira - 1)),
                        FaturaKalemi.KalemTip.CIHAZ_TAKSIT,
                        cihaz_plani=plan,
                        taksit_no=sira,
                    )
                    for sira in range(1, taksit_sayisi + 1)
                )
                if tum_taksitler_faturalandi:
                    _tamamla_plan(plan)

    if olusturulan:
        logger.info("faturala_ayri: %d fatura üretildi", olusturulan)
    return olusturulan


def _kalem_faturalanmis(sozlesme, donem, kalem_tipi, *,
                        cihaz_plani=None, taksit_no=None) -> bool:
    from .models import FaturaKalemi

    direct_type = {
        FaturaKalemi.KalemTip.ABONELIK: Fatura.Tip.KULLANIM_BEDELI,
        FaturaKalemi.KalemTip.CIHAZ_TAKSIT: Fatura.Tip.CIHAZ_TAKSIT,
        FaturaKalemi.KalemTip.CIHAZ_KIRA: Fatura.Tip.CIHAZ_KIRA,
    }.get(kalem_tipi)
    direct = Fatura.objects.filter(
        sozlesme=sozlesme, donem=donem, tip=direct_type,
        cihaz_plani=cihaz_plani,
    )
    if taksit_no is not None:
        direct = direct.filter(taksit_no=taksit_no)
    if direct_type and direct.exists():
        return True

    qs = FaturaKalemi.objects.filter(
        fatura__sozlesme=sozlesme, fatura__donem=donem, tip=kalem_tipi,
    )
    qs = qs.filter(cihaz_plani=cihaz_plani)
    if taksit_no is not None:
        qs = qs.filter(taksit_no=taksit_no)
    return qs.exists()


def _ayri_fatura_olustur(sozlesme, period, fatura_tipi, kalem, *,
                         plan=None, taksit_no=None, kesim_tarihi=None,
                         hizmet_bitis=None) -> bool:
    from .models import FaturaKalemi

    kesim_tarihi = kesim_tarihi or period
    try:
        with transaction.atomic():
            fatura = Fatura.objects.create(
                eczane_id=sozlesme.eczane_id, sozlesme=sozlesme,
                cihaz_plani=plan, tip=fatura_tipi, donem=donem_str(period),
                taksit_no=taksit_no, tutar=kalem["tutar"],
                matrah=kalem["matrah"], kdv_tutari=kalem["kdv_tutari"],
                tevkifat_tutari=kalem["tevkifat_tutari"], kesim_tarihi=kesim_tarihi,
                hizmet_baslangic=period, hizmet_bitis=hizmet_bitis or add_months(period, 1),
                vade_tarihi=add_business_days(kesim_tarihi, 7),
                durum=Fatura.Durum.BEKLIYOR, aciklama=kalem["aciklama"],
            )
            FaturaKalemi.objects.create(fatura=fatura, **kalem)
        return True
    except IntegrityError:
        if Fatura.objects.filter(eczane_id=sozlesme.eczane_id, tip=fatura_tipi,
                                 donem=donem_str(period), cihaz_plani=plan).exists():
            return False
        raise


def faturala_aylik_birlesik(*, bugun: _dt.date | None = None,
                            sozlesme_id: int | None = None) -> int:
    """Eski entegrasyon adı; yeni birleşik fatura üretmez."""
    return faturala_ayri(bugun=bugun, sozlesme_id=sozlesme_id)


def _ay_farki(start: _dt.date, current: _dt.date) -> int:
    return (current.year - start.year) * 12 + current.month - start.month


def cihaz_donem_tarihi(plan, offset: int) -> _dt.date:
    """Kısa aydan sonra sözleşmenin asıl gününe dönen cihaz dönem tarihi."""
    s = plan.sozlesme
    if plan.baslangic_tarihi == add_months(s.baslangic_tarihi, plan.oteleme_ay):
        return add_months(s.baslangic_tarihi, plan.oteleme_ay + offset)
    return add_months(plan.baslangic_tarihi, offset)


def cihaz_taksit_matrahi(plan, taksit_no: int) -> Decimal:
    """Son taksit kuruş farkını kapatarak plan toplamını korur."""
    sayi = int(plan.taksit_sayisi or 1)
    if taksit_no == sayi:
        return plan.toplam_tutar - plan.taksit_tutari * (sayi - 1)
    return plan.taksit_tutari


def _vergi_kalemi(*, tip, matrah, kdv_orani, tevkifat_orani, cihaz_plani,
                  taksit_no, aciklama):
    matrah = Decimal(matrah).quantize(Decimal("0.01"))
    kdv = (matrah * Decimal(kdv_orani or 0) / Decimal("100")).quantize(Decimal("0.01"))
    kesir = Decimal("0")
    if tevkifat_orani:
        pay, payda = tevkifat_orani.split("/", 1)
        kesir = Decimal(pay) / Decimal(payda)
    tevkifat = (kdv * kesir).quantize(Decimal("0.01"))
    return {
        "tip": tip, "cihaz_plani": cihaz_plani, "taksit_no": taksit_no,
        "matrah": matrah, "kdv_orani": int(kdv_orani or 0), "kdv_tutari": kdv,
        "tevkifat_orani": tevkifat_orani or "", "tevkifat_tutari": tevkifat,
        "tutar": matrah + kdv - tevkifat, "aciklama": aciklama,
    }


# ── Sözleşme uzatma (tarihçe) ────────────────────────────────────────────────

def iptal_sozlesme(sozlesme: Sozlesme, *, neden: str = "", user=None):
    """Sözleşmeyi iptal eder ve tarihçeye kayıt düşer."""
    from .models import SozlesmeUzatma

    if sozlesme.durum == Sozlesme.Durum.IPTAL:
        raise ValueError("Sözleşme zaten iptal edilmiş.")

    with UnitOfWork(user=user) as uow:
        uow.add(SozlesmeUzatma(
            sozlesme=sozlesme,
            is_iptal=True,
            neden="",
            iptal_nedeni=neden,
        ))
        sozlesme.durum = Sozlesme.Durum.IPTAL
        uow.update(sozlesme, update_fields=["durum"])
    return sozlesme


def sozlesme_onayla(sozlesme: Sozlesme, *, ip_address: str = "", user=None) -> Sozlesme:
    """Eczacının dijital sözleşme onayını kaydeder ve metni dondurur."""
    from .contract_template import onay_blogu_html, render_sozlesme_html

    if not sozlesme.onay_gerekli:
        return sozlesme
    if sozlesme.sozlesme_surumu == "2026-EK1":
        raise ValueError("Yeni belge setinde dijital imza entegrasyonu henüz devrede değildir.")
    with UnitOfWork(user=user) as uow:
        sozlesme.eczaci_onay_tarihi = timezone.now()
        sozlesme.eczaci_onay_ip = ip_address or None
        # Onay anındaki tam metni dondur (immutable snapshot).
        sozlesme.onayli_sozlesme_metni = (
            render_sozlesme_html(sozlesme) + onay_blogu_html(sozlesme)
        )
        uow.update(sozlesme, update_fields=[
            "eczaci_onay_tarihi", "eczaci_onay_ip", "onayli_sozlesme_metni",
        ])
    return sozlesme


def uzat_sozlesme(sozlesme: Sozlesme, *, ek_ay: int | None = None,
                  ek_gun: int | None = None, neden: str = "", user=None):
    """Sözleşmeyi uzatır; SozlesmeUzatma kaydı oluşturur ve toplamları günceller.

    Standart sözleşme ay ile, demo gün ile uzatılır. Demo toplamı 30 günü aşamaz.
    """
    from .models import SozlesmeUzatma

    if sozlesme.durum != Sozlesme.Durum.AKTIF:
        raise ValueError("İptal edilmiş sözleşme uzatılamaz.")

    if sozlesme.is_demo:
        if not ek_gun or int(ek_gun) <= 0:
            raise ValueError("Demo sözleşme için ek gün gereklidir.")
        ek_gun = int(ek_gun)
        if sozlesme.toplam_gun + ek_gun > Sozlesme.DEMO_MAKS_GUN:
            raise ValueError(
                f"Demo sözleşme toplamı {Sozlesme.DEMO_MAKS_GUN} günü aşamaz."
            )
        ek_ay = None
    else:
        if not ek_ay or int(ek_ay) <= 0:
            raise ValueError("Standart sözleşme için ek ay gereklidir.")
        ek_ay = int(ek_ay)
        ek_gun = None

    with UnitOfWork(user=user) as uow:
        uow.add(SozlesmeUzatma(
            sozlesme=sozlesme, ek_ay=ek_ay, ek_gun=ek_gun, neden=neden,
        ))
        if sozlesme.is_demo:
            sozlesme.ek_gun_toplam = int(sozlesme.ek_gun_toplam) + ek_gun
            fields = ["ek_gun_toplam"]
        else:
            sozlesme.ek_ay_toplam = int(sozlesme.ek_ay_toplam) + ek_ay
            fields = ["ek_ay_toplam"]
        # Uzatma bitiş tarihini ileri taşır; süresi dolmuş sözleşme yeniden geçerli olur
        # (durum zaten AKTIF; "tamamlandı" ayrı bir durum değil, türetilir).
        uow.update(sozlesme, update_fields=fields)
    return sozlesme


# ── Panel kısıtı (erişim) ────────────────────────────────────────────────────

def panel_kisitli(eczane_id: int) -> tuple[bool, str]:
    """Eczacı panelinin kısıtlı olup olmadığını döner: (kisitli, neden).

    Kısıt nedenleri: SOZLESME_YOK (aktif sözleşme yok) | ODEME_GECIKTI | "".
    Kısıtlıyken eczacı yalnızca Hesabım ve Ödemeler bölümünü kullanabilir.
    """
    if not eczane_id:
        return True, "SOZLESME_YOK"
    sozlesme = eczane_aktif_sozlesme(eczane_id)
    if sozlesme is None:
        return True, "SOZLESME_YOK"
    # Dijital imzalı sözleşmede eczacı onayı alınmadan panel açılmaz.
    if sozlesme.onay_gerekli:
        return True, "SOZLESME_ONAYSIZ"
    if eczane_erisim_kapali(eczane_id):
        return True, "ODEME_GECIKTI"
    return False, ""


# ── Sözleşme talepleri ───────────────────────────────────────────────────────

def karar_ver_talep(talep, *, onayla: bool, red_nedeni: str = "", user=None, detail_data: dict | None = None):
    """Sözleşme talebini onaylar (uygular) veya reddeder.

    Onay: YENI→yeni Sozlesme, UZATMA→uzat_sozlesme, IPTAL→hedef durum IPTAL.
    """
    from .models import Sozlesme, SozlesmeTalebi

    if talep.durum != SozlesmeTalebi.Durum.BEKLIYOR:
        raise ValueError("Yalnızca bekleyen talep sonuçlandırılabilir.")

    data = detail_data or {}
    if data.get("istenen_tur"):
        talep.istenen_tur = data["istenen_tur"]
    if data.get("istenen_tip_ay") is not None:
        talep.istenen_tip_ay = data["istenen_tip_ay"]
    if data.get("istenen_demo_gun") is not None:
        talep.istenen_demo_gun = data["istenen_demo_gun"]
    if data.get("ek_ay") is not None:
        talep.ek_ay = data["ek_ay"]
    if data.get("ek_gun") is not None:
        talep.ek_gun = data["ek_gun"]
    if data.get("aciklama") is not None:
        talep.aciklama = data["aciklama"]

    now = timezone.now()
    if not onayla:
        with UnitOfWork(user=user) as uow:
            talep.durum = SozlesmeTalebi.Durum.REDDEDILDI
            talep.red_nedeni = red_nedeni or (data.get("red_nedeni") or "")
            talep.karar_veren = user
            talep.karar_tarihi = now
            uow.update(talep, update_fields=["durum", "red_nedeni", "karar_veren", "karar_tarihi", "aciklama", "istenen_tur", "istenen_tip_ay", "istenen_demo_gun", "ek_ay", "ek_gun"])
        return talep

    with UnitOfWork(user=user) as uow:
        olusan = None
        if talep.talep_tipi == SozlesmeTalebi.Tip.YENI:
            olusan = _talepten_sozlesme_olustur(uow, talep, user, data)
        elif talep.talep_tipi == SozlesmeTalebi.Tip.UZATMA:
            if talep.hedef_sozlesme is None:
                raise ValueError("Uzatma talebinde hedef sözleşme yok.")
            uzat_sozlesme(
                talep.hedef_sozlesme, ek_ay=talep.ek_ay, ek_gun=talep.ek_gun,
                neden=talep.aciklama or "Eczacı talebi", user=user,
            )
        elif talep.talep_tipi == SozlesmeTalebi.Tip.IPTAL:
            if talep.hedef_sozlesme is None:
                raise ValueError("İptal talebinde hedef sözleşme yok.")
            iptal_sozlesme(
                talep.hedef_sozlesme,
                neden=talep.aciklama or "Eczacı iptal talebi",
                user=user,
            )

        talep.durum = SozlesmeTalebi.Durum.ONAYLANDI
        talep.karar_veren = user
        talep.karar_tarihi = now
        talep.olusan_sozlesme = olusan
        uow.update(talep, update_fields=["durum", "karar_veren", "karar_tarihi", "olusan_sozlesme", "aciklama", "istenen_tur", "istenen_tip_ay", "istenen_demo_gun", "ek_ay", "ek_gun"])
    return talep


def _talepten_sozlesme_olustur(uow, talep, user, data=None):
    """Onaylanan YENI talepten sözleşme oluşturur.

    `data` admin tarafından onay modalında girilen sözleşme detaylarını içerir
    (başlangıç, öteleme, bedeller, cihaz durumu/planı). Eksik alanlar talebin
    istenen değerlerinden veya aktif fiyat tanımından tamamlanır.
    """
    from .serializers import SozlesmeSerializer

    data = data or {}
    payload = {
        "eczane": talep.eczane_id,
        "tur": data.get("istenen_tur") or talep.istenen_tur or Sozlesme.Tur.STANDART,
        "sozlesme_tipi_ay": data.get("istenen_tip_ay") or talep.istenen_tip_ay or 24,
        "demo_gun": data.get("istenen_demo_gun") or talep.istenen_demo_gun or 30,
        "baslangic_tarihi": data.get("baslangic_tarihi") or timezone.localdate(),
        "cihaz_durumu": data.get("cihaz_durumu") or Sozlesme.CihazDurum.TAHSIS,
        "oteleme_ay": data.get("oteleme_ay") or 0,
        "notlar": data.get("notlar") or "",
    }
    for field in ("aylik_kullanim_bedeli", "kdv_orani", "tevkifat_orani", "iptal_ceza_orani"):
        if data.get(field) not in (None, ""):
            payload[field] = data[field]
    planlar = data.get("cihaz_planlari") or []
    if not planlar and payload["cihaz_durumu"] == Sozlesme.CihazDurum.SATILIK and data.get("pesin_fiyat"):
        planlar = [{
            "tip": CihazOdemePlani.Tip.SATILIK, "pesin_fiyat": data["pesin_fiyat"],
            "vade_farki_orani": data.get("vade_farki_orani") or "0.00",
            "taksit_sayisi": data.get("taksit_sayisi") or 1,
        }]
    serializer = SozlesmeSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    return sozlesme_olustur(serializer.validated_data, planlar=planlar, user=user)

def sozlesme_hareketleri(eczane_id: int) -> list[dict]:
    """Eczanenin sözleşme hareketleri: sözleşmeler, uzatmalar, talepler, ödemeler (tarih sıralı)."""
    from .models import Fatura, FaturaIslem, Odeme, Sozlesme, SozlesmeTalebi, SozlesmeUzatma

    olaylar: list[dict] = []
    for s in Sozlesme.objects.filter(eczane_id=eczane_id):
        etiket = "Demo sözleşme" if s.is_demo else f"{s.get_sozlesme_tipi_ay_display()} sözleşme"
        olaylar.append({
            "tip": "SOZLESME", "tarih": s.olusturulma_tarihi,
            "baslik": f"{etiket} oluşturuldu",
            "detay": f"Bitiş: {s.bitis_tarihi}",
        })
    for u in SozlesmeUzatma.objects.filter(sozlesme__eczane_id=eczane_id):
        birim = f"{u.ek_gun} gün" if u.ek_gun else f"{u.ek_ay} ay"
        olaylar.append({
            "tip": "UZATMA", "tarih": u.olusturulma_tarihi,
            "baslik": f"Sözleşme uzatıldı (+{birim})", "detay": u.neden or "",
        })
    for t in SozlesmeTalebi.objects.filter(eczane_id=eczane_id):
        olaylar.append({
            "tip": "TALEP", "tarih": t.olusturulma_tarihi,
            "baslik": f"{t.get_talep_tipi_display()} talebi — {t.get_durum_display()}",
            "detay": t.red_nedeni or t.aciklama or "",
        })
    for o in Odeme.objects.filter(fatura__eczane_id=eczane_id).select_related("fatura"):
        olaylar.append({
            "tip": "ODEME", "tarih": o.odeme_tarihi,
            "baslik": f"Ödeme alındı ({o.get_yontem_display()})",
            "detay": f"{o.tutar} TL — {o.fatura.donem}",
        })
    for islem in FaturaIslem.objects.filter(fatura__eczane_id=eczane_id):
        olaylar.append({
            "tip": "FATURA", "tarih": islem.olusturulma_tarihi,
            "baslik": f"Fatura #{islem.fatura_id}: {islem.get_islem_display()}",
            "detay": islem.neden,
        })
    olaylar.sort(key=lambda x: x["tarih"] or timezone.now(), reverse=True)
    return olaylar


# ── Yardımcılar ──────────────────────────────────────────────────────────────

def _son_gun_ay(d: _dt.date) -> _dt.date:
    """Verilen tarihin bulunduğu ayın son gününü döner."""
    last_day = calendar.monthrange(d.year, d.month)[1]
    return _dt.date(d.year, d.month, last_day)


def _vade_sozlesme_gun(baslangic_gun: int, donem_ay: _dt.date) -> _dt.date:
    """Sözleşme başlangıç gününü donem_ay ayında döner (ay sonu güvenli)."""
    last = calendar.monthrange(donem_ay.year, donem_ay.month)[1]
    return _dt.date(donem_ay.year, donem_ay.month, min(baslangic_gun, last))


def _fatura_var(eczane_id: int, tip: str, donem: str, taksit_no: int | None) -> bool:
    return Fatura.objects.filter(
        eczane_id=eczane_id, tip=tip, donem=donem, taksit_no=taksit_no
    ).exists()


def _vade_ay_ici(bugun: _dt.date, *, gun: int) -> _dt.date:
    """İçinde bulunulan ayın `gun`. gününü vade olarak döner (ay sonu güvenli)."""
    last_day = calendar.monthrange(bugun.year, bugun.month)[1]
    return _dt.date(bugun.year, bugun.month, min(gun, last_day))


def _tamamla_plan(plan: CihazOdemePlani) -> None:
    if plan.durum != CihazOdemePlani.Durum.TAMAMLANDI:
        with UnitOfWork() as uow:
            plan.durum = CihazOdemePlani.Durum.TAMAMLANDI
            uow.update(plan, update_fields=["durum"])
