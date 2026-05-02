"""
Ürün/kategori serileştiricileri — admin panel CRUD ve kiosk senkronizasyonu için.
"""
from rest_framework import serializers

from .models import ActiveIngredient, Answer, Category, Question


class AnswerSerializer(serializers.ModelSerializer):
    """Soru cevabı — kiosk sync ve admin panel için."""

    class Meta:
        model = Answer
        fields = ["id", "text", "weight"]


class QuestionSerializer(serializers.ModelSerializer):
    """
    Soru serileştiricisi.
    Admin CRUD'da answers salt okunur olarak listelenir.
    """

    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "category", "text", "order", "answers"]


class AnswerWriteSerializer(serializers.ModelSerializer):
    """Cevap oluşturma/güncelleme için serileştirici."""

    class Meta:
        model = Answer
        fields = ["id", "question", "text", "weight"]


class CategorySerializer(serializers.ModelSerializer):
    """Admin panel için düz kategori serileştiricisi (soru detayı olmadan)."""

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "is_sensitive", "is_active"]


class QuestionWithAnswersSerializer(serializers.ModelSerializer):
    """Kiosk senkronizasyonu için iç içe (nested) cevapları olan soru."""

    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "text", "order", "answers"]


class CategorySyncSerializer(serializers.ModelSerializer):
    """
    Kiosk senkronizasyonu için iç içe sorular ve cevapları olan kategori.
    Sadece aktif kategoriler gönderilir.
    """

    questions = QuestionWithAnswersSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "is_sensitive", "questions"]


class ActiveIngredientSerializer(serializers.ModelSerializer):
    """Etken madde CRUD ve kiosk sync için serileştirici."""

    class Meta:
        model = ActiveIngredient
        fields = ["id", "name", "description"]
