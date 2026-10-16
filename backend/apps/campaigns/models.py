"""DOOH sponsorluk (reklam) modelleri.

Yeniden tasarim: Sponsorluk = ``Campaign``. Her kiosk atamasi ``KioskSponsorship``
ile tanimlanir (tek zaman penceresi + gunluk toplam gosterim N). Tek yerlesim
motoru (``services/sponsorship_engine.py``) saatlik ``Playlist`` / ``PlaylistItem``
kayitlarini uretir.
"""
import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel


def _https_url_validator(value: str) -> None:
    """Yalnizca http(s) semalarina izin ver — javascript:/file:/data: bloklanir."""
    lower = (value or "").lower()
    if not (lower.startswith("https://") or lower.startswith("http://")):
        raise ValidationError("medya_url yalnizca http veya https olabilir.")


# ─────────────────────────────────────────────────────────────────────────────
# Campaign (Sponsorluk) — basitlestirilmis
# ─────────────────────────────────────────────────────────────────────────────


class Campaign(BaseModel):
    """Reklam sponsorlugu. Bir reklamveren altinda bir veya daha cok creative barindirir.

    Kiosk atamalari ``KioskSponsorship`` ile yapilir; hedefleme/il-ilce/kota yoktur.
    """

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        PAUSED = "PAUSED", "Paused"
        COMPLETED = "COMPLETED", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    advertiser_name = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Reklamveren adi (admin panel icin serbest metin).",
    )
    name = models.CharField(max_length=255)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        db_table = "dooh_campaigns"
        ordering = ("-olusturulma_tarihi",)
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"
        indexes = [
            models.Index(fields=("status", "start_date", "end_date")),
        ]

    def __str__(self) -> str:
        return self.name

    def is_active_on(self, when) -> bool:
        return (
            self.status == self.Status.ACTIVE
            and self.start_date <= when <= self.end_date
        )

    @property
    def effective_state(self) -> str:
        """Turetilmis durum (SCHEDULED = ACTIVE & henuz baslamamis)."""
        from django.utils import timezone
        if self.status == self.Status.ACTIVE and self.start_date > timezone.now():
            return "SCHEDULED"
        return self.status


class Creative(BaseModel):
    """Bir sponsorluga ait yayinlanabilir medya (gorsel/video)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="creatives"
    )
    media_url = models.URLField(max_length=2048, validators=[_https_url_validator])
    duration_seconds = models.PositiveSmallIntegerField(
        help_text="Yayin suresi (saniye). 1..60."
    )
    name = models.CharField(max_length=255, blank=True, default="")
    checksum = models.CharField(max_length=128, blank=True, default="",
                                help_text="Edge tarafi cache invalidation icin.")
    object_key = models.CharField(
        max_length=512, null=True, blank=True,
        help_text="S3/RustFS obje anahtari (orn. ads/abc123.mp4).",
    )
    active_media_url = models.URLField(
        max_length=2048, blank=True, default="",
        validators=[_https_url_validator],
        help_text="Islem ekrani alt alani icin medya URL'i (~1080x768, yaklasik 7:5).",
    )
    active_object_key = models.CharField(
        max_length=512, null=True, blank=True,
        help_text="active_media_url icin S3/RustFS obje anahtari.",
    )

    _GRID_DURATIONS = frozenset({15, 30, 45, 60})

    @property
    def is_grid_compliant(self) -> bool:
        """duration_seconds 15sn planning grid ile uyumlu mu?"""
        return int(self.duration_seconds) in self._GRID_DURATIONS

    class Meta:
        db_table = "dooh_creatives"
        ordering = ("campaign_id", "olusturulma_tarihi")
        verbose_name = "Creative"
        verbose_name_plural = "Creatives"
        constraints = [
            models.CheckConstraint(
                check=models.Q(duration_seconds__gte=1) & models.Q(duration_seconds__lte=60),
                name="dooh_creative_duration_1_60",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.campaign.name} ({self.duration_seconds}s)"


# ─────────────────────────────────────────────────────────────────────────────
# KioskSponsorship — tek pencere + gunluk toplam N
# ─────────────────────────────────────────────────────────────────────────────


class KioskSponsorship(BaseModel):
    """Bir kiosk'a bir sponsorlugun atanmasi.

    Tek zaman penceresi ``[window_start_minute, window_end_minute)`` icinde
    gunluk toplam ``count`` gosterim. ``active_weekdays`` ISO (1=Pzt..7=Paz);
    null/bos = her gun. ``start_date``/``end_date`` opsiyonel kiosk-seviyesi
    aralik (kampanya araligi ile kesisir).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kiosk = models.ForeignKey(
        "pharmacies.Kiosk", on_delete=models.CASCADE, related_name="sponsorships"
    )
    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="kiosk_sponsorships"
    )
    window_start_minute = models.PositiveSmallIntegerField(
        help_text="Pencere baslangici (gun ici dakika, 0..1439)."
    )
    window_end_minute = models.PositiveSmallIntegerField(
        help_text="Pencere bitisi (exclusive, 1..1440, > baslangic)."
    )
    count = models.PositiveIntegerField(
        help_text="Pencere icinde gunluk toplam gosterim sayisi (>=1)."
    )
    active_weekdays = models.JSONField(
        null=True, blank=True,
        help_text="Aktif gunler (ISO 1=Pzt..7=Paz). null/bos = her gun.",
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "dooh_kiosk_sponsorships"
        ordering = ("kiosk_id", "campaign_id")
        verbose_name = "Kiosk Sponsorship"
        verbose_name_plural = "Kiosk Sponsorships"
        constraints = [
            models.UniqueConstraint(
                fields=("kiosk", "campaign"),
                name="dooh_kiosk_sponsorship_kiosk_campaign_uniq",
            ),
            models.CheckConstraint(
                check=models.Q(window_start_minute__gte=0)
                & models.Q(window_start_minute__lte=1439),
                name="dooh_ks_window_start_range",
            ),
            models.CheckConstraint(
                check=models.Q(window_end_minute__gte=1)
                & models.Q(window_end_minute__lte=1440),
                name="dooh_ks_window_end_range",
            ),
            models.CheckConstraint(
                check=models.Q(window_end_minute__gt=models.F("window_start_minute")),
                name="dooh_ks_window_end_gt_start",
            ),
            models.CheckConstraint(
                check=models.Q(count__gte=1),
                name="dooh_ks_count_min_1",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.window_end_minute <= self.window_start_minute:
            raise ValidationError(
                {"window_end_minute": "window_end_minute window_start_minute'tan buyuk olmalidir."}
            )
        if self.active_weekdays is not None:
            if not isinstance(self.active_weekdays, list):
                raise ValidationError({"active_weekdays": "Liste olmalidir."})
            for d in self.active_weekdays:
                if not isinstance(d, int) or d < 1 or d > 7:
                    raise ValidationError({"active_weekdays": "1-7 arasi tamsayi (ISO)."})
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError({"end_date": "end_date start_date'ten once olamaz."})

    def __str__(self) -> str:
        return f"KS[kiosk={self.kiosk_id} campaign={self.campaign_id}]"


# ─────────────────────────────────────────────────────────────────────────────
# Playlist / PlaylistItem — saatlik on-hesaplanmis yayin
# ─────────────────────────────────────────────────────────────────────────────


class Playlist(BaseModel):
    """Bir kioskun belirli bir gun + saat icin on-hesaplanmis 60sn loop'u."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kiosk = models.ForeignKey(
        "pharmacies.Kiosk", on_delete=models.CASCADE, related_name="playlists"
    )
    target_date = models.DateField()
    target_hour = models.PositiveSmallIntegerField()
    loop_duration_seconds = models.PositiveSmallIntegerField(default=60)
    version = models.PositiveIntegerField(
        default=1,
        help_text="Her uretimde artan versiyon numarasi. Kiosk ping ile karsilastirir.",
    )

    class Meta:
        db_table = "dooh_playlists"
        ordering = ("kiosk_id", "target_date", "target_hour")
        verbose_name = "Playlist"
        verbose_name_plural = "Playlists"
        constraints = [
            models.UniqueConstraint(
                fields=("kiosk", "target_date", "target_hour"),
                name="dooh_playlist_kiosk_date_hour_uniq",
            ),
            models.CheckConstraint(
                check=models.Q(target_hour__gte=0) & models.Q(target_hour__lte=23),
                name="dooh_playlist_hour_0_23",
            ),
        ]

    def __str__(self) -> str:
        return f"Playlist[{self.kiosk_id} {self.target_date} h={self.target_hour}]"


class PlaylistItem(BaseModel):
    """Playlist icindeki tek bir slot (creative + saat ici offset)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    playlist = models.ForeignKey(
        Playlist, on_delete=models.CASCADE, related_name="items"
    )
    creative = models.ForeignKey(
        Creative, on_delete=models.CASCADE, related_name="playlist_items",
        null=True, blank=True,
    )
    playback_order = models.PositiveSmallIntegerField()
    estimated_start_offset_seconds = models.PositiveSmallIntegerField(
        help_text="Saat ici offset (0..3599). Item [offset, offset+duration) araliginda aktif.",
    )

    class Meta:
        db_table = "dooh_playlist_items"
        ordering = ("playlist_id", "playback_order")
        verbose_name = "Playlist Item"
        verbose_name_plural = "Playlist Items"
        indexes = [
            models.Index(fields=("playlist", "playback_order")),
        ]

    def clean(self) -> None:
        super().clean()
        if self.creative_id is None:
            raise ValidationError("PlaylistItem creative alanini icermelidir.")


class PlayLog(BaseModel):
    """Proof of Play — kioskun rapor ettigi gercek yayin olayi."""

    class PlayStatus(models.TextChoices):
        STARTED = "STARTED", "Basladi"
        COMPLETED = "COMPLETED", "Tamamlandi"
        FAILED = "FAILED", "Basarisiz"
        INTERRUPTED = "INTERRUPTED", "Kesildi"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kiosk = models.ForeignKey(
        "pharmacies.Kiosk", on_delete=models.CASCADE, related_name="play_logs"
    )
    creative = models.ForeignKey(
        Creative, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="play_logs",
    )
    played_at = models.DateTimeField(db_index=True)
    duration_played = models.PositiveSmallIntegerField(
        help_text="Gercekten oynatilan sure (saniye)."
    )
    play_event_id = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text="Kiosk tarafindan uretilen idempotency anahtari. NULL = eski kiosk surumu.",
    )
    status = models.CharField(
        max_length=16,
        choices=PlayStatus.choices,
        default=PlayStatus.COMPLETED,
        db_index=True,
        help_text="Oynatma durumu. Eski kayitlar COMPLETED varsayilir.",
    )
    expected_duration = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Beklenen oynatma suresi (saniye).",
    )
    error_code = models.CharField(max_length=64, blank=True, default="")
    error_summary = models.CharField(
        max_length=255, blank=True, default="",
        help_text="FAILED durumunda sanitize edilmis kisa hata ozeti.",
    )
    occurred_at = models.DateTimeField(
        null=True, blank=True, db_index=True,
        help_text="Kiosk cihaz zamani.",
    )
    received_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Sunucu zamani (ingest aninda set edilir).",
    )

    class Meta:
        db_table = "dooh_play_logs"
        ordering = ("-played_at",)
        verbose_name = "Play Log"
        verbose_name_plural = "Play Logs"
        indexes = [
            models.Index(fields=("kiosk", "played_at")),
            models.Index(fields=("creative", "played_at")),
            models.Index(fields=("status", "played_at")),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["play_event_id"],
                condition=models.Q(play_event_id__isnull=False),
                name="dooh_play_log_play_event_id_unique_non_null",
            ),
        ]


# ─────────────────────────────────────────────────────────────────────────────
# IdleScreenContent — bekleme (idle) ekraninda gosterilen baslik/metin icerigi
# ─────────────────────────────────────────────────────────────────────────────


class IdleScreenContent(BaseModel):
    """Kiosk bekleme (idle) ekraninda gosterilen duz metin icerigi."""

    id = models.BigAutoField(primary_key=True)
    baslik = models.CharField(
        max_length=250,
        help_text="Idle ekrani basligi (duz metin, en fazla 250 karakter).",
    )
    baslik_en = models.CharField(
        max_length=250, blank=True, null=True, default="",
        help_text="Ingilizce idle basligi. Bos = kioskta Turkce basliga geri doner.",
    )
    metin = models.CharField(
        max_length=1000,
        help_text="Idle ekrani metni (duz metin).",
    )
    metin_en = models.CharField(
        max_length=1000, null=True, blank=True, default="",
        help_text="Ingilizce idle metni. Bos = kioskta Turkce metne geri doner.",
    )
    aktif = models.BooleanField(
        default=True,
        help_text="Pasif icerikler kiosk katalogda gorunmez.",
    )
    kategori = models.ForeignKey(
        "products.Kategori",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="idle_contents",
        help_text="Opsiyonel: bu icerigi iliskilendiren saglik kategorisi.",
    )

    class Meta:
        db_table = "dooh_idle_screen_contents"
        ordering = ("-guncellenme_tarihi",)
        verbose_name = "Idle Screen Content"
        verbose_name_plural = "Idle Screen Contents"

    def __str__(self) -> str:
        return self.baslik


# ─────────────────────────────────────────────────────────────────────────────
# Generation Job — asenkron playlist uretim isi (APScheduler + DB queue)
# ─────────────────────────────────────────────────────────────────────────────


class GenerationJob(BaseModel):
    """Bir playlist uretim isinin durumu (DB-backed queue)."""

    class JobStatus(models.TextChoices):
        PENDING = "PENDING", "Bekliyor"
        RUNNING = "RUNNING", "Calisiyor"
        DONE = "DONE", "Tamamlandi"
        FAILED = "FAILED", "Basarisiz"
        RETRY = "RETRY", "Yeniden Deneniyor"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target_date = models.DateField(db_index=True)
    kiosk = models.ForeignKey(
        "pharmacies.Kiosk", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="generation_jobs",
        help_text="NULL ise tum aktif kiosklar icin uretim yapilir.",
    )
    status = models.CharField(
        max_length=10, choices=JobStatus.choices, default=JobStatus.PENDING, db_index=True
    )
    total_kiosks = models.PositiveIntegerField(default=0)
    done_kiosks = models.PositiveIntegerField(default=0)
    failed_kiosks = models.PositiveIntegerField(default=0)
    playlists_generated = models.PositiveIntegerField(default=0)
    triggered_by = models.CharField(
        max_length=64, default="manual",
        help_text="'manual' | 'nightly' | 'campaign_change'",
    )
    error_detail = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    # ── DB-backed queue fields ─────────────────────────────────────────────
    payload = models.JSONField(
        default=dict, blank=True,
        help_text="Is yuku: {kiosk_id, date, trigger_reason, ...}.",
    )
    available_at = models.DateTimeField(
        null=True, blank=True, db_index=True,
        help_text="Retry gecikmesi sonrasi bu zamandan itibaren calistirilabilir.",
    )
    attempt_count = models.PositiveSmallIntegerField(
        default=0, help_text="Toplam calistirma denemesi."
    )
    max_attempts = models.PositiveSmallIntegerField(
        default=3, help_text="Maksimum deneme sayisi (asilirsa FAILED)."
    )
    worker_id = models.CharField(
        max_length=64, null=True, blank=True,
        help_text="Isi sahiplenen worker kimligi (lease icin).",
    )
    lock_expires_at = models.DateTimeField(
        null=True, blank=True, db_index=True,
        help_text="Worker lease suresi. Asilirsa RUNNING -> RETRY.",
    )
    dedupe_key = models.CharField(
        max_length=256, null=True, blank=True, db_index=True,
        help_text="Coalescing anahtari. Format: 'kd:{kiosk_id}:{date}'.",
    )

    class Meta:
        db_table = "dooh_generation_jobs"
        ordering = ("-olusturulma_tarihi",)
        verbose_name = "Generation Job"
        verbose_name_plural = "Generation Jobs"

    def __str__(self) -> str:
        return f"GenerationJob[{self.target_date} {self.status} {self.triggered_by}]"

    @property
    def progress_pct(self) -> int:
        if not self.total_kiosks:
            return 0
        return int(100 * self.done_kiosks / self.total_kiosks)


# =============================================================================
# PharmacyCampaign — Eczaci paneli kampanyalari (kiosk sisteminden bagimsiz)
# =============================================================================

class PharmacyCampaign(BaseModel):
    """Eczaci panelinde gosterilen basit kampanya.

    Kiosk playlist, scheduler, offline sync ve PlayLog sisteminden tamamen
    bagimsizdir. Yalnizca eczaci paneli gosterimi icin tasarlanmistir.
    """

    ALLOWED_DURATIONS = frozenset({15, 30, 60})

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    media_url = models.URLField(
        max_length=2048, validators=[_https_url_validator],
        help_text="Yatay kampanya gorseli (eczaci panelinde serit ve overlay'de gosterilir).",
    )
    object_key = models.CharField(
        max_length=512, null=True, blank=True,
        help_text="S3/RustFS obje anahtari (upload servisinden turetilir).",
    )
    start_at = models.DateTimeField(help_text="Kampanyanin yayin baslangic tarihi ve saati.")
    end_at = models.DateTimeField(help_text="Kampanyanin yayin bitis tarihi ve saati.")
    duration_seconds = models.PositiveSmallIntegerField(
        default=15,
        help_text="Her dongude gosterim suresi (saniye). Izin verilenler: 15, 30, 60.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Pasif kampanyalar feed'de gorunmez.",
    )
    target_pharmacies = models.ManyToManyField(
        "pharmacies.Eczane", blank=True, related_name="pharmacy_campaigns",
        help_text="Tekil hedef eczaneler.",
    )
    target_iller = models.ManyToManyField(
        "lookups.Il", blank=True, related_name="pharmacy_campaigns",
        help_text="Hedef iller (bu ile bagli tum eczaneleri kapsar).",
    )
    target_ilceler = models.ManyToManyField(
        "lookups.Ilce", blank=True, related_name="pharmacy_campaigns",
        help_text="Hedef ilceler (bu ilceye bagli tum eczaneleri kapsar).",
    )

    class Meta:
        db_table = "pharmacy_campaigns"
        ordering = ("-olusturulma_tarihi",)
        verbose_name = "Pharmacy Campaign"
        verbose_name_plural = "Pharmacy Campaigns"
        indexes = [
            models.Index(fields=("is_active", "start_at", "end_at")),
        ]

    def __str__(self) -> str:
        return self.name
