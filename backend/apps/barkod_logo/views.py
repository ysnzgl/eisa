"""Barkod Logo yönetim view'leri (SuperAdmin JWT).

Ayrıca PNG yükleme için özel endpoint: POST /api/barkod-logo/upload-gorsel/
"""
import logging
import uuid

from django.conf import settings
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.core.services.storage_service import StorageService
from apps.pharmacies.permissions import IsSuperAdmin
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from .models import BarkodLogo
from .serializers import BarkodLogoSerializer, validate_barkod_logo_png

logger = logging.getLogger(__name__)


class BarkodLogoViewSet(ModelViewSet):
    """CRUD — /api/barkod-logo/logolar/"""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]
    serializer_class = BarkodLogoSerializer

    def get_queryset(self):
        return BarkodLogo.objects.prefetch_related("hedef_kiosklar").order_by(
            "olusturulma_tarihi", "id"
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Barkod logolar silinemez; geçmiş kayıtlar korunmalıdır. Pasifleştirme kullanın."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class BarkodLogoGorselUploadView(APIView):
    """``POST /api/barkod-logo/upload-gorsel/``

    PNG doğrulama (format, max 336×336, ≤1 MB, şeffaf piksel yok, gri tonlu) ve depo yükleme.
    DOOH_PERSISTENT_MEDIA_URL=True  → kalıcı URL + sha256 checksum (prod)
    DOOH_PERSISTENT_MEDIA_URL=False → presigned URL, checksum boş (dev/varsayılan)
    Döner: {media_url, object_key, checksum}
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "Dosya bulunamadı."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_barkod_logo_png(uploaded)
        except Exception as exc:
            detail = getattr(exc, "detail", None) or str(exc)
            if isinstance(detail, list):
                detail = detail[0]
            return Response({"detail": str(detail)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            storage = StorageService()
            use_persistent = getattr(settings, "DOOH_PERSISTENT_MEDIA_URL", False)

            if use_persistent:
                object_key, checksum = storage.upload_file_with_checksum(uploaded, prefix="barkod-logo")
                media_url = storage.public_url(object_key)
            else:
                # Dev / presigned-URL modu (DOOH_PERSISTENT_MEDIA_URL=False)
                filename = f"{uuid.uuid4().hex}.png"
                object_key = storage.upload_file(uploaded, object_name=filename, prefix="barkod-logo")
                media_url = storage.get_object_url(object_key)
                checksum = ""

        except Exception:
            logger.exception("Barkod logo görseli yüklenemedi")
            return Response(
                {"detail": "Dosya depoya yüklenirken bir hata oluştu."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"media_url": media_url, "object_key": object_key, "checksum": checksum},
            status=status.HTTP_201_CREATED,
        )
