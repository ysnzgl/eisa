"""Kullanici modeli — Panel girisi (SuperAdmin / Eczaci) JWT tasiyicisi."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Kullanici(AbstractUser):
    """Panel kullanicisi. AbstractUser tabanli oldugu icin BaseModel'den TUREMEZ."""

    class Rol(models.TextChoices):
        SUPERADMIN = "superadmin", "Super Admin"
        ECZACI = "pharmacist", "Eczaci"

    rol = models.CharField(max_length=16, choices=Rol.choices, default=Rol.ECZACI)
    eczane = models.ForeignKey(
        "pharmacies.Eczane",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="kullanicilar",
    )

    class Meta:
        db_table = "kullanicilar"
        verbose_name = "Kullanici"
        verbose_name_plural = "Kullanicilar"

    def __str__(self) -> str:  # pragma: no cover
        return self.username
