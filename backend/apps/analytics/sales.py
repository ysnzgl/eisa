"""Oturum inceleme ve satış sonucu geçişlerinin tek yazma noktası."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.uow import UnitOfWork
from apps.products.models import EtkenMadde

from .models import OturumLogu, OturumOnerilenEtkenMadde


@transaction.atomic
def mark_reviewed(*, session_id, pharmacy_id, user):
    session = OturumLogu.objects.select_for_update().filter(
        pk=session_id, eczane_id=pharmacy_id
    ).first()
    if session is None:
        return None
    if session.status == OturumLogu.SatisDurumu.BEKLIYOR:
        session.status = OturumLogu.SatisDurumu.INCELENDI
        session.sold = None
        with UnitOfWork(user=user) as uow:
            uow.update(session, update_fields=["status", "sold"])
    return session


@transaction.atomic
def complete_sale(*, session_id, pharmacy_id, user, sale_result, note="", ingredient_ids=None):
    session = OturumLogu.objects.select_for_update().filter(
        pk=session_id, eczane_id=pharmacy_id
    ).first()
    if session is None:
        return None

    target = {
        "sold": OturumLogu.SatisDurumu.SATIS_YAPILDI,
        "not_sold": OturumLogu.SatisDurumu.SATIS_YAPILMADI,
    }.get(sale_result)
    if target is None:
        raise ValidationError({"detail": "Satış sonucu 'sold' veya 'not_sold' olmalıdır."})
    if session.status in (
        OturumLogu.SatisDurumu.SATIS_YAPILDI,
        OturumLogu.SatisDurumu.SATIS_YAPILMADI,
    ):
        return session

    raw_ids = ingredient_ids or []
    try:
        ids = list(dict.fromkeys(int(value) for value in raw_ids))
    except (TypeError, ValueError):
        raise ValidationError({"ingredient_ids": "Etken maddeler geçerli sayısal ID olmalıdır."})
    if target == OturumLogu.SatisDurumu.SATIS_YAPILMADI and ids:
        raise ValidationError({"ingredient_ids": "Etken madde seçiliyken satış yapılmadı sonucu kaydedilemez."})

    ingredients = {item.id: item for item in EtkenMadde.objects.filter(id__in=ids, aktif=True)}
    missing = sorted(set(ids) - set(ingredients))
    if missing:
        raise ValidationError({"ingredient_ids": f"Geçersiz veya pasif etken madde ID'leri: {missing}"})
    if target == OturumLogu.SatisDurumu.SATIS_YAPILDI and session.oturum_tipi != OturumLogu.OturumTipi.OZEL_DANISMANLIK:
        if not ids and not str(note).strip():
            raise ValidationError({"detail": "En az bir etken madde seçin veya danışma notu girin."})

    if target == OturumLogu.SatisDurumu.SATIS_YAPILDI:
        for ingredient in ingredients.values():
            OturumOnerilenEtkenMadde.objects.get_or_create(
                oturum=session,
                etken_madde=ingredient,
                defaults={"etken_madde_adi_snapshot": ingredient.ad, "satildi": True},
            )
        rows = OturumOnerilenEtkenMadde.objects.filter(oturum=session)
        rows.update(satildi=False)
        rows.filter(etken_madde_id__in=ids).update(satildi=True)
    else:
        OturumOnerilenEtkenMadde.objects.filter(oturum=session).update(satildi=False)

    now = timezone.now()
    session.status = target
    session.result_at = now
    session.sold = target == OturumLogu.SatisDurumu.SATIS_YAPILDI
    session.danisma_tamamlandi = True
    session.danisma_tamamlanma_tarihi = now
    session.danisma_tamamlayan_eczaci = user
    session.danisma_notu = note or ""
    with UnitOfWork(user=user) as uow:
        uow.update(session, update_fields=[
            "status", "result_at", "sold", "danisma_tamamlandi",
            "danisma_tamamlanma_tarihi", "danisma_tamamlayan_eczaci_id", "danisma_notu",
        ])
    return session
