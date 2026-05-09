"""
Reklam (Kampanya) gorunumleri.

Admin: tam CRUD (super admin JWT, UoW ile).
Kiosk: /sync/ endpoint'i — kioskun eczanesine hedeflenmis aktif reklamlar.
Bos hedef_eczaneler = herkese goster (genel yayin).
"""
import logging
import uuid

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from apps.core.services.minio_service import MinioService
from apps.core.uow import UnitOfWork
from apps.pharmacies.auth import KioskAppKeyAuthentication
from apps.pharmacies.models import Kiosk
from apps.pharmacies.permissions import IsKiosk, IsSuperAdmin

from .models import Reklam, ReklamTakvim
from .serializers import ReklamSerializer, ReklamTakvimSerializer


logger = logging.getLogger(__name__)


class ReklamViewSet(viewsets.ModelViewSet):
    queryset = Reklam.objects.prefetch_related("hedef_eczaneler").all()
    serializer_class = ReklamSerializer

    def get_authenticators(self):
        if getattr(self, "action", None) == "sync":
            return [KioskAppKeyAuthentication()]
        return [JWTAuthentication()]

    def get_permissions(self):
        if self.action == "sync":
            return [IsKiosk()]
        return [IsSuperAdmin()]

    # ── UoW ile yazma ──
    def perform_create(self, serializer):
        hedef_eczaneler = serializer.validated_data.pop("hedef_eczaneler", [])
        instance = Reklam(**serializer.validated_data)
        with UnitOfWork(user=self.request.user) as uow:
            uow.add(instance)
            instance.hedef_eczaneler.set(hedef_eczaneler)
        serializer.instance = instance

    def perform_update(self, serializer):
        instance: Reklam = serializer.instance
        hedef_eczaneler = serializer.validated_data.pop("hedef_eczaneler", None)
        for k, v in serializer.validated_data.items():
            setattr(instance, k, v)
        with UnitOfWork(user=self.request.user) as uow:
            uow.update(instance)
            if hedef_eczaneler is not None:
                instance.hedef_eczaneler.set(hedef_eczaneler)

    def perform_destroy(self, instance):
        with UnitOfWork(user=self.request.user) as uow:
            uow.delete(instance)

    # ── Kiosk sync ──
    @action(detail=False, methods=["get"], url_path="sync")
    def sync(self, request):
        """
        GET /api/campaigns/sync/
        Kioskun eczanesine hedeflenmis, su an aktif reklamlar.
        Bos hedef_eczaneler = herkese hedefli (genel yayin).
        """
        kiosk: Kiosk = request.user
        eczane = kiosk.eczane
        now = timezone.now()

        scheduled_ids = ReklamTakvim.objects.filter(
            aktif=True,
            kiosk=kiosk,
            reklam__aktif=True,
            reklam__baslangic_tarihi__lte=now,
            reklam__bitis_tarihi__gte=now,
            baslangic_saat__lte=now.hour,
            bitis_saat__gt=now.hour,
        ).values_list("reklam_id", flat=True)
        if scheduled_ids.exists():
            qs = Reklam.objects.filter(pk__in=scheduled_ids).distinct()
            return Response(ReklamSerializer(qs, many=True).data)

        qs = Reklam.objects.filter(
            aktif=True, baslangic_tarihi__lte=now, bitis_tarihi__gte=now
        )
        # Bos hedef_eczaneler = herkese; yoksa bu eczane dahil olmali
        qs = qs.filter(
            hedef_eczaneler__isnull=True
        ) | qs.filter(
            hedef_eczaneler=eczane
        )
        qs = qs.distinct()

        return Response(ReklamSerializer(qs, many=True).data)


class ReklamTakvimViewSet(viewsets.ModelViewSet):
    queryset = ReklamTakvim.objects.select_related("reklam", "kiosk", "kiosk__eczane").all()
    serializer_class = ReklamTakvimSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        reklam_id = self.request.query_params.get("reklam")
        kiosk_id = self.request.query_params.get("kiosk")
        eczane_id = self.request.query_params.get("eczane")
        if reklam_id:
            qs = qs.filter(reklam_id=reklam_id)
        if kiosk_id:
            qs = qs.filter(kiosk_id=kiosk_id)
        if eczane_id:
            qs = qs.filter(kiosk__eczane_id=eczane_id)
        return qs

    def perform_create(self, serializer):
        instance = ReklamTakvim(**serializer.validated_data)
        with UnitOfWork(user=self.request.user) as uow:
            uow.add(instance)
        serializer.instance = instance

    def perform_update(self, serializer):
        instance: ReklamTakvim = serializer.instance
        for k, v in serializer.validated_data.items():
            setattr(instance, k, v)
        with UnitOfWork(user=self.request.user) as uow:
            uow.update(instance)

    def perform_destroy(self, instance):
        with UnitOfWork(user=self.request.user) as uow:
            uow.delete(instance)


class MediaUploadView(APIView):
    """
    POST /api/campaigns/upload-media/
    Reklam medya dosyasını sunucuya yükler, URL döner.
    Desteklenen: JPEG, PNG, GIF, WebP, MP4, WebM — Max 100 MB.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]
    parser_classes = [MultiPartParser]

    ALLOWED_TYPES = {
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "video/mp4", "video/webm",
    }
    MAX_SIZE = 100 * 1024 * 1024  # 100 MB

    def post(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"error": "Dosya bulunamadı."}, status=status.HTTP_400_BAD_REQUEST)
        if uploaded.content_type not in self.ALLOWED_TYPES:
            return Response({"error": "Desteklenmeyen dosya türü."}, status=status.HTTP_400_BAD_REQUEST)
        if uploaded.size > self.MAX_SIZE:
            return Response({"error": "Dosya 100 MB'dan büyük olamaz."}, status=status.HTTP_400_BAD_REQUEST)

        ext = uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else "bin"
        filename = f"{uuid.uuid4().hex}.{ext}"

        try:
            minio_service = MinioService()
            object_name = minio_service.upload_file(uploaded, object_name=filename, prefix="ads")
            url = minio_service.get_object_url(object_name)
        except Exception:
            logger.exception("Campaign media upload to MinIO failed")
            return Response(
                {"error": "Dosya MinIO'ya yüklenirken bir hata oluştu."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"url": url, "filename": filename, "object_name": object_name},
            status=status.HTTP_201_CREATED,
        )
