"""Kiosk API facade â€” view'ler.

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
from django.db import transaction
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


# â”€â”€ Bootstrap / Provisioning â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
    """``POST /api/kiosk/v1/bootstrap/`` â€” provisioning giris noktasi.

    Fleet Key + HMAC + timestamp ile dogrulanir (App Key auth KULLANILMAZ).
    Onayli+aktif+eczaneli kiosk icin App Key doner.

    Yanitlar:
      200 APPROVED â€” {status, kiosk_id, pharmacy_id, app_key}
      202 PENDING  â€” {status, registration_id, retry_after_seconds}
      403 REJECTED â€” {status}
      401          â€” fleet key veya HMAC gecersiz
      400          â€” eksik/hatali format
      503          â€” sunucu yapilandirmasi eksik
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
        device_id = (request.data.get("device_id") or "").strip()
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

        # 4) HMAC (device_id dahil)
        if not verify_provision_hmac(mac, timestamp, received_hmac, provisioning_secret, device_id):
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
                # Kiosk silinmis/pasif â€” PENDING'e geri don
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
                device_id=device_id or provision_req.device_id,
                device_metadata=device_metadata or provision_req.device_metadata,
            )
            return Response(_pending_response(provision_req), status=status.HTTP_202_ACCEPTED)

        # Yeni cihaz â€” PENDING kayit olustur
        from django.db import IntegrityError as _IntegrityError
        try:
            with transaction.atomic():    # savepoint: isolates IntegrityError
                provision_req = KioskProvisioningRequest(
                    mac_adresi=mac,
                    device_id=device_id,
                    hostname=hostname,
                    device_metadata=device_metadata,
                    status=KioskProvisioningRequest.Status.PENDING,
                    last_seen_at=now,
                    request_count=1,
                )
                provision_req.save()
        except _IntegrityError as exc:
            err_str = str(exc).lower()
            if "device_id" in err_str or "uniq_provisioning_device_id" in err_str:
                # Another provisioning request already claims this device_id
                return Response(
                    {"detail": "Bu device_id baska bir kayit talebiyle iliskilendirilmistir.", "code": "device_id_conflict"},
                    status=status.HTTP_409_CONFLICT,
                )
            # mac_adresi collision: concurrent request created a record for this MAC
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


# â”€â”€ Operasyonel endpoint'ler (AppKey + MAC) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class KioskPingView(KioskAPIView):
    """``GET /api/kiosk/v1/ping/`` — heartbeat + bugunun playlist versiyonu.

    Faz 7: DOOH_KIOSK_ACK flag'i kaldırıldı; desired/applied/horizon alanları her zaman döner.
    """

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

        import zoneinfo
        tz = zoneinfo.ZoneInfo(settings.TIME_ZONE)
        ist_today = now.astimezone(tz).date()
        horizon = int(getattr(settings, "DOOH_HORIZON_DAYS", 3))

        response = {
            "kiosk_id": int(kiosk.pk),
            "date": str(today),
            "playlist_version": kiosk.last_playlist_version or agg["max_version"] or 0,
            "updated_at": agg["max_updated"].isoformat() if agg["max_updated"] else None,
            "server_time": now.isoformat(),
            "desired_playlist_version": kiosk.last_playlist_version or 0,
            "applied_playlist_version": kiosk.applied_playlist_version,
            "horizon_start": str(ist_today),
            "horizon_end": str(ist_today + _dt.timedelta(days=horizon - 1)),
            "timezone": settings.TIME_ZONE,
        }

        return Response(response)


class KioskSyncView(KioskAPIView):
    """``GET /api/kiosk/v1/sync/`` â€” aktif creative + house_ad + lookup listesi."""

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
    """``GET /api/kiosk/v1/catalog/`` â€” kategori/soru/cevap/etken madde/danisma."""

    def get(self, request):
        return Response(build_catalog_payload())


class KioskPlaylistView(KioskAPIView):
    """``GET /api/kiosk/v1/playlist/?date=YYYY-MM-DD`` â€” gunun 24 saatlik playlist'i."""

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
    """``POST /api/kiosk/v1/sessions/`` â€” oturum outbox toplu-yazma (idempotent).

    Response per item:
      {"idempotency_key": "...", "status": "created"|"existing", "qr_kodu": "XXXXXXXX"}
    """

    def post(self, request):
        items = request.data.get("items", [])
        if not isinstance(items, list):
            return Response({"detail": "'items' alani bir liste olmalidir."},
                            status=status.HTTP_400_BAD_REQUEST)
        results, errors = ingest_session_items(self.kiosk, items)
        return_status = status.HTTP_207_MULTI_STATUS if errors else status.HTTP_200_OK
        return Response(
            {"results": results, "errors": errors},
            status=return_status,
        )


class KioskProofOfPlayView(KioskAPIView):
    """``POST /api/kiosk/v1/proof-of-play/`` â€” reklam gosterim (PlayLog) toplu-yazma."""

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
    """``POST /api/kiosk/v1/diagnostics/`` â€” diagnostic outbox (DB'ye yazilmaz)."""

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


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class KioskIdentityEnrollView(KioskAPIView):
    """``POST /api/kiosk/v1/identity/enroll/`` â€” device ID tek-seferlik baglama.

    Amac: Onceden kaydedilmis (App Key'i olan) bir kiosk'a kalici device_id baglamak.
    Guvenlik ozeti:
      - Mevcut AppKey + MAC ile dogrulama gereklidir.
      - Sadece ``Kiosk.device_id IS NULL`` iken gerceklesebilir (tek seferlik).
      - Bir kez baglanan device_id DEGISTIRILEMEZ (concurrent race condition icin
        SELECT...UPDATE filter kullanilir; yalnizca NULL â†’ deger atomik gecisi yapilir).

    Sinir: device_id, cihazin yazilimi tarafindan uretilir (crypto.randomUUID).
    TPM tabanli degildir; SQLite DB kopyalanirsa kopyalanabilir. Bu gercek
    dokumante edilmistir â€” donanim guvencesi saglanmaz.

    Yanitlar:
      200 enrolled  â€” {\"status\": \"enrolled\", \"device_id\": \"...\"}
      200 noop      â€” device_id zaten bu degerle bagli (idempotent)
      409 conflict  â€” device_id zaten FARKLI bir degerle bagli
      400           â€” gecersiz format
    """

    def post(self, request):
        kiosk = self.kiosk
        device_id = (request.data.get("device_id") or "").strip().lower()

        if not device_id:
            return Response(
                {"detail": "device_id zorunlu.", "code": "device_id_required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not _UUID_RE.match(device_id):
            return Response(
                {"detail": "device_id gecerli bir UUID olmali (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).",
                 "code": "device_id_invalid_format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Idempotent: zaten bu degerle bagliysa basarili say
        if kiosk.device_id:
            if kiosk.device_id.lower() == device_id:
                return Response({"status": "enrolled", "device_id": kiosk.device_id})
            return Response(
                {"detail": "Bu kiosk'a farkli bir device_id zaten baglidir. Degistirilemez.",
                 "code": "already_bound"},
                status=status.HTTP_409_CONFLICT,
            )

        # Atomic one-time binding: only update if still NULL
        updated = Kiosk.objects.filter(pk=kiosk.pk, device_id__isnull=True).update(
            device_id=device_id
        )
        if updated:
            return Response({"status": "enrolled", "device_id": device_id})

        # Race condition: someone else bound it between our check and update
        kiosk.refresh_from_db(fields=["device_id"])
        if kiosk.device_id and kiosk.device_id.lower() == device_id:
            return Response({"status": "enrolled", "device_id": kiosk.device_id})
        return Response(
            {"detail": "Device ID baglama yarisi durumu. Mevcut device_id degistirilemez.",
             "code": "already_bound"},
            status=status.HTTP_409_CONFLICT,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Faz 5 — Manifest + ACK (Faz 7: her zaman aktif, flag'siz)
# ─────────────────────────────────────────────────────────────────────────────

import zoneinfo as _zoneinfo


class KioskManifestView(KioskAPIView):
    """``GET /api/kiosk/v1/manifest/`` — 3 günlük authoritative playlist manifesti.

    Faz 7: DOOH_KIOSK_ACK flag'i kaldırıldı; endpoint her zaman aktif.
    """

    def get(self, request):
        tz = _zoneinfo.ZoneInfo(settings.TIME_ZONE)
        now = timezone.now()
        ist_now = now.astimezone(tz)
        today = ist_now.date()
        horizon = int(getattr(settings, "DOOH_HORIZON_DAYS", 3))
        horizon_dates = [today + _dt.timedelta(days=i) for i in range(horizon)]

        with transaction.atomic():
            kiosk = Kiosk.objects.select_for_update().get(pk=self.kiosk.pk)
            desired_version = kiosk.last_playlist_version or 0

            days_data = []
            for d in horizon_dates:
                playlists = list(
                    Playlist.objects
                    .filter(kiosk=kiosk, target_date=d)
                    .order_by("target_hour")
                    .prefetch_related("items__creative__campaign", "items__house_ad")
                )
                from apps.campaigns.serializers import KioskPlaylistSerializer
                days_data.append({
                    "target_date": str(d),
                    "playlists": KioskPlaylistSerializer(playlists, many=True).data,
                })

        return Response({
            "kiosk_id": int(kiosk.pk),
            "playlist_version": desired_version,
            "desired_playlist_version": desired_version,
            "applied_playlist_version": kiosk.applied_playlist_version,
            "timezone": settings.TIME_ZONE,
            "horizon_start": str(horizon_dates[0]),
            "horizon_end": str(horizon_dates[-1]),
            "generated_at": now.isoformat(),
            "days": days_data,
        })


class KioskAckView(KioskAPIView):
    """``POST /api/kiosk/v1/ack/`` — kiosk 3-gün manifest uygulandı bildirimi.

    Faz 7: DOOH_KIOSK_ACK flag'i kaldırıldı; endpoint her zaman aktif.

    ACK kuralları:
      - applied_version > desired_version → 409 (future version kabul edilmez).
      - applied_version < kiosk.applied_playlist_version → STALE_IGNORED (geriye gidemez).
      - applied_version == applied_playlist_version ve horizon aynıysa → IDEMPOTENT.
      - applied_version > applied_playlist_version → APPLIED.
      - Aynı version + ileri horizon coverage → coverage güncellenir.
    """

    def post(self, request):
        playlist_version = request.data.get("playlist_version")
        horizon_start_raw = request.data.get("horizon_start")
        horizon_end_raw = request.data.get("horizon_end")

        # Validate payload
        try:
            playlist_version = int(playlist_version)
            if playlist_version < 0:
                raise ValueError()
        except (TypeError, ValueError):
            return Response(
                {"error": "playlist_version geçerli bir integer olmalıdır."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            h_start = _dt.date.fromisoformat(str(horizon_start_raw))
            h_end = _dt.date.fromisoformat(str(horizon_end_raw))
            if h_end < h_start:
                raise ValueError("horizon_end < horizon_start")
        except (TypeError, ValueError) as exc:
            return Response(
                {"error": f"Geçersiz horizon tarihleri: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()

        with transaction.atomic():
            kiosk = Kiosk.objects.select_for_update().get(pk=self.kiosk.pk)
            desired = kiosk.last_playlist_version or 0

            # Future ACK: kiosk backend'den daha ileride olduğunu iddia ediyor
            if playlist_version > desired:
                return Response(
                    {
                        "ack_status": "FUTURE_REJECTED",
                        "applied_version": playlist_version,
                        "desired_version": desired,
                        "error": "playlist_version desired_version'ı aşıyor.",
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            current_applied = kiosk.applied_playlist_version or 0

            # Stale ACK: geriye gitme yok
            if playlist_version < current_applied:
                return Response({
                    "ack_status": "STALE_IGNORED",
                    "applied_version": current_applied,
                    "desired_version": desired,
                })

            # Idempotent: aynı version, aynı horizon → no-op
            if (
                playlist_version == current_applied
                and kiosk.applied_horizon_start == h_start
                and kiosk.applied_horizon_end == h_end
            ):
                return Response({
                    "ack_status": "IDEMPOTENT",
                    "applied_version": current_applied,
                    "desired_version": desired,
                })

            # APPLIED (version ilerledi veya aynı version + genişleyen horizon)
            kiosk.applied_playlist_version = playlist_version
            kiosk.playlist_applied_at = now
            kiosk.applied_horizon_start = h_start
            kiosk.applied_horizon_end = h_end
            kiosk.save(update_fields=[
                "applied_playlist_version",
                "playlist_applied_at",
                "applied_horizon_start",
                "applied_horizon_end",
                "guncellenme_tarihi",
            ])

        return Response({
            "ack_status": "APPLIED",
            "applied_version": playlist_version,
            "desired_version": desired,
        })
