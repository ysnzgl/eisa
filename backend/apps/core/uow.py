"""
Unit of Work (UoW) — Merkezi Transaction Yoneticisi.

Django'nun `instance.save()` cagrilarini her yere dagitmak yerine, butun yazma
islemlerini bu modul uzerinden gecirir. Bu sayede:

  * `olusturulma_tarihi` / `guncellenme_tarihi` damgalari,
  * `olusturan` / `guncelleyen` kullanici izleri,
  * `surum` (optimistic concurrency) artislari

modellerin icinde save() override'i olmadan, MERKEZI bir yerden uygulanir.

Kullanim:

    from apps.core.uow import UnitOfWork

    with UnitOfWork(user=request.user) as uow:
        eczane = Eczane(ad="Demo", il=il, ilce=ilce)
        uow.add(eczane)               # INSERT (olusturan + olusturulma)
        eczane.adres = "Yeni adres"
        uow.update(eczane)            # UPDATE (guncelleyen + surum +1)
        # uow.delete(eczane)          # DELETE (audit alinabilir, opsiyonel)

Bir `with` blogu icindeki butun islemler tek bir `transaction.atomic` icinde
calisir; herhangi biri hata verirse hepsi rollback olur.
"""
from __future__ import annotations

from typing import Iterable, Optional

from django.db import transaction
from django.db.models import F
from django.utils import timezone


class ConcurrencyError(Exception):
    """Optimistic concurrency uyusmazligi — kayit baska biri tarafindan guncellenmis."""


class UnitOfWork:
    """Tek bir is-birimi (atomic transaction) icindeki yazma islemlerini yonetir."""

    def __init__(self, user=None):
        self._user = user if (user is not None and getattr(user, "pk", None)) else None
        self._atomic = None

    # ── Baglam yonetimi ────────────────────────────────────────────────

    def __enter__(self) -> "UnitOfWork":
        self._atomic = transaction.atomic()
        self._atomic.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._atomic.__exit__(exc_type, exc, tb)

    # ── BaseModel kontrolu ─────────────────────────────────────────────

    @staticmethod
    def _is_base_model(instance) -> bool:
        """instance, BaseModel'den (audit kolonlari olan) turuyorsa True."""
        return all(
            hasattr(instance, attr)
            for attr in ("olusturan_id", "guncelleyen_id", "surum")
        )

    # ── INSERT ─────────────────────────────────────────────────────────

    def add(self, instance, **save_kwargs):
        """
        Yeni bir kaydi insert eder. olusturan/guncelleyen ve surum=1 set edilir.
        BaseModel disindaki modeller icin (Lookup vb.) sadece save() yapilir.
        """
        if self._is_base_model(instance):
            instance.olusturan = self._user
            instance.guncelleyen = self._user
            instance.surum = 1
            now = timezone.now()
            # auto_now_add INSERT'te zaten doldurur; ama biz consistency icin override etmiyoruz.
            instance.guncellenme_tarihi = now
        instance.save(**save_kwargs)
        return instance

    # ── UPDATE (Optimistic Concurrency) ────────────────────────────────

    def update(self, instance, *, expected_version: Optional[int] = None, update_fields: Optional[Iterable[str]] = None):
        """
        Mevcut kaydi gunceller. surum +1 artirilir.

        `expected_version` verilirse, UPDATE WHERE pk=... AND surum=expected
        kullanir; satir etkilemezse `ConcurrencyError` atilir (someone-else-wrote
        senaryosu). Verilmezse instance.surum kullanilir (otomatik).

        BaseModel disindaki modeller icin standart save() yapilir.
        """
        if not self._is_base_model(instance):
            instance.save(update_fields=list(update_fields) if update_fields else None)
            return instance

        if instance.pk is None:
            raise ValueError("update() yalnizca kayitli (pk'li) instance icin cagrilabilir.")

        check_version = expected_version if expected_version is not None else instance.surum
        now = timezone.now()

        # 1) Veri alanlarini guncelle (bilinen alanlar)
        cls = instance.__class__
        if update_fields is not None:
            fields_to_save = list(update_fields)
        else:
            # Tum yerel alanlar (audit/timestamp/surum HARIC) — performans icin yeterli.
            fields_to_save = [
                f.attname
                for f in cls._meta.local_concrete_fields
                if f.attname
                not in (
                    "id",
                    "olusturulma_tarihi",
                    "olusturan_id",
                    "guncellenme_tarihi",
                    "guncelleyen_id",
                    "surum",
                )
            ]

        # 2) Optimistic concurrency: WHERE surum=check_version
        instance.guncelleyen = self._user
        instance.guncellenme_tarihi = now
        # surum'u in-memory'de bir arttiralim (geri yansitilacak)
        instance.surum = check_version + 1

        save_fields = list(set(fields_to_save) | {"guncelleyen_id", "guncellenme_tarihi", "surum"})

        affected = cls.objects.filter(pk=instance.pk, surum=check_version).update(
            **{name: getattr(instance, name) for name in save_fields}
        )
        if affected == 0:
            raise ConcurrencyError(
                f"{cls.__name__}#{instance.pk} kaydi baska bir islem tarafindan guncellenmis "
                f"(beklenen surum={check_version})."
            )
        return instance

    # ── DELETE ─────────────────────────────────────────────────────────

    def delete(self, instance):
        instance.delete()


# ── Standalone yardimcilar (tek seferlik islemler icin) ────────────────────

def save_new(instance, *, user=None):
    """Tek satirlik kisa-yol: INSERT."""
    with UnitOfWork(user=user) as uow:
        return uow.add(instance)


def save_update(instance, *, user=None, expected_version: Optional[int] = None, update_fields=None):
    """Tek satirlik kisa-yol: UPDATE."""
    with UnitOfWork(user=user) as uow:
        return uow.update(instance, expected_version=expected_version, update_fields=update_fields)
