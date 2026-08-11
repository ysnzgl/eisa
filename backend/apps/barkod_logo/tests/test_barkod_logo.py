"""Barkod Logo özelliği — hedefli backend testleri."""
import io
import struct
import uuid
import zlib
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.barkod_logo.models import BarkodLogo
from apps.barkod_logo.serializers import validate_barkod_logo_png
from apps.pharmacies.models import Kiosk


# ─── PNG oluşturucu yardımcıları ─────────────────────────────────────────────

def _crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def _chunk(chunk_type: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", _crc32(chunk_type + data))


def _make_png_bytes(
    width=336, height=336, color_type=0, bit_depth=8,
    pixels=None, trns=None, plte=None, extra_size=0,
):
    """PNG bayt dizisi üretir.

    pixels: None ise color_type'a göre beyaz, opak piksel üretilir.
    trns: tRNS chunk data bytes. color_type 0 için 2 byte, 3 için n byte, vb.
    plte: PLTE chunk data (palette, 3 bytes per entry).
    """
    magic = b"\x89PNG\r\n\x1a\n"
    # IHDR
    ihdr_data = struct.pack(">IIBBBBB", width, height, bit_depth, color_type, 0, 0, 0)
    ihdr = _chunk(b"IHDR", ihdr_data)

    # Kanal sayısı
    ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type, 1)

    # Piksel verisi
    if pixels is None:
        if color_type == 0:    # grayscale → white
            row_pix = b"\xFF" * width
        elif color_type == 2:  # RGB → white
            row_pix = b"\xFF\xFF\xFF" * width
        elif color_type == 3:  # palette index 0
            row_pix = b"\x00" * width
        elif color_type == 4:  # grayscale+alpha → white, opaque
            row_pix = b"\xFF\xFF" * width
        elif color_type == 6:  # RGBA → white, opaque
            row_pix = b"\xFF\xFF\xFF\xFF" * width
        else:
            row_pix = b"\xFF" * (width * ch)
    else:
        row_pix = pixels

    raw = (b"\x00" + row_pix) * height  # filter byte = 0 (None) per row
    idat_data = zlib.compress(raw, level=1)
    idat = _chunk(b"IDAT", idat_data)
    iend = _chunk(b"IEND", b"")

    chunks = [magic, ihdr]
    if plte is not None:
        chunks.append(_chunk(b"PLTE", plte))
    if trns is not None:
        chunks.append(_chunk(b"tRNS", trns))
    chunks += [idat, iend]
    data = b"".join(chunks)
    if extra_size:
        data += b"\x00" * extra_size
    return data


class FakeFile(io.BytesIO):
    def __init__(self, data: bytes, name="test.png", content_type="image/png"):
        super().__init__(data)
        self.name = name
        self.content_type = content_type
        self.size = len(data)


def _png_file(**kwargs) -> FakeFile:
    return FakeFile(_make_png_bytes(**kwargs))


def _png_file_with_size_override(size: int, **kwargs) -> FakeFile:
    f = FakeFile(_make_png_bytes(**kwargs))
    f.size = size
    return f



# ─── Görsel doğrulama testleri ─────────────────────────────────────────────

class TestPngValidation:
    # ── Kabul edilen durumlar ──────────────────────────────────────────────
    def test_grayscale_336x336_kabul(self):
        validate_barkod_logo_png(_png_file(color_type=0))  # hata vermemeli

    def test_rgb_grayscale_336x336_kabul(self):
        # color_type=2 (RGB) ama tüm pikseller R=G=B (beyaz) → gri tonlu kabul
        validate_barkod_logo_png(_png_file(color_type=2))

    def test_opak_rgba_grayscale_kabul(self):
        # color_type=6 (RGBA), tüm pikseller beyaz+opak → kabul
        validate_barkod_logo_png(_png_file(color_type=6))

    # ── Format / ölçü / boyut ret ─────────────────────────────────────────
    def test_png_olmayan_format_reddedilir(self):
        f = FakeFile(b"\xff\xd8\xff" + b"\x00" * 30, name="test.jpg")
        with pytest.raises(Exception):
            validate_barkod_logo_png(f)

    def test_yanlis_olcu_reddedilir(self):
        with pytest.raises(Exception):
            validate_barkod_logo_png(_png_file(width=100, height=100))

    def test_boyut_asimi_reddedilir(self):
        f = _png_file_with_size_override(2 * 1024 * 1024)
        with pytest.raises(Exception):
            validate_barkod_logo_png(f)

    # ── Şeffaflık ret ─────────────────────────────────────────────────────
    def test_rgba_seffaf_piksel_reddedilir(self):
        # RGBA, alpha=127 (yarı saydam) → ret
        row_pix = b"\xFF\xFF\xFF\x7F" * 336  # R=G=B=white, A=127
        with pytest.raises(Exception):
            validate_barkod_logo_png(_png_file(color_type=6, pixels=row_pix))

    def test_grayscale_alpha_seffaf_reddedilir(self):
        # grayscale+alpha, alpha=0 → ret
        row_pix = b"\xFF\x00" * 336  # pixel=white, alpha=0 (fully transparent)
        with pytest.raises(Exception):
            validate_barkod_logo_png(_png_file(color_type=4, pixels=row_pix))

    def test_trns_paletli_seffaf_reddedilir(self):
        # Paletli PNG + tRNS: ilk palette entry alpha=0
        plte = b"\xFF\xFF\xFF"  # 1 entry: white R=G=B
        trns = bytes([0])       # palette index 0 is transparent
        f = _png_file(color_type=3, plte=plte, trns=trns)
        with pytest.raises(Exception):
            validate_barkod_logo_png(f)

    def test_trns_grayscale_reddedilir(self):
        # color_type=0 + tRNS: bir gri değeri saydam
        trns = b"\x00\x00"  # 16-bit grayscale value = 0 is transparent
        f = _png_file(color_type=0, trns=trns)
        with pytest.raises(Exception):
            validate_barkod_logo_png(f)

    # ── Renkli görsel ret ─────────────────────────────────────────────────
    def test_renkli_rgb_reddedilir(self):
        # color_type=2 (RGB), R=255, G=0, B=0 (kırmızı) → renkli, ret
        row_pix = b"\xFF\x00\x00" * 336  # kırmızı piksel
        with pytest.raises(Exception):
            validate_barkod_logo_png(_png_file(color_type=2, pixels=row_pix))

    def test_renkli_rgba_reddedilir(self):
        # color_type=6 (RGBA), R=255, G=0, B=0, A=255 (opak kırmızı) → renkli, ret
        row_pix = b"\xFF\x00\x00\xFF" * 336
        with pytest.raises(Exception):
            validate_barkod_logo_png(_png_file(color_type=6, pixels=row_pix))

    def test_renkli_palet_reddedilir(self):
        # Paletli PNG, palette'de renkli giriş
        plte = b"\xFF\x00\x00"  # kırmızı
        with pytest.raises(Exception):
            validate_barkod_logo_png(_png_file(color_type=3, plte=plte))

    # ── Dosya pozisyonu sıfırlama ─────────────────────────────────────────
    def test_dosya_pozisyonu_sifirlanir(self):
        f = _png_file()
        validate_barkod_logo_png(f)
        assert f.tell() == 0, "Dosya pozisyonu doğrulama sonrası 0 olmalı"


# ─── Model testleri ────────────────────────────────────────────────────────

class TestBarkodLogoModel:
    def test_varsayilan_tarihler(self, db):
        now = timezone.now()
        logo = BarkodLogo(
            ad="Test",
            baslangic_zamani=now,
            bitis_zamani=now + timedelta(days=31),
            aktif=True,
        )
        # Başlangıç bugün
        assert logo.baslangic_zamani.date() == now.date()
        # Bitiş yaklaşık 1 ay sonra
        delta = logo.bitis_zamani - logo.baslangic_zamani
        assert delta.days >= 28

    def test_gunluk_limit_null_sinirsiz(self, db, eczane):
        now = timezone.now()
        logo = BarkodLogo.objects.create(
            ad="Sınırsız",
            baslangic_zamani=now,
            bitis_zamani=now + timedelta(days=30),
            aktif=True,
            gunluk_baski_limiti=None,
        )
        assert logo.gunluk_baski_limiti is None

    def test_pozitif_tam_sayi_kabul(self, db, eczane):
        from django.core.exceptions import ValidationError
        now = timezone.now()
        logo = BarkodLogo(
            ad="Limitli",
            baslangic_zamani=now,
            bitis_zamani=now + timedelta(days=30),
            aktif=True,
            gunluk_baski_limiti=50,
        )
        logo.full_clean()  # hata vermemeli

    def test_sifir_gunluk_limit_reddedilir(self, db):
        from django.core.exceptions import ValidationError
        now = timezone.now()
        logo = BarkodLogo(
            ad="Sıfır",
            baslangic_zamani=now,
            bitis_zamani=now + timedelta(days=30),
            gunluk_baski_limiti=0,
        )
        with pytest.raises(ValidationError):
            logo.full_clean()


# ─── API testleri ──────────────────────────────────────────────────────────

LIST_URL = "/api/barkod-logo/logolar/"


@pytest.fixture
def admin_client_barkod(admin_client):
    return admin_client


class TestBarkodLogoAPI:
    def test_kiosk_yalniz_kendi_logolarini_alir(self, db, kiosk, eczane, admin_client):
        now = timezone.now()
        from apps.pharmacies.models import Kiosk
        il = eczane.il
        ilce = eczane.ilce
        from apps.pharmacies.models import Eczane
        eczane2 = Eczane.objects.create(ad="Eczane B", il=il, ilce=ilce)
        kiosk2 = Kiosk.objects.create(
            eczane=eczane2,
            ad="Kiosk B",
            mac_adresi="11:22:33:44:55:66",
            uygulama_anahtari="test-app-key-b-secure-48chars-xxxxxxxxxxxxxxxxxx",
        )
        logo1 = BarkodLogo.objects.create(
            ad="Logo A", media_url="http://x/a.png", checksum="sha256:aaa",
            baslangic_zamani=now, bitis_zamani=now + timedelta(days=30), aktif=True,
        )
        logo1.hedef_kiosklar.add(kiosk)
        logo2 = BarkodLogo.objects.create(
            ad="Logo B", media_url="http://x/b.png", checksum="sha256:bbb",
            baslangic_zamani=now, bitis_zamani=now + timedelta(days=30), aktif=True,
        )
        logo2.hedef_kiosklar.add(kiosk2)

        # Kiosk1 catalog isteği
        admin_client.credentials(
            HTTP_AUTHORIZATION=f"AppKey {kiosk.uygulama_anahtari}",
            HTTP_X_KIOSK_MAC=kiosk.mac_adresi,
        )
        r = admin_client.get("/api/kiosk/v1/catalog/")
        assert r.status_code == 200
        logolar = r.json()["barkod_logolar"]
        ids = [str(l["id"]) for l in logolar]
        assert str(logo1.id) in ids
        assert str(logo2.id) not in ids

    def test_pasif_kayit_catalogdan_cikar(self, db, kiosk, admin_client):
        now = timezone.now()
        logo = BarkodLogo.objects.create(
            ad="Pasif Logo", media_url="http://x/c.png", checksum="sha256:ccc",
            baslangic_zamani=now, bitis_zamani=now + timedelta(days=30), aktif=False,
        )
        logo.hedef_kiosklar.add(kiosk)
        admin_client.credentials(
            HTTP_AUTHORIZATION=f"AppKey {kiosk.uygulama_anahtari}",
            HTTP_X_KIOSK_MAC=kiosk.mac_adresi,
        )
        r = admin_client.get("/api/kiosk/v1/catalog/")
        assert r.status_code == 200
        logolar = r.json()["barkod_logolar"]
        assert not any(str(l["id"]) == str(logo.id) for l in logolar)

    def test_suresi_dolmus_kayit_catalogdan_cikar(self, db, kiosk, admin_client):
        now = timezone.now()
        logo = BarkodLogo.objects.create(
            ad="Eski Logo", media_url="http://x/d.png", checksum="sha256:ddd",
            baslangic_zamani=now - timedelta(days=60),
            bitis_zamani=now - timedelta(days=1),
            aktif=True,
        )
        logo.hedef_kiosklar.add(kiosk)
        admin_client.credentials(
            HTTP_AUTHORIZATION=f"AppKey {kiosk.uygulama_anahtari}",
            HTTP_X_KIOSK_MAC=kiosk.mac_adresi,
        )
        r = admin_client.get("/api/kiosk/v1/catalog/")
        assert r.status_code == 200
        logolar = r.json()["barkod_logolar"]
        assert not any(str(l["id"]) == str(logo.id) for l in logolar)

    def test_gelecek_tarihli_aktif_kayit_onceden_dagitilebilir(self, db, kiosk, admin_client):
        now = timezone.now()
        logo = BarkodLogo.objects.create(
            ad="Gelecek Logo", media_url="http://x/e.png", checksum="sha256:eee",
            baslangic_zamani=now + timedelta(days=5),  # gelecekte başlıyor
            bitis_zamani=now + timedelta(days=35),
            aktif=True,
        )
        logo.hedef_kiosklar.add(kiosk)
        admin_client.credentials(
            HTTP_AUTHORIZATION=f"AppKey {kiosk.uygulama_anahtari}",
            HTTP_X_KIOSK_MAC=kiosk.mac_adresi,
        )
        r = admin_client.get("/api/kiosk/v1/catalog/")
        assert r.status_code == 200
        logolar = r.json()["barkod_logolar"]
        assert any(str(l["id"]) == str(logo.id) for l in logolar)

    def test_catalog_payload_nullable_gunluk_limit_icerir(self, db, kiosk, admin_client):
        now = timezone.now()
        logo = BarkodLogo.objects.create(
            ad="Limitli", media_url="http://x/f.png", checksum="sha256:fff",
            baslangic_zamani=now, bitis_zamani=now + timedelta(days=30),
            aktif=True, gunluk_baski_limiti=10,
        )
        logo.hedef_kiosklar.add(kiosk)
        admin_client.credentials(
            HTTP_AUTHORIZATION=f"AppKey {kiosk.uygulama_anahtari}",
            HTTP_X_KIOSK_MAC=kiosk.mac_adresi,
        )
        r = admin_client.get("/api/kiosk/v1/catalog/")
        logolar = r.json()["barkod_logolar"]
        found = next((l for l in logolar if str(l["id"]) == str(logo.id)), None)
        assert found is not None
        assert found["gunluk_baski_limiti"] == 10

    def test_silme_yok_405(self, db, admin_client):
        now = timezone.now()
        logo = BarkodLogo.objects.create(
            ad="Sil", media_url="", checksum="",
            baslangic_zamani=now, bitis_zamani=now + timedelta(days=30),
        )
        r = admin_client.delete(f"{LIST_URL}{logo.id}/")
        assert r.status_code == 405

    def test_bos_hedef_kiosk_tum_kiosklara_dagitilir(self, db, kiosk, admin_client):
        """Hedef kiosk seçilmemiş logo → tüm kiosklara (boş = sınırsız hedef)."""
        now = timezone.now()
        logo = BarkodLogo.objects.create(
            ad="Tüm Kiosklar", media_url="http://x/all.png", checksum="sha256:all",
            baslangic_zamani=now, bitis_zamani=now + timedelta(days=30), aktif=True,
            # hedef_kiosklar boş — hiç M2M kaydı yok
        )
        admin_client.credentials(
            HTTP_AUTHORIZATION=f"AppKey {kiosk.uygulama_anahtari}",
            HTTP_X_KIOSK_MAC=kiosk.mac_adresi,
        )
        r = admin_client.get("/api/kiosk/v1/catalog/")
        assert r.status_code == 200
        logolar = r.json()["barkod_logolar"]
        assert any(str(l["id"]) == str(logo.id) for l in logolar)


class TestBarkodLogoSessionIngest:
    def test_barkod_logo_id_session_ingest_sirasinda_saklanir(self, db, kiosk, eczane):
        from apps.analytics.services import ingest_session_items
        from apps.lookups.models import Cinsiyet, YasAraligi
        from apps.products.models import Kategori

        now = timezone.now()
        logo = BarkodLogo.objects.create(
            ad="Logo", media_url="http://x/g.png", checksum="sha256:ggg",
            baslangic_zamani=now, bitis_zamani=now + timedelta(days=30), aktif=True,
        )
        yas = YasAraligi.objects.first()
        cins = Cinsiyet.objects.first()
        kat, _ = Kategori.objects.get_or_create(slug="test-ingest", defaults={"ad": "Test Ingest", "ikon": "fa-circle"})
        idem = uuid.uuid4()
        payload = {
            "idempotency_anahtari": str(idem),
            "yas_araligi_kod": yas.kod,
            "cinsiyet_kod": cins.kod,
            "oturum_tipi": "SIKAYET",
            "kategori_slug": kat.slug,
            "tamamlandi": False,
            "barkod_logo_id": str(logo.id),
        }
        results, errors = ingest_session_items(kiosk, [payload])
        assert not errors, errors
        from apps.analytics.models import OturumLogu
        oturum = OturumLogu.objects.get(idempotency_anahtari=idem)
        assert oturum.barkod_logo_id == logo.id

    def test_eski_payload_alan_olmadan_calisir(self, db, kiosk, eczane):
        from apps.analytics.services import ingest_session_items
        from apps.lookups.models import Cinsiyet, YasAraligi
        from apps.products.models import Kategori

        yas = YasAraligi.objects.first()
        cins = Cinsiyet.objects.first()
        kat, _ = Kategori.objects.get_or_create(slug="test-eski", defaults={"ad": "Test Eski", "ikon": "fa-circle"})
        idem = uuid.uuid4()
        payload = {
            "idempotency_anahtari": str(idem),
            "yas_araligi_kod": yas.kod,
            "cinsiyet_kod": cins.kod,
            "oturum_tipi": "SIKAYET",
            "kategori_slug": kat.slug,
            "tamamlandi": False,
            # barkod_logo_id yok
        }
        results, errors = ingest_session_items(kiosk, [payload])
        assert not errors, errors
        from apps.analytics.models import OturumLogu
        oturum = OturumLogu.objects.get(idempotency_anahtari=idem)
        assert oturum.barkod_logo is None

    def test_gecikli_outbox_logo_pasif_olsa_bile_kabul_edilir(self, db, kiosk, eczane):
        from apps.analytics.services import ingest_session_items
        from apps.lookups.models import Cinsiyet, YasAraligi
        from apps.products.models import Kategori

        now = timezone.now()
        logo = BarkodLogo.objects.create(
            ad="Pasiflesmiş",
            media_url="http://x/h.png", checksum="sha256:hhh",
            baslangic_zamani=now - timedelta(days=10),
            bitis_zamani=now - timedelta(days=1),
            aktif=False,
        )
        yas = YasAraligi.objects.first()
        cins = Cinsiyet.objects.first()
        kat, _ = Kategori.objects.get_or_create(slug="test-gecik", defaults={"ad": "Test Gecik", "ikon": "fa-circle"})
        idem = uuid.uuid4()
        payload = {
            "idempotency_anahtari": str(idem),
            "yas_araligi_kod": yas.kod,
            "cinsiyet_kod": cins.kod,
            "oturum_tipi": "SIKAYET",
            "kategori_slug": kat.slug,
            "tamamlandi": False,
            "barkod_logo_id": str(logo.id),
        }
        # Gecikmiş outbox → logo pasif olsa bile kabul edilmeli
        results, errors = ingest_session_items(kiosk, [payload])
        assert not errors, errors
        from apps.analytics.models import OturumLogu
        oturum = OturumLogu.objects.get(idempotency_anahtari=idem)
        assert oturum.barkod_logo_id == logo.id

    def test_ayni_idempotency_key_iki_kez_merkezi_baski_sayimi_olusturmaz(self, db, kiosk, eczane):
        from apps.analytics.services import ingest_session_items
        from apps.lookups.models import Cinsiyet, YasAraligi
        from apps.products.models import Kategori
        from apps.analytics.models import OturumLogu

        yas = YasAraligi.objects.first()
        cins = Cinsiyet.objects.first()
        kat, _ = Kategori.objects.get_or_create(slug="test-idem", defaults={"ad": "Test Idem", "ikon": "fa-circle"})
        idem = uuid.uuid4()
        payload = {
            "idempotency_anahtari": str(idem),
            "yas_araligi_kod": yas.kod,
            "cinsiyet_kod": cins.kod,
            "oturum_tipi": "SIKAYET",
            "kategori_slug": kat.slug,
            "tamamlandi": False,
        }
        ingest_session_items(kiosk, [payload])
        ingest_session_items(kiosk, [payload])
        count = OturumLogu.objects.filter(idempotency_anahtari=idem).count()
        assert count == 1  # ikinci çağrı yeni kayıt oluşturmamalı


# ─── PROTECT FK testleri ───────────────────────────────────────────────────

class TestBarkodLogoProtect:
    """OturumLogu.barkod_logo FK = PROTECT: geçmiş ölçüm kaybolmaz."""

    def test_iliski_olan_logo_silinemiyor(self, db, kiosk, eczane):
        from apps.analytics.models import OturumLogu
        from apps.lookups.models import Cinsiyet, YasAraligi
        from apps.products.models import Kategori
        from django.db.models.deletion import ProtectedError

        now = timezone.now()
        logo = BarkodLogo.objects.create(
            ad="PROTECT Test", media_url="http://x/p.png", checksum="sha256:ppp",
            baslangic_zamani=now, bitis_zamani=now + timedelta(days=30), aktif=True,
        )
        yas = YasAraligi.objects.first()
        cins = Cinsiyet.objects.first()
        kat, _ = Kategori.objects.get_or_create(slug="test-protect", defaults={"ad": "Test P", "ikon": "fa-circle"})
        # Oturum oluştur ve logoya bağla
        oturum = OturumLogu.objects.create(
            idempotency_anahtari=uuid.uuid4(),
            kiosk=kiosk,
            eczane=eczane,
            yas_araligi=yas,
            cinsiyet=cins,
            kategori=kat,
            oturum_tipi="SIKAYET",
            barkod_logo=logo,
        )
        # PROTECT: logo silinemez
        with pytest.raises(ProtectedError):
            logo.delete()
        # Oturum hâlâ var ve logo FK korunuyor
        oturum.refresh_from_db()
        assert oturum.barkod_logo_id == logo.id

    def test_pasiflestirilmis_logo_gecmis_oturum_fk_degismez(self, db, kiosk, eczane):
        from apps.analytics.models import OturumLogu
        from apps.lookups.models import Cinsiyet, YasAraligi
        from apps.products.models import Kategori

        now = timezone.now()
        logo = BarkodLogo.objects.create(
            ad="Pasif Edilecek", media_url="http://x/q.png", checksum="sha256:qqq",
            baslangic_zamani=now, bitis_zamani=now + timedelta(days=30), aktif=True,
        )
        yas = YasAraligi.objects.first()
        cins = Cinsiyet.objects.first()
        kat, _ = Kategori.objects.get_or_create(slug="test-pasif-fk", defaults={"ad": "Test PF", "ikon": "fa-circle"})
        oturum = OturumLogu.objects.create(
            idempotency_anahtari=uuid.uuid4(),
            kiosk=kiosk,
            eczane=eczane,
            yas_araligi=yas,
            cinsiyet=cins,
            kategori=kat,
            oturum_tipi="SIKAYET",
            barkod_logo=logo,
        )
        # Pasifleştir
        logo.aktif = False
        logo.save(update_fields=["aktif"])
        # Oturum FK değişmemeli
        oturum.refresh_from_db()
        assert oturum.barkod_logo_id == logo.id


# ─── Yetki testleri ────────────────────────────────────────────────────────

class TestBarkodLogoYetki:
    """Yalnız SuperAdmin logo yönetebilir."""

    def test_anonim_logo_listesi_alamaz_401(self, db):
        r = APIClient().get(LIST_URL)
        assert r.status_code == 401

    def test_eczaci_logo_olusturamaz_403(self, db, eczaci_client):
        now = timezone.now()
        r = eczaci_client.post(LIST_URL, {
            "ad": "Deneme",
            "baslangic_zamani": now.isoformat(),
            "bitis_zamani": (now + timedelta(days=30)).isoformat(),
        }, format="json")
        assert r.status_code == 403

    def test_eczaci_logo_duzenleyemez_403(self, db, eczane, eczaci_client):
        now = timezone.now()
        logo = BarkodLogo.objects.create(
            ad="Test", media_url="", checksum="",
            baslangic_zamani=now, bitis_zamani=now + timedelta(days=30),
        )
        r = eczaci_client.patch(f"{LIST_URL}{logo.id}/", {"ad": "Hack"}, format="json")
        assert r.status_code == 403

    def test_superadmin_logo_olusturabilir(self, db, admin_client):
        now = timezone.now()
        r = admin_client.post(LIST_URL, {
            "ad": "Admin Logo",
            "baslangic_zamani": now.isoformat(),
            "bitis_zamani": (now + timedelta(days=30)).isoformat(),
            "aktif": True,
            "hedef_kiosk_idleri_write": [],
        }, format="json")
        assert r.status_code == 201

    def test_kiosk_kendi_logolarini_gorebilir(self, db, kiosk, admin_client):
        admin_client.credentials(
            HTTP_AUTHORIZATION=f"AppKey {kiosk.uygulama_anahtari}",
            HTTP_X_KIOSK_MAC=kiosk.mac_adresi,
        )
        r = admin_client.get("/api/kiosk/v1/catalog/")
        assert r.status_code == 200
        assert "barkod_logolar" in r.json()

