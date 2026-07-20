"""Kiosk API facade — view'ler.

Kiosk <-> Main API operasyonel yuzeyinin tamami burada toplanir. Domain
modelleri ve serializer'lari YENIDEN KULLANILIR; is mantigi kopyalanmaz
(oturum yazma, katalog ve diagnostic mantigi ilgili domain servislerine
delege edilir).

Namespace: /api/kiosk/v1/  (kiosk ID URL'de YOK; kiosk auth context'ten gelir).
"""
from __future__ import annotations

import datetime as _dt
import re

from django.conf import settings
from django.db.models import F, Max
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.analytics.log_ingest import MAX_BATCH_ITEMS, ingest_kiosk_diagnostic_items
from apps.analytics.services import ingest_session_items
from apps.campaigns.models import Campaign, Creative, HouseAd, PlayLog, Playlist
from apps.campaigns.serializers import (
    KioskCreativeSyncSerializer,
    KioskHouseAdSyncSerializer,
    KioskPlaylistSerializer,
    ProofOfPlayBulkSerializer,
)
from apps.lookups.models import Cinsiyet, Il, Ilce, YasAraligi
from apps.pharmacies.auth import (
    check_fleet_key,
    is_timestamp_fresh,
    normalize_mac,
    verify_provision_hmac,
)
from apps.pharmacies.models import Kiosk, KioskProvisioningRequest
from apps.products.services import build_catalog_payload

from .mixins import KioskAPIView

_MAC_RE = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$")
_PROVISIONING_RETRY_AFTER = 30  # saniye


def _parse_date(raw):
    if not raw:
        return timezone.now().date()
    try:
        return _dt.date.fromisoformat(str(raw))
    except ValueError as exc:
        raise ValueError("Gecersiz tarih formati (YYYY-MM-DD bekleniyor).") from exc


# ── Bootstrap / Provisioning ─────────────────────────────────────────────────

def _approved_response(kiosk: Kiosk) -> dict:
    """Onayli + aktif + eczaneli kiosk icin App Key contract'i.

    App Key URETILMEZ. Mevcut ``uygulama_anahtari`` alanindan gelir;
    ayni kiosk tekrar bootstrap yaptiginda AYNI key doner (rotasyon yok).
    """
    return {
        "status": "APPROVED",
        "kiosk_id": kiosk.pk,
        "pharmacy_id": kiosk.eczane_id,
        "app_key": kiosk.uygulama_anahtari,
    }


def _pending_response(provision_req) -> dict:
    return {
        "status": "PENDING",
        "registration_id": str(provision_req.id),
        "retry_after_seconds": _PROVISIONING_RETRY_AFTER,
    }


class KioskBootstrapView(APIView):
    """``POST /api/kiosk/v1/bootstrap/`` — provisioning giris noktasi.

    Fleet Key + HMAC + timestamp ile dogrulanir (App Key auth KULLANILMAZ).
    Onayli+aktif+eczaneli kiosk icin App Key doner.

    Yanitlar:
      200 APPROVED — {status, kiosk_id, pharmacy_id, app_key}
      202 PENDING  — {status, registration_id, retry_after_seconds}
      403 REJECTED — {status}
      401          — fleet key veya HMAC gecersiz
      400          — eksik/hatali format
      503          — sunucu yapilandirmasi eksik
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        fleet_key = getattr(settings, "KIOSK_FLEET_KEY", "") or ""
        provisioning_secret = getattr(settings, "KIOSK_PROVISIONING_SECRET", "") or ""
        if not fleet_key or not provisioning_secret:
            return Response(
                {"detail": "Kiosk provision devre disi (sunucu ayarlari eksik)."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # 1) Fleet key (hangi credential eksik oldugu response'ta belirtilmez)
        if not check_fleet_key(request):
            return Response({"detail": "Kimlik dogrulanamadi."}, status=status.HTTP_401_UNAUTHORIZED)

        # 2) Body alanlari
        raw_mac = request.data.get("mac_adresi") or request.headers.get("X-Kiosk-MAC", "")
        mac = normalize_mac(raw_mac)
        timestamp = (request.data.get("timestamp") or "").strip()
        received_hmac = (request.data.get("hmac") or "").strip()

        if not _MAC_RE.match(mac):
            return Response({"detail": "Gecersiz MAC adresi."}, status=status.HTTP_400_BAD_REQUEST)
        if not timestamp or not received_hmac:
            return Response(
                {"detail": "timestamp ve hmac alanlari zorunludur."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3) Timestamp tazelik (replay koruyu, +/- 5 dk)
        if not is_timestamp_fresh(timestamp):
            return Response(
                {"detail": "Timestamp gecersiz veya suresi dolmus (max +/-5 dk)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 4) HMAC (hangi credential hatali oldugu belirtilmez)
        if not verify_provision_hmac(mac, timestamp, received_hmac, provisioning_secret):
            return Response({"detail": "Kimlik dogrulanamadi."}, status=status.HTTP_401_UNAUTHORIZED)

        # 5) Aktif kayitli kiosk var mi? -> App Key ver
        kiosk = (
            Kiosk.objects.select_related("eczane")
            .filter(aktif=True, mac_adresi__iexact=mac)
            .first()
        )
        if kiosk:
            return Response(_approved_response(kiosk), status=status.HTTP_200_OK)

        # 6) Provision talebi kontrol/olustur (kimlik dogrulamasi gecti)
        now = timezone.now()
        hostname = (request.data.get("hostname") or "").strip()[:255]
        raw_metadata = request.data.get("device_metadata") or {}
        if isinstance(raw_metadata, dict):
            device_metadata = {
                k: v for k, v in raw_metadata.items()
                if k not in ("iot_token", "token", "secret", "hmac", "authorization", "app_key")
            }
        else:
            device_metadata = {}

        provision_req = (
            KioskProvisioningRequest.objects
            .filter(mac_adresi__iexact=mac)
            .order_by("-olusturulma_tarihi")
            .first()
        )

        if provision_req:
            if provision_req.status == KioskProvisioningRequest.Status.APPROVED:
                linked = provision_req.kiosk
                if linked and linked.aktif:
                    return Response(_approved_response(linked), status=status.HTTP_200_OK)
                # Kiosk silinmis/pasif — PENDING'e geri don
                KioskProvisioningRequest.objects.filter(pk=provision_req.pk).update(
                    status=KioskProvisioningRequest.Status.PENDING,
                    last_seen_at=now,
                    request_count=F("request_count") + 1,
                )
                provision_req.refresh_from_db()
                return Response(_pending_response(provision_req), status=status.HTTP_202_ACCEPTED)

            if provision_req.status == KioskProvisioningRequest.Status.REJECTED:
                return Response({"status": "REJECTED"}, status=status.HTTP_403_FORBIDDEN)

            # PENDING: idempotent guncelleme
            KioskProvisioningRequest.objects.filter(pk=provision_req.pk).update(
                last_seen_at=now,
                request_count=F("request_count") + 1,
                hostname=hostname or provision_req.hostname,
                device_metadata=device_metadata or provision_req.device_metadata,
            )
            return Response(_pending_response(provision_req), status=status.HTTP_202_ACCEPTED)

        # Yeni cihaz — PENDING kayit olustur
        try:
            provision_req = KioskProvisioningRequest(
                mac_adresi=mac,
                hostname=hostname,
                device_metadata=device_metadata,
                status=KioskProvisioningRequest.Status.PENDING,
                last_seen_at=now,
                request_count=1,
            )
            provision_req.save()
        except Exception:  # es-zamanli istek zaten olusturmus olabilir
            provision_req = (
                KioskProvisioningRequest.objects
                .filter(mac_adresi__iexact=mac)
                .order_by("-olusturulma_tarihi")
                .first()
            )
            if provision_req:
                KioskProvisioningRequest.objects.filter(pk=provision_req.pk).update(
                    last_seen_at=now, request_count=F("request_count") + 1,
                )
            else:
                return Response(
                    {"detail": "Provision talebi olusturulamadi, daha sonra tekrar deneyin."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
        return Response(_pending_response(provision_req), status=status.HTTP_202_ACCEPTED)


# ── Operasyonel endpoint'ler (AppKey + MAC) ──────────────────────────────────

class KioskPingView(KioskAPIView):
    """``GET /api/kiosk/v1/ping/`` — heartbeat + bugunun playlist versiyonu."""

    def get(self, request):
        kiosk = self.kiosk
        now = timezone.now()
        today = now.date()
        agg = (
            Playlist.objects
            .filter(kiosk=kiosk, target_date=today)
            .aggregate(max_version=Max("version"), max_updated=Max("guncellenme_tarihi"))
        )
        Kiosk.objects.filter(pk=kiosk.pk).update(son_goruldu=now, is_online=True)
        return Response({
            "kiosk_id": int(kiosk.pk),
            "date": str(today),
            "playlist_version": agg["max_version"] or 0,
            "updated_at": agg["max_updated"].isoformat() if agg["max_updated"] else None,
            "server_time": now.isoformat(),
        })


class KioskSyncView(KioskAPIView):
    """``GET /api/kiosk/v1/sync/`` — aktif creative + house_ad + lookup listesi."""

    def get(self, request):
        kiosk = self.kiosk
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
            "lookups": {
                "cinsiyetler": list(Cinsiyet.objects.values("id", "kod", "ad").order_by("id")),
                "yas_araliklari": list(YasAraligi.objects.values("id", "kod", "ad", "alt_sinir", "ust_sinir").order_by("id")),
                "iller": list(Il.objects.values("id", "ad").order_by("ad")),
                "ilceler": list(Ilce.objects.values("id", "il_id", "ad").order_by("il_id", "ad")),
            },
        })


class KioskCatalogView(KioskAPIView):
    """``GET /api/kiosk/v1/catalog/`` — kategori/soru/cevap/etken madde/danisma."""

    def get(self, request):
        return Response(build_catalog_payload())


class KioskPlaylistView(KioskAPIView):
    """``GET /api/kiosk/v1/playlist/?date=YYYY-MM-DD`` — gunun 24 saatlik playlist'i."""

    def get(self, request):
        try:
            target_date = _parse_date(request.query_params.get("date"))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        kiosk = self.kiosk
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


class KioskSessionsView(KioskAPIView):
    """``POST /api/kiosk/v1/sessions/`` — oturum outbox toplu-yazma (idempotent)."""

    def post(self, request):
        items = request.data.get("items", [])
        if not isinstance(items, list):
            return Response({"detail": "'items' alani bir liste olmalidir."},
                            status=status.HTTP_400_BAD_REQUEST)
        accepted, errors = ingest_session_items(self.kiosk, items)
        return_status = status.HTTP_207_MULTI_STATUS if errors else status.HTTP_200_OK
        return Response(
            {"accepted": len(accepted), "accepted_keys": accepted, "errors": errors},
            status=return_status,
        )


class KioskProofOfPlayView(KioskAPIView):
    """``POST /api/kiosk/v1/proof-of-play/`` — reklam gosterim (PlayLog) toplu-yazma."""

    def post(self, request):
        kiosk = self.kiosk
        serializer = ProofOfPlayBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        logs_data = serializer.validated_data["logs"]

        bulk = [
            PlayLog(
                kiosk=kiosk,
                creative_id=entry.get("creative_id"),
                house_ad_id=entry.get("house_ad_id"),
                played_at=entry["played_at"],
                duration_played=entry["duration_played"],
            )
            for entry in logs_data
        ]
        if bulk:
            PlayLog.objects.bulk_create(bulk, batch_size=500)
        Kiosk.objects.filter(pk=kiosk.pk).update(son_goruldu=timezone.now())
        return Response({"ingested": len(bulk)}, status=status.HTTP_201_CREATED)


class KioskDiagnosticsView(KioskAPIView):
    """``POST /api/kiosk/v1/diagnostics/`` — diagnostic outbox (DB'ye yazilmaz)."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "kiosk_diagnostic"

    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        items = payload.get("items")
        if not isinstance(items, list) or not items:
            return Response({"detail": "`items` bos olmayan bir liste olmali."},
                            status=status.HTTP_400_BAD_REQUEST)
        if len(items) > MAX_BATCH_ITEMS:
            return Response(
                {"detail": f"Batch en fazla {MAX_BATCH_ITEMS} kayit icerebilir."},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
        result = ingest_kiosk_diagnostic_items(self.kiosk, items)
        return Response(result, status=status.HTTP_202_ACCEPTED)
