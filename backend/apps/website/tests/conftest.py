"""apps.website test fixture'ları."""
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.users.models import Kullanici


@pytest.fixture(autouse=True)
def _temiz_cache():
    # Throttle sayaçları (LocMemCache) testler arasında taşınmasın.
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _medya_kok(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.WEBSITE_MEDIA_LOCAL = True
    settings.SITE_REVALIDATE_URLS = []
    settings.SITE_REVALIDATE_HEADLESS_HOST = ""
    # pytest-django DEBUG=False çalışır; üretim kuralı gereği geliştirme token'ı reddedilir.
    settings.WEBSITE_SERVER_TOKEN = "test-website-server-token-0123456789abcdef"
    return settings.MEDIA_ROOT


@pytest.fixture
def editor(db):
    return Kullanici.objects.create_user(
        username="editor", password="Str0ngPass!", rol=Kullanici.Rol.EDITOR, first_name="Ece", last_name="Editör"
    )


def _client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def editor_client(editor):
    return _client(editor)


@pytest.fixture
def superadmin_client(superadmin):
    return _client(superadmin)


@pytest.fixture
def eczaci_api(eczaci):
    return _client(eczaci)


@pytest.fixture
def site_istemci(settings):
    """Site sunucusu (Next.js): public/önizleme uçlarına X-Website-Token ile gelir."""
    client = APIClient()
    client.credentials(HTTP_X_WEBSITE_TOKEN=settings.WEBSITE_SERVER_TOKEN)
    return client


@pytest.fixture
def dis_istemci():
    """Token'sız dış istemci (tarayıcı / internet) — public uçlara erişememeli."""
    return APIClient()


def ornek_hero(**ek):
    veri = {
        "baslik": "Bekleme süresini değere dönüştürün",
        "vurgu": "değere",
        "butonlar": [{"etiket": "Pilot", "href": "/#pilot", "stil": "birincil"}],
    }
    veri.update(ek)
    return veri


@pytest.fixture
def sayfa_olustur(db):
    """Servis katmanıyla sayfa + taslak bloklar (+ opsiyonel yayın) oluşturur."""
    from apps.core.uow import save_new
    from apps.website.blocks import bloklari_dogrula
    from apps.website.models import Sayfa
    from apps.website.services.sayfa import bloklari_kaydet, sayfa_yayinla, sayfa_yeniden_yukle

    def _olustur(slug="test-sayfa", bloklar=None, yayinla=False, baslik="Test Sayfa"):
        sayfa = save_new(Sayfa(slug=slug, baslik=baslik))
        girdi = bloklar if bloklar is not None else [{"tip": "hero", "veri": ornek_hero(), "anchor_id": "ust"}]
        temiz, hatalar = bloklari_dogrula(girdi)
        assert not hatalar, hatalar
        bloklari_kaydet(sayfa, temiz, user=None, surum=sayfa.surum)
        sayfa = sayfa_yeniden_yukle(sayfa.pk)
        if yayinla:
            sayfa_yayinla(sayfa, user=None, revalidate_et=False)
            sayfa = sayfa_yeniden_yukle(sayfa.pk)
        return sayfa

    return _olustur


@pytest.fixture
def png_dosyasi():
    """Pillow ile üretilmiş gerçek bir PNG (SimpleUploadedFile)."""
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    def _uret(ad="gorsel.png", boyut=(32, 16), content_type="image/png"):
        tampon = io.BytesIO()
        Image.new("RGB", boyut, (237, 28, 36)).save(tampon, format="PNG")
        return SimpleUploadedFile(ad, tampon.getvalue(), content_type=content_type)

    return _uret


@pytest.fixture
def medya_olustur(db):
    from apps.core.uow import save_new
    from apps.website.models import WebsiteMedya

    def _olustur(**ek):
        alanlar = {
            "object_key": f"website/2026/11/test{WebsiteMedya.objects.count()}.png",
            "dosya_adi": "test.png",
            "mime": "image/png",
            "boyut": 100,
            "genislik": 10,
            "yukseklik": 5,
            "alt": "Test görseli",
        }
        alanlar.update(ek)
        return save_new(WebsiteMedya(**alanlar))

    return _olustur
