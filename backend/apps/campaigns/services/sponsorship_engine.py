"""Tek yerlesim motoru — DOOH sponsorluk playlist uretimi.

Mimari:
  * Saf cekirdek: ``plan_day(target_date, specs) -> DayPlan`` — DB'siz, deterministik.
  * DB sarmalayici: ``plan_kiosk_day(kiosk, date, specs=None)`` — kayitli/uygulanabilir
    atamalari yukler ve cekirdegi calistirir.
  * Kalicilastirma: ``persist_day(kiosk, date, day_plan)`` — 24 saatlik Playlist/PlaylistItem.
  * Dogrulama: ``validate_kiosk(kiosk, specs)`` — kapasite asimini bulur.
  * Simulasyon/probe: ``probe_window`` / ``simulate_scenario``.

Yerlesim algoritmasi (homojen, deterministik):
  - Pencere [S,E) saniye. i. gosterim (0..N-1) ``creatives[i % k]`` kullanir.
  - Ideal zaman t_i = S + (i + phase_j) * (E-S)/N, phase_j = (j+0.5)/M (atama j, toplam M).
  - Tum atamalarin tum gosterimleri (ideal, j, i) ile global siralanir; her biri idealine
    en yakin BOS baslangica yerlesir (saat sinirini asmadan, cakismadan). Yoksa unplaced.
  - Item saat sinirini asamaz: [s, s+d) tek bir saat icinde kalir (offset+d <= 3600).
"""
from __future__ import annotations

import bisect
import datetime as _dt
import hashlib
import zoneinfo
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from django.conf import settings
from django.db import transaction
from django.utils import timezone

_ISTANBUL_TZ = zoneinfo.ZoneInfo("Europe/Istanbul")
_SECONDS_PER_HOUR = 3600
_DAY_SECONDS = 24 * _SECONDS_PER_HOUR
_VALIDATE_DAY_CAP = 400


# ─────────────────────────────────────────────────────────────────────────────
# Veri yapilari
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CreativeSpec:
    id: object
    duration: int
    name: str = ""
    media_url: str = ""
    active_media_url: str = ""
    object_key: str = ""
    active_object_key: str = ""


@dataclass(frozen=True)
class Spec:
    """Atama benzeri yerlesim girdisi (saf cekirdek)."""
    key: str
    campaign_id: object
    campaign_name: str
    window_start_minute: int
    window_end_minute: int
    count: int
    creatives: Tuple[CreativeSpec, ...]
    advertiser_name: str = ""


@dataclass
class PlacedItem:
    start_second: int
    hour: int
    offset: int
    duration: int
    creative_id: object
    campaign_id: object
    key: str


@dataclass
class AssignmentStat:
    key: str
    campaign_id: object
    campaign_name: str
    requested: int
    placed: int
    unplaced: int
    seconds: int
    window_start_minute: int
    window_end_minute: int


@dataclass
class DayPlan:
    date: _dt.date
    items: List[PlacedItem]
    assignment_stats: Dict[str, AssignmentStat]
    hour_used_seconds: List[int]
    fingerprint: str
    ok: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# Saf cekirdek
# ─────────────────────────────────────────────────────────────────────────────


class _Occupancy:
    """Saat bazli dolu araliklar. Her aralik tek bir saat icinde kalir."""

    __slots__ = ("by_hour",)

    def __init__(self) -> None:
        # hour -> sorted list of (start_second, end_second)
        self.by_hour: Dict[int, List[Tuple[int, int]]] = {}

    def add(self, start: int, end: int) -> None:
        hour = start // _SECONDS_PER_HOUR
        lst = self.by_hour.setdefault(hour, [])
        bisect.insort(lst, (start, end))

    def best_start(self, ideal: int, duration: int, s_win: int, e_win: int) -> Optional[int]:
        """Idealine en yakin uygun bos baslangici bul.

        Kisitlar: [s, s+d) pencere icinde, tek saat icinde, cakismasiz.
        Donus: en yakin baslangic saniyesi; hic yoksa None.
        """
        first_hour = s_win // _SECONDS_PER_HOUR
        last_hour = (e_win - 1) // _SECONDS_PER_HOUR
        ideal_hour = min(max(ideal // _SECONDS_PER_HOUR, first_hour), last_hour)

        # Saatleri ideale yakinliga gore sirala (yakindan uzaga).
        hours = range(first_hour, last_hour + 1)
        ordered = sorted(hours, key=lambda h: abs(h - ideal_hour))

        best_start: Optional[int] = None
        best_dist: Optional[int] = None
        for h in ordered:
            lo = max(s_win, h * _SECONDS_PER_HOUR)
            hi = min(e_win, (h + 1) * _SECONDS_PER_HOUR)
            if hi - lo < duration:
                continue
            # Bu saatin ideale alt-sinir mesafesi; best'ten buyukse erken cik.
            if ideal < lo:
                hour_lb = lo - ideal
            elif ideal > hi:
                hour_lb = ideal - hi
            else:
                hour_lb = 0
            if best_dist is not None and hour_lb > best_dist:
                break

            cand = self._best_start_in_hour(h, ideal, duration, lo, hi)
            if cand is None:
                continue
            dist = abs(cand - ideal)
            if best_dist is None or dist < best_dist or (dist == best_dist and cand < best_start):
                best_dist = dist
                best_start = cand
        return best_start

    def _best_start_in_hour(
        self, hour: int, ideal: int, duration: int, lo: int, hi: int
    ) -> Optional[int]:
        intervals = self.by_hour.get(hour, ())
        cursor = lo
        best: Optional[int] = None
        best_dist: Optional[int] = None

        def _consider(a: int, b: int) -> None:
            nonlocal best, best_dist
            if b - a < duration:
                return
            # [a, b-duration] araliginda ideale en yakin baslangic.
            start = min(max(ideal, a), b - duration)
            dist = abs(start - ideal)
            if best_dist is None or dist < best_dist or (dist == best_dist and start < best):
                best_dist = dist
                best = start

        for (s, e) in intervals:
            if e <= lo or s >= hi:
                continue
            if s > cursor:
                _consider(cursor, min(s, hi))
            cursor = max(cursor, e)
            if cursor >= hi:
                break
        if cursor < hi:
            _consider(cursor, hi)
        return best


def _canonical_fingerprint(items: Sequence[PlacedItem]) -> str:
    """Yerlesimden deterministik 16 hex fingerprint (sha256 ilk 16)."""
    rows = sorted(
        (it.start_second, it.duration, str(it.creative_id), str(it.campaign_id))
        for it in items
    )
    h = hashlib.sha256()
    for (ss, dur, cid, camp) in rows:
        h.update(f"{ss}|{dur}|{cid}|{camp}\n".encode("utf-8"))
    return h.hexdigest()[:16]


def plan_day(target_date: _dt.date, specs: Sequence[Spec]) -> DayPlan:
    """Saf cekirdek: verilen atamalar icin gunu planla (DB'siz, deterministik)."""
    # Atamalari stabil anahtara gore sirala -> j indeksi (staggering phase).
    ordered_specs = sorted(specs, key=lambda sp: sp.key)
    m = len(ordered_specs)

    # Her gosterim icin (ideal, j, i, spec) uret.
    shows: List[Tuple[float, int, int, Spec]] = []
    stats: Dict[str, AssignmentStat] = {}
    for j, sp in enumerate(ordered_specs):
        s_win = sp.window_start_minute * 60
        e_win = sp.window_end_minute * 60
        n = sp.count
        k = len(sp.creatives)
        stats[sp.key] = AssignmentStat(
            key=sp.key,
            campaign_id=sp.campaign_id,
            campaign_name=sp.campaign_name,
            requested=n,
            placed=0,
            unplaced=n,
            seconds=0,
            window_start_minute=sp.window_start_minute,
            window_end_minute=sp.window_end_minute,
        )
        if n <= 0 or k == 0 or e_win <= s_win:
            continue
        phase = (j + 0.5) / m if m else 0.5
        span = e_win - s_win
        for i in range(n):
            ideal = s_win + (i + phase) * span / n
            shows.append((ideal, j, i, sp))

    shows.sort(key=lambda t: (t[0], t[1], t[2]))

    occ = _Occupancy()
    items: List[PlacedItem] = []
    for (ideal, j, i, sp) in shows:
        s_win = sp.window_start_minute * 60
        e_win = sp.window_end_minute * 60
        creative = sp.creatives[i % len(sp.creatives)]
        duration = int(creative.duration)
        if duration <= 0 or duration > _SECONDS_PER_HOUR:
            continue
        start = occ.best_start(int(round(ideal)), duration, s_win, e_win)
        if start is None:
            continue
        occ.add(start, start + duration)
        hour = start // _SECONDS_PER_HOUR
        items.append(PlacedItem(
            start_second=start,
            hour=hour,
            offset=start - hour * _SECONDS_PER_HOUR,
            duration=duration,
            creative_id=creative.id,
            campaign_id=sp.campaign_id,
            key=sp.key,
        ))
        st = stats[sp.key]
        st.placed += 1
        st.unplaced -= 1
        st.seconds += duration

    items.sort(key=lambda it: (it.start_second, str(it.campaign_id)))
    hour_used = [0] * 24
    for it in items:
        hour_used[it.hour] += it.duration

    ok = all(st.unplaced == 0 for st in stats.values())
    fp = _canonical_fingerprint(items)
    return DayPlan(
        date=target_date,
        items=items,
        assignment_stats=stats,
        hour_used_seconds=hour_used,
        fingerprint=fp,
        ok=ok,
    )


# ─────────────────────────────────────────────────────────────────────────────
# DB sarmalayici — spec uretimi + uygulanabilirlik
# ─────────────────────────────────────────────────────────────────────────────


def _istanbul_date(dt_value) -> _dt.date:
    if timezone.is_aware(dt_value):
        return dt_value.astimezone(_ISTANBUL_TZ).date()
    return dt_value.date()


def _spec_from_assignment(assignment, creatives: Sequence) -> Spec:
    creative_specs = tuple(
        CreativeSpec(
            id=c.id,
            duration=int(c.duration_seconds),
            name=c.name or "",
            media_url=c.media_url or "",
            active_media_url=c.active_media_url or "",
            object_key=c.object_key or "",
            active_object_key=c.active_object_key or "",
        )
        for c in creatives
    )
    return Spec(
        key=str(assignment.id),
        campaign_id=assignment.campaign_id,
        campaign_name=assignment.campaign.name,
        advertiser_name=getattr(assignment.campaign, "advertiser_name", "") or "",
        window_start_minute=int(assignment.window_start_minute),
        window_end_minute=int(assignment.window_end_minute),
        count=int(assignment.count),
        creatives=creative_specs,
    )


def _is_applicable(assignment, target_date: _dt.date) -> bool:
    """Atama verilen tarihte uygulanabilir mi?"""
    from apps.campaigns.models import Campaign

    if not assignment.is_active:
        return False
    campaign = assignment.campaign
    if campaign.status != Campaign.Status.ACTIVE:
        return False
    # Kampanya tarih araligi (Istanbul yerel tarihi).
    camp_start = _istanbul_date(campaign.start_date)
    camp_end = _istanbul_date(campaign.end_date)
    if not (camp_start <= target_date <= camp_end):
        return False
    # Atama seviyesi opsiyonel aralik.
    if assignment.start_date and target_date < assignment.start_date:
        return False
    if assignment.end_date and target_date > assignment.end_date:
        return False
    # Haftanin gunu (ISO 1=Pzt..7=Paz).
    weekdays = assignment.active_weekdays
    if weekdays:
        if target_date.isoweekday() not in set(weekdays):
            return False
    return True


def _load_assignments(kiosk_id: int):
    from apps.campaigns.models import KioskSponsorship

    return list(
        KioskSponsorship.objects
        .filter(kiosk_id=kiosk_id)
        .select_related("campaign")
        .order_by("olusturulma_tarihi", "id")
    )


def _creatives_for_campaign(campaign_id, cache: Dict) -> List:
    if campaign_id in cache:
        return cache[campaign_id]
    from apps.campaigns.models import Creative

    lst = list(
        Creative.objects
        .filter(campaign_id=campaign_id)
        .order_by("olusturulma_tarihi", "id")
    )
    cache[campaign_id] = lst
    return lst


def build_specs_for_date(kiosk_id: int, target_date: _dt.date, assignments=None) -> List[Spec]:
    """Kiosk icin verilen tarihte uygulanabilir atamalardan Spec listesi uret."""
    if assignments is None:
        assignments = _load_assignments(kiosk_id)
    cache: Dict = {}
    specs: List[Spec] = []
    for a in assignments:
        if not _is_applicable(a, target_date):
            continue
        creatives = _creatives_for_campaign(a.campaign_id, cache)
        if not creatives:
            continue
        specs.append(_spec_from_assignment(a, creatives))
    return specs


def plan_kiosk_day(kiosk, target_date: _dt.date, specs: Optional[Sequence[Spec]] = None) -> DayPlan:
    """DB sarmalayici: specs verilmezse kayitli/uygulanabilir atamalari yukler."""
    kiosk_id = kiosk.id if hasattr(kiosk, "id") else kiosk
    if specs is None:
        specs = build_specs_for_date(kiosk_id, target_date)
    return plan_day(target_date, specs)


# ─────────────────────────────────────────────────────────────────────────────
# Kalicilastirma
# ─────────────────────────────────────────────────────────────────────────────


def _current_db_fingerprint(kiosk_id: int, target_date: _dt.date) -> Optional[str]:
    """Mevcut DB icerigini (o tarih) canonical fingerprint olarak hesapla.

    Hic playlist yoksa None (ilk uretim -> her zaman yaz).
    """
    from apps.campaigns.models import Playlist, PlaylistItem

    playlists = list(
        Playlist.objects.filter(kiosk_id=kiosk_id, target_date=target_date)
    )
    if not playlists:
        return None
    hour_by_id = {p.id: p.target_hour for p in playlists}
    items = (
        PlaylistItem.objects
        .filter(playlist_id__in=hour_by_id.keys())
        .select_related("creative")
    )
    placed: List[PlacedItem] = []
    for it in items:
        if not it.creative_id:
            continue
        hour = hour_by_id[it.playlist_id]
        start = hour * _SECONDS_PER_HOUR + it.estimated_start_offset_seconds
        placed.append(PlacedItem(
            start_second=start,
            hour=hour,
            offset=it.estimated_start_offset_seconds,
            duration=int(it.creative.duration_seconds),
            creative_id=it.creative_id,
            campaign_id=it.creative.campaign_id,
            key="",
        ))
    return _canonical_fingerprint(placed)


def _next_version(kiosk) -> int:
    from django.db.models import Max
    from apps.campaigns.models import Playlist

    max_v = (
        Playlist.objects.filter(kiosk_id=kiosk.id).aggregate(mv=Max("version"))["mv"] or 0
    )
    last = kiosk.last_playlist_version or 0
    return max(max_v, last) + 1


@transaction.atomic
def persist_day(kiosk, target_date: _dt.date, day_plan: DayPlan) -> Optional[int]:
    """24 saatlik Playlist/PlaylistItem olarak kalicilastir.

    Fingerprint degismemisse hicbir sey yazma (None doner). Aksi halde versiyon
    artirarak 24 saatlik (bos saatler dahil) playlist uret; donus = creative sayisi.
    """
    from apps.campaigns.models import Playlist, PlaylistItem
    from apps.pharmacies.models import Kiosk

    kiosk_id = kiosk.id
    current_fp = _current_db_fingerprint(kiosk_id, target_date)
    if current_fp is not None and current_fp == day_plan.fingerprint:
        return None

    version = _next_version(kiosk)

    # Eski kayitlari temizle.
    Playlist.objects.filter(kiosk_id=kiosk_id, target_date=target_date).delete()

    # Saat bazli item gruplama.
    items_by_hour: Dict[int, List[PlacedItem]] = {h: [] for h in range(24)}
    for it in day_plan.items:
        items_by_hour[it.hour].append(it)

    total_creatives = 0
    for hour in range(24):
        playlist = Playlist.objects.create(
            kiosk_id=kiosk_id,
            target_date=target_date,
            target_hour=hour,
            loop_duration_seconds=60,
            version=version,
        )
        hour_items = sorted(items_by_hour[hour], key=lambda it: it.offset)
        bulk = []
        for order, it in enumerate(hour_items):
            bulk.append(PlaylistItem(
                playlist=playlist,
                creative_id=it.creative_id,
                playback_order=order,
                estimated_start_offset_seconds=it.offset,
            ))
            total_creatives += 1
        if bulk:
            PlaylistItem.objects.bulk_create(bulk)

    # Desired versiyonu guncelle (monoton artan).
    Kiosk.objects.filter(pk=kiosk_id).update(last_playlist_version=version)
    return total_creatives


def regenerate_kiosk_day(kiosk_id: int, target_date: _dt.date) -> Optional[int]:
    """Bir kiosk-gun icin planla + kalicilastir. Kiosk aktif degilse None."""
    from apps.pharmacies.models import Kiosk

    try:
        kiosk = Kiosk.objects.get(pk=kiosk_id, aktif=True)
    except Kiosk.DoesNotExist:
        return None
    day_plan = plan_kiosk_day(kiosk, target_date)
    return persist_day(kiosk, target_date, day_plan)


# ─────────────────────────────────────────────────────────────────────────────
# Kapasite dogrulamasi
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ValidationResult:
    valid: bool
    conflicts: List[dict] = field(default_factory=list)


def _horizon_today() -> _dt.date:
    return _dt.datetime.now(_ISTANBUL_TZ).date()


def validate_specs(
    specs_by_assignment: Sequence[Tuple[object, Spec]],
    date_from: _dt.date,
    date_to: _dt.date,
) -> ValidationResult:
    """Verilen atama-spec ciftlerini tarih araliginda dogrula.

    specs_by_assignment: (assignment, spec) ciftleri. assignment uygulanabilirlik
    icin kullanilir (is_active, campaign dates/status, weekdays).
    """
    today = _horizon_today()
    start = max(date_from, today)
    if start > date_to:
        return ValidationResult(valid=True, conflicts=[])

    # Gunleri uygulanabilir atama kumesine gore dedupe et.
    seen_sets: set = set()
    conflicts: List[dict] = []
    day = start
    cap = 0
    while day <= date_to and cap < _VALIDATE_DAY_CAP:
        cap += 1
        applicable = [
            (a, sp) for (a, sp) in specs_by_assignment if _is_applicable(a, day)
        ]
        key = frozenset(sp.key for (a, sp) in applicable)
        if key and key not in seen_sets:
            seen_sets.add(key)
            plan = plan_day(day, [sp for (a, sp) in applicable])
            if not plan.ok:
                for st in plan.assignment_stats.values():
                    if st.unplaced > 0:
                        conflicts.append({
                            "date": str(day),
                            "campaign_id": str(st.campaign_id),
                            "campaign_name": st.campaign_name,
                            "requested": st.requested,
                            "placed": st.placed,
                        })
                        if len(conflicts) >= 20:
                            return ValidationResult(valid=False, conflicts=conflicts)
        day += _dt.timedelta(days=1)

    return ValidationResult(valid=(len(conflicts) == 0), conflicts=conflicts)


def validate_kiosk(kiosk_id: int, assignments) -> ValidationResult:
    """Kiosk'un verilen atama kumesi icin kapasiteyi dogrula.

    assignments: KioskSponsorship benzeri nesneler (DB'ye yazilmamis olabilir).
    """
    cache: Dict = {}
    pairs: List[Tuple[object, Spec]] = []
    earliest: Optional[_dt.date] = None
    latest: Optional[_dt.date] = None
    today = _horizon_today()

    for a in assignments:
        creatives = _creatives_for_campaign(a.campaign_id, cache)
        if not creatives:
            # Creative yoksa yerlesim yapilmaz; kapasite sorunu da olusturmaz.
            continue
        sp = _spec_from_assignment(a, creatives)
        pairs.append((a, sp))

        camp = a.campaign
        c_start = _istanbul_date(camp.start_date)
        c_end = _istanbul_date(camp.end_date)
        a_start = a.start_date or c_start
        a_end = a.end_date or c_end
        d_start = max(c_start, a_start)
        d_end = min(c_end, a_end)
        if d_start > d_end:
            continue
        earliest = d_start if earliest is None else min(earliest, d_start)
        latest = d_end if latest is None else max(latest, d_end)

    if not pairs or earliest is None:
        return ValidationResult(valid=True, conflicts=[])

    start = max(earliest, today)
    end = latest
    if (end - start).days > _VALIDATE_DAY_CAP:
        end = start + _dt.timedelta(days=_VALIDATE_DAY_CAP)
    return validate_specs(pairs, start, end)


# ─────────────────────────────────────────────────────────────────────────────
# Probe / senaryo simulasyonu
# ─────────────────────────────────────────────────────────────────────────────


def _free_slots_count(occ: _Occupancy, duration: int, s_win: int, e_win: int) -> int:
    """Pencere icindeki bos bosluklara kac adet `duration` gosterim sigar.

    Saat sinirlarina saygili. `occ` uzerinde degisiklik yapmaz (okuma).
    """
    first_hour = s_win // _SECONDS_PER_HOUR
    last_hour = (e_win - 1) // _SECONDS_PER_HOUR
    total = 0
    for h in range(first_hour, last_hour + 1):
        lo = max(s_win, h * _SECONDS_PER_HOUR)
        hi = min(e_win, (h + 1) * _SECONDS_PER_HOUR)
        if hi - lo < duration:
            continue
        intervals = occ.by_hour.get(h, ())
        cursor = lo
        free_segments: List[Tuple[int, int]] = []
        for (s, e) in intervals:
            if e <= lo or s >= hi:
                continue
            if s > cursor:
                free_segments.append((cursor, min(s, hi)))
            cursor = max(cursor, e)
            if cursor >= hi:
                break
        if cursor < hi:
            free_segments.append((cursor, hi))
        for (a, b) in free_segments:
            total += (b - a) // duration
    return total


def _occupancy_from_items(items: Sequence[PlacedItem]) -> _Occupancy:
    occ = _Occupancy()
    for it in items:
        occ.add(it.start_second, it.start_second + it.duration)
    return occ


def probe_window(
    kiosk_id: int,
    date_from: _dt.date,
    date_to: _dt.date,
    duration_seconds: int,
    window_start_minute: int,
    window_end_minute: int,
    active_weekdays: Optional[Sequence[int]],
    include_existing: bool = True,
) -> dict:
    """Pencere icinde `duration_seconds`'lik kac gosterim sigabilir (gun bazli)."""
    s_win = window_start_minute * 60
    e_win = window_end_minute * 60
    window_seconds = e_win - s_win
    weekday_set = set(active_weekdays) if active_weekdays else None

    assignments = _load_assignments(kiosk_id) if include_existing else []
    days: List[dict] = []
    max_shows_min: Optional[int] = None
    max_shows_max: Optional[int] = None
    free_seconds_min: Optional[int] = None

    day = date_from
    while day <= date_to:
        if weekday_set and day.isoweekday() not in weekday_set:
            day += _dt.timedelta(days=1)
            continue
        if include_existing:
            specs = build_specs_for_date(kiosk_id, day, assignments)
            plan = plan_day(day, specs)
            occ = _occupancy_from_items(plan.items)
        else:
            occ = _Occupancy()
        max_shows = _free_slots_count(occ, duration_seconds, s_win, e_win)
        used = sum(
            it.duration for it in (plan.items if include_existing else [])
            if s_win <= it.start_second < e_win
        ) if include_existing else 0
        free_seconds = window_seconds - used
        days.append({"date": str(day), "max_shows": max_shows, "free_seconds": free_seconds})
        max_shows_min = max_shows if max_shows_min is None else min(max_shows_min, max_shows)
        max_shows_max = max_shows if max_shows_max is None else max(max_shows_max, max_shows)
        free_seconds_min = free_seconds if free_seconds_min is None else min(free_seconds_min, free_seconds)
        day += _dt.timedelta(days=1)

    return {
        "duration_seconds": duration_seconds,
        "window_start": _minute_to_hhmm(window_start_minute),
        "window_end": _minute_to_hhmm(window_end_minute),
        "window_seconds": window_seconds,
        "max_shows_min": max_shows_min or 0,
        "max_shows_max": max_shows_max or 0,
        "free_seconds_min": free_seconds_min if free_seconds_min is not None else window_seconds,
        "days": days,
    }


def simulate_scenario(
    kiosk_id: int,
    date_from: _dt.date,
    date_to: _dt.date,
    lines: Sequence[dict],
    include_existing: bool = True,
) -> dict:
    """Mevcut (+opsiyonel) atamalar + hipotetik satirlari birlikte calistir."""
    assignments = _load_assignments(kiosk_id) if include_existing else []

    # Hipotetik satirlar icin sentetik spec'ler.
    synth_specs: List[Spec] = []
    for idx, line in enumerate(lines):
        duration = int(line["duration_seconds"])
        synth_specs.append(Spec(
            key=f"__scenario_{idx}",
            campaign_id=f"scenario-{idx}",
            campaign_name=line.get("label", f"Senaryo {idx + 1}"),
            window_start_minute=int(line["window_start_minute"]),
            window_end_minute=int(line["window_end_minute"]),
            count=int(line["count"]),
            creatives=(CreativeSpec(id=f"scenario-c-{idx}", duration=duration),),
        ))

    line_weekdays = [
        set(line["active_weekdays"]) if line.get("active_weekdays") else None
        for line in lines
    ]

    days: List[dict] = []
    line_placed: List[List[int]] = [[] for _ in lines]
    feasible = True

    day = date_from
    while day <= date_to:
        specs = build_specs_for_date(kiosk_id, day, assignments) if include_existing else []
        active_synth = []
        for idx, sp in enumerate(synth_specs):
            wd = line_weekdays[idx]
            if wd and day.isoweekday() not in wd:
                line_placed[idx].append(0)
                continue
            active_synth.append((idx, sp))
        combined = list(specs) + [sp for (_, sp) in active_synth]
        plan = plan_day(day, combined)
        day_feasible = True
        for (idx, sp) in active_synth:
            st = plan.assignment_stats.get(sp.key)
            placed = st.placed if st else 0
            line_placed[idx].append(placed)
            if st and st.unplaced > 0:
                day_feasible = False
                feasible = False
        used = sum(it.duration for it in plan.items)
        days.append({"date": str(day), "feasible": day_feasible, "used_seconds": used})
        day += _dt.timedelta(days=1)

    result_lines = []
    for idx, line in enumerate(lines):
        placed_list = line_placed[idx]
        requested = int(line["count"])
        placed_min = min(placed_list) if placed_list else 0
        unplaced_max = max((requested - p for p in placed_list), default=0) if placed_list else requested
        result_lines.append({
            "label": line.get("label", f"Senaryo {idx + 1}"),
            "requested": requested,
            "placed_min": placed_min,
            "unplaced_max": max(0, unplaced_max),
        })

    return {"feasible": feasible, "lines": result_lines, "days": days}


# ─────────────────────────────────────────────────────────────────────────────
# Yardimcilar — HH:MM dakika donusumu
# ─────────────────────────────────────────────────────────────────────────────


def hhmm_to_minute(value: str, *, allow_2400: bool = False) -> int:
    """'HH:MM' -> dakika. allow_2400 True ise '24:00' = 1440."""
    parts = str(value).strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Gecersiz saat: {value!r} (HH:MM bekleniyor).")
    h, m = int(parts[0]), int(parts[1])
    total = h * 60 + m
    if allow_2400 and total == 1440:
        return 1440
    if not (0 <= total <= 1439):
        raise ValueError(f"Saat araligi disi: {value!r}.")
    return total


def _minute_to_hhmm(minute: int) -> str:
    minute = int(minute)
    return f"{minute // 60:02d}:{minute % 60:02d}"


def second_to_hhmmss(second: int) -> str:
    second = int(second)
    h = second // 3600
    m = (second % 3600) // 60
    s = second % 60
    return f"{h:02d}:{m:02d}:{s:02d}"
