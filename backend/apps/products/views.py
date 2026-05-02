"""
Ürün yönetim görünümleri.
Kiosk: /sync/ endpoint'i (JWT veya App-Key).
Admin: Kategori, Soru, Cevap, Etken Madde CRUD (sadece süper admin).
"""
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.pharmacies.auth import KioskAppKeyAuthentication
from apps.pharmacies.permissions import IsKioskOrAuthenticated, IsSuperAdmin

from .models import ActiveIngredient, Answer, Category, Question
from .serializers import (
    ActiveIngredientSerializer,
    AnswerWriteSerializer,
    CategorySerializer,
    CategorySyncSerializer,
    QuestionSerializer,
)


class ProductSyncView(APIView):
    """
    GET /api/products/sync/
    Kiosk'un yerel SQLite veritabanını güncellemesi için tüm aktif kategorileri
    (iç içe sorular ve cevaplarla) ve tüm etken maddeleri döner.
    JWT veya App-Key ile erişilebilir.
    """

    authentication_classes = [JWTAuthentication, KioskAppKeyAuthentication]
    permission_classes = [IsKioskOrAuthenticated]

    def get(self, request):
        # Sadece aktif kategorileri ve onların sorularını/cevaplarını getir
        categories = Category.objects.filter(is_active=True).prefetch_related(
            "questions__answers"
        )
        ingredients = ActiveIngredient.objects.all().order_by("name")
        return Response(
            {
                "categories": CategorySyncSerializer(categories, many=True).data,
                "ingredients": ActiveIngredientSerializer(ingredients, many=True).data,
            }
        )


class CategoryViewSet(viewsets.ModelViewSet):
    """Kategori CRUD — sadece süper admin erişebilir."""

    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]


class QuestionViewSet(viewsets.ModelViewSet):
    """
    Soru CRUD — sadece süper admin erişebilir.
    Liste yanıtı iç içe cevapları içerir (salt okunur).
    """

    queryset = Question.objects.select_related("category").prefetch_related("answers").all()
    serializer_class = QuestionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]


class AnswerViewSet(viewsets.ModelViewSet):
    """
    Cevap CRUD — sadece süper admin erişebilir.
    Sorulara bağlı cevapları yönetmek için kullanılır.
    """

    queryset = Answer.objects.select_related("question").all()
    serializer_class = AnswerWriteSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]


class ActiveIngredientViewSet(viewsets.ModelViewSet):
    """Etken madde CRUD — sadece süper admin erişebilir."""

    queryset = ActiveIngredient.objects.all().order_by("name")
    serializer_class = ActiveIngredientSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]
