"""Anonim demografik ve davranissal log modelleri (KVKK uyumlu)."""
import uuid

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class OturumLogu(BaseModel):
    """Bir kiosk oturumu â€” kisiyi tanimlayan hicbir veri ICERMEZ."""

    # Kioskun urettigi duplicate-koruma anahtari (SEC-004 / ARC-001).
    idempotency_anahtari = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, db_index=True
    )
    kiosk = models.ForeignKey(
        "pharmacies.Kiosk", on_delete=models.CASCADE, related_name="oturumlar"
    )
    yas_araligi = models.ForeignKey(
        "lookups.YasAraligi", on_delete=models.PROTECT, related_name="oturumlar"
    )
    cinsiyet = models.ForeignKey(
        "lookups.Cinsiyet", on_delete=models.PROTECT, related_name="oturumlar"
    )
    kategori = models.ForeignKey(
        "products.Kategori", on_delete=models.PROTECT, related_name="oturumlar",
        null=True, blank=True,
        help_text="Sikayet akisi icin kategori (oturum_tipi=SIKAYET ise zorunlu)."
    )

    # Oturum tipi: sikayet veya ozel danismanlik
    class OturumTipi(models.TextChoices):
        SIKAYET = "SIKAYET", "Sikayet"
        OZEL_DANISMANLIK = "OZEL_DANISMANLIK", "Ozel Danismanlik"

    oturum_tipi = models.CharField(
        max_length=16, choices=OturumTipi.choices, default=OturumTipi.SIKAYET,
        db_index=True,
        help_text="Akis turu: sikayet (etken madde onerisi) veya ozel danismanlik."
    )

    # Oturum durum (lifecycle)
    class Durum(models.TextChoices):
        COMPLETED = "COMPLETED", "Tamamlandi"
        ABANDONED = "ABANDONED", "Terk Edildi"
        EXPIRED = "EXPIRED", "Suresi Doldu"  # Sunucu turetimi (read-time veya backfill)

    durum = models.CharField(
        max_length=16,
        choices=Durum.choices,
        default=Durum.COMPLETED,
        db_index=True,
        help_text=(
            "Oturum durumu: COMPLETED (kullanici bitirdi), "
            "ABANDONED (inaktivite/terk), "
            "EXPIRED (danisma gerceklesmeyen, sunucu turetimi)."
        ),
    )
    danisma_kategorisi = models.ForeignKey(
        "products.Danisma", on_delete=models.PROTECT, related_name="oturumlar",
        null=True, blank=True,
        help_text="Ozel danismanlik oturumu icin konu (oturum_tipi=OZEL_DANISMANLIK ise zorunlu)."
    )

    hassas_akis = models.BooleanField(default=False)
    qr_kodu = models.CharField(max_length=8, unique=True, db_index=True)
    cevaplar = models.JSONField(default=dict, blank=True)
    onerilen_etken_maddeler = models.JSONField(default=list, blank=True)
    tamamlandi = models.BooleanField(
        default=True,
        help_text=(
            "True = kullanici akisi tamamladi (QR uretildi). "
            "False = 10sn etkilesimsizlik ile terk edilmis (sahte/abandoned oturum)."
        ),
    )

    # Zaman damgasi ayırımı (kiosk vs sunucu saati)
    cihaz_zamani = models.DateTimeField(
        null=True, blank=True, db_index=True,
        help_text="Kiosk tarafindan bildirilen oturum zamani (cihaz saati).",
    )
    sunucu_zamani = models.DateTimeField(
        null=True, blank=True,
        help_text="Oturumun sunucuya ulastigi an (server clock). cihaz saati yanlis oldugunda referans alinir.",
    )

    # Eczaci danisma tamamlama akisi
    danisma_tamamlandi = models.BooleanField(default=False, db_index=True)
    danisma_tamamlanma_tarihi = models.DateTimeField(null=True, blank=True)
    danisma_notu = models.TextField(blank=True)
    danisma_tamamlayan_eczaci = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tamamlanan_danismalar",
    )

    class Meta:
        db_table = "oturum_loglari"
        ordering = ("-olusturulma_tarihi",)
        indexes = [
            models.Index(fields=["olusturulma_tarihi", "kiosk"]),
            models.Index(fields=["durum", "olusturulma_tarihi"]),
            models.Index(fields=["kiosk", "durum"]),
            models.Index(fields=["cihaz_zamani"]),
        ]
        verbose_name = "Oturum Logu"
        verbose_name_plural = "Oturum Loglari"


class OturumCevap(BaseModel):
    """Bir oturum sirasinda verilen cevaplar (normalize edilmis).

    JSON'dan ayrilan veriler: oturum -> soru -> cevap iliski tablosu.
    Snapshot alanlar: soru/cevap silindiginde bile oturum detaylari okunabilir.
    """

    oturum = models.ForeignKey(
        OturumLogu, on_delete=models.CASCADE, related_name="cevap_detaylari"
    )
    soru = models.ForeignKey(
        "products.Soru", on_delete=models.PROTECT, related_name="oturum_cevaplari",
        null=True, blank=True,
        help_text="Soru referansi (silindiginde null). Snapshot alanlar korunur."
    )
    cevap = models.ForeignKey(
        "products.Cevap", on_delete=models.PROTECT, related_name="oturum_secilimleri",
        null=True, blank=True,
        help_text="Cevap referansi (silindiginde null). Snapshot alanlar korunur."
    )

    # Snapshot: soru/cevap silinse bile okunabilir
    soru_metni_snapshot = models.CharField(max_length=500, blank=True)
    cevap_metni_snapshot = models.CharField(max_length=500, blank=True)
    cevap_degeri_snapshot = models.CharField(
        max_length=100, blank=True,
        help_text="Eski format uyumlu (Y/N/diger)."
    )

    class Meta:
        db_table = "oturum_cevaplar"
        unique_together = (("oturum", "soru"),)
        ordering = ("oturum_id", "id")
        verbose_name = "Oturum Cevap"
        verbose_name_plural = "Oturum Cevaplar"


class OturumOnerilenEtkenMadde(BaseModel):
    """Bir oturumda onerilen etken maddeler (normalize edilmis).

    JSON listesinden ayrilan veriler: oturum -> etken_madde iliski tablosu.
    """

    oturum = models.ForeignKey(
        OturumLogu, on_delete=models.CASCADE, related_name="onerilen_etken_madde_detaylari"
    )
    etken_madde = models.ForeignKey(
        "products.EtkenMadde", on_delete=models.PROTECT, related_name="oneri_kayitlari",
        null=True, blank=True,
        help_text="Etken madde referansi (silindiginde null). Snapshot korunur."
    )

    # Snapshot
    etken_madde_adi_snapshot = models.CharField(max_length=250, blank=True)

    class Meta:
        db_table = "oturum_onerilen_etken_maddeler"
        unique_together = (("oturum", "etken_madde"),)
        ordering = ("oturum_id", "id")
        verbose_name = "Oturum Onerilen Etken Madde"
        verbose_name_plural = "Oturum Onerilen Etken Maddeler"


# ─────────────────────────────────────────────────────────────────────────────
# Faz 4 — KioskEvent: kiosk teknik olayları (hata / bağlantı / sync)
# ─────────────────────────────────────────────────────────────────────────────

class KioskEvent(BaseModel):
    """Kiosktaki teknik olayların kalıcı kaydı (Faz 4).

    Playlist dağıtımı veya oturum logları değil; hata, bağlantı kesilmesi,
    restart, senkronizasyon hatası gibi operasyonel olaylar için.
    İdempotency: event_id (kiosk üretir, UUID) — aynı olay tekrar gönderilse
    mükerrer kayıt oluşmaz.
    """

    class EventType(models.TextChoices):
        CONNECTION_LOST = "CONNECTION_LOST", "Baglanti Kesildi"
        CONNECTION_RESTORED = "CONNECTION_RESTORED", "Baglanti Yenilendi"
        SYNC_FAILED = "SYNC_FAILED", "Senkronizasyon Hatasi"
        PLAYBACK_ERROR = "PLAYBACK_ERROR", "Oynatma Hatasi"
        APP_RESTART = "APP_RESTART", "Uygulama Yeniden Basladi"
        OUTBOX_PRESSURE = "OUTBOX_PRESSURE", "Outbox Doluluk Uyarisi"
        GENERAL_ERROR = "GENERAL_ERROR", "Genel Hata"

    class Severity(models.TextChoices):
        INFO = "INFO", "Bilgi"
        WARNING = "WARNING", "Uyari"
        ERROR = "ERROR", "Hata"
        CRITICAL = "CRITICAL", "Kritik"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kiosk = models.ForeignKey(
        "pharmacies.Kiosk", on_delete=models.CASCADE, related_name="kiosk_events"
    )
    event_id = models.UUIDField(
        unique=True, db_index=True,
        help_text="Kiosk tarafindan uretilen idempotency anahtari.",
    )
    event_type = models.CharField(
        max_length=32, choices=EventType.choices,
        default=EventType.GENERAL_ERROR, db_index=True,
    )
    severity = models.CharField(
        max_length=16, choices=Severity.choices,
        default=Severity.WARNING, db_index=True,
    )
    message = models.CharField(max_length=512, blank=True, default="")
    occurred_at = models.DateTimeField(
        null=True, blank=True, db_index=True,
        help_text="Kiosk cihaz zamani.",
    )
    received_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Sunucu zamani.",
    )

    class Meta:
        db_table = "kiosk_events"
        ordering = ("-olusturulma_tarihi",)
        verbose_name = "Kiosk Event"
        verbose_name_plural = "Kiosk Events"
        indexes = [
            models.Index(fields=["kiosk", "event_type", "olusturulma_tarihi"]),
            models.Index(fields=["severity", "olusturulma_tarihi"]),
        ]

    def __str__(self) -> str:
        return f"[{self.kiosk_id}] {self.event_type} ({self.severity})"
