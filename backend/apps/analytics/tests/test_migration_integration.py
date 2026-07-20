"""Migration integration testi: QR data cleanup, backfill ve pharmacies device_id.

Not: Bu test SQLite (in-memory) üzerinde çalışır.
PostgreSQL doğrulaması deployment öncesi ayrı bir pre-production adımıdır.

Kapsam:
  - analytics 0005 durumuna geri alınır (schema rollback)
  - pharmacies 0006 durumuna geri alınır (device_id öncesi)
  - Çeşitli QR durumlarıyla test verisi eklenir (raw SQL — ORM rollback durumunda güvenilmez)
  - analytics 0006/0007/0008 + pharmacies 0007 ileriye uygulanır
  - QR temizliği, format uyumu, unique constraint doğrulanır
  - Backfill komutu dry-run, gerçek çalıştırma ve idempotency kontrol edilir
  - verify_session_data başarılı çalışır
"""
from __future__ import annotations

import re
import uuid
from io import StringIO

from django.test import TransactionTestCase

QR_RE = re.compile(r"^[A-Z0-9]{8}$")


class QrDataMigrationIntegrationTest(TransactionTestCase):
    """End-to-end migration + backfill entegrasyon testi.

    TransactionTestCase kullanımı: MigrationExecutor DDL değişikliklerini
    bir transaction içinde yapamaz (ALTER TABLE, CREATE TABLE vb.), bu nedenle
    standart TestCase (her test için transaction wrap) yerine TransactionTestCase
    zorunludur.

    Temizlik: Test sonunda schema'yı restore eden bir finally bloğu her zaman çalışır.
    """

    def _executor(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        return MigrationExecutor(connection)

    def test_migration_forward_and_backfill(self):
        from django.core.management import call_command
        from django.db import connection

        try:
            self._run_test(connection, call_command)
        finally:
            # Schema'yı her zaman restore et: bu blok hata olsa bile çalışır.
            executor = self._executor()
            leaf_nodes = executor.loader.graph.leaf_nodes()
            executor.migrate(leaf_nodes)

    def _run_test(self, connection, call_command):
        # ─── 1. ROLLBACK ──────────────────────────────────────────────────────────
        # analytics'i 0005'e, pharmacies'i 0006'ya al
        executor = self._executor()
        executor.migrate([
            ("analytics", "0005_oturumlogu_danisma_notu_and_more"),
            ("pharmacies", "0006_kioskprovisioningrequest"),
        ])

        # ─── 2. TEST VERİSİ OLUŞTUR (raw SQL) ───────────────────────────────────
        # ORM kullanılmaz: Django model registry rollback sonrası schema ile
        # uyumsuz (örn. device_id kolonu kaldırıldı ama Kiosk modelinde var).
        with connection.cursor() as cur:

            # Lookups (LookupModel - audit kolonu YOK, yalnız id+ad)
            cur.execute("SELECT id FROM yas_araliklari LIMIT 1")
            row = cur.fetchone()
            if row:
                yas_id = row[0]
            else:
                cur.execute(
                    "INSERT INTO yas_araliklari (kod, ad, alt_sinir, ust_sinir)"
                    " VALUES ('18-24','18-24',18,24)"
                )
                yas_id = cur.lastrowid

            cur.execute("SELECT id FROM cinsiyetler LIMIT 1")
            row = cur.fetchone()
            if row:
                cins_id = row[0]
            else:
                cur.execute("INSERT INTO cinsiyetler (kod, ad) VALUES ('M','Erkek')")
                cins_id = cur.lastrowid

            # il (id, ad — LookupModel, audit kolonu YOK)
            cur.execute("INSERT INTO iller (ad) VALUES ('Mig Test Il')")
            il_id = cur.lastrowid

            # ilce (id, ad, il_id — audit YOK)
            cur.execute(
                "INSERT INTO ilceler (ad, il_id) VALUES ('Mig Test Ilce', ?)",
                [il_id],
            )
            ilce_id = cur.lastrowid

            # eczane (BaseModel — audit alanları var)
            cur.execute(
                "INSERT INTO eczaneler"
                " (ad, il_id, ilce_id, adres, sahip_adi, telefon, aktif,"
                "  olusturulma_tarihi, guncellenme_tarihi, surum)"
                " VALUES ('Mig Eczane', ?, ?, '', '', '', 1,"
                "         datetime('now'), datetime('now'), 1)",
                [il_id, ilce_id],
            )
            eczane_id = cur.lastrowid

            # kiosk — pharmacies 0006 durumunda: device_id kolonu YOK
            # Kolonlar: id, olusturulma_tarihi, guncellenme_tarihi, surum,
            #   mac_adresi, uygulama_anahtari, aktif, son_goruldu,
            #   eczane_id, guncelleyen_id, olusturan_id, ad, is_online, last_playlist_version
            cur.execute(
                "INSERT INTO kiosklar"
                " (eczane_id, ad, mac_adresi, uygulama_anahtari, aktif, is_online,"
                "  olusturulma_tarihi, guncellenme_tarihi, surum)"
                " VALUES (?, 'Mig Kiosk', 'MI:GR:AT:IO:N0:01',"
                "         'mig-test-app-key-48chars-xxxxxxxxxxxxxxxxx', 1, 0,"
                "         datetime('now'), datetime('now'), 1)",
                [eczane_id],
            )
            kiosk_id = cur.lastrowid

            # kategori
            # Kolonlar: id, olusturulma_tarihi, guncellenme_tarihi, surum,
            #   slug, ikon, aktif, guncelleyen_id, olusturan_id,
            #   hedef_cinsiyet_id, ad, bagli_kategori_id
            cur.execute(
                "INSERT INTO kategoriler"
                " (ad, slug, ikon, aktif, surum,"
                "  olusturulma_tarihi, guncellenme_tarihi)"
                " VALUES ('Mig Kategori','mig-kat','fa-pill',1,1,"
                "         datetime('now'), datetime('now'))"
            )
            kat_id = cur.lastrowid

            # ─── oturum_loglari at 0005 schema ────────────────────────────────
            # Colonlar: id, idempotency_anahtari, kiosk_id, yas_araligi_id,
            #   cinsiyet_id, kategori_id (NOT NULL), hassas_akis, qr_kodu,
            #   cevaplar, onerilen_etken_maddeler, tamamlandi, danisma_tamamlandi,
            #   danisma_notu, olusturulma_tarihi, guncellenme_tarihi, surum
            # NOT: oturum_tipi, danisma_kategorisi_id YOK (bunlar 0006'da ekleniyor)
            def insert_oturum(qr, cevaplar="{}", onerilen="[]"):
                cur.execute(
                    "INSERT INTO oturum_loglari"
                    " (idempotency_anahtari, kiosk_id, yas_araligi_id, cinsiyet_id,"
                    "  kategori_id, hassas_akis, qr_kodu, cevaplar,"
                    "  onerilen_etken_maddeler, tamamlandi, danisma_tamamlandi,"
                    "  danisma_notu, olusturulma_tarihi, guncellenme_tarihi, surum)"
                    " VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, 1, 0, '',"
                    "         datetime('now'), datetime('now'), 1)",
                    [str(uuid.uuid4()), kiosk_id, yas_id, cins_id, kat_id,
                     qr, cevaplar, onerilen],
                )
                return cur.lastrowid

            row_valid    = insert_oturum("AB12CD34")         # geçerli, unique → KORUNUR
            row_dup1     = insert_oturum("XXXXXXXX")         # ilk duplicate → KORUNUR
            row_dup2     = insert_oturum("XXXXXXXX")         # ikinci dup → YENİDEN ÜRETILIR
            row_empty    = insert_oturum("")                 # boş → YENİDEN ÜRETILIR
            row_invalid  = insert_oturum("OLD_FORMAT_LONG")  # geçersiz format → YENİDEN ÜRETILIR
            row_json     = insert_oturum(                    # JSON verisi → backfill için
                "VALIDQR1",
                cevaplar='{"1": 2}',
                onerilen="[5]",
            )

        # ─── 3. İLERİ MİGRASYON ─────────────────────────────────────────────────
        executor2 = self._executor()
        executor2.migrate([
            ("analytics", "0008_qr_unique_constraint"),
            ("pharmacies", "0007_kiosk_device_id"),
        ])

        # ─── 4. QR BÜTÜNLÜĞÜ ────────────────────────────────────────────────────
        with connection.cursor() as cur:
            cur.execute("SELECT id, qr_kodu FROM oturum_loglari ORDER BY id")
            rows = cur.fetchall()

        id_to_qr = {r[0]: r[1] for r in rows}
        qr_codes  = [r[1] for r in rows]

        self.assertEqual(len(rows), 6, f"Beklenen 6 kayıt, var olan: {len(rows)}")

        # Tüm QR'lar [A-Z0-9]{8} formatında olmalı
        for qr in qr_codes:
            self.assertRegex(qr, QR_RE, f"QR format ihlali: {qr!r}")

        # Tüm QR'lar unique olmalı
        self.assertEqual(
            len(qr_codes), len(set(qr_codes)),
            f"Duplicate QR migration sonrası: {qr_codes}",
        )

        # Geçerli ve çakışmayan eski QR'lar korunmalı
        self.assertIn("AB12CD34", qr_codes, "Geçerli QR AB12CD34 korunmadı!")
        self.assertIn("XXXXXXXX", qr_codes, "İlk XXXXXXXX duplicate kaydı korunmadı!")
        self.assertIn("VALIDQR1", qr_codes, "VALIDQR1 JSON QR korunmadı!")

        # Duplicate / boş / geçersiz olanlar YENİ QR almış olmalı
        self.assertNotEqual(id_to_qr[row_dup2], "XXXXXXXX",
                            "İkinci duplicate hâlâ XXXXXXXX!")
        self.assertNotEqual(id_to_qr[row_empty], "",
                            "Boş QR hâlâ boş!")
        self.assertNotRegex(id_to_qr[row_invalid], re.compile(r"^OLD_"),
                            "Geçersiz format QR değişmedi!")

        # ─── 5. OTURUM TİPİ KONTROLÜ ────────────────────────────────────────────
        with connection.cursor() as cur:
            cur.execute("SELECT DISTINCT oturum_tipi FROM oturum_loglari")
            tipler = {row[0] for row in cur.fetchall()}
        self.assertEqual(
            tipler, {"SIKAYET"},
            f"Beklenen tüm satırlarda 'SIKAYET', bulunan: {tipler}",
        )

        # ─── 6. YENİ TABLOLAR OLUŞTU MU? ────────────────────────────────────────
        with connection.cursor() as cur:
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
                " AND name IN ('oturum_cevaplar','oturum_onerilen_etken_maddeler')"
            )
            tables = {r[0] for r in cur.fetchall()}
        self.assertIn("oturum_cevaplar", tables)
        self.assertIn("oturum_onerilen_etken_maddeler", tables)

        # ─── 7. PHARMACIES DEVICE_ID KOLONLARI ───────────────────────────────────
        with connection.cursor() as cur:
            cur.execute("PRAGMA table_info(kiosklar)")
            kiosk_cols = {r[1] for r in cur.fetchall()}
            cur.execute("PRAGMA table_info(kiosk_provisioning_requests)")
            prov_cols = {r[1] for r in cur.fetchall()}
        self.assertIn("device_id", kiosk_cols, "Kiosk.device_id kolonu yok!")
        self.assertIn("device_id", prov_cols,  "KioskProvisioningRequest.device_id kolonu yok!")

        # ─── 8. BACKFILL DRY-RUN ────────────────────────────────────────────────
        with connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM oturum_cevaplar")
            cevap_before = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM oturum_onerilen_etken_maddeler")
            oneri_before = cur.fetchone()[0]

        out1 = StringIO()
        call_command("backfill_session_normalization", dry_run=True, stdout=out1)

        with connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM oturum_cevaplar")
            self.assertEqual(
                cur.fetchone()[0], cevap_before,
                "Dry-run OturumCevap kaydı oluşturdu — YANLIŞ!",
            )
            cur.execute("SELECT COUNT(*) FROM oturum_onerilen_etken_maddeler")
            self.assertEqual(
                cur.fetchone()[0], oneri_before,
                "Dry-run OturumOnerilen kaydı oluşturdu — YANLIŞ!",
            )
        self.assertIn("DRY RUN", out1.getvalue(), "Dry-run çıktısında 'DRY RUN' yok!")

        # ─── 9. BACKFILL GERÇEK ÇALIŞMA ─────────────────────────────────────────
        out2 = StringIO()
        call_command("backfill_session_normalization", stdout=out2)

        with connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM oturum_cevaplar")
            cevap_after = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM oturum_onerilen_etken_maddeler")
            oneri_after = cur.fetchone()[0]

        # JSON verisi olan VALIDQR1 satırı için child kayıtlar oluşmalı
        self.assertGreater(
            cevap_after, cevap_before,
            "Backfill OturumCevap oluşturmadı! JSON verisi olan satır için bekleniyor.",
        )
        self.assertGreater(
            oneri_after, oneri_before,
            "Backfill OturumOnerilen oluşturmadı! JSON verisi olan satır için bekleniyor.",
        )

        # ─── 10. BACKFILL İDEMPOTENSI ───────────────────────────────────────────
        out3 = StringIO()
        call_command("backfill_session_normalization", stdout=out3)

        with connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM oturum_cevaplar")
            cevap_second = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM oturum_onerilen_etken_maddeler")
            oneri_second = cur.fetchone()[0]

        self.assertEqual(
            cevap_after, cevap_second,
            f"İkinci backfill çalışması duplicate OturumCevap oluşturdu! "
            f"({cevap_after} → {cevap_second})",
        )
        self.assertEqual(
            oneri_after, oneri_second,
            f"İkinci backfill çalışması duplicate OturumOnerilen oluşturdu! "
            f"({oneri_after} → {oneri_second})",
        )

        # ─── 11. VERIFY_SESSION_DATA ─────────────────────────────────────────────
        out4 = StringIO()
        call_command("verify_session_data", stdout=out4)
        report = out4.getvalue()
        self.assertIn("SESSION DATA QUALITY REPORT", report)
        # Hiç duplicate/boş/format dışı QR kalmamalı (migration 0007 temizledi)
        self.assertIn("Duplicate QR groups     : 0", report)
        self.assertIn("Empty QR                : 0", report)
        self.assertIn("Invalid-format QR       : 0", report)
        # Backfill tamamlandığında backfill candidate'ı 0 olmalı
        self.assertIn("All data is clean and normalized.", report)
