"""
ERR-003: Merkezi DRF exception handler.

DRF'nin varsayılan davranışı 500 hatalarında bile bazen iç hata mesajını
yansıtabiliyor. Bu modül:
  - Bilinmeyen / 5xx exception'larında istemciye genel bir mesaj döner.
  - Detaylı stack trace'i `eisa.errors` logger'ına gönderir (operatör görür).
  - DRF'nin yakalayabildiği validation/permission hatalarını olduğu gibi geçirir.
"""
from __future__ import annotations

import logging
import uuid

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("eisa.errors")


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if response is not None:
        # DRF tarafından zaten anlamlı bir 4xx üretildi.
        return response

    # Buraya düşen her şey 500 sayılır. Stack trace logla, jenerik mesaj döndür.
    request = context.get("request") if context else None
    view = context.get("view") if context else None
    err_id = uuid.uuid4().hex[:12]
    logger.exception(
        "Unhandled API exception [%s] view=%s path=%s",
        err_id,
        getattr(view, "__class__", type(view)).__name__ if view else None,
        getattr(request, "path", None),
    )
    return Response(
        {
            "detail": "Sunucu hatası oluştu, lütfen daha sonra tekrar deneyin.",
            "error_id": err_id,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
