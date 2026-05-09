"""DOOH Loop-Filler Scheduler.

Bir kiosk + tarih icin 24 adet 60sn loop uretir (her saat icin bir Playlist).
Algoritma 4 pass'tir:

  Pass 1 — PER_LOOP : Loop icine sabit (her loop'ta N kez) yerlesim.
  Pass 2 — PER_HOUR : Saat icindeki secili loop'lara enjeksiyon.
  Pass 3 — PER_DAY  : Gun icindeki hedef saatlere rasgele dagitim.
  Pass 4 — Filler   : Bos kalan saniyelere HouseAd dolgusu.

Kapasite kuralı (her loop için):

    S_available = T_loop - sum(d_i * f_i)         (i = creative_i, f_i = freq)

Bu algoritma kiosk uzerinde calismaz; merkezi bir worker tarafindan gunluk
calistirilir (bkz. management/commands/generate_playlists.py).
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import List, Optional, Sequence

from django.db import transaction
from django.utils import timezone

from apps.campaigns.models import (
    Campaign,
    Creative,
    HouseAd,
    Playlist,
    PlaylistItem,
    ScheduleRule,
)
from apps.pharmacies.models import Kiosk

logger = logging.getLogger(__name__)


DEFAULT_LOOP_SECONDS = 60


@dataclass
class LoopSlot:
    """In-memory temsili: 60sn'lik bir loop'un ic dolulugu."""

    creative_id: Optional[str]
    house_ad_id: Optional[str]
    duration: int
    offset: int  # saniye, 0..T_loop-1


@dataclass
class LoopBlock:
    """Tek bir 60sn'lik loop (= bir saatin icindeki 1 loop)."""

    hour: int
    loop_index: int
    capacity: int = DEFAULT_LOOP_SECONDS
    used: int = 0
    items: List[LoopSlot] = field(default_factory=list)

    @property
    def available(self) -> int:
        return self.capacity - self.used

    def fits(self, duration: int) -> bool:
        return duration <= self.available

    def add(self, *, duration: int, creative_id: Optional[str] = None,
            house_ad_id: Optional[str] = None, offset: Optional[int] = None) -> LoopSlot:
        if not self.fits(duration):
            raise ValueError(
                f"LoopBlock(h={self.hour},i={self.loop_index}) does not fit {duration}s "
                f"(available={self.available})"
            )
        slot = LoopSlot(
            creative_id=creative_id,
            house_ad_id=house_ad_id,
            duration=duration,
            offset=offset if offset is not None else self.used,
        )
        self.items.append(slot)
        self.used += duration
        return slot


@dataclass
class HourPlan:
    """Bir saat icindeki tum loop'lar (varsayilan: saatte 60 loop = 3600s)."""

    hour: int
    loops: List[LoopBlock]

    @classmethod
    def empty(cls, hour: int, loop_seconds: int = DEFAULT_LOOP_SECONDS) -> "HourPlan":
        n = max(1, 3600 // loop_seconds)
        return cls(hour=hour, loops=[
            LoopBlock(hour=hour, loop_index=i, capacity=loop_seconds) for i in range(n)
        ])


class PlaylistGenerator:
    """Bir kioskun belirli bir gunu icin Playlist'leri uretir."""

    def __init__(self, kiosk: Kiosk, target_date: date, *,
                 loop_seconds: int = DEFAULT_LOOP_SECONDS,
                 rng: Optional[random.Random] = None) -> None:
        self.kiosk = kiosk
        self.target_date = target_date
        self.loop_seconds = loop_seconds
        self.rng = rng or random.Random(int(kiosk.pk) * 100000 + target_date.toordinal())
        self.plan: dict[int, HourPlan] = {
            h: HourPlan.empty(h, loop_seconds) for h in range(24)
        }

    # ── Public API ─────────────────────────────────────────────────────

    def generate(self) -> List[Playlist]:
        rules = self._fetch_active_rules()
        self._pass1_per_loop(rules)
        self._pass2_per_hour(rules)
        self._pass3_per_day(rules)
        self._pass4_filler()
        return self._persist()

    # ── Pass 1: PER_LOOP ───────────────────────────────────────────────

    def _pass1_per_loop(self, rules: Sequence[ScheduleRule]) -> None:
        for rule in rules:
            if rule.frequency_type != ScheduleRule.FrequencyType.PER_LOOP:
                continue
            creative = self._pick_creative(rule.campaign)
            if creative is None:
                continue
            f = max(1, int(rule.frequency_value))
            d = int(creative.duration_seconds)
            if d * f > self.loop_seconds:
                logger.warning(
                    "PER_LOOP rule exceeds loop capacity: campaign=%s d=%s f=%s loop=%s",
                    rule.campaign_id, d, f, self.loop_seconds,
                )
                continue
            spacing = self.loop_seconds / f
            for hour in self._rule_hours(rule):
                for loop in self.plan[hour].loops:
                    if not loop.fits(d * f):
                        continue
                    for k in range(f):
                        target_offset = int(round(k * spacing))
                        if loop.fits(d):
                            loop.add(
                                duration=d,
                                creative_id=str(creative.pk),
                                offset=min(target_offset, loop.capacity - d),
                            )

    # ── Pass 2: PER_HOUR ──────────────────────────────────────────────

    def _pass2_per_hour(self, rules: Sequence[ScheduleRule]) -> None:
        for rule in rules:
            if rule.frequency_type != ScheduleRule.FrequencyType.PER_HOUR:
                continue
            creative = self._pick_creative(rule.campaign)
            if creative is None:
                continue
            d = int(creative.duration_seconds)
            f = max(1, int(rule.frequency_value))
            for hour in self._rule_hours(rule):
                candidates = [l for l in self.plan[hour].loops if l.fits(d)]
                self.rng.shuffle(candidates)
                candidates.sort(key=lambda l: l.used)
                for loop in candidates[:f]:
                    loop.add(duration=d, creative_id=str(creative.pk))

    # ── Pass 3: PER_DAY ───────────────────────────────────────────────

    def _pass3_per_day(self, rules: Sequence[ScheduleRule]) -> None:
        for rule in rules:
            if rule.frequency_type != ScheduleRule.FrequencyType.PER_DAY:
                continue
            creative = self._pick_creative(rule.campaign)
            if creative is None:
                continue
            d = int(creative.duration_seconds)
            f = max(1, int(rule.frequency_value))
            target_hours = self._rule_hours(rule)
            all_loops: List[LoopBlock] = []
            for h in target_hours:
                all_loops.extend(self.plan[h].loops)
            candidates = [l for l in all_loops if l.fits(d)]
            self.rng.shuffle(candidates)
            for loop in candidates[:f]:
                loop.add(duration=d, creative_id=str(creative.pk))

    # ── Pass 4: Filler / House Ads ─────────────────────────────────────

    def _pass4_filler(self) -> None:
        house_ads = list(HouseAd.objects.filter(aktif=True).order_by("priority", "id"))
        if not house_ads:
            return
        idx = 0
        for h in range(24):
            for loop in self.plan[h].loops:
                while loop.available > 0:
                    candidate = self._pick_filler(house_ads, loop.available, idx)
                    if candidate is None:
                        break
                    loop.add(duration=int(candidate.duration_seconds),
                             house_ad_id=str(candidate.pk))
                    idx += 1

    def _pick_filler(self, house_ads: Sequence[HouseAd], available: int,
                     start_idx: int) -> Optional[HouseAd]:
        n = len(house_ads)
        for i in range(n):
            ha = house_ads[(start_idx + i) % n]
            if int(ha.duration_seconds) <= available:
                return ha
        return None

    # ── Persistence ────────────────────────────────────────────────────

    @transaction.atomic
    def _persist(self) -> List[Playlist]:
        Playlist.objects.filter(
            kiosk=self.kiosk, target_date=self.target_date
        ).delete()

        playlists: List[Playlist] = []
        for h in range(24):
            hour_plan = self.plan[h]
            playlist = Playlist.objects.create(
                kiosk=self.kiosk,
                target_date=self.target_date,
                target_hour=h,
                loop_duration_seconds=self.loop_seconds,
            )
            playlists.append(playlist)

            # Tum loop'lardaki slot'lari, saat-bazli mutlak offset ile yaz.
            # estimated_start_offset_seconds = loop_index * loop_seconds + slot.offset
            # Kiosk bunlari playback_order sirasi ile sirayla oynatir.
            bulk: list[PlaylistItem] = []
            order = 0
            for loop in hour_plan.loops:
                slots = sorted(loop.items, key=lambda s: s.offset)
                base = loop.loop_index * self.loop_seconds
                for slot in slots:
                    bulk.append(PlaylistItem(
                        playlist=playlist,
                        creative_id=slot.creative_id,
                        house_ad_id=slot.house_ad_id,
                        playback_order=order,
                        estimated_start_offset_seconds=base + slot.offset,
                    ))
                    order += 1
            if bulk:
                PlaylistItem.objects.bulk_create(bulk)
        return playlists

    # ── Helpers ────────────────────────────────────────────────────────

    def _fetch_active_rules(self) -> List[ScheduleRule]:
        naive_noon = datetime.combine(self.target_date, time(12, 0))
        when = timezone.make_aware(naive_noon) if timezone.is_naive(naive_noon) else naive_noon
        eczane_id = self.kiosk.eczane_id
        qs = (
            ScheduleRule.objects
            .select_related("campaign")
            .filter(
                campaign__status=Campaign.Status.ACTIVE,
                campaign__start_date__lte=when,
                campaign__end_date__gte=when,
            )
        )
        rules: List[ScheduleRule] = []
        for r in qs:
            targets = r.campaign.target_pharmacies.all()
            if targets.exists() and not targets.filter(pk=eczane_id).exists():
                continue
            rules.append(r)
        return rules

    def _rule_hours(self, rule: ScheduleRule) -> List[int]:
        if rule.target_hours:
            return [int(h) for h in rule.target_hours if 0 <= int(h) <= 23]
        return list(range(24))

    def _pick_creative(self, campaign: Campaign) -> Optional[Creative]:
        return campaign.creatives.order_by("olusturulma_tarihi").first()


def generate_for_kiosk(kiosk: Kiosk, target_date: date) -> List[Playlist]:
    """Cron / management komutundan kullanilan kisa-yol."""
    return PlaylistGenerator(kiosk, target_date).generate()


def available_seconds(kiosk: Kiosk, target_date: date, hour: int) -> int:
    """Bir kiosk + tarih + saat icin loop bazinda en kotu durumdaki bos saniye.

    Bir saat icinde N adet loop vardir. Her loop'a yerlesen toplam dolulugu
    hesaplar; donen deger en dolu loop'taki kalan saniye sayisidir
    (yani "yeni bir kural eklersek bu hour icin tum loop'lara sigan sure").

    Henuz uretilmemis playlist'ler icin tum loop_seconds'u doner.
    """
    pl = Playlist.objects.filter(
        kiosk=kiosk, target_date=target_date, target_hour=hour,
    ).prefetch_related("items__creative", "items__house_ad").first()
    if pl is None:
        return DEFAULT_LOOP_SECONDS

    loop_seconds = int(pl.loop_duration_seconds)
    per_loop_used: dict[int, int] = {}
    for item in pl.items.all():
        idx = int(item.estimated_start_offset_seconds) // loop_seconds
        if item.creative_id and item.creative:
            per_loop_used[idx] = per_loop_used.get(idx, 0) + int(item.creative.duration_seconds)
        elif item.house_ad_id and item.house_ad:
            per_loop_used[idx] = per_loop_used.get(idx, 0) + int(item.house_ad.duration_seconds)
    if not per_loop_used:
        return loop_seconds
    return max(0, loop_seconds - max(per_loop_used.values()))
