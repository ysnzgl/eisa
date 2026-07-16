"""
ERR-003: Merkezi DRF exception handler.

DRF'nin varsayılan davranışı 500 hatalarında bile bazen iç hata mesajını
yansıtabiliyor. Bu modül:
  - Bilinmeyen / 5xx exception'larında istemciye genel bir mesaj döner.
  - Detaylı stack trace'i `eisa.errors` logger'ına gönderir (operatör görür).
  - `X-Correlation-ID` başlığını response'a ve payload'a ekler.
  - Aynı exception'ın request middleware tarafından tekrar loglanmaması için
    request üzerinde `_eisa_exception_logged` bayrağını set eder.
"""
from __future__ import annotations

import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.core.logging.correlation import (
    CORRELATION_HEADER,
    get_correlation_id,
    new_correlation_id,
)
from apps.core.logging.formatters import LOG_HANDLED_MARK

logger = logging.getLogger("eisa.errors")


def custom_exception_handler(exc, context):
    request = context.get("request") if context else None
    view = context.get("view") if context else None

    correlation_id = get_correlation_id() or new_correlation_id()

    response = drf_exception_handler(exc, context)

    if response is not None:
        # DRF tarafından zaten anlamlı bir 4xx üretildi.
        _annotate_response(response, correlation_id)
        return response

    # Buraya düşen her şey 500 sayılır. Stack trace logla, jenerik mesaj döndür.
    view_name = getattr(view.__class__, "__name__", None) if view else None
    if request is not None:
        setattr(request, LOG_HANDLED_MARK, True)
    logger.exception(
        "unhandled_api_exception",
        extra={
            "event": "unhandled_api_exception",
            "view": view_name,
            "request_method": getattr(request, "method", None),
            "request_path": getattr(request, "path", None),
            "correlation_id": correlation_id,
        },
    )
    response = Response(
        {
            "detail": "Sunucu hatası oluştu, lütfen daha sonra tekrar deneyin.",
            "correlation_id": correlation_id,
        },
        status=500,
    )
    _annotate_response(response, correlation_id)
    return response


def _annotate_response(response, correlation_id: str) -> None:
    if correlation_id and CORRELATION_HEADER not in response.headers:
        response.headers[CORRELATION_HEADER] = correlation_id
