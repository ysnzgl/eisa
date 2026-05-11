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
    GET    /api/kiosk/v1/{kiosk_id}/sync/                -> tum aktif creative + house_ad listesi
    GET    /api/kiosk/v1/{kiosk_id}/playlist/?date=YYYY-MM-DD
    POST   /api/kiosk/v1/{kiosk_id}/proof-of-play/       -> bulk PlayLog ingest
"""
from __future__ import annotations

import datetime as _dt
import logging
from typing import Iterable

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.uow import UnitOfWork
from apps.pharmacies.auth import KioskAppKeyAuthentication
from apps.pharmacies.models import Kiosk
from apps.pharmacies.permissions import IsKiosk, IsSuperAdmin
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from .models import (
    Campaign,
    CampaignTarget,
    Creative,
    HouseAd,
    PlayLog,
    Playlist,
    PricingMatrix,
    ScheduleRule,
)
from .serializers import (
    CampaignSerializer,
    CampaignTargetSerializer,
    CreativeSerializer,
    HouseAdSerializer,
    KioskCreativeSyncSerializer,
    KioskHouseAdSyncSerializer,
    KioskPlaylistSerializer,
    PlaylistAdminSerializer,
    PricingMatrixSerializer,
    ProofOfPlayBulkSerializer,
    ScheduleRuleSerializer,
)
from .services.scheduler import available_seconds, generate_for_kiosk, simulate_campaign_capacity

logger = logging.getLogger(__name__)


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
        "creatives", "target_pharmacies", "targets__il", "targets__ilce", "targets__eczane"
    ).select_related("schedule_rule")
    serializer_class = CampaignSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def perform_create(self, serializer):
        targets = serializer.validated_data.pop("target_pharmacies", [])
        instance = Campaign(**serializer.validated_data)
        with UnitOfWork(user=self.request.user) as uow:
            uow.add(instance)
            instance.target_pharmacies.set(targets)
        serializer.instance = instance

    def perform_update(self, serializer):
        instance: Campaign = serializer.instance
        targets = serializer.validated_data.pop("target_pharmacies", None)
        for k, v in serializer.validated_data.items():
            setattr(instance, k, v)
        with UnitOfWork(user=self.request.user) as uow:
            uow.update(instance)
            if targets is not None:
                instance.target_pharmacies.set(targets)

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


class PlaylistGenerateView(APIView):
    """``POST /api/campaigns/v2/playlists/generate/``

    Admin panelden tetiklenen manuel playlist uretimi. Body opsiyonel::

        { "date": "2026-05-11", "kiosk": 12 }

    - ``date`` verilmezse YARIN (UTC) varsayilir.
    - ``kiosk`` verilmezse TUM aktif kiosklar icin uretim yapilir.
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

        kiosk_id = request.data.get("kiosk")
        kiosks_qs = Kiosk.objects.filter(aktif=True)
        if kiosk_id is not None:
            kiosks_qs = kiosks_qs.filter(pk=kiosk_id)
            if not kiosks_qs.exists():
                return Response(
                    {"error": f"Aktif kiosk bulunamadi: {kiosk_id}"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        results = []
        total = 0
        for kiosk in kiosks_qs:
            try:
                playlists = generate_for_kiosk(kiosk, target_date)
            except Exception as exc:
                logger.exception("Playlist uretimi basarisiz kiosk=%s", kiosk.pk)
                results.append({
                    "kiosk_id": int(kiosk.pk),
                    "ok": False,
                    "error": str(exc),
                    "playlists": 0,
                })
                continue
            total += len(playlists)
            results.append({
                "kiosk_id": int(kiosk.pk),
                "ok": True,
                "playlists": len(playlists),
            })

        return Response({
            "target_date": str(target_date),
            "kiosk_count": len(results),
            "playlists_generated": total,
            "results": results,
        }, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# Kiosk Edge API (App-Key + MAC)
# ─────────────────────────────────────────────────────────────────────────────


def _ensure_kiosk_match(request, kiosk_id: int) -> Response | None:
    """Authenticated kiosk request.user; URL'deki id ile eslesmeli."""
    auth_kiosk: Kiosk = request.user
    if not isinstance(auth_kiosk, Kiosk) or int(auth_kiosk.pk) != int(kiosk_id):
        return Response({"error": "Kiosk kimligi URL ile eslesmiyor."},
                        status=status.HTTP_403_FORBIDDEN)
    return None


class KioskSyncView(APIView):
    """``GET /api/kiosk/v1/{kiosk_id}/sync/``

    Bu kiosku ilgilendiren TUM aktif creative + tum aktif house_ad listesini doner.
    Kiosk bunlari local storage'a indirir ve hash ile cache'ler.
    """

    authentication_classes = [KioskAppKeyAuthentication]
    permission_classes = [IsKiosk]

    def get(self, request, kiosk_id):
        guard = _ensure_kiosk_match(request, kiosk_id)
        if guard is not None:
            return guard
        kiosk: Kiosk = request.user
        now = timezone.now()
        eczane_id = kiosk.eczane_id

        creatives_qs = (
            Creative.objects
            .select_related("campaign")
            .filter(
                campaign__status=Campaign.Status.ACTIVE,
                campaign__start_date__lte=now,
                campaign__end_date__gte=now,
            )
        )
        # Hedef eczane filtresi (bos liste = herkese)
        creative_payload: list[dict] = []
        for c in creatives_qs:
            targets = c.campaign.target_pharmacies.all()
            if targets.exists() and not targets.filter(pk=eczane_id).exists():
                continue
            creative_payload.append(KioskCreativeSyncSerializer(c).data)

        house_ads = HouseAd.objects.filter(aktif=True)
        return Response({
            "kiosk_id": int(kiosk.pk),
            "generated_at": now.isoformat(),
            "creatives": creative_payload,
            "house_ads": KioskHouseAdSyncSerializer(house_ads, many=True).data,
        })


class KioskPlaylistView(APIView):
    """``GET /api/kiosk/v1/{kiosk_id}/playlist/?date=YYYY-MM-DD``

    Ilgili gunun 24 saatlik playlist'lerini siralayarak doner.
    """

    authentication_classes = [KioskAppKeyAuthentication]
    permission_classes = [IsKiosk]

    def get(self, request, kiosk_id):
        guard = _ensure_kiosk_match(request, kiosk_id)
        if guard is not None:
            return guard
        try:
            target_date = _parse_date(request.query_params.get("date"))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        kiosk: Kiosk = request.user
        playlists = (
            Playlist.objects
            .filter(kiosk=kiosk, target_date=target_date)
            .order_by("target_hour")
            .prefetch_related("items__creative", "items__house_ad")
        )
        return Response({
            "kiosk_id": int(kiosk.pk),
            "target_date": str(target_date),
            "loop_duration_seconds": 60,
            "playlists": KioskPlaylistSerializer(playlists, many=True).data,
        })


class KioskPingView(APIView):
    """``GET /api/kiosk/v1/{kiosk_id}/ping/``

    Heartbeat (Ping-Pong) endpoint. Kiosk bu endpoint'i periyodik olarak cagirir.
    Yanit olarak o kiosk icin bugunun playlist versiyon numarasini doner.

    Kiosk, kendi versiyonu ile gelen versiyonu karsilastirir:
      - Eger yeni versiyon varsa => /playlist/ endpoint'ini cagirarak
        guncellenmis playlist'i indirir (Delta Sync).
      - Ayni versiyon ise => hicbir islem yapmaz, yerel playlist'i oynatir.

    Yani doner::

        {
          "kiosk_id": 12,
          "date": "2026-05-15",
          "playlist_version": 7,
          "updated_at": "2026-05-15T03:00:00Z",
          "server_time": "2026-05-15T14:22:01Z"
        }
    """

    authentication_classes = [KioskAppKeyAuthentication]
    permission_classes = [IsKiosk]

    def get(self, request, kiosk_id):
        guard = _ensure_kiosk_match(request, kiosk_id)
        if guard is not None:
            return guard
        kiosk: Kiosk = request.user
        now = timezone.now()
        today = now.date()

        # Bugunun playlist versiyonunu doner (en guncellenmis saat'in versiyonu)
        from django.db.models import Max
        agg = (
            Playlist.objects
            .filter(kiosk=kiosk, target_date=today)
            .aggregate(max_version=Max("version"), max_updated=Max("guncellenme_tarihi"))
        )

        # Kiosun son-goruldu zamanini guncelle (heartbeat kaydı)
        Kiosk.objects.filter(pk=kiosk.pk).update(son_goruldu=now)

        return Response({
            "kiosk_id": int(kiosk.pk),
            "date": str(today),
            "playlist_version": agg["max_version"] or 0,
            "updated_at": agg["max_updated"].isoformat() if agg["max_updated"] else None,
            "server_time": now.isoformat(),
        })


class ProofOfPlayView(APIView):
    """``POST /api/kiosk/v1/{kiosk_id}/proof-of-play/`` (bulk ingest).

    Body::

        { "logs": [
            {"creative_id": "<uuid>", "played_at": "2026-...Z", "duration_played": 15},
            {"house_ad_id": "<uuid>", "played_at": "2026-...Z", "duration_played": 10}
        ]}
    """

    authentication_classes = [KioskAppKeyAuthentication]
    permission_classes = [IsKiosk]

    def post(self, request, kiosk_id):
        guard = _ensure_kiosk_match(request, kiosk_id)
        if guard is not None:
            return guard
        kiosk: Kiosk = request.user

        serializer = ProofOfPlayBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        logs_data = serializer.validated_data["logs"]

        bulk = []
        for entry in logs_data:
            bulk.append(PlayLog(
                kiosk=kiosk,
                creative_id=entry.get("creative_id"),
                house_ad_id=entry.get("house_ad_id"),
                played_at=entry["played_at"],
                duration_played=entry["duration_played"],
            ))
        if bulk:
            PlayLog.objects.bulk_create(bulk, batch_size=500)

        # Kiosku canli olarak isaretle
        Kiosk.objects.filter(pk=kiosk.pk).update(son_goruldu=timezone.now())

        return Response({"ingested": len(bulk)}, status=status.HTTP_201_CREATED)
