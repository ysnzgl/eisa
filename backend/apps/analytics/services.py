"""Analitik domain servisleri.

Kiosk oturum (session) toplu-yazma is mantigi burada tek noktada tutulur ve
`kiosk_api` facade tarafindan yeniden kullanilir. View'lar bu mantigi
kopyalamaz.
"""
from __future__ import annotations

from typing import Any

from apps.core.uow import UnitOfWork
from apps.lookups.models import Cinsiyet, YasAraligi
from apps.products.models import Kategori

from .models import OturumLogu
from .serializers import OturumLoguItemSerializer


def ingest_session_items(kiosk, items: list[Any]) -> tuple[list[str], list[dict]]:
    """Kiosk'tan gelen oturum kayitlarini idempotent sekilde yazar.

    `kiosk` dogrulanmis Kiosk ornegidir (auth context'ten gelir). Payload'daki
    kiosk bilgisine GUVENILMEZ; kayit her zaman `kiosk` ile iliskilendirilir.

    Doner: (accepted_keys, errors)
    """
    accepted: list[str] = []
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

        if OturumLogu.objects.filter(idempotency_anahtari=idem).exists():
            accepted.append(str(idem))
            continue

        try:
            kategori = Kategori.objects.get(slug=d["kategori_slug"])
        except Kategori.DoesNotExist:
            errors.append({"index": i, "idempotency_anahtari": str(idem),
                           "errors": {"kategori_slug": [f"'{d['kategori_slug']}' kategori yok."]}})
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

        instance = OturumLogu(
            idempotency_anahtari=idem,
            kiosk=kiosk,
            kategori=kategori,
            yas_araligi=yas,
            cinsiyet=cins,
            hassas_akis=d.get("hassas_akis", False),
            qr_kodu=d["qr_kodu"],
            cevaplar=d.get("cevaplar", {}),
            onerilen_etken_maddeler=d.get("onerilen_etken_maddeler", []),
            tamamlandi=d.get("tamamlandi", True),
        )
        with UnitOfWork(user=None) as uow:
            uow.add(instance)
        kiosk_ts = d.get("olusturulma_tarihi")
        if kiosk_ts:
            OturumLogu.objects.filter(pk=instance.pk).update(olusturulma_tarihi=kiosk_ts)
        accepted.append(str(idem))

    return accepted, errors
