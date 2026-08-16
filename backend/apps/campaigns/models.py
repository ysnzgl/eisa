"""DOOH reklam (kampanya) modelleri.

DOOH v2: ``Campaign`` / ``Creative`` / ``ScheduleRule`` / ``Playlist`` /
``PlaylistItem`` / ``PlayLog`` / ``IdleScreenContent`` / ``PricingMatrix`` — merkezi,
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
    barindirir; yayinlanma kurallari ``ScheduleRule`` / ``DeliveryRule`` ile tanimlanir."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Taslak"              # Faz 1: henuz yayinda degil
        ACTIVE = "ACTIVE", "Active"
        PAUSED = "PAUSED", "Paused"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Iptal"       # Faz 1: kalici iptal

    class TargetScope(models.TextChoices):
        ALL = "ALL", "Tum aktif kiosklar"      # Hedef kural gerektirmez
        RULES = "RULES", "Hedefleme kurallari" # CampaignTarget satirlarina gore

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
    target_scope = models.CharField(
        max_length=8, choices=TargetScope.choices, null=True, blank=True,
        help_text=(
            "Hedefleme kapsami. "
            "NULL = legacy davranis (CampaignTarget yoksa tum kiosklar). "
            "ALL = tum aktif kiosklar dinamik. "
            "RULES = CampaignTarget kayitlarina gore (include/exclude). "
            "Faz 1'de eklendu; Faz 2+'de zorunlu olmasi planlanmaktadir."
        ),
    )
    follows = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="followed_by",
        help_text=(
            "A->B ardisillik: bu kampanya hangi kampanyadan hemen sonra oynansin. "
            "Yalniz ikili (A->B); zincir/dongü yasak. "
            "Service-level validation uygulanir."
        ),
    )

    # Pacing: Faz 7'de is_guaranteed, impression_goal, frequency_cap_per_hour kaldırıldı.
    # Canonical: DeliveryRule(CAMPAIGN_TOTAL / GUARANTEED).
    # Öncelik alanı korunuyor (placement engine ordering için).
    priority = models.PositiveSmallIntegerField(
        default=50,
        help_text="Slot cakismasinda oncelik (1=en yuksek, 100=en dusuk). Dusuk deger once yerlesir.",
    )

    # Legacy M2M (geriye donus uyumluluk; yeni kampanyalar CampaignTarget kullanir)
    # Fiziksel alan korunuyor (legacy data compat); yeni kampanyalar CampaignTarget kullanir.
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
        constraints = [
            # follows kendi kendine bakamazsiniz (A->B, not A->A)
            models.CheckConstraint(
                check=~models.Q(follows=models.F("id")),
                name="dooh_campaign_no_self_follow",
            ),
            # Bir kampanyanin en fazla bir dogrudan ardili olabilir
            models.UniqueConstraint(
                fields=["follows"],
                condition=models.Q(follows__isnull=False),
                name="dooh_campaign_follows_unique_predecessor",
            ),
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
        KIOSK = "KIOSK", "Tekil Kiosk"   # Faz 1

    class TargetMode(models.TextChoices):
        INCLUDE = "INCLUDE", "Dahil et"   # Faz 1: varsayilan
        EXCLUDE = "EXCLUDE", "Haric tut"  # Faz 1: cikart

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
    kiosk = models.ForeignKey(
        "pharmacies.Kiosk", on_delete=models.CASCADE, null=True, blank=True,
        related_name="+",
        help_text="KIOSK tipi icin zorunlu.",
    )
    mode = models.CharField(
        max_length=8, choices=TargetMode.choices, null=True, blank=True,
        help_text="INCLUDE (dahil et) veya EXCLUDE (hariç tut). NULL = legacy INCLUDE davranisi.",
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
        if self.target_type == self.TargetType.KIOSK and not self.kiosk_id:
            raise ValidationError({"kiosk": "KIOSK hedefi için kiosk alanı zorunludur."})

    def __str__(self) -> str:
        if self.target_type == self.TargetType.IL:
            return f"IL:{self.il}"
        if self.target_type == self.TargetType.ILCE:
            return f"ILCE:{self.ilce}"
        if self.target_type == self.TargetType.KIOSK:
            return f"KIOSK:{self.kiosk}"
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
    object_key = models.CharField(
        max_length=512, null=True, blank=True,
        help_text=(
            "S3/RustFS obje anahtarı (örn. ads/abc123.mp4). "
            "Kalıcı media_url üretiminde kullanılır. "
            "NULL ise backfill_media_object_keys komutuyla doldurulabilir."
        ),
    )
    weight = models.PositiveSmallIntegerField(
        default=1,
        help_text="Rotasyon agirligi (1=esit). V2 motor agirlikli round-robin icin kullanir.",
    )
    active_media_url = models.URLField(
        max_length=2048, blank=True, default="",
        validators=[_https_url_validator],
        help_text=(
            "Islem ekrani alt alani icin medya URL'i (~1080x768, yaklasik 7:5). "
            "Bos birakılırsa AdStrip'te bekleme ekrani gorseli fallback olarak kullanilir."
        ),
    )
    active_object_key = models.CharField(
        max_length=512, null=True, blank=True,
        help_text=(
            "active_media_url icin S3/RustFS obje anahtarı (örn. ads/abc123.mp4). "
            "NULL ise backfill_media_object_keys komutuyla doldurulabilir."
        ),
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
        if self.creative_id is None:
            raise ValidationError(
                "PlaylistItem creative alanini icermelidir."
            )


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
    # Faz 3: oynatma durumu + zengin alan seti
    status = models.CharField(
        max_length=16,
        choices=PlayStatus.choices,
        default=PlayStatus.COMPLETED,
        db_index=True,
        help_text="Oynatma durumu. Eski kayitlar COMPLETED varsayilir.",
    )
    expected_duration = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Beklenen oynatma suresi (saniye). PlaylistItem.duration_seconds'tan gelir.",
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
            # Nullable unique: ayni play_event_id iki kez gonderilmez; NULL = eski format
            models.UniqueConstraint(
                fields=["play_event_id"],
                condition=models.Q(play_event_id__isnull=False),
                name="dooh_play_log_play_event_id_unique_non_null",
            ),
        ]


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
# IdleScreenContent — bekleme (idle) ekraninda gosterilen baslik/metin icerigi
# ─────────────────────────────────────────────────────────────────────────────


class IdleScreenContent(BaseModel):
    """Kiosk bekleme (idle) ekraninda gosterilen duz metin icerigi.

    Baslik fade, metin daktilo animasyonu ile ``AdPromo large`` gorunumunde
    rastgele (shuffled-bag) dondurulur. Medya/HTML icermez; yalniz duz metin.
    Eski gorsel tabanli ``HouseAd`` idle icerigi bu modelle degistirildi.
    """

    id = models.BigAutoField(primary_key=True)
    baslik = models.CharField(
        max_length=250,
        help_text="Idle ekrani basligi (duz metin, en fazla 250 karakter).",
    )
    metin = models.CharField(
        max_length=1000,
        help_text="Idle ekrani metni (duz metin, en fazla 500 karakter).",
    )
    aktif = models.BooleanField(
        default=True,
        help_text="Pasif icerikler kiosk katalogda gorunmez.",
    )
    kategori = models.ForeignKey(
        "products.Kategori",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
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
        RETRY = "RETRY", "Yeniden Deneniyor"   # Faz 4: geçici hata sonrası backoff

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

    # ── Faz 4: DB-backed queue fields ─────────────────────────────────────────
    payload = models.JSONField(
        default=dict, blank=True,
        help_text=(
            "İş yükü: {kiosk_id, date, trigger_reason, ...}. "
            "Model instance, credential veya secret içermez."
        ),
    )
    available_at = models.DateTimeField(
        null=True, blank=True, db_index=True,
        help_text="Retry gecikmesi sonrası bu zamandan itibaren çalıştırılabilir.",
    )
    attempt_count = models.PositiveSmallIntegerField(
        default=0, help_text="Toplam çalıştırma denemesi."
    )
    max_attempts = models.PositiveSmallIntegerField(
        default=3, help_text="Maksimum deneme sayısı (aşılırsa FAILED)."
    )
    worker_id = models.CharField(
        max_length=64, null=True, blank=True,
        help_text="İşi sahiplenen worker kimliği (lease için). RUNNING durumunda dolu.",
    )
    lock_expires_at = models.DateTimeField(
        null=True, blank=True, db_index=True,
        help_text="Worker lease süresi. Bu aşılırsa RUNNING → RETRY (stale recovery).",
    )
    dedupe_key = models.CharField(
        max_length=256, null=True, blank=True, db_index=True,
        help_text=(
            "Coalescing anahtarı. Format: 'kd:{kiosk_id}:{date}'. "
            "Aynı anahtar için PENDING job varken yeni oluşturulmaz."
        ),
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
# Faz 1 — Yeni modeller (additive, tum alanlar null=True/blank=True)
# =============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# DeliveryRule — ScheduleRule'un yerine geçecek; dual-read geçis donemi
# ─────────────────────────────────────────────────────────────────────────────


class DeliveryRule(BaseModel):
    """Kampanya yayın frekans ve garanti kuralı (ScheduleRule'un halefi).

    Faz 1'de ScheduleRule ile birlikte (dual-read) yaşar.
    Faz 7'de ScheduleRule deprecate edilir.

    delivery_type:
      TIME_WINDOW    — Belirli pencerede N kez
      PER_HOUR       — Her takvim saatinde N kez (per-kiosk)
      PER_DAY        — Her günde N kez (per-kiosk)
      CAMPAIGN_TOTAL — Kampanya boyunca toplam N gösterim (global; PlanningRun/KioskDayQuota ile)
      LEGACY_PER_LOOP — PER_LOOP'tan dönüştürülen salt-okunur kural
    """

    class DeliveryType(models.TextChoices):
        TIME_WINDOW = "TIME_WINDOW", "Belirli Zaman Penceresi"
        PER_HOUR = "PER_HOUR", "Saatte N kez (per-kiosk)"
        PER_DAY = "PER_DAY", "Gunde N kez (per-kiosk)"
        CAMPAIGN_TOTAL = "CAMPAIGN_TOTAL", "Kampanya Toplami (global)"
        LEGACY_PER_LOOP = "LEGACY_PER_LOOP", "Loop Basi (Legacy, salt-okunur)"

    class GuaranteeMode(models.TextChoices):
        GUARANTEED = "GUARANTEED", "Garanti (kapasite ayrilir)"
        BEST_EFFORT = "BEST_EFFORT", "En Iyi Caba (bos slota yerlesir)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.OneToOneField(
        Campaign, on_delete=models.CASCADE, related_name="delivery_rule"
    )
    delivery_type = models.CharField(max_length=20, choices=DeliveryType.choices)
    count = models.PositiveIntegerField(
        help_text="Gosterim sayisi (TIME_WINDOW/PER_HOUR/PER_DAY/CAMPAIGN_TOTAL icin)."
    )
    window_start_time = models.TimeField(
        null=True, blank=True,
        help_text="TIME_WINDOW baslangici (HH:MM). TIME_WINDOW icin zorunlu.",
    )
    window_end_time = models.TimeField(
        null=True, blank=True,
        help_text="TIME_WINDOW bitisi (HH:MM). TIME_WINDOW icin zorunlu.",
    )
    active_hours = models.JSONField(
        null=True, blank=True,
        help_text="Aktif saatler (0-23). Null = tum gun.",
    )
    active_weekdays = models.JSONField(
        null=True, blank=True,
        help_text="Aktif haftanin gunleri (0=Pzt..6=Paz). Null = her gun.",
    )
    guarantee_mode = models.CharField(
        max_length=12, choices=GuaranteeMode.choices,
        default=GuaranteeMode.BEST_EFFORT,
    )
    max_per_hour = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Saatlik azami gosterim (opsiyonel cap, per-kiosk).",
    )

    class Meta:
        db_table = "dooh_delivery_rules"
        ordering = ("campaign_id",)
        verbose_name = "Delivery Rule"
        verbose_name_plural = "Delivery Rules"
        constraints = [
            models.CheckConstraint(
                check=models.Q(count__gte=1),
                name="dooh_delivery_rule_count_min_1",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.delivery_type == self.DeliveryType.TIME_WINDOW:
            if not self.window_start_time or not self.window_end_time:
                raise ValidationError(
                    "TIME_WINDOW icin window_start_time ve window_end_time zorunludur."
                )
        if self.active_hours is not None:
            if not isinstance(self.active_hours, list):
                raise ValidationError({"active_hours": "Liste olmalidir."})
            for h in self.active_hours:
                if not isinstance(h, int) or h < 0 or h > 23:
                    raise ValidationError({"active_hours": "0-23 arasi tamsayi olmalidir."})
        if self.active_weekdays is not None:
            if not isinstance(self.active_weekdays, list):
                raise ValidationError({"active_weekdays": "Liste olmalidir."})
            for d in self.active_weekdays:
                if not isinstance(d, int) or d < 0 or d > 6:
                    raise ValidationError({"active_weekdays": "0-6 arasi tamsayi olmalidir."})

    def __str__(self) -> str:
        return f"{self.campaign} {self.delivery_type}={self.count} [{self.guarantee_mode}]"


# ─────────────────────────────────────────────────────────────────────────────
# PlanningRun + KioskDayQuota — CAMPAIGN_TOTAL global kota yonetimi
# ─────────────────────────────────────────────────────────────────────────────


class PlanningRun(BaseModel):
    """Bir horizon uretiminin atomik referansi.

    CAMPAIGN_TOTAL kampanyalar icin kiosk-gun kotalarini onceden hesaplar.
    Her PlanningRun bir horizon (baslangic..bitis) icin uretimi temsil eder.
    """

    class RunStatus(models.TextChoices):
        PENDING = "PENDING", "Bekliyor"
        ACTIVE = "ACTIVE", "Aktif"
        DONE = "DONE", "Tamamlandi"
        FAILED = "FAILED", "Basarisiz"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    horizon_start = models.DateField()
    horizon_end = models.DateField()
    status = models.CharField(
        max_length=8, choices=RunStatus.choices, default=RunStatus.PENDING,
    )

    class Meta:
        db_table = "dooh_planning_runs"
        ordering = ("-olusturulma_tarihi",)
        verbose_name = "Planning Run"
        verbose_name_plural = "Planning Runs"

    def __str__(self) -> str:
        return f"PlanningRun[{self.horizon_start}..{self.horizon_end} {self.status}]"


class CampaignTotalAllocation(BaseModel):
    """CAMPAIGN_TOTAL kampanya icin planning run basina kota ozeti.

    sum(KioskDayQuota.quota for this campaign/run) == total_target garantisi.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    planning_run = models.ForeignKey(
        PlanningRun, on_delete=models.CASCADE, related_name="allocations"
    )
    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="total_allocations"
    )
    total_target = models.PositiveIntegerField(
        help_text="DeliveryRule.count (kampanya toplami)."
    )
    allocated_total = models.PositiveIntegerField(
        default=0, help_text="Kiosk-gun kotalarinin toplami."
    )

    class Meta:
        db_table = "dooh_campaign_total_allocations"
        ordering = ("planning_run_id", "campaign_id")
        verbose_name = "Campaign Total Allocation"
        verbose_name_plural = "Campaign Total Allocations"
        constraints = [
            models.UniqueConstraint(
                fields=("planning_run", "campaign"),
                name="dooh_cta_run_campaign_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"CTA[{self.campaign} run={self.planning_run_id}]"


class KioskDayQuota(BaseModel):
    """CAMPAIGN_TOTAL icin kiosk+gun bazinda kota ve yerlesme sayaci.

    Bagimsiz kiosk+gun islemleri bu tablo uzerinden global toplami korur:
      sum(placed for all kiosk-days) <= CampaignTotalAllocation.total_target
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    planning_run = models.ForeignKey(
        PlanningRun, on_delete=models.CASCADE, related_name="kiosk_quotas"
    )
    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="kiosk_quotas"
    )
    kiosk = models.ForeignKey(
        "pharmacies.Kiosk", on_delete=models.CASCADE, related_name="+"
    )
    date = models.DateField()
    quota = models.PositiveIntegerField(
        default=0, help_text="Bu kiosk-gun icin izin verilen gosterim sayisi."
    )
    placed = models.PositiveIntegerField(
        default=0, help_text="Uretimde gercekten yerlestirilen gosterim sayisi."
    )

    class Meta:
        db_table = "dooh_kiosk_day_quotas"
        ordering = ("planning_run_id", "campaign_id", "date")
        verbose_name = "Kiosk Day Quota"
        verbose_name_plural = "Kiosk Day Quotas"
        constraints = [
            models.UniqueConstraint(
                fields=("planning_run", "campaign", "kiosk", "date"),
                name="dooh_kdq_run_campaign_kiosk_date_uniq",
            ),
            models.CheckConstraint(
                check=models.Q(quota__gte=0),
                name="dooh_kdq_quota_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(placed__gte=0),
                name="dooh_kdq_placed_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(placed__lte=models.F("quota")),
                name="dooh_kdq_placed_lte_quota",
            ),
        ]

    def __str__(self) -> str:
        return f"KDQ[{self.campaign} kiosk={self.kiosk_id} {self.date}]"


# ─────────────────────────────────────────────────────────────────────────────
# KioskDesiredBundle — monoton desired_bundle_version (Faz 5'te aktif kullanilir)
# ─────────────────────────────────────────────────────────────────────────────


class KioskDesiredBundle(BaseModel):
    """Kiosk bazinda monoton artan desired_bundle_version.

    Faz 1'de yapi olusturulur; Faz 5'te kiosk API ve ACK mekanizmasiyla aktif olur.
    Fingerprint: tum horizon gunlerindeki canonical kiosk payload'inin hash'i
    (asset_id, object_key, media_url, checksum, duration, offset vs. dahil).
    Fingerprint degismemisse version artmaz.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kiosk = models.OneToOneField(
        "pharmacies.Kiosk", on_delete=models.CASCADE, related_name="desired_bundle"
    )
    desired_bundle_version = models.PositiveIntegerField(
        default=0,
        help_text="Kiosk bazinda monoton artan versiyon (Max(Playlist.version) KULLANILMAZ).",
    )
    content_fingerprint = models.CharField(
        max_length=64, blank=True, default="",
        help_text="SHA-256 (hex) canonical payload hash. Degismemisse version artmaz.",
    )
    valid_from = models.DateField(
        null=True, blank=True,
        help_text="Gecerli horizon baslangici.",
    )
    horizon_days = models.PositiveSmallIntegerField(
        default=3,
        help_text="Kac gun ileri playlist uretiliyor (rolling horizon).",
    )

    class Meta:
        db_table = "dooh_kiosk_desired_bundles"
        ordering = ("kiosk_id",)
        verbose_name = "Kiosk Desired Bundle"
        verbose_name_plural = "Kiosk Desired Bundles"

    def __str__(self) -> str:
        return f"KDB[kiosk={self.kiosk_id} v={self.desired_bundle_version}]"


# =============================================================================
# PharmacyCampaign — Eczacı paneli kampanyaları (kiosk sisteminden bağımsız)
# =============================================================================

class PharmacyCampaign(BaseModel):
    """Eczacı panelinde gösterilen basit kampanya.

    Kiosk playlist, scheduler, offline sync ve PlayLog sisteminden tamamen
    bağımsızdır. Yalnızca eczacı paneli gösterimi için tasarlanmıştır.

    Hedefleme: target_pharmacies (tekil eczane), target_iller (il), target_ilceler (ilçe).
    Feed eşleşmesi: bu üçünden herhangi biriyle eşleşen eczacıya kampanya gösterilir (OR).
    """

    # İzin verilen gösterim süreleri (saniye)
    ALLOWED_DURATIONS = frozenset({15, 30, 60})

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    media_url = models.URLField(
        max_length=2048, validators=[_https_url_validator],
        help_text="Yatay kampanya görseli (eczacı panelinde şerit ve overlay'de gösterilir).",
    )
    object_key = models.CharField(
        max_length=512, null=True, blank=True,
        help_text="S3/RustFS obje anahtarı (upload servisinden türetilir).",
    )
    start_at = models.DateTimeField(help_text="Kampanyanın yayın başlangıç tarihi ve saati.")
    end_at = models.DateTimeField(help_text="Kampanyanın yayın bitiş tarihi ve saati.")
    duration_seconds = models.PositiveSmallIntegerField(
        default=15,
        help_text="Her döngüde gösterim süresi (saniye). İzin verilenler: 15, 30, 60.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Pasif kampanyalar feed'de görünmez.",
    )
    # Hedefleme — üçü OR mantığıyla çalışır
    target_pharmacies = models.ManyToManyField(
        "pharmacies.Eczane", blank=True, related_name="pharmacy_campaigns",
        help_text="Tekil hedef eczaneler.",
    )
    target_iller = models.ManyToManyField(
        "lookups.Il", blank=True, related_name="pharmacy_campaigns",
        help_text="Hedef iller (bu ile bağlı tüm eczaneleri kapsar).",
    )
    target_ilceler = models.ManyToManyField(
        "lookups.Ilce", blank=True, related_name="pharmacy_campaigns",
        help_text="Hedef ilçeler (bu ilçeye bağlı tüm eczaneleri kapsar).",
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
