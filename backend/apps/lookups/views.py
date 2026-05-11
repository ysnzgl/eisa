"""Lookup (sabit veri) API görünümleri — İl, İlçe, Cinsiyet, Yaş Aralığı listeleme."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from .models import Cinsiyet, Il, Ilce, YasAraligi


class IllerView(APIView):
    """GET /api/lookups/iller/ — İlleri döner.

    ?has_pharmacies=true  →  yalnızca en az bir eczanesi olan iller.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Il.objects
        if request.query_params.get("has_pharmacies"):
            qs = qs.filter(eczaneler__isnull=False).distinct()
        return Response(list(qs.values("id", "ad").order_by("ad")))


class IlcelerView(APIView):
    """GET /api/lookups/ilceler/?il={id} — İle bağlı ilçeleri döner.

    ?has_pharmacies=true  →  yalnızca en az bir eczanesi olan ilçeler.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        il_id = request.query_params.get("il")
        if not il_id:
            return Response([])
        qs = Ilce.objects.filter(il_id=il_id)
        if request.query_params.get("has_pharmacies"):
            qs = qs.filter(eczaneler__isnull=False).distinct()
        return Response(list(qs.values("id", "ad", "il_id").order_by("ad")))


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
