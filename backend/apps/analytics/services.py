"""Analitik domain servisleri.

Kiosk oturum (session) toplu-yazma is mantigi burada tek noktada tutulur ve
`kiosk_api` facade tarafindan yeniden kullanilir. View'lar bu mantigi
kopyalamaz.

Oturum Tipleri:
  SIKAYET        : Kullanici sikayet kategorisi secer, sorulari cevaplar,
                   etken madde onerileri gosterilir.
  OZEL_DANISMANLIK: Kullanici yalniz ozel danismanlik konusu secer;
                   soru/cevap/etken madde onerileri BULUNMAZ; eczaciya QR olusturulur.

QR Tasarimi:
  - Backend her oturum icin benzersiz 8 karakter [A-Z0-9] QR kodu URETIR.
  - Istemciden gelen qr_kodu YOKSAYILIR; edge nihai QR'i backend'den alir.
  - DB unique constraint + IntegrityError retry ile cakisma onlenir.
  - Her retry ayri savepoint (nested transaction) icinde calisir.
  - "QR collision imkansiz" degil; DB onu saklar, retry cozum saglar.

Soru-Cevap Uyumu (SIKAYET):
  - Yeni SIKAYET ingestion'inda soru/cevap mevcut olmali ve eslesmelidir.
  - Uyumsuzluk HTTP 400 (SessionValidationError) + tam transaction rollback uretir.
  - Legacy backfill (management command) farkli davranir: null FK + snapshot.
"""
from __future__ import annotations

import re
import secrets
import string
from typing import Any

from django.db import IntegrityError, transaction

from apps.core.uow import UnitOfWork
from apps.lookups.models import Cinsiyet, YasAraligi
from apps.products.models import Cevap, Danisma, EtkenMadde, Kategori, Soru

from .models import OturumCevap, OturumLogu, OturumOnerilenEtkenMadde
from .serializers import OturumLoguItemSerializer


QR_ALPHABET = string.ascii_uppercase + string.digits  # A-Z, 0-9
QR_LENGTH = 8
MAX_QR_RETRY = 5
_QR_RE = re.compile(r'^[A-Z0-9]{8}$')


def generate_qr_candidate() -> str:
    """Rastgele 8 karakter [A-Z0-9] QR adayi uretir.

    Benzersizligi GARANTILEMEZ; caller DB unique constraint ile dogrular.
    Kriptografik rastgelelige gerek yok; secrets.choice yeterli.
    """
    return ''.join(secrets.choice(QR_ALPHABET) for _ in range(QR_LENGTH))


class SessionValidationError(Exception):
    """Oturum icindeki bir alana ozgu dogrulama hatasi.

    Bu hata bir atomic savepoint icinde raise edildiginde tum transaction
    (parent OturumLogu dahil) rollback olur. Caller 400-level error uretir.
    """
    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(message)


def ingest_session_items(kiosk, items: list[Any]) -> tuple[list[dict], list[dict]]:
    """Kiosk'tan gelen oturum kayitlarini idempotent sekilde yazar.

    `kiosk` dogrulanmis Kiosk ornegidir (auth context'ten gelir). Payload'daki
    kiosk bilgisine GUVENILMEZ; kayit her zaman `kiosk` ile iliskilendirilir.

    Istemciden gelen `qr_kodu` YOKSAYILIR. Backend her oturum icin benzersiz
    bir QR kodu uretir ve response'ta doner.

    Idempotency: Ayni idempotency_anahtari tekrar gelirse mevcut kayit ve
    QR kodu dogrudan doner (yeni kayit olusturulmaz, child'lar tekrarlanmaz).

    Doner: (results, errors)
      results: [{"idempotency_key": str, "status": "created"|"existing", "qr_kodu": str}]
      errors:  [{"index": int, "idempotency_anahtari": str, "errors": dict}]
    """
    results: list[dict] = []
    errors: list[dict] = []

    for i, raw in enumerate(items):
        ser = OturumLoguItemSerializer(data=raw)
        if not ser.is_valid():
            errors.append({
                "index": i,
                "idempotency_anahtari": (raw or {}).get("idempotency_anahtari"),
                "errors": ser.errors,
            })
            continue
        d = ser.validated_data
        idem = d["idempotency_anahtari"]

        # Idempotency: mevcut kayit varsa ayni QR'i dondur
        existing = OturumLogu.objects.filter(idempotency_anahtari=idem).only("qr_kodu").first()
        if existing:
            results.append({
                "idempotency_key": str(idem),
                "status": "existing",
                "qr_kodu": existing.qr_kodu,
            })
            continue

        # Oturum tipi + lookup cozumleme
        oturum_tipi = d.get("oturum_tipi", "SIKAYET")
        kategori = None
        danisma_kategorisi = None

        if oturum_tipi == "SIKAYET":
            # SIKAYET: normal kategori zorunlu; danisma kategorisi yasak
            if d.get("danisma_kategorisi_id") or d.get("danisma_kategorisi_slug"):
                errors.append({"index": i, "idempotency_anahtari": str(idem),
                               "errors": {"danisma_kategorisi_id": [
                                   "Sikayet oturumunda ozel danismanlik kategorisi olamaz."
                               ]}})
                continue
            kategori_slug = d.get("kategori_slug")
            if not kategori_slug:
                errors.append({"index": i, "idempotency_anahtari": str(idem),
                               "errors": {"kategori_slug": ["Sikayet icin kategori_slug zorunlu."]}})
                continue
            try:
                kategori = Kategori.objects.get(slug=kategori_slug)
            except Kategori.DoesNotExist:
                errors.append({"index": i, "idempotency_anahtari": str(idem),
                               "errors": {"kategori_slug": [f"'{kategori_slug}' kategori yok."]}})
                continue

        elif oturum_tipi == "OZEL_DANISMANLIK":
            # OZEL_DANISMANLIK: danisma kategorisi zorunlu; normal kategori, cevap, oneri yasak
            if d.get("kategori_slug"):
                errors.append({"index": i, "idempotency_anahtari": str(idem),
                               "errors": {"kategori_slug": [
                                   "Ozel danismanlik oturumunda sikayet kategorisi olamaz."
                               ]}})
                continue
            if d.get("cevaplar"):
                errors.append({"index": i, "idempotency_anahtari": str(idem),
                               "errors": {"cevaplar": [
                                   "Ozel danismanlik oturumunda cevap bulunmamali."
                               ]}})
                continue
            if d.get("onerilen_etken_maddeler"):
                errors.append({"index": i, "idempotency_anahtari": str(idem),
                               "errors": {"onerilen_etken_maddeler": [
                                   "Ozel danismanlik oturumunda etken madde onerisi bulunmamali."
                               ]}})
                continue
            # Danisma kategorisi: ID tercih edilir, slug fallback
            danisma_id = d.get("danisma_kategorisi_id")
            if danisma_id:
                danisma_kategorisi = Danisma.objects.filter(id=danisma_id).first()
                if not danisma_kategorisi:
                    errors.append({"index": i, "idempotency_anahtari": str(idem),
                                   "errors": {"danisma_kategorisi_id": [
                                       f"Danisma kategorisi bulunamadi: id={danisma_id}"
                                   ]}})
                    continue
            else:
                danisma_slug = d.get("danisma_kategorisi_slug")
                if not danisma_slug:
                    errors.append({"index": i, "idempotency_anahtari": str(idem),
                                   "errors": {"danisma_kategorisi_slug": [
                                       "Ozel danismanlik icin danisma_kategorisi_id veya slug zorunlu."
                                   ]}})
                    continue
                danisma_kategorisi = Danisma.objects.filter(slug=danisma_slug).first()
                if not danisma_kategorisi:
                    errors.append({"index": i, "idempotency_anahtari": str(idem),
                                   "errors": {"danisma_kategorisi_slug": [
                                       f"'{danisma_slug}' danisma kategorisi yok."
                                   ]}})
                    continue

        try:
            yas = YasAraligi.objects.get(kod=d["yas_araligi_kod"])
        except YasAraligi.DoesNotExist:
            errors.append({"index": i, "idempotency_anahtari": str(idem),
                           "errors": {"yas_araligi_kod": [f"Yas araligi yok: {d['yas_araligi_kod']}"]}})
            continue
        try:
            cins = Cinsiyet.objects.get(kod=d["cinsiyet_kod"])
        except Cinsiyet.DoesNotExist:
            errors.append({"index": i, "idempotency_anahtari": str(idem),
                           "errors": {"cinsiyet_kod": [f"Cinsiyet yok: {d['cinsiyet_kod']}"]}})
            continue

        # QR retry loop
        qr_inserted = None
        last_error: Exception | None = None

        for attempt in range(MAX_QR_RETRY):
            qr_candidate = generate_qr_candidate()
            try:
                with transaction.atomic():
                    instance = OturumLogu(
                        idempotency_anahtari=idem,
                        kiosk=kiosk,
                        oturum_tipi=oturum_tipi,
                        kategori=kategori,
                        danisma_kategorisi=danisma_kategorisi,
                        yas_araligi=yas,
                        cinsiyet=cins,
                        hassas_akis=d.get("hassas_akis", False),
                        qr_kodu=qr_candidate,
                        cevaplar=d.get("cevaplar", {}),
                        onerilen_etken_maddeler=d.get("onerilen_etken_maddeler", []),
                        tamamlandi=d.get("tamamlandi", True),
                    )
                    with UnitOfWork(user=None) as uow:
                        uow.add(instance)

                    kiosk_ts = d.get("olusturulma_tarihi")
                    if kiosk_ts:
                        OturumLogu.objects.filter(pk=instance.pk).update(olusturulma_tarihi=kiosk_ts)

                    # Soru-cevap ve etken madde normalizasyonu
                    # SessionValidationError raise ederse rollback (parent + children)
                    _create_child_records(instance, d)
                    qr_inserted = qr_candidate
                    break

            except SessionValidationError as exc:
                errors.append({
                    "index": i,
                    "idempotency_anahtari": str(idem),
                    "errors": {exc.field: [exc.message]},
                })
                qr_inserted = None
                break

            except IntegrityError as exc:
                err_str = str(exc).lower()
                if "qr_kodu" in err_str or "oturum_loglari_qr" in err_str:
                    last_error = exc
                    if attempt == MAX_QR_RETRY - 1:
                        errors.append({
                            "index": i,
                            "idempotency_anahtari": str(idem),
                            "errors": {"qr_kodu": [
                                f"QR benzersizligi saglanamadi ({MAX_QR_RETRY} denemede)."
                            ]},
                        })
                    continue

                if "idempotency" in err_str:
                    concurrent = OturumLogu.objects.filter(idempotency_anahtari=idem).only("qr_kodu").first()
                    if concurrent:
                        results.append({
                            "idempotency_key": str(idem),
                            "status": "existing",
                            "qr_kodu": concurrent.qr_kodu,
                        })
                    else:
                        errors.append({
                            "index": i,
                            "idempotency_anahtari": str(idem),
                            "errors": {"database": [str(exc)]},
                        })
                    qr_inserted = None
                    break

                errors.append({
                    "index": i,
                    "idempotency_anahtari": str(idem),
                    "errors": {"database": [str(exc)]},
                })
                qr_inserted = None
                break

            except Exception as exc:
                errors.append({
                    "index": i,
                    "idempotency_anahtari": str(idem),
                    "errors": {"database": [str(exc)]},
                })
                qr_inserted = None
                break

        if qr_inserted:
            results.append({
                "idempotency_key": str(idem),
                "status": "created",
                "qr_kodu": qr_inserted,
            })

    return results, errors


def _create_child_records(instance: OturumLogu, d: dict) -> None:
    """OturumCevap ve OturumOnerilenEtkenMadde kayitlarini olusturur.

    Caller bir atomic savepoint icindedir; bu fonksiyon transaction-safe.
    Idempotent: instance yeni olusturuldugunda cagirilir, duplicate olmaz.

    SIKAYET oturumunda soru-cevap eslesmesi ZORUNLUDUR; uyumsuzluk
    SessionValidationError raise eder ve tum transaction'i rollback eder.
    Bu backfill'den FARKLIDIR (backfill null FK + snapshot kullanir).
    """
    is_sikayet = (instance.oturum_tipi == "SIKAYET")

    # Cevap normalizasyonu
    cevaplar = d.get("cevaplar", {})
    if isinstance(cevaplar, dict):
        for soru_id_str, cevap_value in cevaplar.items():
            try:
                soru_id = int(soru_id_str)
            except (ValueError, TypeError):
                if is_sikayet:
                    raise SessionValidationError("cevaplar", f"Gecersiz soru_id anahtari: {soru_id_str!r}")
                continue

            soru = Soru.objects.filter(id=soru_id).first()
            if is_sikayet and soru is None:
                raise SessionValidationError("cevaplar", f"Soru #{soru_id} bulunamadi.")

            cevap = None
            cevap_metin = ""

            if isinstance(cevap_value, (int, str)):
                try:
                    cevap_id = int(cevap_value)
                except (ValueError, TypeError):
                    # Kiosk binary "Y"/"N" degerleri gonderir; cevap_id yerine
                    # snapshot kaydedilir, FK null kalir. Hem SIKAYET hem
                    # diger tipler icin tolere edilir — normalizasyon, hard validation degil.
                    _YN_LABELS = {"Y": "Evet", "N": "Hay\u0131r"}
                    cevap_metin = _YN_LABELS.get(str(cevap_value).upper(), str(cevap_value))
                else:
                    cevap_obj = Cevap.objects.filter(id=cevap_id).first()
                    if cevap_obj is None:
                        if is_sikayet:
                            raise SessionValidationError(
                                "cevaplar", f"Cevap #{cevap_id} bulunamadi."
                            )
                    elif soru and cevap_obj.soru_id != soru_id:
                        if is_sikayet:
                            raise SessionValidationError(
                                "cevaplar",
                                f"Cevap #{cevap_id}, Soru #{soru_id}'e ait degil "
                                f"(cevap.soru_id={cevap_obj.soru_id})."
                            )
                        # Legacy backfill: null FK + snapshot notu
                        cevap_metin = f"[uyumsuz: {cevap_obj.metin}]"
                    else:
                        cevap = cevap_obj
                        cevap_metin = cevap_obj.metin if cevap_obj else ""

            OturumCevap.objects.get_or_create(
                oturum=instance,
                soru=soru,
                defaults={
                    "cevap": cevap,
                    "soru_metni_snapshot": soru.metin if soru else f"Soru #{soru_id}",
                    "cevap_metni_snapshot": cevap_metin,
                    "cevap_degeri_snapshot": str(cevap_value),
                },
            )

    # Etken madde normalizasyonu
    onerilen = d.get("onerilen_etken_maddeler", [])
    if isinstance(onerilen, list):
        for value in onerilen:
            etken_madde = None
            etken_madde_adi = ""

            if isinstance(value, (int, str)):
                try:
                    etken_id = int(value)
                    em = EtkenMadde.objects.filter(id=etken_id).first()
                    if em:
                        etken_madde = em
                        etken_madde_adi = em.ad
                    else:
                        etken_madde_adi = f"Etken Madde #{etken_id}"
                except (ValueError, TypeError):
                    etken_madde_adi = str(value)
            elif isinstance(value, dict):
                etken_id = value.get("id")
                if etken_id:
                    try:
                        em = EtkenMadde.objects.filter(id=int(etken_id)).first()
                        if em:
                            etken_madde = em
                            etken_madde_adi = em.ad
                    except (ValueError, TypeError):
                        pass
                if not etken_madde_adi:
                    etken_madde_adi = value.get("ad", str(value))

            if etken_madde or etken_madde_adi:
                if etken_madde is not None:
                    # FK mevcut — FK uzerinden unique
                    OturumOnerilenEtkenMadde.objects.get_or_create(
                        oturum=instance,
                        etken_madde=etken_madde,
                        defaults={"etken_madde_adi_snapshot": etken_madde_adi},
                    )
                else:
                    # FK null (string isim) — snapshot adi uzerinden unique;
                    # get_or_create(etken_madde=None) birden fazla null kaydi
                    # birlestirirdi (veri kaybi), bu yuzden snapshot da anahtar.
                    OturumOnerilenEtkenMadde.objects.get_or_create(
                        oturum=instance,
                        etken_madde=None,
                        etken_madde_adi_snapshot=etken_madde_adi,
                    )
