"""Medya: lokal modda yükleme, tür/boyut kontrolü, SVG reddi, proxy ile sunum ve silme."""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.media_proxy import validate_media_object_key
from apps.website.models import WebsiteMedya

pytestmark = pytest.mark.django_db

URL = "/api/website/admin/medya/"


def test_png_yukleme_lokal_mod_ve_proxy(editor_client, site_istemci, png_dosyasi, _medya_kok):
    yanit = editor_client.post(URL, {"dosya": png_dosyasi("Kiosk Görseli.png", (40, 20)), "alt": "Kiosk"}, format="multipart")
    assert yanit.status_code == 201, yanit.data
    d = yanit.data
    assert set(d) == {"id", "yol", "alt", "genislik", "yukseklik", "mime", "dosya_adi", "boyut", "olusturulma_tarihi"}
    assert d["mime"] == "image/png" and (d["genislik"], d["yukseklik"]) == (40, 20) and d["alt"] == "Kiosk"
    assert d["yol"].startswith("/api/media/website/") and d["yol"].endswith(".png")
    medya = WebsiteMedya.objects.get(pk=d["id"])
    import re
    assert re.match(r"^website/\d{4}/\d{2}/[0-9a-f]{32}\.png$", medya.object_key)
    assert (_medya_kok / medya.object_key).is_file()

    sunum = site_istemci.get(d["yol"])
    assert sunum.status_code == 200
    assert sunum["Content-Type"] == "image/png"
    assert b"".join(sunum.streaming_content).startswith(b"\x89PNG")
    sunum.close()  # dosya tanıtıcısını bırak (Windows'ta silme için gerekli)

    liste = editor_client.get(URL, {"q": "kiosk"}).data
    assert liste["count"] == 1 and liste["results"][0]["id"] == d["id"]
    assert editor_client.get(URL, {"q": "yok"}).data["count"] == 0

    assert editor_client.patch(f"{URL}{d['id']}/", {"alt": "Yeni alt"}, format="json").data["alt"] == "Yeni alt"

    assert editor_client.delete(f"{URL}{d['id']}/").status_code == 204
    assert not (_medya_kok / medya.object_key).exists()
    assert site_istemci.get(d["yol"]).status_code == 404


def test_svg_ve_sahte_dosyalar_reddedilir(editor_client):
    svg = SimpleUploadedFile("logo.svg", b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>', content_type="image/svg+xml")
    yanit = editor_client.post(URL, {"dosya": svg}, format="multipart")
    assert yanit.status_code == 400 and "SVG" in yanit.data["dosya"][0]

    # Uzantısı/türü PNG gibi görünen SVG içeriği de reddedilir (içerik incelenir).
    gizli_svg = SimpleUploadedFile("logo.png", b"<svg onload=alert(1)></svg>", content_type="image/png")
    assert editor_client.post(URL, {"dosya": gizli_svg}, format="multipart").status_code == 400

    metin = SimpleUploadedFile("not.png", b"bu bir resim degil", content_type="image/png")
    assert editor_client.post(URL, {"dosya": metin}, format="multipart").status_code == 400

    assert editor_client.post(URL, {}, format="multipart").data == {"dosya": ["Bu alan zorunludur."]}
    assert WebsiteMedya.objects.count() == 0


def test_bildirilen_tur_yerine_icerik_kullanilir(editor_client, png_dosyasi):
    yanit = editor_client.post(URL, {"dosya": png_dosyasi("foto.jpg", content_type="image/jpeg")}, format="multipart")
    assert yanit.status_code == 201
    assert yanit.data["mime"] == "image/png" and yanit.data["yol"].endswith(".png")


def test_boyut_siniri(editor_client, png_dosyasi, monkeypatch):
    from apps.website.services import medya as medya_servisi

    monkeypatch.setattr(medya_servisi, "MAKS_BOYUT", 10)
    yanit = editor_client.post(URL, {"dosya": png_dosyasi()}, format="multipart")
    assert yanit.status_code == 400 and "10 MB" in yanit.data["dosya"][0]


def test_eczaci_medya_yukleyemez(eczaci_api, png_dosyasi):
    assert eczaci_api.post(URL, {"dosya": png_dosyasi()}, format="multipart").status_code == 403


def test_proxy_allow_list_ve_traversal(site_istemci, _medya_kok):
    assert validate_media_object_key("website/2026/11/a.webp") == "website/2026/11/a.webp"
    for kotu in ("website/../../core_api/settings.py", "/website/a.png", "website\\a.png", "website//a.png", "gizli/a.png"):
        with pytest.raises(ValueError):
            validate_media_object_key(kotu)
    # MEDIA_ROOT dışındaki bir dosyaya proxy üzerinden erişilemez.
    (_medya_kok.parent / "gizli.txt").write_text("gizli")
    assert site_istemci.get("/api/media/website/../gizli.txt").status_code in (404, 416)
    assert site_istemci.get("/api/media/website/2026/11/olmayan.png").status_code == 404
