"""DOOH reklam (kampanya) modelleri — eczane hedefli.

Bu modul iki kusak modeli barindirir:

* **Legacy**: ``Reklam`` ve ``ReklamTakvim`` — basit saat-araligi tabanli yayin
  takvimi (geriye donuk uyumluluk icin korunur).
* **DOOH v2**: ``Campaign`` / ``Creative`` / ``ScheduleRule`` / ``Playlist`` /
  ``PlaylistItem`` / ``PlayLog`` / ``HouseAd`` / ``PricingMatrix`` — merkezi,
  60sn loop tabanli, on-hesaplanmis playlist mimarisi.
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


class Reklam(BaseModel):
    """DOOH idle reklami. Bos hedef_eczaneler = herkese goster."""

    ad = models.CharField(max_length=255)
    musteri = models.CharField(max_length=255, blank=True, default="")
    medya_url = models.URLField(max_length=2048, validators=[_https_url_validator])
    sure_saniye = models.PositiveSmallIntegerField(default=15)
    baslangic_tarihi = models.DateTimeField()
    bitis_tarihi = models.DateTimeField()
    yayin_baslangic = models.TimeField(null=True, blank=True, help_text="Günlük yayın başlangıç saati")
    yayin_bitis = models.TimeField(null=True, blank=True, help_text="Günlük yayın bitiş saati")

    hedef_eczaneler = models.ManyToManyField(
        "pharmacies.Eczane", blank=True, related_name="reklamlar"
    )

    aktif = models.BooleanField(default=True)

    class Meta:
        db_table = "reklamlar"
        ordering = ("-olusturulma_tarihi",)
        verbose_name = "Reklam"
        verbose_name_plural = "Reklamlar"

    def __str__(self) -> str:
        return self.ad


class ReklamTakvim(BaseModel):
    """Reklamin belirli bir kioskta gun ici hangi saatlerde yayinlanacagini tutar."""

    reklam = models.ForeignKey(
        Reklam, on_delete=models.CASCADE, related_name="takvim_atamalari"
    )
    kiosk = models.ForeignKey(
        "pharmacies.Kiosk", on_delete=models.CASCADE, related_name="reklam_takvimi"
    )
    baslangic_saat = models.PositiveSmallIntegerField()
    bitis_saat = models.PositiveSmallIntegerField()
    aktif = models.BooleanField(default=True)

    class Meta:
        db_table = "reklam_takvimi"
        ordering = ("kiosk_id", "baslangic_saat", "bitis_saat")
        verbose_name = "Reklam Takvim Ataması"
        verbose_name_plural = "Reklam Takvim Atamaları"
        constraints = [
            models.CheckConstraint(
                check=models.Q(baslangic_saat__gte=0)
                & models.Q(baslangic_saat__lte=23)
                & models.Q(bitis_saat__gte=1)
                & models.Q(bitis_saat__lte=24)
                & models.Q(baslangic_saat__lt=models.F("bitis_saat")),
                name="reklam_takvimi_saat_araligi_gecerli",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.reklam} -> {self.kiosk} ({self.baslangic_saat}-{self.bitis_saat})"


# ─────────────────────────────────────────────────────────────────────────────
# DOOH v2 — Centralized Pre-Computed Playlist Architecture
# ─────────────────────────────────────────────────────────────────────────────


class Campaign(BaseModel):
    """Reklam kampanyasi (DOOH v2). Bir reklamveren altinda birden cok creative
    barindirir; yayinlanma kurallari ``ScheduleRule`` ile tanimlanir."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        PAUSED = "PAUSED", "Paused"
        COMPLETED = "COMPLETED", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    advertiser_id = models.UUIDField(
        help_text="Reklamveren (advertiser) UUID'si — harici sistem kimligi."
    )
    name = models.CharField(max_length=255)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    target_pharmacies = models.ManyToManyField(
        "pharmacies.Eczane", blank=True, related_name="dooh_campaigns",
        help_text="Bos liste = tum eczanelere yayinla.",
    )

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


class Creative(BaseModel):
    """Bir kampanyaya ait yayinlanabilir medya (gorsel/video)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="creatives"
    )
    media_url = models.URLField(max_length=2048, validators=[_https_url_validator])
    duration_seconds = models.PositiveSmallIntegerField(
        help_text="Yayin suresi (saniye). Tipik: 5, 10, 15, 30."
    )
    name = models.CharField(max_length=255, blank=True, default="")
    checksum = models.CharField(max_length=128, blank=True, default="",
                                help_text="Edge tarafi cache invalidation icin.")

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


class ScheduleRule(BaseModel):
    """Bir kampanyanin yayin frekans matrisi.

    ``frequency_type`` + ``frequency_value`` cifti; opsiyonel ``target_hours``
    (JSON dizisi) ile saat hedefleme yapilir (Null = tum gun).
    """

    class FrequencyType(models.TextChoices):
        PER_LOOP = "PER_LOOP", "Per 60s loop"
        PER_HOUR = "PER_HOUR", "Per hour"
        PER_DAY = "PER_DAY", "Per day"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="schedule_rules"
    )
    frequency_type = models.CharField(max_length=16, choices=FrequencyType.choices)
    frequency_value = models.PositiveSmallIntegerField()
    target_hours = models.JSONField(
        null=True, blank=True,
        help_text="Hedef saatler (0-23). Null/bos = tum gun.",
    )

    class Meta:
        db_table = "dooh_schedule_rules"
        ordering = ("campaign_id", "frequency_type")
        verbose_name = "Schedule Rule"
        verbose_name_plural = "Schedule Rules"
        constraints = [
            models.CheckConstraint(
                check=models.Q(frequency_value__gte=1),
                name="dooh_rule_freq_value_min_1",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.target_hours is not None:
            if not isinstance(self.target_hours, list):
                raise ValidationError({"target_hours": "Liste olmalidir."})
            for h in self.target_hours:
                if not isinstance(h, int) or h < 0 or h > 23:
                    raise ValidationError({"target_hours": "0-23 arasi tamsayilar."})

    def __str__(self) -> str:
        return f"{self.campaign} {self.frequency_type}={self.frequency_value}"


class Playlist(BaseModel):
    """Bir kioskun belirli bir gun + saat icin on-hesaplanmis 60sn loop'u."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kiosk = models.ForeignKey(
        "pharmacies.Kiosk", on_delete=models.CASCADE, related_name="playlists"
    )
    target_date = models.DateField()
    target_hour = models.PositiveSmallIntegerField()
    loop_duration_seconds = models.PositiveSmallIntegerField(default=60)

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
    """Playlist icindeki tek bir slot (creative + offset)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    playlist = models.ForeignKey(
        Playlist, on_delete=models.CASCADE, related_name="items"
    )
    creative = models.ForeignKey(
        Creative, on_delete=models.PROTECT, related_name="playlist_items",
        null=True, blank=True,
    )
    house_ad = models.ForeignKey(
        "campaigns.HouseAd", on_delete=models.PROTECT, related_name="playlist_items",
        null=True, blank=True,
        help_text="Filler (Pass 4) icin; creative NULL olur.",
    )
    playback_order = models.PositiveSmallIntegerField()
    estimated_start_offset_seconds = models.PositiveSmallIntegerField()

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
        if (self.creative_id is None) == (self.house_ad_id is None):
            raise ValidationError(
                "PlaylistItem creative VEYA house_ad alanlarindan tam olarak birini icermelidir."
            )


class PlayLog(BaseModel):
    """Proof of Play — kioskun rapor ettigi gercek yayin olayi."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kiosk = models.ForeignKey(
        "pharmacies.Kiosk", on_delete=models.CASCADE, related_name="play_logs"
    )
    creative = models.ForeignKey(
        Creative, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="play_logs",
    )
    house_ad = models.ForeignKey(
        "campaigns.HouseAd", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="play_logs",
    )
    played_at = models.DateTimeField(db_index=True)
    duration_played = models.PositiveSmallIntegerField(
        help_text="Gercekten oynatilan sure (saniye)."
    )

    class Meta:
        db_table = "dooh_play_logs"
        ordering = ("-played_at",)
        verbose_name = "Play Log"
        verbose_name_plural = "Play Logs"
        indexes = [
            models.Index(fields=("kiosk", "played_at")),
            models.Index(fields=("creative", "played_at")),
        ]


class HouseAd(BaseModel):
    """Dolgu (filler) reklamlari — eczane bilgilendirme / saglik ipuclari /
    nobetci eczane vb. Loop'ta bos kalan saniyeleri doldurur (Pass 4)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    media_url = models.URLField(max_length=2048, validators=[_https_url_validator])
    duration_seconds = models.PositiveSmallIntegerField(default=10)
    aktif = models.BooleanField(default=True)
    priority = models.PositiveSmallIntegerField(
        default=100,
        help_text="Dusuk degerli once secilir (filler queue ordering).",
    )

    class Meta:
        db_table = "dooh_house_ads"
        ordering = ("priority", "olusturulma_tarihi")
        verbose_name = "House Ad"
        verbose_name_plural = "House Ads"
        constraints = [
            models.CheckConstraint(
                check=models.Q(duration_seconds__gte=1) & models.Q(duration_seconds__lte=60),
                name="dooh_house_ad_duration_1_60",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class PricingMatrix(BaseModel):
    """Reklam fiyat carpan matrisi (singleton).

    Toplam fiyat hesabi (referans formul):

        total = base_price_per_second * duration * frequency_multiplier *
                (prime_time_coefficient if hour in prime_hours else 1.0)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    base_price_per_second = models.DecimalField(max_digits=10, decimal_places=4, default=1.0)
    prime_time_coefficient = models.DecimalField(max_digits=6, decimal_places=3, default=1.5)
    prime_hours = models.JSONField(default=list, help_text="Prime time saatleri, orn. [17,18,19,20].")
    frequency_multipliers = models.JSONField(
        default=dict,
        help_text='Frekans tipine gore carpanlar, orn. {"PER_LOOP": 3.0, "PER_HOUR": 1.5, "PER_DAY": 1.0}.',
    )
    currency = models.CharField(max_length=3, default="TRY")
    is_default = models.BooleanField(default=True)

    class Meta:
        db_table = "dooh_pricing_matrix"
        ordering = ("-olusturulma_tarihi",)
        verbose_name = "Pricing Matrix"
        verbose_name_plural = "Pricing Matrices"

    def multiplier_for(self, frequency_type: str) -> float:
        try:
            return float(self.frequency_multipliers.get(frequency_type, 1.0))
        except (TypeError, ValueError):
            return 1.0
