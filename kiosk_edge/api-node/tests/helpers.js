import Database from 'better-sqlite3';

export function makeMemoryDb() {
  const db = new Database(':memory:');
  db.pragma('foreign_keys = ON');
  db.exec(`
    CREATE TABLE categories (
      id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
      icon TEXT NOT NULL DEFAULT 'fa-circle',
      is_sensitive INTEGER NOT NULL DEFAULT 0, is_active INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE questions (
      id INTEGER PRIMARY KEY,
      category_id INTEGER NOT NULL REFERENCES categories(id),
      seed_id TEXT NOT NULL UNIQUE, text TEXT NOT NULL,
      priority INTEGER NOT NULL DEFAULT 0, match_rules TEXT NOT NULL DEFAULT '[]');
    CREATE TABLE campaigns (
      id INTEGER PRIMARY KEY, name TEXT NOT NULL,
      media_local_path TEXT NOT NULL DEFAULT '',
      starts_at TEXT NOT NULL, ends_at TEXT NOT NULL,
      targeting TEXT NOT NULL DEFAULT '{}', is_active INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE session_log_outbox (
      id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      pushed_at TEXT);
    CREATE TABLE ad_impression_outbox (
      id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      pushed_at TEXT);
  `);
  return db;
}

export const fakeSettings = {
  sqlitePath: ':memory:',
  centralApiBase: 'http://localhost:8000',
  kioskAppKey: 'test-key',
  kioskMac: '00:11:22:33:44:55',
  localApiSecret: 'test-secret',
  pullIntervalSec: 900,
  pushIntervalSec: 300,
  verifyTls: false,
  devMode: true,
  host: '127.0.0.1',
  port: 0,
};
