"""
PostgreSQL Integration Tests — Concurrency & MVCC

Bu testler gerçek PostgreSQL üzerinde:
- select_for_update() row-level locking
- A→B follows unique predecessor race condition
- A→B / B→A concurrent cycle prevention
- KioskDayQuota placed<=quota concurrency
- Global CAMPAIGN_TOTAL quota invariant
- A→B target intersection validation

SQLite'da bu testler simüle edilemez (select_for_update gerçek lock yapmaz).

Çalıştırma:
    docker-compose -f docker-compose.test-pg.yml up -d
    pytest apps/campaigns/tests/integration/ -m postgresql --ds=core_api.test_settings_pg -v

NOT: Testler PostgreSQL connection'ı zorunlu kılar. SQLite üzerinde skip edilir.
"""
import threading
import time
import uuid
from django.db import connection, transaction, close_old_connections
from django.utils import timezone
import pytest

from apps.campaigns.models import (
    Campaign,
    DeliveryRule,
    PlanningRun,
    KioskDayQuota,
)
from apps.campaigns.services.follows_service import (
    set_campaign_follows,
    FollowsConstraintError,
)


pytestmark = pytest.mark.postgresql


def _assert_postgresql():
    """PostgreSQL connection zorunluluğunu assert et. SQLite ise testi skip et."""
    vendor = connection.vendor
    if vendor != 'postgresql':
        pytest.skip(
            f"Bu test PostgreSQL gerektirir. Mevcut DB vendor: {vendor}. "
            "Önce docker-compose -f docker-compose.test-pg.yml up -d yapın ve "
            "--ds=core_api.test_settings_pg kullanın."
        )


@pytest.mark.django_db(transaction=True)
class TestFollowsConcurrency:
    """A→B follows unique predecessor concurrency testleri."""

    def test_concurrent_follows_same_predecessor_race(
        self, django_db_setup, django_db_blocker, kiosk
    ):
        """
        İki thread aynı predecessor'ı seçmeye çalışır.
        Beklenti: Biri başarılı, diğeri IntegrityError veya FollowsConstraintError.
        
        SQLite'da bu test geçer ama gerçek concurrency koruması yok.
        PostgreSQL'de gerçek MVCC race condition testi.
        
        NOT: kiosk fixture gerekli (ALL target_scope için hiç kiosk yoksa kesişim olmaz)
        """
        _assert_postgresql()
        
        # Üç kampanya: A (predecessor), B, C (iki yarışan)
        campaign_a = Campaign.objects.create(
            name="Campaign A (Predecessor)",
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timezone.timedelta(days=7)).date(),
            status="ACTIVE",
            target_scope="ALL",
        )
        campaign_b = Campaign.objects.create(
            name="Campaign B (Follower 1)",
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timezone.timedelta(days=7)).date(),
            status="ACTIVE",
            target_scope="ALL",
        )
        campaign_c = Campaign.objects.create(
            name="Campaign C (Follower 2)",
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timezone.timedelta(days=7)).date(),
            status="ACTIVE",
            target_scope="ALL",
        )

        results = {"b": None, "c": None}
        exceptions = {"b": None, "c": None}
        barrier = threading.Barrier(2)

        def set_follows_b():
            """Thread 1: B → A"""
            try:
                close_old_connections()
                barrier.wait()  # Eşzamanlı başlangıç
                with transaction.atomic():
                    result = set_campaign_follows(campaign_b.pk, campaign_a.pk)
                    results["b"] = result
            except Exception as e:
                exceptions["b"] = e
            finally:
                close_old_connections()

        def set_follows_c():
            """Thread 2: C → A (aynı predecessor)"""
            try:
                close_old_connections()
                barrier.wait()  # Eşzamanlı başlangıç
                with transaction.atomic():
                    result = set_campaign_follows(campaign_c.pk, campaign_a.pk)
                    results["c"] = result
            except Exception as e:
                exceptions["c"] = e
            finally:
                close_old_connections()

        thread_b = threading.Thread(target=set_follows_b)
        thread_c = threading.Thread(target=set_follows_c)

        thread_b.start()
        thread_c.start()
        thread_b.join(timeout=10)
        thread_c.join(timeout=10)

        # Assertion: Tam olarak biri başarılı, diğeri hata
        success_count = sum(1 for r in results.values() if r is not None)
        error_count = sum(1 for e in exceptions.values() if e is not None)

        assert success_count == 1, (
            f"Tam olarak bir thread başarılı olmalı. "
            f"results={results}, exceptions={exceptions}"
        )
        assert error_count == 1, (
            f"Tam olarak bir thread hata almalı (unique constraint). "
            f"results={results}, exceptions={exceptions}"
        )

        # Başarısız olan thread IntegrityError veya FollowsConstraintError almalı
        failed_exception = next(e for e in exceptions.values() if e is not None)
        assert (
            "unique" in str(failed_exception).lower()
            or "follows" in str(failed_exception).lower()
            or isinstance(failed_exception, FollowsConstraintError)
        ), f"Unexpected exception: {failed_exception}"
        
        # Final DB state: A'nın tam olarak bir ardılı var
        campaign_a.refresh_from_db()
        followers = Campaign.objects.filter(follows=campaign_a)
        assert followers.count() == 1, f"A'nın yalnız bir ardılı olmalı, bulundu: {followers.count()}"

    def test_concurrent_follows_cycle_prevention(self, kiosk):
        """
        İki thread eşzamanlı cycle oluşturmaya çalışır:
        T1: B → A
        T2: A → B
        
        Beklenti: İkisi birden commit edemez. Son durumda cycle yok.
        
        NOT: kiosk fixture gerekli (ALL target_scope için hiç kiosk yoksa kesişim olmaz)
        """
        _assert_postgresql()
        
        campaign_a = Campaign.objects.create(
            name="Campaign A",
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timezone.timedelta(days=7)).date(),
            status="ACTIVE",
            target_scope="ALL",
        )
        campaign_b = Campaign.objects.create(
            name="Campaign B",
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timezone.timedelta(days=7)).date(),
            status="ACTIVE",
            target_scope="ALL",
        )

        results = {"b_to_a": None, "a_to_b": None}
        exceptions = {"b_to_a": None, "a_to_b": None}
        barrier = threading.Barrier(2)

        def set_b_to_a():
            """Thread 1: B → A"""
            try:
                close_old_connections()
                barrier.wait()  # Eşzamanlı başlangıç
                with transaction.atomic():
                    result = set_campaign_follows(campaign_b.pk, campaign_a.pk)
                    results["b_to_a"] = result
            except Exception as e:
                exceptions["b_to_a"] = e
            finally:
                close_old_connections()

        def set_a_to_b():
            """Thread 2: A → B"""
            try:
                close_old_connections()
                barrier.wait()  # Eşzamanlı başlangıç
                with transaction.atomic():
                    result = set_campaign_follows(campaign_a.pk, campaign_b.pk)
                    results["a_to_b"] = result
            except Exception as e:
                exceptions["a_to_b"] = e
            finally:
                close_old_connections()

        thread_1 = threading.Thread(target=set_b_to_a)
        thread_2 = threading.Thread(target=set_a_to_b)

        thread_1.start()
        thread_2.start()
        thread_1.join(timeout=10)
        thread_2.join(timeout=10)

        # Assertion: En fazla biri başarılı (iki transaction birden commit edemez)
        success_count = sum(1 for r in results.values() if r is not None)
        assert success_count <= 1, (
            f"İki transaction da cycle oluşturamaz. "
            f"results={results}, exceptions={exceptions}"
        )

        # Final DB state: Cycle olmamalı
        campaign_a.refresh_from_db()
        campaign_b.refresh_from_db()
        
        if campaign_a.follows_id == campaign_b.pk:
            assert campaign_b.follows_id != campaign_a.pk, "Cycle detected: A→B→A"
        elif campaign_b.follows_id == campaign_a.pk:
            assert campaign_a.follows_id != campaign_b.pk, "Cycle detected: B→A→B"
        # Else: hiçbiri kurulamadı, bu da geçerli

    def test_concurrent_follows_different_predecessors_allowed(self, kiosk):
        """
        İki thread farklı predecessor seçer → her ikisi de başarılı.
        
        NOT: kiosk fixture gerekli (ALL target_scope için hiç kiosk yoksa kesişim olmaz)
        """
        _assert_postgresql()
        
        campaign_a = Campaign.objects.create(
            name="Campaign A",
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timezone.timedelta(days=7)).date(),
            status="ACTIVE",
            target_scope="ALL",
        )
        campaign_b = Campaign.objects.create(
            name="Campaign B",
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timezone.timedelta(days=7)).date(),
            status="ACTIVE",
            target_scope="ALL",
        )
        campaign_c = Campaign.objects.create(
            name="Campaign C",
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timezone.timedelta(days=7)).date(),
            status="ACTIVE",
            target_scope="ALL",
        )
        campaign_d = Campaign.objects.create(
            name="Campaign D",
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timezone.timedelta(days=7)).date(),
            status="ACTIVE",
            target_scope="ALL",
        )

        results = {"c": None, "d": None}
        exceptions = {"c": None, "d": None}
        barrier = threading.Barrier(2)

        def set_follows_c():
            try:
                close_old_connections()
                barrier.wait()
                with transaction.atomic():
                    results["c"] = set_campaign_follows(campaign_c.pk, campaign_a.pk)
            except Exception as e:
                exceptions["c"] = e
            finally:
                close_old_connections()

        def set_follows_d():
            try:
                close_old_connections()
                barrier.wait()
                with transaction.atomic():
                    results["d"] = set_campaign_follows(campaign_d.pk, campaign_b.pk)
            except Exception as e:
                exceptions["d"] = e
            finally:
                close_old_connections()

        thread_c = threading.Thread(target=set_follows_c)
        thread_d = threading.Thread(target=set_follows_d)

        thread_c.start()
        thread_d.start()
        thread_c.join(timeout=10)
        thread_d.join(timeout=10)

        # Her iki thread de başarılı olmalı (farklı predecessor)
        assert exceptions["c"] is None, f"C → A hata aldı: {exceptions['c']}"
        assert exceptions["d"] is None, f"D → B hata aldı: {exceptions['d']}"
        assert results["c"] is not None, "C → A başarısız"
        assert results["d"] is not None, "D → B başarısız"
        assert results["c"].follows == campaign_a
        assert results["d"].follows == campaign_b


@pytest.mark.django_db(transaction=True)
class TestKioskQuotaConcurrency:
    """KioskDayQuota placed<=quota concurrency testleri."""

    def test_concurrent_quota_placement_constraint(self, kiosk):
        """
        İki thread aynı kiosk-gün için quota yerleştirme yapar.
        Beklenti: placed <= quota constraint korunur (DB veya application level).
        
        PostgreSQL serializable isolation veya explicit locking gerektirir.
        
        NOT: Bu test row-level constraint'i test eder (KioskDayQuota.placed <= quota).
        Global allocation_total SUM invariant ayrı test gerektirir (test_concurrent_global_quota_invariant).
        """
        _assert_postgresql()
        
        today = timezone.now().date()
        planning_run = PlanningRun.objects.create(
            horizon_start=today,
            horizon_end=today + timezone.timedelta(days=3),
            status=PlanningRun.RunStatus.ACTIVE,
        )
        campaign = Campaign.objects.create(
            name="Test Campaign",
            start_date=today,
            end_date=today + timezone.timedelta(days=7),
            status="ACTIVE",
            target_scope="ALL",
        )

        # İlk quota: placed=0, quota=10
        quota = KioskDayQuota.objects.create(
            planning_run=planning_run,
            campaign=campaign,
            kiosk=kiosk,
            date=today,
            quota=10,
            placed=0,
        )

        exceptions = []
        barrier = threading.Barrier(2)

        def increment_placed(amount):
            """Thread: placed += amount (8 veya 5)"""
            try:
                close_old_connections()
                barrier.wait()  # Eşzamanlı başlangıç
                with transaction.atomic():
                    # select_for_update: row-level lock
                    q = KioskDayQuota.objects.select_for_update(nowait=False).get(
                        pk=quota.pk
                    )
                    q.placed += amount
                    q.save()
            except Exception as e:
                exceptions.append(e)
            finally:
                close_old_connections()

        thread_1 = threading.Thread(target=lambda: increment_placed(8))
        thread_2 = threading.Thread(target=lambda: increment_placed(5))

        thread_1.start()
        thread_2.start()
        thread_1.join(timeout=10)
        thread_2.join(timeout=10)

        # Refresh from DB
        quota.refresh_from_db()

        # Beklenti: placed <= quota (DB constraint veya serialization)
        # Eğer her iki thread de başarılıysa 8+5=13 > 10 → constraint ihlali olmalı
        # Ya da biri IntegrityError almalı
        if exceptions:
            # En az bir thread constraint ihlali aldı → DOĞRU
            assert any(
                "placed_lte_quota" in str(e).lower() or "constraint" in str(e).lower()
                for e in exceptions
            ), f"Unexpected exception: {exceptions}"
        else:
            # İki thread de başarılıysa placed <= quota olmalı
            assert quota.placed <= quota.quota, (
                f"Concurrency race: placed={quota.placed} > quota={quota.quota}. "
                "select_for_update() koruması başarısız."
            )

    def test_concurrent_global_quota_invariant(self, kiosk):
        """
        Global CAMPAIGN_TOTAL quota invariant testi.
        
        Gerçek invariant: SUM(reserved/placed for allocation) <= allocation_total
        
        Test senaryosu:
        - allocation_total = 100
        - T1: kiosk_1, date_1 için 60 reserve eder
        - T2: kiosk_2, date_2 için 60 reserve eder
        - İkisi birden başarılı olamaz (60+60 > 100)
        - Son durum: SUM(placed) <= 100
        """
        _assert_postgresql()
        
        from apps.pharmacies.models import Eczane, Kiosk
        from apps.campaigns.services.quota_service import GlobalQuotaService, QuotaReservationError
        
        # Planning run oluştur
        today = timezone.now().date()
        planning_run = PlanningRun.objects.create(
            horizon_start=today,
            horizon_end=today + timezone.timedelta(days=3),
            status=PlanningRun.RunStatus.ACTIVE,
        )
        
        # Campaign + CAMPAIGN_TOTAL delivery rule
        campaign = Campaign.objects.create(
            name="Global Quota Test Campaign",
            start_date=today,
            end_date=today + timezone.timedelta(days=7),
            status="ACTIVE",
            target_scope="ALL",
        )
        
        delivery_rule = DeliveryRule.objects.create(
            campaign=campaign,
            delivery_type=DeliveryRule.DeliveryType.CAMPAIGN_TOTAL,
            count=100,  # total_target = 100
            guarantee_mode=DeliveryRule.GuaranteeMode.GUARANTEED,
        )
        
        # İki kiosk oluştur
        from apps.lookups.models import Il, Ilce
        istanbul = Il.objects.create(ad="İstanbul")
        kadikoy = Ilce.objects.create(il=istanbul, ad="Kadıköy")
        eczane_a = Eczane.objects.create(ad="Eczane A", il=istanbul, ilce=kadikoy)
        eczane_b = Eczane.objects.create(ad="Eczane B", il=istanbul, ilce=kadikoy)
        
        kiosk_1 = Kiosk.objects.create(
            device_id="k1-global",
            mac_adresi="AA:BB:CC:DD:EE:01",
            eczane=eczane_a,
            ad="Kiosk 1",
            uygulama_anahtari="app-key-k1-" + str(uuid.uuid4())[:16]
        )
        kiosk_2 = Kiosk.objects.create(
            device_id="k2-global",
            mac_adresi="AA:BB:CC:DD:EE:02",
            eczane=eczane_b,
            ad="Kiosk 2",
            uygulama_anahtari="app-key-k2-" + str(uuid.uuid4())[:16]
        )
        
        # Allocation başlat
        GlobalQuotaService.initialize_allocation(
            planning_run=planning_run,
            campaign=campaign,
            delivery_rule=delivery_rule,
            target_kiosks=[kiosk_1.id, kiosk_2.id],
            date_range=[today, today + timezone.timedelta(days=1)],
        )
        
        results = {"t1": None, "t2": None}
        exceptions = {"t1": None, "t2": None}
        barrier = threading.Barrier(2)
        
        def reserve_t1():
            """Thread 1: kiosk_1, today için 60 reserve"""
            try:
                close_old_connections()
                barrier.wait()  # Eşzamanlı başlangıç
                quota = GlobalQuotaService.reserve_for_kiosk_day(
                    planning_run=planning_run,
                    campaign=campaign,
                    kiosk_id=kiosk_1.id,
                    date=today,
                    requested_count=60,
                )
                results["t1"] = quota
            except Exception as e:
                exceptions["t1"] = e
            finally:
                close_old_connections()
        
        def reserve_t2():
            """Thread 2: kiosk_2, today+1 için 60 reserve"""
            try:
                close_old_connections()
                barrier.wait()  # Eşzamanlı başlangıç
                quota = GlobalQuotaService.reserve_for_kiosk_day(
                    planning_run=planning_run,
                    campaign=campaign,
                    kiosk_id=kiosk_2.id,
                    date=today + timezone.timedelta(days=1),
                    requested_count=60,
                )
                results["t2"] = quota
            except Exception as e:
                exceptions["t2"] = e
            finally:
                close_old_connections()
        
        thread_1 = threading.Thread(target=reserve_t1)
        thread_2 = threading.Thread(target=reserve_t2)
        
        thread_1.start()
        thread_2.start()
        thread_1.join(timeout=10)
        thread_2.join(timeout=10)
        
        # Assertion: En fazla biri başarılı (60+60 > 100)
        success_count = sum(1 for r in results.values() if r is not None)
        error_count = sum(1 for e in exceptions.values() if e is not None)
        
        assert success_count + error_count == 2, (
            f"Thread sonuçları eksik: success={success_count}, error={error_count}"
        )
        
        assert success_count <= 1, (
            f"İki thread da başarılı olamaz (60+60 > 100). "
            f"results={results}, exceptions={exceptions}"
        )
        
        # En az bir thread QuotaReservationError almalı
        if error_count > 0:
            failed_exceptions = [e for e in exceptions.values() if e is not None]
            assert any(
                isinstance(e, QuotaReservationError) or "quota" in str(e).lower()
                for e in failed_exceptions
            ), f"Unexpected exceptions: {failed_exceptions}"
        
        # Final DB state: SUM(placed) <= 100
        from django.db.models import Sum as DBSum
        total_placed = KioskDayQuota.objects.filter(
            planning_run=planning_run,
            campaign=campaign,
        ).aggregate(total=DBSum("placed"))["total"] or 0
        
        assert total_placed <= 100, (
            f"Global quota invariant violated: total_placed={total_placed} > 100"
        )
        
        # Başarılı reservation toplamı DB toplamına eşit olmalı
        successful_placed = sum(
            r.placed for r in results.values() if r is not None
        )
        assert total_placed == successful_placed, (
            f"DB total mismatch: total_placed={total_placed}, "
            f"successful_placed={successful_placed}"
        )


@pytest.mark.django_db
class TestTargetIntersection:
    """A→B target intersection validation."""

    def test_follows_target_no_overlap_rejected(self, db):
        """
        A: target_scope=RULES, hedef İstanbul
        B: target_scope=RULES, hedef Ankara
        → set_campaign_follows(A, B) → ValidationError (hedef kesişmesi yok)
        """
        _assert_postgresql()
        
        from apps.lookups.models import Il, Ilce
        from apps.pharmacies.models import Eczane, Kiosk
        from apps.campaigns.models import CampaignTarget

        now = timezone.now()
        
        # İki il
        istanbul = Il.objects.create(ad="İstanbul")
        ankara = Il.objects.create(ad="Ankara")
        
        # İlçeler
        kadikoy = Ilce.objects.create(il=istanbul, ad="Kadıköy")
        cankaya = Ilce.objects.create(il=ankara, ad="Çankaya")
        
        # İki eczane
        pharm_ist = Eczane.objects.create(ad="İst Eczane", il=istanbul, ilce=kadikoy)
        pharm_ank = Eczane.objects.create(ad="Ank Eczane", il=ankara, ilce=cankaya)
        
        # İki kiosk
        kiosk_ist = Kiosk.objects.create(
            device_id="k-ist", 
            mac_adresi="AA:BB:01", 
            eczane=pharm_ist, 
            ad="K İst",
            uygulama_anahtari="app-key-ist-" + str(uuid.uuid4())[:16]
        )
        kiosk_ank = Kiosk.objects.create(
            device_id="k-ank", 
            mac_adresi="AA:BB:02", 
            eczane=pharm_ank, 
            ad="K Ank",
            uygulama_anahtari="app-key-ank-" + str(uuid.uuid4())[:16]
        )
        
        # A: hedef İstanbul
        campaign_a = Campaign.objects.create(
            name="A (İstanbul)",
            start_date=now.date(),
            end_date=(now + timezone.timedelta(days=7)).date(),
            status="ACTIVE",
            target_scope="RULES",
        )
        CampaignTarget.objects.create(
            campaign=campaign_a, target_type=CampaignTarget.TargetType.IL, il=istanbul, mode="INCLUDE"
        )
        
        # B: hedef Ankara
        campaign_b = Campaign.objects.create(
            name="B (Ankara)",
            start_date=now.date(),
            end_date=(now + timezone.timedelta(days=7)).date(),
            status="ACTIVE",
            target_scope="RULES",
        )
        CampaignTarget.objects.create(
            campaign=campaign_b, target_type=CampaignTarget.TargetType.IL, il=ankara, mode="INCLUDE"
        )
        
        # A → B: hedef kesişmesi yok
        with pytest.raises(FollowsConstraintError, match="[Hh]edef kesismesi yok"):
            set_campaign_follows(campaign_a.pk, campaign_b.pk)

    def test_follows_target_overlap_allowed(self, kiosk):
        """
        A: target_scope=ALL
        B: target_scope=RULES, herhangi hedef
        → set_campaign_follows(A, B) → OK (ALL her şeyi kapsar)
        """
        _assert_postgresql()

        now = timezone.now()
        
        campaign_a = Campaign.objects.create(
            name="Campaign A (ALL)",
            start_date=now.date(),
            end_date=(now + timezone.timedelta(days=7)).date(),
            status="ACTIVE",
            target_scope="ALL",
        )
        campaign_b = Campaign.objects.create(
            name="Campaign B (RULES)",
            start_date=now.date(),
            end_date=(now + timezone.timedelta(days=7)).date(),
            status="ACTIVE",
            target_scope="RULES",
        )
        
        # B için kiosk hedefi ekle
        from apps.campaigns.models import CampaignTarget
        CampaignTarget.objects.create(
            campaign=campaign_b, 
            target_type=CampaignTarget.TargetType.KIOSK, 
            kiosk=kiosk, 
            mode="INCLUDE"
        )

        # B → A (A=ALL → her zaman kesişim var)
        result = set_campaign_follows(campaign_b.pk, campaign_a.pk)
        assert result.follows == campaign_a
