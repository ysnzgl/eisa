"""
Site önbellek yenileme (CONTRACT §6).

Yayın / ayar / menü / blog değişikliklerinden sonra sitenin `/api/revalidate` ucuna
`{"tags": [...]}` POST edilir. İstek `transaction.on_commit` içinde, kısa timeout ile
yapılır; hata loglanır ve API isteği başarısız SAYILMAZ.

Hedefler:
  - SITE_REVALIDATE_URLS (virgüllü liste)
  - SITE_REVALIDATE_HEADLESS_HOST ("host:port") → DNS ile çözülen TÜM IP'lere
    http://<ip>:<port>/api/revalidate (K8s headless service ile pod başına fan-out)
"""
from __future__ import annotations

import json
import logging
import socket
import urllib.error
import urllib.request

from django.conf import settings
from django.db import transaction

logger = logging.getLogger("eisa.website")


def hedef_urller() -> list[str]:
    urller = list(getattr(settings, "SITE_REVALIDATE_URLS", []) or [])
    headless = (getattr(settings, "SITE_REVALIDATE_HEADLESS_HOST", "") or "").strip()
    if headless:
        host, _, port = headless.rpartition(":")
        if not host or not port.isdigit():
            logger.warning("website_revalidate_headless_gecersiz", extra={"deger": headless})
        else:
            try:
                bilgiler = socket.getaddrinfo(host, int(port), proto=socket.IPPROTO_TCP)
                ipler = sorted({b[4][0] for b in bilgiler})
            except OSError as exc:
                logger.warning("website_revalidate_dns_hatasi", extra={"host": host, "hata": str(exc)})
                ipler = []
            for ip in ipler:
                ip_str = f"[{ip}]" if ":" in ip else ip
                urller.append(f"http://{ip_str}:{port}/api/revalidate")
    # Sırayı koruyarak tekilleştir.
    return list(dict.fromkeys(urller))


def _post(url: str, tags: list[str]) -> None:
    govde = json.dumps({"tags": tags}).encode("utf-8")
    istek = urllib.request.Request(
        url,
        data=govde,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Revalidate-Secret": getattr(settings, "REVALIDATE_SECRET", ""),
        },
    )
    timeout = float(getattr(settings, "SITE_REVALIDATE_TIMEOUT", 3) or 3)
    with urllib.request.urlopen(istek, timeout=timeout) as yanit:  # noqa: S310 — URL ayarlardan gelir
        yanit.read(1024)


def revalidate_gonder(tags: list[str]) -> None:
    """Tüm hedeflere senkron gönderir; hatalar loglanır, yukarı fırlatılmaz."""
    for url in hedef_urller():
        try:
            _post(url, tags)
            logger.info("website_revalidate_ok", extra={"url": url, "tags": tags})
        except (urllib.error.URLError, OSError, ValueError) as exc:
            logger.warning("website_revalidate_hatasi", extra={"url": url, "tags": tags, "hata": str(exc)})
        except Exception:  # pragma: no cover — beklenmeyen hata da isteği bozmasın
            logger.exception("website_revalidate_beklenmeyen_hata", extra={"url": url, "tags": tags})


def revalidate(*tags: str) -> None:
    """Commit sonrası verilen tag'leri yeniler (tekilleştirilmiş, sıralı)."""
    temiz = list(dict.fromkeys(t for t in tags if t))
    if not temiz:
        return
    transaction.on_commit(lambda: revalidate_gonder(temiz))


def sayfa_tagleri(slug: str) -> tuple[str, ...]:
    return (f"sayfa:{slug}", "sayfalar", "site")


def blog_tagleri(*sluglar: str) -> tuple[str, ...]:
    return ("blog", *[f"blog:{s}" for s in sluglar if s])
