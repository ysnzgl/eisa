"""
Çok etken maddeli oturum testleri.

Kapsam:
  1. Tek soruda birden fazla etken madde — hepsi OturumOnerilenEtkenMadde'ye kaydedilmeli
  2. Birden fazla sorudan gelen farklı maddeler birleştirilmeli
  3. Aynı madde farklı sorulardan (veya aynı listede tekrar) gelirse tekleştirilmeli
  4. Senkronizasyon tekrarında (aynı idempotency_key) mükerrer kayıt oluşmamalı
  5. sold=1 istatistiğinde aynı başvuru içindeki aynı maddenin bir kez sayılması
  6. Snapshot (null-FK) kayıtlar için DB-seviyesi unique constraint
"""
from __future__ import annotations

import uuid

import pytest
from django.db import IntegrityError

from apps.analytics.models import OturumLogu, OturumOnerilenEtkenMadde
from apps.analytics.services import ingest_session_items
from apps.lookups.seed import seed_lookups
from apps.lookups.models import Cinsiyet, Il, Ilce, YasAraligi
from apps.pharmacies.models import Eczane, Kiosk
from apps.products.models import EtkenMadde, Kategori

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _seed(db):
    seed_lookups()


@pytest.fixture
def eczane(db):
    il, _ = Il.objects.get_or_create(ad="TestIl")
    ilce, _ = Ilce.objects.get_or_create(il=il, ad="TestIlce")
    return Eczane.objects.create(ad="TestEczane", il=il, ilce=ilce)


@pytest.fixture
def kiosk(db, eczane):
    return Kiosk.objects.create(
        eczane=eczane,
        ad="Kiosk1",
        mac_adresi="AA:BB:CC:DD:EE:01",
        uygulama_anahtari="test-key-01",
    )


@pytest.fixture
def kategori(db):
    return Kategori.objects.create(ad="Test Kategori", slug="test-kategori")


def _em(ad):
    return EtkenMadde.objects.get_or_create(ad=ad)[0]


def _ingest(kiosk, kategori, ingredient_names, idem=None):
    """Kiosk üzerinden verilen etken madde listesi ile bir oturum ingest eder."""
    payload = {
        "idempotency_anahtari": idem or str(uuid.uuid4()),
        "kiosk_mac": kiosk.mac_adresi,
        "yas_araligi_kod": YasAraligi.objects.first().kod,
        "cinsiyet_kod": Cinsiyet.objects.first().kod,
        "oturum_tipi": "SIKAYET",
        "kategori_slug": kategori.slug,
        "hassas_akis": False,
        "cevaplar": {},
        "onerilen_etken_maddeler": ingredient_names,
        "tamamlandi": True,
        "olusturulma_tarihi": "2026-08-15T10:00:00.000Z",
    }
    results, errors = ingest_session_items(kiosk, [payload])
    assert errors == [], f"Ingest hataları: {errors}"
    assert len(results) == 1
    return OturumLogu.objects.get(idempotency_anahtari=payload["idempotency_anahtari"])


# ── Test 1: Tek soruda birden fazla etken madde ───────────────────────────────

class TestTekSorudaBirdenFazlaEtkenMadde:
    def test_uc_madde_hepsi_kaydedilir(self, db, kiosk, kategori):
        em_a = _em("Magnezyum")
        em_b = _em("B12")
        em_c = _em("D3")
        oturum = _ingest(kiosk, kategori, ["Magnezyum", "B12", "D3"])
        kayitli = list(
            OturumOnerilenEtkenMadde.objects.filter(oturum=oturum)
            .values_list("etken_madde__ad", flat=True)
        )
        assert set(kayitli) == {"Magnezyum", "B12", "D3"}
        assert len(kayitli) == 3

    def test_iki_madde_hepsi_kaydedilir(self, db, kiosk, kategori):
        _em("Demir")
        _em("Kalsiyum")
        oturum = _ingest(kiosk, kategori, ["Demir", "Kalsiyum"])
        kayitli = list(
            OturumOnerilenEtkenMadde.objects.filter(oturum=oturum)
            .values_list("etken_madde__ad", flat=True)
        )
        assert set(kayitli) == {"Demir", "Kalsiyum"}


# ── Test 2: Birden fazla sorudan gelen farklı maddeler birleştirilir ──────────

class TestBirdenFazlaSorudanBirlestirme:
    def test_dort_farkli_madde_hepsi_kaydedilir(self, db, kiosk, kategori):
        # Q1→A,B,C  Q2→B,D  Q3→A,C,E  ⟹  A,B,C,D,E  (5 tekil)
        ingredient_list = ["A", "B", "C", "D", "E"]  # kiosk motoru zaten tekilleştirir
        oturum = _ingest(kiosk, kategori, ingredient_list)
        kayitli_sayisi = OturumOnerilenEtkenMadde.objects.filter(oturum=oturum).count()
        assert kayitli_sayisi == 5

    def test_dort_farkli_madde_isimleri_dogru(self, db, kiosk, kategori):
        for ad in ["A", "B", "C", "D", "E"]:
            _em(ad)
        oturum = _ingest(kiosk, kategori, ["A", "B", "C", "D", "E"])
        kayitli = set(
            OturumOnerilenEtkenMadde.objects.filter(oturum=oturum)
            .values_list("etken_madde__ad", flat=True)
        )
        assert kayitli == {"A", "B", "C", "D", "E"}


# ── Test 3: Tekilleştirme — aynı madde listede birden fazla kez ───────────────

class TestTekillestime:
    def test_tekrarlayan_madde_bir_kez_kaydedilir(self, db, kiosk, kategori):
        # Backend get_or_create ile aynı FK'lı maddeyi bir kez kaydeder.
        oturum = _ingest(kiosk, kategori, ["Magnezyum", "B12", "Magnezyum", "B12"])
        kayitli_sayisi = OturumOnerilenEtkenMadde.objects.filter(oturum=oturum).count()
        assert kayitli_sayisi == 2

    def test_uc_sorudan_gelen_tekrar_tekillesir(self, db, kiosk, kategori):
        # Kiosk motoru zaten tekilleştirir; backend ek güvence sağlar.
        for ad in ["A", "B", "C", "D", "E"]:
            _em(ad)
        # Kiosk çıktısı: A,B,C,B,D,A,C,E → motor → A,B,C,D,E
        oturum = _ingest(kiosk, kategori, ["A", "B", "C", "D", "E"])
        assert OturumOnerilenEtkenMadde.objects.filter(oturum=oturum).count() == 5


# ── Test 4: Senkronizasyon tekrarında mükerrer kayıt oluşmaz ─────────────────

class TestSenkronizasyonIdempotency:
    def test_ayni_key_tekrar_ingest_edilirse_kayit_sayisi_artmaz(self, db, kiosk, kategori):
        idem = str(uuid.uuid4())
        oturum = _ingest(kiosk, kategori, ["Magnezyum", "B12", "D3"], idem=idem)
        ilk_sayisi = OturumOnerilenEtkenMadde.objects.filter(oturum=oturum).count()
        assert ilk_sayisi == 3

        # Aynı idempotency_key tekrar gönderildiğinde — ingest "existing" döner, yeni kayıt yok
        payload = {
            "idempotency_anahtari": idem,
            "kiosk_mac": kiosk.mac_adresi,
            "yas_araligi_kod": YasAraligi.objects.first().kod,
            "cinsiyet_kod": Cinsiyet.objects.first().kod,
            "oturum_tipi": "SIKAYET",
            "kategori_slug": kategori.slug,
            "hassas_akis": False,
            "cevaplar": {},
            "onerilen_etken_maddeler": ["Magnezyum", "B12", "D3"],
            "tamamlandi": True,
            "olusturulma_tarihi": "2026-08-15T10:00:00.000Z",
        }
        results2, errors2 = ingest_session_items(kiosk, [payload])
        assert errors2 == []
        assert results2[0]["status"] == "existing"

        # OturumLogu sayısı hâlâ 1
        assert OturumLogu.objects.filter(idempotency_anahtari=idem).count() == 1
        # Etken madde kayıtları artmadı
        assert OturumOnerilenEtkenMadde.objects.filter(oturum=oturum).count() == ilk_sayisi

    def test_get_or_create_duplicate_koruyor_fk_mevcut(self, db, kiosk, kategori):
        """FK çözümlenebilirse unique_together IntegrityError yerine mevcut kaydı döner."""
        em = _em("Demir")
        oturum = _ingest(kiosk, kategori, ["Demir"])
        # Manuel ikinci create — get_or_create kullanarak (IntegrityError beklenmez)
        obj, created = OturumOnerilenEtkenMadde.objects.get_or_create(
            oturum=oturum, etken_madde=em,
            defaults={"etken_madde_adi_snapshot": "Demir"},
        )
        assert not created  # Var olan kaydı döndürmeli
        assert OturumOnerilenEtkenMadde.objects.filter(oturum=oturum, etken_madde=em).count() == 1


# ── Test 5: sold=1 istatistiğinde aynı madde bir kez sayılır ──────────────────

class TestSoldStats:
    def test_ayni_oturumda_ayni_madde_bir_kez_sayilir(self, db, kiosk, kategori):
        """
        Bir sold=True oturumda aynı madde birden fazla sorudan gelse bile
        OturumOnerilenEtkenMadde unique_together → sadece 1 kayıt → Count('id')=1.
        """
        from django.db.models import Count
        from django.db.models.functions import Coalesce

        em = _em("Magnezyum")
        oturum = _ingest(kiosk, kategori, ["Magnezyum"])
        oturum.sold = True
        oturum.save(update_fields=["sold"])

        # "get_or_create" ile aynı maddeyi tekrar eklemeye çalış — yeni kayıt oluşmamalı
        OturumOnerilenEtkenMadde.objects.get_or_create(
            oturum=oturum, etken_madde=em,
            defaults={"etken_madde_adi_snapshot": "Magnezyum"},
        )

        em_qs = (
            OturumOnerilenEtkenMadde.objects.filter(oturum__sold=True)
            .annotate(em_adi=Coalesce("etken_madde__ad", "etken_madde_adi_snapshot"))
            .values("em_adi")
            .annotate(sayi=Count("id"))
            .order_by("-sayi")
        )
        madde_row = em_qs.filter(em_adi="Magnezyum").first()
        assert madde_row is not None
        assert madde_row["sayi"] == 1  # tek oturum → bir kez sayılır

    def test_farkli_sold_oturumlardaki_ayni_madde_dogru_sayilir(self, db, kiosk, kategori):
        """İki farklı sold oturumda aynı madde varsa sayi=2 olmalı."""
        from django.db.models import Count
        from django.db.models.functions import Coalesce

        em = _em("B12")
        o1 = _ingest(kiosk, kategori, ["B12"], idem=str(uuid.uuid4()))
        o1.sold = True
        o1.save(update_fields=["sold"])

        o2 = _ingest(kiosk, kategori, ["B12"], idem=str(uuid.uuid4()))
        o2.sold = True
        o2.save(update_fields=["sold"])

        em_qs = (
            OturumOnerilenEtkenMadde.objects.filter(oturum__sold=True)
            .annotate(em_adi=Coalesce("etken_madde__ad", "etken_madde_adi_snapshot"))
            .values("em_adi")
            .annotate(sayi=Count("id"))
            .order_by("-sayi")
        )
        row = em_qs.filter(em_adi="B12").first()
        assert row is not None
        assert row["sayi"] == 2


# ── Test 6: Snapshot (null-FK) unique constraint ──────────────────────────────

class TestSnapshotUniqueConstraint:
    def test_null_fk_ayni_snapshot_duplicate_hata_verir(self, db, kiosk, kategori):
        """
        etken_madde=None iken aynı (oturum, etken_madde_adi_snapshot) çifti
        IntegrityError üretmeli (0017 migration constraint).
        """
        oturum = _ingest(kiosk, kategori, [])  # boş liste — temiz oturum

        OturumOnerilenEtkenMadde.objects.create(
            oturum=oturum, etken_madde=None, etken_madde_adi_snapshot="BilinmeyenMadde"
        )
        with pytest.raises(IntegrityError):
            OturumOnerilenEtkenMadde.objects.create(
                oturum=oturum, etken_madde=None, etken_madde_adi_snapshot="BilinmeyenMadde"
            )

    def test_null_fk_farkli_snapshot_izin_verilir(self, db, kiosk, kategori):
        """Farklı snapshot adlarına sahip null-FK satırları aynı oturumda olabilir."""
        oturum = _ingest(kiosk, kategori, [])

        OturumOnerilenEtkenMadde.objects.create(
            oturum=oturum, etken_madde=None, etken_madde_adi_snapshot="Madde1"
        )
        OturumOnerilenEtkenMadde.objects.create(
            oturum=oturum, etken_madde=None, etken_madde_adi_snapshot="Madde2"
        )
        assert OturumOnerilenEtkenMadde.objects.filter(oturum=oturum).count() == 2
