import io
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError

from .documents import docx_paragraphs, validate_document
from .models import Gorev, GorevDosya

pytestmark = pytest.mark.django_db


def document(ext):
    if ext == "pdf":
        return b"%PDF-1.7\nexample"
    if ext in {"xls", "doc"}:
        return b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1example"
    output = io.BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml" if ext == "docx" else "xl/workbook.xml",
                         '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                         '<w:p><w:r><w:t>Merhaba &lt;script&gt;</w:t></w:r></w:p></w:document>')
    return output.getvalue()


@pytest.mark.parametrize("ext", ["pdf", "doc", "docx", "xls", "xlsx"])
def test_upload_persistent_attachment(admin_client, ext):
    task = Gorev.objects.create(baslik="Test", icerik="İçerik")
    payload = document(ext)
    with patch("apps.gorevler.views.StorageService") as cls:
        cls.return_value.upload_file.return_value = f"is-takip/{task.pk}/uuid.{ext}"
        response = admin_client.post(f"/api/is-takip/gorevler/{task.pk}/dosyalar/", {
            "dosya": SimpleUploadedFile(f"örnek.{ext}", payload),
        }, format="multipart")
        assert response.status_code == 201
        cls.return_value.upload_file.assert_called_once()
    attachment = GorevDosya.objects.get()
    assert attachment.object_key.startswith("is-takip/")
    assert attachment.olusturan.rol == "superadmin"
    data = admin_client.get(f"/api/is-takip/gorevler/{task.pk}/").json()
    assert data["dosyalar"][0]["id"] == attachment.pk
    assert "object_key" not in data["dosyalar"][0]


@pytest.mark.parametrize("filename,content", [("test.exe", b"MZ"), ("test.pdf", b"<html>"), ("test.docx", b"PK"), ("test.xls", b"")])
def test_reject_invalid_files(admin_client, filename, content):
    task = Gorev.objects.create(baslik="Test", icerik="İçerik")
    with patch("apps.gorevler.views.StorageService") as cls:
        response = admin_client.post(f"/api/is-takip/gorevler/{task.pk}/dosyalar/", {
            "dosya": SimpleUploadedFile(filename, content),
        }, format="multipart")
        assert response.status_code == 400
        cls.assert_not_called()


def test_reject_oversize():
    uploaded = SimpleUploadedFile("test.pdf", document("pdf"))
    uploaded.size = 25 * 1024 * 1024 + 1
    with pytest.raises(ValidationError):
        validate_document(uploaded)


def test_private_download_scoped_to_task(admin_client, eczaci):
    from rest_framework.test import APIClient
    anonymous = APIClient()
    pharmacist = APIClient()
    pharmacist.force_authenticate(eczaci)
    task = Gorev.objects.create(baslik="Test", icerik="İçerik")
    other = Gorev.objects.create(baslik="Other", icerik="İçerik")
    file = GorevDosya.objects.create(gorev=task, ad="örnek.pdf", object_key="is-takip/uuid.pdf", content_type="application/pdf", boyut=8)
    path = f"/api/is-takip/gorevler/{task.pk}/dosyalar/{file.pk}/"
    assert anonymous.get(path).status_code in {401, 403}
    assert pharmacist.get(path).status_code == 403
    assert admin_client.get(f"/api/is-takip/gorevler/{other.pk}/dosyalar/{file.pk}/").status_code == 404
    with patch("apps.gorevler.views.StorageService") as cls:
        source = MagicMock()
        source.stream.return_value = [b"%PDF-1.7"]
        cls.return_value.client.get_object.return_value = source
        response = admin_client.get(path + "?indir=1")
        assert response.status_code == 200
        assert response["Content-Disposition"].startswith("attachment;")
        assert response["Cache-Control"] == "private, no-store"
        assert b"".join(response.streaming_content) == b"%PDF-1.7"
        source.close.assert_called_once()
        source.release_conn.assert_called_once()


def test_failed_upload_has_no_record(admin_client):
    task = Gorev.objects.create(baslik="Test", icerik="İçerik")
    with patch("apps.gorevler.views.StorageService") as cls:
        cls.return_value.upload_file.side_effect = OSError("offline")
        response = admin_client.post(f"/api/is-takip/gorevler/{task.pk}/dosyalar/", {
            "dosya": SimpleUploadedFile("test.pdf", document("pdf")),
        }, format="multipart")
    assert response.status_code == 503
    assert not GorevDosya.objects.exists()


def test_docx_preview_is_text_only():
    assert docx_paragraphs(document("docx")) == ["Merhaba <script>"]
    with pytest.raises(ValidationError):
        docx_paragraphs(b"bad zip")
