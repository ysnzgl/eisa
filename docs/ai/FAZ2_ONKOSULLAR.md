# FAZ 2 ÖNKOŞULLAR — TAMAMLANMA RAPORU

**Son Güncelleme:** 2026-07-22 04:47 UTC+3  
**Durum:** ✅ **Gate 1 & 2 TAMAMLANDI** | ⏳ **Gate 3 & 4 BEKLEMEDE**

---

## Gate 1: PostgreSQL Concurrency (✅ TAMAMLANDI)

**Amaç:** Gerçek PostgreSQL üzerinde select_for_update concurrency testleri.

### Tamamlanan İşler
1. ✅ PostgreSQL test container (docker-compose.test-pg.yml)
2. ✅ Integration test suite (`@pytest.mark.postgresql`)
3. ✅ A→B unique predecessor race test
4. ✅ A→B cycle prevention test (concurrent)
5. ✅ KioskDayQuota placed<=quota test (row-level)
6. ✅ **GlobalQuotaService CAMPAIGN_TOTAL global invariant test**

### Test Sonuçları
```bash
pytest apps/campaigns/tests/integration/ -m postgresql --ds=core_api.test_settings_pg -v

7 passed, 0 failed, 0 skipped
exit code: 0
connection.vendor: postgresql
database: eisa_test_integration
süre: 18.20s
```

**Geçen testler:**
1. test_concurrent_follows_same_predecessor_race
2. test_concurrent_follows_cycle_prevention
3. test_concurrent_follows_different_predecessors_allowed
4. test_concurrent_follows_with_intermediate_save
5. test_concurrent_quota_placement_constraint
6. test_concurrent_quota_different_days_allowed
7. **test_concurrent_global_quota_invariant** (CAMPAIGN_TOTAL)

---

## Gate 2: A→B Target Intersection (✅ TAMAMLANDI)

**Amaç:** A→B ilişkisi kurulurken hedef kiosk kesişimi zorunlu.

### Tamamlanan İşler
1. ✅ `follows_service.py`: `_targets_overlap()` fonksiyonu
2. ✅ Target resolution: ALL / RULES (INCLUDE/EXCLUDE hierarchy)
3. ✅ IL → ILCE → ECZANE → KIOSK genişlemesi
4. ✅ Integration testi (gerçek DB, hedef kesişimi yok → rejected)
5. ✅ `set_campaign_follows()` validation entegrasyonu

### Test Sonuçları
```bash
pytest apps/campaigns/tests/test_faz1_final.py -v

26 passed, 0 failed, 21 warnings
exit code: 0
süre: 11.04s
```

**Yeni testler:**
- test_follows_target_no_overlap_rejected (A: İstanbul, B: Ankara → ValidationError)
- test_follows_target_overlap_allowed (A: İstanbul+Ankara, B: Ankara → OK)

---

## Gate 3: Staging Migration + Smoke Test (❌ BLOKER: Staging Erişimi Yok)

**Amaç:** Faz 1 migration'ları staging ortamında çalıştırılmış ve doğrulanmış olmalı.

### Migration Durumu (Lokal Kontrol ✅)
```bash
# makemigrations --check
python manage.py makemigrations --check --dry-run campaigns
→ "No changes detected in app 'campaigns'"
exit code: 0
```

### Migration Zinciri
```
0001_initial
0002_initial
...
0015_creative_object_key_housead_object_key
0016_faz1_additive_schema  (PlanningRun, DeliveryRule, KioskDayQuota, CampaignTotalAllocation)
0017_faz1_kiosk_quota_constraints  (quota>=0, placed>=0, placed<=quota)
0018_faz1_campaign_follows_unique  (follows unique constraint)
```

### Rollback Plan
**Forward:** `python manage.py migrate campaigns`
**Rollback:** `python manage.py migrate campaigns 0016`
- 0017 ve 0018'i geri alır (constraints)
- Tüm Faz 1 modelleri (0016'da) korunur

### Staging Gereksinimleri (Eksik)
1. ❌ Staging DB connection string
2. ❌ Staging ortam erişimi
3. ❌ Backup/restore yetkisi

**Durum:** Migration kodu hazır ve doğrulandı; staging ortamı erişimi yok.
**Çalıştırılması gereken:** Staging DB'de `python manage.py migrate campaigns` + smoke test

---

## Gate 4: S3/RustFS Bucket Policy Testi (❌ BLOKER: Staging Credential Yok)

**Amaç:** Kalıcı medya URL'leri production'da çalışacak; bucket policy doğrulanmalı.

### Backend Storage Implementasyonu (✅ Doğrulandı)
**Dosya:** `apps/core/services/storage_service.py`
**Client:** Minio Python SDK (boto3-compatible S3 client)
**Operations:**
- `put_object()` — Upload with content-type
- `bucket_exists()` — Bucket existence check
- `make_bucket()` — Auto-create on startup
- SHA-256 checksum calculation (64KB streaming)

### Storage Configuration
```python
# settings.py (production deploy values)
S3_ENDPOINT = "files.eisa.com.tr"  # or localhost:9000 (dev)
S3_BUCKET = "eisa-files"            # or "dev" (local)
S3_ACCESS_KEY = config("S3_ACCESS_KEY")
S3_SECRET_KEY = config("S3_SECRET_KEY")
S3_SECURE = True                    # HTTPS (production)
S3_FORCE_PATH_STYLE = True          # Path-style URLs
S3_PUBLIC_BASE_URL = "https://files.eisa.com.tr/eisa-files"  # Bucket-inclusive base

# Media URL format
media_url = S3_PUBLIC_BASE_URL + "/" + object_key
# Example: https://files.eisa.com.tr/eisa-files/ads/abc123.mp4
```

### Gerekli S3 Policy (Referans)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadAds",
      "Effect": "Allow",
      "Principal": "*",
      "Action": ["s3:GetObject", "s3:HeadObject"],
      "Resource": "arn:aws:s3:::eisa-files/ads/*"
    }
  ]
}
```

### Service Account Yetkiler (Backend IAM User)
**Gerekli:**
- `s3:PutObject` (bucket: eisa-files, prefix: ads/*)
- `s3:GetObject` (smoke test için geçici)
- `s3:DeleteObject` (smoke test cleanup için geçici)
- `s3:ListBucket` (bucket_exists için)

**Gerekli Değil:**
- Diğer bucket'lara erişim
- Bucket creation/deletion
- Policy modification

### Staging Smoke Test (Eksik)
1. ❌ Staging S3 credential (ACCESS_KEY/SECRET_KEY)
2. ❌ Staging endpoint erişimi
3. Test adımları:
   ```bash
   # 1. Upload test file
   curl -X POST -F "file=@test.jpg" \
     -H "Authorization: Bearer $TOKEN" \
     $STAGING_API/api/campaigns/upload-media/
   # Response: {"object_key": "ads/xxx.jpg", "media_url": "https://..."}
   
   # 2. Public GET test
   curl -I $media_url  # Expect: 200 OK, Content-Type: image/jpeg
   
   # 3. HEAD test
   curl -I --head $media_url  # Expect: 200 OK, ETag header
   
   # 4. Delete test object (cleanup)
   # (Backend'den delete endpoint yoksa manual S3 client ile)
   ```

**Durum:** Storage kod hazır ve doğrulandı; staging credential ve erişim yok.
**Çalıştırılması gereken:** Staging ortamda upload/GET/HEAD/delete smoke testi

---

## Faz 0.5 Operasyonel Rollout (⏳ DEVAM EDİYOR)

### A. backfill_media_object_keys (⚠️ DRY-RUN BEKLENIYOR)
**Durum:** Management command var, production'da çalıştırılmadı.

**Yapılacak:**
1. Dry-run: `python manage.py backfill_media_object_keys --dry-run > report.txt`
2. Rapor inceleme: kaç Creative/HouseAd güncellendi, hata var mı?
3. Apply: `python manage.py backfill_media_object_keys --apply`
4. Doğrulama: `SELECT COUNT(*) FROM dooh_creatives WHERE object_key IS NULL`

### B. Production env değişkenleri (❌ YOK)
**Durum:** `DOOH_PERSISTENT_MEDIA_URL` ve `S3_PUBLIC_BASE_URL` henüz production'da set edilmedi.

**Yapılacak:**
```bash
# production.env
DOOH_PERSISTENT_MEDIA_URL=true
S3_PUBLIC_BASE_URL=https://files.eisa.com.tr/eisa-files
```

### C. Production smoke test (❌ YOK)
**Yapılacak:**
1. Yeni Creative upload → `media_url` kalıcı mı?
2. Kiosk `/api/kiosk/v1/sync/` → `media_url` kalıcı mı?
3. Kiosk media cache: `source_checksum` vs `file_checksum` karşılaştırması çalışıyor mu?

---

## Faz 2 Başlangıç — PlacementEngine V2 Shadow Mode (✅ TAMAMLANDI)

**Durum:** Minimum viable slice tamamlandı. Detaylı rapor: [FAZ2_COMPLETE.md](./FAZ2_COMPLETE.md)

### Tamamlanan İşler
1. ✅ GlobalQuotaService (CAMPAIGN_TOTAL reservation)
2. ✅ PlacementEngine V2 core algorithm
3. ✅ Shadow mode scheduler integration
4. ✅ Feature flag system (off/shadow)
5. ✅ Target resolution (ALL/RULES)
6. ✅ Date/weekday/active hours filters
7. ✅ Delivery type dispatch (4 types)
8. ✅ Guarantee mode priority
9. ✅ Overlap prevention (HourGrid)
10. ✅ A→B follows topological sort
11. ✅ Deterministic fingerprint
12. ✅ V1 output preservation guarantee
13. ✅ Exception isolation
14. ✅ Comprehensive test suite (13 tests)

### Test Sonuçları
```bash
# PlacementEngine V2
pytest apps/campaigns/tests/test_placement_engine_v2.py -v
13 passed, 0 failed
exit code: 0

# Faz 1 Regression
pytest apps/campaigns/tests/test_faz1_final.py -v
26 passed, 0 failed
exit code: 0

# PostgreSQL Concurrency
pytest apps/campaigns/tests/integration/ -m postgresql --ds=core_api.test_settings_pg -v
7 passed, 0 failed
exit code: 0

# TOPLAM: 46/46 tests passing
```

### Kabul Kriterleri (Tamamlandı)
- [x] V2 için doğrudan unit/integration testleri ekle (13/13 passing)
- [x] PlacementEngineV2 içinde gerçek asgari placement mantığını tamamla
- [x] Feature flag davranışı (off/shadow implemented)
- [x] Shadow çalışması: V2 hiçbir playlist kaydını yazmamalı (validated)
- [x] Testleri gerçekten çalıştır (46/46 tests executed, exit code 0)
- [x] Ham final summary ve exit code ver (FAZ2_COMPLETE.md)

---

## Özet

| Önkoşul | Durum | Blokaj |
|---------|-------|--------|
| PostgreSQL integration testleri | ✅ TAMAMLANDI | — |
| A→B target intersection validation | ✅ TAMAMLANDI | — |
| PlacementEngine V2 shadow mode | ✅ TAMAMLANDI | — |
| Shadow side-effect-free guarantee | ✅ TAMAMLANDI | — |
| Migration kod hazırlığı | ✅ TAMAMLANDI | — |
| Storage kod hazırlığı | ✅ TAMAMLANDI | — |
| **Gate 3: Staging migration** | ❌ **BLOKER** | **Staging DB erişimi yok** |
| **Gate 4: S3 smoke test** | ❌ **BLOKER** | **Staging credential yok** |
| backfill_media_object_keys | ⏳ DRY-RUN | Faz 0.5 |
| production env variables | ⏳ BEKLEMEDE | Faz 0.5 |

### Kod Durumu
✅ **FAZ 2 TAMAMLANDI**
- Feature Flag: `DOOH_ENGINE_V2=off` (safe default)
- Test durumu: **46/46 tests passing, exit code 0**
- Shadow guarantee: **Side-effect-free validated**
- Migration kod: **Hazır (0017, 0018)**
- Storage kod: **Hazır (Minio/S3 client)**

### Operasyonel Blokerler
❌ **Gate 3:** Staging DB connection string + migration smoke test
❌ **Gate 4:** Staging S3 credential + upload/GET/HEAD/delete testi

### Staging Ortamda Çalıştırılacak Komutlar

**Gate 3 (Migration):**
```bash
# Staging DB connection ile
python manage.py showmigrations campaigns
python manage.py migrate campaigns --plan
python manage.py migrate campaigns  # Apply 0017, 0018
python manage.py check
# Smoke test: campaign CRUD, follows constraint, quota constraint
```

**Gate 4 (S3 Smoke Test):**
```bash
# Staging S3 credential ile
curl -X POST -F "file=@test.jpg" \
  -H "Authorization: Bearer $STAGING_TOKEN" \
  $STAGING_API/api/campaigns/upload-media/
# Response media_url'i GET/HEAD testleri
# Test object'i sil (cleanup)
```

**Rollback Plan:**
```bash
# Migration rollback (if needed)
python manage.py migrate campaigns 0016  # Reverts 0017, 0018
```

---

**Sonraki Adımlar:**
1. **Operasyon:** Gate 3 ve 4'ü staging ortamda tamamla
2. **Kod:** Gate 3/4 tamamlandıktan sonra shadow activation hazırlığı
3. **İleri:** Faz 2.3 — Shadow metrics persistence

---

**Değişiklik Geçmişi:**
- 2026-07-22 05:15: Gate 3/4 kod hazırlığı tamamlandı, staging blokerler tespit edildi
- 2026-07-22 04:59: Shadow side-effect-free guarantee validated
- 2026-07-22 04:47: Gate 1 & 2 tamamlandı, PlacementEngine V2 shadow mode tamamlandı
- 2026-07-22 00:00: İlk önkoşullar belirlendi
