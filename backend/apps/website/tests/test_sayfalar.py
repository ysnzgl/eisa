"""Sayfa yaşam döngüsü: oluştur → bloklar → yayınla → public; yayından kaldır; revizyon; 409."""
from unittest.mock import patch

import pytest

from apps.website.models import MenuOgesi, Sayfa, SayfaRevizyon
from apps.website.services.menu import menu_kaydet

from .conftest import ornek_hero

pytestmark = pytest.mark.django_db

ADMIN = "/api/website/admin/sayfalar/"


def _bloklar_put(client, sayfa_id, surum, bloklar):
    return client.put(f"{ADMIN}{sayfa_id}/bloklar/", {"surum": surum, "bloklar": bloklar}, format="json")


def test_tam_akis_yayinla_public_gorunur(editor_client, site_istemci, medya_olustur):
    yanit = editor_client.post(ADMIN, {"slug": "teknoloji", "baslik": "Teknoloji", "sira": 2}, format="json")
    assert yanit.status_code == 201, yanit.data
    sayfa = yanit.data
    assert sayfa["durum"] == "taslak" and sayfa["bloklar"] == [] and sayfa["taslak_degisti"] is True

    # Yayında değil → public 404
    assert site_istemci.get("/api/website/public/sayfalar/teknoloji/").status_code == 404

    medya = medya_olustur()
    yanit = _bloklar_put(
        editor_client, sayfa["id"], sayfa["surum"],
        [
            {"tip": "sayfa_basligi", "veri": {"baslik": "Teknoloji", "fazla": "atılır"}, "gorunur": True, "anchor_id": ""},
            {"tip": "gorsel_metin", "veri": {"baslik": "Kiosk", "metin": "Metin", "gorsel": {"id": medya.pk}}, "gorunur": True, "anchor_id": "kiosk"},
            {"tip": "sss", "veri": {"baslik": "SSS", "sorular": [{"soru": "S?", "cevap": "C."}]}, "gorunur": False, "anchor_id": ""},
        ],
    )
    assert yanit.status_code == 200, yanit.data
    detay = yanit.data
    assert [b["tip"] for b in detay["bloklar"]] == ["sayfa_basligi", "gorsel_metin", "sss"]
    assert [b["sira"] for b in detay["bloklar"]] == [0, 1, 2]
    assert "fazla" not in detay["bloklar"][0]["veri"]
    assert detay["surum"] == sayfa["surum"] + 1

    yanit = editor_client.post(f"{ADMIN}{sayfa['id']}/yayinla/", {"not": "İlk yayın"}, format="json")
    assert yanit.status_code == 200
    assert yanit.data["durum"] == "yayinda" and yanit.data["taslak_degisti"] is False

    public = site_istemci.get("/api/website/public/sayfalar/teknoloji/")
    assert public.status_code == 200
    assert public["Cache-Control"] == "public, max-age=60"
    veri = public.data
    assert set(veri) == {"slug", "baslik", "seo", "yayin_tarihi", "revizyon_id", "bloklar"}
    assert veri["seo"] == {"baslik": "Teknoloji", "aciklama": "", "og_gorsel": None}
    # gorunur=false blok public'te yok; id "b_<pk>" biçiminde.
    assert [b["tip"] for b in veri["bloklar"]] == ["sayfa_basligi", "gorsel_metin"]
    assert all(b["id"].startswith("b_") for b in veri["bloklar"])
    assert set(veri["bloklar"][1]) == {"id", "tip", "anchor_id", "veri"}
    assert veri["bloklar"][1]["anchor_id"] == "kiosk"
    assert veri["bloklar"][1]["veri"]["gorsel"]["yol"].startswith("/api/media/website/")

    liste = site_istemci.get("/api/website/public/sayfalar/")
    assert liste.status_code == 200
    assert [s["slug"] for s in liste.data] == ["teknoloji"]
    assert set(liste.data[0]) == {"slug", "guncellenme"}


def test_taslak_degisiklik_public_snapshotu_etkilemez(editor_client, site_istemci, sayfa_olustur):
    sayfa = sayfa_olustur(slug="hakkimizda", yayinla=True)
    eski = site_istemci.get("/api/website/public/sayfalar/hakkimizda/").data
    yanit = _bloklar_put(editor_client, sayfa.pk, sayfa.surum, [{"tip": "hero", "veri": ornek_hero(baslik="Yeni değere", vurgu="değere")}])
    assert yanit.status_code == 200
    assert yanit.data["taslak_degisti"] is True
    yeni = site_istemci.get("/api/website/public/sayfalar/hakkimizda/").data
    assert yeni["bloklar"][0]["veri"]["baslik"] == eski["bloklar"][0]["veri"]["baslik"]


def test_yayindan_kaldir_404(editor_client, site_istemci, sayfa_olustur):
    sayfa = sayfa_olustur(slug="sponsorlar", yayinla=True)
    assert site_istemci.get("/api/website/public/sayfalar/sponsorlar/").status_code == 200
    yanit = editor_client.post(f"{ADMIN}{sayfa.pk}/yayindan-kaldir/")
    assert yanit.status_code == 200 and yanit.data["durum"] == "taslak"
    assert site_istemci.get("/api/website/public/sayfalar/sponsorlar/").status_code == 404
    assert site_istemci.get("/api/website/public/sayfalar/").data == []


def test_revizyon_listesi_ve_geri_al(editor_client, site_istemci, sayfa_olustur, editor):
    sayfa = sayfa_olustur(slug="iletisim", yayinla=True)
    ilk_rev = sayfa.aktif_revizyon_id

    _bloklar_put(editor_client, sayfa.pk, sayfa.surum, [{"tip": "hero", "veri": ornek_hero(baslik="İkinci değere", vurgu="değere")}])
    editor_client.post(f"{ADMIN}{sayfa.pk}/yayinla/", {"not": "ikinci"}, format="json")
    assert site_istemci.get("/api/website/public/sayfalar/iletisim/").data["bloklar"][0]["veri"]["baslik"] == "İkinci değere"

    revler = editor_client.get(f"{ADMIN}{sayfa.pk}/revizyonlar/").data
    assert len(revler) == 2
    assert set(revler[0]) == {"id", "yayinlayan_adi", "yayin_tarihi", "not", "aktif"}
    assert revler[0]["aktif"] is True and revler[0]["not"] == "ikinci" and revler[0]["yayinlayan_adi"] == "Ece Editör"
    assert revler[1]["aktif"] is False

    yanit = editor_client.post(f"{ADMIN}{sayfa.pk}/revizyonlar/{ilk_rev}/geri-al/")
    assert yanit.status_code == 200, yanit.data
    assert yanit.data["bloklar"][0]["veri"]["baslik"] == "Bekleme süresini değere dönüştürün"
    assert yanit.data["taslak_degisti"] is False
    assert SayfaRevizyon.objects.filter(sayfa_id=sayfa.pk).count() == 3
    assert site_istemci.get("/api/website/public/sayfalar/iletisim/").data["bloklar"][0]["veri"]["baslik"] == "Bekleme süresini değere dönüştürün"

    # Başka sayfanın revizyonu ile geri alma 404
    diger = sayfa_olustur(slug="diger", yayinla=True)
    assert editor_client.post(f"{ADMIN}{sayfa.pk}/revizyonlar/{diger.aktif_revizyon_id}/geri-al/").status_code == 404


def test_optimistic_concurrency_409(editor_client, superadmin_client, sayfa_olustur):
    sayfa = sayfa_olustur(slug="cakisma")
    surum = sayfa.surum
    ilk = editor_client.patch(f"{ADMIN}{sayfa.pk}/", {"baslik": "Editor", "surum": surum}, format="json")
    assert ilk.status_code == 200 and ilk.data["surum"] == surum + 1

    ikinci = superadmin_client.patch(f"{ADMIN}{sayfa.pk}/", {"baslik": "Admin", "surum": surum}, format="json")
    assert ikinci.status_code == 409
    assert ikinci.data["surum"] == surum + 1
    assert Sayfa.objects.get(pk=sayfa.pk).baslik == "Editor"

    blok = _bloklar_put(superadmin_client, sayfa.pk, surum, [{"tip": "hero", "veri": ornek_hero()}])
    assert blok.status_code == 409

    eksik = editor_client.patch(f"{ADMIN}{sayfa.pk}/", {"baslik": "Sürümsüz"}, format="json")
    assert eksik.status_code == 400 and "surum" in eksik.data


def test_bloklar_put_hata_bicimi_ve_id_korunumu(editor_client, sayfa_olustur):
    sayfa = sayfa_olustur(slug="bloklu")
    detay = editor_client.get(f"{ADMIN}{sayfa.pk}/").data
    blok_id = detay["bloklar"][0]["id"]

    yanit = _bloklar_put(
        editor_client, sayfa.pk, detay["surum"],
        [
            {"id": blok_id, "tip": "hero", "veri": ornek_hero()},
            {"tip": "sss", "veri": {"baslik": "S", "sorular": []}},
            {"tip": "sayfa_basligi", "veri": {"baslik": ""}},
        ],
    )
    assert yanit.status_code == 400
    assert yanit.data == {
        "bloklar": {
            "1": {"sorular": ["En az 1 öğe olmalıdır."]},
            "2": {"baslik": ["Bu alan zorunludur."]},
        }
    }

    yanit = _bloklar_put(
        editor_client, sayfa.pk, detay["surum"],
        [{"tip": "sayfa_basligi", "veri": {"baslik": "Yeni"}}, {"id": blok_id, "tip": "hero", "veri": ornek_hero()}],
    )
    assert yanit.status_code == 200
    assert [b["tip"] for b in yanit.data["bloklar"]] == ["sayfa_basligi", "hero"]
    assert yanit.data["bloklar"][1]["id"] == blok_id  # id'si gelen blok korunur, sırası değişir

    yanit = _bloklar_put(editor_client, sayfa.pk, yanit.data["surum"], [{"tip": "sayfa_basligi", "veri": {"baslik": "Tek"}}])
    assert [b["tip"] for b in yanit.data["bloklar"]] == ["sayfa_basligi"]  # id'si gelmeyen eski bloklar silinir


def test_slug_kurallari_ve_silme_korumasi(editor_client, sayfa_olustur):
    for slug in ("blog", "api", "_next", "admin", "Buyuk-Harf", "türkçe"):
        yanit = editor_client.post(ADMIN, {"slug": slug, "baslik": "X"}, format="json")
        assert yanit.status_code == 400 and "slug" in yanit.data, slug

    sayfa_olustur(slug="mevcut")
    assert editor_client.post(ADMIN, {"slug": "mevcut", "baslik": "X"}, format="json").status_code == 400

    for slug in ("anasayfa", "kvkk", "cerez-politikasi"):
        korunan = sayfa_olustur(slug=slug)
        yanit = editor_client.delete(f"{ADMIN}{korunan.pk}/")
        assert yanit.status_code == 400, slug

    menude = sayfa_olustur(slug="menude")
    menu_kaydet(
        "header",
        [{"id": None, "etiket": "Menüdeki", "link_tipi": "sayfa", "sayfa_id": menude.pk, "bolum_anchor": "", "url": "",
          "yeni_sekme": False, "cta": False, "aktif": True, "cocuklar": []}],
        user=None, revalidate_et=False,
    )
    yanit = editor_client.delete(f"{ADMIN}{menude.pk}/")
    assert yanit.status_code == 400 and "Header" in yanit.data["detail"] and "Menüdeki" in yanit.data["detail"]

    MenuOgesi.objects.all().delete()
    assert editor_client.delete(f"{ADMIN}{menude.pk}/").status_code == 204
    assert not Sayfa.objects.filter(pk=menude.pk).exists()


def test_onizleme_url_uretir(editor_client, sayfa_olustur, settings):
    settings.SITE_PUBLIC_URL = "https://eisa.com.tr"
    sayfa = sayfa_olustur(slug="onizlenecek")
    yanit = editor_client.post(f"{ADMIN}{sayfa.pk}/onizleme/")
    assert yanit.status_code == 200
    assert yanit.data["url"].startswith("https://eisa.com.tr/api/preview?tur=sayfa&slug=onizlenecek&token=")


def test_yayinla_dogru_taglerle_revalidate_tetikler(editor_client, sayfa_olustur, django_capture_on_commit_callbacks):
    sayfa = sayfa_olustur(slug="anasayfa")
    with patch("apps.website.services.revalidate.revalidate_gonder") as gonder:
        with django_capture_on_commit_callbacks(execute=True):
            assert editor_client.post(f"{ADMIN}{sayfa.pk}/yayinla/").status_code == 200
        gonder.assert_called_once_with(["sayfa:anasayfa", "sayfalar", "site"])

        gonder.reset_mock()
        with django_capture_on_commit_callbacks(execute=True):
            editor_client.post(f"{ADMIN}{sayfa.pk}/yayindan-kaldir/")
        gonder.assert_called_once_with(["sayfa:anasayfa", "sayfalar", "site"])

        # Taslak kaydı public'i etkilemez → revalidate yok.
        gonder.reset_mock()
        sayfa.refresh_from_db()
        with django_capture_on_commit_callbacks(execute=True):
            _bloklar_put(editor_client, sayfa.pk, sayfa.surum, [{"tip": "hero", "veri": ornek_hero()}])
        gonder.assert_not_called()

        # 409 durumunda (rollback) revalidate çağrılmaz.
        with django_capture_on_commit_callbacks(execute=True):
            yanit = editor_client.patch(f"{ADMIN}{sayfa.pk}/", {"baslik": "Eski sürüm", "surum": 1}, format="json")
        assert yanit.status_code == 409
        gonder.assert_not_called()
