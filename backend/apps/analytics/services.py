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
from django.utils import timezone

from apps.core.uow import UnitOfWork
from apps.lookups.models import Cinsiyet, YasAraligi
from apps.products.models import Cevap, Danisma, EtkenMadde, Kategori, Soru

from .models import OturumCevap, OturumLogu, OturumOnerilenEtkenMadde
from .serializers import OturumLoguItemSerializer


QR_ALPHABET = string.ascii_uppercase + string.digits  # A-Z, 0-9
QR_LENGTH = 8
MAX_QR_RETRY = 5
_QR_RE = re.compile(r'^[A-Z0-9]{8}$')

# Crockford Base32 — yeni 9 karakterli kiosk QR formatı
CROCKFORD_ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
_CROCKFORD_RE = re.compile(r'^[0123456789ABCDEFGHJKMNPQRSTVWXYZ]{9}$')


def _crockford_checksum_valid(code: str) -> bool:
    """9 karakterli Crockford QR için checksum doğrulama."""
    if len(code) != 9:
        return False
    try:
        total = sum(CROCKFORD_ALPHABET.index(c) * (i + 1) for i, c in enumerate(code[:8]))
        return code[8] == CROCKFORD_ALPHABET[total % 32]
    except ValueError:
        return False


def _parse_kiosk_prefix(code: str) -> int:
    """QR kodunun ilk karakterini Crockford alphabetindeki sıra numarasına çevirir."""
    try:
        return CROCKFORD_ALPHABET.index(code[0])
    except (ValueError, IndexError):
        return -1


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

    QR kodu kararı:
    - Payload'da 9 karakterli Crockford QR varsa → kiosk üretmiş; doğrula ve kabul et.
    - QR yoksa (eski kiosk / tamamlandi=False) → backend 8 karakterli üretir.
    - tamamlandi=False → qr_kodu null bırakılır (abandoned session).

    Doğrulama (Crockford QR):
    - Format: CROCKFORD_ALPHABET, 9 karakter
    - Checksum: son karakter kontrolü
    - Prefix: code[0] == CROCKFORD_ALPHABET[kiosk.eczane_kiosk_no] kontrolü
    - Eczane unique: aynı (eczane, qr_kodu) daha önce farklı idempotency ile kaydedilmemeli

    Idempotency: Ayni idempotency_anahtari tekrar gelirse mevcut kayit ve
    QR kodu dogrudan doner (yeni kayit olusturulmaz, child'lar tekrarlanmaz).

    Doner: (results, errors)
      results: [{"idempotency_key": str, "status": "created"|"existing", "qr_kodu": str}]
      errors:  [{"index": int, "idempotency_anahtari": str, "errors": dict}]
    """
    results: list[dict] = []
    errors: list[dict] = []
    now = timezone.now()
    # eczane FK — ingest sırasında daima auth kiosk'tan alınır
    eczane = kiosk.eczane

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

        tamamlandi = d.get("tamamlandi", True)

        # ── QR kodu kararı ────────────────────────────────────────────────────
        # Kiosk 9 karakterli Crockford QR gönderdiyse doğrula ve kabul et.
        # Göndermedi (eski kiosk / abandoned) → backend üretir veya null bırakır.
        incoming_qr = (d.get("qr_kodu") or "").strip().upper() or None
        kiosk_generated_qr: str | None = None
        legacy_generate = False  # backend QR üretimi tetiklenecek mi?

        if incoming_qr and _CROCKFORD_RE.match(incoming_qr):
            # Yeni format: checksum doğrula
            if not _crockford_checksum_valid(incoming_qr):
                errors.append({"index": i, "idempotency_anahtari": str(idem),
                               "errors": {"qr_kodu": ["Geçersiz QR checksum."]}})
                continue
            # Prefix: kiosk.eczane_kiosk_no ile eşleşmeli
            if kiosk.eczane_kiosk_no is not None:
                expected_prefix = CROCKFORD_ALPHABET[kiosk.eczane_kiosk_no]
                if incoming_qr[0] != expected_prefix:
                    errors.append({"index": i, "idempotency_anahtari": str(idem),
                                   "errors": {"qr_kodu": [
                                       f"QR prefix uyumsuz: beklenen '{expected_prefix}'."
                                   ]}})
                    continue
            # Eczane conflict: aynı QR aynı eczanede farklı idempotency ile var mı?
            if eczane:
                conflict = (
                    OturumLogu.objects
                    .filter(eczane=eczane, qr_kodu=incoming_qr)
                    .exclude(idempotency_anahtari=idem)
                    .exists()
                )
                if conflict:
                    errors.append({"index": i, "idempotency_anahtari": str(idem),
                                   "errors": {"qr_kodu": [
                                       "Bu QR kodu eczanede zaten kayıtlı."
                                   ]}})
                    continue
            kiosk_generated_qr = incoming_qr
        elif tamamlandi and not incoming_qr:
            # Eski kiosk: backend üretecek
            legacy_generate = True
        elif not tamamlandi:
            # Abandoned: QR yok
            pass
        elif incoming_qr and not _CROCKFORD_RE.match(incoming_qr):
            # Eski 8-char legacy QR gönderilmiş → backend üretir (geçiş dönemi uyumu)
            legacy_generate = True

        # QR retry loop — yalnız backend üretimi için
        qr_inserted: str | None = None
        insert_success = False
        last_error: Exception | None = None

        for attempt in range(MAX_QR_RETRY):
            qr_candidate = (
                kiosk_generated_qr if kiosk_generated_qr
                else (generate_qr_candidate() if legacy_generate else None)
            )
            try:
                with transaction.atomic():
                    instance = OturumLogu(
                        idempotency_anahtari=idem,
                        kiosk=kiosk,
                        eczane=eczane,
                        oturum_tipi=oturum_tipi,
                        kategori=kategori,
                        danisma_kategorisi=danisma_kategorisi,
                        yas_araligi=yas,
                        cinsiyet=cins,
                        hassas_akis=d.get("hassas_akis", False),
                        qr_kodu=qr_candidate,
                        cevaplar=d.get("cevaplar", {}),
                        onerilen_etken_maddeler=d.get("onerilen_etken_maddeler", []),
                        tamamlandi=tamamlandi,
                        durum=(
                            OturumLogu.Durum.COMPLETED
                            if tamamlandi
                            else OturumLogu.Durum.ABANDONED
                        ),
                        cihaz_zamani=d.get("olusturulma_tarihi"),
                        sunucu_zamani=now,
                    )
                    # barkod_logo_id: kiosk payload'ından gelen opsiyonel alan.
                    # Gecikmiş outbox kaydında logo artık pasif/silinmiş olabilir → SET_NULL ile kabul edilir.
                    # Eski payload'lar bu alanı içermeyebilir → None ile çalışmaya devam eder.
                    raw_logo_id = d.get("barkod_logo_id")
                    if raw_logo_id:
                        from apps.barkod_logo.models import BarkodLogo
                        logo = BarkodLogo.objects.filter(pk=raw_logo_id).first()
                        if logo:
                            instance.barkod_logo = logo
                    with UnitOfWork(user=None) as uow:
                        uow.add(instance)

                    # Soru-cevap ve etken madde normalizasyonu
                    # SessionValidationError raise ederse rollback (parent + children)
                    _create_child_records(instance, d)
                    qr_inserted = qr_candidate
                    insert_success = True
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
                if any(k in err_str for k in ("qr_kodu", "oturum_loglari_qr", "uniq_oturum_eczane_qr")):
                    last_error = exc
                    if attempt == MAX_QR_RETRY - 1 or kiosk_generated_qr:
                        errors.append({
                            "index": i,
                            "idempotency_anahtari": str(idem),
                            "errors": {"qr_kodu": [
                                "QR eczanede zaten kayıtlı." if kiosk_generated_qr
                                else f"QR benzersizligi saglanamadi ({MAX_QR_RETRY} denemede)."
                            ]},
                        })
                        break
                    continue  # backend üretiminde yeni aday dene

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

        if insert_success:
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
                    # String name — try to resolve to a DB record by name
                    etken_madde_adi = str(value)
                    em = EtkenMadde.objects.filter(ad__iexact=etken_madde_adi).first()
                    if em:
                        etken_madde = em
                        etken_madde_adi = em.ad
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
                    # Try name lookup for dict entries too
                    name = value.get("ad", "")
                    if name:
                        em = EtkenMadde.objects.filter(ad__iexact=name).first()
                        if em:
                            etken_madde = em
                            etken_madde_adi = em.ad
                        else:
                            etken_madde_adi = name

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
