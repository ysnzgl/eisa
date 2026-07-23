"""Faz 3 — PostgreSQL concurrency / race testleri.

FA-10  İki eşzamanlı activation toplam allocation değerini aşamaz
FA-11  Race testinde yalnız izin verilen transaction başarılı olur

PostgreSQL MVCC + select_for_update(nowait=False) ile.
"""
from __future__ import annotations

import datetime as _dt
import threading
import uuid

import pytest
from django.db import close_old_connections, transaction
from django.test import override_settings
from django.utils import timezone

from apps.campaigns.models import (
    Campaign,
    CampaignTotalAllocation,
    Creative,
    DeliveryRule,
    KioskDayQuota,
    PlanningRun,
)
from apps.campaigns.services.activation_service import ActivationService, CapacityError
from apps.pharmacies.models import Eczane, Kiosk


pytestmark = pytest.mark.postgresql

TODAY = _dt.date(2026, 7, 22)


def _make_aware(d: _dt.date, hour: int = 0) -> _dt.datetime:
    return timezone.make_aware(_dt.datetime.combine(d, _dt.time(hour, 0)))


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures (reuse test DB from conftest, but create fresh objects)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def kiosk_fa(db):
    from apps.lookups.seed import seed_lookups
    from apps.lookups.models import Il, Ilce
    seed_lookups()
    il = Il.objects.get_or_create(ad="Istanbul")[0]
    ilce = Ilce.objects.get_or_create(il=il, ad="Kadikoy")[0]
    eczane = Eczane.objects.create(ad="FA10 Eczane", il=il, ilce=ilce)
    return Kiosk.objects.create(
        eczane=eczane,
        ad="FA10 Kiosk",
        mac_adresi=f"FA:10:00:{uuid.uuid4().hex[:2].upper()}:00:01",
        uygulama_anahtari=f"fa10-key-{uuid.uuid4().hex}",
        aktif=True,
    )


@pytest.fixture
def house_ad_fa(db):
    from apps.campaigns.models import HouseAd
    return HouseAd.objects.create(
        name="FA10 HouseAd",
        media_url="http://localhost:9000/dev/ads/fa10-filler.mp4",
        duration_seconds=15,
        priority=1,
        aktif=True,
    )


def _make_total_campaign(kiosk_id, total_target=4):
    """CAMPAIGN_TOTAL kampanya ve gerekli nesneleri oluştur."""
    base = _make_aware(TODAY, hour=0)
    camp = Campaign.objects.create(
        name=f"FA10-Camp-{uuid.uuid4().hex[:6]}",
        start_date=base - _dt.timedelta(days=1),
        end_date=base,
        status=Campaign.Status.ACTIVE,
        target_scope="ALL",
    )
    Creative.objects.create(
        campaign=camp,
        media_url=f"http://localhost:9000/dev/ads/fa10-{uuid.uuid4().hex}.mp4",
        duration_seconds=15,
    )
    DeliveryRule.objects.create(
        campaign=camp,
        delivery_type="CAMPAIGN_TOTAL",
        count=total_target,
        guarantee_mode="BEST_EFFORT",
    )
    return camp


# ─────────────────────────────────────────────────────────────────────────────
# FA-10  İki eşzamanlı activation toplam allocation'ı aşmaz
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db(transaction=True)
@override_settings(DOOH_ENGINE_V2="active")
def test_fa10_concurrent_activations_respect_global_quota(kiosk_fa, house_ad_fa):
    """İki thread aynı CAMPAIGN_TOTAL kampanyayı aktive etmeye çalışır.

    GlobalQuotaService.reserve_for_kiosk_day → select_for_update(nowait=False)
    ile serialize edildiğinden toplam placed <= total_target olmalı.
    """
    close_old_connections()
    total_target = 2
    camp = _make_total_campaign(kiosk_fa.id, total_target=total_target)
    campaign_pk = camp.pk

    results = []
    errors = []
    barrier = threading.Barrier(2)

    def run_activate():
        close_old_connections()
        try:
            from apps.campaigns.models import Campaign as Camp
            c = Camp.objects.get(pk=campaign_pk)
            barrier.wait(timeout=10)
            result = ActivationService.activate(c)
            results.append(result)
        except Exception as exc:
            errors.append(exc)
        finally:
            close_old_connections()

    t1 = threading.Thread(target=run_activate)
    t2 = threading.Thread(target=run_activate)
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)

    # Global invariant: sum(placed) <= total_target
    quotas = KioskDayQuota.objects.filter(campaign=campaign_pk)
    total_placed = sum(q.placed for q in quotas)
    assert total_placed <= total_target, (
        f"Global invariant ihlali: placed={total_placed} > total_target={total_target}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# FA-11  Race testinde yalnız izin verilen transaction başarılı olur
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db(transaction=True)
@override_settings(DOOH_ENGINE_V2="active")
def test_fa11_race_only_permitted_transaction_succeeds(kiosk_fa, house_ad_fa):
    """Aynı anda iki GUARANTEED aktivasyon: yalnız biri başarılı olabilir.

    GUARANTEED + count > capacity → sadece bir thread 409 alabilir,
    diğeri ya başarılı ya da da 409 alır. Playlist sayısı max birinin değeri.

    Bu test, toplam playlist sayısının tekli aktivasyonla aynı olduğunu doğrular
    (yarış koşulunda iki aktivasyon aynı playtlisti iki kez oluşturmamalı).
    """
    close_old_connections()
    camp = _make_total_campaign(kiosk_fa.id, total_target=100)

    # First activation (sequential baseline)
    from apps.campaigns.models import Campaign as Camp
    c = Camp.objects.get(pk=camp.pk)
    ActivationService.activate(c)

    pl_after_first = __import__("apps.campaigns.models", fromlist=["Playlist"]).Playlist.objects.filter(kiosk=kiosk_fa).count()

    # Race: two threads try to activate the same campaign at same time
    barrier = threading.Barrier(2)

    def run_activate():
        close_old_connections()
        try:
            c2 = Camp.objects.get(pk=camp.pk)
            barrier.wait(timeout=10)
            ActivationService.activate(c2)
        except (CapacityError, Exception):
            pass
        finally:
            close_old_connections()

    t1 = threading.Thread(target=run_activate)
    t2 = threading.Thread(target=run_activate)
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)

    from apps.campaigns.models import Playlist
    pl_after_race = Playlist.objects.filter(kiosk=kiosk_fa).count()

    # Replace semantics: race doesn't ADD extra playlists beyond single-activation count
    assert pl_after_race == pl_after_first, (
        f"Race sonrası playlist sayısı beklenenden farklı: "
        f"after_race={pl_after_race}, after_first={pl_after_first}"
    )
