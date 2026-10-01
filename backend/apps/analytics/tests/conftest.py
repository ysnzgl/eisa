"""Analytics testleri için ortak fixture'lar.

Panel kısıtı (sözleşme/ödeme durumu) analytics kapsamının dışındadır; bu testler
eczane-izolasyonu ve oturum davranışını doğrular. Kısıt kontrolü abonelik
testlerinde ayrıca doğrulanır, burada bypass edilir.
"""
import pytest


@pytest.fixture(autouse=True)
def _bypass_panel_kisit(monkeypatch):
    monkeypatch.setattr(
        "apps.abonelik.services.panel_kisitli",
        lambda eczane_id: (False, ""),
    )
