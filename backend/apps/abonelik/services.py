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

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.uow import UnitOfWork

from .models import CihazOdemePlani, Fatura, FiyatTanimi, Odeme, Sozlesme

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


# ── Fiyat tanımı (parametre) ─────────────────────────────────────────────────

def aktif_fiyat(*, bugun: _dt.date | None = None) -> FiyatTanimi | None:
    """Verilen tarihte geçerli en güncel fiyat tanımını döner (yoksa None)."""
    bugun = bugun or timezone.localdate()
    return (
        FiyatTanimi.objects.filter(gecerlilik_baslangic__lte=bugun)
        .order_by("-gecerlilik_baslangic", "-id")
        .first()
    )


# ── Kullanım bedeli faturalandırma ──────────────────────────────────────────

def faturala_kullanim_bedeli(*, bugun: _dt.date | None = None) -> int:
    """Aktif sözleşmeler için içinde bulunulan dönemin kullanım bedeli faturasını üretir.

    Öteleme (grace) dönemi ve sözleşme bitişi kontrol edilir. İdempotenttir:
    aynı eczane + dönem için ikinci fatura oluşmaz.

    Dönüş: oluşturulan fatura sayısı.
    """
    bugun = bugun or timezone.localdate()
    donem = donem_str(bugun)
    olusturulan = 0

    # Demo sözleşmelerde kullanım bedeli faturalanmaz.
    sozlesmeler = Sozlesme.objects.filter(
        durum=Sozlesme.Durum.AKTIF, tur=Sozlesme.Tur.STANDART
    ).select_related("eczane")
    for sozlesme in sozlesmeler:
        baslangic = sozlesme.kullanim_bedeli_baslangic
        bitis = sozlesme.bitis_tarihi
        # Öteleme dönemi bitmeden veya sözleşme sona erdikten sonra fatura kesilmez.
        if bugun < baslangic or bugun > bitis:
            continue
        if _fatura_var(sozlesme.eczane_id, Fatura.Tip.KULLANIM_BEDELI, donem, None):
            continue

        vade = _vade_ay_ici(bugun, gun=CIHAZ_TAKSIT_SON_GUN)
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
    donem = donem_str(bugun)
    olusturulan = 0

    sozlesmeler = Sozlesme.objects.filter(
        durum=Sozlesme.Durum.AKTIF,
        tur=Sozlesme.Tur.STANDART,
        cihaz_durumu=Sozlesme.CihazDurum.KIRALIK,
    ).select_related("eczane")
    for sozlesme in sozlesmeler:
        if not sozlesme.cihaz_kira_bedeli or sozlesme.cihaz_kira_bedeli <= 0:
            continue
        if bugun < sozlesme.baslangic_tarihi or bugun > sozlesme.bitis_tarihi:
            continue
        if _fatura_var(sozlesme.eczane_id, Fatura.Tip.CIHAZ_KIRA, donem, None):
            continue

        vade = _vade_ay_ici(bugun, gun=CIHAZ_TAKSIT_SON_GUN)
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
def ode_fatura(fatura: Fatura, *, yontem: str = Odeme.Yontem.KREDI_KARTI, user=None) -> Odeme:
    """Faturaya karşılık tahsilat kaydı oluşturur ve faturayı ÖDENDI yapar.

    Mock tahsilat: gerçek ödeme ağ geçidi çağrısı yapılmaz.
    """
    if fatura.durum == Fatura.Durum.ODENDI:
        raise ValueError("Fatura zaten ödenmiş.")
    if fatura.durum == Fatura.Durum.IPTAL:
        raise ValueError("İptal edilmiş fatura ödenemez.")

    now = timezone.now()
    with UnitOfWork(user=user) as uow:
        odeme = Odeme(fatura=fatura, tutar=fatura.tutar, yontem=yontem, odeme_tarihi=now)
        uow.add(odeme)
        fatura.durum = Fatura.Durum.ODENDI
        fatura.odenme_tarihi = now
        uow.update(fatura, update_fields=["durum", "odenme_tarihi"])
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
    if eczane_aktif_sozlesme(eczane_id) is None:
        return True, "SOZLESME_YOK"
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
    from .models import CihazOdemePlani, Sozlesme

    data = data or {}
    bugun = timezone.localdate()
    baslangic = data.get("baslangic_tarihi") or bugun
    fiyat = aktif_fiyat(bugun=baslangic)

    tur = data.get("istenen_tur") or talep.istenen_tur or Sozlesme.Tur.STANDART
    cihaz_durumu = data.get("cihaz_durumu") or Sozlesme.CihazDurum.SATILIK
    kira = data.get("cihaz_kira_bedeli")
    if kira in (None, ""):
        kira = (fiyat.cihaz_kira_bedeli if fiyat else Decimal("0.00"))
    if cihaz_durumu != Sozlesme.CihazDurum.KIRALIK:
        kira = Decimal("0.00")

    ortak = dict(
        eczane_id=talep.eczane_id,
        baslangic_tarihi=baslangic,
        durum=Sozlesme.Durum.AKTIF,
        cihaz_durumu=cihaz_durumu,
        cihaz_kira_bedeli=kira,
        notlar=data.get("notlar", "") or "",
    )

    if tur == Sozlesme.Tur.DEMO:
        s = Sozlesme(
            tur=Sozlesme.Tur.DEMO,
            demo_gun=data.get("istenen_demo_gun") or talep.istenen_demo_gun or 30,
            **ortak,
        )
    else:
        aylik = data.get("aylik_kullanim_bedeli")
        if aylik in (None, ""):
            aylik = (fiyat.abonelik_bedeli if fiyat else Decimal("3900.00"))
        s = Sozlesme(
            tur=Sozlesme.Tur.STANDART,
            sozlesme_tipi_ay=data.get("istenen_tip_ay") or talep.istenen_tip_ay or 24,
            oteleme_ay=int(data.get("oteleme_ay") or 0),
            aylik_kullanim_bedeli=aylik,
            **ortak,
        )
    uow.add(s)

    # Satılık cihaz için ödeme planı (peşin fiyat girilmişse).
    pesin = data.get("pesin_fiyat")
    if (
        tur != Sozlesme.Tur.DEMO
        and cihaz_durumu == Sozlesme.CihazDurum.SATILIK
        and pesin not in (None, "")
        and Decimal(str(pesin)) > 0
    ):
        uow.add(CihazOdemePlani(
            sozlesme=s,
            pesin_fiyat=Decimal(str(pesin)),
            vade_farki_orani=Decimal(str(data.get("vade_farki_orani") or "0.00")),
            taksit_sayisi=int(data.get("taksit_sayisi") or 1),
            baslangic_tarihi=data.get("cihaz_baslangic_tarihi") or baslangic,
        ))
    return s


def sozlesme_hareketleri(eczane_id: int) -> list[dict]:
    """Eczanenin sözleşme hareketleri: sözleşmeler, uzatmalar, talepler, ödemeler (tarih sıralı)."""
    from .models import Fatura, Odeme, Sozlesme, SozlesmeTalebi, SozlesmeUzatma

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
    olaylar.sort(key=lambda x: x["tarih"] or timezone.now(), reverse=True)
    return olaylar


# ── Yardımcılar ──────────────────────────────────────────────────────────────

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
