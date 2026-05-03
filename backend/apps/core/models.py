"""
Cekirdek (Core) Entity tanimlari.

Sistemdeki tum is-mantigi tablolari `BaseModel`'den turer. Lookup tablolari
(Il, Ilce, Cinsiyet, YasAraligi vb.) bu kalitimdan haric tutulur — onlarin
kendi sade bir abstract'i (`LookupModel`) vardir.

Yazma islemleri MUTLAKA `apps.core.uow.UnitOfWork` uzerinden yapilmalidir.
Modeller icinde save() override'lari YOKTUR.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class BaseModel(models.Model):
    """
    Tum is-mantigi tablolarinin uzerine kurulacagi soyut base.

    Kolonlar:
      - olusturulma_tarihi  : INSERT aninda set edilir.
      - olusturan           : INSERT aninda UoW tarafindan set edilir.
      - guncellenme_tarihi  : Her UPDATE'de UoW tarafindan set edilir.
      - guncelleyen         : Her UPDATE'de UoW tarafindan set edilir.
      - surum               : Optimistic Concurrency icin (UoW her UPDATE'de +1).
    """

    olusturulma_tarihi = models.DateTimeField(auto_now_add=True, db_index=True)
    olusturan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        editable=False,
    )
    guncellenme_tarihi = models.DateTimeField(auto_now_add=True)
    guncelleyen = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        editable=False,
    )
    surum = models.PositiveIntegerField(default=1, editable=False)

    class Meta:
        abstract = True


class LookupModel(models.Model):
    """
    Sabit (lookup) tablolari icin sade abstract.
    Audit/version kolonlari TASIMAZ — referans verisidir, "save edilmez".
    """

    class Meta:
        abstract = True
