"""Ortak uygulama gorunumleri."""

import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .media_proxy import stream_storage_object


logger = logging.getLogger(__name__)


class PublicMediaProxyView(APIView):
    """Public yayin medyasi icin suresiz, object_key tabanli proxy."""

    # img/video etiketleri token refresh interceptor'undan gecmez. Yalniz
    # validate_media_object_key allow-list'indeki public yayin prefix'leri acilir.
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    def get(self, request, object_key: str):
        try:
            return stream_storage_object(request, object_key)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE)
        except Exception:
            logger.warning("Media proxy object not found", extra={"object_key": object_key})
            return Response({"detail": "Medya bulunamadi."}, status=status.HTTP_404_NOT_FOUND)
