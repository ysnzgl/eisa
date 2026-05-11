// SQLite (better-sqlite3) — yerel offline-first sema (Turkce + lookup tablolari).
// Backend'in 3NF semasiyla 1:1 hizalanir; kiosk dis sunucu olmadan calisir.
import path from 'node:path';
import fs from 'node:fs';
import Database from 'better-sqlite3';

let _db = null;

const DEFAULT_OUTBOX_MAX_ROWS = 10000;

// Sema versiyonu — creatives ve house_ads tablolari eklendi; reklamlar kaldirildi.
// proof-of-play outbox payload guncellendi.
const SCHEMA_VERSION = 4;

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
  _db.pragma('foreign_keys = ON');
  initSchema(_db, options.outboxMaxRows ?? DEFAULT_OUTBOX_MAX_ROWS);
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

function initSchema(db, outboxMaxRows = DEFAULT_OUTBOX_MAX_ROWS) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS schema_meta (version INTEGER NOT NULL);

    -- LOOKUP TABLOLARI (audit kolonu YOK)
    CREATE TABLE IF NOT EXISTS iller (
      id    INTEGER PRIMARY KEY,
      ad    TEXT    NOT NULL UNIQUE
    );
    CREATE TABLE IF NOT EXISTS ilceler (
      id    INTEGER PRIMARY KEY,
      il_id INTEGER NOT NULL REFERENCES iller(id),
      ad    TEXT    NOT NULL
    );
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
      hassas               INTEGER NOT NULL DEFAULT 0,
      aktif                INTEGER NOT NULL DEFAULT 1,
      surum                INTEGER NOT NULL DEFAULT 1,
      hedef_cinsiyetler    TEXT    NOT NULL DEFAULT '[]',
      hedef_yas_araliklari TEXT    NOT NULL DEFAULT '[]',
      olusturulma_tarihi   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      guncellenme_tarihi   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );

    CREATE TABLE IF NOT EXISTS sorular (
      id                   INTEGER PRIMARY KEY,
      kategori_id          INTEGER NOT NULL REFERENCES kategoriler(id),
      seed_id              TEXT,
      metin                TEXT    NOT NULL,
      sira                 INTEGER NOT NULL DEFAULT 0,
      eslesme_kurallari    TEXT    NOT NULL DEFAULT '[]',
      surum                INTEGER NOT NULL DEFAULT 1,
      hedef_cinsiyetler    TEXT    NOT NULL DEFAULT '[]',
      hedef_yas_araliklari TEXT    NOT NULL DEFAULT '[]',
      olusturulma_tarihi   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      guncellenme_tarihi   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );

    CREATE TABLE IF NOT EXISTS cevaplar (
      id      INTEGER PRIMARY KEY,
      soru_id INTEGER NOT NULL REFERENCES sorular(id) ON DELETE CASCADE,
      metin   TEXT    NOT NULL,
      agirlik INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS etken_maddeler (
      id       INTEGER PRIMARY KEY,
      ad       TEXT    NOT NULL UNIQUE,
      aciklama TEXT    NOT NULL DEFAULT ''
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
      gonderilme_tarihi    TEXT
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
    CREATE INDEX IF NOT EXISTS ilceler_il_idx        ON ilceler(il_id);
    CREATE INDEX IF NOT EXISTS oturum_outbox_pending ON oturum_outbox(gonderilme_tarihi);
    CREATE INDEX IF NOT EXISTS reklam_outbox_pending ON reklam_gosterim_outbox(gonderilme_tarihi);
  `);

  const meta = db.prepare('SELECT version FROM schema_meta LIMIT 1').get();
  if (!meta) {
    db.prepare('INSERT INTO schema_meta (version) VALUES (?)').run(SCHEMA_VERSION);
  } else if (meta.version !== SCHEMA_VERSION) {
    db.prepare('UPDATE schema_meta SET version = ?').run(SCHEMA_VERSION);
  }

  installOutboxFifoTriggers(db, outboxMaxRows);
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
    hassas: !!row.hassas,
    aktif: !!row.aktif,
    hedef_cinsiyetler: safeJson(row.hedef_cinsiyetler, []),
    hedef_yas_araliklari: safeJson(row.hedef_yas_araliklari, []),
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
