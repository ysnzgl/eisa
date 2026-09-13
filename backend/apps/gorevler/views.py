"""Sadece süper adminler için iş takip API'si."""
from django.db.models import Q
from rest_framework import viewsets

from apps.pharmacies.permissions import IsSuperAdmin

from .models import Gorev
from .serializers import GorevSerializer


class GorevViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class = GorevSerializer
    queryset = Gorev.objects.select_related("atanan_kullanici", "olusturan").order_by("-olusturulma_tarihi")
    http_method_names = ["get", "post", "patch", "put", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        if durum := params.get("durum"):
            qs = qs.filter(durum=durum)

        if atanan_kullanici_id := params.get("atanan_kullanici_id"):
            qs = qs.filter(atanan_kullanici_id=atanan_kullanici_id)

        if q := params.get("q"):
            q = q.strip()
            if q:
                qs = qs.filter(Q(baslik__icontains=q) | Q(icerik__icontains=q))

        return qs
