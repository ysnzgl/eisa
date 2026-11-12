"""Generate browser fixtures with the real contract renderer and synthetic records.

Run from the repository root with .venv/Scripts/python.exe on Windows.
No connection is made to the development database and no real account is used.
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.environ["DJANGO_SETTINGS_MODULE"] = "core_api.test_settings"

import django

django.setup()

from apps.abonelik.contract_docx import contract_preview_html
from apps.abonelik.models import CihazOdemePlani

class RelatedRows(list):
    def all(self):
        return self

    def exclude(self, **kwargs):
        return RelatedRows(row for row in self if not all(getattr(row, key) == value for key, value in kwargs.items()))

    def order_by(self, field):
        return RelatedRows(sorted(self, key=lambda row: getattr(row, field)))


pharmacy = SimpleNamespace(ad="Merkez Eczanesi",
    sahip_adi="Ecz. Test", telefon="05000000000", adres="Örnek Cad. No: 1, Melikgazi / Kayseri")
contract = SimpleNamespace(pk=1, eczane=pharmacy, sozlesme_tipi_ay=24,
    sozlesme_surumu="2026-EK1", gercek_imza_tarihi=None, oteleme_ay=0,
    kullanim_bedeli_baslangic=dt.date(2026, 11, 8),
    baslangic_tarihi=dt.date(2026, 11, 8), aylik_kullanim_bedeli="3900", kdv_orani=20,
    bolge_snapshot={"ad": "Kayseri Merkez", "il": "Kayseri", "ilce": "Melikgazi"},
    sponsorluk_tarifeleri_snapshot=[{"ad": "Bölge Sponsorluğu – 6 ila 15 Cihaz",
        "min_cihaz": 6, "max_cihaz": 15, "brut_bedel": "36000", "kdv_orani": 20}])
device = SimpleNamespace(seri_no="EISA-SN-2026-001", marka="e-isa", model="K21",
    ekran_boyutu="21,5 inç FHD", garanti_ay=24, eczane=pharmacy)
plan = SimpleNamespace(id=1, tip="TAHSIS", Tip=CihazOdemePlani.Tip, adet=1, durum="AKTIF",
    cihaz_bilgisi="e-isa K21", baslangic_tarihi=contract.baslangic_tarihi, tahsis_bedeli=None,
    oteleme_ay=0, taksit_sayisi=1, cihazlar=RelatedRows([device]))
contract.cihaz_planlari = RelatedRows([plan])
fixtures = {}
with patch("apps.sirket.models.BankaHesabi.objects.filter") as accounts:
    accounts.return_value.exists.return_value = False
    accounts.return_value.order_by.return_value.first.return_value = None
    for kind in ("EK1", "EK2"):
        html, missing = contract_preview_html(contract, kind)
        fixtures[kind] = {"belge_seti": "EK1_EK2", "belge_turu": kind,
            "eksik_alanlar": missing, "html": html}
target = BACKEND.parent / "web_panels/tests/visual/fixtures/contracts.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(fixtures, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Generated full Ek-1/Ek-2 previews: {target}")
