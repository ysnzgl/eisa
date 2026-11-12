"""Onaylı Word şablonlarından Ek-1 ve Ek-2 üretimi.

Yalnız ``word/document.xml`` içindeki değişken tablo hücreleri değiştirilir;
sabit maddeler ve paketin diğer parçaları aynen korunur.
"""
from __future__ import annotations

import copy
import io
import html
import os
import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from django.conf import settings


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


class ContractTemplateError(RuntimeError):
    pass


def _template_path(kind: str) -> Path:
    name = "e-isa_Eczane_Sozlesmesi_Ek1_Son.docx" if kind == "EK1" else "e-isa_Zimmet_Tutanagi_Ek2.docx"
    env_name = f"EISA_CONTRACT_{kind}_TEMPLATE"
    candidates = [
        os.getenv(env_name),
        str(Path(settings.BASE_DIR) / "contract_templates" / name),
        str(Path.home() / "Downloads" / name),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise ContractTemplateError(
        f"{kind} Word şablonu bulunamadı. {env_name} ortam değişkenini tanımlayın."
    )


def _fmt_date(value) -> str:
    return value.strftime("%d.%m.%Y") if value else ""


def _fmt_money(value) -> str:
    amount = Decimal(str(value or 0))
    return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " TL"


def _parse_document(xml_bytes: bytes):
    # Prefixleri korumak, mc:Ignorable gibi prefix değerlerini geçersiz kılmamak için
    # kaynak belgedeki tüm namespace tanımlarını yeniden kaydederiz.
    for _event, item in ET.iterparse(io.BytesIO(xml_bytes), events=("start-ns",)):
        prefix, uri = item
        try:
            ET.register_namespace(prefix, uri)
        except ValueError:
            pass
    return ET.fromstring(xml_bytes)


def _serialize_document(root, source_xml: bytes) -> bytes:
    """mc:Ignorable gibi öznitelik değerlerinde kullanılan ad alanlarını da korur."""
    serialized = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    root_start = serialized.index(b"<", serialized.index(b"?>") + 2)
    root_end = serialized.index(b">", root_start)
    opening = serialized[root_start:root_end]
    declarations = []
    namespaces = {}
    for event, value in ET.iterparse(io.BytesIO(source_xml), events=("start-ns", "start")):
        if event == "start":
            break
        namespaces[value[0]] = value[1]
    from xml.sax.saxutils import quoteattr
    for prefix, uri in namespaces.items():
        name = f"xmlns:{prefix}" if prefix else "xmlns"
        if (name + "=").encode() not in opening:
            declarations.append(f" {name}={quoteattr(uri)}".encode())
    return serialized[:root_end] + b"".join(declarations) + serialized[root_end:]


def _cells(row):
    return row.findall("./w:tc", NS)


def _set_cell(cell, value: object) -> None:
    texts = cell.findall(".//w:t", NS)
    text = str(value if value is not None else "")
    if texts:
        texts[0].text = text
        if text.startswith(" ") or text.endswith(" "):
            texts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        for node in texts[1:]:
            node.text = ""
        return
    paragraph = cell.find("./w:p", NS)
    if paragraph is None:
        paragraph = ET.SubElement(cell, f"{{{W}}}p")
    run = ET.SubElement(paragraph, f"{{{W}}}r")
    ET.SubElement(run, f"{{{W}}}t").text = text


def _replace_data_rows(table, rows: list[list[str]]) -> None:
    table_rows = table.findall("./w:tr", NS)
    if len(table_rows) < 2:
        raise ContractTemplateError("Word şablonundaki dinamik tabloda örnek veri satırı yok.")
    prototype = table_rows[1]
    for old in table_rows[1:]:
        table.remove(old)
    for values in rows:
        row = copy.deepcopy(prototype)
        cells = _cells(row)
        for index, value in enumerate(values):
            if index < len(cells):
                _set_cell(cells[index], value)
        table.append(row)


def _plan_label(plan) -> str:
    if plan.tip in (plan.Tip.TAHSIS, plan.Tip.KIRALIK):
        return "Tahsis"
    if plan.taksit_sayisi <= 1:
        return "Peşin satış"
    return f"{plan.taksit_sayisi} ay vadeli satış / {plan.taksit_sayisi} taksit"


def _device_rows(sozlesme):
    plans = list(sozlesme.cihaz_planlari.exclude(durum="IPTAL").order_by("id"))
    rows = []
    for plan in plans:
        model = plan.cihaz_bilgisi or "[CİHAZ MODELİ GİRİLMELİ]"
        physical = list(plan.cihazlar.order_by("seri_no"))
        for device in physical:
            label = " ".join(filter(None, (device.marka, device.model, device.ekran_boyutu)))
            rows.append((label, device.seri_no, _plan_label(plan), plan))
        for _ in range(max(0, plan.adet - len(physical))):
            rows.append((model, "[SERİ NO GİRİLMELİ]", _plan_label(plan), plan))
    return rows


def missing_fields(sozlesme, kind: str) -> list[str]:
    missing = []
    if not sozlesme.gercek_imza_tarihi:
        missing.append("Gerçek imza tarihi")
    pharmacy = sozlesme.eczane
    for value, label in (
        (pharmacy.adres, "Eczane tam adresi"),
        (pharmacy.sahip_adi, "Eczacı / teslim alan adı soyadı"),
        (pharmacy.telefon, "Eczane telefonu"),
    ):
        if not value:
            missing.append(label)
    devices = _device_rows(sozlesme)
    if not devices:
        missing.append("Cihaz ödeme/tahsis planı")
    if any("[CİHAZ MODELİ" in row[0] for row in devices):
        missing.append("Cihaz model bilgisi")
    if kind == "EK1":
        from apps.sirket.models import BankaHesabi
        if not BankaHesabi.objects.filter(aktif=True).exists():
            missing.append("Ödeme hesabı / IBAN")
        if not sozlesme.bolge_snapshot:
            missing.append("Eczanenin sözleşme bölgesi")
        if not sozlesme.sponsorluk_tarifeleri_snapshot:
            missing.append("Sözleşme tarihinde geçerli sponsorluk tarifeleri")
        physical = [device for plan in sozlesme.cihaz_planlari.exclude(durum="IPTAL") for device in plan.cihazlar.all()]
        if len(physical) != len(devices) or not physical or any(device.garanti_ay is None for device in physical):
            missing.append("Garanti süresi")
    if kind == "EK2":
        if any("[SERİ NO" in row[1] for row in devices):
            missing.append("Cihaz seri numaraları")
        missing.extend(["Teslim eden personel adı, görevi ve telefonu", "Teslim saati"])
    # Hukuki görüşme sonrasına bırakılan alanlar bilinçli olarak otomatik doldurulmaz.
    return list(dict.fromkeys(missing))


def _fill_ek1(root, sozlesme) -> None:
    tables = root.findall(".//w:tbl", NS)
    if len(tables) < 10:
        raise ContractTemplateError("Ek-1 şablon yapısı beklenen 10 tabloyu içermiyor.")
    pharmacy = sozlesme.eczane
    devices = _device_rows(sozlesme)
    plans = list(sozlesme.cihaz_planlari.exclude(durum="IPTAL").order_by("id"))

    # Seçim ve taksit tarihleri sabit 2/4 ay seçeneklerinden değil gerçek plandan gelir.
    for paragraph in root.findall("./w:body/w:p", NS):
        nodes = paragraph.findall(".//w:t", NS)
        text = "".join(node.text or "" for node in nodes)
        replacement = None
        if text.startswith("Seçilen model:"):
            replacement = "Seçilen model: " + "; ".join(dict.fromkeys(_plan_label(plan) for plan in plans))
        elif "Taksit takvimi bu bölüme eklenir:" in text:
            from .services import add_months
            schedules = []
            for plan in plans:
                if plan.tip == plan.Tip.SATILIK:
                    dates = ", ".join(_fmt_date(add_months(sozlesme.baslangic_tarihi, plan.oteleme_ay + month)) for month in range(max(1, plan.taksit_sayisi)))
                    schedules.append(f"{plan.cihaz_bilgisi or 'Cihaz'}: {dates}")
            replacement = text.split("Taksit takvimi bu bölüme eklenir:")[0] + "Taksit takvimi: " + ("; ".join(schedules) or "Tahsis; cihaz satış taksiti bulunmuyor.")
        if replacement is not None and nodes:
            nodes[0].text = replacement
            for node in nodes[1:]:
                node.text = ""

    summary = tables[0].findall("./w:tr", NS)
    _set_cell(_cells(summary[0])[1], f"{pharmacy.ad} / {pharmacy.sahip_adi or '[ECZACI ADI GİRİLMELİ]'}")
    _set_cell(_cells(summary[1])[1], f"{pharmacy.ad} - {pharmacy.adres or '[TAM ADRES GİRİLMELİ]'}")
    _set_cell(_cells(summary[2])[1], "; ".join(dict.fromkeys(row[0] for row in devices)) or "[CİHAZ MODELİ GİRİLMELİ]")
    serials = ", ".join(row[1] for row in devices)
    _set_cell(_cells(summary[3])[1], f"{len(devices)} adet / {serials or '[SERİ NO GİRİLMELİ]'}")
    _set_cell(_cells(summary[4])[1], f"{_fmt_date(sozlesme.baslangic_tarihi)} / {_fmt_date(sozlesme.baslangic_tarihi)}")

    header = _cells(tables[1].findall("./w:tr", NS)[0])
    for cell, value in zip(header, ("Cihaz modeli", "Adet", "Edinim modeli", "Bedel ve ödeme")):
        _set_cell(cell, value)
    plan_rows = []
    for plan in plans:
        if plan.tip == plan.Tip.SATILIK:
            payment = f"Toplam {_fmt_money(plan.toplam_tutar)}"
            if plan.taksit_sayisi > 1:
                payment += f" / {plan.taksit_sayisi} x {_fmt_money(plan.taksit_tutari)}"
        else:
            payment = "Tahsis" + (f" / {_fmt_money(plan.tahsis_bedeli)}" if plan.tahsis_bedeli else "")
        plan_rows.append([plan.cihaz_bilgisi or "[MODEL GİRİLMELİ]", str(plan.adet), _plan_label(plan), payment])
    _replace_data_rows(tables[1], plan_rows or [["[MODEL GİRİLMELİ]", "0", "Tahsis", ""]])

    price_rows = tables[2].findall("./w:tr", NS)
    _set_cell(_cells(price_rows[0])[1], f"{_fmt_money(sozlesme.aylik_kullanim_bedeli)} + KDV %{sozlesme.kdv_orani}")
    deferral_rows = tables[3].findall("./w:tr", NS)
    _set_cell(_cells(deferral_rows[0])[1], f"Aktivasyon Tarihi'nden itibaren {sozlesme.sozlesme_tipi_ay or 0} ay + {sozlesme.oteleme_ay} ay öteleme")
    _set_cell(_cells(deferral_rows[1])[1], "☒ Yok     ☐ Var" if not sozlesme.oteleme_ay else f"☐ Yok     ☒ Var: {sozlesme.oteleme_ay} ay")
    _set_cell(_cells(deferral_rows[3])[1], _fmt_date(sozlesme.kullanim_bedeli_baslangic))
    device_deferrals = sorted({p.oteleme_ay for p in plans})
    _set_cell(_cells(deferral_rows[4])[1], "Yalnızca aylık Kullanım Bedeli. Cihaz ötelemesi: " + (", ".join(f"{v} ay" for v in device_deferrals) or "cihaz planı yok"))

    from apps.sirket.models import BankaHesabi
    bank = BankaHesabi.objects.filter(aktif=True).order_by("-varsayilan", "sira", "id").first()
    payment_rows = tables[4].findall("./w:tr", NS)
    _set_cell(_cells(payment_rows[4])[1], f"{bank.banka_adi} / {bank.iban}" if bank else "[BANKA / IBAN GİRİLMELİ]")

    region = sozlesme.bolge_snapshot or {}
    region_rows = [[region.get("ad", "[BÖLGE TANIMLANMALI]"),
                    " / ".join(filter(None, (region.get("il"), region.get("ilce") or "Tüm ilçeler"))) if region else "[KAPSAM TANIMLANMALI]"]]
    # Bölge kaydı yalnız ad ve coğrafi kapsam taşır; cihaz/sponsor sınırı uydurulmaz.
    region_table = tables[6]
    for row in region_table.findall("./w:tr", NS):
        for cell in _cells(row)[2:]:
            row.remove(cell)
        for cell in _cells(row):
            width = cell.find("./w:tcPr/w:tcW", NS)
            if width is not None:
                width.set(f"{{{W}}}w", "4680")
    grid = region_table.find("./w:tblGrid", NS)
    if grid is not None:
        for column in list(grid)[2:]:
            grid.remove(column)
        for column in grid:
            column.set(f"{{{W}}}w", "4680")
    _replace_data_rows(tables[6], region_rows)

    tariffs = sozlesme.sponsorluk_tarifeleri_snapshot or []
    tariff_rows = []
    for tariff in tariffs:
        maximum = tariff.get("max_cihaz") or "∞"
        tariff_rows.append([tariff.get("ad", ""),
                            f"{tariff.get('min_cihaz', 1)}-{maximum} cihaz; {_fmt_money(tariff.get('brut_bedel'))} KDV dahil (%{tariff.get('kdv_orani', 0)})"])
    # Bu tablo başlıksızdır. Paket kapsamı, sponsor üst sınırı/teyit ve süre
    # hükümleri değişken fiyat satırlarıyla birlikte silinmemelidir.
    tariff_table = tables[7]
    original_rows = tariff_table.findall("./w:tr", NS)
    fixed_rows = [copy.deepcopy(row) for row in original_rows
                  if "".join(node.text or "" for node in _cells(row)[0].findall(".//w:t", NS))
                  in ("Paket kapsamı", "Eczane Bazlı Sponsorluk – Cihaz başına eş zamanlı azami Sponsor", "Bölge Sponsorluğu süresi")]
    _replace_data_rows(tariff_table, tariff_rows or [["[GEÇERLİ TARİFE YOK]", "Yönetim panelinden tarife tanımlanmalı"]])
    tariff_table.remove(tariff_table.findall("./w:tr", NS)[0])
    for row in fixed_rows:
        tariff_table.append(row)

    physical = [device for plan in plans for device in plan.cihazlar.all()]
    if physical and len(physical) == len(devices) and all(device.garanti_ay is not None for device in physical):
        durations = {device.garanti_ay for device in physical}
        warranty = (f"Sözleşme başlangıcından itibaren {next(iter(durations))} ay" if len(durations) == 1
                    else "; ".join(f"{device.seri_no}: {device.garanti_ay} ay" for device in physical))
        for row in tables[8].findall("./w:tr", NS):
            cells = _cells(row)
            if len(cells) > 1 and "Garanti süresi" in "".join(node.text or "" for node in cells[0].findall(".//w:t", NS)):
                _set_cell(cells[1], warranty)

    sign_rows = tables[9].findall("./w:tr", NS)
    _set_cell(_cells(sign_rows[1])[0], f"Ad Soyad / Unvan: {pharmacy.sahip_adi or '[GİRİLMELİ]'}\nKaşe - İmza:\nTarih: {_fmt_date(sozlesme.gercek_imza_tarihi) or '[İMZA TARİHİ GİRİLMELİ]'}")


def _fill_ek2(root, sozlesme) -> None:
    tables = root.findall(".//w:tbl", NS)
    if len(tables) < 7:
        raise ContractTemplateError("Ek-2 şablon yapısı beklenen 7 tabloyu içermiyor.")
    pharmacy = sozlesme.eczane
    devices = _device_rows(sozlesme)
    metadata = tables[0].findall("./w:tr", NS)
    _set_cell(_cells(metadata[0])[1], f"EK2-{sozlesme.baslangic_tarihi.year}-{sozlesme.pk:06d}")
    _set_cell(_cells(metadata[1])[1], _fmt_date(sozlesme.gercek_imza_tarihi) or "[İMZA / ONAY TARİHİ GİRİLMELİ]")
    _set_cell(_cells(metadata[2])[1], f"{_fmt_date(sozlesme.baslangic_tarihi)} / [SAAT GİRİLMELİ]")
    _set_cell(_cells(metadata[3])[1], pharmacy.adres or "[TAM ADRES GİRİLMELİ]")
    labels = sorted({_plan_label(row[3]) for row in devices})
    _set_cell(_cells(metadata[4])[1], ", ".join(labels) or "Tahsis")

    parties = tables[1].findall("./w:tr", NS)
    _set_cell(_cells(parties[1])[0], "Yetkili / teknik personel: [GİRİLMELİ]\nGörevi: [GİRİLMELİ]\nTelefon: [GİRİLMELİ]")
    _set_cell(_cells(parties[1])[1], f"Eczane unvanı: {pharmacy.ad}\nAdı soyadı (Eczacı / yetkili): {pharmacy.sahip_adi or '[GİRİLMELİ]'}\nTelefon: {pharmacy.telefon or '[GİRİLMELİ]'}")

    rows = [[str(index), model, "1", serial_no, "☐ Yeni, hasarsız"]
            for index, (model, serial_no, _label, _plan) in enumerate(devices, 1)]
    _replace_data_rows(tables[2], rows or [["1", "[MODEL GİRİLMELİ]", "0", "[SERİ NO GİRİLMELİ]", "☐ Yeni, hasarsız"]])

    # Bölüm 6'daki # ile işaretli tarih alanları; hükmün geri kalanı aynen kalır.
    for paragraph in root.findall("./w:body/w:p", NS):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", NS))
        value = None
        if "Ödeme Başlangıç Tarihi:" in text and "#" in text:
            value = _fmt_date(sozlesme.kullanim_bedeli_baslangic)
        elif text.startswith("Aktivasyon Tarihi:") and "#" in text:
            value = _fmt_date(sozlesme.baslangic_tarihi)
        if value:
            for node in paragraph.findall(".//w:t", NS):
                node.text = (node.text or "").replace("#", value)

    # 4=aksesuar, 5=kontrol listesi, 7=kusur/eksik: tablolar 3, 4 ve 5 elle doldurulur.
    # Son tablo (6) ise bölüm 8'deki imza alanıdır; bilinen taraf bilgileri aktarılır.
    signatures = tables[6].findall("./w:tr", NS)
    date = _fmt_date(sozlesme.gercek_imza_tarihi) or "[İMZA TARİHİ GİRİLMELİ]"
    _set_cell(_cells(signatures[1])[0], f"Ad Soyad: [TESLİM EDEN GİRİLMELİ]\nKaşe - İmza:\nTarih: {date}")
    _set_cell(_cells(signatures[1])[1], f"Ad Soyad: {pharmacy.sahip_adi or '[GİRİLMELİ]'}\nKaşe - İmza:\nTarih: {date}")


def generate_contract_docx(sozlesme, kind: str) -> tuple[bytes, list[str]]:
    if sozlesme.sozlesme_surumu != "2026-EK1":
        raise ContractTemplateError(
            "Eski sözleşme yeni Ek-1/Ek-2 şablonuyla yeniden yorumlanamaz."
        )
    kind = kind.upper()
    if kind not in ("EK1", "EK2"):
        raise ContractTemplateError("Belge türü EK1 veya EK2 olmalıdır.")
    template = _template_path(kind)
    output = io.BytesIO()
    with ZipFile(template, "r") as source, ZipFile(output, "w", ZIP_DEFLATED) as target:
        document_xml = source.read("word/document.xml")
        root = _parse_document(document_xml)
        (_fill_ek1 if kind == "EK1" else _fill_ek2)(root, sozlesme)
        rendered_xml = _serialize_document(root, document_xml)
        for info in source.infolist():
            target.writestr(info, rendered_xml if info.filename == "word/document.xml" else source.read(info.filename))
    return output.getvalue(), missing_fields(sozlesme, kind)


def contract_preview_html(sozlesme, kind="EK1"):
    """İndirilen dosyayla aynı doldurulmuş Word içeriğinin güvenli HTML önizlemesi."""
    content, missing = generate_contract_docx(sozlesme, kind)
    with ZipFile(io.BytesIO(content)) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))

    def paragraph(node):
        pieces = []
        for run in node.findall(".//w:r", NS):
            text = "".join(html.escape(item.text or "").replace(chr(10), "<br>")
                           if item.tag == f"{{{W}}}t" else "<br>"
                           for item in run.iter() if item.tag in (f"{{{W}}}t", f"{{{W}}}br"))
            for property_name, tag in (("b", "strong"), ("i", "em")):
                setting = run.find(f"./w:rPr/w:{property_name}", NS)
                if setting is not None and setting.get(f"{{{W}}}val", "1") not in ("0", "false", "off"):
                    text = f"<{tag}>{text}</{tag}>"
            pieces.append(text)
        text = "".join(pieces)
        if not text.strip():
            return ""
        align = node.find("./w:pPr/w:jc", NS)
        align = align.get(f"{{{W}}}val", "left") if align is not None else "left"
        align = align if align in ("left", "right", "center", "justify") else "left"
        return f'<p style="text-align:{align}">{text}</p>'

    def table(node):
        rows = []
        for row in node.findall("./w:tr", NS):
            cells = []
            for cell in _cells(row):
                span = cell.find("./w:tcPr/w:gridSpan", NS)
                colspan = int(span.get(f"{{{W}}}val", "1")) if span is not None else 1
                body = "".join(paragraph(p) for p in cell.findall("./w:p", NS))
                cells.append(f'<td colspan="{colspan}">{body}</td>')
            rows.append("<tr>" + "".join(cells) + "</tr>")
        return '<table class="sz-table"><tbody>' + "".join(rows) + "</tbody></table>"

    body = root.find("./w:body", NS)
    rendered = "".join(paragraph(node) if node.tag == f"{{{W}}}p" else table(node)
                       if node.tag == f"{{{W}}}tbl" else "" for node in body)
    return '<article class="sz-contract sz-official-document">' + rendered + "</article>", missing
