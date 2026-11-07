"""
Web sitesi medya servisi (CONTRACT §2 MediaRef, §5 Medya).

  - Kabul: image/jpeg, image/png, image/webp, image/gif, image/avif — en fazla 10 MB.
  - SVG KABUL EDİLMEZ (XSS riski). Tür, istemcinin bildirdiği content-type'a değil,
    dosya içeriğine (Pillow / imza) göre belirlenir.
  - Anahtar: website/YYYY/MM/<uuid>.<ext>
  - WEBSITE_MEDIA_LOCAL=True ise MEDIA_ROOT/website/... altına yazılır; aksi halde
    StorageService (RustFS/S3). İki durumda da /api/media/website/... yolundan sunulur.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("eisa.website")

MAKS_BOYUT = 10 * 1024 * 1024
IZINLI_MIME_UZANTI = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/avif": "avif",
}
_PILLOW_FORMAT_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "GIF": "image/gif",
    "AVIF": "image/avif",
}
MEDYA_ONEKI = "website/"


class MedyaHatasi(ValueError):
    """Kullanıcıya gösterilebilir yükleme hatası."""


def _avif_imzasi_mi(bas: bytes) -> bool:
    # ISO-BMFF: [4 bayt boyut]["ftyp"][marka] — avif / avis
    return len(bas) >= 12 and bas[4:8] == b"ftyp" and bas[8:12] in (b"avif", b"avis")


def dosyayi_incele(dosya) -> tuple[str, int | None, int | None]:
    """(mime, genislik, yukseklik) döner; uygun değilse MedyaHatasi fırlatır."""
    if dosya.size > MAKS_BOYUT:
        raise MedyaHatasi("Dosya boyutu en fazla 10 MB olabilir.")
    if dosya.size == 0:
        raise MedyaHatasi("Dosya boş.")

    ad = (dosya.name or "").lower()
    bildirilen = (getattr(dosya, "content_type", "") or "").lower()
    dosya.seek(0)
    bas = dosya.read(512)
    dosya.seek(0)
    if ad.endswith((".svg", ".svgz")) or "svg" in bildirilen or b"<svg" in bas.lower() or bas.lstrip().startswith(b"<"):
        raise MedyaHatasi("SVG ve HTML/XML tabanlı dosyalar kabul edilmez.")

    try:
        from PIL import Image

        with Image.open(dosya) as img:
            fmt = (img.format or "").upper()
            genislik, yukseklik = img.size
        mime = _PILLOW_FORMAT_MIME.get(fmt)
        if not mime:
            raise MedyaHatasi("Desteklenmeyen görsel türü. İzin verilenler: JPEG, PNG, WebP, GIF, AVIF.")
        return mime, int(genislik), int(yukseklik)
    except MedyaHatasi:
        raise
    except Exception:
        # Pillow'un açamadığı ama imzası AVIF olan dosya: boyutlar null (CONTRACT §2).
        if _avif_imzasi_mi(bas):
            return "image/avif", None, None
        raise MedyaHatasi("Geçersiz veya desteklenmeyen görsel dosyası.")
    finally:
        dosya.seek(0)


def yeni_object_key(mime: str) -> str:
    simdi = timezone.now()
    return f"{MEDYA_ONEKI}{simdi:%Y}/{simdi:%m}/{uuid.uuid4().hex}.{IZINLI_MIME_UZANTI[mime]}"


def _lokal_kok() -> Path:
    return (Path(settings.MEDIA_ROOT) / "website").resolve()


def lokal_yol(object_key: str) -> Path | None:
    """object_key → MEDIA_ROOT/website altındaki güvenli mutlak yol (dışarı taşarsa None)."""
    if not object_key.startswith(MEDYA_ONEKI) or ".." in object_key or "\\" in object_key:
        return None
    kok = _lokal_kok()
    yol = (Path(settings.MEDIA_ROOT) / object_key).resolve()
    try:
        yol.relative_to(kok)
    except ValueError:
        return None
    return yol


def lokal_mod() -> bool:
    return bool(getattr(settings, "WEBSITE_MEDIA_LOCAL", False))


def dosyayi_kaydet(dosya, object_key: str, mime: str) -> None:
    if lokal_mod():
        hedef = lokal_yol(object_key)
        if hedef is None:  # pragma: no cover — anahtar bizim üretimimiz
            raise MedyaHatasi("Geçersiz medya anahtarı.")
        hedef.parent.mkdir(parents=True, exist_ok=True)
        dosya.seek(0)
        with open(hedef, "wb") as f:
            for parca in dosya.chunks():
                f.write(parca)
        return

    from apps.core.services.storage_service import StorageService

    storage = StorageService()
    dosya.seek(0)
    storage.client.put_object(
        bucket_name=storage.bucket_name,
        object_name=object_key,
        data=dosya,
        length=dosya.size,
        content_type=mime,
    )


def dosyayi_sil(object_key: str) -> None:
    """Depodan siler; hata loglanır (DB kaydı yine silinir)."""
    try:
        if lokal_mod():
            yol = lokal_yol(object_key)
            if yol and yol.exists():
                yol.unlink()
            return
        from apps.core.services.storage_service import StorageService

        StorageService().delete_object(object_key)
    except Exception as exc:
        logger.warning("website_medya_silme_hatasi", extra={"object_key": object_key, "hata": str(exc)})


# ── Çıktıda MediaRef tazeleme ───────────────────────────────────────────────


def _medya_ref_mi(d) -> bool:
    return (
        isinstance(d, dict)
        and "id" in d
        and isinstance(d.get("yol"), str)
        and d["yol"].startswith("/api/media/website/")
    )


def _idleri_topla(dugum, idler: set) -> None:
    if _medya_ref_mi(dugum):
        try:
            idler.add(int(dugum["id"]))
        except (TypeError, ValueError):
            pass
        return
    if isinstance(dugum, dict):
        for v in dugum.values():
            _idleri_topla(v, idler)
    elif isinstance(dugum, list):
        for v in dugum:
            _idleri_topla(v, idler)


def _degistir(dugum, harita: dict):
    if _medya_ref_mi(dugum):
        try:
            return harita.get(int(dugum["id"]))
        except (TypeError, ValueError):
            return None
    if isinstance(dugum, dict):
        return {k: _degistir(v, harita) for k, v in dugum.items()}
    if isinstance(dugum, list):
        return [_degistir(v, harita) for v in dugum]
    return dugum


def medya_referanslarini_tazele(veri):
    """
    Yanıt üretirken tüm MediaRef'leri tek sorguyla DB'den tazeler.
    Silinmiş medya `null` olur (CONTRACT §5: silinen görsel sitede gösterilmez).
    """
    from ..models import WebsiteMedya

    idler: set[int] = set()
    _idleri_topla(veri, idler)
    if not idler:
        return veri
    harita = {m.pk: m.media_ref() for m in WebsiteMedya.objects.filter(pk__in=idler)}
    return _degistir(veri, harita)
