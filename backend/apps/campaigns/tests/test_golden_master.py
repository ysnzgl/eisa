"""Faz 0 — Golden-master / characterization testleri.

Bu dosya mevcut ``PlaylistGenerator`` davranışını değiştirmeden kilitler.
Her test, kodun şu anki çıktısını "doğru" olarak tanımlar; hiç bir assertion
kasıtlı olarak yeni davranış talep etmez.

V2 motoru (Faz 2+) bu testleri kırmadan geçmek zorundadır.
Faz 1 additive-schema değişiklikleri bu testleri kırmamalıdır.

Senaryolar (K1 — plan.md Faz 0 kabul kriteri):
  01  gm_single_per_hour_all_kiosks
  02  gm_per_day_even_distribution
  03  gm_per_loop_legacy_multiplicity
  04  gm_target_il_only
  05  gm_target_ilce_only
  06  gm_target_eczane_specific
  07  gm_legacy_target_pharmacies_m2m
  08  gm_no_target_means_all_current
  09  gm_priority_ordering_two_campaigns
  10  gm_guaranteed_flag_ordering
  11  gm_house_ad_filler_fill
  12  gm_multi_creative_first_only
  13  gm_hourly_offset_absolute_0_3599   (ek güvence)
  14  gm_date_range_boundary             (ek güvence)
"""
from __future__ import annotations

import datetime as _dt
import uuid
from collections import Counter

import pytest
from django.utils import timezone

from apps.campaigns.models import (
    Campaign,
    CampaignTarget,
    Creative,
    HouseAd,
    Playlist,
    PlaylistItem,
    ScheduleRule,
)
from apps.campaigns.services.scheduler import generate_for_kiosk
from apps.lookups.models import Il, Ilce
from apps.pharmacies.models import Eczane, Kiosk


# ─────────────────────────────────────────────────────────────────────────────
# Yardımcı fabrikalar
# ─────────────────────────────────────────────────────────────────────────────

TODAY = _dt.date(2026, 7, 21)  # sabit tarih — deterministik seed için
# TODAY'ın midnight'ı (timezone-aware) — tarih hesaplamaları için baz
_TODAY_START = None  # lazy init — Django kurulumundan sonra hesaplanır


def _today_start() -> "_dt.datetime":
    """TODAY'ın timezone-aware midnight değeri.

    `timezone.now() - 1 day` yerine sabit TODAY kullanmak zorundayız;
    aksi hâlde scheduler noon filtresi saat 12'den sonra başarısız olur
    (start_date UTC > noon_UTC → kampanya filtreye takılır).
    """
    return timezone.make_aware(_dt.datetime.combine(TODAY, _dt.time(0, 0)))


def _campaign(
    name: str,
    start_offset_days: int = -1,
    end_offset_days: int = 30,
    status: str = "ACTIVE",
    priority: int = 50,
) -> Campaign:
    base = _today_start()
    return Campaign.objects.create(
        name=name,
        start_date=base + _dt.timedelta(days=start_offset_days),
        end_date=base + _dt.timedelta(days=end_offset_days),
        status=status,
        priority=priority,
        target_scope="ALL",
    )


def _creative(campaign: Campaign, duration: int, url_suffix: str = "") -> Creative:
    return Creative.objects.create(
        campaign=campaign,
        media_url=f"https://cdn.example.com/{campaign.pk}{url_suffix}.mp4",
        duration_seconds=duration,
    )


def _rule(
    campaign: Campaign,
    freq_type: str,
    freq_value: int,
    target_hours: list | None = None,
) -> ScheduleRule:
    return ScheduleRule.objects.create(
        campaign=campaign,
        frequency_type=freq_type,
        frequency_value=freq_value,
        target_hours=target_hours,
    )


def _kiosk(eczane: Eczane, suffix: str = "") -> Kiosk:
    mac = f"AA:BB:CC:DD:EE:{suffix[:2].upper().zfill(2)}" if suffix else "AA:BB:CC:DD:EE:FF"
    return Kiosk.objects.create(
        eczane=eczane,
        mac_adresi=mac,
        uygulama_anahtari=f"key-{uuid.uuid4().hex}",
        aktif=True,
    )


def _items_for_hour(kiosk: Kiosk, hour: int) -> list[PlaylistItem]:
    pl = Playlist.objects.get(kiosk=kiosk, target_date=TODAY, target_hour=hour)
    return list(pl.items.select_related("creative", "house_ad").order_by("playback_order"))


def _creative_ids_in_hour(kiosk: Kiosk, hour: int) -> set[uuid.UUID]:
    return {i.creative_id for i in _items_for_hour(kiosk, hour) if i.creative_id}


def _total_duration_per_loop(kiosk: Kiosk, hour: int, loop_sec: int = 60) -> dict[int, int]:
    """Loop indeksi → o looptaki toplam süre (saniye)."""
    used: dict[int, int] = {}
    for item in _items_for_hour(kiosk, hour):
        idx = int(item.estimated_start_offset_seconds) // loop_sec
        dur = (
            item.creative.duration_seconds
            if item.creative_id
            else item.house_ad.duration_seconds
        )
        used[idx] = used.get(idx, 0) + int(dur)
    return used


# ─────────────────────────────────────────────────────────────────────────────
# Paylaşılan fixture'lar
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def il_istanbul(db) -> Il:
    il, _ = Il.objects.get_or_create(ad="Istanbul")
    return il


@pytest.fixture
def il_ankara(db) -> Il:
    il, _ = Il.objects.get_or_create(ad="Ankara")
    return il


@pytest.fixture
def ilce_kadikoy(db, il_istanbul) -> Ilce:
    ilce, _ = Ilce.objects.get_or_create(il=il_istanbul, ad="Kadikoy")
    return ilce


@pytest.fixture
def ilce_besiktas(db, il_istanbul) -> Ilce:
    ilce, _ = Ilce.objects.get_or_create(il=il_istanbul, ad="Besiktas")
    return ilce


@pytest.fixture
def eczane_kadikoy(db, il_istanbul, ilce_kadikoy) -> Eczane:
    return Eczane.objects.create(ad="Kadikoy Eczanesi", il=il_istanbul, ilce=ilce_kadikoy)


@pytest.fixture
def eczane_besiktas(db, il_istanbul, ilce_besiktas) -> Eczane:
    return Eczane.objects.create(ad="Besiktas Eczanesi", il=il_istanbul, ilce=ilce_besiktas)


@pytest.fixture
def eczane_ankara(db, il_ankara) -> Eczane:
    ilce_ankara, _ = Ilce.objects.get_or_create(
        il=il_ankara, ad="Cankaya"
    )
    return Eczane.objects.create(ad="Ankara Eczanesi", il=il_ankara, ilce=ilce_ankara)


@pytest.fixture
def kiosk_kadikoy(db, eczane_kadikoy) -> Kiosk:
    return _kiosk(eczane_kadikoy, suffix="KD")


@pytest.fixture
def kiosk_besiktas(db, eczane_besiktas) -> Kiosk:
    return _kiosk(eczane_besiktas, suffix="BK")


@pytest.fixture
def kiosk_ankara(db, eczane_ankara) -> Kiosk:
    return _kiosk(eczane_ankara, suffix="AK")


@pytest.fixture
def house_ad_10s(db) -> HouseAd:
    return HouseAd.objects.create(
        name="Filler 10s",
        media_url="https://cdn.example.com/filler10.mp4",
        duration_seconds=10,
        priority=100,
        aktif=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GM-01  tek PER_HOUR kampanya, hedef yok → tüm kiosklar
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_gm_single_per_hour_all_kiosks(kiosk_kadikoy, kiosk_besiktas, house_ad_10s):
    """Hedefsiz aktif PER_HOUR kampanya her kioskun her saatinde görünmeli.

    Mevcut davranış (golden): hedef yoksa _campaign_targets_eczane → True.
    Her saat için kampanya creative'i en az 1 defa yerleştirilir.
    """
    camp = _campaign("GM01")
    creative = _creative(camp, duration=15)
    _rule(camp, "PER_HOUR", 1)

    for k in [kiosk_kadikoy, kiosk_besiktas]:
        playlists = generate_for_kiosk(k, TODAY)
        assert len(playlists) == 24, f"kiosk={k.pk}: 24 playlist bekleniyor"
        for pl in playlists:
            hour_items = list(pl.items.select_related("creative").all())
            creative_ids = {i.creative_id for i in hour_items if i.creative_id}
            assert creative.pk in creative_ids, (
                f"kiosk={k.pk} saat={pl.target_hour}: creative bulunamadi"
            )


# ─────────────────────────────────────────────────────────────────────────────
# GM-02  PER_DAY dağılım snapshot'ı
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_gm_per_day_even_distribution(kiosk_kadikoy, house_ad_10s):
    """PER_DAY=4: gün boyunca toplam 4 loop'a creative yerleşmeli.

    Mevcut davranış (golden): _pass3_per_day, rng.shuffle(all_loops)[:f].
    Bu test toplam sayıyı kilitler; loop dağılımı snapshot'ını kilitlemez
    (rng deterministic olduğundan aynı seed → aynı seçim).
    """
    camp = _campaign("GM02")
    creative = _creative(camp, duration=15)
    _rule(camp, "PER_DAY", 4)

    generate_for_kiosk(kiosk_kadikoy, TODAY)

    # 24 saatteki tüm playlistlerdeki creative loop sayısını topla
    total_loops_with_creative = 0
    for hour in range(24):
        items = _items_for_hour(kiosk_kadikoy, hour)
        loop_sec = 60
        loops_with_c: set[int] = set()
        for item in items:
            if item.creative_id == creative.pk:
                idx = int(item.estimated_start_offset_seconds) // loop_sec
                loops_with_c.add(idx)
        total_loops_with_creative += len(loops_with_c)

    assert total_loops_with_creative == 4, (
        f"PER_DAY=4 → 4 loop bekleniyor, bulundu={total_loops_with_creative}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# GM-03  PER_LOOP legacy çoklu yerleşim
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_gm_per_loop_legacy_multiplicity(kiosk_kadikoy, house_ad_10s):
    """PER_LOOP freq=2, dur=15: her loop'ta 2 creative slot, 0s ve 30s offset.

    Mevcut davranış (golden): spacing = 60/2 = 30; k=0→offset=0, k=1→offset=30.
    """
    camp = _campaign("GM03")
    creative = _creative(camp, duration=15)
    _rule(camp, "PER_LOOP", 2)

    generate_for_kiosk(kiosk_kadikoy, TODAY)

    # Saat 0'ı incele; loop 0 = offset 0..59
    items_h0 = _items_for_hour(kiosk_kadikoy, 0)
    loop0_creative_offsets = sorted(
        int(i.estimated_start_offset_seconds)
        for i in items_h0
        if i.creative_id == creative.pk
        and i.estimated_start_offset_seconds < 60  # loop 0
    )
    assert loop0_creative_offsets == [0, 30], (
        f"PER_LOOP=2 dur=15 → loop0 offset'ler [0,30] bekleniyor, bulundu={loop0_creative_offsets}"
    )

    # Her looptan 2 creative: toplam loop sayısı 60 (60 loop/saat × 1 saat)
    # Sadece saat=0 için kontrol yeterli; diğer saatler aynı mantık.
    loop_creative_count: Counter[int] = Counter()
    for item in items_h0:
        if item.creative_id == creative.pk:
            idx = int(item.estimated_start_offset_seconds) // 60
            loop_creative_count[idx] += 1
    assert all(cnt == 2 for cnt in loop_creative_count.values()), (
        f"Her loop'ta 2 creative bekleniyor: {dict(loop_creative_count)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# GM-04  IL hedefli kampanya — yalnız eşleşen il
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_gm_target_il_only(
    kiosk_kadikoy, kiosk_ankara, il_istanbul, house_ad_10s
):
    """IL=Istanbul → yalnız Istanbul kiosklarına yayınlanmalı; Ankara kiosku atlanmalı."""
    camp = _campaign("GM04")
    creative = _creative(camp, duration=15)
    _rule(camp, "PER_HOUR", 1)
    CampaignTarget.objects.create(
        campaign=camp,
        target_type=CampaignTarget.TargetType.IL,
        il=il_istanbul,
    )

    generate_for_kiosk(kiosk_kadikoy, TODAY)
    generate_for_kiosk(kiosk_ankara, TODAY)

    # Istanbul kiosku → creative var
    assert creative.pk in _creative_ids_in_hour(kiosk_kadikoy, 9), (
        "IL=Istanbul → Kadikoy kiosku creative bekleniyor"
    )
    # Ankara kiosku → creative yok
    assert creative.pk not in _creative_ids_in_hour(kiosk_ankara, 9), (
        "IL=Istanbul → Ankara kiosku creative içermemeli"
    )


# ─────────────────────────────────────────────────────────────────────────────
# GM-05  ILCE hedefli kampanya
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_gm_target_ilce_only(
    kiosk_kadikoy, kiosk_besiktas, ilce_kadikoy, house_ad_10s
):
    """ILCE=Kadikoy → yalnız Kadikoy kiosku; Besiktas atlanmalı."""
    camp = _campaign("GM05")
    creative = _creative(camp, duration=15)
    _rule(camp, "PER_HOUR", 1)
    CampaignTarget.objects.create(
        campaign=camp,
        target_type=CampaignTarget.TargetType.ILCE,
        ilce=ilce_kadikoy,
    )

    generate_for_kiosk(kiosk_kadikoy, TODAY)
    generate_for_kiosk(kiosk_besiktas, TODAY)

    assert creative.pk in _creative_ids_in_hour(kiosk_kadikoy, 10)
    assert creative.pk not in _creative_ids_in_hour(kiosk_besiktas, 10)


# ─────────────────────────────────────────────────────────────────────────────
# GM-06  ECZANE hedefli kampanya — tek spesifik eczane
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_gm_target_eczane_specific(
    kiosk_kadikoy, kiosk_besiktas, eczane_kadikoy, house_ad_10s
):
    """ECZANE=eczane_kadikoy → yalnız bu eczanedeki kiosk; Besiktas atlanmalı."""
    camp = _campaign("GM06")
    creative = _creative(camp, duration=15)
    _rule(camp, "PER_HOUR", 1)
    CampaignTarget.objects.create(
        campaign=camp,
        target_type=CampaignTarget.TargetType.ECZANE,
        eczane=eczane_kadikoy,
    )

    generate_for_kiosk(kiosk_kadikoy, TODAY)
    generate_for_kiosk(kiosk_besiktas, TODAY)

    assert creative.pk in _creative_ids_in_hour(kiosk_kadikoy, 14)
    assert creative.pk not in _creative_ids_in_hour(kiosk_besiktas, 14)


# ─────────────────────────────────────────────────────────────────────────────
# GM-07  Legacy target_pharmacies M2M
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_gm_legacy_target_pharmacies_m2m(
    kiosk_kadikoy, kiosk_besiktas, eczane_kadikoy, house_ad_10s
):
    """CampaignTarget yokken legacy M2M devreye girmeli.

    Mevcut davranış (golden): _campaign_targets_eczane →
    CampaignTarget yok → legacy M2M → sadece listedeki eczane eşleşir.
    """
    camp = _campaign("GM07")
    creative = _creative(camp, duration=15)
    _rule(camp, "PER_HOUR", 1)
    # CampaignTarget YOK — yalnız legacy M2M
    camp.target_pharmacies.add(eczane_kadikoy)

    generate_for_kiosk(kiosk_kadikoy, TODAY)
    generate_for_kiosk(kiosk_besiktas, TODAY)

    assert creative.pk in _creative_ids_in_hour(kiosk_kadikoy, 11)
    assert creative.pk not in _creative_ids_in_hour(kiosk_besiktas, 11)


# ─────────────────────────────────────────────────────────────────────────────
# GM-08  Hedefsiz kampanya = tüm eczaneler (mevcut davranış)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_gm_no_target_means_all_current(
    kiosk_kadikoy, kiosk_besiktas, kiosk_ankara, house_ad_10s
):
    """CampaignTarget ve target_pharmacies yoksa → tüm kiosklar (mevcut davranış golden).

    Uyarı: Bu davranış Faz 1'de `target_scope=RULES` ile değiştirilecek.
    Bu test mevcut davranışı kilitler; V2 geçişinde kasıtlı kırılacaktır.
    """
    camp = _campaign("GM08")
    creative = _creative(camp, duration=15)
    _rule(camp, "PER_HOUR", 1)
    # Hedef YOK → _campaign_targets_eczane → True

    for k in [kiosk_kadikoy, kiosk_besiktas, kiosk_ankara]:
        generate_for_kiosk(k, TODAY)
        assert creative.pk in _creative_ids_in_hour(k, 8), (
            f"kiosk={k.pk}: hedefsiz kampanya her kioskta görünmeli"
        )


# ─────────────────────────────────────────────────────────────────────────────
# GM-09  İki kampanya, priority sıralaması
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_gm_priority_ordering_two_campaigns(kiosk_kadikoy, house_ad_10s):
    """priority=1 kampanya PER_LOOP=2 ile tüm kapasiteyi doldurunca,
    priority=99 kampanya hiç yerleştirilmemeli.

    Mevcut davranış (golden): sıralama "-is_guaranteed, priority" →
    priority=1 önce fetch edilip tüm loop'ları doldurur; priority=99 hiç sığmaz.
    """
    # Yüksek öncelikli: 2×30s = 60s → lopu doldurur
    camp_hi = _campaign("GM09-HI", priority=1)
    creative_hi = _creative(camp_hi, duration=30, url_suffix="-hi")
    _rule(camp_hi, "PER_LOOP", 2)

    # Düşük öncelikli: 15s — yer kalmayacak
    camp_lo = _campaign("GM09-LO", priority=99)
    creative_lo = _creative(camp_lo, duration=15, url_suffix="-lo")
    _rule(camp_lo, "PER_LOOP", 1)

    generate_for_kiosk(kiosk_kadikoy, TODAY)

    items_h0 = _items_for_hour(kiosk_kadikoy, 0)

    # Yüksek öncelikli creative her loop'ta 2 defa olmalı (loop 0)
    loop0_hi = [
        i for i in items_h0
        if i.creative_id == creative_hi.pk and i.estimated_start_offset_seconds < 60
    ]
    assert len(loop0_hi) == 2, (
        f"priority=1 kampanya loop0'da 2 slot bekleniyor, bulundu={len(loop0_hi)}"
    )

    # Düşük öncelikli creative hiç olmamalı (kapasite dolu)
    lo_anywhere = [i for i in items_h0 if i.creative_id == creative_lo.pk]
    assert len(lo_anywhere) == 0, (
        f"priority=99 kampanya kapasitesi doluyken yerleştirilmemeli, bulundu={len(lo_anywhere)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# GM-10  Priority sıralamada önce (is_guaranteed Faz 7'de kaldırıldı)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_gm_guaranteed_flag_ordering(kiosk_kadikoy, house_ad_10s):
    """Faz 7: is_guaranteed kaldırıldı; priority sıralaması canonical.

    Daha düşük priority sayısı = daha yüksek öncelik.
    priority=1 kampanya priority=99 kampanyadan önce işlenir.
    """
    # Düşük öncelik sayısı (daha iyi priority)
    camp_high = _campaign("GM10-HIGH-PRIO", priority=1)
    creative_high = _creative(camp_high, duration=30, url_suffix="-h")
    _rule(camp_high, "PER_LOOP", 2)  # 30×2=60 → lopu doldurur

    # Yüksek priority sayısı (daha düşük öncelik)
    camp_low = _campaign("GM10-LOW-PRIO", priority=99)
    creative_low = _creative(camp_low, duration=15, url_suffix="-l")
    _rule(camp_low, "PER_LOOP", 1)

    generate_for_kiosk(kiosk_kadikoy, TODAY)

    items_h0 = _items_for_hour(kiosk_kadikoy, 0)
    loop0_high = [
        i for i in items_h0
        if i.creative_id == creative_high.pk and i.estimated_start_offset_seconds < 60
    ]
    loop0_low = [
        i for i in items_h0
        if i.creative_id == creative_low.pk and i.estimated_start_offset_seconds < 60
    ]

    # Yüksek öncelik (priority=1) önce işlendi → lopu doldurdu
    assert len(loop0_high) == 2, (
        f"priority=1 kampanya loop0'da 2 slot bekleniyor, bulundu={len(loop0_high)}"
    )
    # Düşük öncelik için yer kalmadı
    assert len(loop0_low) == 0, (
        f"priority=99 kampanya dolu lopta yer bulmamalı, bulundu={len(loop0_low)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# GM-11  HouseAd filler — boş kapasite priority sırasıyla dolar
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_gm_house_ad_filler_fill(kiosk_kadikoy):
    """Kampanya kuralı yokken her loop HouseAd ile tam 60s dolmalı.

    Mevcut davranış (golden): _pass4_filler, priority sırası (küçük önce).
    """
    ha_pri10 = HouseAd.objects.create(
        name="Filler-10s-pri10",
        media_url="https://cdn.example.com/ha10.mp4",
        duration_seconds=10,
        priority=10,
        aktif=True,
    )
    ha_pri50 = HouseAd.objects.create(
        name="Filler-10s-pri50",
        media_url="https://cdn.example.com/ha50.mp4",
        duration_seconds=10,
        priority=50,
        aktif=True,
    )

    generate_for_kiosk(kiosk_kadikoy, TODAY)

    # Her loop 60s dolu olmalı
    for hour in range(24):
        used = _total_duration_per_loop(kiosk_kadikoy, hour)
        for idx, total in used.items():
            assert total == 60, (
                f"saat={hour} loop={idx}: 60s bekleniyor, bulundu={total}"
            )

    # Saat 0, loop 0'daki house ad'lerin ilki daha düşük priority'li olmalı
    items_h0_loop0 = [
        i for i in _items_for_hour(kiosk_kadikoy, 0)
        if i.estimated_start_offset_seconds < 60
    ]
    assert len(items_h0_loop0) > 0
    first_ha = items_h0_loop0[0]
    assert first_ha.house_ad_id is not None
    # priority=10 olanın önce gelmesi bekleniyor (filler queue ordering)
    assert first_ha.house_ad.priority == 10, (
        f"İlk filler priority=10 bekleniyor, bulundu={first_ha.house_ad.priority}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# GM-12  Çoklu creative'de yalnız ilk creative kullanılır (mevcut davranış)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_gm_multi_creative_first_only(kiosk_kadikoy, house_ad_10s):
    """Kampanyaya 3 creative eklendiğinde yalnız ilk (olusturulma_tarihi ASC) kullanılmalı.

    Mevcut davranış (golden): _pick_creative → .order_by("olusturulma_tarihi").first().
    Bu, V2'de ağırlıklı round-robin ile kasıtlı kırılacak; mevcut davranış burada kilitlenir.
    """
    camp = _campaign("GM12")
    creative_first = Creative.objects.create(
        campaign=camp,
        media_url="https://cdn.example.com/first.mp4",
        duration_seconds=15,
        name="first",
    )
    creative_second = Creative.objects.create(
        campaign=camp,
        media_url="https://cdn.example.com/second.mp4",
        duration_seconds=15,
        name="second",
    )
    creative_third = Creative.objects.create(
        campaign=camp,
        media_url="https://cdn.example.com/third.mp4",
        duration_seconds=15,
        name="third",
    )
    _rule(camp, "PER_HOUR", 1)

    generate_for_kiosk(kiosk_kadikoy, TODAY)

    all_creative_ids: set = set()
    for hour in range(24):
        all_creative_ids.update(_creative_ids_in_hour(kiosk_kadikoy, hour))

    assert creative_first.pk in all_creative_ids, "İlk creative kullanılmali"
    assert creative_second.pk not in all_creative_ids, (
        "İkinci creative mevcut davranışta kullanılmamalı"
    )
    assert creative_third.pk not in all_creative_ids, (
        "Üçüncü creative mevcut davranışta kullanılmamalı"
    )


# ─────────────────────────────────────────────────────────────────────────────
# GM-13  Offset'ler saat-mutlak 0..3599 (ek güvence)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_gm_hourly_offset_absolute_0_3599(kiosk_kadikoy, house_ad_10s):
    """Her playlistin tüm item offset'leri 0 ≤ offset < 3600 aralığında olmalı.

    Ve bir saatteki loop N, offset = loop_index * loop_sec + slot_offset.
    Loop_sec=60 → saat başı offset = loop_index * 60; en büyük offset < 3600.
    """
    camp = _campaign("GM13")
    _creative(camp, duration=15)
    _rule(camp, "PER_LOOP", 2)

    generate_for_kiosk(kiosk_kadikoy, TODAY)

    for hour in range(24):
        items = _items_for_hour(kiosk_kadikoy, hour)
        for item in items:
            off = int(item.estimated_start_offset_seconds)
            assert 0 <= off < 3600, (
                f"saat={hour}: offset={off} 0..3599 dışında"
            )

    # Saat 0'daki loop 0 → offset < 60; loop 1 → 60 ≤ offset < 120
    items_h0 = _items_for_hour(kiosk_kadikoy, 0)
    loop_offsets: dict[int, list[int]] = {}
    for item in items_h0:
        idx = int(item.estimated_start_offset_seconds) // 60
        loop_offsets.setdefault(idx, []).append(
            int(item.estimated_start_offset_seconds) - idx * 60
        )

    for loop_idx, slot_offsets in loop_offsets.items():
        for slot_off in slot_offsets:
            assert 0 <= slot_off < 60, (
                f"loop={loop_idx}: slot_offset={slot_off} 0..59 dışında"
            )


# ─────────────────────────────────────────────────────────────────────────────
# GM-14  Tarih aralığı sınırında üretim / üretmeme (ek güvence)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_gm_date_range_boundary(kiosk_kadikoy, house_ad_10s):
    """Kampanya yalnız kendi tarih aralığında üretilmeli.

    Mevcut davranış (golden): _fetch_active_rules → noon filtresi:
      start_date ≤ noon ≤ end_date
    Boundary: kampanya bugün başlıyor (start_date = bugünün başı) → bugün dahil.
    Kampanya dün bitmiş → bugün dahil değil.
    """
    today_noon = timezone.make_aware(
        _dt.datetime.combine(TODAY, _dt.time(12, 0))
    )
    yesterday_end = today_noon - _dt.timedelta(hours=13)  # dün sonu

    # Kampanya bugün başlayan, 30 gün devam eden
    camp_active = Campaign.objects.create(
        name="GM14-active",
        start_date=today_noon - _dt.timedelta(hours=11),  # bugün
        end_date=today_noon + _dt.timedelta(days=30),
        status=Campaign.Status.ACTIVE,
    )
    creative_active = _creative(camp_active, duration=15, url_suffix="-active")
    _rule(camp_active, "PER_HOUR", 1)

    # Kampanya dün bitmiş
    camp_expired = Campaign.objects.create(
        name="GM14-expired",
        start_date=today_noon - _dt.timedelta(days=10),
        end_date=yesterday_end,  # dün sonu
        status=Campaign.Status.ACTIVE,
    )
    creative_expired = _creative(camp_expired, duration=15, url_suffix="-expired")
    _rule(camp_expired, "PER_HOUR", 1)

    generate_for_kiosk(kiosk_kadikoy, TODAY)

    # Aktif kampanya bugün görünmeli
    active_found = any(
        creative_active.pk in _creative_ids_in_hour(kiosk_kadikoy, h)
        for h in range(24)
    )
    assert active_found, "Bugün başlayan kampanya today üretiminde görünmeli"

    # Süresi dolan kampanya bugün görünmemeli
    expired_found = any(
        creative_expired.pk in _creative_ids_in_hour(kiosk_kadikoy, h)
        for h in range(24)
    )
    assert not expired_found, "Dün biten kampanya bugün üretimde olmamalı"


# ─────────────────────────────────────────────────────────────────────────────
# Kiosk API contract testleri (Faz 0 — golden)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_gm_kiosk_playlist_contract_fields(kiosk_kadikoy, house_ad_10s):
    """Kiosk playlist endpoint'i beklenen contract alanlarını döndürmeli.

    Korunan alanlar: asset_type, asset_id, media_url, duration_seconds,
    playback_order, estimated_start_offset_seconds.
    """
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    generate_for_kiosk(kiosk_kadikoy, TODAY)

    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"AppKey {kiosk_kadikoy.uygulama_anahtari}",
        HTTP_X_KIOSK_MAC=kiosk_kadikoy.mac_adresi,
    )
    r = client.get(f"/api/kiosk/v1/playlist/?date={TODAY}")
    assert r.status_code == 200, r.content

    body = r.json()
    assert "kiosk_id" in body
    assert "target_date" in body
    assert "loop_duration_seconds" in body
    assert "playlists" in body
    assert len(body["playlists"]) == 24

    # İlk playlist'in item'larını incele
    pl0 = body["playlists"][0]
    assert "target_hour" in pl0
    assert "items" in pl0
    assert len(pl0["items"]) > 0

    item = pl0["items"][0]
    required_fields = {
        "id", "asset_type", "asset_id", "media_url",
        "duration_seconds", "playback_order", "estimated_start_offset_seconds",
    }
    missing = required_fields - item.keys()
    assert not missing, f"Eksik contract alanları: {missing}"

    assert item["asset_type"] in ("creative", "house_ad")
    assert isinstance(item["asset_id"], str)
    assert item["media_url"].startswith("http")
    assert isinstance(item["duration_seconds"], int)
    assert isinstance(item["playback_order"], int)
    assert 0 <= item["estimated_start_offset_seconds"] < 3600


@pytest.mark.django_db
def test_gm_kiosk_ping_returns_playlist_version(kiosk_kadikoy, house_ad_10s):
    """Ping endpoint'i playlist_version döndürmeli; üretim sonrası ≥ 1 olmalı."""
    from rest_framework.test import APIClient
    from django.utils import timezone as tz

    today = tz.now().date()  # Gerçek bugün (tarih-bağımsız)

    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"AppKey {kiosk_kadikoy.uygulama_anahtari}",
        HTTP_X_KIOSK_MAC=kiosk_kadikoy.mac_adresi,
    )

    # Üretim öncesi
    r1 = client.get("/api/kiosk/v1/ping/")
    assert r1.status_code == 200
    assert r1.json()["playlist_version"] == 0

    generate_for_kiosk(kiosk_kadikoy, today)

    # Üretim sonrası
    r2 = client.get("/api/kiosk/v1/ping/")
    assert r2.status_code == 200
    assert r2.json()["playlist_version"] >= 1


@pytest.mark.django_db
def test_gm_proof_of_play_contract(kiosk_kadikoy, house_ad_10s):
    """Proof-of-play bulk ingest: creative_id ile 201, eksik id ile 400.

    Mevcut contract (golden): POST /api/kiosk/v1/proof-of-play/ {logs:[...]}.
    """
    from rest_framework.test import APIClient

    camp = _campaign("GM-POP")
    creative = _creative(camp, duration=15)

    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"AppKey {kiosk_kadikoy.uygulama_anahtari}",
        HTTP_X_KIOSK_MAC=kiosk_kadikoy.mac_adresi,
    )

    # Geçerli log
    payload_ok = {"logs": [{
        "creative_id": str(creative.pk),
        "played_at": timezone.now().isoformat(),
        "duration_played": 15,
    }]}
    r = client.post("/api/kiosk/v1/proof-of-play/", payload_ok, format="json")
    assert r.status_code == 201
    assert r.json()["ingested"] == 1

    # creative_id ve house_ad_id ikisi de eksik → 400
    payload_bad = {"logs": [{
        "played_at": timezone.now().isoformat(),
        "duration_played": 15,
    }]}
    r2 = client.post("/api/kiosk/v1/proof-of-play/", payload_bad, format="json")
    assert r2.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# Genel kapasité invariantı — tüm senaryolar için çapraz kontrol
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_gm_capacity_invariant_never_exceeded(kiosk_kadikoy, house_ad_10s):
    """Hiçbir koşulda bir loop'ta toplam kullanım 60s'i geçmemeli.

    Bu test tüm golden senaryolar için evrensel invariant kontrolüdür.
    """
    # Birden fazla kural: PER_LOOP + PER_HOUR + PER_DAY aynı anda
    camp1 = _campaign("GM-INV-1", priority=1)
    _creative(camp1, duration=10, url_suffix="-1")
    _rule(camp1, "PER_LOOP", 2)  # 20s

    camp2 = _campaign("GM-INV-2", priority=50)
    _creative(camp2, duration=15, url_suffix="-2")
    _rule(camp2, "PER_HOUR", 1)  # 15s

    camp3 = _campaign("GM-INV-3", priority=80)
    _creative(camp3, duration=10, url_suffix="-3")
    _rule(camp3, "PER_DAY", 3)  # 3 loop'a 10s

    generate_for_kiosk(kiosk_kadikoy, TODAY)

    for hour in range(24):
        used = _total_duration_per_loop(kiosk_kadikoy, hour, loop_sec=60)
        for loop_idx, total in used.items():
            assert total <= 60, (
                f"KAPASİTE AŞIMI: saat={hour} loop={loop_idx} toplam={total}s > 60s"
            )
