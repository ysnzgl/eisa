"""
Hafif iş-mantığı denetim (audit) logları.

PostgreSQL'de tutulur; ağır log altyapılarına (ElasticSearch vb.) gerek bırakmaz.
Sadece kritik olaylar yazılır:
  - Süper Admin CRUD işlemleri (eczane, kiosk, ürün, kampanya vb.)
  - Kiosk online/offline durum değişiklikleri ve heartbeat olayları
Sistem/exception logları buraya YAZILMAZ; onlar dosya tabanlı JSON loglara gider.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Denetlenebilir iş-mantığı olayları."""

    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        LOGIN = "login", "Login"
        LOGIN_FAILED = "login_failed", "Login Failed"
        KIOSK_ONLINE = "kiosk_online", "Kiosk Online"
        KIOSK_OFFLINE = "kiosk_offline", "Kiosk Offline"
        KIOSK_HEARTBEAT = "kiosk_heartbeat", "Kiosk Heartbeat"
        REGENERATE_KEY = "regenerate_key", "Regenerate App Key"
        OTHER = "other", "Other"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="İşlemi yapan kullanıcı (panel kullanıcısı). Kiosk olayları için NULL olabilir.",
    )
    actor_repr = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Kullanıcı silinse bile okunabilirlik için aktör temsili.",
    )
    action = models.CharField(max_length=32, choices=Action.choices)
    target_type = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Hedef model adı (örn. Pharmacy, Kiosk, Campaign).",
    )
    target_id = models.CharField(max_length=64, blank=True, default="")
    summary = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)

    # Kiosk olayları için kullanışlı bağlam
    kiosk_mac = models.CharField(max_length=17, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["kiosk_mac", "created_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.actor_repr or '-'} {self.action} {self.target_type}#{self.target_id}"


def record(
    *,
    action: str,
    actor=None,
    target=None,
    target_type: str = "",
    target_id: str = "",
    summary: str = "",
    metadata: dict | None = None,
    kiosk_mac: str = "",
    ip_address: str | None = None,
) -> AuditLog:
    """Tek satırda audit kaydı yaratan yardımcı.

    `target` verilirse `target_type` ve `target_id` otomatik doldurulur.
    """
    if target is not None and not target_type:
        target_type = target.__class__.__name__
        target_id = str(getattr(target, "pk", "") or "")

    return AuditLog.objects.create(
        actor=actor if getattr(actor, "pk", None) else None,
        actor_repr=str(actor) if actor is not None else "",
        action=action,
        target_type=target_type or "",
        target_id=str(target_id or ""),
        summary=summary[:255],
        metadata=metadata or {},
        kiosk_mac=kiosk_mac or "",
        ip_address=ip_address,
    )
