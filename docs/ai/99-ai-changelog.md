# AI Changelog — Dokümantasyon ve Kod Değişiklikleri

**Amaç:** AI tarafından yapılan değişikliklerin kısa kaydı.
**Format:** Tarih — Değişiklik (max 10 satır/kayıt)

---

## 2026-07-23

### [Frontend+Backend] Faz 6+7 Nihai Kapanış Denetimi (Tamamlandı)

**Root cause düzeltmeleri:**
- Login 500: settings_dev_sqlite.py DEFAULT_THROTTLE_RATES={} kaldırıldı; Local dev PG'ye migration uygulandı
- PlaylistEditor gerçek read-only: Tüm mutation fonk. + importlar KALDIRILDI (298 satırlık temiz bileşen)
- CampaignSerializer: deprecated alanlar ANY değer → 400 (True/False/null/0)
- CampaignWizard: target_days state + toggleDay() + DAYS_OF_WEEK KALDIRILDI
- is_enabled/is_active_mode/should_publish helper metodları KALDIRILDI (PlacementEngineV2'den)
- test_c19: hardcoded tarih bağımlılığı düzeltildi (pre-existing flaky test)

**Migration veri etkisi (0020, kanıtlandı):**
- Test PG 0019→0020: is_guaranteed/impression_goal/frequency_cap_per_hour DROP edildi
- SQL: ALTER TABLE dooh_campaigns DROP COLUMN ... CASCADE (3 kolon)
- Kayıt korundu, yalnız kolon silindi. Tüm değerler nullable/default'du.

**Docs güncellendi:**
- 00-AI-INDEX.md, 01-backend.md, 05-cross-project-flows.md, 06-db-and-api-contracts.md

**Test Sonuçları:**
- Backend SQLite: 436 passed | PostgreSQL: 16 passed | Frontend: 57 passed
- Build: exit 0 | git diff --check: exit 0

**Browser (gerçek auth, gerçek PostgreSQL):**
- Login 200 ✓ | Dashboard gerçek verilerle ✓ | CampaignWizard ✓ | DoohControlCenter ✓
- PlaylistEditor salt-okunur ✓ (1 kiosk) | pharmacist → /login redirect ✓
- Backend RBAC: IsSuperAdmin permission → 403 kanıtlandı
- Screenshots: Desktop ✓ | Narrow (375px) ✓

**Production'a hiçbir şey uygulanmadı.**




### [DOOH] Faz 4/5 KapanÄ±ÅŸ Denetimi â€” Kritik DÃ¼zeltmeler (TAMAMLANDI)

**DÃ¼zeltilen aÃ§Ä±klar:**
1. **Fingerprint source-of-truth**: `Kiosk.last_v2_fingerprints` stale metadata â†’ gerÃ§ek `PlaylistItem` kayÄ±tlarÄ±ndan hesaplama (`ActivationService._compute_playlist_fingerprint()`). Manuel/V1 mutasyon sonrasÄ± stale fingerprint "aynÄ±" sayÄ±lmaz.
2. **Fingerprint check inside lock**: Ã–nceki `process_job` lock-dÄ±ÅŸÄ± fingerprint kontrolÃ¼ yapÄ±yordu â†’ concurrent workers iki kez publish edebilirdi. DÃ¼zeltme: `_persist_plan(check_fingerprint=True)` fingerprint'i row-lock altÄ±nda DB'den hesaplar.
3. **Pending ACK dayanÄ±klÄ±lÄ±ÄŸÄ±**: Max retry â†’ ACK siliniyordu. DÃ¼zeltme: capped backoff (30sâ†’1800s), hiÃ§bir zaman silinmez. 409 FUTURE_REJECTED â†’ resync flag + ACK korunur. Conditional clear (`clearPendingAckIfMatches`) eski ACK cevabÄ±nÄ±n yeni pending'i silmesini Ã¶nler.
4. **Kiosk eczane deÄŸiÅŸimi**: pre_save ile eski eczane_id capture â†’ post_save'de eski+yeni kapsam invalidation.
5. **Eczane il/ilÃ§e/aktiflik sinyali**: Yeni signal (Eczane post_save) â†’ eczanedeki kiosklar Ã— horizon invalidation.

**Test SonuÃ§larÄ±:**
- SQLite: 430 passed, 0 failed, 0 skipped (exit 0)
- PostgreSQL: 16 passed, 0 failed, 0 skipped (exit 0)
- Node.js: 96 passed, 0 failed (exit 0)

---

### [DOOH] Faz 3 â€” Simulation / Activation / Reservation (TAMAMLANDI)

**DeÄŸiÅŸiklik:**
- `activation_service.py` (yeni): `ActivationService.simulate()` (read-only) + `ActivationService.activate()` (atomic, all-or-nothing GUARANTEED, BEST_EFFORT, CAMPAIGN_TOTAL global invariant)
- `views_v2.py`: `CampaignViewSet.simulate` (POST .../simulate/) + `CampaignViewSet.activate` (POST .../activate/) action'larÄ± eklendi
- `serializers.py`: `SimulationResultSerializer`, `ActivationResultSerializer`, `KioskDaySimResultSerializer` eklendi
- `placement_engine_v2.py`: `is_active_mode()` eklendi, `is_enabled()` shadow+active, `should_publish()` active mode
- `settings.py`: `DOOH_ENGINE_V2` comment gÃ¼ncellendi (off/shadow/active)
- `scheduler.py`: trailing whitespace dÃ¼zeltildi, shadow+active comment gÃ¼ncellendi
- `tests/test_faz3_simulation_activation.py` (yeni): 21 test (FA-01..FA-16)
- `tests/integration/test_faz3_concurrency.py` (yeni): FA-10, FA-11 PostgreSQL race testleri

**Test SonuÃ§larÄ±:** 371 passed, 7 skipped, 0 failed (Exit: 0)
**git diff --check:** Exit 0 (no trailing whitespace)

---

### [DOOH] Faz 2 â€” PlacementEngine V2 Shadow Mode (TAMAMLANDI)

**DeÄŸiÅŸiklik:**
- `placement_engine_v2.py` (yeni): DeliveryRule dispatch, HourGrid overlap, follows chain, house_ad filler, SHA-256 fingerprint
- `quota_service.py` (yeni): `GlobalQuotaService.reserve_for_kiosk_day()` + `initialize_allocation()` (parent row locking)
- `follows_service.py` (yeni): `set_campaign_follows()` service, `_targets_overlap()` ile ALL-scope sentinel fix
- `scheduler.py`: V2 shadow mode entegrasyonu (V1 authoritative, V2 loglar)
- Migration 0015-0018: object_key, Faz1 schema, quota constraints, follows unique
- `tests/test_placement_engine_v2.py` (yeni): 13 test (tÃ¼mÃ¼ geÃ§ti)
- `tests/integration/test_concurrency_postgresql.py` (yeni): 7 PostgreSQL concurrency test

**Bug DÃ¼zeltmeleri:**
- `follows_service._targets_overlap`: ALL/None scope iÃ§in empty kiosk set false-positive hatasÄ± â†’ `_ALL_SCOPE` sentinel ile dÃ¼zeltildi
- `analytics/views.py`: `uow.update()` Ã§aÄŸrÄ±sÄ±nda Ã§ift audit field (`guncelleyen` + `guncelleyen_id`) â†’ PostgreSQL `multiple assignments to same column` â†’ fazla alanlar kaldÄ±rÄ±ldÄ±
- `test_golden_master.py` + `test_persistent_media.py`: `timezone.now() - 1 day` â†’ Ã¶ÄŸleden sonra scheduler noon UTC filtresini geÃ§emiyordu â†’ `_today_start()` sabit TODAY bazlÄ± helper ile dÃ¼zeltildi
- `tests/conftest.py` (yeni): `disable_campaign_signals` autouse fixture â†’ SQLite table lock sorunu Ã§Ã¶zÃ¼ldÃ¼

**Local DB DoÄŸrulama:**
- `python manage.py migrate`: tÃ¼m migration'lar uygulandÄ± (0001-0018)
- `python manage.py check`: 0 issue
- `python manage.py makemigrations --check`: No changes detected
- PostgreSQL constraint: `placed > quota` â†’ IntegrityError doÄŸrulandÄ±

**Test SonuÃ§larÄ± (Faz 2):** 348 passed, 7 skipped, 0 failed

---

### [DOOH] Faz 2 BaÅŸlangÄ±Ã§ â€” PlacementEngine V2 Shadow Mode

**Kapsam:**
PlacementEngine V2 shadow mode. V1 scheduler korunur, deÄŸiÅŸtirilmez. V2 paralel Ã§alÄ±ÅŸÄ±r (shadow), diff metrikleri toplar. Production cutover yok.

**Ã–nkoÅŸullar (DOOH_ENGINE_V2=shadow aÃ§Ä±lmadan):**
- PostgreSQL integration testi: select_for_update/MVCC concurrency (Aâ†’B race)
- Aâ†’B target intersection validation testi (real DB)
- staging migration 0015â€“0018 apply + smoke test
- files.eisa.com.tr GET/HEAD gerÃ§ek bucket policy testi

**YapÄ±lacak:**
- placement_engine_v2.py: DeliveryRule dispatch, target_scope resolver, follows chain, slot allocation
- scheduler.py: shadow mode orchestration (V1 Ã¼retir, V2 loglar)
- ShadowRunMetric model + report_shadow_diff management command
- PostgreSQL docker-compose + concurrency testleri
- docs/ai/09-placement-engine-v2.md

### [DOOH] Faz 1 Final Denetimi â€” KoÅŸullu Kabul

**Durum:** Kod tarafÄ± tamamlandÄ±. Faz 0.5 operasyonel rollout ve PostgreSQL concurrency testleri devam ediyor.

**DeÄŸiÅŸiklikler:**
- `CampaignSerializer.validate()`: `target_scope` yeni CREATE'te zorunlu (ALL|RULES). `is_guaranteed=True` API gÃ¶nderilince 400 (aÃ§Ä±k hata). `follows` read-only (yalnÄ±z `set_campaign_follows()` servisi).
- `follows_service.py`: Tarih araligÄ± kesiÅŸimi + yayÄ±n saati kesiÅŸimi (DeliveryRule.active_hours) + CANCELLED kontrol eklendi. Unique predecessor explicit check (select_for_update iÃ§inde). Dosya ASCII unicode temizlendi.
- `Campaign` model: `dooh_campaign_follows_unique_predecessor` partial unique index â†’ migration 0018.
- `test_dooh_v2.py::test_admin_create_campaign_201`: target_scope="ALL" eklendi.
- `test_closure.py::test_c07`: `is_guaranteed=True â†’ 400` beklentisine gÃ¼ncellendi.
- `test_golden_master.py::test_gm_kiosk_ping_returns_playlist_version`: TODAY hardcoded â†’ `timezone.now().date()` (tarih-baÄŸÄ±msÄ±z).
- Vue `api.test.js login()`: Pre-existing hata dÃ¼zeltildi; `access/refresh` yerine `role/userId` beklentisine.
- Yeni test dosyasÄ±: `test_faz1_final.py` (target_scope, Aâ†’B intersection, CAMPAIGN_TOTAL quota, canonical guarantee testleri).
- Yeni Vue test: `dooh_media_flow.test.js` (uploadMedia response â†’ form state â†’ create payload canonical akÄ±ÅŸ).
- Docs gÃ¼ncellendi: 01-backend, 02-web-panels, 03-kiosk-edge, 05-cross-project-flows, 06-db-and-api-contracts, 08-dooh-advertising, implementation-plan.

**Dosyalar:** `campaigns/serializers.py`, `campaigns/services/follows_service.py`, `campaigns/models.py`, `migrations/0018_*.py`, `tests/test_dooh_v2.py`, `tests/test_closure.py`, `tests/test_golden_master.py`, `tests/test_faz1_final.py`, `web_panels/src/services/__tests__/dooh_media_flow.test.js`, `web_panels/src/services/__tests__/api.test.js`, doc dosyalarÄ±.
**Testler:** 143/143 backend (exit 0), 80/80 kiosk edge, 14/14 Vue (exit 0), Vue build âœ“.
**Migrations:** 0017 (KioskDayQuota constraints), 0018 (follows unique predecessor). Forward/backward âœ“.
**SQLite concurrency sÄ±nÄ±rÄ±:** BelgelenmiÅŸ (test_ab06); gerÃ§ek MVCC testi PostgreSQL integration gerektirir.

### [DOOH] Faz 0.5 + Faz 1 KapanÄ±ÅŸ Denetimi

**Faz 0.5 kapanÄ±ÅŸ:**
- `StorageService.public_url()` basitleÅŸtirildi: S3_PUBLIC_BASE_URL bucket dahil, sadece `base + "/" + key`. BoÅŸsa ImproperlyConfigured.
- `S3_PUBLIC_BASE_URL` sÃ¶zleÅŸmesi: `https://files.eisa.com.tr/eisa-files` (bucket dahil) â†’ `media_url = S3_PUBLIC_BASE_URL + "/" + object_key`. Bucket otomatik ekleme kaldÄ±rÄ±ldÄ±.
- `_derive_object_key_from_url` basitleÅŸtirildi: S3_PUBLIC_BASE_URL prefix'ini strip eder; path traversal korumasÄ±.
- test_settings.py: `S3_PUBLIC_BASE_URL = "http://localhost:9000/dev"` (bucket dahil).
- `CampaignWizard.vue`: `uploadMedia` response'tan `media_url`, `object_key`, `checksum` canonical olarak alÄ±nÄ±r; `createCreative` bu 3 alanÄ± gÃ¶nderir; `data.url` yalnÄ±z legacy fallback.

**Faz 1 kapanÄ±ÅŸ:**
- `HouseAdSerializer`: `is_grid_compliant` + `validate_duration_seconds` grid validasyonu eklendi.
- `CreativeSerializer.validate_duration_seconds()`: grid validasyonu (yeni/deÄŸiÅŸen â†’ 15/30/45/60 zorunlu; legacy aynÄ± deÄŸer korunur).
- `CampaignSerializer.is_guaranteed`: `read_only_fields`'e eklendi (canonical kaynak: DeliveryRule.guarantee_mode).
- `DeliveryRuleSerializer.validate()`: `LEGACY_PER_LOOP` yazÄ±lmasÄ±nÄ± reddeder.
- `KioskDayQuota`: `placed>=0`, `quota>=0`, `placed<=quota` CheckConstraint eklendi â†’ migration 0017.
- Yeni `apps/campaigns/services/follows_service.py`: `set_campaign_follows()` â€” transaction.atomic + select_for_update; self-link, zincir derinliÄŸi, dÃ¶ngÃ¼ korumasÄ±.
- Yeni `tests/test_closure.py`: 26 kapanÄ±ÅŸ testi (C01â€“C19).

**Migration:** 0017 (KioskDayQuota constraints). Forward âœ“, backward âœ“, check âœ“.
**Testler:** 123/123 backend, 80/80 kiosk edge, Vue build âœ“.

### [DOOH] Faz 1 â€” Additive Domain Schema + Legacy Compatibility

**DeÄŸiÅŸiklik:**
- `Campaign`: `DRAFT`/`CANCELLED` status; `target_scope` (ALL|RULES|null); `follows` FK (self, null); `effective_state` property (SCHEDULED tÃ¼retilmiÅŸ); `is_guaranteed`/`impression_goal`/`frequency_cap_per_hour` deprecate notu eklendi.
- `CampaignTarget`: `KIOSK` target type; `kiosk` FK; `mode` (INCLUDE|EXCLUDE|null).
- `Creative`: `weight` (default=1); `is_grid_compliant` property.
- `HouseAd`: `is_grid_compliant` property.
- `PlayLog`: `play_event_id` (UUID, null=True â€” K5 adÄ±m A).
- Yeni modeller: `DeliveryRule` (delivery_type/count/window/active_hours/guarantee_mode), `PlanningRun`, `CampaignTotalAllocation`, `KioskDayQuota`, `KioskDesiredBundle`.
- Migration 0016 (additive, reversible). Forward/backward âœ“. `makemigrations --check` âœ“.
- Yeni management command: `report_grid_noncompliant_media`.
- Serializer gÃ¼ncellemeleri: `CreativeSerializer`+weight+is_grid_compliant, `CampaignTargetSerializer`+kiosk+mode, `CampaignSerializer`+effective_state+target_scope+follows, yeni `DeliveryRuleSerializer`.

**Dosyalar:** `campaigns/models.py`, `campaigns/serializers.py`, `campaigns/migrations/0016_faz1_additive_schema.py`, `management/commands/report_grid_noncompliant_media.py`, `campaigns/tests/test_faz1_schema.py`.
**Testler:** 97/97 (44 yeni Faz 1 testi; tÃ¼m golden-master ve Faz 0.5 testleri yeÅŸil).
**Not:** ScheduleRule dual-read korunuyor; DeliveryRule eklendi. `DOOH_DELIVERY_RULE_MODEL` feature flag Faz 2'de; Faz 1'de model ÅŸemasÄ± yeterli.

---

## 2026-07-21

### [DOOH] Faz 0.5 â€” KalÄ±cÄ± Medya URL (v2 â€” tamamlandi)

**DeÄŸiÅŸiklik:**
- **URL format dogrulandi:** Production `S3_ENDPOINT=files.eisa.com.tr` + `S3_BUCKET=eisa-files` + `S3_FORCE_PATH_STYLE=True` â†’ kalici URL = `https://files.eisa.com.tr/eisa-files/<object_key>`. Bucket adi path'e dahil.
- `StorageService`: `upload_file_with_checksum()` (64KB chunk streaming SHA-256, iki geÃ§is), `public_url()` (bucket-aware, path-style).
- `MediaUploadView`: `DOOH_PERSISTENT_MEDIA_URL` feature flag (False=legacy, True=kalici). Response: `{object_key, media_url, checksum, url, filename, object_name}`.
- `Creative` + `HouseAd`: `object_key (null=True, blank=True)` â€” K5 additive. Migration 0015.
- `_derive_object_key_from_url`: bucket-aware, path traversal korumasi, presigned/yabanci host reddeder.
- `backfill_media_object_keys`: guvenlik sertlestirme (host whitelist, bucket/path dogrulama, path traversal, URL decode, --apply=HEAD zorunlu, --skip-head-check-DANGEROUS).
- `settings.py`: `S3_PUBLIC_BASE_URL` (opsiyonel override), `DOOH_PERSISTENT_MEDIA_URL` flag.

**Dosyalar:** `storage_service.py`, `campaigns/views.py`, `campaigns/models.py`, `campaigns/serializers.py`, `migrations/0015_*.py`, `management/commands/backfill_media_object_keys.py`, `settings.py`, `test_settings.py`, `web_panels/src/services/dooh.js`. Kiosk: `tests/mediaCache.test.js` (8 yeni test, KC-01..KC-08).
**Testler:** Backend 53/53 (test_persistent_media.py 19 yeni: M01..M15 + 2 integrasyon + 2 golden kontrol), kiosk edge 80/80.
**Etki:** `media_url` kalici URL â†’ kiosk `source_url` stabil â†’ gereksiz yeniden-indirme ortadan kalkar. DOOH_PERSISTENT_MEDIA_URL=True ile aktif; False (varsayilan) legacy rollback.

**DeÄŸiÅŸiklik:**
- `StorageService`: `upload_file_with_checksum()` (SHA-256 stream + dÃ¶ner `(object_key, checksum)`) ve `public_url()` (stabil `S3_PUBLIC_BASE_URL/object_key`) eklendi.
- `MediaUploadView`: Presigned yerine kalÄ±cÄ± URL dÃ¶ner. Response: `{object_key, media_url, checksum, url, filename, object_name}`. `url`/`object_name` geriye-uyumlu alias.
- `Creative` + `HouseAd` modeline `object_key` (CharField, blank, additive migration).
- `CreativeSerializer` + `HouseAdSerializer`: `object_key` alanÄ± eklendi; `media_url` S3_PUBLIC_BASE_URL ile baÅŸlÄ±yorsa `object_key` otomatik tÃ¼retilir.
- `settings.py`: `S3_PUBLIC_BASE_URL` (prod'da zorunlu, boÅŸsa `ImproperlyConfigured`). `test_settings.py`: varsayÄ±lan set edildi.
- Yeni migration: `0015_creative_object_key_housead_object_key.py`.
- Yeni management command: `backfill_media_object_keys` (dry-run varsayÄ±lan, --apply, --head-check).

**Dosyalar:** `storage_service.py`, `campaigns/views.py`, `campaigns/models.py`, `campaigns/serializers.py`, `campaigns/migrations/0015_*.py`, `management/commands/backfill_media_object_keys.py`, `settings.py`, `test_settings.py`, `web_panels/src/services/dooh.js`.
**Testler:** `test_persistent_media.py` (14 yeni test: M01â€“M12 + 2 entegrasyon). 48/48 yeÅŸil.
**Etki:** Kiosk playlist contract `media_url` alanÄ± korunur; deÄŸeri kalÄ±cÄ± `https://files.eisa.com.tr/...` URL'si. `mediaCache.js` `source_url` stabileÅŸince gereksiz yeniden-indirme Ã§Ã¶zÃ¼lÃ¼r.

---

### [DOOH] Faz 0 â€” Golden-Master / Characterization Testleri

### [Backend] â€” OturumCevap/OturumOnerilenEtkenMadde Veri KaybÄ± DÃ¼zeltmesi

**DoÄŸrulanan sorunlar (canlÄ± shell ile kanÄ±tlandÄ±):**
1. **OturumOnerilenEtkenMadde merge hatasÄ± (KRÄ°TÄ°K):** `get_or_create(etken_madde=None, defaults={"snapshot": name})` â€” FK null iken ikinci ve sonraki string malzeme adlarÄ± birinci kaydÄ±n `defaults`'Ä±nÄ± gÃ¼ncellemek yerine onu GET ediyordu. `["Melatonin","Valerian","B12"]` â†’ 3 beklenen kayÄ±t yerine 1 kaydediliyordu. Kiosk recommendation engine string isimler dÃ¶ndÃ¼rdÃ¼ÄŸÃ¼ iÃ§in her SIKAYET session'Ä±nda veri kaybÄ± oluÅŸuyordu.
2. **`cevap_metni_snapshot` format sorunu:** Binary "Y"/"N" deÄŸerleri iÃ§in `cevap_metni_snapshot = "Y"` kaydediliyordu; insan-okunur "Evet"/"HayÄ±r" yerine. `cevap_degeri_snapshot` zaten raw "Y"/"N" deÄŸerini saklÄ±yor.

**DÃ¼zeltmeler (`backend/apps/analytics/services.py` `_create_child_records`):**
- `OturumOnerilenEtkenMadde`: FK mevcut ise `get_or_create(etken_madde=em)`; FK null ise `get_or_create(etken_madde=None, etken_madde_adi_snapshot=name)` â€” snapshot isim lookup'a dahil edildi, merge engellendi.
- `cevap_metni_snapshot`: `{"Y": "Evet", "N": "HayÄ±r"}` eÅŸleÅŸmesi ile insan-okunur deÄŸer saklanÄ±r.

**DeÄŸiÅŸmeyen davranÄ±ÅŸlar:**
- OturumCevap: SIKAYET'te soru FK her zaman non-null (raise ile korunuyor) â†’ merge riski yok. âœ“
- QR sorgu (`get_cevap_detaylari`): JSON backup `obj.cevaplar`'dan okur â†’ `_answer_text_from_value("Y") = "Evet"` zaten doÄŸru. âœ“
- `onerilen_etken_madde_detaylari` QR gÃ¶rÃ¼nÃ¼mÃ¼: `obj.onerilen_etken_maddeler` JSON'dan okur â†’ tÃ¼m adlar gÃ¶rÃ¼nÃ¼r. âœ“

**Soru 6 (GerÃ§ek Cevap ID'leri):** Daha doÄŸru olur; gereklilikler: kiosk sorular API'ye cevaplar eklenmesi + QuestionScreen'in cevap_id dispatch etmesi + App.svelte'in cevap_id saklamasÄ±. Mevcut binary Y/N + snapshot yaklaÅŸÄ±mÄ± QR sorgusu iÃ§in yeterli; analitik normalize tablolar iÃ§in gelecekte eklenebilir.

**Test:** `apps/analytics/tests/test_session_normalization.py` â€” 33/33 (2 yeni test: `test_sikayet_multiple_binary_answers_no_merge`, `test_multiple_string_ingredients_all_saved` â€” regresyon koruma)
**Migration:** Yok (uygulama mantÄ±ÄŸÄ± deÄŸiÅŸikliÄŸi; DB ÅŸemasÄ± deÄŸiÅŸmedi)

, Ã‡ift GÃ¶nderim KorumasÄ±, Scheduler Outbox Fix

**KÃ¶k Nedenler:**
1. **207 â†’ 502 hatasÄ±:** `server.js` backend 207 dÃ¶ndÃ¼rdÃ¼ÄŸÃ¼nde item `errors[]`'a dÃ¼ÅŸmÃ¼ÅŸse `resultItem` bulunamÄ±yor, `backendQr = null` â†’ 502.
2. **Ã‡ift gÃ¶nderim:** `api.js` `retry: 1`; Node 502 dÃ¶nÃ¼nce `_request` retry yapÄ±yor; her istekte Node yeni UUID Ã¼retiyor â†’ 2 farklÄ± Django isteÄŸi.
3. **Scheduler outbox bug:** `consumeBulkPushResponse` `body.accepted_keys` arÄ±yordu; backend aslÄ±nda `body.results[].idempotency_key` dÃ¶ndÃ¼rÃ¼yor â†’ outbox kayÄ±tlarÄ± hiÃ§bir zaman "gÃ¶nderildi" iÅŸaretlenmiyordu.

**DeÄŸiÅŸiklikler:**

**`kiosk_edge/api-node/src/server.js`:**
- `tamamlandi=true` akÄ±ÅŸÄ± tamamen yeniden yazÄ±ldÄ±: Ã¶nce outbox'a kaydet (INSERT OR IGNORE), sonra backend'e gÃ¶nder.
- 207 + `errors[]` â†’ 422 (`backend_rejected`), outbox'ta kalÄ±r, `retry_count=99` (sonsuz retry engeli).
- Backend eriÅŸilemez â†’ 503 (`backend_unreachable`/`backend_error`), outbox kaydÄ± korunur; artÄ±k yanÄ±ltÄ±cÄ± 502 dÃ¶nmez.
- Idempotent re-delivery: `gonderilme_tarihi` set + `qr_kodu` mevcut â†’ backend Ã§aÄŸrÄ±sÄ± yapÄ±lmadan mevcut QR dÃ¶ner.
- `idempotency_anahtari` artÄ±k body'den alÄ±nÄ±r (UI'dan `sessionId` geliyor); yoksa yeni UUID Ã¼retilir.
- `tamamlandi=false` inline path: 207'de sadece `results[]`'dakiler gÃ¶nderildi iÅŸaretlenir.
- YapÄ±sal log eklendi: `event`, `upstream_status`, `kiosk_id`, `batch_size`, `accepted/duplicate/rejected_count`. Secret, QR, kiÅŸisel veri loglanmaz.

**`kiosk_edge/api-node/src/scheduler.js`:**
- `OUTBOX_MAX_RETRY = 10` sabiti eklendi.
- `oturum_outbox` query: `retry_count < OUTBOX_MAX_RETRY` filtresi eklendi (kalÄ±cÄ± hatalÄ± kayÄ±tlar atlanÄ±r).
- `consumeBulkPushResponse` tamamen yeniden yazÄ±ldÄ±: `body.accepted_keys` â†’ `body.results[].idempotency_key` (gerÃ§ek backend ÅŸemasÄ±). Kabul edilenler: `UPDATE gonderilme_tarihi`. Reddedilenler: `retry_count++`, `error_reason` kaydedilir.

**`kiosk_edge/api-node/src/db.js`:**
- `oturum_outbox` tablosuna `retry_count INTEGER NOT NULL DEFAULT 0` ve `error_reason TEXT` eklendi.
- Non-destructive migration: `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` (veri kaybÄ± yok).

**`kiosk_edge/api-node/src/validators.js`:**
- `oturumGonderSchema`'ya `idempotency_anahtari` (optional UUID) eklendi.

**`kiosk_edge/ui/src/lib/api.js`:**
- `submitSession`: `sessionId` parametresi eklendi, `idempotency_anahtari` body'ye dahil edildi.
- `retry: 1` â†’ `retry: 0` (idempotency outbox garantisi; Ã§ift kayÄ±t riski ortadan kalktÄ±).

**`kiosk_edge/ui/src/App.svelte`:**
- `sessionSubmitting` flag eklendi (aktif HTTP Ã§aÄŸrÄ±sÄ± sÄ±rasÄ±nda Ã§ift tetikleme engeli).
- `selectConsult`: `sessionSubmitting` guard eklendi; hÄ±zlÄ± Ã§ift dokunma korumasÄ±.
- `doSubmitSession` ve `doSubmitConsult`: `sessionId` (dÄ±ÅŸ scope) `submitSession`'a geÃ§irildi.
- `resetToIdle`: `sessionSubmitting = false` eklendi.

**`kiosk_edge/api-node/tests/server.test.js`:**
- 12 yeni senaryo testi eklendi (vi.mock ile requestWithRetry mock'landÄ±).
- Senaryo 1-12: 200/existing/207-partial/401/403/500/eriÅŸilemez/idempotency/double-submit/kabul-iÅŸaret/red-iÅŸaret/secret log.

**`kiosk_edge/api-node/tests/helpers.js`:**
- `oturum_outbox` ÅŸemasÄ±na `retry_count`, `error_reason` eklendi.

**Test:** `npm test` â†’ 72/72 geÃ§ti (5 test dosyasÄ±).
**Breaking:** Yok. `POST /api/oturum/gonder` response'a `sync_durum` alanÄ± eklendi (geriye uyumlu).
**Migration:** Yok (SQLite non-destructive ALTER TABLE).



### [Backend + kiosk_edge + UI] â€” Device ID, Session Normalization, QR Unique, Consultation Type
**DeÄŸiÅŸiklik:** Kiosk persistent device identity, session analytics normalization, QR unique constraint, ve consultation session type eklendi.
**Backend:** `Kiosk.device_id` (nullable unique), `KioskProvisioningRequest.device_id` eklendi. Bootstrap HMAC artÄ±k `MAC + timestamp + device_id` iÃ§eriyor. Auth: `X-Kiosk-Device-ID` header'Ä± zorunlu (device_id set edildiyse). `OturumLogu`: `oturum_tipi` (SIKAYET/OZEL_DANISMANLIK), `danisma_kategorisi` FK, `kategori` nullable yapÄ±ldÄ±, `qr_kodu` unique constraint. Yeni modeller: `OturumCevap` (oturumâ†’soruâ†’cevap normalize, snapshot), `OturumOnerilenEtkenMadde` (oturumâ†’etken_madde normalize, snapshot). `analytics.services.generate_qr_candidate()` (IntegrityError retry + savepoint), `ingest_session_items()` oturum tipi validation (SIKAYET/OZEL_DANISMANLIK) + soru-cevap uyum kontrolÃ¼ (strict 400) + child record creation + transaction. JSON fieldlar backup olarak korundu (expand/contract pattern). `/api/kiosk/v1/identity/enroll/` endpoint'i (tek-seferlik device_id baÄŸlama). Migration: `0007_kiosk_device_id.py` (pharmacies), `0006_session_normalization.py`, `0007_qr_cleanup.py`, `0008_qr_unique_constraint.py` (analytics).
**Kiosk edge:** `provisioning.js`: `crypto.randomUUID()` ile `device_id` Ã¼retimi, SQLite `kiosk_meta`'ya kaydedildi. Bootstrap request'e `device_id` parametresi, HMAC'e dahil edildi. `getAuthHeaders()`: `X-Kiosk-Device-ID` header'Ä± eklendi. `server.js`: Session payload'a `oturum_tipi`, `kategori_slug` (nullable), `danisma_kategorisi_slug` (nullable) eklendi. `validators.js`: `oturumGonderSchema` gÃ¼ncellendu.
**UI:** `App.svelte` + `api.js`: `submitSession()` parametrelerine `oturumTipi`, `categorySlug`, `danismaKategorisiSlug` eklendi. Consultation flow `oturum_tipi=DANISMANLIK` olarak gÃ¶nderiliyor.
**Test:** Backend 137/137 (analytics + pharmacies + kiosk_api), kiosk_edge 49/49, UI build baÅŸarÄ±lÄ±. Duplicate QR fix script ile mevcut collision'lar temizlendi.
**Breaking:** Bootstrap HMAC artÄ±k device_id iÃ§eriyor (eski kiosk'lar legacy MAC-only ile Ã§alÄ±ÅŸmaya devam eder ama yeni kiosk'lar device_id set olana kadar auth alamaz). QR unique constraint DB'de enforce edildi.

### [Backend + kiosk_edge] â€” Kiosk API Facade + Tek App Key Authentication (IoT/dual auth kaldÄ±rÄ±ldÄ±)
**DeÄŸiÅŸiklik:** KiosklarÄ±n Main API ile tÃ¼m operasyonel iletiÅŸimi tek namespace, tek auth ve tek merkezi client altÄ±nda toplandÄ±.
**Backend:** Yeni `apps/kiosk_api/` facade uygulamasÄ± (authentication/permissions/mixins/views/urls/serializers/tests). TÃ¼m operasyonel kiosk endpoint'leri `/api/kiosk/v1/` altÄ±nda ve **kiosk ID iÃ§ermez** (`request.kiosk` auth context'inden gelir): `bootstrap, ping, sync, catalog, playlist, sessions, proof-of-play, diagnostics`. Facade domain mantÄ±ÄŸÄ±nÄ± kopyalamaz; mevcut model+serializer'larÄ± ve yeni domain servislerini (`analytics.services.ingest_session_items`, `products.services.build_catalog_payload`, `analytics.log_ingest.ingest_kiosk_diagnostic_items`) yeniden kullanÄ±r.
**Auth:** Tek operasyonel sÄ±nÄ±f `KioskAppKeyAuthentication` (`Authorization: AppKey <key>` + `X-Kiosk-MAC`); `request.kiosk` atar; **401** (App Key/MAC eksik/geÃ§ersiz) ve **403** (kiosk pasif/onaysÄ±z/eczanesiz) ayrÄ±mÄ± + makine-okunur `code`. `KioskIoTTokenAuthentication`, `create_iot_token`, `verify_iot_token`, `_create_iot_token_for_kiosk`, `KIOSK_IOT_TOKEN_TTL_DAYS` **tamamen kaldÄ±rÄ±ldÄ±** (fiziksel kolon yok â†’ migration yok). Bootstrap artÄ±k `iot_token` yerine **`app_key`** dÃ¶ner (APPROVED/PENDING/REJECTED). Bootstrap `pharmacies` app'inden facade'e taÅŸÄ±ndÄ±; eski `/api/pharmacies/kiosks/bootstrap/` ve `/api/kiosk/v1/{id}/...` route'larÄ± kaldÄ±rÄ±ldÄ± (hard cutover). Provisioning admin API'leri (`/api/pharmacies/kiosks/provisioning/*`) ve panel endpoint'leri deÄŸiÅŸmedi.
**Kiosk edge:** `provisioning.js` App Key'i bootstrap yanÄ±tÄ±ndan SQLite `kiosk_meta`'ya yazar; `getAuthHeaders(db)` her istekte SQLite'tan `kiosk_app_key`+`kiosk_mac` okur (freeze/stale sorunu Ã§Ã¶zÃ¼ldÃ¼, restart gerekmez); IoT/Bearer/Fleet Ã¼retimi kaldÄ±rÄ±ldÄ±; `handle401Error`/`handle403Error` App Key'i **silmez**, backoff uygular; `cleanupLegacyIotToken` eski `iot_token`'Ä± bir defalÄ±k siler. `config.js` yalnÄ±z `EISA_KIOSK_FLEET_KEY`+`EISA_KIOSK_PROVISIONING_SECRET` credential okur (App Key/MAC/ID/pharmacy env fallback kaldÄ±rÄ±ldÄ±; MAC otomatik tespit + SQLite'ta sabit). `scheduler.js` tÃ¼m Ã§aÄŸrÄ±lar merkezi client'tan yeni `/api/kiosk/v1/` endpoint'lerine; 401+403 ayrÄ±. `server.js` anlÄ±k session `/api/kiosk/v1/sessions/`'e, koÅŸul `hasAppKeyCredentials(db)`. `db.js` SQLite dizin `700` / dosya `600` (Linux).
**Migration:** Yok. Mevcut `Kiosk.uygulama_anahtari` kullanÄ±ldÄ±; yeni tablo/kolon yok.
**Test:** Backend 153/153 (yeni `apps/kiosk_api/tests` dahil), kiosk-edge 49/49 (yeni `provisioning.test.js`). `conftest.eczane` fixture'Ä± Il/Ilce iÃ§in `get_or_create`'e Ã§evrildi (Ã¶nceden kÄ±rÄ±k, DOOH testlerini de dÃ¼zeltti). `server.test.js`'teki iki eski QR beklentisi 8 karakter bitpack QR'a hizalandÄ± (mevcut davranÄ±ÅŸ).
**Breaking:** Operasyonel kiosk auth artÄ±k yalnÄ±z App Key + MAC; Bearer/IoT/Fleet/JWT reddedilir. `/api/kiosk/v1/{id}/...` ve `/api/pharmacies/kiosks/bootstrap/` kaldÄ±rÄ±ldÄ±. Bootstrap `iot_token` yerine `app_key` dÃ¶ner.

### [analytics + web_panels + kiosk_edge] â€” EczacÄ± QR sorgu dÃ¼zeltmesi, kamera kaldÄ±rma, detay response normalizasyonu
**DeÄŸiÅŸiklik:** EczacÄ± QR sorgusunda endpoint/contract uyumsuzluklarÄ± dÃ¼zeltildi. `GET /api/analytics/sessions/` QR parametresi ile Ã§aÄŸrÄ±ldÄ±ÄŸÄ±nda 400/403/404 ayrÄ±mÄ± netleÅŸti; eczane sahipliÄŸi backend'de zorunlu hale getirildi. Response mevcut alanlar korunarak normalize edildi (`kiosk_detay`, `eczane`, `yas_araligi_detay`, `cinsiyet_detay`, `kategori_detay`, `cevap_detaylari`, `onerilen_etken_madde_detaylari`, `satis_sonucu`).
**Frontend:** `QrScan.vue` ekranÄ±ndan kamera akÄ±ÅŸÄ± tamamen kaldÄ±rÄ±ldÄ± (getUserMedia/BarcodeDetector/video state yok). Sayfa input-focus ile aÃ§Ä±lÄ±r; barkod okuyucu Enter ile tek istek tetikler; loading sÄ±rasÄ±nda Ã§ift istek engellenir; hata/baÅŸarÄ± durumlarÄ±nda input yeniden focus alÄ±r. Hata mesajlarÄ± ayrÄ±ÅŸtÄ±rÄ±ldÄ±: boÅŸ, format, bulunamadÄ±, baÅŸka eczane.
**Kiosk edge:** `POST /api/oturum/gonder` response ve backend'e gÃ¶nderilen `qr_kodu` deÄŸeri 8 karakter bitpack QR ile hizalandÄ±; QR Ã¼retim algoritmasÄ± deÄŸiÅŸtirilmedi.
**DanÄ±ÅŸma tamamlama:** `POST /api/analytics/sessions/{id}/complete/` isteÄŸi opsiyonel `sale_result` alÄ±r (`sold|not_sold`). Not: satÄ±ÅŸ sonucu iÃ§in kalÄ±cÄ± DB kolonu yok; mevcut ÅŸema korunmuÅŸtur (migration yok).
**Test/Build:** Backend `apps/analytics/tests/test_qr_flow.py` eklendi ve geÃ§ti. Web build baÅŸarÄ±lÄ±. Frontend unit testlerinde pre-existing bir `api.test.js` beklenti uyumsuzluÄŸu devam ediyor. Tam backend suite'te pre-existing `campaigns` testlerinde lookup fixture kaynaklÄ± hatalar mevcut.

---

## 2026-07-16

### [TÃ¼m modÃ¼ller] â€” Merkezi Loglama: JSON stdout + Correlation ID + Diagnostic Outbox
**DeÄŸiÅŸiklik:** Kubernetes uyumlu yapÄ±sal loglama altyapÄ±sÄ± kuruldu. Uygulamalar dosyaya log YAZMIYOR; JSON stdout Ã¼retiyor. Loki/Alloy/Grafana bu gÃ¶revde kurulmadÄ±.
**Backend:** `apps/core/logging/` paketi (JSON formatter + correlation middleware + redaction), settings dosyasÄ±nda RotatingFileHandler kaldÄ±rÄ±ldÄ±, `LOG_LEVEL`/`LOG_FORMAT`/`SERVICE_NAME`/`APP_ENV`/`APP_VERSION` env eklendi. Yeni endpoint'ler: `POST /api/analytics/diagnostic-ingest/` (kiosk auth, DB'ye YAZMAZ, JSON stdout), `POST /api/analytics/client-events/` (JWT auth, rate limited). `X-Correlation-ID` her response'a eklenir; exception handler double-log'u engellemek iÃ§in `_eisa_exception_logged` bayraÄŸÄ± kullanÄ±r.
**Fastify:** Pino JSON stdout, `logRedaction.js` (Authorization/token/qr_kodu/cevaplar vb. maskelenir), `correlationId.js` AsyncLocalStorage, `diagnosticOutbox.js` (SQLite v10: max 5000 kayÄ±t, 7 gÃ¼n, batch 100, exponential backoff, FIFO trigger), scheduler `pushDiagnostics()` + `X-Correlation-ID` propagation. Yeni endpoint: `POST /api/log/client` (Svelte UI hata kÃ¶prÃ¼sÃ¼).
**Vue:** `src/lib/logger.js` production-safe wrapper, `app.config.errorHandler` + `window.onerror` + `unhandledrejection`, axios interceptor `X-Correlation-ID` yakalar; kritik hatalar backend'e allow-list ile bildirilir.
**Svelte:** `src/lib/logger.js` yerel Fastify'ye rate-limited hata kÃ¶prÃ¼sÃ¼ (yalnÄ±zca `screen_render_failed`, `local_api_unreachable`, `media_playback_failed`, `session_submit_failed`, `playlist_invalid` + tarayÄ±cÄ± global'leri).
**Docker/K8s:** `EISA_LOG_DIR`, `DJANGO_LOG_DIR`, log emptyDir/PVC, `/app/logs` mount, kiosk `/var/log/eisa` volume kaldÄ±rÄ±ldÄ±; standart label seti (`app.kubernetes.io/component`, `.../version`) eklendi.
**AuditLog / OturumLogu / PlayLog dokunulmadÄ±** â€” iÅŸ kayÄ±tlarÄ± PostgreSQL'de kalÄ±yor.
**Testler:** Backend 76/76 (test_logging.py), Fastify 42/42 (12 yeni). web_panels + kiosk_edge/ui build baÅŸarÄ±lÄ±. Not: `apps/campaigns/tests/test_dooh_v2.py` ve `web_panels api.test.js` pre-existing (bu gÃ¶rev Ã¶ncesi) hatalar; loglama deÄŸiÅŸiklikleriyle ilgisi yok.
**DokÃ¼man:** `docs/operations/logging.md` (yeni), 01/02/03/04/05 kÄ±saca gÃ¼ncellendi.
**Breaking:** Yok. Eski `error_id` alanÄ± 500 yanÄ±tlarÄ±nda `correlation_id` ile deÄŸiÅŸti â€” panel bunu gÃ¶stermek istiyorsa alan adÄ±na dikkat etmeli.

---


### [kiosk_edge/ui] â€” Dead Code TemizliÄŸi: SensitiveScreen KaldÄ±rÄ±ldÄ±
**DeÄŸiÅŸiklik:** Runtime'da hiÃ§bir yerden Ã§aÄŸrÄ±lmayan `SensitiveScreen.svelte` silindi. YalnÄ±z bu dosyada kullanÄ±lan Ã¶lÃ¼ CSS selector'larÄ± (`.cat-card.sensitive*`, `.sensitive-badge`, `.sensitive-info-box`) temizlendi. `stores/kiosk.js` ekran state yorumu gerÃ§ek akÄ±ÅŸla hizalandÄ± (`sensitive` â†’ `consult`).
**Dosyalar:** `kiosk_edge/ui/src/components/SensitiveScreen.svelte` (silindi), `kiosk_edge/ui/src/app.css`, `kiosk_edge/ui/src/stores/kiosk.js`
**Breaking:** Yok (aktif akÄ±ÅŸ `ConsultScreen` Ã¼zerinden devam ediyor).
**Test:** `npm test`, `npm run build` (kiosk_edge/ui)

---

## 2026-07-14

### [kiosk_edge] â€” Bootstrap Ä°steÄŸine Cihaz Metadata Eklendi
**DeÄŸiÅŸiklik:** `provisioning.js`'e `collectDeviceMetadata()` fonksiyonu eklendi. Bootstrap isteÄŸi artÄ±k `hostname` ve `device_metadata` gÃ¶nderir.
**Toplanan alanlar:** hostname, os_type, os_platform, os_release, arch, cpu_model, cpu_cores, total_memory_mb, ip_addresses (iface+IPv4), node_version, uptime_seconds.
**GÃ¼venlik:** Her alan `try/catch` iÃ§inde; token/secret/hmac iÃ§ermiyor; `collectDeviceMetadata` export edildi.
**Dosyalar:** `kiosk_edge/api-node/src/provisioning.js`
**Breaking:** Yok (bootstrap body yeni isteÄŸe baÄŸlÄ± alanlar aldÄ±; backend zaten kabul ediyordu).

### [web_panels] â€” Dashboard Pending Devices Banner + PendingDevices UX Ä°yileÅŸtirme
**DeÄŸiÅŸiklik:** Dashboard'a `pendingCount > 0` olduÄŸunda sarÄ± uyarÄ± banner'Ä± eklendi (`/admin/devices/pending` linki ile). PendingDevices.vue: eczane seÃ§imi `<select>`'ten `EisaLookup` autocomplete'e Ã§evrildi (ad/il/ilÃ§e arama); metadata detay modalÄ± yapÄ±landÄ±rÄ±lmÄ±ÅŸ gÃ¶rÃ¼nÃ¼me (insan okunur etiketler, IP listesi, uptime formatlÄ±) geÃ§irildi.
**Dosyalar:** `web_panels/src/views/admin/Dashboard.vue`, `PendingDevices.vue`, `services/devices.js`
**Breaking:** Yok.

---

## 2026-07-14

### [Backend + web_panels + kiosk_edge] â€” Onay Bekleyen Cihaz Provisioning AkÄ±ÅŸÄ±
**DeÄŸiÅŸiklik:** KayÄ±tsÄ±z kiosklar iÃ§in uÃ§tan uca IoT cihaz kayÄ±t ve onay sistemi eklendi.
**Backend:** `KioskProvisioningRequest` modeli (PENDING/APPROVED/REJECTED lifecycle), migration 0006, `KioskBootstrapView` gÃ¼ncellendi (202 PENDING / 403 REJECTED), admin provisioning API endpoints (`/api/pharmacies/kiosks/provisioning/` list/detail/approve/reject).
**web_panels:** `PendingDevices.vue` yeni view, `/admin/devices/pending` route, AdminLayout nav item, `devices.js` service fonksiyonlarÄ± eklendi.
**kiosk_edge:** `provisioning.js` durum makinesi (UNREGISTEREDâ†’PENDING_APPROVALâ†’APPROVED/REJECTED), `scheduler.js` bootstrap retry, `getProvisioningState` export edildi.
**GÃ¼venlik:** fleet_key/provision_secret DB/log/UI'da saklanmaz; sabit zaman karÅŸÄ±laÅŸtÄ±rma korundu; onay transaction+select_for_update ile race condition gÃ¼venli; pending cihaz normal API'lere eriÅŸemez.
**Dosyalar:** `pharmacies/models.py`, `pharmacies/migrations/0006_*.py`, `pharmacies/serializers.py`, `pharmacies/views.py`, `pharmacies/urls.py`, `pharmacies/tests/test_provisioning.py`, `web_panels/.../PendingDevices.vue`, `devices.js`, `router/index.js`, `AdminLayout.vue`, `kiosk_edge/api-node/src/provisioning.js`, `scheduler.js`. **DokÃ¼man:** 00-AI-INDEX, 01-backend, 02-web-panels, 03-kiosk-edge-api-node, 05-cross-project-flows, 06-db-and-api-contracts gÃ¼ncellendi.
**Test:** 24/24 backend testi geÃ§ti.
**Breaking:** KioskBootstrapView davranÄ±ÅŸÄ± deÄŸiÅŸti: bilinmeyen MAC artÄ±k 404 yerine 202 dÃ¶ndÃ¼rÃ¼yor.

---

## 2026-07-07

### Kiosk Edge â€” SQLite FK KaldÄ±rma + QR AnÄ±nda Sync + ConsultScreen Visual Temizlik
**DeÄŸiÅŸiklik:** 3 kiosk iyileÅŸtirmesi yapÄ±ldÄ±: (1) SQLite foreign key constraint'leri kaldÄ±rÄ±ldÄ±, (2) QR oluÅŸtuÄŸunda session anÄ±nda backend'e iletilir, (3) DanÄ±ÅŸma kategori ikonlarÄ±nÄ±n altÄ±ndaki "X alt konu" yazÄ±sÄ± kaldÄ±rÄ±ldÄ± (alt kategori yapÄ±sÄ± korundu).
**Detay:**
1. **SQLite FK kaldÄ±rma:** `db.js` schema'sÄ±ndan tÃ¼m `REFERENCES` clause'larÄ± kaldÄ±rÄ±ldÄ± (kategoriler, danisma_kategorileri, sorular, cevaplar, M2M tablolar). Backend zaten veri bÃ¼tÃ¼nlÃ¼ÄŸÃ¼nÃ¼ saÄŸladÄ±ÄŸÄ± iÃ§in lokal DB'de gereksiz kontroller kaldÄ±rÄ±ldÄ±. `scheduler.js` PRAGMA foreign_keys komutlarÄ± temizlendi.
2. **QR anÄ±nda sync:** `server.js` POST `/api/oturum/gonder` endpoint'i gÃ¼ncellendi â†’ `tamamlandi=true` olduÄŸunda anÄ±nda backend'e `POST /api/analytics/sessions/` yapÄ±lÄ±r (exponential backoff retry ile). BaÅŸarÄ±lÄ± olursa outbox kaydÄ± `gonderilme_tarihi` iÅŸaretlenir; baÅŸarÄ±sÄ±z olursa scheduler tekrar dener. `scheduler.js` `requestWithRetry` fonksiyonu export edildi.
3. **ConsultScreen visual temizlik:** `ConsultScreen.svelte` kategori ikonlarÄ±nÄ±n altÄ±ndaki conditional "X alt konu" badge kaldÄ±rÄ±ldÄ± (lines 63-65). Alt kategori navigation yapÄ±sÄ± (activeParent, selectParent, selectChild, backToParents) tamamen korundu; sadece gÃ¶rsel sayÄ± gÃ¶sterimi kaldÄ±rÄ±ldÄ±.
**Dosyalar:** `kiosk_edge/api-node/src/db.js`, `scheduler.js` (export requestWithRetry), `server.js` (immediate sync), `kiosk_edge/ui/src/components/ConsultScreen.svelte`
**DokÃ¼man:** 03-kiosk-edge-api-node.md, 04-kiosk-edge-ui.md, 07-session-and-analytics.md gÃ¼ncellendi.
**Test:** Container rebuild, sync success, 41 kategori + 6 danÄ±ÅŸma + 104 etken madde + 8 lookup baÅŸarÄ±yla senkronize edildi.
**Breaking:** Yok.

---

## 2026-07-01

### Kiosk UI â€” Normal Idle EkranÄ± KaldÄ±rÄ±ldÄ± + BileÅŸen Refactor
**DeÄŸiÅŸiklik:** AÃ§Ä±lÄ±ÅŸta gelen "normal idle" bekleme ekranÄ± kaldÄ±rÄ±ldÄ±; uygulama artÄ±k doÄŸrudan Ã§ekici (attractor) ekranla aÃ§Ä±lÄ±yor. Tekrar eden parÃ§alar bileÅŸene Ã§Ä±karÄ±ldÄ±.
**Detay:**
1. `IdleScreen.svelte` artÄ±k tek-durumlu attractor: aÃ§Ä±lÄ±ÅŸta anÄ±nda gÃ¶sterilir (10sn bekleme + iki-durumlu screensaver mantÄ±ÄŸÄ± kaldÄ±rÄ±ldÄ±). Reklam varsa gÃ¶rseller dÃ¶ner, yoksa `<AdPromo large />`. Eski `.screen-idle`/`.idle-*` markup ve CSS silindi.
2. `MediaView.svelte` (YENÄ°) â€” URL uzantÄ±sÄ±na gÃ¶re `<video>`/`<img>` render eden ortak bileÅŸen; AdStrip + IdleScreen kullanÄ±yor (kopyalanan img/video mantÄ±ÄŸÄ± tekilleÅŸtirildi).
3. `ScreenHeader.svelte` (YENÄ°) â€” Logo + opsiyonel subtitle; Welcome/Demographics/Category/Consult/Question ekranlarÄ±ndaki tekrarlanan `kiosk-header` markup'Ä± bununla deÄŸiÅŸtirildi.
**Dosyalar:** `IdleScreen.svelte`, `MediaView.svelte` (YENÄ°), `ScreenHeader.svelte` (YENÄ°), `AdStrip.svelte`, `Welcome/Category/Consult/Demographics/QuestionScreen.svelte`, `app.css` (Ã¶lÃ¼ idle stilleri temizlendi)
**DokÃ¼man:** 04-kiosk-edge-ui.md gÃ¼ncellendi.
**Test:** ui 16/16 geÃ§ti; tarayÄ±cÄ±da doÄŸrulandÄ±.
**Breaking:** Yok (idle screen state aynÄ±; sadece gÃ¶rÃ¼nÃ¼m/komponent yapÄ±sÄ± deÄŸiÅŸti).

### Kiosk UI â€” Marka Logosu, Ortak AdPromo, Ekran Koruyucu Promosu, 20sn Inaktivite
**DeÄŸiÅŸiklik:** 4 UI iyileÅŸtirmesi yapÄ±ldÄ±.
**Detay:**
1. `Logo.svelte` (YENÄ°) + `assets/eisa-logo.svg` & `eisa-logo-light.svg` â€” tÃ¼m "e-Ä°SA" yazÄ±larÄ± resmi marka logosu ile deÄŸiÅŸtirildi (koyu zeminde beyaz varyant).
2. `AdPromo.svelte` (YENÄ°) â€” dÃ¶nen "Bu Alana Reklam Verebilirsiniz" tasarÄ±mÄ± ortak bileÅŸene Ã§Ä±karÄ±ldÄ±; AdStrip (reklam yokken) ve IdleScreen ekran koruyucusunda (reklam yokken, `large`) kullanÄ±lÄ±yor.
3. IdleScreen `ss-overlay-text` ekranÄ±n ÃœSTÃœNE konumlandÄ±rÄ±ldÄ±; ekran koruyucu artÄ±k stok gÃ¶rseller yerine reklam yoksa AdPromo dÃ¶ndÃ¼rÃ¼yor.
4. App.svelte global inaktivite `10s â†’ 20s`; idle/wifi dÄ±ÅŸÄ±ndaki HER ekranda 20sn iÅŸlemsizlikte idle'a dÃ¶ner (`finalizeAbandonedSession()` ile terk edilmiÅŸ oturum analitiÄŸi korunur).
**Dosyalar:** `Logo.svelte`, `AdPromo.svelte`, `IdleScreen.svelte`, `AdStrip.svelte`, `App.svelte`, `Welcome/Category/Consult/Demographics/QuestionScreen.svelte`, `app.css`, `assets/eisa-logo*.svg`
**DokÃ¼man:** 04-kiosk-edge-ui.md gÃ¼ncellendi.
**Test:** ui 16/16 geÃ§ti.
**Breaking:** Yok.

### Kiosk â†” Backend DOOH Uyum Denetimi â€” TZ + Slot + Ã–lÃ¼ Endpoint DÃ¼zeltmeleri
**DeÄŸiÅŸiklik:** Reklam gÃ¶sterim mantÄ±ÄŸÄ±nÄ±n backend ile uyumu denetlendi; 3 gerÃ§ek hata dÃ¼zeltildi.
**Hatalar:**
1. **Zaman dilimi (TZ):** Kiosk playlist'i UTC saatine gÃ¶re seÃ§iyordu; backend `target_hour` Istanbul yereli (USE_TZ, Europe/Istanbul) â†’ reklamlar ~3 saat kayÄ±yordu.
2. **Slot Ã¶lÃ§eÄŸi:** `estimated_start_offset_seconds` saat-mutlak (0..3599) iken AdStrip slot dÃ¶ngÃ¼sÃ¼ 60sn'e gÃ¶re sarÄ±yordu â†’ sadece ilk dakikanÄ±n Ã¶ÄŸeleri oynuyor, PER_HOUR/PER_DAY reklamlar hiÃ§ gÃ¶rÃ¼nmÃ¼yordu.
3. **Ã–lÃ¼ endpoint:** `server.js` `/api/lookups/iller*` kaldÄ±rÄ±lmÄ±ÅŸ SQLite tablolarÄ±nÄ± (db.js v9) sorguluyordu.
**Dosyalar:**
- `kiosk_edge/api-node/src/timezone.js` (YENÄ° â€” `istanbulNow()`)
- `kiosk_edge/api-node/src/server.js` (`/api/playlist/current` Istanbul tarih/saat; Ã¶lÃ¼ iller endpoint'leri kaldÄ±rÄ±ldÄ±)
- `kiosk_edge/api-node/src/scheduler.js` (playlist Ã§ekme Istanbul tarihi)
- `kiosk_edge/ui/src/components/AdStrip.svelte` (slot dÃ¶ngÃ¼sÃ¼ 3600sn; Istanbul saati ile yeniden yÃ¼kleme; kullanÄ±lmayan `loopSeconds` kaldÄ±rÄ±ldÄ±)
**DokÃ¼man:** 08-dooh-advertising.md (Playlist/PlaylistItem/HouseAd/PlayLog modelleri, AdStrip Ã¶rneÄŸi, sync aralÄ±klarÄ±, TZ & Slot bÃ¶lÃ¼mÃ¼, Ã§Ã¶zÃ¼len riskler) gerÃ§ek kodla hizalandÄ±.
**Test:** api-node 30/30, ui 16/16 geÃ§ti.
**Breaking:** Yok (davranÄ±ÅŸ dÃ¼zeltmesi; cihaz/konteyner TZ'sinden baÄŸÄ±msÄ±z Ã§alÄ±ÅŸÄ±r).

### Kiosk Demo â€” Rancher/Kubernetes Manifest
**DeÄŸiÅŸiklik:** BirleÅŸik kiosk container'Ä± demo.eisa.com.tr Ã¼zerinden yayÄ±nlamak iÃ§in K8s manifest eklendi.
**Dosyalar:** `deploy/eisa-kiosk-demo.yaml` (YENÄ°)
**Kapsam:** Namespace + ConfigMap (EISA_ env'leri) + Deployment (ghcr.io/ysnzgl/eisa-kiosk:1.0.0, port 80) + Service (ClusterIP) + Ingress (traefik + cert-manager, demo.eisa.com.tr TLS).
**Pattern:** `deploy/eisa-app-production.yaml` ile aynÄ± konvansiyon.
**Storage:** emptyDir (demo veri backend'den pull edilir); opsiyonel PVC Ã¶rneÄŸi yorum olarak eklendi.
**Breaking:** Yok.

### Kiosk Docker â€” Tek Container BirleÅŸtirme
**DeÄŸiÅŸiklik:** API Node ve UI tek container'da birleÅŸtirildi (Ã¶nce ayrÄ± 2 servisti).
**Dosyalar:**
- `kiosk_edge/Dockerfile` (YENÄ° â€” birleÅŸik multi-stage: ui-build + api-deps + runner)
- `kiosk_edge/.dockerignore` (YENÄ°)
- `kiosk_edge/docker-compose.demo.yml` (tek `kiosk` servisi, port 8080â†’80)
- `kiosk_edge/ui/src/lib/api.js` (`||` â†’ `??` ki boÅŸ VITE_API_BASE relative path olsun)
- `kiosk_edge/README_DEMO_DOCKER.md` (birleÅŸik mimari gÃ¼ncellendi)
**Mimari:** Nginx (:80) UI static + `/api` proxy â†’ Node (127.0.0.1:8765); supervisord ile 2 process.
**DokÃ¼man:** 03-kiosk-edge-api-node.md, 04-kiosk-edge-ui.md Docker bÃ¶lÃ¼mleri gÃ¼ncellendi.
**Breaking:** Yok (ilk versiyondaki ayrÄ± `api-node/Dockerfile` ve `ui/Dockerfile` kaldÄ±rÄ±ldÄ±; tek kÃ¶k `Dockerfile` kullanÄ±lÄ±yor).

### Kiosk IdleScreen Layout Ä°yileÅŸtirmesi
**DeÄŸiÅŸiklik:** Bekleme ekranÄ±ndaki logo ve ana iÃ§erik ortadan yukarÄ±ya taÅŸÄ±ndÄ±.
**Dosyalar:** `kiosk_edge/ui/src/app.css` (.screen-idle: `align-items: flex-start`, .idle-content: `margin-top: 80px`)
**Etki:** Daha dengeli gÃ¶rsel yerleÅŸim, alt banner iÃ§in daha fazla alan.

### Kiosk Docker Deployment (Demo)
**DeÄŸiÅŸiklik:** demo.eisa.com.tr iÃ§in Docker yapÄ±sÄ± oluÅŸturuldu. GerÃ§ek kiosk deployment'Ä±nda kullanÄ±lmaz.
**Not:** Ä°lk versiyonda ayrÄ± `api-node/Dockerfile` + `ui/Dockerfile` vardÄ±; sonradan tek kÃ¶k `Dockerfile`'a birleÅŸtirildi (Ã¼stteki kayÄ±t).
**Dosyalar:**
- `kiosk_edge/docker-compose.demo.yml` (demo compose)
- `kiosk_edge/.env.demo` (environment variables)
- `kiosk_edge/README_DEMO_DOCKER.md` (deployment guide)
- `kiosk_edge/ui/.env.example` (VITE_API_BASE konfigÃ¼rasyonu)
- `kiosk_edge/ui/src/lib/api.js` (API_BASE configurable: `import.meta.env.VITE_API_BASE`)
**DokÃ¼man:** 03-kiosk-edge-api-node.md, 04-kiosk-edge-ui.md gÃ¼ncellenmiÅŸ (Docker Deployment bÃ¶lÃ¼mÃ¼ eklendi).
**Breaking:** Yok.

---

## 2026-06-05

### DanÄ±ÅŸma Tamamlama AkÄ±ÅŸÄ± UygulanmasÄ±
**DeÄŸiÅŸiklik:** Backend'e pharmacist-side consultation completion endpoint eklendi. Yeni DB alanlarÄ±: `danisma_tamamlandi`, `danisma_tamamlanma_tarihi`, `danisma_notu`, `danisma_tamamlayan_eczaci`.
**Dosyalar:** `backend/apps/analytics/views.py` (OturumLoguCompleteView), `models.py` (4 yeni alan), `serializers.py` (yeni alanlar), `urls.py` (endpoint path); `web_panels/src/views/pharmacist/QrScan.vue` (completion UI), `services/analytics.js` (completeSession helper).
**Migration:** `0005_oturumlogu_danisma_notu_and_more.py`
**Endpoint:** `POST /api/analytics/sessions/{id}/complete/` (eczacÄ±-only, pharmacy ownership enforced, idempotent).
**DokÃ¼man:** `07-session-and-analytics.md`, `06-db-and-api-contracts.md` gÃ¼ncellenmiÅŸ.
**Breaking:** Yok.

### Ä°lk DokÃ¼mantasyon Seti OluÅŸturuldu
**Dosyalar:** 00-AI-INDEX.md, 01-backend.md, 02-web-panels.md, 03-kiosk-edge-api-node.md, 04-kiosk-edge-ui.md, 05-cross-project-flows.md, 06-db-and-api-contracts.md
**AmaÃ§:** Token-ekonomik AI context
**Kapsam:** Backend/frontend/kiosk modÃ¼lleri, kritik akÄ±ÅŸlar, API contract'larÄ±, belirsiz/riskli alanlar

### Optimization Pass â€” Context Quality
**GÃ¼ncellenen:** TÃ¼m mevcut dokÃ¼manlar
**Eklenen bÃ¶lÃ¼mler:** "When To Read This File", "Important Source Files", "Do Not Change Without Checking"
**Yeni dosyalar:** 07-session-and-analytics.md, 08-dooh-advertising.md, AI-WORKFLOW.md, AI-RULES.md
**Etki:** Daha hÄ±zlÄ± context bulma, tekrar azaltma, kritik contract korumasÄ±

**Ã–nemli bulgular:**
- DOOH v2 playlist mimarisi (60sn pre-computed)
- Offline-first kiosk (SQLite + outbox)
- Dual authentication (App-Key+MAC / IoT Token)
- Legacy Campaign.target_pharmacies + yeni CampaignTarget (belirsiz priority)
- Outbox pressure kontrolÃ¼ (tam dolunca ne olur belirsiz)
- Session idempotency (backend impl doÄŸrulanmalÄ±)
- QR collision riski (unique constraint yok)
- Media cache placeholder

---

## Gelecek KayÄ±tlar

---

## 2026-07-22

### [Frontend] â€” Faz 6: CampaignWizard + DoohControlCenter
**DeÄŸiÅŸiklik:** 6 adÄ±mlÄ± CampaignWizard (Bilgiler/Medya/Hedefleme/Frekans/SimÃ¼lasyon/Aktive Et), DoohControlCenter (kampanya/job/kiosk izleme), useKioskRolloutStatus composable
**Dosyalar:** `CampaignWizard.vue`, `DoohControlCenter.vue` (yeni), `useKioskRolloutStatus.js` (yeni), `dooh.js`, `router/index.js`, `AdminLayout.vue`, `PlaylistEditor.vue`, `faz6_campaign_wizard.test.js` (yeni)
**Etki:** DOOH v2 contractlarla uÃ§tan uca wizard; rollout izleme merkezi; 43 frontend test
**Breaking:** Yok â€” additive deÄŸiÅŸiklikler
**DokÃ¼man:** `02-web-panels.md`, `08-dooh-advertising.md`, `implementation-plan-dooh-scheduler.md` gÃ¼ncellendi

### [Frontend] â€” Faz 6 KapanÄ±ÅŸ Denetimi: Bug DÃ¼zeltmeleri
**DeÄŸiÅŸiklik:** (1) `summaryStats.behindKiosks` camelCase key fix, (2) `close()` unsaved changes warning, (3) `target_days` UI disabled, (4) `dooh.js` getIller/getIlceler duplicate kaldÄ±rÄ±ldÄ±, (5) PlaylistEditor â†’ lookups.js import
**Dosyalar:** `DoohControlCenter.vue`, `CampaignWizard.vue`, `dooh.js`, `PlaylistEditor.vue`
**Etki:** summaryStats doÄŸru; kullanÄ±cÄ±ya kayÄ±p uyarÄ±sÄ±; misleading UI dÃ¼zeltildi
**Breaking:** Yok
**DokÃ¼man:** Bu changelog

### [Backend] â€” Faz 4/5 Hardening: Fingerprint + ACK + Sinyaller
**DeÄŸiÅŸiklik:** Fingerprint kaynaÄŸÄ± PlaylistItem DB kayÄ±tlarÄ±ndan hesaplanÄ±yor; ACK capped backoff (30sâ†’1800s); Eczane sinyali; pre_save eski eczane_id yakalama
**Dosyalar:** `activation_service.py`, `queue_worker.py`, `signals.py`, `db.js`, `scheduler.js`
**Etki:** 12 regression test; concurrent worker gÃ¼venli; ACK asla silinmiyor (max retry'da)
**Breaking:** Yok
**DokÃ¼man:** `implementation-plan-dooh-scheduler.md` Faz 5

### [Backend] â€” Faz 5: Desired/Applied Version + Kiosk ACK/Manifest
**DeÄŸiÅŸiklik:** KioskManifestView, KioskAckView, pending_ack SQLite tablosu, clearPendingAckIfMatches
**Dosyalar:** `kiosk_api/views.py`, `pharmacies/models.py`, `kiosk_edge/api-node/src/db.js`, `scheduler.js`
**Etki:** 18 backend test + 15 kiosk edge test
**Breaking:** Yok â€” flag=false legacy kiosklar etkilenmez
**DokÃ¼man:** `08-dooh-advertising.md` Faz 5

### [Backend] â€” Faz 4: Invalidation / DB Queue / Staged Publish
**DeÄŸiÅŸiklik:** GenerationJob DB queue, InvalidationService, QueueWorker, Campaign/Kiosk/Eczane sinyalleri
**Dosyalar:** `invalidation_service.py`, `queue_worker.py`, `signals.py`, `models.py` (0019 migration)
**Etki:** 31 + 12 backend test
**Breaking:** Yok
**DokÃ¼man:** `implementation-plan-dooh-scheduler.md` Faz 4

### [Backend] â€” Faz 3: Simulation / Activation
**DeÄŸiÅŸiklik:** `POST .../simulate/` (read-only), `POST .../activate/` (DOOH_ENGINE_V2=active)
**Dosyalar:** `activation_service.py`, `views_v2.py`, `serializers.py`
**Etki:** 21 test (FA-01..FA-16)
**Breaking:** Yok â€” DOOH_ENGINE_V2=off durumunda activate 403
**DokÃ¼man:** `08-dooh-advertising.md` Faz 3 Endpoint Contract

### [Backend] â€” Faz 2: PlacementEngine V2 Shadow Mode
**DeÄŸiÅŸiklik:** PlacementEngineV2, GlobalQuotaService, shadow mod scheduler entegrasyonu
**Dosyalar:** `placement_engine_v2.py`, `quota_service.py`, `scheduler.py`, migrations 0015-0018
**Etki:** 169 + 179 = 348 passed (Faz 2 sonrasÄ±)
**Breaking:** Yok â€” V1 authoritative, V2 shadow
**DokÃ¼man:** `implementation-plan-dooh-scheduler.md` Faz 2

**Format Ã¶rneÄŸi (max 10 satÄ±r):**

```
## YYYY-MM-DD

### [ModÃ¼l] â€” DeÄŸiÅŸiklik BaÅŸlÄ±ÄŸÄ±
**DeÄŸiÅŸiklik:** ...
**Dosyalar:** ...
**Etki:** ...
**Breaking:** Var/Yok
**DokÃ¼man:** GÃ¼ncellendi/Eklendi
```

---

**Not:** Bu dosya AI tarafÄ±ndan otomatik gÃ¼ncellenir.

