"""Custom User modeli — paneller (SuperAdmin, Eczacı) için JWT taşıyıcı."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPERADMIN = "superadmin", "Süper Admin"
        PHARMACIST = "pharmacist", "Eczacı"

    role = models.CharField(max_length=16, choices=Role.choices, default=Role.PHARMACIST)
    pharmacy = models.ForeignKey(
        "pharmacies.Pharmacy",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )

    class Meta:
        db_table = "users"
