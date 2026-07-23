"""
CAMPAIGN_TOTAL Quota Reservation Service

Global invariant: SUM(all kiosk-day placements for allocation) <= allocation_total

Ayrı kiosk-gün eşzamanlı rezervasyonlar ortak parent CampaignTotalAllocation
üzerinden transaction.atomic + select_for_update ile serialize edilir.
"""
from decimal import Decimal
from typing import Dict, List
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.campaigns.models import (
    Campaign,
    PlanningRun,
    CampaignTotalAllocation,
    KioskDayQuota,
    DeliveryRule,
)


class QuotaReservationError(Exception):
    """Quota reservation failed (insufficient quota, invalid state, etc.)"""
    pass


class GlobalQuotaService:
    """
    CAMPAIGN_TOTAL kampanyalar için global quota yönetimi.
    
    Her rezervasyon işlemi parent CampaignTotalAllocation satırını kilitler,
    böylece paralel kiosk-gün işlemleri global toplamı aşamaz.
    """
    
    @staticmethod
    def reserve_for_kiosk_day(
        planning_run: PlanningRun,
        campaign: Campaign,
        kiosk_id: int,
        date,
        requested_count: int,
    ) -> "KioskDayQuota":
        """
        Kiosk-gün için quota rezerve et.
        
        Global invariant: SUM(all placed for this allocation) <= total_target
        
        Args:
            planning_run: PlanningRun instance
            campaign: Campaign with CAMPAIGN_TOTAL delivery rule
            kiosk_id: Kiosk ID
            date: Date for placement
            requested_count: Requested placement count
        
        Returns:
            KioskDayQuota instance (created or updated)
        
        Raises:
            QuotaReservationError: Insufficient quota or invalid state
        """
        if requested_count <= 0:
            raise QuotaReservationError(f"Invalid requested_count: {requested_count}")
        
        with transaction.atomic():
            # 1. Parent allocation'ı kilitle (global serialization)
            try:
                allocation = CampaignTotalAllocation.objects.select_for_update(
                    nowait=False
                ).get(
                    planning_run=planning_run,
                    campaign=campaign,
                )
            except CampaignTotalAllocation.DoesNotExist:
                raise QuotaReservationError(
                    f"CampaignTotalAllocation not found for campaign={campaign.id} "
                    f"planning_run={planning_run.id}"
                )
            
            # 2. Kiosk-day quota satırını al veya oluştur
            quota, created = KioskDayQuota.objects.select_for_update(nowait=False).get_or_create(
                planning_run=planning_run,
                campaign=campaign,
                kiosk_id=kiosk_id,
                date=date,
                defaults={
                    "quota": 0,  # İlk oluşturulduğunda quota 0
                    "placed": 0,
                },
            )
            
            # 3. Global toplamı kontrol et
            current_total = KioskDayQuota.objects.filter(
                planning_run=planning_run,
                campaign=campaign,
            ).aggregate(total=Sum("placed"))["total"] or 0
            
            # Yeni placement sonrası global toplam
            new_total = current_total - quota.placed + requested_count
            
            if new_total > allocation.total_target:
                raise QuotaReservationError(
                    f"Global quota exceeded: current={current_total}, "
                    f"requested={requested_count}, total_target={allocation.total_target}, "
                    f"kiosk={kiosk_id}, date={date}"
                )
            
            # 4. Row-level constraint: placed <= quota
            if requested_count > quota.quota:
                raise QuotaReservationError(
                    f"Kiosk-day quota exceeded: requested={requested_count}, "
                    f"quota={quota.quota}, kiosk={kiosk_id}, date={date}"
                )
            
            # 5. Placement'i uygula
            quota.placed = requested_count
            quota.save(update_fields=["placed", "guncellenme_tarihi"])
            
            return quota
    
    @staticmethod
    def initialize_allocation(
        planning_run: PlanningRun,
        campaign: Campaign,
        delivery_rule: DeliveryRule,
        target_kiosks: List[int],
        date_range: List,  # List of dates
    ) -> "CampaignTotalAllocation":
        """
        CAMPAIGN_TOTAL kampanyası için allocation'ı başlat.
        
        Total_target'i kiosk-gün kapasitelerine capacity-weighted dağıt.
        
        Args:
            planning_run: PlanningRun instance
            campaign: Campaign instance
            delivery_rule: DeliveryRule with delivery_type=CAMPAIGN_TOTAL
            target_kiosks: List of kiosk IDs
            date_range: List of dates in horizon
        
        Returns:
            CampaignTotalAllocation instance
        """
        if delivery_rule.delivery_type != DeliveryRule.DeliveryType.CAMPAIGN_TOTAL:
            raise QuotaReservationError(
                f"Invalid delivery_type: {delivery_rule.delivery_type}, "
                f"expected CAMPAIGN_TOTAL"
            )
        
        total_target = delivery_rule.count
        
        with transaction.atomic():
            # 1. Allocation oluştur
            allocation, created = CampaignTotalAllocation.objects.get_or_create(
                planning_run=planning_run,
                campaign=campaign,
                defaults={
                    "total_target": total_target,
                    "allocated_total": 0,
                },
            )
            
            if not created:
                # Zaten varsa güncelle (idempotent)
                allocation.total_target = total_target
                allocation.save(update_fields=["total_target", "guncellenme_tarihi"])
            
            # 2. Kiosk-day quota'ları oluştur (capacity-weighted distribution)
            # Basit dağıtım: her kiosk-gün eşit pay
            # Gerçek implementasyon capacity bazlı ağırlıklandırma yapabilir
            
            kiosk_day_count = len(target_kiosks) * len(date_range)
            if kiosk_day_count == 0:
                raise QuotaReservationError("No target kiosks or dates")
            
            # Eşit dağıtım (basitleştirilmiş)
            quota_per_kiosk_day = total_target // kiosk_day_count
            remainder = total_target % kiosk_day_count
            
            allocated_count = 0
            for kiosk_id in target_kiosks:
                for date in date_range:
                    # İlk remainder kiosk-güne +1 bonus
                    quota = quota_per_kiosk_day + (1 if allocated_count < remainder else 0)
                    
                    KioskDayQuota.objects.update_or_create(
                        planning_run=planning_run,
                        campaign=campaign,
                        kiosk_id=kiosk_id,
                        date=date,
                        defaults={
                            "quota": quota,
                            "placed": 0,
                        },
                    )
                    allocated_count += 1
            
            allocation.allocated_total = total_target
            allocation.save(update_fields=["allocated_total", "guncellenme_tarihi"])
            
            return allocation
