"""
PlacementEngine V2 — Shadow Mode Implementation

CAMPAIGN_TOTAL + DeliveryRule-based slot placement.

Shadow mode: V1 scheduler korunur, V2 paralel çalışır, sonucu log'a yazar.
Feature flag: DOOH_ENGINE_V2 (off/shadow)
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import List, Dict, Optional, Set, Tuple
from decimal import Decimal
import hashlib
import json
import logging

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Prefetch
from django.utils import timezone

from apps.campaigns.models import (
    Campaign,
    Creative,
    DeliveryRule,
    HouseAd,
    CampaignTarget,
    PlanningRun,
    KioskDayQuota,
)
from apps.campaigns.services.quota_service import GlobalQuotaService

logger = logging.getLogger(__name__)


@dataclass
class PlacementSlot:
    """Placement slot in hour grid."""
    start_offset: int  # 0..3599 (saat içinde saniye)
    end_offset: int  # exclusive
    duration_seconds: int
    creative_id: Optional[str] = None
    house_ad_id: Optional[str] = None
    campaign_id: Optional[str] = None
    asset_type: str = "creative"  # creative / house_ad
    
    def overlaps(self, other: "PlacementSlot") -> bool:
        """Check if this slot overlaps with another."""
        return not (self.end_offset <= other.start_offset or other.end_offset <= self.start_offset)


@dataclass
class HourGrid:
    """24 saatlik placement grid."""
    date: date
    slots: List[PlacementSlot]
    
    @classmethod
    def create(cls, target_date: date) -> "HourGrid":
        """Boş grid oluştur."""
        return cls(date=target_date, slots=[])
    
    def can_place(self, start_offset: int, duration: int) -> bool:
        """Belirtilen offset+duration için yer var mı (overlap check)."""
        if start_offset < 0 or start_offset + duration > 3600:
            return False
        
        proposed = PlacementSlot(
            start_offset=start_offset,
            end_offset=start_offset + duration,
            duration_seconds=duration,
        )
        
        for slot in self.slots:
            if proposed.overlaps(slot):
                return False
        
        return True
    
    def find_next_free_offset(self, duration: int, start_from: int = 0) -> Optional[int]:
        """Duration süresi için bir sonraki boş offset'i bul."""
        # Mevcut slot'ları sırala
        sorted_slots = sorted(self.slots, key=lambda s: s.start_offset)
        
        current_offset = max(0, start_from)
        
        for slot in sorted_slots:
            if current_offset + duration <= slot.start_offset:
                # Bu slot'tan önce yer var
                return current_offset
            # Slot'tan sonraya geç
            current_offset = max(current_offset, slot.end_offset)
        
        # Sonraki boş alan
        if current_offset + duration <= 3600:
            return current_offset
        
        return None
    
    def place_slot(
        self,
        start_offset: int,
        duration: int,
        creative_id=None,
        house_ad_id=None,
        campaign_id=None,
    ) -> bool:
        """Slot yerleştir (overlap check ile)."""
        if not self.can_place(start_offset, duration):
            return False
        
        self.slots.append(PlacementSlot(
            start_offset=start_offset,
            end_offset=start_offset + duration,
            duration_seconds=duration,
            creative_id=creative_id,
            house_ad_id=house_ad_id,
            campaign_id=campaign_id,
            asset_type="house_ad" if house_ad_id else "creative",
        ))
        return True


@dataclass
class PlacementDemand:
    """Placement demand (DeliveryRule'dan türetilir)."""
    campaign: Campaign  # Campaign instance (follows çözümü için)
    delivery_rule: DeliveryRule
    creatives: List[Dict]  # [{id, duration, weight}]
    
    @property
    def campaign_id(self) -> str:
        return str(self.campaign.id)
    
    @property
    def guarantee_mode(self) -> str:
        return self.delivery_rule.guarantee_mode
    
    @property
    def priority(self) -> int:
        return self.campaign.priority
    
    @property
    def delivery_type(self) -> str:
        return self.delivery_rule.delivery_type


def _resolve_target_kiosks(campaign: Campaign) -> Set[int]:
    """
    Campaign'in hedefladigi kiosk ID setini döndür.
    
    Follows service'deki mantıkla aynı (INCLUDE/EXCLUDE hierarchy).
    """
    from apps.pharmacies.models import Kiosk, Eczane
    
    if campaign.target_scope in ("ALL", None):
        return set(Kiosk.objects.filter(aktif=True).values_list("id", flat=True))
    
    # target_scope=RULES → resolve
    included = set()
    excluded = set()
    
    targets = list(
        CampaignTarget.objects
        .filter(campaign=campaign)
        .select_related("kiosk", "kiosk__eczane", "il", "ilce", "eczane")
    )
    
    for target in targets:
        mode = target.mode or "INCLUDE"
        target_kiosk_ids = set()
        
        if target.target_type == CampaignTarget.TargetType.KIOSK:
            if target.kiosk_id:
                target_kiosk_ids.add(target.kiosk_id)
        
        elif target.target_type == CampaignTarget.TargetType.ECZANE:
            if target.eczane_id:
                target_kiosk_ids.update(
                    Kiosk.objects.filter(eczane_id=target.eczane_id, aktif=True)
                    .values_list("id", flat=True)
                )
        
        elif target.target_type == CampaignTarget.TargetType.ILCE:
            if target.ilce_id:
                eczane_ids = Eczane.objects.filter(ilce_id=target.ilce_id).values_list("id", flat=True)
                target_kiosk_ids.update(
                    Kiosk.objects.filter(eczane_id__in=eczane_ids, aktif=True)
                    .values_list("id", flat=True)
                )
        
        elif target.target_type == CampaignTarget.TargetType.IL:
            if target.il_id:
                eczane_ids = Eczane.objects.filter(il_id=target.il_id).values_list("id", flat=True)
                target_kiosk_ids.update(
                    Kiosk.objects.filter(eczane_id__in=eczane_ids, aktif=True)
                    .values_list("id", flat=True)
                )
        
        if mode == "INCLUDE":
            included.update(target_kiosk_ids)
        elif mode == "EXCLUDE":
            excluded.update(target_kiosk_ids)
    
    return included - excluded


def _is_active_on_date(campaign: Campaign, delivery_rule: DeliveryRule, target_date: date) -> bool:
    """Kampanya bu tarihte aktif mi?"""
    # Tarih aralığı kontrolü (DateTimeField → date convert)
    campaign_start = campaign.start_date.date() if hasattr(campaign.start_date, 'date') else campaign.start_date
    campaign_end = campaign.end_date.date() if hasattr(campaign.end_date, 'date') else campaign.end_date
    
    if not (campaign_start <= target_date <= campaign_end):
        return False
    
    # Weekday kontrolü
    weekday = target_date.isoweekday()  # 1=Monday, 7=Sunday
    active_weekdays = delivery_rule.active_weekdays
    if active_weekdays and weekday not in active_weekdays:
        return False
    
    return True


@dataclass
class ShadowPlan:
    """V2 shadow mode çıktısı."""
    kiosk_id: int
    date: date
    playlist_items: List[Dict]
    metrics: Dict
    fingerprint: str


class PlacementEngineV2:
    """
    PlacementEngine V2 — Canonical (Faz 7)

    V2 her zaman aktif. DOOH_ENGINE_V2 feature flag kaldırıldı.
    """

    @staticmethod
    def plan_kiosk_day(
        kiosk_id: int,
        target_date: date,
        planning_run: Optional[PlanningRun] = None,
    ) -> ShadowPlan:
        """
        Kiosk-gün için placement planı üret (shadow mode).
        
        Args:
            kiosk_id: Kiosk ID
            target_date: Target date
            planning_run: PlanningRun instance (CAMPAIGN_TOTAL için gerekli)
        
        Returns:
            ShadowPlan with playlist items and metrics
        """
        from apps.pharmacies.models import Kiosk
        
        try:
            kiosk = Kiosk.objects.get(id=kiosk_id, aktif=True)
        except Kiosk.DoesNotExist:
            # Pasif kiosk → boş plan
            return ShadowPlan(
                kiosk_id=kiosk_id,
                date=target_date,
                playlist_items=[],
                metrics={"error": "kiosk_not_active"},
                fingerprint="",
            )
        
        # 1. Build demands (tarih/weekday filtresi dahil)
        demands = PlacementEngineV2._build_demands(kiosk, target_date, planning_run)
        
        # 2. Follows chain resolver: A→B ardışıklığını çöz
        demands = PlacementEngineV2._resolve_follows_chains(demands)
        
        # 3. Create hour grid (24 saat × 3600 saniye)
        grid = HourGrid.create(target_date)
        
        # 4. Sort by priority (guaranteed first, then priority, then id)
        sorted_demands = sorted(
            demands,
            key=lambda d: (
                0 if d.guarantee_mode == "GUARANTEED" else 1,
                -d.priority,
                d.campaign_id,
            )
        )
        
        # 5. Place guaranteed demands
        for demand in sorted_demands:
            if demand.guarantee_mode == "GUARANTEED":
                PlacementEngineV2._place_demand(grid, demand, kiosk_id, target_date, planning_run)
        
        # 6. Place best-effort demands
        for demand in sorted_demands:
            if demand.guarantee_mode == "BEST_EFFORT":
                PlacementEngineV2._place_demand(grid, demand, kiosk_id, target_date, planning_run)
        
        # 7. Fill house ads
        PlacementEngineV2._fill_house_ads(grid)
        
        # 8. Materialize playlist items
        items = PlacementEngineV2._materialize(grid)
        
        # 9. Calculate fingerprint
        fingerprint = PlacementEngineV2._calculate_fingerprint(items)
        
        # 10. Metrics
        metrics = {
            "total_items": len(items),
            "creative_items": len([i for i in items if i["asset_type"] == "creative"]),
            "house_ad_items": len([i for i in items if i["asset_type"] == "house_ad"]),
            "total_duration": sum(i["duration_seconds"] for i in items),
            "total_campaigns": len(set(d.campaign_id for d in demands)),
        }
        
        return ShadowPlan(
            kiosk_id=kiosk_id,
            date=target_date,
            playlist_items=items,
            metrics=metrics,
            fingerprint=fingerprint,
        )
    
    @staticmethod
    def _build_demands(kiosk, target_date: date, planning_run) -> List[PlacementDemand]:
        """Active kampanyalardan placement demand'leri üret."""
        demands = []
        
        # Active campaigns for this date
        campaigns = Campaign.objects.filter(
            status="ACTIVE",
            start_date__lte=target_date,
            end_date__gte=target_date,
        ).prefetch_related(
            "delivery_rule",
            "creatives",
            "targets",
        ).select_related("follows")
        
        for campaign in campaigns:
            # Delivery rule check
            try:
                delivery_rule = campaign.delivery_rule
            except DeliveryRule.DoesNotExist:
                continue
            
            # Tarih/weekday aktiflik kontrolü
            if not _is_active_on_date(campaign, delivery_rule, target_date):
                continue
            
            # Target scope check
            target_kiosks = _resolve_target_kiosks(campaign)
            if kiosk.id not in target_kiosks:
                continue
            
            # Creatives
            creatives = [
                {
                    "id": str(c.id),
                    "duration": c.duration_seconds,
                    "weight": c.weight,
                }
                for c in campaign.creatives.all()
            ]
            
            if not creatives:
                continue
            
            demand = PlacementDemand(
                campaign=campaign,
                delivery_rule=delivery_rule,
                creatives=creatives,
            )
            
            demands.append(demand)
        
        return demands
    
    @staticmethod
    def _resolve_follows_chains(demands: List[PlacementDemand]) -> List[PlacementDemand]:
        """
        A→B follows zincirleri çöz.
        
        B'nin predecessor'u A ise:
        - A ve B demand listesinde ise, A'yı B'den önce yerleştir
        - B'yi demand listesinden çıkar, A'nın içine embedded et
        
        Basitleştirilmiş versiyon: Şimdilik yalnızca sıralamayı ayarla.
        Gerçek embedding Faz 3'te yapılabilir.
        """
        # follows_id → campaign mapping
        campaign_map = {d.campaign_id: d for d in demands}
        
        # B→A predecessors
        predecessors = {}
        for demand in demands:
            if demand.campaign.follows_id:
                predecessors[demand.campaign_id] = str(demand.campaign.follows_id)
        
        # Topological sort (basit: follows varsa önce onu yerleştir)
        sorted_demands = []
        visited = set()
        
        def visit(demand_id):
            if demand_id in visited:
                return
            visited.add(demand_id)
            
            # Predecessor varsa önce onu ziyaret et
            if demand_id in predecessors:
                pred_id = predecessors[demand_id]
                if pred_id in campaign_map:
                    visit(pred_id)
            
            if demand_id in campaign_map:
                sorted_demands.append(campaign_map[demand_id])
        
        for demand in demands:
            visit(demand.campaign_id)
        
        return sorted_demands
    
    @staticmethod
    def _place_demand(
        grid: HourGrid,
        demand: PlacementDemand,
        kiosk_id: int,
        target_date: date,
        planning_run: Optional[PlanningRun],
    ) -> int:
        """
        Demand'i grid'e yerleştir.
        
        Returns:
            Yerleştirilen placement sayısı
        """
        delivery_type = demand.delivery_rule.delivery_type
        count = demand.delivery_rule.count
        
        # CAMPAIGN_TOTAL: Global quota check
        if delivery_type == "CAMPAIGN_TOTAL":
            if planning_run is None:
                return 0
            
            try:
                quota = KioskDayQuota.objects.get(
                    planning_run=planning_run,
                    campaign_id=demand.campaign_id,
                    kiosk_id=kiosk_id,
                    date=target_date,
                )
                available = quota.quota - quota.placed
                count = min(count, available)
            except KioskDayQuota.DoesNotExist:
                count = 0
        
        if count <= 0:
            return 0
        
        # TIME_WINDOW: Belirli saat aralığında yerleştir
        if delivery_type == "TIME_WINDOW":
            window_start = demand.delivery_rule.window_start_time
            window_end = demand.delivery_rule.window_end_time
            
            if window_start and window_end:
                start_offset = window_start.hour * 3600 + window_start.minute * 60 + window_start.second
                end_offset = window_end.hour * 3600 + window_end.minute * 60 + window_end.second
                
                return PlacementEngineV2._place_in_window(
                    grid, demand, count, start_offset, end_offset
                )
        
        # PER_HOUR: Saate N kez yerleştir
        if delivery_type == "PER_HOUR":
            active_hours = demand.delivery_rule.active_hours or list(range(24))
            max_per_hour = demand.delivery_rule.max_per_hour or count
            
            placed = 0
            for hour in active_hours:
                hour_start = hour * 3600
                hour_end = (hour + 1) * 3600
                placed += PlacementEngineV2._place_in_window(
                    grid, demand, min(count, max_per_hour), hour_start, hour_end
                )
            
            return placed
        
        # PER_DAY: Gün içinde N kez yerleştir
        if delivery_type == "PER_DAY":
            active_hours = demand.delivery_rule.active_hours or list(range(24))
            
            # Tüm active hours'ı birleştir
            windows = []
            for hour in active_hours:
                windows.append((hour * 3600, (hour + 1) * 3600))
            
            placed = 0
            for start, end in windows:
                if placed >= count:
                    break
                placed += PlacementEngineV2._place_in_window(
                    grid, demand, count - placed, start, end
                )
            
            return placed
        
        # LEGACY_PER_LOOP: Desteklenmiyor (V2'de yok)
        return 0
    
    @staticmethod
    def _place_in_window(
        grid: HourGrid,
        demand: PlacementDemand,
        count: int,
        start_offset: int,
        end_offset: int,
    ) -> int:
        """Belirtilen window içinde count adet placement yap."""
        placed = 0
        
        # Creative seç (weight-based, şimdilik ilk creative)
        if not demand.creatives:
            return 0
        
        creative = demand.creatives[0]
        duration = creative["duration"]
        
        current_offset = start_offset
        
        for _ in range(count):
            # Bir sonraki boş offset'i bul
            free_offset = grid.find_next_free_offset(duration, current_offset)
            
            if free_offset is None or free_offset + duration > end_offset:
                break
            
            # Yerleştir
            if grid.place_slot(
                start_offset=free_offset,
                duration=duration,
                creative_id=creative["id"],
                campaign_id=demand.campaign_id,
            ):
                placed += 1
                current_offset = free_offset + duration
            else:
                break
        
        return placed
    
    @staticmethod
    def _fill_house_ads(grid: HourGrid):
        """Grid boşluklarını house ad ile doldur."""
        house_ads = list(HouseAd.objects.filter(aktif=True).order_by("-priority", "id"))
        
        if not house_ads:
            return
        
        # 0..3599 arasındaki boş alanları bul
        current_offset = 0
        house_ad_idx = 0
        
        while current_offset < 3600:
            # Bir sonraki house ad
            house_ad = house_ads[house_ad_idx % len(house_ads)]
            duration = house_ad.duration_seconds
            
            # Boş alan bul
            free_offset = grid.find_next_free_offset(duration, current_offset)
            
            if free_offset is None:
                break
            
            # Yerleştir
            if not grid.place_slot(
                start_offset=free_offset,
                duration=duration,
                house_ad_id=str(house_ad.id),
            ):
                break
            
            current_offset = free_offset + duration
            house_ad_idx += 1
    
    @staticmethod
    def _materialize(grid: HourGrid) -> List[Dict]:
        """Grid'den playlist item'ları üret."""
        # Slot'ları offset'e göre sırala
        sorted_slots = sorted(grid.slots, key=lambda s: s.start_offset)
        
        items = []
        for i, slot in enumerate(sorted_slots):
            item = {
                "playback_order": i,
                "asset_id": slot.creative_id or slot.house_ad_id,
                "asset_type": slot.asset_type,
                "duration_seconds": slot.duration_seconds,
                "estimated_start_offset_seconds": slot.start_offset,
                "campaign_id": slot.campaign_id,
            }
            items.append(item)
        
        return items
    
    @staticmethod
    def _calculate_fingerprint(items: List[Dict]) -> str:
        """Playlist fingerprint hesapla."""
        # Canonical representation
        canonical = json.dumps(
            [
                {
                    "asset_id": i["asset_id"],
                    "asset_type": i["asset_type"],
                    "duration": i["duration_seconds"],
                    "offset": i["estimated_start_offset_seconds"],
                }
                for i in items
            ],
            sort_keys=True,
        )
        
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]
