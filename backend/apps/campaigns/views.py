"""Reklam medya yukleme view'i.

DOOH v2 mimarisi tum kampanya/playlist isini ``views_v2`` icindeki
viewset'lerden yapar. Burada sadece ortak medya upload endpoint'i kalir.
"""
import logging
import uuid

from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from apps.core.services.storage_service import StorageService
from apps.pharmacies.permissions import IsSuperAdmin


logger = logging.getLogger(__name__)


class MediaUploadView(APIView):
    """``POST /api/campaigns/upload-media/`` — DOOH creative ve house ad medyasi
    icin ortak yukleme noktasi. Yuklenen dosyanin public URL'sini doner.

    Desteklenen MIME: JPEG, PNG, GIF, WebP, MP4, WebM. Max boyut: 100 MB.
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
            storage_service = StorageService()
            object_name = storage_service.upload_file(uploaded, object_name=filename, prefix="ads")
            url = storage_service.get_object_url(object_name)
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
