"""Kiosk API facade — serializer yeniden ihraclari.

Facade kendi serializer'ini TANIMLAMAZ; domain app'lerindeki mevcut
serializer'lari yeniden kullanir. Bu modul yalniz tek-nokta import kolayligi
saglar.
"""
from apps.analytics.serializers import OturumLoguItemSerializer
from apps.campaigns.serializers import (
    KioskCreativeSyncSerializer,
    KioskHouseAdSyncSerializer,
    KioskPlaylistSerializer,
    ProofOfPlayBulkSerializer,
)
from apps.products.serializers import (
    DanismaSyncSerializer,
    EtkenMaddeSerializer,
    KategoriSyncSerializer,
)

__all__ = [
    "OturumLoguItemSerializer",
    "KioskCreativeSyncSerializer",
    "KioskHouseAdSyncSerializer",
    "KioskPlaylistSerializer",
    "ProofOfPlayBulkSerializer",
    "DanismaSyncSerializer",
    "EtkenMaddeSerializer",
    "KategoriSyncSerializer",
]
