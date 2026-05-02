"""Şikayet kategorileri, sorular ve etken madde önerileri."""
from django.db import models


class Category(models.Model):
    """Şikayet kategorisi (Uyku, Enerji, Bağışıklık vb.) veya 'Hassas Durum'."""

    name = models.CharField(max_length=128, unique=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=64, default="fa-circle")
    is_sensitive = models.BooleanField(
        default=False, help_text="Sessiz triyaj akışı (Akış B) için işaretle."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "categories"


class Question(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="questions")
    seed_id = models.CharField(max_length=32, unique=True, null=True, blank=True)
    text = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)
    match_rules = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "questions"
        ordering = ["order"]


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    text = models.CharField(max_length=255)
    weight = models.IntegerField(default=0)

    class Meta:
        db_table = "answers"


class ActiveIngredient(models.Model):
    """Etken madde (Magnezyum, B12 vb.). Marka önerisi YASAKTIR."""

    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "active_ingredients"
