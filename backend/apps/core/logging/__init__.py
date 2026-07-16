"""
E-İSA merkezi loglama altyapısı.

Bu paket Django tarafında Kubernetes stdout/stderr'e JSON log üretimini,
korelasyon ID takibini ve hassas verilerin maskelenmesini sağlar.
Dosyaya log yazılmaz; toplama işi node collector'a (Alloy/Loki) bırakılır.
"""

from .correlation import (
    CORRELATION_HEADER,
    get_correlation_id,
    new_correlation_id,
    set_correlation_id,
)
from .formatters import JsonFormatter
from .redaction import sanitize, sanitize_headers

__all__ = [
    "CORRELATION_HEADER",
    "JsonFormatter",
    "get_correlation_id",
    "new_correlation_id",
    "sanitize",
    "sanitize_headers",
    "set_correlation_id",
]
