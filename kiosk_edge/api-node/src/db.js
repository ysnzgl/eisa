// SQLite (better-sqlite3) — yerel offline-first sema (Turkce + lookup tablolari).
// Backend'in 3NF semasiyla 1:1 hizalanir; kiosk dis sunucu olmadan calisir.
import path from 'node:path';
import fs from 'node:fs';
import Database from 'better-sqlite3';

let _db = null;

const DEFAULT_OUTBOX_MAX_ROWS = 10000;
const DEFAULT_DIAGNOSTIC_MAX_ROWS = 5000;

// Sema versiyonu — v11: pending_ack + applied_version kiosk_meta alanları (Faz 5).
const SCHEMA_VERSION = 11;

export function openDb(sqlitePath, options = {}) {
  if (_db) return _db;
  const dir = path.dirname(sqlitePath);
  if (dir && dir !== '.' && !fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  // Eski (v1, ingilizce alanlar) sema varsa DB'yi sifirla.
  if (fs.existsSync(sqlitePath)) {
    try {
      const probe = new Database(sqlitePath, { readonly: true });
      const row = probe.prepare(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
      ).get('schema_meta');
      let version = 1;
      if (row) {
        const r = probe.prepare('SELECT version FROM schema_meta LIMIT 1').get();
        version = r?.version ?? 1;
      }
      probe.close();
      if (version !== SCHEMA_VERSION) {
        for (const ext of ['', '-wal', '-shm']) {
          const p = sqlitePath + ext;
          if (fs.existsSync(p)) fs.unlinkSync(p);
        }
      }
    } catch {
      for (const ext of ['', '-wal', '-shm']) {
        const p = sqlitePath + ext;
        if (fs.existsSync(p)) fs.unlinkSync(p);
      }
    }
  }

  _db = new Database(sqlitePath);
  _db.pragma('journal_mode = WAL');
  // Yerel guvenlik: App Key iceren DB yalniz servis kullanicisina acik olsun.
  // Linux hedefi; Windows'ta chmod etkisizdir ve sessizce gecilir.
  if (process.platform !== 'win32') {
    try { fs.chmodSync(dir, 0o700); } catch { /* dizin izni ayarlanamadi */ }
    for (const ext of ['', '-wal', '-shm']) {
      try { fs.chmodSync(sqlitePath + ext, 0o600); } catch { /* dosya henuz olusmamis olabilir */ }
    }
  }
  initSchema(_db, {
    outboxMaxRows: options.outboxMaxRows ?? DEFAULT_OUTBOX_MAX_ROWS,
    diagnosticMaxRows: options.diagnosticMaxRows ?? DEFAULT_DIAGNOSTIC_MAX_ROWS,
  });
  return _db;
}

export function getDb() {
  if (!_db) throw new Error('DB acilmadi; once openDb() cagirin.');
  return _db;
}

export function closeDb() {
  if (_db) {
    _db.close();
    _db = null;
  }
}

/**
 * ERR-006: Outbox kapasitesinin %80'ini gectiginde uyari log'u uretir.
 */
export function checkOutboxPressure(logger, maxRows = DEFAULT_OUTBOX_MAX_ROWS) {
  if (!_db) return { oturum: 0, reklam: 0, threshold: maxRows, warned: false };
  const limit = Math.max(100, Number(maxRows) | 0);
  const threshold = Math.floor(limit * 0.8);
  const oturum = _db.prepare('SELECT COUNT(*) AS c FROM oturum_outbox').get().c;
  const reklam = _db.prepare('SELECT COUNT(*) AS c FROM reklam_gosterim_outbox').get().c;
  let warned = false;
  if (oturum >= threshold && logger?.warn) {
    logger.warn({ count: oturum, threshold, limit },
      'oturum_outbox kapasitesinin %80\'ine yaklasti');
    warned = true;
  }
  if (reklam >= threshold && logger?.warn) {
    logger.warn({ count: reklam, threshold, limit },
      'reklam_gosterim_outbox kapasitesinin %80\'ine yaklasti');
    warned = true;
  }
  return { oturum, reklam, threshold, warned };
}

function initSchema(db, options = {}) {
  const outboxMaxRows = typeof options === 'number'
    ? options
    : options.outboxMaxRows ?? DEFAULT_OUTBOX_MAX_ROWS;
  const diagnosticMaxRows = typeof options === 'number'
    ? DEFAULT_DIAGNOSTIC_MAX_ROWS
    : options.diagnosticMaxRows ?? DEFAULT_DIAGNOSTIC_MAX_ROWS;
  db.exec(`
    CREATE TABLE IF NOT EXISTS schema_meta (version INTEGER NOT NULL);

    -- LOOKUP TABLOLARI (audit kolonu YOK)
    CREATE TABLE IF NOT EXISTS cinsiyetler (
      id  INTEGER PRIMARY KEY,
      kod TEXT    NOT NULL UNIQUE,
      ad  TEXT    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS yas_araliklari (
      id        INTEGER PRIMARY KEY,
      kod       TEXT    NOT NULL UNIQUE,
      ad        TEXT    NOT NULL,
      alt_sinir INTEGER,
      ust_sinir INTEGER
    );

    -- IS TABLOLARI (BaseModel kolonlari: olusturulma_tarihi, surum)
    CREATE TABLE IF NOT EXISTS kategoriler (
      id                   INTEGER PRIMARY KEY,
      slug                 TEXT    NOT NULL UNIQUE,
      ad                   TEXT    NOT NULL,
      ikon                 TEXT    NOT NULL DEFAULT 'fa-circle',
      bagli_kategori_id    INTEGER,
      hedef_cinsiyet_id    INTEGER,
      aktif                INTEGER NOT NULL DEFAULT 1,
      surum                INTEGER NOT NULL DEFAULT 1,
      hedef_cinsiyetler    TEXT    NOT NULL DEFAULT '[]',
      hedef_yas_araliklari TEXT    NOT NULL DEFAULT '[]',
      olusturulma_tarihi   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      guncellenme_tarihi   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );

    CREATE TABLE IF NOT EXISTS danisma_kategorileri (
      id                 INTEGER PRIMARY KEY,
      slug               TEXT    NOT NULL UNIQUE,
      ad                 TEXT    NOT NULL,
      ikon               TEXT    NOT NULL DEFAULT 'fa-comments',
      ust_kategori_id    INTEGER,
      aktif              INTEGER NOT NULL DEFAULT 1,
      olusturulma_tarihi TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      guncellenme_tarihi TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );

    CREATE TABLE IF NOT EXISTS sorular (
      id                   INTEGER PRIMARY KEY,
      kategori_id          INTEGER NOT NULL,
      seed_id              TEXT,
      metin                TEXT    NOT NULL,
      sira                 INTEGER NOT NULL DEFAULT 0,
      eslesme_kurallari    TEXT    NOT NULL DEFAULT '[]',
      hedef_cinsiyet_id    INTEGER,
      surum                INTEGER NOT NULL DEFAULT 1,
      hedef_cinsiyetler    TEXT    NOT NULL DEFAULT '[]',
      hedef_yas_araliklari TEXT    NOT NULL DEFAULT '[]',
      olusturulma_tarihi   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      guncellenme_tarihi   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );

    CREATE TABLE IF NOT EXISTS cevaplar (
      id      INTEGER PRIMARY KEY,
      soru_id INTEGER NOT NULL,
      metin   TEXT    NOT NULL,
      agirlik INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS etken_maddeler (
      id       INTEGER PRIMARY KEY,
      ad       TEXT    NOT NULL UNIQUE,
      aciklama TEXT    NOT NULL DEFAULT '',
      aktif    INTEGER NOT NULL DEFAULT 1,
      surum    INTEGER NOT NULL DEFAULT 1,
      olusturulma_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      guncellenme_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );

    -- Backend M2M hedefleme iliskileri (kiosk sorgulari icin de normalize tutulur).
    CREATE TABLE IF NOT EXISTS kategori_hedef_yas_araliklari (
      kategori_id    INTEGER NOT NULL,
      yas_araligi_id INTEGER NOT NULL,
      PRIMARY KEY (kategori_id, yas_araligi_id)
    );
    CREATE TABLE IF NOT EXISTS soru_hedef_yas_araliklari (
      soru_id        INTEGER NOT NULL,
      yas_araligi_id INTEGER NOT NULL,
      PRIMARY KEY (soru_id, yas_araligi_id)
    );
    CREATE TABLE IF NOT EXISTS soru_etken_maddeler (
      soru_id        INTEGER NOT NULL,
      etken_madde_id INTEGER NOT NULL,
      rol            TEXT    NOT NULL DEFAULT 'ana',
      PRIMARY KEY (soru_id, etken_madde_id)
    );

    CREATE TABLE IF NOT EXISTS creatives (
      id               TEXT    PRIMARY KEY,
      media_url        TEXT    NOT NULL DEFAULT '',
      duration_seconds INTEGER NOT NULL DEFAULT 15,
      checksum         TEXT    NOT NULL DEFAULT '',
      type             TEXT    NOT NULL DEFAULT 'creative',
      aktif            INTEGER NOT NULL DEFAULT 1,
      guncellenme_tarihi TEXT  NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );
    CREATE TABLE IF NOT EXISTS house_ads (
      id               TEXT    PRIMARY KEY,
      name             TEXT    NOT NULL DEFAULT '',
      media_url        TEXT    NOT NULL DEFAULT '',
      duration_seconds INTEGER NOT NULL DEFAULT 15,
      type             TEXT    NOT NULL DEFAULT 'house_ad',
      aktif            INTEGER NOT NULL DEFAULT 1,
      guncellenme_tarihi TEXT  NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );

    -- OUTBOX
    CREATE TABLE IF NOT EXISTS oturum_outbox (
      id                   INTEGER PRIMARY KEY AUTOINCREMENT,
      idempotency_anahtari TEXT    UNIQUE,
      payload              TEXT    NOT NULL,
      olusturulma_tarihi   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      gonderilme_tarihi    TEXT,
      retry_count          INTEGER NOT NULL DEFAULT 0,
      error_reason         TEXT
    );
    CREATE TABLE IF NOT EXISTS reklam_gosterim_outbox (
      id                   INTEGER PRIMARY KEY AUTOINCREMENT,
      idempotency_anahtari TEXT    UNIQUE,
      payload              TEXT    NOT NULL,
      olusturulma_tarihi   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      gonderilme_tarihi    TEXT
    );

    CREATE INDEX IF NOT EXISTS sorular_kategori_idx  ON sorular(kategori_id);
    CREATE INDEX IF NOT EXISTS cevaplar_soru_idx     ON cevaplar(soru_id);
    CREATE INDEX IF NOT EXISTS danisma_ust_idx       ON danisma_kategorileri(ust_kategori_id);
    CREATE INDEX IF NOT EXISTS kategoriler_hedef_cinsiyet_idx ON kategoriler(hedef_cinsiyet_id);
    CREATE INDEX IF NOT EXISTS sorular_hedef_cinsiyet_idx     ON sorular(hedef_cinsiyet_id);
    CREATE INDEX IF NOT EXISTS kategori_hedef_yas_idx         ON kategori_hedef_yas_araliklari(yas_araligi_id);
    CREATE INDEX IF NOT EXISTS soru_hedef_yas_idx             ON soru_hedef_yas_araliklari(yas_araligi_id);
    CREATE INDEX IF NOT EXISTS soru_etken_madde_idx           ON soru_etken_maddeler(etken_madde_id);
    CREATE INDEX IF NOT EXISTS oturum_outbox_pending ON oturum_outbox(gonderilme_tarihi);
    CREATE INDEX IF NOT EXISTS reklam_outbox_pending ON reklam_gosterim_outbox(gonderilme_tarihi);

    -- LOCAL MEDIA CACHE (offline reklam oynatimi)
    CREATE TABLE IF NOT EXISTS media_cache (
      asset_id        TEXT    NOT NULL,
      asset_type      TEXT    NOT NULL CHECK(asset_type IN ('creative','house_ad')),
      source_url      TEXT    NOT NULL,
      source_checksum TEXT    NOT NULL DEFAULT '',
      file_checksum   TEXT    NOT NULL DEFAULT '',
      local_path      TEXT    NOT NULL,
      mime_type       TEXT    NOT NULL DEFAULT '',
      file_size       INTEGER NOT NULL DEFAULT 0,
      status          TEXT    NOT NULL DEFAULT 'ready',
      error_message   TEXT    NOT NULL DEFAULT '',
      synced_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      PRIMARY KEY (asset_id, asset_type)
    );
    CREATE INDEX IF NOT EXISTS media_cache_status_idx ON media_cache(status);

    -- DOOH PLAYLIST (merkezi scheduler'dan cekilir)
    CREATE TABLE IF NOT EXISTS kiosk_meta (
      key   TEXT PRIMARY KEY,
      value TEXT NOT NULL DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS playlists (
      id                    TEXT    PRIMARY KEY,
      target_date           TEXT    NOT NULL,
      target_hour           INTEGER NOT NULL,
      loop_duration_seconds INTEGER NOT NULL DEFAULT 60,
      version               INTEGER NOT NULL DEFAULT 1,
      synced_at             TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      UNIQUE(target_date, target_hour)
    );
    CREATE TABLE IF NOT EXISTS playlist_items (
      id                             TEXT    PRIMARY KEY,
      playlist_id                    TEXT    NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
      playback_order                 INTEGER NOT NULL DEFAULT 0,
      asset_id                       TEXT    NOT NULL,
      asset_type                     TEXT    NOT NULL CHECK(asset_type IN ('creative','house_ad')),
      media_url                      TEXT    NOT NULL DEFAULT '',
      duration_seconds               INTEGER NOT NULL DEFAULT 15,
      estimated_start_offset_seconds INTEGER NOT NULL DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS playlist_items_playlist_idx ON playlist_items(playlist_id, playback_order);
    CREATE INDEX IF NOT EXISTS playlists_date_hour_idx     ON playlists(target_date, target_hour);

    -- TEKNIK LOG OUTBOX (bounded diagnostic)
    -- Yalnizca WARNING/ERROR/CRITICAL kayitlari icin. INFO/DEBUG YAZILMAZ.
    -- Backend'e batch olarak gonderilir; backend bunlari DB'ye yazmadan JSON stdout'a doner.
    CREATE TABLE IF NOT EXISTS diagnostic_outbox (
      id             INTEGER PRIMARY KEY AUTOINCREMENT,
      created_at     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      level          TEXT    NOT NULL,
      event          TEXT    NOT NULL,
      message        TEXT    NOT NULL DEFAULT '',
      context_json   TEXT    NOT NULL DEFAULT '{}',
      correlation_id TEXT,
      retry_count    INTEGER NOT NULL DEFAULT 0,
      next_retry_at  TEXT,
      sent_at        TEXT
    );
    CREATE INDEX IF NOT EXISTS diagnostic_outbox_pending_idx
      ON diagnostic_outbox(sent_at, next_retry_at);
    CREATE INDEX IF NOT EXISTS diagnostic_outbox_event_idx
      ON diagnostic_outbox(event, created_at);

    -- FAZ 5: Pending ACK (singleton — Kiosk SQLite commit sonrası backend'e bildirim)
    -- id=1 singleton: her manifest uygulaması en fazla bir pending ACK bırakır.
    -- ACK başarılı olunca silinir. Process crash → restart'ta yeniden gönderilir.
    CREATE TABLE IF NOT EXISTS pending_ack (
      id               INTEGER PRIMARY KEY CHECK(id = 1),
      playlist_version INTEGER NOT NULL,
      horizon_start    TEXT    NOT NULL,
      horizon_end      TEXT    NOT NULL,
      created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      retry_count      INTEGER NOT NULL DEFAULT 0
    );
  `);

  const meta = db.prepare('SELECT version FROM schema_meta LIMIT 1').get();
  if (!meta) {
    db.prepare('INSERT INTO schema_meta (version) VALUES (?)').run(SCHEMA_VERSION);
  } else if (meta.version !== SCHEMA_VERSION) {
    db.prepare('UPDATE schema_meta SET version = ?').run(SCHEMA_VERSION);
  }

  // Non-destructive column additions (idempotent — mevcut DB'lerde ALTER TABLE ile eklenir).
  const outboxCols = db.prepare("PRAGMA table_info(oturum_outbox)").all().map((c) => c.name);
  if (!outboxCols.includes('retry_count')) {
    db.exec('ALTER TABLE oturum_outbox ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0');
  }
  if (!outboxCols.includes('error_reason')) {
    db.exec('ALTER TABLE oturum_outbox ADD COLUMN error_reason TEXT');
  }

  // Faz 5: pending_ack tablosuna next_retry_at kolonu ekle (idempotent)
  const ackCols = db.prepare("PRAGMA table_info(pending_ack)").all().map((c) => c.name);
  if (!ackCols.includes('next_retry_at')) {
    db.exec('ALTER TABLE pending_ack ADD COLUMN next_retry_at TEXT');
  }

  installOutboxFifoTriggers(db, outboxMaxRows);
  installDiagnosticFifoTrigger(db, diagnosticMaxRows);
}

export function installDiagnosticFifoTrigger(db, maxRows = DEFAULT_DIAGNOSTIC_MAX_ROWS) {
  const limit = Math.max(100, Number(maxRows) | 0);
  db.exec('DROP TRIGGER IF EXISTS diagnostic_outbox_fifo_cap;');
  db.exec(`
    CREATE TRIGGER diagnostic_outbox_fifo_cap
    AFTER INSERT ON diagnostic_outbox
    WHEN (SELECT COUNT(*) FROM diagnostic_outbox) > ${limit}
    BEGIN
      DELETE FROM diagnostic_outbox
       WHERE id IN (
         SELECT id FROM diagnostic_outbox
          -- Once basariyla gonderilmis olanlar, sonra en eski dusuk oncelikli DEBUG/INFO (yoksa WARNING).
          ORDER BY CASE WHEN sent_at IS NOT NULL THEN 0
                        WHEN level IN ('DEBUG','INFO') THEN 1
                        WHEN level = 'WARNING' THEN 2
                        ELSE 3 END,
                   id ASC
          LIMIT ((SELECT COUNT(*) FROM diagnostic_outbox) - ${limit})
       );
    END;
  `);
}

export function installOutboxFifoTriggers(db, maxRows = DEFAULT_OUTBOX_MAX_ROWS) {
  const limit = Math.max(100, Number(maxRows) | 0);
  const tables = ['oturum_outbox', 'reklam_gosterim_outbox'];
  for (const t of tables) {
    const trigger = `${t}_fifo_cap`;
    db.exec(`DROP TRIGGER IF EXISTS ${trigger};`);
    db.exec(`
      CREATE TRIGGER ${trigger}
      AFTER INSERT ON ${t}
      WHEN (SELECT COUNT(*) FROM ${t}) > ${limit}
      BEGIN
        DELETE FROM ${t}
         WHERE id IN (
           SELECT id FROM ${t}
            ORDER BY id ASC
            LIMIT ((SELECT COUNT(*) FROM ${t}) - ${limit})
         );
      END;
    `);
  }
}

// ── Satir donusturuculer ──
export function rowToKategori(row) {
  if (!row) return null;
  return {
    id: row.id,
    slug: row.slug,
    ad: row.ad,
    ikon: row.ikon,
    bagli_kategori_id: row.bagli_kategori_id ?? null,
    hedef_cinsiyet_id: row.hedef_cinsiyet_id ?? null,
    aktif: !!row.aktif,
    hedef_cinsiyetler: safeJson(row.hedef_cinsiyetler, []),
    hedef_yas_araliklari: safeJson(row.hedef_yas_araliklari, []),
  };
}

export function rowToDanismaKategori(row) {
  if (!row) return null;
  return {
    id: row.id,
    slug: row.slug,
    ad: row.ad,
    ikon: row.ikon,
    ust_kategori_id: row.ust_kategori_id ?? null,
    aktif: !!row.aktif,
  };
}

export function rowToSoru(row) {
  if (!row) return null;
  return {
    id: row.id,
    kategori_id: row.kategori_id,
    seed_id: row.seed_id,
    metin: row.metin,
    sira: row.sira,
    eslesme_kurallari: safeJson(row.eslesme_kurallari, []),
    hedef_cinsiyet_id: row.hedef_cinsiyet_id ?? null,
    hedef_cinsiyetler: safeJson(row.hedef_cinsiyetler, []),
    hedef_yas_araliklari: safeJson(row.hedef_yas_araliklari, []),
  };
}

export function rowToCreative(row) {
  if (!row) return null;
  return {
    id: row.id,
    media_url: row.media_url,
    duration_seconds: row.duration_seconds,
    checksum: row.checksum,
    type: row.type || 'creative',
    aktif: !!row.aktif,
  };
}

export function rowToHouseAd(row) {
  if (!row) return null;
  return {
    id: row.id,
    name: row.name,
    media_url: row.media_url,
    duration_seconds: row.duration_seconds,
    type: row.type || 'house_ad',
    aktif: !!row.aktif,
  };
}

export function safeJson(raw, fallback) {
  if (raw === null || raw === undefined) return fallback;
  if (typeof raw !== 'string') return raw;
  try {
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

// ── Faz 5: Pending ACK helpers ───────────────────────────────────────────────

/**
 * Manifest başarıyla uygulandıktan sonra pending ACK kaydet (singleton).
 * İkinci kayıt eski kaydın üzerine yazar (UPDATE OR REPLACE).
 */
export function savePendingAck(db, { playlistVersion, horizonStart, horizonEnd }) {
  db.prepare(
    `INSERT OR REPLACE INTO pending_ack (id, playlist_version, horizon_start, horizon_end, retry_count)
     VALUES (1, ?, ?, ?, 0)`,
  ).run(playlistVersion, horizonStart, horizonEnd);
}

/**
 * Pending ACK'i oku. Yoksa null döner.
 */
export function getPendingAck(db) {
  return db.prepare('SELECT * FROM pending_ack WHERE id = 1').get() ?? null;
}

/**
 * Pending ACK başarıyla gönderildikten sonra sil.
 */
export function clearPendingAck(db) {
  db.prepare('DELETE FROM pending_ack WHERE id = 1').run();
}

/**
 * Pending ACK'i koşullu temizle (compare-and-swap).
 * Yalnızca version+horizon tam eşleşiyorsa siler.
 * Daha yeni manifest uygulanmışsa (yeni pending_ack) eski ACK cevabı onu silemez.
 */
export function clearPendingAckIfMatches(db, { playlistVersion, horizonStart, horizonEnd }) {
  db.prepare(
    `DELETE FROM pending_ack WHERE id = 1
     AND playlist_version = ? AND horizon_start = ? AND horizon_end = ?`,
  ).run(playlistVersion, horizonStart, horizonEnd);
}

/**
 * ACK retry için sonraki deneme zamanını ayarla (capped exponential backoff).
 * Max retry sınırı yok — sonsuz tight loop olmadan kalıcı olarak tutulur.
 * Daha yeni manifest uygulanınca pending_ack üzerine yazılır (INSERT OR REPLACE).
 */
export function setAckNextRetry(db, retryCount) {
  // Backoff: 30s, 60s, 120s, 300s, 600s, 1800s (max 30 dk)
  const backoffSeconds = [30, 60, 120, 300, 600, 1800];
  const backoff = backoffSeconds[Math.min(retryCount, backoffSeconds.length - 1)];
  const nextRetryAt = new Date(Date.now() + backoff * 1000).toISOString();
  db.prepare(
    'UPDATE pending_ack SET next_retry_at = ?, retry_count = retry_count + 1 WHERE id = 1',
  ).run(nextRetryAt);
  return { backoff, nextRetryAt };
}
