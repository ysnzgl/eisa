from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.uow import UnitOfWork
from apps.pharmacies.permissions import IsSuperAdmin

from .models import BankaHesabi, SirketProfili
from .serializers import BankaHesabiSerializer, SirketProfiliSerializer


def get_company():
    company = SirketProfili.objects.prefetch_related("banka_hesaplari").first()
    if company:
        return company
    company = SirketProfili(
        ticari_unvan="e-İSA Yazılım A.Ş.", marka_adi="e-İSA",
        vergi_dairesi="", vergi_numarasi="0000000000", adres="Kayseri / Türkiye",
    )
    with UnitOfWork() as uow:
        uow.add(company)
    return company


class SirketProfiliView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        return Response(SirketProfiliSerializer(get_company()).data)

    def put(self, request):
        serializer = SirketProfiliSerializer(
            get_company(), data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request):
        serializer = SirketProfiliSerializer(
            get_company(), data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class BankaHesabiViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class = BankaHesabiSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return BankaHesabi.objects.filter(sirket=get_company())

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["sirket"] = get_company()
        return context

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        with UnitOfWork(user=request.user) as uow:
            uow.delete(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

