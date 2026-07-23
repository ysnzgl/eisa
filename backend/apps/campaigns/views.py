"""Reklam medya yukleme view'i.

DOOH v2 mimarisi tum kampanya/playlist isini ``views_v2`` icindeki
viewset'lerden yapar. Burada sadece ortak medya upload endpoint'i kalir.

Feature flag: ``DOOH_PERSISTENT_MEDIA_URL`` (settings)
  False (varsayılan) — eski presigned URL davranışı; rollback: flag'i kapat.
  True              — kalıcı URL akışı (upload_file_with_checksum + public_url).
"""
import logging
import uuid

from django.conf import settings
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

        use_persistent = getattr(settings, "DOOH_PERSISTENT_MEDIA_URL", False)

        try:
            storage_service = StorageService()

            if use_persistent:
                object_key, checksum = storage_service.upload_file_with_checksum(
                    uploaded, prefix="ads"
                )
                media_url = storage_service.public_url(object_key)
                return Response(
                    {
                        "object_key": object_key,
                        "media_url": media_url,
                        "checksum": checksum,
                        # Geçiş dönemi geriye-uyumlu alias'lar — eski API tüketicileri için zorunlu
                        "url": media_url,
                        "filename": object_key.rsplit("/", 1)[-1],
                        "object_name": object_key,
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                # Legacy: presigned URL (DOOH_PERSISTENT_MEDIA_URL=False)
                ext = uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else "bin"
                filename = f"{uuid.uuid4().hex}.{ext}"
                object_name = storage_service.upload_file(uploaded, object_name=filename, prefix="ads")
                url = storage_service.get_object_url(object_name)
                return Response(
                    {"url": url, "filename": filename, "object_name": object_name},
                    status=status.HTTP_201_CREATED,
                )

        except Exception:
            logger.exception("Campaign media upload to MinIO failed")
            return Response(
                {"error": "Dosya MinIO'ya yüklenirken bir hata oluştu."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
            storage_service = StorageService()
            object_key, checksum = storage_service.upload_file_with_checksum(
                uploaded, prefix="ads"
            )
            media_url = storage_service.public_url(object_key)
        except Exception:
            logger.exception("Campaign media upload to MinIO failed")
            return Response(
                {"error": "Dosya MinIO'ya yüklenirken bir hata oluştu."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "object_key": object_key,
                "media_url": media_url,
                "checksum": checksum,
                # Geçiş dönemi geriye-uyumlu alias'lar — eski API tüketicileri için zorunlu
                "url": media_url,
                "filename": object_key.rsplit("/", 1)[-1],
                "object_name": object_key,
            },
            status=status.HTTP_201_CREATED,
        )
