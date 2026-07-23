"""A->B ardisilik application service.

Tum follows iliskisi yazma/guncelleme islemleri bu servis uzerinden yapilir.
Serializer ve ORM dogrudan yazma noktalari bu servisi kullanmalidir.

Dogrulamalar (transaction icinde, select_for_update ile):
  1. Self-link yasak (A kendini takip edemez)
  2. Hedef kampanyanin zinciri olmamali: maksimum ikili (A->B)
  3. Dongu yasak: B A'yi takip ediyorsa A B'yi takip edemez
  4. Unique predecessor DB constraint
  5. Tarih araligı kesisimi: A ve B tarih araligları ortussmeli
  6. Yayın saati kesisimi: A ve B active_hours (DeliveryRule) ortussmeli (varsa)
  7. Pause/cancel: CANCELLED kampanya ardisilik kuramaz

Concurrency korumasi:
  - select_for_update(nowait=False) ile her iki kampanya lock'lanir.
  - Iki esszamanli istek ayni predecessor'u almaya calisirsa birincisi
    transaction'i commit edince ikincisi DB unique constraint'ten IntegrityError alir.

SQLite notu:
  SQLite WAL modunda select_for_update + thread concurrency test guvenilir degil.
  Gercek concurrency testi PostgreSQL gerektirmektedir. Bu fazdaki testler yalniz
  sekansiyel mantiksal dogrulamayi kapsar.
"""
from __future__ import annotations

from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError

from apps.campaigns.models import Campaign


class FollowsConstraintError(ValidationError):
    """A->B iliskisi kurarken olusan is mantigi hatasi."""
    pass


def _dates_overlap(a: Campaign, b: Campaign) -> bool:
    """Iki kampanyanin tarih araligları ortusuyor mu?"""
    return a.start_date <= b.end_date and b.start_date <= a.end_date


def _hours_overlap(rule_a, rule_b) -> bool:
    """Iki DeliveryRule active_hours kesisiyor mu?

    None = tum gun; iki null veya biri null digerini kapsar: True.
    Hicbir ortak saat yoksa: False.
    """
    if rule_a is None or rule_b is None:
        return True
    hours_a = getattr(rule_a, "active_hours", None)
    hours_b = getattr(rule_b, "active_hours", None)
    if hours_a is None or hours_b is None:
        return True
    return bool(set(hours_a) & set(hours_b))


def _targets_overlap(a: Campaign, b: Campaign) -> bool:
    """Iki kampanyanin hedef kiosk setleri kesisiyor mu?

    target_scope=ALL: tum kiosklar hedeflenir → her zaman kesisim var.
    target_scope=RULES: CampaignTarget INCLUDE/EXCLUDE kayitlari resolve edilir.
    target_scope=None (legacy): ALL gibi davranir.

    RULES targeting semantigi:
      1. INCLUDE target'lari toplanir (union)
      2. EXCLUDE target'lari cikarilir (set difference)
      3. Efektif hedef kumesi bos degilse kesisim kontrol edilir

    Kesisim yoksa False (A ve B ortak hic bir kioska ulasamiyor).
    """
    from apps.campaigns.models import CampaignTarget
    from apps.pharmacies.models import Kiosk

    # İkisi de RULES → CampaignTarget kayitlarini resolve et
    _ALL_SCOPE = object()  # Sentinel: "tüm kiosklar" - DB sorgusu gerektirmez

    def resolve_kiosk_ids(campaign):
        """Campaign'in INCLUDE/EXCLUDE targeting ile hedefledigi kiosk ID setini dondur.

        Mantik:
          1. INCLUDE tipindeki tum target'lari genislet (il → eczaneler → kiosklar)
          2. EXCLUDE tipindeki tum target'lari genislet
          3. included - excluded → efektif hedef kumesi

        target_scope=ALL veya None → _ALL_SCOPE sentinel doner (DB sorgusu yapmadan).
        Bu sekilde test ortaminda kiosk yokken de dogru davranir.
        """
        from apps.pharmacies.models import Eczane

        # target_scope=ALL veya NULL → tüm kioskları hedefler (sentinel)
        if campaign.target_scope in ("ALL", None):
            return _ALL_SCOPE

        # target_scope=RULES → resolve
        included = set()
        excluded = set()

        targets = list(
            CampaignTarget.objects
            .filter(campaign=campaign)
            .select_related("kiosk", "kiosk__eczane", "il", "ilce", "eczane")
        )

        for target in targets:
            mode = target.mode or "INCLUDE"  # NULL = legacy INCLUDE

            target_kiosk_ids = set()

            if target.target_type == CampaignTarget.TargetType.KIOSK:
                # Direkt kiosk
                if target.kiosk_id:
                    target_kiosk_ids.add(target.kiosk_id)

            elif target.target_type == CampaignTarget.TargetType.ECZANE:
                # Eczanedeki tum kiosklar
                if target.eczane_id:
                    target_kiosk_ids.update(
                        Kiosk.objects.filter(eczane_id=target.eczane_id).values_list("id", flat=True)
                    )

            elif target.target_type == CampaignTarget.TargetType.ILCE:
                # Ilcedeki tum eczanelerin tum kiosklari
                if target.ilce_id:
                    eczane_ids = Eczane.objects.filter(ilce_id=target.ilce_id).values_list("id", flat=True)
                    target_kiosk_ids.update(
                        Kiosk.objects.filter(eczane_id__in=eczane_ids).values_list("id", flat=True)
                    )

            elif target.target_type == CampaignTarget.TargetType.IL:
                # Ildeki tum eczanelerin tum kiosklari
                if target.il_id:
                    eczane_ids = Eczane.objects.filter(il_id=target.il_id).values_list("id", flat=True)
                    target_kiosk_ids.update(
                        Kiosk.objects.filter(eczane_id__in=eczane_ids).values_list("id", flat=True)
                    )

            # INCLUDE vs EXCLUDE
            if mode == "INCLUDE":
                included.update(target_kiosk_ids)
            elif mode == "EXCLUDE":
                excluded.update(target_kiosk_ids)

        # Efektif hedef kumesi: included - excluded
        effective = included - excluded
        return effective

    a_kiosks = resolve_kiosk_ids(a)
    b_kiosks = resolve_kiosk_ids(b)

    # Sentinel mantığı: _ALL_SCOPE "tüm kiosklar" demek
    if a_kiosks is _ALL_SCOPE and b_kiosks is _ALL_SCOPE:
        # Her ikisi de tüm kiosklara yayın yapıyor → her zaman kesişim var
        return True
    if a_kiosks is _ALL_SCOPE:
        # A tüm kioskları, B belirli kiosklara yayın yapıyor
        # B'nin efektif hedef kumesi boş değilse kesişim var
        return bool(b_kiosks)
    if b_kiosks is _ALL_SCOPE:
        return bool(a_kiosks)

    # İkisi de RULES scope: efektif hedef kumesi bos mu kontrolu
    if not a_kiosks or not b_kiosks:
        return False

    # Kesisim var mi?
    return bool(a_kiosks & b_kiosks)


def set_campaign_follows(
    campaign_id: str,
    follows_id: str | None,
) -> Campaign:
    """campaign_id kampanyasinin follows alanini ayarlar.

    follows_id=None: iliskiyi kaldirir.
    Dogrulama basarisiz olursa FollowsConstraintError firlatir.
    Unique predecessor constraint ihlalinde IntegrityError firlatir.
    """
    if follows_id is not None and str(campaign_id) == str(follows_id):
        raise FollowsConstraintError(
            {"follows": "Kampanya kendini takip edemez (self-link yasak)."}
        )

    with transaction.atomic():
        campaign = (
            Campaign.objects
            .select_for_update(nowait=False)
            .get(pk=campaign_id)
        )

        if follows_id is None:
            campaign.follows = None
            campaign.save(update_fields=["follows"])
            return campaign

        follows_campaign = (
            Campaign.objects
            .select_for_update(nowait=False)
            .get(pk=follows_id)
        )

        # Dongu kontrolu
        if follows_campaign.follows_id is not None:
            if str(follows_campaign.follows_id) == str(campaign_id):
                raise FollowsConstraintError(
                    {"follows": (
                        f"Dongu tespit edildi: '{follows_campaign.name}' zaten "
                        f"'{campaign.name}' kampanyasini takip ediyor."
                    )}
                )
            raise FollowsConstraintError(
                {"follows": (
                    f"Zincir derinligi: '{follows_campaign.name}' zaten baska bir "
                    f"kampanyayi takip ediyor. Yalniz ikili (A->B) iliskiye izin verilir."
                )}
            )

        # Tarih araligı kesisimi
        if not _dates_overlap(campaign, follows_campaign):
            raise FollowsConstraintError(
                {"follows": (
                    f"Tarih araligı kesismesi yok: "
                    f"'{campaign.name}' ({campaign.start_date.date()}--{campaign.end_date.date()}) "
                    f"ile '{follows_campaign.name}' "
                    f"({follows_campaign.start_date.date()}--{follows_campaign.end_date.date()}) "
                    f"tarih araligları ortusmuyor."
                )}
            )

        # Yayın saati kesisimi (DeliveryRule varsa)
        try:
            rule_a = campaign.delivery_rule
        except Exception:
            rule_a = None
        try:
            rule_b = follows_campaign.delivery_rule
        except Exception:
            rule_b = None

        if not _hours_overlap(rule_a, rule_b):
            raise FollowsConstraintError(
                {"follows": (
                    "Yayın saati kesismesi yok: Kampanyalarin active_hours aralikları "
                    "ortusmuyor. Kampanyalar ortak en az bir saat paylasmalidir."
                )}
            )

        # Hedef kiosk kesisimi (target_scope)
        if not _targets_overlap(campaign, follows_campaign):
            raise FollowsConstraintError(
                {"follows": (
                    "Hedef kesismesi yok: Kampanyalar ortak kiosk paylasmiyor. "
                    "A->B iliskisi kurulabilmesi icin her iki kampanya en az bir "
                    "ortak kiosk'a ulasmalidir."
                )}
            )

        # Pause/cancel kontrolu
        if campaign.status in (Campaign.Status.CANCELLED,):
            raise FollowsConstraintError(
                {"follows": "Iptal edilmis kampanya icin ardisilik iliskisi kurulamaz."}
            )
        if follows_campaign.status in (Campaign.Status.CANCELLED,):
            raise FollowsConstraintError(
                {"follows": f"'{follows_campaign.name}' iptal edilmis; ardisilik iliskisi kurulamaz."}
            )

        # Unique predecessor kontrolu (DB constraint'ten önce açık hata ver)
        existing_follower = (
            Campaign.objects
            .filter(follows=follows_campaign)
            .exclude(pk=campaign_id)
            .first()
        )
        if existing_follower is not None:
            raise FollowsConstraintError(
                {"follows": (
                    f"'{follows_campaign.name}' kampanyasi zaten "
                    f"'{existing_follower.name}' tarafindan takip ediliyor. "
                    f"Bir kampanyanin yalnizca bir dogrudan ardili olabilir."
                )}
            )

        campaign.follows = follows_campaign
        try:
            campaign.save(update_fields=["follows"])
        except IntegrityError as exc:
            raise FollowsConstraintError(
                {"follows": (
                    f"'{follows_campaign.name}' kampanyasi zaten baska bir kampanya "
                    f"tarafindan takip ediliyor (unique predecessor ihlali)."
                )}
            ) from exc

    return campaign


def clear_campaign_follows(campaign_id: str) -> Campaign:
    """campaign_id kampanyasinin follows iliskisini kaldirir."""
    return set_campaign_follows(campaign_id, follows_id=None)
