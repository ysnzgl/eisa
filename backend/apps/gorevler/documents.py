"""İş ekleri için sınırlı belge doğrulaması ve DOCX metin önizlemesi."""
import io
from pathlib import Path
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree

from rest_framework.exceptions import ValidationError

MAX_FILE_SIZE = 25 * 1024 * 1024
TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def validate_document(uploaded):
    if uploaded is None:
        raise ValidationError({"dosya": "Dosya seçin."})
    ext = Path(uploaded.name).suffix.lower()
    if ext not in TYPES:
        raise ValidationError({"dosya": "PDF, Word (.doc/.docx) veya Excel (.xls/.xlsx) yükleyin."})
    if not 0 < uploaded.size <= MAX_FILE_SIZE:
        raise ValidationError({"dosya": "Dosya boş olamaz ve 25 MB sınırını aşamaz."})
    if len(uploaded.name) > 255:
        raise ValidationError({"dosya": "Dosya adı 255 karakteri aşamaz."})
    header = uploaded.read(8)
    uploaded.seek(0)
    valid = False
    if ext == ".pdf":
        valid = header.startswith(b"%PDF-")
    elif ext in {".doc", ".xls"}:
        valid = header == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    else:
        try:
            with ZipFile(uploaded) as archive:
                member = "word/document.xml" if ext == ".docx" else "xl/workbook.xml"
                valid = "[Content_Types].xml" in archive.namelist() and member in archive.namelist()
                if sum(info.file_size for info in archive.infolist()) > 100 * 1024 * 1024:
                    raise ValidationError({"dosya": "Belgenin açılmış boyutu 100 MB sınırını aşamaz."})
        except (BadZipFile, OSError):
            pass
        finally:
            uploaded.seek(0)
    if not valid:
        raise ValidationError({"dosya": "Dosya içeriği uzantısıyla eşleşmiyor veya dosya bozuk."})
    uploaded.content_type = TYPES[ext]
    return TYPES[ext]


def docx_paragraphs(data):
    try:
        with ZipFile(io.BytesIO(data)) as archive:
            info = archive.getinfo("word/document.xml")
            if info.file_size > 5 * 1024 * 1024:
                raise ValueError("Önizleme sınırı aşıldı")
            xml = archive.read(info)
        # Entity/DTD işleme yapılmaz; yalnız sınırlı boyutta düz metin okunur.
        markup = xml.replace(b"\x00", b"").upper()
        if b"<!DOCTYPE" in markup or b"<!ENTITY" in markup:
            raise ValueError("DTD desteklenmiyor")
        root = ElementTree.fromstring(xml)
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        paragraphs = []
        for p in root.iter(f"{ns}p"):
            paragraphs.append("".join(t.text or "" for t in p.iter(f"{ns}t")))
            if len(paragraphs) >= 2000:
                break
        return paragraphs
    except (BadZipFile, KeyError, ValueError, ElementTree.ParseError, RuntimeError, NotImplementedError):
        raise ValidationError({"detail": "Bu belge önizlenemiyor. Dosyayı indirerek açabilirsiniz."})
