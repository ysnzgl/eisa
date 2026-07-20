# Kiosk-Backend Offline Sync Plani

## 1) Mimari Akis

- Kiosk UI sadece lokal API ile konusur: http://127.0.0.1:8765
- Lokal API (api-node) SQLite uzerinde offline-first calisir.
- Backend ile iletisim scheduler uzerinden Pull + Push dongusu ile yapilir.

Akis:
1. Pull katalog: /api/kiosk/v1/catalog/
2. Pull kiosk reklam + lookup: /api/kiosk/v1/sync/
3. Ping versiyon kontrolu: /api/kiosk/v1/ping/
4. Playlist guncelleme: /api/kiosk/v1/playlist/?date=YYYY-MM-DD
5. Push oturum outbox: /api/kiosk/v1/sessions/
6. Push proof-of-play outbox: /api/kiosk/v1/proof-of-play/

## 2) Veri Guncelligi Stratejisi

- Katalog ve reklamlar periyodik pull ile yenilenir.
- Playlist icin versiyon tabanli delta-sync kullanilir:
  - ping.playlist_version > local_version ise playlist yeniden cekilir.
- Idempotency anahtari ile oturum push tekrarli gonderimde cift kayit olusmaz.
- Proof-of-play gonderim basarisiz olursa outbox'ta tutulur ve sonraki dongude tekrar denenir.

## 3) Offline Dayaniklilik

- Backend ulasilamazsa kiosk akisi devam eder:
  - Soru/cevap ve lookup verileri local SQLite'tan okunur.
  - Oturum ve impression olaylari outbox'a yazilir.
  - Ag geri geldiginde otomatik push edilir.
- Reklam medya dosyalari local diskte cache'lenir.
  - UI media_url olarak once lokal endpoint kullanir: /api/media/{assetType}/{assetId}
  - Lokal dosya yoksa remote_media_url fallback yapilir.

## 4) Lokal Medya Saklama Kurallari

- Klasor: EISA_MEDIA_DIR (varsayilan: /var/lib/eisa/media)
- Kaynak tablosu: media_cache
  - asset_id, asset_type, source_url, source_checksum, local_path, status, synced_at
- Senkronizasyon kurali:
  - source_url/source_checksum degismisse dosya yeniden indirilir.
  - Aktif listeden cikan medya dosyasi ve media_cache kaydi temizlenir.

## 5) Operasyonel Oneriler

- Yalniz `EISA_KIOSK_FLEET_KEY` ve `EISA_KIOSK_PROVISIONING_SECRET` env'den okunur.
- App Key ve MAC SQLite `kiosk_meta` icinde tutulur; backend kaydiyla eslesme bootstrap sonrasinda saglanir.
- Pull/Push/Ping araliklari saha kosullarina gore ayarlanabilir:
  - Pull: 10-15 dk
  - Push: 1-5 dk
  - Ping: 30-60 sn
