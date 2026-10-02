"""Reklam medya yukleme view'i.

DOOH v2 mimarisi tum kampanya/playlist isini ``views_v2`` icindeki
viewset'lerden yapar. Burada sadece ortak medya upload endpoint'i kalir.

Yukleme yaniti daima object_key tabanli API proxy URL'i dondurur. Presigned URL
uretilmez veya veritabanina yazilmaz.
"""
import logging

from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from apps.core.media_proxy import media_proxy_url
from apps.core.services.storage_service import StorageService
from apps.pharmacies.permissions import IsSuperAdmin


logger = logging.getLogger(__name__)


class MediaUploadView(APIView):
    """``POST /api/campaigns/upload-media/`` — DOOH creative ve house ad medyasi
    icin ortak yukleme noktasi. Yuklenen dosyanin proxy URL'sini doner.

    Desteklenen MIME: JPEG, PNG, GIF, WebP, MP4, WebM. Max boyut: 100 MB.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]
    parser_classes = [MultiPartParser]

    ALLOWED_TYPES = {
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "video/mp4", "video/webm",
    }
    # media_kind=image isteklerinde yalnız bu MIME'ler kabul edilir.
    IMAGE_ONLY_TYPES = {"image/jpeg", "image/png", "image/webp"}
    MAX_SIZE = 100 * 1024 * 1024  # 100 MB

    # Magic-byte imzaları: (offset, bytes)
    _MAGIC = [
        (0, b"\xff\xd8\xff"),                              # JPEG
        (0, b"\x89PNG\r\n\x1a\n"),                        # PNG
        (0, b"RIFF"),                                      # WebP (RIFF header)
    ]

    @staticmethod
    def _is_webp(header: bytes) -> bool:
        return header[:4] == b"RIFF" and header[8:12] == b"WEBP"

    @classmethod
    def _check_image_magic(cls, header: bytes, content_type: str) -> bool:
        """content_type ile magic-byte imzasının uyuşup uyuşmadığını doğrula."""
        if content_type == "image/jpeg":
            return header[:3] == b"\xff\xd8\xff"
        if content_type == "image/png":
            return header[:8] == b"\x89PNG\r\n\x1a\n"
        if content_type == "image/webp":
            return cls._is_webp(header)
        return False

    def post(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"error": "Dosya bulunamadı."}, status=status.HTTP_400_BAD_REQUEST)

        media_kind = request.data.get("media_kind", "").strip().lower()
        allowed = self.IMAGE_ONLY_TYPES if media_kind == "image" else self.ALLOWED_TYPES

        if uploaded.content_type not in allowed:
            return Response(
                {"error": "Desteklenmeyen dosya türü. Görsel yalnızca PNG/JPEG/WebP kabul eder."
                 if media_kind == "image" else "Desteklenmeyen dosya türü."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if media_kind == "image":
            header = uploaded.read(12)
            uploaded.seek(0)
            if not self._check_image_magic(header, uploaded.content_type):
                return Response(
                    {"error": "Dosya içeriği beyan edilen MIME türüyle uyuşmuyor."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if uploaded.size > self.MAX_SIZE:
            return Response({"error": "Dosya 100 MB'dan büyük olamaz."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            storage_service = StorageService()
            object_key, checksum = storage_service.upload_file_with_checksum(uploaded, prefix="ads")
            media_url = media_proxy_url(object_key, request)
            return Response(
                {
                    "object_key": object_key,
                    "media_url": media_url,
                    "checksum": checksum,
                    "url": media_url,
                    "filename": object_key.rsplit("/", 1)[-1],
                    "object_name": object_key,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception:
            logger.exception("Campaign media upload to MinIO failed")
            return Response(
                {"error": "Dosya MinIO'ya yüklenirken bir hata oluştu."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
