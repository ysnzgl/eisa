"""DOOH v2 — Spec-compliant view'leri.

Endpoint haritasi:

  Management API (JWT, SuperAdmin):
    POST   /api/campaigns/v2/                 -> Campaign create
    GET    /api/campaigns/v2/                 -> liste
    GET    /api/campaigns/v2/{id}/
    POST   /api/campaigns/v2/{id}/rules/      -> ScheduleRule (frekans matrisi)
    GET    /api/campaigns/v2/{id}/rules/
    GET    /api/campaigns/v2/{id}/timeline/?date=YYYY-MM-DD&hour=18
    GET    /api/campaigns/v2/pricing-matrix/  -> tek (singleton) — PUT/PATCH ile guncelle
    GET    /api/campaigns/v2/house-ads/
    GET    /api/inventory/availability/?date=YYYY-MM-DD&hour=18[&kiosk=<id>]

  Kiosk Edge API (App-Key + MAC):
    GET    /api/kiosk/v1/sync/                            -> tum aktif creative + house_ad listesi
    GET    /api/kiosk/v1/playlist/?date=YYYY-MM-DD
    POST   /api/kiosk/v1/proof-of-play/                   -> bulk PlayLog ingest
"""
from __future__ import annotations

import datetime as _dt
import logging
from typing import Iterable

from django.conf import settings

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.uow import UnitOfWork
from apps.pharmacies.models import Kiosk
from apps.pharmacies.permissions import IsSuperAdmin
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

import threading

from .models import (
    Campaign,
    CampaignTarget,
    Creative,
    DayPlan,
    DeliveryRule,
    GenerationJob,
    HouseAd,
    HourPlan,
    PlayLog,
    Playlist,
    PlaylistTemplate,
    PricingMatrix,
    ScheduleRule,
)
from .serializers import (
    ActivationResultSerializer,
    CampaignSerializer,
    CampaignTargetSerializer,
    CreativeSerializer,
    DayPlanSerializer,
    GenerationJobSerializer,
    HouseAdSerializer,
    HourPlanSerializer,
    KioskCreativeSyncSerializer,
    KioskHouseAdSyncSerializer,
    KioskPlaylistSerializer,
    PlaylistAdminSerializer,
    PlaylistTemplateSerializer,
    PricingMatrixSerializer,
    ProofOfPlayBulkSerializer,
    ScheduleRuleSerializer,
    SimulationResultSerializer,
)
from .services.scheduler import available_seconds, generate_for_kiosk, simulate_campaign_capacity

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Bridge: ScheduleRule → DeliveryRule otomatik senkronizasyon
# ─────────────────────────────────────────────────────────────────────────────

_SCHEDULE_TO_DELIVERY_TYPE = {
    "PER_LOOP": DeliveryRule.DeliveryType.LEGACY_PER_LOOP,
    "PER_HOUR": DeliveryRule.DeliveryType.PER_HOUR,
    "PER_DAY":  DeliveryRule.DeliveryType.PER_DAY,
}


def _sync_delivery_rule_from_schedule_rule(campaign: Campaign, rule: ScheduleRule) -> None:
    """ScheduleRule kaydedilince ilgili DeliveryRule'u upsert et.

    simulate() ve validate_for_activation() DeliveryRule'a ihtiyaç duyar.
    Bu bridge, wizard'ın ScheduleRule-tabanlı akışını DeliveryRule motoruyla
    uyumlu hale getirir.
    """
    delivery_type = _SCHEDULE_TO_DELIVERY_TYPE.get(
        rule.frequency_type, DeliveryRule.DeliveryType.LEGACY_PER_LOOP
    )
    count = max(1, int(rule.frequency_value or 1))
    active_hours = list(rule.target_hours) if rule.target_hours else None

    try:
        dr = campaign.delivery_rule
        dr.delivery_type = delivery_type
        dr.count = count
        dr.active_hours = active_hours
        dr.save(update_fields=["delivery_type", "count", "active_hours",
                               "guncellenme_tarihi"])
    except DeliveryRule.DoesNotExist:
        DeliveryRule.objects.create(
            campaign=campaign,
            delivery_type=delivery_type,
            count=count,
            active_hours=active_hours,
            guarantee_mode=DeliveryRule.GuaranteeMode.BEST_EFFORT,
        )


def _parse_date(raw: str | None) -> _dt.date:
    if not raw:
        return timezone.now().date()
    try:
        return _dt.datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"Gecersiz tarih formati: {raw} (YYYY-MM-DD bekleniyor)") from exc


# ─────────────────────────────────────────────────────────────────────────────
# Management API
# ─────────────────────────────────────────────────────────────────────────────


class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.prefetch_related(
        "creatives", "targets__il", "targets__ilce", "targets__eczane"
    ).select_related("schedule_rule")
    serializer_class = CampaignSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def perform_create(self, serializer):
        instance = Campaign(**serializer.validated_data)
        with UnitOfWork(user=self.request.user) as uow:
            uow.add(instance)
        serializer.instance = instance

    def perform_update(self, serializer):
        instance: Campaign = serializer.instance
        for k, v in serializer.validated_data.items():
            setattr(instance, k, v)
        with UnitOfWork(user=self.request.user) as uow:
            uow.update(instance)

    def perform_destroy(self, instance):
        with UnitOfWork(user=self.request.user) as uow:
            uow.delete(instance)

    # ── Toplu işlem (bulk action) ──
    @action(detail=False, methods=["post"], url_path="bulk-action")
    def bulk_action(self, request):
        """``POST /api/campaigns/v2/campaigns/bulk-action/``

        Body::

            { "action": "delete" | "pause" | "activate", "ids": ["uuid", ...] }

        Returns ``{ "updated": <int>, "action": <str> }``.
        """
        action_name = (request.data.get("action") or "").lower()
        ids = request.data.get("ids") or []
        if action_name not in {"delete", "pause", "activate"}:
            return Response(
                {"error": "action must be one of: delete | pause | activate"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(ids, list) or not ids:
            return Response(
                {"error": "ids must be a non-empty array"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = Campaign.objects.filter(pk__in=ids)
        updated = 0
        with UnitOfWork(user=request.user) as uow:
            if action_name == "delete":
                for c in list(qs):
                    uow.delete(c)
                    updated += 1
            else:
                new_status = (
                    Campaign.Status.PAUSED if action_name == "pause"
                    else Campaign.Status.ACTIVE
                )
                for c in list(qs):
                    if c.status != new_status:
                        c.status = new_status
                        uow.update(c)
                    updated += 1
        return Response({"updated": updated, "action": action_name})

    # ── CampaignTarget (IL/ILCE/ECZANE hiyerarşik hedefleme) ──
    @action(detail=True, methods=["get", "post"], url_path="targets")
    def targets(self, request, pk=None):
        """``GET``: kampanyanın hedef listesini döner.
        ``POST``: hedef listesini TAMAMEN YENİDEN YAZAR (replace semantics).

        Body örneği::

            [
              {"target_type": "IL",     "il": 6},
              {"target_type": "ILCE",   "ilce": 42},
              {"target_type": "ECZANE", "eczane": 99}
            ]
        """
        campaign = self.get_object()

        if request.method == "GET":
            qs = campaign.targets.select_related("il", "ilce", "eczane").all()
            return Response(CampaignTargetSerializer(qs, many=True).data)

        # POST — replace all targets
        if not isinstance(request.data, list):
            return Response(
                {"error": "Hedef listesi JSON dizi (array) olmalıdır."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser = CampaignTargetSerializer(
            data=[{**item, "campaign": str(campaign.pk)} for item in request.data],
            many=True,
        )
        ser.is_valid(raise_exception=True)

        with UnitOfWork(user=request.user) as uow:
            campaign.targets.all().delete()
            for validated in ser.validated_data:
                validated["campaign"] = campaign
                obj = CampaignTarget(**validated)
                uow.add(obj)

        qs = campaign.targets.select_related("il", "ilce", "eczane").all()
        return Response(
            CampaignTargetSerializer(qs, many=True).data,
            status=status.HTTP_201_CREATED,
        )

    # ── Kapasite önizleme (Before / After) ──
    @action(detail=False, methods=["post"], url_path="preview")
    def preview(self, request):
        """``POST /api/campaigns/v2/campaigns/preview/``

        Yeni bir kural eklemeden ÖNCE kapasite etkisini hesaplar.
        Kayıt yapmaz, sadece simülasyon sonucunu döner.

        Body::

            {
              "kiosk": 12,
              "date": "2026-05-15",
              "creative_duration": 15,
              "frequency_type": "PER_LOOP",
              "frequency_value": 2,
              "target_hours": [9,10,11,17,18]  // null = tüm gün
            }

        Yanıt::

            {
              "date": "2026-05-15",
              "kiosk": 12,
              "hours": [
                {"hour": 9, "before_available": 45, "after_available": 15, "has_conflict": false},
                ...
              ]
            }
        """
        kiosk_id = request.data.get("kiosk")
        if kiosk_id:
            try:
                kiosk = Kiosk.objects.get(pk=kiosk_id)
            except Kiosk.DoesNotExist:
                return Response({"error": f"Kiosk bulunamadı: {kiosk_id}"},
                                status=status.HTTP_404_NOT_FOUND)
        else:
            # Kiosk belirtilmemişse ilk aktif kiosku kullan
            kiosk = Kiosk.objects.filter(aktif=True).first()
            if not kiosk:
                try:
                    target_date = _parse_date(request.data.get("date"))
                except ValueError:
                    target_date = timezone.now().date()
                return Response({
                    "date": str(target_date), "kiosk": None,
                    "loop_duration_seconds": 60, "hours": [],
                    "note": "Sistemde aktif kiosk bulunamadı.",
                })
        try:
            target_date = _parse_date(request.data.get("date"))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            creative_duration = int(request.data.get("creative_duration", 15))
            frequency_type = str(request.data.get("frequency_type", "PER_LOOP"))
            frequency_value = int(request.data.get("frequency_value", 1))
        except (TypeError, ValueError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        target_hours = request.data.get("target_hours")  # None = all day

        result = simulate_campaign_capacity(
            kiosk=kiosk,
            target_date=target_date,
            creative_duration=creative_duration,
            frequency_type=frequency_type,
            frequency_value=frequency_value,
            target_hours=target_hours,
        )

        return Response({
            "date": str(target_date),
            "kiosk": int(kiosk.pk),
            "loop_duration_seconds": 60,
            "hours": list(result.values()),
        })

    # ── Frekans kuralı (tek kural per kampanya) ──
    @action(detail=True, methods=["get", "post", "put", "delete"], url_path="rules")
    def rules(self, request, pk=None):
        campaign = self.get_object()

        if request.method == "GET":
            rule = getattr(campaign, "schedule_rule", None)
            if rule is None:
                return Response(None)
            return Response(ScheduleRuleSerializer(rule).data)

        if request.method == "DELETE":
            rule = getattr(campaign, "schedule_rule", None)
            if rule is not None:
                with UnitOfWork(user=request.user) as uow:
                    uow.delete(rule)
            return Response(status=status.HTTP_204_NO_CONTENT)

        # POST/PUT — upsert: tek kural; varsa günceller, yoksa oluşturur
        payload = request.data
        if isinstance(payload, list):
            return Response(
                {"error": "Bir kampanyanın yalnızca tek frekans kuralı olabilir. Liste değil tek nesne gönderin."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = {**dict(payload), "campaign": str(campaign.pk)}
        existing = getattr(campaign, "schedule_rule", None)
        serializer = ScheduleRuleSerializer(instance=existing, data=data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        validated["campaign"] = campaign

        with UnitOfWork(user=request.user) as uow:
            if existing is None:
                rule = ScheduleRule(**validated)
                uow.add(rule)
            else:
                for k, v in validated.items():
                    setattr(existing, k, v)
                uow.update(existing)
                rule = existing

        # Bridge: ScheduleRule → DeliveryRule upsert (simulate/activate için gerekli)
        _sync_delivery_rule_from_schedule_rule(campaign, rule)

        return Response(
            ScheduleRuleSerializer(rule).data,
            status=status.HTTP_201_CREATED if existing is None else status.HTTP_200_OK,
        )

    # ── Admin Timeline View ──
    @action(detail=False, methods=["get"], url_path="timeline")
    def timeline(self, request):
        """Bir kiosk + tarih + saat icin Playlist'i (Gantt verisi) doner."""
        try:
            target_date = _parse_date(request.query_params.get("date"))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        kiosk_id = request.query_params.get("kiosk")
        hour = request.query_params.get("hour")
        if kiosk_id is None or hour is None:
            return Response(
                {"error": "kiosk ve hour query parametreleri zorunludur."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            hour = int(hour)
        except (TypeError, ValueError):
            return Response({"error": "hour 0-23 olmalidir."},
                            status=status.HTTP_400_BAD_REQUEST)

        playlist = Playlist.objects.filter(
            kiosk_id=kiosk_id, target_date=target_date, target_hour=hour,
        ).prefetch_related("items__creative__campaign", "items__house_ad").first()

        if playlist is None:
            return Response({"playlist": None, "items": []})
        return Response(PlaylistAdminSerializer(playlist).data)

    # ── Haftalık takvim ısı haritası (lightweight) ──
    @action(detail=False, methods=["get"], url_path="calendar")
    def calendar(self, request):
        """``GET /api/campaigns/v2/campaigns/calendar/?kiosk=<id>&start=YYYY-MM-DD[&days=7]``

        Bir kiosk için ``start`` tarihinden itibaren ``days`` gün boyunca,
        her (gün × saat) hücresi için: doluluk yüzdesi + farklı kampanya
        sayısı + ilk 3 kampanya adı döner. DB'ye yeni tablo gerekmez —
        mevcut Playlist + PlaylistItem üzerinden hesaplanır.
        """
        kiosk_id = request.query_params.get("kiosk")
        if not kiosk_id:
            return Response({"error": "kiosk parametresi zorunludur."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            start_date = _parse_date(request.query_params.get("start"))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        try:
            days = max(1, min(31, int(request.query_params.get("days", 7))))
        except (TypeError, ValueError):
            days = 7
        end_date = start_date + _dt.timedelta(days=days - 1)

        playlists = (
            Playlist.objects
            .filter(kiosk_id=kiosk_id, target_date__gte=start_date, target_date__lte=end_date)
            .prefetch_related("items__creative__campaign", "items__house_ad")
        )

        # cells[date_str][hour] = {used, free, campaigns: set, top: [name1,...]}
        cells: dict = {}
        for pl in playlists:
            day_key = str(pl.target_date)
            cells.setdefault(day_key, {})
            loop_sec = pl.loop_duration_seconds or 60
            used = 0
            campaign_seconds: dict = {}
            for it in pl.items.all():
                dur = (it.creative.duration_seconds if it.creative_id
                       else it.house_ad.duration_seconds if it.house_ad_id else 0)
                used += dur or 0
                if it.creative_id and it.creative.campaign_id:
                    name = it.creative.campaign.name
                    campaign_seconds[name] = campaign_seconds.get(name, 0) + dur
            # Loop sayısını hesapla (saat 3600 sn / 60 sn = 60 loop)
            loops_in_hour = max(1, 3600 // loop_sec)
            total_capacity = loops_in_hour * loop_sec
            top = sorted(campaign_seconds.items(), key=lambda kv: -kv[1])[:3]
            cells[day_key][pl.target_hour] = {
                "used_seconds": used,
                "capacity_seconds": total_capacity,
                "fill_pct": round(100 * used / total_capacity, 1) if total_capacity else 0,
                "campaign_count": len(campaign_seconds),
                "top_campaigns": [{"name": n, "seconds": s} for n, s in top],
            }
        return Response({
            "kiosk": int(kiosk_id),
            "start": str(start_date),
            "end": str(end_date),
            "days": days,
            "cells": cells,
        })

    # ── Faz 3: Simulate ───────────────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="simulate")
    def simulate(self, request, pk=None):
        """``POST /api/campaigns/v2/campaigns/{id}/simulate/``

        Read-only simulation: PlacementEngine V2 ile hedef kiosk+tarih
        kombinasyonlarını hesaplar; hiçbir tabloya yazma yapmaz.

        Response::

            {
              "campaign_id": "uuid",
              "fingerprint": "hex16",
              "target_kiosks": [1, 2],
              "date_range": ["2026-07-22", ...],
              "kiosk_days": [...],
              "total_requested": N,
              "total_placed": N,
              "total_unplaced": N,
              "would_succeed": true,
              "blocking_reasons": []
            }
        """
        from apps.campaigns.services.activation_service import ActivationService

        campaign = self.get_object()

        result = ActivationService.simulate(campaign)

        ser = SimulationResultSerializer(result)
        return Response(ser.data)

    # ── Faz 3: Activate ───────────────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        """``POST /api/campaigns/v2/campaigns/{id}/activate/``

        Kampanyayı V2 motoru ile aktive et.
        DOOH_ENGINE_V2=active gerektirir.

        GUARANTEED: all-or-nothing — herhangi bir hedef başarısızsa 409 döner.
        BEST_EFFORT: mevcut kapasiteye sığan hedefler aktive edilir.

        Response::

            {
              "campaign_id": "uuid",
              "planning_run_id": "uuid",
              "activated_kiosks": N,
              "activated_dates": N,
              "total_placements": N,
              "fingerprint": "hex16",
              "is_complete": true,
              "blocking_reasons": []
            }
        """
        from apps.campaigns.services.activation_service import (
            ActivationService,
            ActivationValidationError,
            CapacityError,
        )

        campaign = self.get_object()

        try:
            result = ActivationService.activate(campaign, user=request.user)
        except ActivationValidationError as exc:
            return Response(
                {"error": str(exc), "validation_errors": exc.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except CapacityError as exc:
            return Response(
                {"error": str(exc), "blocking_reasons": exc.blocking_reasons},
                status=status.HTTP_409_CONFLICT,
            )

        ser = ActivationResultSerializer(result)
        return Response(ser.data, status=status.HTTP_200_OK)


class CreativeViewSet(viewsets.ModelViewSet):
    queryset = Creative.objects.select_related("campaign").all()
    serializer_class = CreativeSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        cid = self.request.query_params.get("campaign")
        if cid:
            qs = qs.filter(campaign_id=cid)
        return qs

    def perform_create(self, serializer):
        instance = Creative(**serializer.validated_data)
        with UnitOfWork(user=self.request.user) as uow:
            uow.add(instance)
        serializer.instance = instance

    def perform_update(self, serializer):
        instance: Creative = serializer.instance
        for k, v in serializer.validated_data.items():
            setattr(instance, k, v)
        with UnitOfWork(user=self.request.user) as uow:
            uow.update(instance)

    def perform_destroy(self, instance):
        with UnitOfWork(user=self.request.user) as uow:
            uow.delete(instance)


class ScheduleRuleViewSet(viewsets.ModelViewSet):
    queryset = ScheduleRule.objects.select_related("campaign").all()
    serializer_class = ScheduleRuleSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def perform_create(self, serializer):
        instance = ScheduleRule(**serializer.validated_data)
        with UnitOfWork(user=self.request.user) as uow:
            uow.add(instance)
        serializer.instance = instance

    def perform_update(self, serializer):
        instance: ScheduleRule = serializer.instance
        for k, v in serializer.validated_data.items():
            setattr(instance, k, v)
        with UnitOfWork(user=self.request.user) as uow:
            uow.update(instance)

    def perform_destroy(self, instance):
        with UnitOfWork(user=self.request.user) as uow:
            uow.delete(instance)


class HouseAdViewSet(viewsets.ModelViewSet):
    queryset = HouseAd.objects.all()
    serializer_class = HouseAdSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def perform_create(self, serializer):
        instance = HouseAd(**serializer.validated_data)
        with UnitOfWork(user=self.request.user) as uow:
            uow.add(instance)
        serializer.instance = instance

    def perform_update(self, serializer):
        instance: HouseAd = serializer.instance
        for k, v in serializer.validated_data.items():
            setattr(instance, k, v)
        with UnitOfWork(user=self.request.user) as uow:
            uow.update(instance)

    def perform_destroy(self, instance):
        with UnitOfWork(user=self.request.user) as uow:
            uow.delete(instance)


class PricingMatrixView(APIView):
    """Singleton — GET tek satiri doner, PUT yeni satir / mevcut singleton'i gunceller."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def _get_or_default(self) -> PricingMatrix:
        instance = PricingMatrix.objects.filter(is_default=True).first()
        if instance is None:
            instance = PricingMatrix.objects.first()
        return instance

    def get(self, request):
        instance = self._get_or_default()
        if instance is None:
            return Response({})
        return Response(PricingMatrixSerializer(instance).data)

    def put(self, request):
        instance = self._get_or_default()
        serializer = PricingMatrixSerializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)

        if instance is None:
            new = PricingMatrix(**serializer.validated_data)
            with UnitOfWork(user=request.user) as uow:
                uow.add(new)
            return Response(PricingMatrixSerializer(new).data,
                            status=status.HTTP_201_CREATED)

        for k, v in serializer.validated_data.items():
            setattr(instance, k, v)
        with UnitOfWork(user=request.user) as uow:
            uow.update(instance)
        return Response(PricingMatrixSerializer(instance).data)

    def patch(self, request):
        instance = self._get_or_default()
        if instance is None:
            return Response({"error": "PricingMatrix tanimlanmamis. Once PUT ile olusturun."},
                            status=status.HTTP_404_NOT_FOUND)
        serializer = PricingMatrixSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for k, v in serializer.validated_data.items():
            setattr(instance, k, v)
        with UnitOfWork(user=request.user) as uow:
            uow.update(instance)
        return Response(PricingMatrixSerializer(instance).data)


class InventoryAvailabilityView(APIView):
    """``GET /api/inventory/availability/?date=YYYY-MM-DD&hour=18[&kiosk=<id>]``

    Belirli bir tarih+saat icin; tek kiosk veya tum kiosklar uzerinden ortalama
    musait reklam saniyesini doner.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        try:
            target_date = _parse_date(request.query_params.get("date"))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        hour_raw = request.query_params.get("hour")
        if hour_raw is None:
            return Response({"error": "hour parametresi zorunludur."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            hour = int(hour_raw)
        except ValueError:
            return Response({"error": "hour 0-23 olmalidir."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not 0 <= hour <= 23:
            return Response({"error": "hour 0-23 olmalidir."},
                            status=status.HTTP_400_BAD_REQUEST)

        kiosk_id = request.query_params.get("kiosk")
        if kiosk_id:
            kiosk = get_object_or_404(Kiosk, pk=kiosk_id)
            secs = available_seconds(kiosk, target_date, hour)
            return Response({
                "date": str(target_date),
                "hour": hour,
                "kiosk": int(kiosk.pk),
                "available_seconds": secs,
                "loop_duration_seconds": 60,
            })

        # Tum aktif kiosklar — toplam ve ortalama
        kiosks = list(Kiosk.objects.filter(aktif=True))
        if not kiosks:
            return Response({
                "date": str(target_date), "hour": hour,
                "available_seconds_total": 0,
                "available_seconds_avg": 0,
                "kiosk_count": 0,
            })
        per: list[int] = [available_seconds(k, target_date, hour) for k in kiosks]
        return Response({
            "date": str(target_date),
            "hour": hour,
            "kiosk_count": len(kiosks),
            "available_seconds_total": sum(per),
            "available_seconds_avg": sum(per) // len(per),
            "loop_duration_seconds": 60,
        })


# ─────────────────────────────────────────────────────────────────────────────
# DayPlan tabanlı Playlist üretimi (yardımcı)
# ─────────────────────────────────────────────────────────────────────────────


def _generate_from_day_plan(kiosk, target_date, day_plan) -> list:
    """DayPlan hiyerarşisini kullanarak bir kiosk için Playlist kayıtları üretir.

    DayPlan → HourPlan → PlaylistTemplate (LoopTemplate) → PlaylistItem zincirine
    göre her atanmış saat için bir Playlist üretir.

    Returns:
        Üretilen/güncellenen Playlist nesnelerinin listesi.
    """
    from django.db import transaction
    from apps.campaigns.models import (
        Creative, DayPlan as _DayPlan, HourPlan as _HourPlan,
        PlaylistTemplate as _PT, Playlist, PlaylistItem,
    )
    from django.db.models import Max

    # Mevcut max versiyon
    agg = Playlist.objects.filter(kiosk=kiosk, target_date=target_date).aggregate(mv=Max("version"))
    next_version = (agg["mv"] or 0) + 1

    produced = []
    hour_plan_cache: dict = {}
    loop_template_cache: dict = {}
    creative_cache: dict = {}

    with transaction.atomic():
        for slot in (day_plan.slots or []):
            hour = int(slot["hour"])
            hour_plan_id = str(slot["hour_plan_id"])

            # HourPlan yükle (önbellek)
            if hour_plan_id not in hour_plan_cache:
                try:
                    hour_plan_cache[hour_plan_id] = _HourPlan.objects.get(pk=hour_plan_id)
                except _HourPlan.DoesNotExist:
                    logger.warning("HourPlan bulunamadi: %s (saat %d atlanıyor)", hour_plan_id, hour)
                    continue
            hour_plan = hour_plan_cache[hour_plan_id]

            if not hour_plan.slots:
                continue

            # Saati temsil eden Playlist'i upsert et
            playlist, created = Playlist.objects.update_or_create(
                kiosk=kiosk,
                target_date=target_date,
                target_hour=hour,
                defaults={
                    "loop_duration_seconds": 60,
                    "version": next_version,
                },
            )
            if not created:
                playlist.version = next_version
                playlist.save(update_fields=["version"])

            # Eski PlaylistItem'ları temizle
            PlaylistItem.objects.filter(playlist=playlist).delete()

            # HourPlan'ın ilk slot'undaki LoopTemplate'den item'ları oluştur
            # (birden fazla slot varsa offset_minutes'e göre sırayla ekle)
            playback_order = 0
            cumulative_offset = 0

            for lslot in sorted(hour_plan.slots, key=lambda x: int(x.get("offset_minutes", 0))):
                loop_tpl_id = str(lslot["loop_template_id"])
                if loop_tpl_id not in loop_template_cache:
                    try:
                        loop_template_cache[loop_tpl_id] = _PT.objects.get(pk=loop_tpl_id)
                    except _PT.DoesNotExist:
                        logger.warning("LoopTemplate bulunamadi: %s", loop_tpl_id)
                        continue
                loop_tpl = loop_template_cache[loop_tpl_id]

                for item_slot in (loop_tpl.slots or []):
                    creative_id = item_slot.get("creative_id")
                    if not creative_id:
                        continue
                    if creative_id not in creative_cache:
                        try:
                            creative_cache[creative_id] = Creative.objects.get(pk=creative_id)
                        except Creative.DoesNotExist:
                            logger.warning("Creative bulunamadi: %s", creative_id)
                            continue
                    PlaylistItem.objects.create(
                        playlist=playlist,
                        creative=creative_cache[creative_id],
                        playback_order=playback_order,
                        estimated_start_offset_seconds=cumulative_offset,
                    )
                    playback_order += 1
                    cumulative_offset += int(item_slot.get("duration_seconds", 5))

            produced.append(playlist)

    return produced


class PlaylistGenerateView(APIView):
    """``POST /api/campaigns/v2/playlists/generate/``

    Admin panelden tetiklenen manuel playlist uretimi. Body::

        {
          "date": "2026-05-11",          # opsiyonel; verilmezse bugun
          "day_plan_id": "<uuid>",        # opsiyonel; DayPlan hiyerarsisi kullanilir
          "scope": "all"|"il"|"ilce"|"kiosks",  # opsiyonel; default "all"
          "il_id": 34,                   # scope="il" veya "ilce" ise zorunlu
          "ilce_id": 1020,               # scope="ilce" ise zorunlu
          "kiosk_ids": [1, 2, 3]         # scope="kiosks" ise zorunlu
        }
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        raw_date = request.data.get("date")
        try:
            if raw_date:
                target_date = _dt.datetime.strptime(raw_date, "%Y-%m-%d").date()
            else:
                target_date = timezone.now().date()
        except ValueError:
            return Response(
                {"error": f"Gecersiz tarih: {raw_date} (YYYY-MM-DD bekleniyor)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        day_plan_id = request.data.get("day_plan_id")
        day_plan = None
        if day_plan_id:
            try:
                day_plan = DayPlan.objects.get(pk=day_plan_id)
            except DayPlan.DoesNotExist:
                return Response(
                    {"error": f"DayPlan bulunamadi: {day_plan_id}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        scope      = request.data.get("scope", "all")
        il_id      = request.data.get("il_id")
        ilce_id    = request.data.get("ilce_id")
        kiosk_ids  = request.data.get("kiosk_ids")

        kiosks_qs = Kiosk.objects.filter(aktif=True).select_related("eczane")

        if scope == "il" and il_id is not None:
            kiosks_qs = kiosks_qs.filter(eczane__il_id=il_id)
        elif scope == "ilce" and ilce_id is not None:
            kiosks_qs = kiosks_qs.filter(eczane__ilce_id=ilce_id)
        elif scope == "kiosks" and kiosk_ids:
            kiosks_qs = kiosks_qs.filter(pk__in=kiosk_ids)

        kiosk_id = None  # kept for GenerationJob FK (NULL = multi-kiosk run)

        kiosks = list(kiosks_qs)

        # Faz 7: Async queue canonical — sadece PENDING job oluştur, worker bağımsız işler
        from apps.campaigns.services.invalidation_service import _create_or_coalesce_job
        created_jobs = []
        for k in kiosks:
            job_obj = _create_or_coalesce_job(k.id, target_date, "manual_generate")
            if job_obj:
                created_jobs.append(job_obj)

        first_job = created_jobs[0] if created_jobs else None
        return Response(
            {
                "job_id": str(first_job.pk) if first_job else None,
                "total_kiosks": len(kiosks),
                "target_date": str(target_date),
                "status": "PENDING",
                "queue_mode": True,
                "note": None if first_job else "Tum kiosklar icin is zaten kuyrukta.",
            },
            status=status.HTTP_202_ACCEPTED,
        )


# ─────────────────────────────────────────────────────────────────────────────
# GenerationJob izleme
# ─────────────────────────────────────────────────────────────────────────────


class GenerationJobView(APIView):
    """``GET /api/campaigns/v2/playlists/jobs/{id}/``

    İş durumunu sorgular. Admin panel progress bar için poll eder.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request, job_id: str):
        job = get_object_or_404(GenerationJob, pk=job_id)
        return Response(GenerationJobSerializer(job).data)


class GenerationJobListView(APIView):
    """``GET /api/campaigns/v2/playlists/jobs/``

    Son 50 generation job'ını listeler.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        qs = GenerationJob.objects.select_related("kiosk").order_by("-olusturulma_tarihi")[:50]
        return Response(GenerationJobSerializer(qs, many=True).data)


# ─────────────────────────────────────────────────────────────────────────────
# PlaylistTemplate CRUD
# ─────────────────────────────────────────────────────────────────────────────


class PlaylistTemplateViewSet(viewsets.ModelViewSet):
    """``/api/campaigns/v2/playlist-templates/``

    Elle tasarlanan 60sn loop şablonlarını yönetir.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]
    serializer_class = PlaylistTemplateSerializer
    queryset = PlaylistTemplate.objects.all().order_by("-olusturulma_tarihi")


# ─────────────────────────────────────────────────────────────────────────────
# HourPlan CRUD
# ─────────────────────────────────────────────────────────────────────────────


class HourPlanViewSet(viewsets.ModelViewSet):
    """``/api/campaigns/v2/hour-plans/``

    1 saatlik yayın planlarını yönetir. Her plan, sıralı LoopTemplate
    referanslarından oluşur.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]
    serializer_class = HourPlanSerializer
    queryset = HourPlan.objects.all().order_by("-olusturulma_tarihi")


# ─────────────────────────────────────────────────────────────────────────────
# DayPlan CRUD
# ─────────────────────────────────────────────────────────────────────────────


class DayPlanViewSet(viewsets.ModelViewSet):
    """``/api/campaigns/v2/day-plans/``

    24 saatlik günlük yayın planlarını yönetir. Her plan, 0-23 saatler için
    HourPlan ataması içerir.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]
    serializer_class = DayPlanSerializer
    queryset = DayPlan.objects.all().order_by("-olusturulma_tarihi")


# ─────────────────────────────────────────────────────────────────────────────
# Kiosk Edge API (App-Key + MAC)
# ─────────────────────────────────────────────────────────────────────────────



