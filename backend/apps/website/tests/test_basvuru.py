"""Public başvuru formu: geçerli kayıt, KVKK, honeypot, throttle, IP hash ve admin gelen kutusu."""
import pytest

from apps.website.models import Basvuru
from apps.website.yardimcilar import ip_hash

pytestmark = pytest.mark.django_db

URL = "/api/website/public/basvurular/"


def _govde(**ek):
    veri = {
        "tip": "pilot", "ad_soyad": "Ayşe Yılmaz", "kurum": "Şifa Eczanesi", "eposta": "ayse@example.com",
        "telefon": "+90 555 000 00 00", "il": "İstanbul", "mesaj": "Pilot hakkında bilgi almak istiyorum.",
        "kvkk_onay": True, "kaynak_sayfa": "/#pilot", "website": "",
    }
    veri.update(ek)
    return veri


def test_gecerli_basvuru_kaydedilir(site_istemci, sayfa_olustur):
    kvkk = sayfa_olustur(slug="kvkk", yayinla=True)
    yanit = site_istemci.post(URL, _govde(), format="json", REMOTE_ADDR="203.0.113.7")
    assert yanit.status_code == 201 and yanit.data == {"ok": True}
    b = Basvuru.objects.get()
    assert (b.tip, b.ad_soyad, b.durum, b.kvkk_onay) == ("pilot", "Ayşe Yılmaz", "yeni", True)
    assert b.kvkk_metin_versiyonu == f"kvkk-r{kvkk.aktif_revizyon_id}"
    assert b.ip_hash == ip_hash("203.0.113.7") and "203.0.113.7" not in b.ip_hash
    assert len(b.ip_hash) == 64


def test_kvkk_onaysiz_ve_eksik_alanlar_400(site_istemci):
    yanit = site_istemci.post(URL, _govde(kvkk_onay=False), format="json")
    assert yanit.status_code == 400 and "kvkk_onay" in yanit.data
    yanit = site_istemci.post(URL, _govde(ad_soyad="", eposta="gecersiz", mesaj="x" * 2001, telefon="1" * 21, tip="baska"), format="json")
    assert yanit.status_code == 400
    assert {"ad_soyad", "eposta", "mesaj", "telefon", "tip"} <= set(yanit.data)
    assert Basvuru.objects.count() == 0


def test_honeypot_201_doner_kayit_olusturmaz(site_istemci):
    yanit = site_istemci.post(URL, _govde(website="http://spam.example"), format="json")
    assert yanit.status_code == 201 and yanit.data == {"ok": True}
    assert Basvuru.objects.count() == 0


def test_throttle_ip_basina_5_saat(site_istemci):
    for _ in range(5):
        assert site_istemci.post(URL, _govde(), format="json", REMOTE_ADDR="198.51.100.1").status_code == 201
    yanit = site_istemci.post(URL, _govde(), format="json", REMOTE_ADDR="198.51.100.1")
    assert yanit.status_code == 429
    # Başka IP etkilenmez.
    assert site_istemci.post(URL, _govde(), format="json", REMOTE_ADDR="198.51.100.2").status_code == 201
    assert Basvuru.objects.count() == 6


def test_site_sunucusu_istemci_ip_aktarimi(dis_istemci, settings):
    settings.WEBSITE_SERVER_TOKEN = "test-site-token-guclu"
    basliklar = {"HTTP_X_WEBSITE_TOKEN": "test-site-token-guclu", "REMOTE_ADDR": "10.0.0.5"}
    # Site sunucusu (tek pod IP) farklı istemcileri aktarabilir; throttle istemci IP'sine göre çalışır.
    for i in range(5):
        assert dis_istemci.post(URL, _govde(), format="json", HTTP_X_WEBSITE_CLIENT_IP="192.0.2.10", **basliklar).status_code == 201
    assert dis_istemci.post(URL, _govde(), format="json", HTTP_X_WEBSITE_CLIENT_IP="192.0.2.10", **basliklar).status_code == 429
    assert dis_istemci.post(URL, _govde(), format="json", HTTP_X_WEBSITE_CLIENT_IP="192.0.2.11", **basliklar).status_code == 201
    assert Basvuru.objects.filter(ip_hash=ip_hash("192.0.2.10")).count() == 5

    # Yanlış token → uç hiç yokmuş gibi 404; kayıt oluşmaz, IP beyanına güvenilmez.
    yanit = dis_istemci.post(URL, _govde(), format="json", HTTP_X_WEBSITE_TOKEN="yanlis", HTTP_X_WEBSITE_CLIENT_IP="192.0.2.99", REMOTE_ADDR="10.9.9.9")
    assert yanit.status_code == 404
    assert not Basvuru.objects.filter(ip_hash__in=[ip_hash("10.9.9.9"), ip_hash("192.0.2.99")]).exists()


def test_uretimde_varsayilan_token_kabul_edilmez(dis_istemci, settings):
    settings.DEBUG = False
    settings.WEBSITE_SERVER_TOKEN = "dev-website-token"
    yanit = dis_istemci.post(URL, _govde(), format="json", HTTP_X_WEBSITE_TOKEN="dev-website-token", HTTP_X_WEBSITE_CLIENT_IP="192.0.2.50", REMOTE_ADDR="10.1.1.1")
    # Fail-closed: üretimde geliştirme token'ı ile site uçları kapalıdır.
    assert yanit.status_code == 404
    assert not Basvuru.objects.exists()

def test_admin_gelen_kutusu_filtre_ozet_ve_patch(editor_client, editor, site_istemci):
    site_istemci.post(URL, _govde(), format="json", REMOTE_ADDR="198.51.100.3")
    site_istemci.post(URL, _govde(tip="sponsor", ad_soyad="Mehmet Kaya", eposta="m@example.com"), format="json", REMOTE_ADDR="198.51.100.4")

    yanit = editor_client.get("/api/website/admin/basvurular/")
    assert yanit.status_code == 200
    assert yanit.data["count"] == 2 and yanit.data["yeni_sayisi"] == 2 and len(yanit.data["results"]) == 2
    b = yanit.data["results"][0]
    assert set(b) == {
        "id", "tip", "ad_soyad", "kurum", "eposta", "telefon", "il", "mesaj", "kvkk_onay", "kvkk_metin_versiyonu",
        "kaynak_sayfa", "durum", "notlar", "atanan", "olusturulma_tarihi",
    }
    assert "ip_hash" not in b

    assert editor_client.get("/api/website/admin/basvurular/", {"tip": "sponsor"}).data["count"] == 1
    assert editor_client.get("/api/website/admin/basvurular/", {"q": "Mehmet"}).data["count"] == 1
    assert editor_client.get("/api/website/admin/basvurular/", {"page_size": 1}).data["results"].__len__() == 1
    assert editor_client.get("/api/website/admin/basvurular/ozet/").data == {"yeni": 2}

    hedef = Basvuru.objects.get(tip="sponsor")
    yanit = editor_client.patch(
        f"/api/website/admin/basvurular/{hedef.pk}/",
        {"durum": "iletisimde", "notlar": "Arandı", "atanan_id": editor.pk, "ad_soyad": "Değiştirilemez"},
        format="json",
    )
    assert yanit.status_code == 200, yanit.data
    assert yanit.data["durum"] == "iletisimde" and yanit.data["atanan"] == {"id": editor.pk, "ad": "Ece Editör"}
    assert yanit.data["ad_soyad"] == "Mehmet Kaya"
    assert editor_client.get("/api/website/admin/basvurular/ozet/").data == {"yeni": 1}
    assert editor_client.patch(f"/api/website/admin/basvurular/{hedef.pk}/", {"durum": "uydurma"}, format="json").status_code == 400
    assert editor_client.delete(f"/api/website/admin/basvurular/{hedef.pk}/").status_code == 204
