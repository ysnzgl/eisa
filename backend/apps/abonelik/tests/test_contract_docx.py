import datetime as dt
import io
import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

import pytest

from apps.abonelik import contract_docx
from apps.abonelik.models import CihazOdemePlani, Sozlesme


W = contract_docx.W
NS = {"w": W}


def _table(row_shapes):
    rows = []
    for column_count in row_shapes:
        cells = "".join(f'<w:tc><w:p><w:r><w:t>slot-{i}</w:t></w:r></w:p></w:tc>' for i in range(column_count))
        rows.append(f"<w:tr>{cells}</w:tr>")
    return f"<w:tbl>{''.join(rows)}</w:tbl>"


def _template(tmp_path: Path, kind: str) -> Path:
    shapes = (
        [[2] * 5, [4, 4], [2], [2] * 5, [2] * 5, [2], [4, 4], [2, 2], [2], [1, 1]]
        if kind == "EK1" else
        [[2] * 5, [2, 2], [5, 5, 5, 5], [3, 3], [3, 3], [1], [2, 2]]
    )
    xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W}"><w:body>'
        + "".join(_table(table) for table in shapes)
        + "<w:sectPr/></w:body></w:document>"
    )
    path = tmp_path / f"{kind}.docx"
    with ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", xml)
        archive.writestr("word/styles.xml", "PRESERVE")
    return path


@pytest.fixture
def standard_contract(db, eczane):
    eczane.adres = "Test Cad. 1 Kadıköy"
    eczane.sahip_adi = "Ecz. Ayşe Test"
    eczane.telefon = "05000000000"
    eczane.save()
    contract = Sozlesme.objects.create(
        eczane=eczane, sozlesme_tipi_ay=24, baslangic_tarihi=dt.date(2026, 11, 8),
        aylik_kullanim_bedeli=Decimal("3900"), kdv_orani=20, oteleme_ay=2,
        bolge_snapshot={"ad": "Kayseri Bölgesi", "il": "Kayseri", "ilce": "Melikgazi"},
        sponsorluk_tarifeleri_snapshot=[{
            "ad": "Bölge 6-15", "min_cihaz": 6, "max_cihaz": 15,
            "brut_bedel": "36000", "kdv_orani": 20,
        }],
    )
    CihazOdemePlani.objects.create(
        sozlesme=contract, tip=CihazOdemePlani.Tip.TAHSIS, adet=2,
        cihaz_bilgisi='21.5" FHD kiosk', baslangic_tarihi=contract.baslangic_tarihi,
    )
    return contract


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["EK1", "EK2"])
def test_word_sablonu_doldurulur_ve_diger_paket_parcalari_korunur(
    tmp_path, monkeypatch, standard_contract, kind,
):
    template = _template(tmp_path, kind)
    monkeypatch.setattr(contract_docx, "_template_path", lambda _kind: template)

    content, missing = contract_docx.generate_contract_docx(standard_contract, kind)

    with ZipFile(io.BytesIO(content)) as output:
        assert output.read("word/styles.xml") == b"PRESERVE"
        root = ET.fromstring(output.read("word/document.xml"))
    if kind == "EK2":
        with ZipFile(template) as original:
            source_root = ET.fromstring(original.read("word/document.xml"))
        for index in (3, 4, 5):
            assert ET.tostring(root.findall(".//w:tbl", NS)[index]) == ET.tostring(source_root.findall(".//w:tbl", NS)[index])
    text = " ".join(node.text or "" for node in root.findall(".//w:t", NS))
    assert "Test Eczanesi" in text
    assert '21.5" FHD kiosk' in text
    assert "Tahsis" in text
    if kind == "EK1":
        assert "Kayseri Bölgesi" in text
        assert "36.000,00 TL" in text
    else:
        device_table = root.findall(".//w:tbl", NS)[2]
        assert len(device_table.findall("./w:tr", NS)) == 3  # başlık + iki cihaz
        assert "Cihaz seri numaraları" in missing
        assert "#" not in text


def test_ignorable_namespace_declaration_survives_serialization():
    xml = (f'<w:document xmlns:w="{W}" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
           'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" mc:Ignorable="w14">'
           '<w:body/></w:document>').encode()
    result = contract_docx._serialize_document(contract_docx._parse_document(xml), xml)
    declarations = dict(value for event, value in ET.iterparse(io.BytesIO(result), events=("start-ns",)))
    assert declarations["w14"] == "http://schemas.microsoft.com/office/word/2010/wordml"
