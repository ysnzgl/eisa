"""
Korelasyon ID ve HTTP istek yaşam döngüsü middleware'leri.

`CorrelationIdMiddleware`:
  - Gelen istekten `X-Correlation-ID` başlığını okur, güvenli değilse UUID üretir.
  - Response başlığına aynı değeri yazar.
  - Middleware boyunca contextvars üzerinden log'lara aktarır.

`RequestLoggingMiddleware`:
  - İstek başlangıcında saati kayıt eder.
  - İstek bitiminde tek bir `request_completed` log kaydı üretir.
  - Health/readiness endpoint'lerinde gürültü üretmez.
  - Aynı hatanın iki kez log'lanmasını önlemek için exception handler'ın işaret
    bıraktığı `_eisa_exception_logged` bayrağını dikkate alır.
"""
from __future__ import annotations

import logging
import time
from typing import Callable

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from .correlation import (
    CORRELATION_HEADER,
    get_correlation_id,
    new_correlation_id,
    reset_correlation_id,
    sanitize_incoming,
    set_correlation_id,
)
from .formatters import LOG_HANDLED_MARK

logger = logging.getLogger("eisa.request")

# Health/readiness ve boş sistem endpoint'lerinde gürültüyü azalt.
_QUIET_PATHS = frozenset({
    "/", "/healthz", "/healthz/", "/readyz", "/readyz/", "/favicon.ico",
})

# Yalnızca güvenli olduğu bilinen ilk path bileşenlerini logla; UUID/QR gibi
# değerler ayrı `path_template` alanına konur; tam path yazılmaz.
_MAX_LOGGABLE_PATH = 256


class CorrelationIdMiddleware(MiddlewareMixin):
    """İstek boyunca korelasyon ID takibi."""

    header_name = CORRELATION_HEADER

    def process_request(self, request: HttpRequest) -> None:
        incoming = request.headers.get(self.header_name) if hasattr(request, "headers") else None
        correlation_id = sanitize_incoming(incoming) or new_correlation_id()
        set_correlation_id(correlation_id)
        request.correlation_id = correlation_id  # type: ignore[attr-defined]

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        cid = get_correlation_id() or getattr(request, "correlation_id", None)
        if cid and self.header_name not in response.headers:
            response.headers[self.header_name] = cid
        return response

    def process_exception(self, request: HttpRequest, exception: Exception) -> None:  # noqa: ARG002
        # Bağlam contextvars üzerinde kalır; response üretiminde yine set edilecek.
        return None


class RequestLoggingMiddleware(MiddlewareMixin):
    """Her HTTP isteği için yalnızca bir tamamlanma log kaydı üretir."""

    def process_request(self, request: HttpRequest) -> None:
        request._eisa_request_started_ns = time.perf_counter_ns()  # type: ignore[attr-defined]

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        try:
            self._emit(request, response, exc=None)
        finally:
            reset_correlation_id()
        return response

    def process_exception(self, request: HttpRequest, exception: Exception) -> None:  # noqa: D401
        # Exception handler zincirinden geçmemiş bir hata; korelasyon ID kaybolmasın diye
        # bir kez log ediyoruz. Django daha sonra `process_response`'i de çağırırsa
        # `_eisa_exception_logged` bayrağı sayesinde tekrar log oluşmaz.
        marker = getattr(request, LOG_HANDLED_MARK, False)
        if marker:
            return None
        setattr(request, LOG_HANDLED_MARK, True)
        actor = _actor_type(request)
        logger.error(
            "request_failed",
            exc_info=True,
            extra={
                "event": "request_failed",
                "request_method": request.method,
                "request_path": _safe_path(request.path),
                "actor_type": actor,
                "duration_ms": _elapsed_ms(request),
            },
        )
        return None

    def _emit(
        self,
        request: HttpRequest,
        response: HttpResponse,
        *,
        exc: Exception | None,
    ) -> None:
        path = _safe_path(request.path)
        if path in _QUIET_PATHS and 200 <= response.status_code < 400:
            return

        status = response.status_code
        level = logging.INFO
        if 400 <= status < 500 and status not in (400, 401, 403, 404, 405, 409, 422, 429):
            level = logging.INFO
        elif status in (401, 403, 429):
            level = logging.WARNING
        elif status == 500 or status >= 500:
            level = logging.ERROR
        elif status == 400 and getattr(request, "_eisa_bad_request_is_anomaly", False):
            level = logging.WARNING

        extra = {
            "event": "request_completed",
            "request_method": request.method,
            "request_path": path,
            "status_code": status,
            "duration_ms": _elapsed_ms(request),
            "actor_type": _actor_type(request),
        }
        route = getattr(getattr(request, "resolver_match", None), "route", None)
        if route:
            extra["route"] = route

        if exc is None and getattr(request, LOG_HANDLED_MARK, False):
            # Exception önce loglanmış — kısa tamamlanma satırıyla yetin.
            logger.log(level, "request_completed", extra=extra)
            return

        logger.log(level, "request_completed", extra=extra)


def _elapsed_ms(request: HttpRequest) -> int:
    started = getattr(request, "_eisa_request_started_ns", None)
    if started is None:
        return 0
    return max(0, (time.perf_counter_ns() - started) // 1_000_000)


def _safe_path(path: str | None) -> str:
    if not path:
        return "/"
    if len(path) > _MAX_LOGGABLE_PATH:
        return path[:_MAX_LOGGABLE_PATH] + "…"
    return path


def _actor_type(request: HttpRequest) -> str:
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        role = getattr(user, "rol", None)
        if role:
            return f"user:{role}"
        return "user"
    auth = getattr(request, "auth", None)
    if isinstance(auth, dict) and auth.get("kiosk_id"):
        return "kiosk"
    if request.META.get("HTTP_X_KIOSK_KEY"):
        return "kiosk"
    return "anonymous"
