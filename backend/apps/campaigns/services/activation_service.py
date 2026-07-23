"""
Faz 3 — Simulation / Activation / Reservation Service

Campaign activation with:
- Read-only simulation (no DB mutations)
- All-or-nothing GUARANTEED activation
- BEST_EFFORT activation (respects global quota)
- CAMPAIGN_TOTAL concurrency-safe global invariant
- Idempotent re-activation (replace, not append)

Design:
  simulate() and activate() use the same planning path (PlacementEngineV2.plan_kiosk_day).
  Activation = plan (read-only) + validate + atomic persist.
  sim == generate == activation pre-plan (same fingerprint, same slots).
"""
from __future__ import annotations

import hashlib
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Set

from django.db import transaction
from django.db.models import Max

from apps.campaigns.models import (
    Campaign,
    CampaignTotalAllocation,
    DeliveryRule,
    KioskDayQuota,
    Playlist,
    PlaylistItem,
    PlanningRun,
)
from apps.campaigns.services.placement_engine_v2 import PlacementEngineV2, ShadowPlan
from apps.campaigns.services.quota_service import GlobalQuotaService, QuotaReservationError

logger = logging.getLogger(__name__)

_MAX_HORIZON_DAYS = 90


class CapacityError(Exception):
    """Kapasite/quota yetersizliği — 409 Conflict."""

    def __init__(self, message: str, blocking_reasons: Optional[List[str]] = None) -> None:
        super().__init__(message)
        self.blocking_reasons = blocking_reasons or []


class ActivationValidationError(Exception):
    """Aktivasyon öncesi validation hatası — 400 Bad Request."""

    def __init__(self, message: str, errors: Optional[Dict] = None) -> None:
        super().__init__(message)
        self.errors = errors or {}


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclasses
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class KioskDaySimResult:
    kiosk_id: int
    date: date
    requested: int
    placed: int
    unplaced: int
    capacity_used_seconds: int
    blocking_reasons: List[str] = field(default_factory=list)
    fingerprint: str = ""


@dataclass
class SimulationResult:
    campaign_id: str
    fingerprint: str
    target_kiosks: List[int]
    date_range: List[date]
    kiosk_days: List[KioskDaySimResult]
    total_requested: int
    total_placed: int
    total_unplaced: int
    would_succeed: bool
    blocking_reasons: List[str]


@dataclass
class ActivationResult:
    campaign_id: str
    planning_run_id: Optional[str]
    activated_kiosks: int
    activated_dates: int
    total_placements: int
    fingerprint: str
    is_complete: bool
    blocking_reasons: List[str]


# ─────────────────────────────────────────────────────────────────────────────
# ActivationService
# ─────────────────────────────────────────────────────────────────────────────


class ActivationService:
    """
    Faz 3 campaign simulation and activation.

    All methods are static; no instance state.
    """

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _get_date_range(campaign: Campaign) -> List[date]:
        """Campaign date range [start..end], capped at _MAX_HORIZON_DAYS."""
        start = (
            campaign.start_date.date()
            if hasattr(campaign.start_date, "date")
            else campaign.start_date
        )
        end = (
            campaign.end_date.date()
            if hasattr(campaign.end_date, "date")
            else campaign.end_date
        )
        end = min(end, start + timedelta(days=_MAX_HORIZON_DAYS - 1))

        result: List[date] = []
        current = start
        while current <= end:
            result.append(current)
            current += timedelta(days=1)
        return result

    @staticmethod
    def _resolve_target_kiosks(campaign: Campaign) -> List[int]:
        """Resolve active kiosk IDs for campaign."""
        from apps.campaigns.services.placement_engine_v2 import _resolve_target_kiosks
        return sorted(_resolve_target_kiosks(campaign))

    @staticmethod
    def _combined_fingerprint(fingerprints: List[str]) -> str:
        if not fingerprints:
            return ""
        payload = json.dumps(sorted(fingerprints), sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    @staticmethod
    def _compute_playlist_fingerprint(kiosk_id: int, target_date: date) -> Optional[str]:
        """Mevcut Playlist/PlaylistItem içeriğinden V2-uyumlu fingerprint hesapla.

        Faz 5 correctness fix:
        - Kiosk.last_v2_fingerprints stale olabilir (V1/manuel değişiklik sonrası).
        - Gerçek DB içeriğinden hesaplama her zaman tutarlıdır.
        - Bu fonksiyon Kiosk row-lock altında çağrılmalıdır.
        - V2 plan fingerprint ile karşılaştırılarak gereksiz publish önlenir.
        - DB'de kayıt yoksa None döner → publish zorunlu.
        """
        items = list(
            PlaylistItem.objects
            .filter(playlist__kiosk_id=kiosk_id, playlist__target_date=target_date)
            .order_by("estimated_start_offset_seconds", "playlist__target_hour", "playback_order")
            .select_related("creative", "house_ad")
            .values(
                "creative_id", "house_ad_id", "playback_order",
                "estimated_start_offset_seconds",
                "creative__duration_seconds", "house_ad__duration_seconds",
            )
        )
        if not items:
            return None

        canonical_items = []
        for i in items:
            asset_id = str(i["creative_id"]) if i["creative_id"] else str(i["house_ad_id"])
            asset_type = "creative" if i["creative_id"] else "house_ad"
            duration = (
                i["creative__duration_seconds"] if i["creative_id"]
                else i["house_ad__duration_seconds"]
            )
            canonical_items.append({
                "asset_id": asset_id,
                "asset_type": asset_type,
                "duration": duration or 0,
                "offset": i["estimated_start_offset_seconds"],
            })

        canonical = json.dumps(canonical_items, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    # ── Validation ────────────────────────────────────────────────────────────

    @staticmethod
    def validate_for_activation(campaign: Campaign) -> None:
        """
        Pre-activation domain validation. Raises ActivationValidationError (→ 400).

        Checks:
        1. status in {ACTIVE, DRAFT}
        2. start_date < end_date
        3. At least one grid-compliant creative
        4. DeliveryRule exists and count >= 1
        5. Target resolution non-empty
        6. Follows dependency not CANCELLED
        """
        errors: Dict[str, str] = {}

        # 1. Status
        allowed_statuses = {Campaign.Status.ACTIVE, Campaign.Status.DRAFT}
        if campaign.status not in allowed_statuses:
            errors["status"] = (
                f"Aktivasyon için kampanya ACTIVE veya DRAFT olmalıdır. Mevcut: {campaign.status}"
            )

        # 2. Date range
        if campaign.start_date >= campaign.end_date:
            errors["date_range"] = "start_date end_date'den önce olmalıdır."

        # 3. Creatives
        creatives = list(campaign.creatives.all())
        compliant = [c for c in creatives if c.is_grid_compliant]
        if not compliant:
            errors["creatives"] = (
                "Grid-uyumlu (15/30/45/60s) en az bir creative gereklidir. "
                f"Mevcut creative sayısı: {len(creatives)}."
            )

        # 4. DeliveryRule
        try:
            rule = campaign.delivery_rule
            if rule.count < 1:
                errors["delivery_rule"] = "DeliveryRule.count >= 1 olmalıdır."
        except DeliveryRule.DoesNotExist:
            errors["delivery_rule"] = "Kampanya için DeliveryRule tanımlanmamış."

        # 5. Target resolution
        if not errors:
            target_kiosks = ActivationService._resolve_target_kiosks(campaign)
            if not target_kiosks:
                errors["targets"] = "Hedef çözümlemesi boş kiosk seti döndürdü."

        # 6. Follows dependency
        if campaign.follows_id:
            follows_campaign = campaign.follows
            if follows_campaign and follows_campaign.status == Campaign.Status.CANCELLED:
                errors["follows"] = (
                    f"Takip edilen kampanya '{follows_campaign.name}' iptal edilmiş."
                )

        if errors:
            raise ActivationValidationError("Aktivasyon doğrulama hatası", errors=errors)

    # ── Simulate ─────────────────────────────────────────────────────────────

    @staticmethod
    def simulate(campaign: Campaign) -> SimulationResult:
        """
        Read-only simulation. Zero DB mutations.

        Uses PlacementEngineV2.plan_kiosk_day (commit=False implicitly) for all
        target kiosk+date combinations. Returns identical plans as activation
        pre-plan step → same fingerprint guarantee.
        """
        target_kiosks = ActivationService._resolve_target_kiosks(campaign)
        date_range = ActivationService._get_date_range(campaign)

        try:
            delivery_rule = campaign.delivery_rule
        except DeliveryRule.DoesNotExist:
            return SimulationResult(
                campaign_id=str(campaign.id),
                fingerprint="",
                target_kiosks=target_kiosks,
                date_range=date_range,
                kiosk_days=[],
                total_requested=0,
                total_placed=0,
                total_unplaced=0,
                would_succeed=False,
                blocking_reasons=["DeliveryRule bulunamadı"],
            )

        is_guaranteed = (
            delivery_rule.guarantee_mode == DeliveryRule.GuaranteeMode.GUARANTEED
        )

        kiosk_days: List[KioskDaySimResult] = []
        all_fingerprints: List[str] = []
        total_requested = 0
        total_placed = 0
        all_blocking: List[str] = []

        for kiosk_id in target_kiosks:
            for d in date_range:
                plan: ShadowPlan = PlacementEngineV2.plan_kiosk_day(
                    kiosk_id=kiosk_id,
                    target_date=d,
                    planning_run=None,
                )

                creative_items = [
                    i for i in plan.playlist_items if i["asset_type"] == "creative"
                ]
                placed = len(creative_items)
                requested = delivery_rule.count
                unplaced = max(0, requested - placed)

                reasons: List[str] = []
                if unplaced > 0 and is_guaranteed:
                    reason = (
                        f"kiosk={kiosk_id} date={d}: "
                        f"{unplaced}/{requested} slot yerleştirilemedi"
                    )
                    reasons.append(reason)
                    all_blocking.append(reason)

                kiosk_days.append(
                    KioskDaySimResult(
                        kiosk_id=kiosk_id,
                        date=d,
                        requested=requested,
                        placed=placed,
                        unplaced=unplaced,
                        capacity_used_seconds=sum(
                            i["duration_seconds"] for i in creative_items
                        ),
                        blocking_reasons=reasons,
                        fingerprint=plan.fingerprint,
                    )
                )
                total_requested += requested
                total_placed += placed
                if plan.fingerprint:
                    all_fingerprints.append(plan.fingerprint)

        combined_fp = ActivationService._combined_fingerprint(all_fingerprints)

        return SimulationResult(
            campaign_id=str(campaign.id),
            fingerprint=combined_fp,
            target_kiosks=target_kiosks,
            date_range=date_range,
            kiosk_days=kiosk_days,
            total_requested=total_requested,
            total_placed=total_placed,
            total_unplaced=total_requested - total_placed,
            would_succeed=not all_blocking,
            blocking_reasons=all_blocking,
        )

    # ── Activate ─────────────────────────────────────────────────────────────

    @staticmethod
    def activate(campaign: Campaign, user=None) -> ActivationResult:
        """
        Activate campaign (atomic, all-or-nothing for GUARANTEED).

        Step 1: Validate (400 on failure).
        Step 2: Pre-plan all kiosk+dates (read-only).
        Step 3: For GUARANTEED — if any slot missing, raise CapacityError (409).
        Step 4: In transaction.atomic():
                  a. Create PlanningRun
                  b. For CAMPAIGN_TOTAL: initialize allocation + quotas
                  c. Reserve quota per kiosk+date
                  d. Persist Playlist + PlaylistItem (replace existing)
                  e. Mark PlanningRun DONE

        CAMPAIGN_TOTAL global invariant held by select_for_update on
        CampaignTotalAllocation (GlobalQuotaService).

        Idempotency: _persist_plan deletes existing playlists for kiosk+date
        before creating new ones → re-activation replaces, doesn't append.
        KioskDayQuota.placed is set (not incremented) per activation.
        """
        ActivationService.validate_for_activation(campaign)

        target_kiosks = ActivationService._resolve_target_kiosks(campaign)
        date_range = ActivationService._get_date_range(campaign)

        delivery_rule = campaign.delivery_rule
        is_guaranteed = (
            delivery_rule.guarantee_mode == DeliveryRule.GuaranteeMode.GUARANTEED
        )
        is_campaign_total = (
            delivery_rule.delivery_type == DeliveryRule.DeliveryType.CAMPAIGN_TOTAL
        )

        # Step 2: Pre-plan (read-only, no DB mutations)
        pre_plans: Dict = {}
        blocking_reasons: List[str] = []

        for kiosk_id in target_kiosks:
            for d in date_range:
                plan: ShadowPlan = PlacementEngineV2.plan_kiosk_day(
                    kiosk_id=kiosk_id,
                    target_date=d,
                    planning_run=None,
                )
                pre_plans[(kiosk_id, d)] = plan

                creative_count = len(
                    [i for i in plan.playlist_items if i["asset_type"] == "creative"]
                )
                if is_guaranteed and creative_count < delivery_rule.count:
                    blocking_reasons.append(
                        f"kiosk={kiosk_id} date={d}: "
                        f"kapasite yetersiz (yerleşen={creative_count}, "
                        f"talep={delivery_rule.count})"
                    )

        # Step 3: GUARANTEED fast-fail
        if is_guaranteed and blocking_reasons:
            raise CapacityError(
                "GUARANTEED kampanya için tüm hedeflerde tam kapasite gereklidir.",
                blocking_reasons=blocking_reasons,
            )

        # Step 4: Atomic commit
        total_placements = 0
        planning_run_id: Optional[str] = None
        all_fingerprints: List[str] = []
        activated_kiosks: Set[int] = set()
        activated_dates: Set[date] = set()
        final_blocking: List[str] = []

        with transaction.atomic():
            # 4a. PlanningRun
            if date_range:
                planning_run = PlanningRun.objects.create(
                    horizon_start=date_range[0],
                    horizon_end=date_range[-1],
                    status=PlanningRun.RunStatus.ACTIVE,
                )
                planning_run_id = str(planning_run.id)
            else:
                planning_run = None

            # 4b. CAMPAIGN_TOTAL: initialize allocation + per-kiosk-day quotas
            if is_campaign_total and planning_run:
                GlobalQuotaService.initialize_allocation(
                    planning_run=planning_run,
                    campaign=campaign,
                    delivery_rule=delivery_rule,
                    target_kiosks=list(target_kiosks),
                    date_range=list(date_range),
                )

            # 4c-d. Reserve quota + persist per kiosk+date
            for kiosk_id in target_kiosks:
                for d in date_range:
                    plan = pre_plans[(kiosk_id, d)]
                    creative_count = len(
                        [i for i in plan.playlist_items if i["asset_type"] == "creative"]
                    )

                    # CAMPAIGN_TOTAL quota reservation (serialized via select_for_update)
                    if is_campaign_total and planning_run and creative_count > 0:
                        try:
                            GlobalQuotaService.reserve_for_kiosk_day(
                                planning_run=planning_run,
                                campaign=campaign,
                                kiosk_id=kiosk_id,
                                date=d,
                                requested_count=creative_count,
                            )
                        except QuotaReservationError as exc:
                            if is_guaranteed:
                                # Triggers transaction rollback
                                raise CapacityError(
                                    f"GUARANTEED quota aşıldı: {exc}",
                                    blocking_reasons=[str(exc)],
                                ) from exc
                            # BEST_EFFORT: skip this kiosk+date
                            final_blocking.append(
                                f"kiosk={kiosk_id} date={d}: quota aşıldı"
                            )
                            continue

                    # Persist Playlist + PlaylistItem
                    n = ActivationService._persist_plan(kiosk_id, d, plan)
                    total_placements += n
                    activated_kiosks.add(kiosk_id)
                    activated_dates.add(d)
                    if plan.fingerprint:
                        all_fingerprints.append(plan.fingerprint)

            # 4e. Mark PlanningRun DONE
            if planning_run:
                planning_run.status = PlanningRun.RunStatus.DONE
                planning_run.save(update_fields=["status", "guncellenme_tarihi"])

        combined_fp = ActivationService._combined_fingerprint(all_fingerprints)

        return ActivationResult(
            campaign_id=str(campaign.id),
            planning_run_id=planning_run_id,
            activated_kiosks=len(activated_kiosks),
            activated_dates=len(activated_dates),
            total_placements=total_placements,
            fingerprint=combined_fp,
            is_complete=not final_blocking and not blocking_reasons,
            blocking_reasons=final_blocking or blocking_reasons,
        )

    # ── Persistence helper ────────────────────────────────────────────────────

    @staticmethod
    def _persist_plan(
        kiosk_id: int,
        target_date: date,
        plan: ShadowPlan,
        check_fingerprint: bool = False,
    ) -> Optional[int]:
        """
        Persist V2 plan → Playlist + PlaylistItem (race-safe).

        check_fingerprint=False (default, activation):
          Always publish regardless of current content.
          Returns creative_count (int >= 0).

        check_fingerprint=True (queue worker):
          Re-checks fingerprint from actual PlaylistItem records INSIDE Kiosk lock.
          If current DB content matches new plan → returns None (skipped, no version bump).
          If different → publishes and returns creative_count.
          Correctness guarantee: manual/V1 mutations detected because we compute
          from actual DB, not from stale metadata.

        Faz 4 hardening:
          - Kiosk satırı select_for_update() ile kilitlenir → concurrent publish lost-update önlenir.
          - last_playlist_version (desired version) aynı transaction içinde güncellenir.
          - Fingerprint last_v2_fingerprints[date] içinde saklanır (metadata, not truth source).

        MUST be called within transaction.atomic().
        """
        from apps.pharmacies.models import Kiosk

        try:
            # Race-safe: Kiosk satırını kilitle → aynı anda iki worker version'ı iki kez artıramaz
            kiosk = Kiosk.objects.select_for_update().get(id=kiosk_id)
        except Kiosk.DoesNotExist:
            logger.warning("_persist_plan: kiosk %s not found", kiosk_id)
            return 0

        if check_fingerprint and plan.fingerprint:
            # Correctness: compute fingerprint from actual DB content INSIDE lock.
            # Manual/V1 mutations are detected here; Kiosk.last_v2_fingerprints is NOT used.
            current_fp = ActivationService._compute_playlist_fingerprint(kiosk_id, target_date)
            if current_fp == plan.fingerprint:
                return None  # sentinel: skipped (fingerprint unchanged, verified inside lock)

        # Version: kilitlendikten sonra Max hesapla → race-safe monoton artış
        agg = Playlist.objects.filter(kiosk=kiosk).aggregate(mv=Max("version"))
        next_version = (agg["mv"] or 0) + 1

        # Replace: delete existing for kiosk+date
        Playlist.objects.filter(kiosk=kiosk, target_date=target_date).delete()

        # Group items by hour (offset // 3600)
        items_by_hour: Dict[int, list] = defaultdict(list)
        for item in plan.playlist_items:
            hour = item["estimated_start_offset_seconds"] // 3600
            items_by_hour[hour].append(item)

        creative_count = 0

        for hour in range(24):
            playlist = Playlist.objects.create(
                kiosk=kiosk,
                target_date=target_date,
                target_hour=hour,
                version=next_version,
            )

            hour_items = sorted(
                items_by_hour.get(hour, []),
                key=lambda i: i["estimated_start_offset_seconds"],
            )

            bulk: list = []
            for order, item in enumerate(hour_items):
                if item["asset_type"] == "creative":
                    creative_count += 1
                    bulk.append(
                        PlaylistItem(
                            playlist=playlist,
                            creative_id=item["asset_id"],
                            playback_order=order,
                            estimated_start_offset_seconds=item[
                                "estimated_start_offset_seconds"
                            ],
                        )
                    )
                else:
                    bulk.append(
                        PlaylistItem(
                            playlist=playlist,
                            house_ad_id=item["asset_id"],
                            playback_order=order,
                            estimated_start_offset_seconds=item[
                                "estimated_start_offset_seconds"
                            ],
                        )
                    )

            if bulk:
                PlaylistItem.objects.bulk_create(bulk)

        # Desired version bump + fingerprint storage (Kiosk satırı zaten kilitli)
        update_fields = ["guncellenme_tarihi"]
        if not kiosk.last_playlist_version or next_version > kiosk.last_playlist_version:
            kiosk.last_playlist_version = next_version
            update_fields.append("last_playlist_version")

        if plan.fingerprint:
            fp_dict = kiosk.last_v2_fingerprints or {}
            fp_dict[str(target_date)] = plan.fingerprint
            kiosk.last_v2_fingerprints = fp_dict
            update_fields.append("last_v2_fingerprints")

        kiosk.save(update_fields=update_fields)

        return creative_count
