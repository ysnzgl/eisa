"""DOOH sponsorluk yonetim API'si (JWT, SuperAdmin).

Tek motor (``services/sponsorship_engine``) uzerine kurulu yonetim uclari:
- ``campaigns/`` CRUD + bulk-action + ``{id}/kiosks/`` + ``{id}/assign-kiosks/``
- ``creatives/`` CRUD (kapasite yeniden dogrulama)
- ``idle-contents/`` CRUD
- ``sponsorship-kiosks/`` liste + ``{kiosk_id}/sponsorships|preview|copy|simulate/``
- ``playlists/jobs|day-stream|generate/`` ve ``pharmacy-campaigns/``.
"""
from __future__ import annotations

import datetime as _dt
import logging
import mimetypes
import uuid
import zoneinfo
from typing import List, Optional

from django.db import transaction
from django.db.models import Count, Q
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.uow import UnitOfWork
from apps.core.media_proxy import media_proxy_url
from apps.pharmacies.models import Kiosk
from apps.pharmacies.permissions import IsSuperAdmin, IsEczaci
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from .models import (
    Campaign,
    Creative,
    GenerationJob,
    IdleScreenContent,
    KioskSponsorship,
    PharmacyCampaign,
    Playlist,
)
from .serializers import (
    CampaignSerializer,
    CreativeSerializer,
    GenerationJobSerializer,
    IdleScreenContentSerializer,
    KioskSponsorshipItemSerializer,
    KioskSponsorshipReadSerializer,
    PharmacyCampaignFeedSerializer,
    PharmacyCampaignSerializer,
)
from .services import sponsorship_engine as engine
from .services.sponsorship_engine import hhmm_to_minute, second_to_hhmmss

logger = logging.getLogger(__name__)

_ISTANBUL_TZ = zoneinfo.ZoneInfo("Europe/Istanbul")


# ─────────────────────────────────────────────────────────────────────────────
# Yardimcilar
# ─────────────────────────────────────────────────────────────────────────────


def _parse_date(raw: Optional[str]) -> _dt.date:
    return _dt.datetime.strptime(raw, "%Y-%m-%d").date()


def _today_istanbul() -> _dt.date:
    return _dt.datetime.now(_ISTANBUL_TZ).date()


def _minute_to_hhmm(minute: int) -> str:
    minute = int(minute)
    return f"{minute // 60:02d}:{minute % 60:02d}"


def _capacity_response(detail: str, conflicts: List[dict], **extra) -> Response:
    body = {"code": "capacity_exceeded", "detail": detail, "conflicts": conflicts}
    body.update(extra)
    return Response(body, status=status.HTTP_400_BAD_REQUEST)


def engine_enqueue_campaign(campaign_id, reason: str) -> None:
    """Kampanya degisikligi sonrasi etkilenen kiosklari kuyruga al (best-effort)."""
    try:
        from .services.invalidation_service import enqueue_for_campaign
        enqueue_for_campaign(campaign_id, reason)
    except Exception:  # pragma: no cover
        logger.exception("enqueue_for_campaign basarisiz: %s", campaign_id)


class _DraftAssignment:
    """DB'ye yazilmamis atama — kapasite dogrulamasi / preview icin."""

    def __init__(self, campaign, window_start_minute, window_end_minute, count,
                 active_weekdays=None, start_date=None, end_date=None, is_active=True,
                 id=None):
        self.id = id or uuid.uuid4()
        self.campaign = campaign
        self.campaign_id = campaign.id
        self.window_start_minute = int(window_start_minute)
        self.window_end_minute = int(window_end_minute)
        self.count = int(count)
        self.active_weekdays = active_weekdays
        self.start_date = start_date
        self.end_date = end_date
        self.is_active = is_active


def _kiosk_summary(kiosk) -> dict:
    ecz = kiosk.eczane if kiosk.eczane_id else None
    return {
        "id": kiosk.id,
        "ad": kiosk.ad,
        "eczane_id": kiosk.eczane_id,
        "eczane_adi": ecz.ad if ecz else "",
        "il_adi": ecz.il.ad if ecz and ecz.il_id else "",
        "ilce_adi": ecz.ilce.ad if ecz and ecz.ilce_id else "",
        "aktif": kiosk.aktif,
        "is_online": kiosk.is_online,
        "son_goruldu": kiosk.son_goruldu,
    }


def _validate_campaign_assignments(campaign: Campaign, creatives_override=None) -> List[dict]:
    """Kampanyanin atandigi her kiosk icin kapasite dogrula; conflict listesi don."""
    conflicts: List[dict] = []
    kiosk_ids = (
        KioskSponsorship.objects.filter(campaign_id=campaign.id)
        .values_list("kiosk_id", flat=True).distinct()
    )
    for kid in kiosk_ids:
        assignments = list(
            KioskSponsorship.objects.filter(kiosk_id=kid).select_related("campaign")
        )
        for a in assignments:
            if a.campaign_id == campaign.id:
                a.campaign = campaign
        result = engine.validate_kiosk(kid, assignments, creatives_override=creatives_override)
        if not result.valid:
            conflicts.extend(result.conflicts)
            if len(conflicts) >= 20:
                break
    return conflicts


# ─────────────────────────────────────────────────────────────────────────────
# Campaign (Sponsorluk) CRUD
# ─────────────────────────────────────────────────────────────────────────────


class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.prefetch_related("creatives").all()
    serializer_class = CampaignSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        qs = super().get_queryset().annotate(
            _assigned_kiosk_count=Count("kiosk_sponsorships", distinct=True)
        )
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(advertiser_name__icontains=search))
        status_q = self.request.query_params.get("status")
        if status_q:
            qs = qs.filter(status=status_q)
        return qs.order_by("-olusturulma_tarihi")

    def perform_create(self, serializer):
        instance = Campaign(**serializer.validated_data)
        with UnitOfWork(user=self.request.user) as uow:
            uow.add(instance)
        serializer.instance = instance

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance: Campaign = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        resp = self._validate_campaign_capacity(instance, serializer.validated_data)
        if resp is not None:
            return resp
        for k, v in serializer.validated_data.items():
            setattr(instance, k, v)
        with UnitOfWork(user=self.request.user) as uow:
            uow.update(instance)
        engine_enqueue_campaign(instance.id, "campaign_update")
        return Response(self.get_serializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance: Campaign = self.get_object()
        campaign_id = instance.id
        with UnitOfWork(user=request.user) as uow:
            uow.delete(instance)
        engine_enqueue_campaign(campaign_id, "campaign_delete")
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _validate_campaign_capacity(self, instance: Campaign, changes: dict) -> Optional[Response]:
        status_after = changes.get("status", instance.status)
        if status_after != Campaign.Status.ACTIVE:
            return None
        tmp = Campaign(
            id=instance.id,
            name=changes.get("name", instance.name),
            advertiser_name=changes.get("advertiser_name", instance.advertiser_name),
            start_date=changes.get("start_date", instance.start_date),
            end_date=changes.get("end_date", instance.end_date),
            status=status_after,
        )
        conflicts = _validate_campaign_assignments(tmp)
        if conflicts:
            return _capacity_response(
                "Bu degisiklik atanmis kiosklarin kapasitesini asiyor.", conflicts
            )
        return None

    @action(detail=False, methods=["post"], url_path="bulk-action")
    def bulk_action(self, request):
        action_name = (request.data.get("action") or "").lower()
        ids = request.data.get("ids") or []
        if action_name == "activate":
            action_name = "resume"
        if action_name not in {"delete", "pause", "resume"}:
            return Response(
                {"error": "action must be one of: delete | pause | resume"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(ids, list) or not ids:
            return Response(
                {"error": "ids must be a non-empty array"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = Campaign.objects.filter(pk__in=ids)
        updated = 0
        affected: List = []
        with UnitOfWork(user=request.user) as uow:
            if action_name == "delete":
                for c in list(qs):
                    affected.append(c.id)
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
                    affected.append(c.id)
                    updated += 1
        for cid in affected:
            engine_enqueue_campaign(cid, f"bulk_{action_name}")
        return Response({"updated": updated, "action": action_name})

    @action(detail=True, methods=["get"], url_path="kiosks")
    def kiosks(self, request, pk=None):
        campaign = self.get_object()
        qs = (
            KioskSponsorship.objects
            .filter(campaign=campaign)
            .select_related("kiosk__eczane__il", "kiosk__eczane__ilce")
            .order_by("kiosk__ad")
        )
        return Response(KioskSponsorshipReadSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="assign-kiosks")
    def assign_kiosks(self, request, pk=None):
        campaign = self.get_object()
        kiosk_ids = request.data.get("kiosk_ids") or []
        if not isinstance(kiosk_ids, list) or not kiosk_ids:
            return Response({"error": "kiosk_ids zorunludur."}, status=status.HTTP_400_BAD_REQUEST)

        item_ser = KioskSponsorshipItemSerializer(data={
            "campaign_id": campaign.id,
            "window_start": request.data.get("window_start"),
            "window_end": request.data.get("window_end"),
            "count": request.data.get("count"),
            "active_weekdays": request.data.get("active_weekdays"),
            "start_date": request.data.get("start_date"),
            "end_date": request.data.get("end_date"),
            "is_active": request.data.get("is_active", True),
        })
        item_ser.is_valid(raise_exception=True)
        data = item_ser.validated_data
        dry_run = bool(request.data.get("dry_run", False))

        kiosks = {k.id: k for k in Kiosk.objects.filter(pk__in=kiosk_ids).select_related("eczane")}
        already = set(
            KioskSponsorship.objects
            .filter(campaign=campaign, kiosk_id__in=kiosk_ids)
            .values_list("kiosk_id", flat=True)
        )

        assigned: List[int] = []
        skipped: List[int] = [kid for kid in kiosk_ids if kid in already]
        rejected: List[dict] = []

        for kid in kiosk_ids:
            if kid in already:
                continue
            kiosk = kiosks.get(kid)
            if kiosk is None:
                continue
            existing = list(
                KioskSponsorship.objects.filter(kiosk_id=kid).select_related("campaign")
            )
            draft = _DraftAssignment(
                campaign=campaign,
                window_start_minute=data["window_start_minute"],
                window_end_minute=data["window_end_minute"],
                count=data["count"],
                active_weekdays=data.get("active_weekdays"),
                start_date=data.get("start_date"),
                end_date=data.get("end_date"),
                is_active=data.get("is_active", True),
            )
            result = engine.validate_kiosk(kid, existing + [draft])
            if not result.valid:
                rejected.append({
                    "kiosk_id": kid,
                    "kiosk_name": kiosk.ad,
                    "conflicts": result.conflicts,
                })
            else:
                assigned.append(kid)

        if rejected and not dry_run:
            return _capacity_response(
                "Bazi kiosklar kapasiteyi asiyor; hicbir sey kaydedilmedi.",
                [c for r in rejected for c in r["conflicts"]],
                rejected=rejected,
                skipped_already_assigned=skipped,
            )

        if not dry_run:
            with transaction.atomic():
                for kid in assigned:
                    KioskSponsorship.objects.create(
                        kiosk_id=kid,
                        campaign=campaign,
                        window_start_minute=data["window_start_minute"],
                        window_end_minute=data["window_end_minute"],
                        count=data["count"],
                        active_weekdays=data.get("active_weekdays"),
                        start_date=data.get("start_date"),
                        end_date=data.get("end_date"),
                        is_active=data.get("is_active", True),
                    )

        return Response({
            "assigned": assigned,
            "skipped_already_assigned": skipped,
            "rejected": rejected,
            "dry_run": dry_run,
        })


# ─────────────────────────────────────────────────────────────────────────────
# Creative CRUD
# ─────────────────────────────────────────────────────────────────────────────


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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campaign = serializer.validated_data["campaign"]
        instance = Creative(**serializer.validated_data)
        resp = self._capacity_guard_with(campaign, extra_creative=instance)
        if resp is not None:
            return resp
        with UnitOfWork(user=request.user) as uow:
            uow.add(instance)
        engine_enqueue_campaign(campaign.id, "creative_create")
        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance: Creative = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        patched = Creative(
            id=instance.id,
            campaign_id=instance.campaign_id,
            duration_seconds=serializer.validated_data.get("duration_seconds", instance.duration_seconds),
        )
        resp = self._capacity_guard_with(instance.campaign, replace_creative=patched)
        if resp is not None:
            return resp
        for k, v in serializer.validated_data.items():
            setattr(instance, k, v)
        with UnitOfWork(user=request.user) as uow:
            uow.update(instance)
        engine_enqueue_campaign(instance.campaign_id, "creative_update")
        return Response(self.get_serializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance: Creative = self.get_object()
        campaign = instance.campaign
        campaign_id = instance.campaign_id
        resp = self._capacity_guard_with(campaign, remove_creative_id=instance.id)
        if resp is not None:
            return resp
        with UnitOfWork(user=request.user) as uow:
            uow.delete(instance)
        engine_enqueue_campaign(campaign_id, "creative_delete")
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _capacity_guard_with(self, campaign, extra_creative=None,
                             replace_creative=None, remove_creative_id=None) -> Optional[Response]:
        creatives = list(
            Creative.objects.filter(campaign_id=campaign.id).order_by("olusturulma_tarihi", "id")
        )
        if remove_creative_id is not None:
            creatives = [c for c in creatives if c.id != remove_creative_id]
        if replace_creative is not None:
            creatives = [replace_creative if c.id == replace_creative.id else c for c in creatives]
        if extra_creative is not None:
            creatives = creatives + [extra_creative]
        conflicts = _validate_campaign_assignments(
            campaign, creatives_override={campaign.id: creatives}
        )
        if conflicts:
            return _capacity_response(
                "Bu creative degisikligi atanmis kiosklarin kapasitesini asiyor.", conflicts
            )
        return None

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        creative = self.get_object()
        object_key = creative.object_key
        if not object_key:
            return Response(
                {"error": "Bu creative icin object_key bulunamadi."},
                status=status.HTTP_404_NOT_FOUND,
            )
        from apps.core.services.storage_service import StorageService
        try:
            storage = StorageService()
            minio_resp = storage.client.get_object(storage.bucket_name, object_key)
        except Exception:
            logger.warning("Creative download: object not found key=%s id=%s", object_key, pk)
            return Response({"error": "Medya storage'da bulunamadi."}, status=status.HTTP_404_NOT_FOUND)

        filename = object_key.rsplit("/", 1)[-1]
        content_type, _ = mimetypes.guess_type(object_key)
        content_type = content_type or "application/octet-stream"

        def _stream():
            try:
                for chunk in minio_resp.stream(amt=65536):
                    yield chunk
            finally:
                minio_resp.close()
                minio_resp.release_conn()

        http_resp = StreamingHttpResponse(_stream(), content_type=content_type)
        http_resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return http_resp


# ─────────────────────────────────────────────────────────────────────────────
# IdleScreenContent CRUD
# ─────────────────────────────────────────────────────────────────────────────


class IdleScreenContentViewSet(viewsets.ModelViewSet):
    queryset = IdleScreenContent.objects.all()
    serializer_class = IdleScreenContentSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def perform_create(self, serializer):
        instance = IdleScreenContent(**serializer.validated_data)
        with UnitOfWork(user=self.request.user) as uow:
            uow.add(instance)
        serializer.instance = instance

    def perform_update(self, serializer):
        instance: IdleScreenContent = serializer.instance
        for k, v in serializer.validated_data.items():
            setattr(instance, k, v)
        with UnitOfWork(user=self.request.user) as uow:
            uow.update(instance)

    def perform_destroy(self, instance):
        with UnitOfWork(user=self.request.user) as uow:
            uow.delete(instance)


# ─────────────────────────────────────────────────────────────────────────────
# Kiosk-centric sponsorluk yonetimi
# ─────────────────────────────────────────────────────────────────────────────


class SponsorshipKioskListView(APIView):
    """``GET /api/campaigns/v2/sponsorship-kiosks/?search=&unassigned=1``"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        qs = (
            Kiosk.objects
            .select_related("eczane__il", "eczane__ilce")
            .annotate(
                sponsorship_count=Count("sponsorships", distinct=True),
                active_sponsorship_count=Count(
                    "sponsorships", filter=Q(sponsorships__is_active=True), distinct=True
                ),
            )
            .order_by("ad")
        )
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(Q(ad__icontains=search) | Q(eczane__ad__icontains=search))
        if request.query_params.get("unassigned") in ("1", "true", "True"):
            qs = qs.filter(sponsorship_count=0)

        data = []
        for k in qs:
            summary = _kiosk_summary(k)
            summary["sponsorship_count"] = k.sponsorship_count
            summary["active_sponsorship_count"] = k.active_sponsorship_count
            data.append(summary)
        return Response(data)


class SponsorshipKioskDetailView(APIView):
    """GET/PUT ``sponsorship-kiosks/{kiosk_id}/sponsorships/``"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def _get_kiosk(self, kiosk_id):
        return get_object_or_404(
            Kiosk.objects.select_related("eczane__il", "eczane__ilce"), pk=kiosk_id
        )

    def _items_payload(self, kiosk_id) -> List[dict]:
        rows = (
            KioskSponsorship.objects
            .filter(kiosk_id=kiosk_id)
            .select_related("campaign")
            .order_by("olusturulma_tarihi", "id")
        )
        camp_ids = [r.campaign_id for r in rows]
        creatives_by_campaign: dict = {}
        for c in Creative.objects.filter(campaign_id__in=camp_ids).order_by("olusturulma_tarihi", "id"):
            creatives_by_campaign.setdefault(c.campaign_id, []).append(c)
        items = []
        for r in rows:
            crs = creatives_by_campaign.get(r.campaign_id, [])
            items.append({
                "id": str(r.id),
                "campaign_id": str(r.campaign_id),
                "campaign_name": r.campaign.name,
                "advertiser_name": r.campaign.advertiser_name or "",
                "campaign_status": r.campaign.status,
                "campaign_start_date": r.campaign.start_date,
                "campaign_end_date": r.campaign.end_date,
                "creative_count": len(crs),
                "creative_durations": [c.duration_seconds for c in crs],
                "window_start": _minute_to_hhmm(r.window_start_minute),
                "window_end": _minute_to_hhmm(r.window_end_minute),
                "count": r.count,
                "active_weekdays": r.active_weekdays,
                "start_date": r.start_date,
                "end_date": r.end_date,
                "is_active": r.is_active,
            })
        return items

    def get(self, request, kiosk_id):
        kiosk = self._get_kiosk(kiosk_id)
        return Response({
            "kiosk": _kiosk_summary(kiosk),
            "items": self._items_payload(kiosk.id),
        })

    def put(self, request, kiosk_id):
        kiosk = self._get_kiosk(kiosk_id)
        raw_items = request.data.get("items", [])
        if not isinstance(raw_items, list):
            return Response({"error": "items liste olmalidir."}, status=status.HTTP_400_BAD_REQUEST)

        ser = KioskSponsorshipItemSerializer(data=raw_items, many=True)
        ser.is_valid(raise_exception=True)
        validated = ser.validated_data

        camp_ids = [v["campaign_id"] for v in validated]
        if len(camp_ids) != len(set(camp_ids)):
            return Response(
                {"error": "Ayni kampanya birden fazla kez atanamaz."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        campaigns = {c.id: c for c in Campaign.objects.filter(pk__in=camp_ids)}
        missing = [str(cid) for cid in camp_ids if cid not in campaigns]
        if missing:
            return Response(
                {"error": f"Kampanya bulunamadi: {', '.join(missing)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        drafts = [
            _DraftAssignment(
                campaign=campaigns[v["campaign_id"]],
                window_start_minute=v["window_start_minute"],
                window_end_minute=v["window_end_minute"],
                count=v["count"],
                active_weekdays=v.get("active_weekdays"),
                start_date=v.get("start_date"),
                end_date=v.get("end_date"),
                is_active=v.get("is_active", True),
            )
            for v in validated
        ]
        result = engine.validate_kiosk(kiosk.id, drafts)
        if not result.valid:
            return _capacity_response(
                "Bu atama kumesi kiosk kapasitesini asiyor.", result.conflicts
            )

        with transaction.atomic():
            KioskSponsorship.objects.filter(kiosk_id=kiosk.id).delete()
            for v in validated:
                KioskSponsorship.objects.create(
                    kiosk_id=kiosk.id,
                    campaign=campaigns[v["campaign_id"]],
                    window_start_minute=v["window_start_minute"],
                    window_end_minute=v["window_end_minute"],
                    count=v["count"],
                    active_weekdays=v.get("active_weekdays"),
                    start_date=v.get("start_date"),
                    end_date=v.get("end_date"),
                    is_active=v.get("is_active", True),
                )

        return Response({
            "kiosk": _kiosk_summary(kiosk),
            "items": self._items_payload(kiosk.id),
        })


class SponsorshipKioskPreviewView(APIView):
    """POST ``sponsorship-kiosks/{kiosk_id}/preview/`` (DB yazmaz)."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request, kiosk_id):
        kiosk = get_object_or_404(Kiosk, pk=kiosk_id)
        raw_date = request.data.get("date")
        try:
            target_date = _parse_date(raw_date) if raw_date else _today_istanbul()
        except (ValueError, TypeError):
            return Response({"error": "Gecersiz tarih (YYYY-MM-DD)."}, status=status.HTTP_400_BAD_REQUEST)

        raw_items = request.data.get("items", None)
        if raw_items is not None:
            ser = KioskSponsorshipItemSerializer(data=raw_items, many=True)
            ser.is_valid(raise_exception=True)
            validated = ser.validated_data
            camp_ids = [v["campaign_id"] for v in validated]
            campaigns = {c.id: c for c in Campaign.objects.filter(pk__in=camp_ids)}
            drafts = [
                _DraftAssignment(
                    campaign=campaigns[v["campaign_id"]],
                    window_start_minute=v["window_start_minute"],
                    window_end_minute=v["window_end_minute"],
                    count=v["count"],
                    active_weekdays=v.get("active_weekdays"),
                    start_date=v.get("start_date"),
                    end_date=v.get("end_date"),
                    is_active=v.get("is_active", True),
                )
                for v in validated if v["campaign_id"] in campaigns
            ]
            specs = engine.build_specs_for_date(kiosk.id, target_date, drafts)
        else:
            specs = engine.build_specs_for_date(kiosk.id, target_date)

        plan = engine.plan_day(target_date, specs)

        creative_ids = [it.creative_id for it in plan.items]
        creatives = {c.id: c for c in Creative.objects.filter(pk__in=creative_ids)}
        spec_by_campaign = {sp.campaign_id: sp for sp in specs}

        items_out = []
        for it in plan.items:
            cr = creatives.get(it.creative_id)
            sp = spec_by_campaign.get(it.campaign_id)
            items_out.append({
                "start": second_to_hhmmss(it.start_second),
                "end": second_to_hhmmss(it.start_second + it.duration),
                "start_second": it.start_second,
                "hour": it.hour,
                "offset": it.offset,
                "duration": it.duration,
                "campaign_id": str(it.campaign_id),
                "campaign_name": sp.campaign_name if sp else "",
                "advertiser_name": sp.advertiser_name if sp else "",
                "creative_id": str(it.creative_id),
                "creative_name": cr.name if cr else "",
                "media_url": (
                    media_proxy_url(cr.object_key, request) if cr and cr.object_key
                    else (cr.media_url if cr else "")
                ),
                "active_media_url": (
                    media_proxy_url(cr.active_object_key, request)
                    if cr and cr.active_object_key else (cr.active_media_url if cr else "")
                ),
            })

        hours_out = []
        for h in range(24):
            used = plan.hour_used_seconds[h]
            count = sum(1 for it in plan.items if it.hour == h)
            hours_out.append({
                "hour": h,
                "used_seconds": used,
                "item_count": count,
                "utilization": round(used / 3600.0, 4),
            })

        assignments_out = []
        for sp in specs:
            st = plan.assignment_stats.get(sp.key)
            assignments_out.append({
                "campaign_id": str(sp.campaign_id),
                "campaign_name": sp.campaign_name,
                "requested": st.requested if st else sp.count,
                "placed": st.placed if st else 0,
                "unplaced": st.unplaced if st else sp.count,
                "window_start": _minute_to_hhmm(sp.window_start_minute),
                "window_end": _minute_to_hhmm(sp.window_end_minute),
            })

        return Response({
            "kiosk_id": kiosk.id,
            "date": str(target_date),
            "ok": plan.ok,
            "fingerprint": plan.fingerprint,
            "total_used_seconds": sum(plan.hour_used_seconds),
            "items": items_out,
            "hours": hours_out,
            "assignments": assignments_out,
        })


class SponsorshipKioskCopyView(APIView):
    """POST ``sponsorship-kiosks/{kiosk_id}/copy/`` — OVERWRITE."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request, kiosk_id):
        source = get_object_or_404(Kiosk, pk=kiosk_id)
        target_ids = request.data.get("target_kiosk_ids") or []
        dry_run = bool(request.data.get("dry_run", False))
        if not isinstance(target_ids, list) or not target_ids:
            return Response({"error": "target_kiosk_ids zorunludur."}, status=status.HTTP_400_BAD_REQUEST)
        if source.id in target_ids:
            return Response(
                {"error": "Kaynak kiosk hedefler arasinda olamaz."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        source_specs = list(
            KioskSponsorship.objects.filter(kiosk_id=source.id).select_related("campaign")
        )
        source_campaign_names = [s.campaign.name for s in source_specs]
        targets = {k.id: k for k in Kiosk.objects.filter(pk__in=target_ids)}

        targets_out = []
        for tid in target_ids:
            tkiosk = targets.get(tid)
            if tkiosk is None:
                continue
            existing = list(
                KioskSponsorship.objects.filter(kiosk_id=tid).select_related("campaign")
            )
            existing_names = [e.campaign.name for e in existing]
            removed = [n for n in existing_names if n not in source_campaign_names]
            kept = [n for n in existing_names if n in source_campaign_names]
            added = [n for n in source_campaign_names if n not in existing_names]
            targets_out.append({
                "kiosk_id": tid,
                "kiosk_name": tkiosk.ad,
                "removed": removed,
                "added": added,
                "kept": kept,
            })

        if not dry_run:
            with transaction.atomic():
                for tid in target_ids:
                    if tid not in targets:
                        continue
                    KioskSponsorship.objects.filter(kiosk_id=tid).delete()
                    for s in source_specs:
                        KioskSponsorship.objects.create(
                            kiosk_id=tid,
                            campaign=s.campaign,
                            window_start_minute=s.window_start_minute,
                            window_end_minute=s.window_end_minute,
                            count=s.count,
                            active_weekdays=s.active_weekdays,
                            start_date=s.start_date,
                            end_date=s.end_date,
                            is_active=s.is_active,
                        )

        return Response({
            "dry_run": dry_run,
            "source_kiosk_id": source.id,
            "item_count": len(source_specs),
            "targets": targets_out,
        })


class SponsorshipKioskSimulateView(APIView):
    """POST ``sponsorship-kiosks/{kiosk_id}/simulate/`` — probe + senaryo."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request, kiosk_id):
        kiosk = get_object_or_404(Kiosk, pk=kiosk_id)
        today = _today_istanbul()
        try:
            date_from = _parse_date(request.data["date_from"]) if request.data.get("date_from") else today
            date_to = (
                _parse_date(request.data["date_to"]) if request.data.get("date_to")
                else today + _dt.timedelta(days=6)
            )
        except (ValueError, TypeError):
            return Response({"error": "Gecersiz tarih (YYYY-MM-DD)."}, status=status.HTTP_400_BAD_REQUEST)
        if date_to < date_from:
            return Response({"error": "date_to, date_from'dan once olamaz."}, status=status.HTTP_400_BAD_REQUEST)
        if (date_to - date_from).days > 92:
            return Response({"error": "Aralik en fazla 92 gun olabilir."}, status=status.HTTP_400_BAD_REQUEST)

        include_existing = bool(request.data.get("include_existing", True))

        probe_cfg = request.data.get("probe")
        probe_out = None
        if probe_cfg:
            try:
                ws = hhmm_to_minute(probe_cfg["window_start"])
                we = hhmm_to_minute(probe_cfg["window_end"], allow_2400=True)
            except (ValueError, KeyError):
                return Response({"error": "Gecersiz probe penceresi."}, status=status.HTTP_400_BAD_REQUEST)
            if we <= ws:
                return Response({"error": "probe window_end > window_start olmali."}, status=status.HTTP_400_BAD_REQUEST)
            probe_out = engine.probe_window(
                kiosk.id, date_from, date_to,
                duration_seconds=int(probe_cfg["duration_seconds"]),
                window_start_minute=ws, window_end_minute=we,
                active_weekdays=probe_cfg.get("active_weekdays"),
                include_existing=include_existing,
            )

        scenario_cfg = request.data.get("scenario") or []
        scenario_out = None
        if scenario_cfg:
            lines = []
            for line in scenario_cfg:
                try:
                    ws = hhmm_to_minute(line["window_start"])
                    we = hhmm_to_minute(line["window_end"], allow_2400=True)
                except (ValueError, KeyError):
                    return Response({"error": "Gecersiz senaryo penceresi."}, status=status.HTTP_400_BAD_REQUEST)
                lines.append({
                    "label": line.get("label", ""),
                    "duration_seconds": int(line["duration_seconds"]),
                    "count": int(line["count"]),
                    "window_start_minute": ws,
                    "window_end_minute": we,
                    "active_weekdays": line.get("active_weekdays"),
                })
            scenario_out = engine.simulate_scenario(
                kiosk.id, date_from, date_to, lines, include_existing=include_existing
            )

        return Response({
            "kiosk_id": kiosk.id,
            "date_from": str(date_from),
            "date_to": str(date_to),
            "probe": probe_out,
            "scenario": scenario_out,
        })


# ─────────────────────────────────────────────────────────────────────────────
# Playlist uretim / izleme
# ─────────────────────────────────────────────────────────────────────────────


class PlaylistGenerateView(APIView):
    """``POST /api/campaigns/v2/playlists/generate/`` — yeni motorla kuyruk uretimi."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        raw_date = request.data.get("date")
        try:
            target_date = _parse_date(raw_date) if raw_date else _today_istanbul()
        except (ValueError, TypeError):
            return Response(
                {"error": f"Gecersiz tarih: {raw_date} (YYYY-MM-DD bekleniyor)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        scope = request.data.get("scope", "all")
        il_id = request.data.get("il_id")
        ilce_id = request.data.get("ilce_id")
        kiosk_ids = request.data.get("kiosk_ids")

        kiosks_qs = Kiosk.objects.filter(aktif=True).select_related("eczane")
        if scope == "il" and il_id is not None:
            kiosks_qs = kiosks_qs.filter(eczane__il_id=il_id)
        elif scope == "ilce" and ilce_id is not None:
            kiosks_qs = kiosks_qs.filter(eczane__ilce_id=ilce_id)
        elif scope == "kiosks" and kiosk_ids:
            kiosks_qs = kiosks_qs.filter(pk__in=kiosk_ids)

        kiosks = list(kiosks_qs)

        from apps.campaigns.services.invalidation_service import _create_or_coalesce_job
        created_jobs = []
        for k in kiosks:
            job_obj = _create_or_coalesce_job(k.id, target_date, "manual_generate")
            if job_obj:
                created_jobs.append(job_obj)

        from apps.campaigns.services.queue_worker import drain_queue
        processed = 0
        try:
            processed = drain_queue(max_jobs=max(20, len(created_jobs)))
        except Exception:
            logger.exception("PlaylistGenerateView: senkron drain_queue basarisiz")

        first_job = created_jobs[0] if created_jobs else None
        return Response(
            {
                "job_id": str(first_job.pk) if first_job else None,
                "total_kiosks": len(kiosks),
                "target_date": str(target_date),
                "processed": processed,
                "status": "DONE" if processed else "PENDING",
                "queue_mode": True,
                "note": None if first_job else "Tum kiosklar icin is zaten kuyrukta.",
            },
            status=status.HTTP_202_ACCEPTED,
        )


class GenerationJobView(APIView):
    """``GET /api/campaigns/v2/playlists/jobs/{id}/``"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request, job_id: str):
        job = get_object_or_404(GenerationJob, pk=job_id)
        return Response(GenerationJobSerializer(job).data)


class GenerationJobListView(APIView):
    """``GET /api/campaigns/v2/playlists/jobs/``"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        qs = GenerationJob.objects.select_related("kiosk").order_by("-olusturulma_tarihi")[:50]
        return Response(GenerationJobSerializer(qs, many=True).data)


class KioskDayStreamView(APIView):
    """``GET /api/campaigns/v2/playlists/day-stream/?kiosk=&date=`` — yayindaki plan."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        kiosk_id = request.query_params.get("kiosk")
        raw_date = request.query_params.get("date")
        if not kiosk_id:
            return Response({"error": "kiosk parametresi zorunludur."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            target_date = _parse_date(raw_date) if raw_date else _today_istanbul()
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        kiosk = get_object_or_404(Kiosk.objects.select_related("eczane"), pk=kiosk_id)

        playlists = (
            Playlist.objects
            .filter(kiosk_id=kiosk_id, target_date=target_date)
            .prefetch_related("items__creative__campaign")
            .order_by("target_hour")
        )

        hours_data = []
        for pl in playlists:
            items_data = []
            for item in pl.items.all():
                if not item.creative_id:
                    continue
                media_url = (
                    media_proxy_url(item.creative.object_key, request)
                    if item.creative.object_key else item.creative.media_url
                )
                active_media_url = (
                    media_proxy_url(item.creative.active_object_key, request)
                    if item.creative.active_object_key else item.creative.active_media_url or ""
                )
                name = item.creative.campaign.name if item.creative.campaign_id else item.creative.name
                items_data.append({
                    "id": str(item.id),
                    "asset_id": str(item.creative_id),
                    "asset_type": "creative",
                    "name": name,
                    "media_url": media_url,
                    "active_media_url": active_media_url,
                    "duration_seconds": item.creative.duration_seconds,
                    "playback_order": item.playback_order,
                    "estimated_start_offset_seconds": item.estimated_start_offset_seconds,
                })
            hours_data.append({
                "target_hour": pl.target_hour,
                "version": pl.version,
                "loop_duration_seconds": pl.loop_duration_seconds,
                "items": items_data,
            })

        return Response({
            "kiosk_id": kiosk.id,
            "kiosk_name": kiosk.ad,
            "is_online": kiosk.is_online,
            "son_goruldu": kiosk.son_goruldu,
            "last_playlist_version": kiosk.last_playlist_version,
            "desired_version": kiosk.last_playlist_version,
            "applied_version": kiosk.applied_playlist_version,
            "applied_horizon_end": kiosk.applied_horizon_end,
            "playlist_applied_at": kiosk.playlist_applied_at,
            "target_date": str(target_date),
            "hours": hours_data,
        })


# ─────────────────────────────────────────────────────────────────────────────
# PharmacyCampaign — eczaci paneli (dokunulmadi)
# ─────────────────────────────────────────────────────────────────────────────


class PharmacyCampaignViewSet(viewsets.ModelViewSet):
    """``/api/campaigns/v2/pharmacy-campaigns/`` — Admin CRUD + eczaci feed."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]
    serializer_class = PharmacyCampaignSerializer
    queryset = PharmacyCampaign.objects.prefetch_related("target_pharmacies").order_by("-olusturulma_tarihi")

    @action(detail=False, methods=["get"], permission_classes=[IsEczaci], url_path="feed")
    def feed(self, request):
        from apps.pharmacies.models import Eczane as EczaneModel
        eczane_id = getattr(request.user, "eczane_id", None)
        if not eczane_id:
            return Response([], status=status.HTTP_200_OK)
        try:
            eczane = EczaneModel.objects.values("il_id", "ilce_id").get(pk=eczane_id)
        except EczaneModel.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)

        il_id = eczane["il_id"]
        ilce_id = eczane["ilce_id"]
        now = timezone.now()
        base_qs = PharmacyCampaign.objects.filter(
            is_active=True, start_at__lte=now, end_at__gte=now,
        )
        match_q = (
            Q(target_pharmacies__id=eczane_id)
            | Q(target_iller__id=il_id)
            | Q(target_ilceler__id=ilce_id)
        )
        qs = base_qs.filter(match_q).distinct()
        return Response(PharmacyCampaignFeedSerializer(qs, many=True).data)
