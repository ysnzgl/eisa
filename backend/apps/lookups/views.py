"""Lookup (sabit veri) API görünümleri — İl, İlçe, Cinsiyet, Yaş Aralığı listeleme."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from .models import Cinsiyet, Il, Ilce, YasAraligi


class IllerView(APIView):
    """GET /api/lookups/iller/ — Tüm illeri döner."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Il.objects.values("id", "ad", "plaka").order_by("ad")
        return Response(list(qs))


class IlcelerView(APIView):
    """GET /api/lookups/ilceler/?il={id} — İle bağlı ilçeleri döner."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        il_id = request.query_params.get("il")
        if not il_id:
            return Response([])
        qs = Ilce.objects.filter(il_id=il_id).values("id", "ad", "il_id").order_by("ad")
        return Response(list(qs))


class CinsiyetlerView(APIView):
    """GET /api/lookups/cinsiyetler/ — Cinsiyet listesi döner."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Cinsiyet.objects.values("id", "kod", "ad").order_by("ad")
        return Response(list(qs))


class YasAraliklariView(APIView):
    """GET /api/lookups/yas-araliklari/ — Yaş aralıklarını döner."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = YasAraligi.objects.values("id", "kod", "ad", "alt_sinir", "ust_sinir").order_by("alt_sinir")
        return Response(list(qs))
