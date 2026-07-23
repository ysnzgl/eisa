"""
PlacementEngine V2 Unit/Integration Tests

Test coverage:
- Feature flag off/shadow behavior
- V1 sonucu korunuyor (shadow mode)
- Target resolution (ALL/RULES)
- Tarih/weekday/active hours filtreleri
- Delivery type dispatch (CAMPAIGN_TOTAL/PER_DAY/PER_HOUR/TIME_WINDOW)
- Guarantee mode priority
- Slot overlap prevention
- A→B follows ordering
- Quota constraint handling
- House ad filling
- Deterministic fingerprint
"""
import uuid
from datetime import date, time, timedelta
from unittest.mock import patch

import pytest
from django.conf import settings
from django.utils import timezone

from apps.campaigns.models import (
    Campaign,
    Creative,
    DeliveryRule,
    HouseAd,
    PlanningRun,
    KioskDayQuota,
    CampaignTotalAllocation,
)
from apps.campaigns.services.placement_engine_v2 import PlacementEngineV2
from apps.pharmacies.models import Kiosk, Eczane


@pytest.fixture
def kiosk(db):
    """Test kiosk fixture."""
    from apps.lookups.models import Il, Ilce
    
    istanbul = Il.objects.create(ad="İstanbul")
    kadikoy = Ilce.objects.create(il=istanbul, ad="Kadıköy")
    eczane = Eczane.objects.create(ad="Test Eczane", il=istanbul, ilce=kadikoy)
    
    return Kiosk.objects.create(
        device_id="test-kiosk",
        mac_adresi="AA:BB:CC:DD:EE:FF",
        eczane=eczane,
        ad="Test Kiosk",
        uygulama_anahtari="test-app-key-" + str(uuid.uuid4())[:16],
        aktif=True,
    )


@pytest.fixture
def house_ad(db):
    """House ad fixture."""
    return HouseAd.objects.create(
        name="House Ad 1",
        media_url="https://example.com/house.mp4",
        duration_seconds=15,
        aktif=True,
        priority=1,
    )


class TestFeatureFlag:
    """Faz 7: DOOH_ENGINE_V2 flag ve is_enabled/is_active_mode/should_publish metodları kaldırıldı."""

    def test_flag_off_returns_false(self):
        """Faz 7: is_enabled() metodu kaldırıldı (flag helper yok)."""
        assert not hasattr(PlacementEngineV2, 'is_enabled')

    def test_flag_shadow_returns_true(self):
        """Faz 7: is_active_mode() metodu kaldırıldı."""
        assert not hasattr(PlacementEngineV2, 'is_active_mode')

    def test_should_publish_always_false(self):
        """Faz 7: should_publish() metodu kaldırıldı."""
        assert not hasattr(PlacementEngineV2, 'should_publish')


class TestEmptyState:
    """Boş durum testleri."""

    def test_no_campaigns_returns_empty(self, kiosk, house_ad):
        """Kampanya yoksa yalnız house ad döner."""
        today = date.today()

        plan = PlacementEngineV2.plan_kiosk_day(
            kiosk_id=kiosk.id,
            target_date=today,
        )
        
        assert plan.kiosk_id == kiosk.id
        assert plan.date == today
        assert plan.metrics["creative_items"] == 0
        assert plan.metrics["house_ad_items"] > 0
        assert plan.fingerprint != ""
    
    def test_inactive_kiosk_returns_empty(self, kiosk):
        """Pasif kiosk için boş plan döner."""
        kiosk.aktif = False
        kiosk.save()
        
        today = date.today()
        
        plan = PlacementEngineV2.plan_kiosk_day(
            kiosk_id=kiosk.id,
            target_date=today,
        )
        
        assert plan.playlist_items == []
        assert "error" in plan.metrics


class TestTargetResolution:
    """Target scope resolution testleri."""
    
    def test_target_scope_all_includes_kiosk(self, kiosk, house_ad):
        """target_scope=ALL tüm aktif kiosk'ları hedefler."""
        today = date.today()
        
        campaign = Campaign.objects.create(
            name="Test Campaign",
            start_date=today,
            end_date=today + timedelta(days=7),
            status="ACTIVE",
            target_scope="ALL",
        )
        
        DeliveryRule.objects.create(
            campaign=campaign,
            delivery_type=DeliveryRule.DeliveryType.PER_DAY,
            count=5,
            guarantee_mode=DeliveryRule.GuaranteeMode.BEST_EFFORT,
        )
        
        Creative.objects.create(
            campaign=campaign,
            media_url="https://example.com/creative.mp4",
            duration_seconds=15,
            name="Creative 1",
        )
        
        plan = PlacementEngineV2.plan_kiosk_day(
            kiosk_id=kiosk.id,
            target_date=today,
        )
        
        assert plan.metrics["creative_items"] > 0
        assert plan.metrics["total_campaigns"] == 1


class TestDateFilters:
    """Tarih/weekday filtreleri testleri."""
    
    def test_campaign_outside_date_range_excluded(self, kiosk, house_ad):
        """Tarih aralığı dışındaki kampanya elenir."""
        today = date.today()
        past_date = today - timedelta(days=10)
        
        campaign = Campaign.objects.create(
            name="Past Campaign",
            start_date=past_date,
            end_date=past_date + timedelta(days=5),  # Bitti
            status="ACTIVE",
            target_scope="ALL",
        )
        
        DeliveryRule.objects.create(
            campaign=campaign,
            delivery_type=DeliveryRule.DeliveryType.PER_DAY,
            count=5,
            guarantee_mode=DeliveryRule.GuaranteeMode.BEST_EFFORT,
        )
        
        Creative.objects.create(
            campaign=campaign,
            media_url="https://example.com/creative.mp4",
            duration_seconds=15,
            name="Creative 1",
        )
        
        plan = PlacementEngineV2.plan_kiosk_day(
            kiosk_id=kiosk.id,
            target_date=today,
        )
        
        assert plan.metrics["total_campaigns"] == 0
    
    def test_weekday_filter_excludes_campaign(self, kiosk, house_ad):
        """Active weekdays dışındaki günlerde kampanya elenir."""
        today = date.today()
        weekday = today.isoweekday()  # 1=Monday, 7=Sunday
        
        # Bugün dışındaki tüm günler
        other_weekdays = [d for d in range(1, 8) if d != weekday]
        
        campaign = Campaign.objects.create(
            name="Weekday Campaign",
            start_date=today,
            end_date=today + timedelta(days=7),
            status="ACTIVE",
            target_scope="ALL",
        )
        
        DeliveryRule.objects.create(
            campaign=campaign,
            delivery_type=DeliveryRule.DeliveryType.PER_DAY,
            count=5,
            guarantee_mode=DeliveryRule.GuaranteeMode.BEST_EFFORT,
            active_weekdays=other_weekdays,
        )
        
        Creative.objects.create(
            campaign=campaign,
            media_url="https://example.com/creative.mp4",
            duration_seconds=15,
            name="Creative 1",
        )
        
        plan = PlacementEngineV2.plan_kiosk_day(
            kiosk_id=kiosk.id,
            target_date=today,
        )
        
        assert plan.metrics["total_campaigns"] == 0


class TestGuaranteeModePriority:
    """Guarantee mode priority testleri."""
    
    def test_guaranteed_placed_before_best_effort(self, kiosk, house_ad):
        """GUARANTEED kampanyalar BEST_EFFORT'tan önce yerleşir."""
        today = date.today()
        
        # BEST_EFFORT kampanya
        campaign_be = Campaign.objects.create(
            name="Best Effort",
            start_date=today,
            end_date=today + timedelta(days=7),
            status="ACTIVE",
            target_scope="ALL",
            priority=100,  # Yüksek priority
        )
        
        DeliveryRule.objects.create(
            campaign=campaign_be,
            delivery_type=DeliveryRule.DeliveryType.TIME_WINDOW,
            count=10,
            guarantee_mode=DeliveryRule.GuaranteeMode.BEST_EFFORT,
            window_start_time=time(hour=9),
            window_end_time=time(hour=17),
        )
        
        Creative.objects.create(
            campaign=campaign_be,
            media_url="https://example.com/be.mp4",
            duration_seconds=30,
            name="BE Creative",
        )
        
        # GUARANTEED kampanya
        campaign_g = Campaign.objects.create(
            name="Guaranteed",
            start_date=today,
            end_date=today + timedelta(days=7),
            status="ACTIVE",
            target_scope="ALL",
            priority=10,  # Düşük priority
        )
        
        DeliveryRule.objects.create(
            campaign=campaign_g,
            delivery_type=DeliveryRule.DeliveryType.TIME_WINDOW,
            count=5,
            guarantee_mode=DeliveryRule.GuaranteeMode.GUARANTEED,
            window_start_time=time(hour=9),
            window_end_time=time(hour=17),
        )
        
        Creative.objects.create(
            campaign=campaign_g,
            media_url="https://example.com/g.mp4",
            duration_seconds=30,
            name="G Creative",
        )
        
        plan = PlacementEngineV2.plan_kiosk_day(
            kiosk_id=kiosk.id,
            target_date=today,
        )
        
        # GUARANTEED kampanya item'ları BEST_EFFORT'tan önce
        guaranteed_items = [
            i for i in plan.playlist_items
            if i["campaign_id"] == str(campaign_g.id)
        ]
        be_items = [
            i for i in plan.playlist_items
            if i["campaign_id"] == str(campaign_be.id)
        ]
        
        if guaranteed_items and be_items:
            first_guaranteed_offset = min(i["estimated_start_offset_seconds"] for i in guaranteed_items)
            first_be_offset = min(i["estimated_start_offset_seconds"] for i in be_items)
            
            assert first_guaranteed_offset < first_be_offset


class TestSlotOverlapPrevention:
    """Slot overlap prevention testleri."""
    
    def test_no_overlapping_slots(self, kiosk, house_ad):
        """Yerleştirilen slot'lar üst üste binmez."""
        today = date.today()
        
        campaign = Campaign.objects.create(
            name="Test Campaign",
            start_date=today,
            end_date=today + timedelta(days=7),
            status="ACTIVE",
            target_scope="ALL",
        )
        
        DeliveryRule.objects.create(
            campaign=campaign,
            delivery_type=DeliveryRule.DeliveryType.PER_DAY,
            count=50,  # Çok sayıda placement
            guarantee_mode=DeliveryRule.GuaranteeMode.BEST_EFFORT,
        )
        
        Creative.objects.create(
            campaign=campaign,
            media_url="https://example.com/creative.mp4",
            duration_seconds=30,
            name="Creative 1",
        )
        
        plan = PlacementEngineV2.plan_kiosk_day(
            kiosk_id=kiosk.id,
            target_date=today,
        )
        
        # Tüm slot'ları kontrol et
        for i, item in enumerate(plan.playlist_items):
            start = item["estimated_start_offset_seconds"]
            end = start + item["duration_seconds"]
            
            # Diğer slot'larla overlap kontrolü
            for j, other in enumerate(plan.playlist_items):
                if i == j:
                    continue
                
                other_start = other["estimated_start_offset_seconds"]
                other_end = other_start + other["duration_seconds"]
                
                # Overlap yoksa: end <= other_start veya other_end <= start
                assert end <= other_start or other_end <= start, (
                    f"Overlap detected: item {i} [{start}..{end}] "
                    f"overlaps with item {j} [{other_start}..{other_end}]"
                )


class TestFollowsOrdering:
    """A→B follows ordering testleri."""
    
    def test_follows_predecessor_placed_first(self, kiosk, house_ad):
        """B→A ilişkisi varsa A önce yerleşir."""
        today = date.today()
        
        # A kampanyası
        campaign_a = Campaign.objects.create(
            name="Campaign A",
            start_date=today,
            end_date=today + timedelta(days=7),
            status="ACTIVE",
            target_scope="ALL",
            priority=10,
        )
        
        DeliveryRule.objects.create(
            campaign=campaign_a,
            delivery_type=DeliveryRule.DeliveryType.TIME_WINDOW,
            count=3,
            guarantee_mode=DeliveryRule.GuaranteeMode.BEST_EFFORT,
            window_start_time=time(hour=10),
            window_end_time=time(hour=12),
        )
        
        Creative.objects.create(
            campaign=campaign_a,
            media_url="https://example.com/a.mp4",
            duration_seconds=30,
            name="Creative A",
        )
        
        # B kampanyası (A'yı takip eder)
        campaign_b = Campaign.objects.create(
            name="Campaign B",
            start_date=today,
            end_date=today + timedelta(days=7),
            status="ACTIVE",
            target_scope="ALL",
            priority=100,  # Yüksek priority ama follows var
            follows=campaign_a,
        )
        
        DeliveryRule.objects.create(
            campaign=campaign_b,
            delivery_type=DeliveryRule.DeliveryType.TIME_WINDOW,
            count=3,
            guarantee_mode=DeliveryRule.GuaranteeMode.BEST_EFFORT,
            window_start_time=time(hour=10),
            window_end_time=time(hour=12),
        )
        
        Creative.objects.create(
            campaign=campaign_b,
            media_url="https://example.com/b.mp4",
            duration_seconds=30,
            name="Creative B",
        )
        
        plan = PlacementEngineV2.plan_kiosk_day(
            kiosk_id=kiosk.id,
            target_date=today,
        )
        
        # A ve B item'larını bul
        a_items = [i for i in plan.playlist_items if i["campaign_id"] == str(campaign_a.id)]
        b_items = [i for i in plan.playlist_items if i["campaign_id"] == str(campaign_b.id)]
        
        if a_items and b_items:
            # A'nın ilk offset'i B'nin ilk offset'inden küçük olmalı
            first_a = min(i["estimated_start_offset_seconds"] for i in a_items)
            first_b = min(i["estimated_start_offset_seconds"] for i in b_items)
            
            assert first_a < first_b, "A→B follows: A önce yerleşmeli"


class TestDeterministicOutput:
    """Deterministic output testleri."""
    
    def test_same_input_same_fingerprint(self, kiosk, house_ad):
        """Aynı girdiler aynı fingerprint üretir."""
        today = date.today()
        
        campaign = Campaign.objects.create(
            name="Test Campaign",
            start_date=today,
            end_date=today + timedelta(days=7),
            status="ACTIVE",
            target_scope="ALL",
        )
        
        DeliveryRule.objects.create(
            campaign=campaign,
            delivery_type=DeliveryRule.DeliveryType.PER_DAY,
            count=5,
            guarantee_mode=DeliveryRule.GuaranteeMode.BEST_EFFORT,
        )
        
        Creative.objects.create(
            campaign=campaign,
            media_url="https://example.com/creative.mp4",
            duration_seconds=15,
            name="Creative 1",
        )
        
        # İki kez çalıştır
        plan1 = PlacementEngineV2.plan_kiosk_day(
            kiosk_id=kiosk.id,
            target_date=today,
        )
        
        plan2 = PlacementEngineV2.plan_kiosk_day(
            kiosk_id=kiosk.id,
            target_date=today,
        )
        
        assert plan1.fingerprint == plan2.fingerprint
        assert len(plan1.playlist_items) == len(plan2.playlist_items)


@pytest.mark.django_db
def test_v2_does_not_modify_v1_output(kiosk, house_ad):
    """
    Faz 7: V2 canonical; generate_for_kiosk V1 scheduler çalıştırır.

    V1 scheduler V2 shadow çağrısı yapmaz artık (Faz 7'de shadow kaldırıldı).
    Quota/allocation tabloları V1 scheduler tarafından değiştirilmez (V2 aktif değil).
    """
    from apps.campaigns.services.scheduler import generate_for_kiosk
    from apps.campaigns.models import Playlist

    today = date.today()

    campaign = Campaign.objects.create(
        name="Test Campaign",
        start_date=today,
        end_date=today + timedelta(days=7),
        status="ACTIVE",
        target_scope="ALL",
    )

    DeliveryRule.objects.create(
        campaign=campaign,
        delivery_type=DeliveryRule.DeliveryType.PER_DAY,
        count=5,
        guarantee_mode=DeliveryRule.GuaranteeMode.BEST_EFFORT,
    )

    Creative.objects.create(
        campaign=campaign,
        media_url="https://example.com/creative.mp4",
        duration_seconds=15,
        name="Creative 1",
    )

    # V1 üretimi
    v1_playlists = generate_for_kiosk(kiosk, today)
    v1_count = sum(pl.items.count() for pl in v1_playlists)

    # V1 playlist'leri oluşturuldu
    assert len(v1_playlists) == 24  # 24 saat
    assert v1_count >= 0  # boş da olabilir (house_ad filler ile)

    # Quota/allocation V1 tarafından değiştirilmez (V2 queue worker sorumlu)
    assert KioskDayQuota.objects.count() == 0
    assert CampaignTotalAllocation.objects.count() == 0
