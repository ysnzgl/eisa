"""Yeni testler: Backend QR üretimi, session normalizasyonu, şikâyet/özel danışmanlık akışı.

Kapsam:
  - Backend QR generation (random, format, uniqueness)
  - Forced collision retry (mock ile)
  - Idempotency: aynı key → aynı QR
  - SIKAYET session normalization (OturumCevap, OturumOnerilenEtkenMadde)
  - Soru-cevap uyumsuzluğu → 400 + rollback (SIKAYET için)
  - Child kayıt duplicate koruması (idempotency retry)
  - JSON backfill (management command)
  - OZEL_DANISMANLIK session kabulü (id ve slug ile)
  - OZEL_DANISMANLIK validasyon: kategori_slug yasak, cevap yasak, oneri yasak
  - SIKAYET validasyon: danisma kategorisi yasak
  - Danışmanlık central QR response
  - Farklı eczane QR erişimi 403
  - QR idempotency network retry senaryosu
"""
from __future__ import annotations

import re
import uuid
from unittest.mock import patch

import pytest
from django.db import IntegrityError

from apps.analytics.models import OturumCevap, OturumLogu, OturumOnerilenEtkenMadde
from apps.analytics.services import SessionValidationError, generate_qr_candidate, ingest_session_items
from apps.lookups.models import Cinsiyet, Il, Ilce, YasAraligi
from apps.lookups.seed import seed_lookups
from apps.pharmacies.models import Eczane, Kiosk
from apps.products.models import Cevap, Danisma, EtkenMadde, Kategori, Soru

QR_RE = re.compile(r'^[A-Z0-9]{8}$')
SESSIONS_URL = "/api/kiosk/v1/sessions/"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def eczane(db):
    seed_lookups()
    il, _ = Il.objects.get_or_create(ad="Test Il")
    ilce, _ = Ilce.objects.get_or_create(il=il, ad="Test Ilce")
    return Eczane.objects.create(ad="Test Eczanesi Norm", il=il, ilce=ilce)


@pytest.fixture
def kiosk_obj(db, eczane):
    return Kiosk.objects.create(
        eczane=eczane,
        mac_adresi="AA:BB:CC:11:22:33",
        uygulama_anahtari="test-norm-key-48chars-xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )


@pytest.fixture
def kiosk_client_norm(api_client, kiosk_obj):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"AppKey {kiosk_obj.uygulama_anahtari}",
        HTTP_X_KIOSK_MAC=kiosk_obj.mac_adresi,
    )
    return api_client


@pytest.fixture
def kategori(db):
    return Kategori.objects.get_or_create(ad="Test Kategori", slug="test-norm")[0]


@pytest.fixture
def danisma_kategori(db):
    return Danisma.objects.get_or_create(ad="Test Danisma", slug="test-danisma")[0]


@pytest.fixture
def soru_cevap(db, kategori):
    soru = Soru.objects.create(kategori=kategori, metin="Test soru?", sira=1)
    cevap = Cevap.objects.create(soru=soru, metin="Evet", agirlik=10)
    return soru, cevap


@pytest.fixture
def diger_soru_cevap(db, kategori):
    """Farklı bir soruya ait cevap (uyumsuzluk testi için)."""
    diger_soru = Soru.objects.create(kategori=kategori, metin="Diger soru?", sira=2)
    diger_cevap = Cevap.objects.create(soru=diger_soru, metin="Hayir", agirlik=5)
    return diger_soru, diger_cevap


@pytest.fixture
def etken_madde(db):
    return EtkenMadde.objects.get_or_create(ad="Test Etken Madde")[0]


def _base_item(kategori, *, tipi="SIKAYET", danisma_slug=None, danisma_id=None):
    base = {
        "idempotency_anahtari": str(uuid.uuid4()),
        "yas_araligi_kod": YasAraligi.objects.first().kod,
        "cinsiyet_kod": Cinsiyet.objects.first().kod,
        "oturum_tipi": tipi,
        "hassas_akis": False,
        "cevaplar": {},
        "onerilen_etken_maddeler": [],
        "tamamlandi": True,
    }
    if tipi == "SIKAYET":
        base["kategori_slug"] = kategori.slug
    if danisma_slug:
        base["danisma_kategorisi_slug"] = danisma_slug
    if danisma_id:
        base["danisma_kategorisi_id"] = danisma_id
    return base


# ── QR Generation ─────────────────────────────────────────────────────────────

class TestQRFormat:
    def test_candidate_format(self):
        for _ in range(50):
            qr = generate_qr_candidate()
            assert QR_RE.match(qr), f"Invalid QR: {qr!r}"

    def test_candidate_length(self):
        assert len(generate_qr_candidate()) == 8


class TestSessionQRGeneration:
    def test_session_gets_backend_qr(self, db, kiosk_obj, kategori):
        item = _base_item(kategori)
        results, errors = ingest_session_items(kiosk_obj, [item])

        assert not errors
        assert len(results) == 1
        r = results[0]
        assert r["status"] == "created"
        assert QR_RE.match(r["qr_kodu"]), f"Invalid QR: {r['qr_kodu']!r}"

        oturum = OturumLogu.objects.get(idempotency_anahtari=item["idempotency_anahtari"])
        assert oturum.qr_kodu == r["qr_kodu"]

    def test_idempotency_same_qr_returned(self, db, kiosk_obj, kategori):
        """Same idempotency key → same QR, no duplicate record.

        Bu test network retry senaryosunu da kapsar:
        Backend session ve QR oluşturur → ilk response kaybolur →
        edge aynı idempotency key ile tekrar gönderir →
        backend mevcut session ve aynı QR'ı döndürür (ikinci oturum oluşmaz).
        """
        item = _base_item(kategori)
        results1, _ = ingest_session_items(kiosk_obj, [item])
        results2, _ = ingest_session_items(kiosk_obj, [item])  # simulates retry

        assert results1[0]["qr_kodu"] == results2[0]["qr_kodu"]
        assert results2[0]["status"] == "existing"
        assert OturumLogu.objects.filter(
            idempotency_anahtari=item["idempotency_anahtari"]
        ).count() == 1

    def test_forced_collision_retry(self, db, kiosk_obj, kategori):
        """First QR candidate causes IntegrityError; second succeeds."""
        item = _base_item(kategori)
        original_generate = generate_qr_candidate

        age = YasAraligi.objects.first()
        cins = Cinsiyet.objects.first()
        OturumLogu.objects.create(
            kiosk=kiosk_obj, yas_araligi=age, cinsiyet=cins,
            kategori=kategori, qr_kodu="AAAAAAAA", tamamlandi=True,
        )

        attempts = [0]

        def patched_generate():
            attempts[0] += 1
            if attempts[0] == 1:
                return "AAAAAAAA"  # collision
            return original_generate()

        with patch("apps.analytics.services.generate_qr_candidate", side_effect=patched_generate):
            results, errors = ingest_session_items(kiosk_obj, [item])

        assert not errors
        assert results[0]["status"] == "created"
        assert results[0]["qr_kodu"] != "AAAAAAAA"
        assert attempts[0] >= 2

    def test_max_retry_exceeded_returns_error(self, db, kiosk_obj, kategori):
        """When all retry attempts produce a duplicate, returns error."""
        item = _base_item(kategori)

        age = YasAraligi.objects.first()
        cins = Cinsiyet.objects.first()
        OturumLogu.objects.create(
            kiosk=kiosk_obj, yas_araligi=age, cinsiyet=cins,
            kategori=kategori, qr_kodu="ZZZZZZZZ", tamamlandi=True,
        )

        with patch("apps.analytics.services.generate_qr_candidate", return_value="ZZZZZZZZ"):
            results, errors = ingest_session_items(kiosk_obj, [item])

        assert not results
        assert len(errors) == 1
        assert "qr_kodu" in errors[0]["errors"]


# ── SIKAYET Session Normalization ─────────────────────────────────────────────

class TestSikayetSession:
    def test_sikayet_accepted(self, db, kiosk_obj, kategori):
        item = _base_item(kategori)
        results, errors = ingest_session_items(kiosk_obj, [item])

        assert not errors
        oturum = OturumLogu.objects.get(idempotency_anahtari=item["idempotency_anahtari"])
        assert oturum.oturum_tipi == "SIKAYET"
        assert oturum.kategori == kategori
        assert oturum.danisma_kategorisi is None

    def test_sikayet_requires_kategori_slug(self, db, kiosk_obj, kategori):
        item = _base_item(kategori)
        del item["kategori_slug"]

        results, errors = ingest_session_items(kiosk_obj, [item])

        assert not results
        assert "kategori_slug" in errors[0]["errors"]

    def test_sikayet_rejects_danisma_kategorisi(self, db, kiosk_obj, kategori, danisma_kategori):
        """SIKAYET oturumunda özel danışmanlık kategorisi olamaz."""
        item = _base_item(kategori)
        item["danisma_kategorisi_slug"] = danisma_kategori.slug

        results, errors = ingest_session_items(kiosk_obj, [item])

        assert not results
        assert "danisma_kategorisi_id" in errors[0]["errors"]

    def test_sikayet_child_records_created(self, db, kiosk_obj, kategori, soru_cevap, etken_madde):
        soru, cevap = soru_cevap
        item = _base_item(kategori)
        item["cevaplar"] = {str(soru.id): cevap.id}
        item["onerilen_etken_maddeler"] = [etken_madde.id]

        results, errors = ingest_session_items(kiosk_obj, [item])

        assert not errors
        oturum = OturumLogu.objects.get(idempotency_anahtari=item["idempotency_anahtari"])

        cevap_row = OturumCevap.objects.get(oturum=oturum, soru=soru)
        assert cevap_row.cevap == cevap
        assert cevap_row.soru_metni_snapshot == soru.metin
        assert cevap_row.cevap_metni_snapshot == cevap.metin

        oem = OturumOnerilenEtkenMadde.objects.get(oturum=oturum, etken_madde=etken_madde)
        assert oem.etken_madde_adi_snapshot == etken_madde.ad

    def test_sikayet_cevap_soru_mismatch_returns_400_and_rollbacks(
        self, db, kiosk_obj, kategori, soru_cevap, diger_soru_cevap
    ):
        """SIKAYET'te soru-cevap uyumsuzluğu → 400 + tam transaction rollback.

        Parent OturumLogu ve tüm OturumCevap kayıtları rollback olmalı.
        """
        soru, _ = soru_cevap
        diger_soru, diger_cevap = diger_soru_cevap
        item = _base_item(kategori)
        # soru.id → diger_cevap.id (mismatch: diger_cevap belongs to diger_soru)
        item["cevaplar"] = {str(soru.id): diger_cevap.id}

        results, errors = ingest_session_items(kiosk_obj, [item])

        # Error returned, no results
        assert not results
        assert len(errors) == 1
        assert "cevaplar" in errors[0]["errors"]
        # Parent OturumLogu must NOT exist (full rollback)
        assert not OturumLogu.objects.filter(idempotency_anahtari=item["idempotency_anahtari"]).exists()
        # No child records either
        assert OturumCevap.objects.count() == 0

    def test_sikayet_unknown_soru_returns_400(self, db, kiosk_obj, kategori):
        """SIKAYET'te olmayan soru_id → 400."""
        item = _base_item(kategori)
        item["cevaplar"] = {"99999": "1"}

        results, errors = ingest_session_items(kiosk_obj, [item])

        assert not results
        assert "cevaplar" in errors[0]["errors"]
        assert not OturumLogu.objects.filter(idempotency_anahtari=item["idempotency_anahtari"]).exists()

    def test_sikayet_idempotency_no_child_duplicates(self, db, kiosk_obj, kategori, soru_cevap):
        soru, cevap = soru_cevap
        item = _base_item(kategori)
        item["cevaplar"] = {str(soru.id): cevap.id}

        ingest_session_items(kiosk_obj, [item])
        ingest_session_items(kiosk_obj, [item])  # retry

        oturum = OturumLogu.objects.get(idempotency_anahtari=item["idempotency_anahtari"])
        assert OturumCevap.objects.filter(oturum=oturum, soru=soru).count() == 1

    def test_string_ingredient_stored_as_snapshot(self, db, kiosk_obj, kategori):
        item = _base_item(kategori)
        item["onerilen_etken_maddeler"] = ["Bilinmeyen Madde"]

        results, errors = ingest_session_items(kiosk_obj, [item])

        assert not errors
        oturum = OturumLogu.objects.get(idempotency_anahtari=item["idempotency_anahtari"])
        assert OturumOnerilenEtkenMadde.objects.filter(
            oturum=oturum, etken_madde__isnull=True,
            etken_madde_adi_snapshot="Bilinmeyen Madde"
        ).exists()


# ── OZEL_DANISMANLIK Session ──────────────────────────────────────────────────

class TestOzelDanismanlikSession:
    def test_ozel_danismanlik_accepted_with_slug(self, db, kiosk_obj, danisma_kategori, kategori):
        item = _base_item(kategori, tipi="OZEL_DANISMANLIK", danisma_slug=danisma_kategori.slug)

        results, errors = ingest_session_items(kiosk_obj, [item])

        assert not errors
        oturum = OturumLogu.objects.get(idempotency_anahtari=item["idempotency_anahtari"])
        assert oturum.oturum_tipi == "OZEL_DANISMANLIK"
        assert oturum.danisma_kategorisi == danisma_kategori
        assert oturum.kategori is None

    def test_ozel_danismanlik_accepted_with_id(self, db, kiosk_obj, danisma_kategori, kategori):
        """danisma_kategorisi_id (integer) ile de kabul edilmeli."""
        item = _base_item(kategori, tipi="OZEL_DANISMANLIK", danisma_id=danisma_kategori.id)

        results, errors = ingest_session_items(kiosk_obj, [item])

        assert not errors
        oturum = OturumLogu.objects.get(idempotency_anahtari=item["idempotency_anahtari"])
        assert oturum.danisma_kategorisi == danisma_kategori

    def test_ozel_danismanlik_requires_danisma_kategori(self, db, kiosk_obj, kategori):
        """danisma_kategorisi_slug / id ikisi de yoksa 400."""
        item = _base_item(kategori, tipi="OZEL_DANISMANLIK")

        results, errors = ingest_session_items(kiosk_obj, [item])

        assert not results
        assert "danisma_kategorisi_slug" in errors[0]["errors"]

    def test_ozel_danismanlik_rejects_kategori_slug(self, db, kiosk_obj, kategori, danisma_kategori):
        """OZEL_DANISMANLIK'ta şikâyet kategorisi olamaz."""
        item = _base_item(kategori, tipi="OZEL_DANISMANLIK", danisma_slug=danisma_kategori.slug)
        item["kategori_slug"] = kategori.slug  # explicitly set

        results, errors = ingest_session_items(kiosk_obj, [item])

        assert not results
        assert "kategori_slug" in errors[0]["errors"]

    def test_ozel_danismanlik_rejects_cevaplar(self, db, kiosk_obj, kategori, danisma_kategori, soru_cevap):
        """OZEL_DANISMANLIK'ta cevap bulunmamalı."""
        soru, cevap = soru_cevap
        item = _base_item(kategori, tipi="OZEL_DANISMANLIK", danisma_slug=danisma_kategori.slug)
        item["cevaplar"] = {str(soru.id): cevap.id}

        results, errors = ingest_session_items(kiosk_obj, [item])

        assert not results
        assert "cevaplar" in errors[0]["errors"]

    def test_ozel_danismanlik_rejects_onerilen(self, db, kiosk_obj, kategori, danisma_kategori, etken_madde):
        """OZEL_DANISMANLIK'ta etken madde önerisi bulunmamalı."""
        item = _base_item(kategori, tipi="OZEL_DANISMANLIK", danisma_slug=danisma_kategori.slug)
        item["onerilen_etken_maddeler"] = [etken_madde.id]

        results, errors = ingest_session_items(kiosk_obj, [item])

        assert not results
        assert "onerilen_etken_maddeler" in errors[0]["errors"]

    def test_ozel_danismanlik_returns_qr(self, db, kiosk_obj, danisma_kategori, kategori):
        item = _base_item(kategori, tipi="OZEL_DANISMANLIK", danisma_slug=danisma_kategori.slug)

        results, errors = ingest_session_items(kiosk_obj, [item])

        assert not errors
        assert QR_RE.match(results[0]["qr_kodu"])


# ── API Endpoint Integration ───────────────────────────────────────────────────

class TestSessionsEndpoint:
    def test_session_response_has_results_format(self, db, kiosk_client_norm, kiosk_obj, kategori):
        item = _base_item(kategori)
        res = kiosk_client_norm.post(
            SESSIONS_URL, {"items": [item]}, format="json"
        )
        assert res.status_code == 200
        data = res.json()
        assert "results" in data
        assert "errors" in data
        assert len(data["results"]) == 1
        r = data["results"][0]
        assert r["status"] == "created"
        assert QR_RE.match(r["qr_kodu"])

    def test_different_pharmacy_qr_returns_403(self, db):
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken

        seed_lookups()
        il, _ = Il.objects.get_or_create(ad="Test Il2")
        ilce, _ = Ilce.objects.get_or_create(il=il, ad="Test Ilce2")
        other_eczane = Eczane.objects.create(ad="Diger Eczane Norm", il=il, ilce=ilce)
        other_kiosk = Kiosk.objects.create(
            eczane=other_eczane,
            mac_adresi="FF:EE:DD:CC:BB:AA",
            uygulama_anahtari="other-norm-key-48chars-xxxxxxxxxxxxxxxxxxxxxx",
        )
        # Create session on other_kiosk
        age = YasAraligi.objects.first()
        cins = Cinsiyet.objects.first()
        kat = Kategori.objects.get_or_create(ad="Test Norm K2", slug="test-norm-k2")[0]
        oturum = OturumLogu.objects.create(
            kiosk=other_kiosk,
            yas_araligi=age,
            cinsiyet=cins,
            kategori=kat,
            qr_kodu="Z9X8W7V6",
            tamamlandi=True,
        )

        # Login as pharmacist of first pharmacy (different eczane)
        Kullanici = get_user_model()
        eczane1 = Eczane.objects.exclude(pk=other_eczane.pk).first()
        if not eczane1:
            eczane1 = Eczane.objects.create(ad="Eczane1 Norm", il=il, ilce=ilce)
        pharmacist = Kullanici.objects.create_user(
            username="pharm_norm_cross", password="Str0ngPass!",
            rol="pharmacist", eczane=eczane1,
        )
        client = APIClient()
        refresh = RefreshToken.for_user(pharmacist)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        res = client.get("/api/analytics/sessions/", {"qr_kodu": "Z9X8W7V6"})
        assert res.status_code == 403


# ── JSON Backfill ──────────────────────────────────────────────────────────────

class TestBackfillCommand:
    def test_backfill_creates_child_records_from_json(self, db, kiosk_obj, kategori):
        from django.core.management import call_command
        from io import StringIO

        soru = Soru.objects.create(kategori=kategori, metin="Backfill soru?", sira=99)
        cevap = Cevap.objects.create(soru=soru, metin="Evet", agirlik=1)
        em = EtkenMadde.objects.get_or_create(ad="Backfill Madde")[0]

        age = YasAraligi.objects.first()
        cins = Cinsiyet.objects.first()
        # Create legacy session with JSON only (no child records)
        oturum = OturumLogu.objects.create(
            kiosk=kiosk_obj,
            yas_araligi=age,
            cinsiyet=cins,
            kategori=kategori,
            qr_kodu="BF123456",
            tamamlandi=True,
            cevaplar={str(soru.id): cevap.id},
            onerilen_etken_maddeler=[em.id],
        )
        assert OturumCevap.objects.filter(oturum=oturum).count() == 0

        out = StringIO()
        call_command("backfill_session_normalization", stdout=out)

        assert OturumCevap.objects.filter(oturum=oturum, soru=soru).exists()
        assert OturumOnerilenEtkenMadde.objects.filter(oturum=oturum, etken_madde=em).exists()

    def test_backfill_idempotent(self, db, kiosk_obj, kategori):
        from django.core.management import call_command
        from io import StringIO

        age = YasAraligi.objects.first()
        cins = Cinsiyet.objects.first()
        oturum = OturumLogu.objects.create(
            kiosk=kiosk_obj,
            yas_araligi=age,
            cinsiyet=cins,
            kategori=kategori,
            qr_kodu="IDEM5678",
            tamamlandi=True,
            cevaplar={"999": "888"},  # non-existent IDs
        )

        call_command("backfill_session_normalization", stdout=StringIO())
        call_command("backfill_session_normalization", stdout=StringIO())  # second run

        # Should not duplicate child records
        assert OturumCevap.objects.filter(oturum=oturum).count() <= 1

    def test_dry_run_no_records_created(self, db, kiosk_obj, kategori):
        from django.core.management import call_command
        from io import StringIO

        soru = Soru.objects.create(kategori=kategori, metin="Dry run soru?", sira=100)
        cevap = Cevap.objects.create(soru=soru, metin="Evet", agirlik=1)

        age = YasAraligi.objects.first()
        cins = Cinsiyet.objects.first()
        oturum = OturumLogu.objects.create(
            kiosk=kiosk_obj,
            yas_araligi=age,
            cinsiyet=cins,
            kategori=kategori,
            qr_kodu="DRYRUN78",
            tamamlandi=True,
            cevaplar={str(soru.id): cevap.id},
        )

        call_command("backfill_session_normalization", dry_run=True, stdout=StringIO())

        assert OturumCevap.objects.filter(oturum=oturum).count() == 0


# ── Kiosk Binary Format Contract (SIKAYET vs OZEL_DANISMANLIK) ────────────────
#
# Amaç: Kiosk UI ikili ("Y"/"N") cevap formatı ile şikâyet akışını test eder.
#
# Kök neden (tespit edilen):
#   - UI cevaplar payload'ını { str(soru.id): "Y" } formatında gönderir.
#   - Backend services.py _create_child_records() eskiden "Y"/"N" string değerleri
#     için SessionValidationError fırlatıyordu (int("Y") → ValueError → strict raise).
#   - OZEL_DANISMANLIK cevaplar boş gönderdiği için sorun yoktu.
#   - Düzeltme: "Y"/"N" → cevap_metin_snapshot olarak kaydedilir, cevap FK null kalır.

class TestKioskBinaryFormatContract:

    def test_sikayet_binary_yn_cevaplar_accepted(self, db, kiosk_obj, kategori, soru_cevap):
        """SIKAYET — kiosk binary { str(soru_id): "Y"/"N" } format kabul edilmeli.

        Bu test kiosk UI'ın gönderdiği gerçek formatı simüle eder.
        cevap FK null kalır; string snapshot kaydedilir.
        """
        soru, _ = soru_cevap
        item = {
            "idempotency_anahtari": str(uuid.uuid4()),
            "yas_araligi_kod": YasAraligi.objects.first().kod,
            "cinsiyet_kod": Cinsiyet.objects.first().kod,
            "oturum_tipi": "SIKAYET",
            "kategori_slug": kategori.slug,
            "hassas_akis": False,
            "cevaplar": {str(soru.id): "Y"},  # kiosk binary format
            "onerilen_etken_maddeler": ["Melatonin", "Valerian"],  # string names
            "tamamlandi": True,
        }

        results, errors = ingest_session_items(kiosk_obj, [item])

        # Hata olmamalı
        assert not errors, f"Beklenmeyen errors: {errors}"
        assert len(results) == 1
        assert results[0]["status"] == "created"
        assert QR_RE.match(results[0]["qr_kodu"])

        oturum = OturumLogu.objects.get(idempotency_anahtari=item["idempotency_anahtari"])
        # OturumCevap oluşturulmuş olmalı — cevap FK null, snapshot insan-okunur format
        cevap_row = OturumCevap.objects.get(oturum=oturum, soru=soru)
        assert cevap_row.cevap is None  # FK null (binary değer, cevap nesnesi değil)
        assert cevap_row.cevap_metni_snapshot == "Evet"   # insan-okunur; 'Y' değil
        assert cevap_row.cevap_degeri_snapshot == "Y"     # raw değer korunur

        # String etken madde adları snapshot olarak kaydedilmeli (en az biri)
        snaps = list(OturumOnerilenEtkenMadde.objects.filter(oturum=oturum)
                     .values_list("etken_madde_adi_snapshot", flat=True))
        assert len(snaps) >= 1
        assert "Melatonin" in snaps

    def test_sikayet_binary_n_cevap_accepted(self, db, kiosk_obj, kategori, soru_cevap):
        """SIKAYET — "N" (Hayır) binary değeri de tolere edilmeli."""
        soru, _ = soru_cevap
        item = {
            "idempotency_anahtari": str(uuid.uuid4()),
            "yas_araligi_kod": YasAraligi.objects.first().kod,
            "cinsiyet_kod": Cinsiyet.objects.first().kod,
            "oturum_tipi": "SIKAYET",
            "kategori_slug": kategori.slug,
            "hassas_akis": False,
            "cevaplar": {str(soru.id): "N"},
            "onerilen_etken_maddeler": [],
            "tamamlandi": True,
        }

        results, errors = ingest_session_items(kiosk_obj, [item])

        assert not errors
        oturum = OturumLogu.objects.get(idempotency_anahtari=item["idempotency_anahtari"])
        cevap_row = OturumCevap.objects.get(oturum=oturum, soru=soru)
        assert cevap_row.cevap_metni_snapshot == "Hay\u0131r"  # insan-okunur
        assert cevap_row.cevap_degeri_snapshot == "N"         # raw korunur

    def test_sikayet_multiple_binary_answers_no_merge(self, db, kiosk_obj, kategori):
        """Birden fazla Y/N cevapı ayrı OturumCevap kayıtı oluşturmalı — birleşmemeli."""
        s1 = Soru.objects.create(kategori=kategori, metin="Soru A?", sira=10)
        s2 = Soru.objects.create(kategori=kategori, metin="Soru B?", sira=11)
        s3 = Soru.objects.create(kategori=kategori, metin="Soru C?", sira=12)
        item = {
            "idempotency_anahtari": str(uuid.uuid4()),
            "yas_araligi_kod": YasAraligi.objects.first().kod,
            "cinsiyet_kod": Cinsiyet.objects.first().kod,
            "oturum_tipi": "SIKAYET",
            "kategori_slug": kategori.slug,
            "hassas_akis": False,
            "cevaplar": {str(s1.id): "Y", str(s2.id): "N", str(s3.id): "Y"},
            "onerilen_etken_maddeler": [],
            "tamamlandi": True,
        }

        results, errors = ingest_session_items(kiosk_obj, [item])

        assert not errors
        oturum = OturumLogu.objects.get(idempotency_anahtari=item["idempotency_anahtari"])
        # 3 soru → 3 ayrı kayıt (birleşmemeli)
        assert OturumCevap.objects.filter(oturum=oturum).count() == 3
        snap_y = OturumCevap.objects.get(oturum=oturum, soru=s1)
        snap_n = OturumCevap.objects.get(oturum=oturum, soru=s2)
        assert snap_y.cevap_metni_snapshot == "Evet"
        assert snap_n.cevap_metni_snapshot == "Hay\u0131r"

    def test_multiple_string_ingredients_all_saved(self, db, kiosk_obj, kategori):
        """Birden fazla string etken madde adı — hepsi ayrı kayıt olarak saklanmalı.

        Regresyon: eskiden get_or_create(etken_madde=None) ikinci ve sonraki
        kayıtları birlestiriyordu (veri kaybı). Her string isim kendi satırını almalı.
        """
        item = {
            "idempotency_anahtari": str(uuid.uuid4()),
            "yas_araligi_kod": YasAraligi.objects.first().kod,
            "cinsiyet_kod": Cinsiyet.objects.first().kod,
            "oturum_tipi": "SIKAYET",
            "kategori_slug": kategori.slug,
            "hassas_akis": False,
            "cevaplar": {},
            "onerilen_etken_maddeler": ["Melatonin", "Valerian", "B12"],
            "tamamlandi": True,
        }

        results, errors = ingest_session_items(kiosk_obj, [item])

        assert not errors
        oturum = OturumLogu.objects.get(idempotency_anahtari=item["idempotency_anahtari"])
        snaps = list(OturumOnerilenEtkenMadde.objects.filter(oturum=oturum)
                     .values_list("etken_madde_adi_snapshot", flat=True))
        # Tümü saklanmalı — merge olmamalı
        assert len(snaps) == 3, f"Beklenen 3, alınan {len(snaps)}: {snaps}"
        assert "Melatonin" in snaps
        assert "Valerian" in snaps
        assert "B12" in snaps

    def test_sikayet_unknown_soru_id_still_errors(self, db, kiosk_obj, kategori):
        """Var olmayan soru ID → hata (Y/N toleransı geçersiz soru_id'yi affetmez)."""
        item = {
            "idempotency_anahtari": str(uuid.uuid4()),
            "yas_araligi_kod": YasAraligi.objects.first().kod,
            "cinsiyet_kod": Cinsiyet.objects.first().kod,
            "oturum_tipi": "SIKAYET",
            "kategori_slug": kategori.slug,
            "hassas_akis": False,
            "cevaplar": {"99999": "Y"},  # Y tolere edilir ama soru 99999 yok
            "onerilen_etken_maddeler": [],
            "tamamlandi": True,
        }

        results, errors = ingest_session_items(kiosk_obj, [item])

        assert not results
        assert "cevaplar" in errors[0]["errors"]
        assert not OturumLogu.objects.filter(idempotency_anahtari=item["idempotency_anahtari"]).exists()

    def test_sikayet_seed_id_key_still_errors(self, db, kiosk_obj, kategori, soru_cevap):
        """seed_id string ('en_q1') as key → hata (kiosk ID dönüşümü düzeltildi, seed_id kabul edilmez)."""
        soru, _ = soru_cevap
        item = {
            "idempotency_anahtari": str(uuid.uuid4()),
            "yas_araligi_kod": YasAraligi.objects.first().kod,
            "cinsiyet_kod": Cinsiyet.objects.first().kod,
            "oturum_tipi": "SIKAYET",
            "kategori_slug": kategori.slug,
            "hassas_akis": False,
            "cevaplar": {"en_q1": "Y"},  # seed_id olarak gönderilen key — hata vermeli
            "onerilen_etken_maddeler": [],
            "tamamlandi": True,
        }

        results, errors = ingest_session_items(kiosk_obj, [item])

        # seed_id geçersiz integer → hata
        assert not results
        assert "cevaplar" in errors[0]["errors"]
        assert "en_q1" in str(errors[0]["errors"])

    def test_sikayet_via_api_endpoint_with_binary_format(self, db, kiosk_client_norm, kiosk_obj, kategori, soru_cevap):
        """End-to-end: kiosk API endpoint üzerinden binary format testi."""
        soru, _ = soru_cevap
        payload = {
            "items": [{
                "idempotency_anahtari": str(uuid.uuid4()),
                "yas_araligi_kod": YasAraligi.objects.first().kod,
                "cinsiyet_kod": Cinsiyet.objects.first().kod,
                "oturum_tipi": "SIKAYET",
                "kategori_slug": kategori.slug,
                "hassas_akis": False,
                "cevaplar": {str(soru.id): "Y"},
                "onerilen_etken_maddeler": ["Omega-3"],
                "tamamlandi": True,
            }]
        }

        res = kiosk_client_norm.post(SESSIONS_URL, payload, format="json")

        assert res.status_code == 200, f"Unexpected status: {res.status_code} — {res.json()}"
        data = res.json()
        assert not data["errors"], f"Unexpected errors: {data['errors']}"
        assert data["results"][0]["status"] == "created"
        assert QR_RE.match(data["results"][0]["qr_kodu"])
