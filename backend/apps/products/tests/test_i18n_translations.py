"""Kategori/Soru/Danisma TR/EN ceviri (i18n) testleri.

Kapsam:
  1. build_catalog_payload kategori.ad_en / soru.metin_en / danisma.ad_en icerir
  2. Bos _en alanlari serializer'da bos string olarak doner (Turkce fallback UI'da)
  3. KategoriSerializer (admin) ad_en okur/yazar
  4. SoruSerializer (admin) metin_en okur/yazar
  5. DanismaSerializer (admin) ad_en okur/yazar
"""
from __future__ import annotations

import pytest

from apps.products.models import Danisma, Kategori, Soru
from apps.products.serializers import (
    DanismaSerializer,
    KategoriSerializer,
    SoruSerializer,
)
from apps.products.services import build_catalog_payload


@pytest.mark.django_db
def test_catalog_payload_icerir_en_alanlari():
    kat = Kategori.objects.create(ad="Uyku", ad_en="Sleep", slug="uyku")
    Soru.objects.create(
        kategori=kat, metin="Yorgun musunuz?", metin_en="Are you tired?", sira=1
    )
    Danisma.objects.create(ad="Kadin Sagligi", ad_en="Women's Health", slug="kadin")

    payload = build_catalog_payload()

    kategori = payload["kategoriler"][0]
    assert kategori["ad"] == "Uyku"
    assert kategori["ad_en"] == "Sleep"
    assert kategori["sorular"][0]["metin"] == "Yorgun musunuz?"
    assert kategori["sorular"][0]["metin_en"] == "Are you tired?"

    danisma = payload["danisma_kategorileri"][0]
    assert danisma["ad"] == "Kadin Sagligi"
    assert danisma["ad_en"] == "Women's Health"


@pytest.mark.django_db
def test_catalog_bos_en_bos_string_doner():
    kat = Kategori.objects.create(ad="Enerji", slug="enerji")
    Soru.objects.create(kategori=kat, metin="Yorgun musunuz?", sira=1)

    payload = build_catalog_payload()
    kategori = payload["kategoriler"][0]
    assert kategori["ad_en"] == ""
    assert kategori["sorular"][0]["metin_en"] == ""


@pytest.mark.django_db
def test_kategori_serializer_ad_en_read_write():
    kat = Kategori.objects.create(ad="Uyku", ad_en="Sleep", slug="uyku")
    data = KategoriSerializer(kat).data
    assert data["ad_en"] == "Sleep"

    ser = KategoriSerializer(
        kat, data={"ad": "Uyku", "ad_en": "Deep Sleep", "slug": "uyku"}, partial=True
    )
    assert ser.is_valid(), ser.errors
    updated = ser.save()
    assert updated.ad_en == "Deep Sleep"


@pytest.mark.django_db
def test_soru_serializer_metin_en_read_write():
    kat = Kategori.objects.create(ad="Uyku", slug="uyku")
    soru = Soru.objects.create(
        kategori=kat, metin="Yorgun musunuz?", metin_en="Are you tired?", sira=1
    )
    data = SoruSerializer(soru).data
    assert data["metin_en"] == "Are you tired?"

    ser = SoruSerializer(
        soru, data={"metin_en": "Do you feel tired?"}, partial=True
    )
    assert ser.is_valid(), ser.errors
    updated = ser.save()
    assert updated.metin_en == "Do you feel tired?"


@pytest.mark.django_db
def test_danisma_serializer_ad_en_read_write():
    d = Danisma.objects.create(ad="Kadin Sagligi", ad_en="Women's Health", slug="kadin")
    data = DanismaSerializer(d).data
    assert data["ad_en"] == "Women's Health"

    ser = DanismaSerializer(
        d, data={"ad_en": "Women Health"}, partial=True
    )
    assert ser.is_valid(), ser.errors
    updated = ser.save()
    assert updated.ad_en == "Women Health"


@pytest.mark.django_db
def test_catalog_payload_orders_kategoriler_by_sira():
    Kategori.objects.create(ad="Uyku", slug="uyku", sira=20)
    Kategori.objects.create(ad="Enerji", slug="enerji", sira=10)

    payload = build_catalog_payload()

    assert [item["ad"] for item in payload["kategoriler"]] == ["Enerji", "Uyku"]


@pytest.mark.django_db
def test_kategori_sira_requires_min_1_and_unique_order():
    Kategori.objects.create(ad="Uyku", slug="uyku", sira=1)

    serializer = KategoriSerializer(data={"ad": "Enerji", "slug": "enerji", "sira": 0})
    assert not serializer.is_valid()
    assert "sira" in serializer.errors

    second = Kategori.objects.create(ad="Zihin", slug="zihin", sira=1)
    assert second.sira == 2


@pytest.mark.django_db
def test_kategori_sira_can_repeat_on_different_parent_branches():
    root_a = Kategori.objects.create(ad="Root A", slug="root-a", sira=1)
    root_b = Kategori.objects.create(ad="Root B", slug="root-b", sira=2)

    child_a = Kategori.objects.create(
        ad="Child A-1", slug="child-a-1", bagli_kategori=root_a, sira=1
    )
    child_b = Kategori.objects.create(
        ad="Child B-1", slug="child-b-1", bagli_kategori=root_b, sira=1
    )

    assert child_a.sira == 1
    assert child_b.sira == 1


@pytest.mark.django_db
def test_kategori_sira_auto_shifts_only_within_same_parent_branch():
    root = Kategori.objects.create(ad="Root", slug="root", sira=1)
    Kategori.objects.create(ad="Child 1", slug="child-1", bagli_kategori=root, sira=1)

    child_2 = Kategori.objects.create(ad="Child 2", slug="child-2", bagli_kategori=root, sira=1)
    assert child_2.sira == 2
