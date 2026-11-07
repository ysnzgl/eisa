"""Sadece süper adminler için iş takip API'si."""
import logging
from pathlib import Path

from django.db.models import Q
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils.http import content_disposition_header
from minio.error import S3Error
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from apps.core.services.storage_service import StorageService
from apps.core.uow import UnitOfWork
from apps.pharmacies.permissions import IsSuperAdmin

from .models import Gorev, GorevDosya
from .serializers import GorevSerializer, GorevDosyaSerializer
from .documents import validate_document, docx_paragraphs

logger = logging.getLogger(__name__)


class GorevViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class = GorevSerializer
    queryset = Gorev.objects.select_related("atanan_kullanici", "olusturan").prefetch_related("dosyalar").order_by("-olusturulma_tarihi")
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]

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

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser])
    def dosyalar(self, request, pk=None):
        gorev = self.get_object()
        uploaded = request.FILES.get("dosya")
        content_type = validate_document(uploaded)
        try:
            storage = StorageService()
            key = storage.upload_file(uploaded, prefix=f"is-takip/{gorev.pk}")
        except Exception:
            logger.exception("İş dosyası yüklenemedi")
            return Response({"detail": "Dosya depolama servisine yüklenemedi."}, status=503)
        try:
            with UnitOfWork(user=request.user) as uow:
                dosya = uow.add(GorevDosya(
                    gorev=gorev, ad=Path(uploaded.name).name, object_key=key,
                    content_type=content_type, boyut=uploaded.size,
                ))
        except Exception:
            try:
                storage.delete_object(key)
            except Exception:
                logger.exception("Kaydedilemeyen iş dosyası temizlenemedi")
            raise
        return Response(GorevDosyaSerializer(dosya).data, status=201)

    @action(detail=True, methods=["get"], url_path=r"dosyalar/(?P<dosya_id>\d+)")
    def dosya(self, request, pk=None, dosya_id=None):
        dosya = get_object_or_404(self.get_object().dosyalar, pk=dosya_id)
        try:
            storage = StorageService()
            if request.query_params.get("onizleme") == "metin":
                if not dosya.ad.lower().endswith(".docx"):
                    return Response({"detail": "Metin önizlemesi yalnız DOCX için desteklenir."}, status=400)
                response = Response({"paragraflar": docx_paragraphs(storage.read_object(dosya.object_key))})
                response["Cache-Control"] = "private, no-store"
                return response
            source = storage.client.get_object(storage.bucket_name, dosya.object_key)
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject"}:
                return Response({"detail": "Dosya depolamada bulunamadı."}, status=404)
            logger.exception("İş dosyası okunamadı")
            return Response({"detail": "Dosya depolama servisine ulaşılamadı."}, status=503)
        except APIException:
            raise
        except Exception:
            logger.exception("İş dosyası okunamadı")
            return Response({"detail": "Dosya depolama servisine ulaşılamadı."}, status=503)

        def chunks():
            try:
                yield from source.stream(amt=65536)
            finally:
                source.close()
                source.release_conn()

        response = StreamingHttpResponse(chunks(), content_type=dosya.content_type)
        response["Content-Length"] = str(dosya.boyut)
        response["Content-Disposition"] = content_disposition_header(
            request.query_params.get("indir") == "1" or dosya.content_type != "application/pdf", dosya.ad,
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        with UnitOfWork(user=request.user) as uow:
            uow.delete(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
