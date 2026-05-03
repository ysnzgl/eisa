// SQLite (better-sqlite3) — şema oluşturma ve JSON yardımcıları.
import path from 'node:path';
import fs from 'node:fs';
import Database from 'better-sqlite3';

let _db = null;

// Outbox satır sayısı bu eşiği aşarsa "FIFO koruması" devreye girer.
// Kiosk uzun süre çevrimdışı kalsa bile eMMC dolmaz.
const DEFAULT_OUTBOX_MAX_ROWS = 10000;

export function openDb(sqlitePath, options = {}) {
  if (_db) return _db;
  const dir = path.dirname(sqlitePath);
  if (dir && dir !== '.' && !fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  _db = new Database(sqlitePath);
  _db.pragma('journal_mode = WAL');
  _db.pragma('foreign_keys = ON');
  initSchema(_db, options.outboxMaxRows ?? DEFAULT_OUTBOX_MAX_ROWS);
  return _db;
}

export function getDb() {
  if (!_db) throw new Error('DB açılmadı; önce openDb() çağırın.');
  return _db;
}

export function closeDb() {
  if (_db) {
    _db.close();
    _db = null;
  }
}

function initSchema(db, outboxMaxRows = DEFAULT_OUTBOX_MAX_ROWS) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS categories (
      id           INTEGER PRIMARY KEY,
      slug         TEXT    NOT NULL UNIQUE,
      name         TEXT    NOT NULL,
      icon         TEXT    NOT NULL DEFAULT 'fa-circle',
      is_sensitive INTEGER NOT NULL DEFAULT 0,
      is_active    INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS questions (
      id          INTEGER PRIMARY KEY,
      category_id INTEGER NOT NULL REFERENCES categories(id),
      seed_id     TEXT    NOT NULL UNIQUE,
      text        TEXT    NOT NULL,
      priority    INTEGER NOT NULL DEFAULT 0,
      match_rules TEXT    NOT NULL DEFAULT '[]'
    );

    CREATE TABLE IF NOT EXISTS campaigns (
      id               INTEGER PRIMARY KEY,
      name             TEXT    NOT NULL,
      media_local_path TEXT    NOT NULL DEFAULT '',
      starts_at        TEXT    NOT NULL,
      ends_at          TEXT    NOT NULL,
      targeting        TEXT    NOT NULL DEFAULT '{}',
      is_active        INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS session_log_outbox (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      payload    TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      pushed_at  TEXT
    );

    CREATE TABLE IF NOT EXISTS ad_impression_outbox (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      payload    TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      pushed_at  TEXT
    );
  `);

  installOutboxFifoTriggers(db, outboxMaxRows);
}

/**
 * FIFO koruyucu trigger'ları kurar.
 * Outbox tablosu `maxRows`'u aşınca en eski kayıtlar (id ASC) silinir.
 * Bu, eMMC'nin dolmasını ve OS-seviyesi kilitlenmeyi önleyen son güvenlik bariyeridir.
 *
 * Not: Tetikleyici INSERT'ten SONRA çalışır; bu yüzden boyut tabanlı toplu ekleme
 * sırasında bile satır sayısı `maxRows`'un sadece çok kısa süreliğine üstüne çıkabilir.
 */
export function installOutboxFifoTriggers(db, maxRows = DEFAULT_OUTBOX_MAX_ROWS) {
  const limit = Math.max(100, Number(maxRows) | 0);
  const tables = ['session_log_outbox', 'ad_impression_outbox'];
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

// JSON sütunlarını parse eden satır dönüştürücüleri
export function rowToCategory(row) {
  if (!row) return null;
  return {
    id: row.id,
    slug: row.slug,
    name: row.name,
    icon: row.icon,
    is_sensitive: !!row.is_sensitive,
    is_active: !!row.is_active,
  };
}

export function rowToQuestion(row) {
  if (!row) return null;
  return {
    id: row.id,
    category_id: row.category_id,
    seed_id: row.seed_id,
    text: row.text,
    priority: row.priority,
    match_rules: safeJson(row.match_rules, []),
  };
}

export function rowToCampaign(row) {
  if (!row) return null;
  return {
    id: row.id,
    name: row.name,
    media_local_path: row.media_local_path,
    starts_at: row.starts_at,
    ends_at: row.ends_at,
    targeting: safeJson(row.targeting, {}),
    is_active: !!row.is_active,
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
