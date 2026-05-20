"""DOOH reklam (kampanya) modelleri.

DOOH v2: ``Campaign`` / ``Creative`` / ``ScheduleRule`` / ``Playlist`` /
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
        null=True, blank=True,
        help_text="Reklamveren (advertiser) UUID'si — harici sistem kimligi (opsiyonel)."
    )
    advertiser_name = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Reklamveren adi (admin panel icin serbest metin)."
    )
    name = models.CharField(max_length=255)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    # Pacing alanları
    impression_goal = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Toplam gösterim hedefi (opsiyonel). Örn: 5000 kez göster.",
    )
    frequency_cap_per_hour = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Saatte maksimum gösterim sayısı (opsiyonel). Örn: saatte en fazla 2 kez çıksın.",
    )

    # Öncelik & güvence
    priority = models.PositiveSmallIntegerField(
        default=50,
        help_text="Slot çakışmasında öncelik (1=en yüksek, 100=en düşük). Düşük değer önce yerleşir.",
    )
    is_guaranteed = models.BooleanField(
        default=False,
        help_text="True ise kapasite dolsa bile hiç atlanmaz; Pass 4 filler'dan yer açılır.",
    )

    # Legacy M2M (geriye dönük uyumluluk; yeni kampanyalar CampaignTarget kullanır)
    target_pharmacies = models.ManyToManyField(
        "pharmacies.Eczane", blank=True, related_name="dooh_campaigns",
        help_text="[Eski] Bos liste = tum eczanelere yayinla. Yeni kampanyalar CampaignTarget kullanir.",
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


class CampaignTarget(BaseModel):
    """Kampanya lokasyon hedefi (Il / Ilce / Eczane hiyerarsisi).

    Bir kampanya; il, ilce veya spesifik eczane seviyesinde hedeflenebilir.
    Scheduler bu kayitlari cozumleyerek hangi eczanelerin etkilendigini bulur.

    Ornekler:
      - type=IL,    il=Ankara_id        => Ankara'nin tum eczaneleri
      - type=ILCE,  ilce=Melikgazi_id   => Melikgazi'nin tum eczaneleri
      - type=ECZANE,eczane=xyz_id       => Tek spesifik eczane
    """

    class TargetType(models.TextChoices):
        IL = "IL", "İl (Tüm ilçe ve eczaneler)"
        ILCE = "ILCE", "İlçe (Tüm eczaneler)"
        ECZANE = "ECZANE", "Spesifik Eczane"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="targets"
    )
    target_type = models.CharField(max_length=8, choices=TargetType.choices)
    il = models.ForeignKey(
        "lookups.Il", on_delete=models.PROTECT, null=True, blank=True,
        related_name="+",
    )
    ilce = models.ForeignKey(
        "lookups.Ilce", on_delete=models.PROTECT, null=True, blank=True,
        related_name="+",
    )
    eczane = models.ForeignKey(
        "pharmacies.Eczane", on_delete=models.CASCADE, null=True, blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "dooh_campaign_targets"
        ordering = ("campaign_id", "target_type")
        verbose_name = "Campaign Target"
        verbose_name_plural = "Campaign Targets"

    def clean(self) -> None:
        super().clean()
        if self.target_type == self.TargetType.IL and not self.il_id:
            raise ValidationError({"il": "IL hedefi için il alanı zorunludur."})
        if self.target_type == self.TargetType.ILCE and not self.ilce_id:
            raise ValidationError({"ilce": "ILCE hedefi için ilce alanı zorunludur."})
        if self.target_type == self.TargetType.ECZANE and not self.eczane_id:
            raise ValidationError({"eczane": "ECZANE hedefi için eczane alanı zorunludur."})

    def __str__(self) -> str:
        if self.target_type == self.TargetType.IL:
            return f"IL:{self.il}"
        if self.target_type == self.TargetType.ILCE:
            return f"ILCE:{self.ilce}"
        return f"ECZANE:{self.eczane}"


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
    campaign = models.OneToOneField(
        Campaign, on_delete=models.CASCADE, related_name="schedule_rule"
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
    version = models.PositiveIntegerField(
        default=1,
        help_text="Her üretimde artan versiyon numarası. Kiosk ping ile karşılaştırır.",
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
    """Playlist icindeki tek bir slot (creative + offset)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    playlist = models.ForeignKey(
        Playlist, on_delete=models.CASCADE, related_name="items"
    )
    creative = models.ForeignKey(
        Creative, on_delete=models.CASCADE, related_name="playlist_items",
        null=True, blank=True,
    )
    house_ad = models.ForeignKey(
        "campaigns.HouseAd", on_delete=models.CASCADE, related_name="playlist_items",
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


# ─────────────────────────────────────────────────────────────────────────────
# Playlist Şablon — elle tasarlanmış loop yapısını saklar
# ─────────────────────────────────────────────────────────────────────────────

class PlaylistTemplate(BaseModel):
    """Görsel editörde tasarlanmış 60sn loop şablonu.

    ``slots`` JSON alanı, her slot için offset/duration/campaign bilgisini saklar.
    Şablon belirli bir kiosk/il/ilçe kırılımına uygulanarak Playlist üretimini tetikler.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    loop_duration_seconds = models.PositiveSmallIntegerField(default=60)
    slots = models.JSONField(
        default=list,
        help_text=(
            "[{campaign_id, creative_id, offset_seconds, duration_seconds}, ...] "
            "seklinde 60sn slot listesi."
        ),
    )
    target_hours = models.JSONField(
        default=list,
        blank=True,
        help_text="Bu sablonun aktif oldugu saat dilimleri (0-23). Bos = herhangi bir saat kurali tanimlanmamis.",
    )
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "dooh_playlist_templates"
        ordering = ("-olusturulma_tarihi",)
        verbose_name = "Playlist Template"
        verbose_name_plural = "Playlist Templates"

    def __str__(self) -> str:
        return self.name


# ─────────────────────────────────────────────────────────────────────────────
# HourPlan — 1 saatlik yayın planı (LoopTemplate sekansı)
# ─────────────────────────────────────────────────────────────────────────────

class HourPlan(BaseModel):
    """Bir saatlik yayın planı. Birden fazla 60sn LoopTemplate'i sırayla tanımlar.

    ``slots`` JSON alanı, her slot için dakika ofseti, süre ve hangi LoopTemplate
    kullanılacağını saklar::

        [
          {"offset_minutes": 0, "duration_minutes": 30, "loop_template_id": "<uuid>"},
          {"offset_minutes": 30, "duration_minutes": 30, "loop_template_id": "<uuid>"},
        ]

    Toplam duration_minutes <= 60 olmalıdır.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    slots = models.JSONField(
        default=list,
        help_text=(
            "[{offset_minutes, duration_minutes, loop_template_id}, ...] "
            "seklinde 60 dakikalik slot listesi."
        ),
    )

    class Meta:
        db_table = "dooh_hour_plans"
        ordering = ("-olusturulma_tarihi",)
        verbose_name = "Hour Plan"
        verbose_name_plural = "Hour Plans"

    def __str__(self) -> str:
        return self.name


# ─────────────────────────────────────────────────────────────────────────────
# DayPlan — 24 saatlik günlük yayın planı (HourPlan haritası)
# ─────────────────────────────────────────────────────────────────────────────

class DayPlan(BaseModel):
    """24 saatlik günlük yayın planı. Her saate bir HourPlan atar.

    ``slots`` JSON alanı::

        [
          {"hour": 0, "hour_plan_id": "<uuid>"},
          {"hour": 8, "hour_plan_id": "<uuid>"},
          ...
        ]

    Aynı saat birden fazla kez tanımlanamaz. Tanımlanmayan saatler otomatik
    üretimde atlanır (boş kalır).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    slots = models.JSONField(
        default=list,
        help_text=(
            "[{hour: 0..23, hour_plan_id: uuid}, ...] "
            "seklinde 24 saatlik HourPlan atamalari."
        ),
    )

    class Meta:
        db_table = "dooh_day_plans"
        ordering = ("-olusturulma_tarihi",)
        verbose_name = "Day Plan"
        verbose_name_plural = "Day Plans"

    def __str__(self) -> str:
        return self.name


# ─────────────────────────────────────────────────────────────────────────────
# Generation Job — asenkron playlist üretim işi (APScheduler + PostgreSQL)
# ─────────────────────────────────────────────────────────────────────────────

class GenerationJob(BaseModel):
    """Bir playlist üretim işinin durumu.

    Admin panel bu tabloyu poll ederek progress bar ve sonuç özeti gösterir.
    APScheduler nightly job veya manuel tetikleme her ikisi de bu kaydı oluşturur.
    """

    class JobStatus(models.TextChoices):
        PENDING = "PENDING", "Bekliyor"
        RUNNING = "RUNNING", "Çalışıyor"
        DONE = "DONE", "Tamamlandı"
        FAILED = "FAILED", "Başarısız"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target_date = models.DateField(db_index=True)
    kiosk = models.ForeignKey(
        "pharmacies.Kiosk", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="generation_jobs",
        help_text="NULL ise tüm aktif kiosklar için üretim yapılır.",
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
