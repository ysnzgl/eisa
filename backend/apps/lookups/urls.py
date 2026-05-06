"""Lookup URL yönlendirmeleri."""
from django.urls import path

from .views import CinsiyetlerView, IlcelerView, IllerView, YasAraliklariView

urlpatterns = [
    path("iller/", IllerView.as_view(), name="iller"),
    path("ilceler/", IlcelerView.as_view(), name="ilceler"),
    path("cinsiyetler/", CinsiyetlerView.as_view(), name="cinsiyetler"),
    path("yas-araliklari/", YasAraliklariView.as_view(), name="yas-araliklari"),
]
