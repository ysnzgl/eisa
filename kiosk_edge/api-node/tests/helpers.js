// Test yardimcilari — yeni Turkce sema (db.js initSchema'siyla birebir).
import Database from 'better-sqlite3';

export function makeMemoryDb() {
  const db = new Database(':memory:');
  db.pragma('foreign_keys = ON');
  db.exec(`
    CREATE TABLE iller (
      id INTEGER PRIMARY KEY, ad TEXT NOT NULL UNIQUE, plaka INTEGER);
    CREATE TABLE ilceler (
      id INTEGER PRIMARY KEY, il_id INTEGER NOT NULL REFERENCES iller(id), ad TEXT NOT NULL);
    CREATE TABLE cinsiyetler (
      id INTEGER PRIMARY KEY, kod TEXT NOT NULL UNIQUE, ad TEXT NOT NULL);
    CREATE TABLE yas_araliklari (
      id INTEGER PRIMARY KEY, kod TEXT NOT NULL UNIQUE, ad TEXT NOT NULL,
      alt_sinir INTEGER, ust_sinir INTEGER);

    CREATE TABLE kategoriler (
      id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, ad TEXT NOT NULL,
      ikon TEXT NOT NULL DEFAULT 'fa-circle',
      hassas INTEGER NOT NULL DEFAULT 0, aktif INTEGER NOT NULL DEFAULT 1,
      surum INTEGER NOT NULL DEFAULT 1,
      hedef_cinsiyetler TEXT NOT NULL DEFAULT '[]',
      hedef_yas_araliklari TEXT NOT NULL DEFAULT '[]',
      olusturulma_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      guncellenme_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));

    CREATE TABLE sorular (
      id INTEGER PRIMARY KEY,
      kategori_id INTEGER NOT NULL REFERENCES kategoriler(id),
      seed_id TEXT, metin TEXT NOT NULL,
      sira INTEGER NOT NULL DEFAULT 0, eslesme_kurallari TEXT NOT NULL DEFAULT '[]',
      surum INTEGER NOT NULL DEFAULT 1,
      hedef_cinsiyetler TEXT NOT NULL DEFAULT '[]',
      hedef_yas_araliklari TEXT NOT NULL DEFAULT '[]',
      olusturulma_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      guncellenme_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));

    CREATE TABLE cevaplar (
      id INTEGER PRIMARY KEY, soru_id INTEGER NOT NULL REFERENCES sorular(id) ON DELETE CASCADE,
      metin TEXT NOT NULL, agirlik INTEGER NOT NULL DEFAULT 0);

    CREATE TABLE etken_maddeler (
      id INTEGER PRIMARY KEY, ad TEXT NOT NULL UNIQUE, aciklama TEXT NOT NULL DEFAULT '');

    CREATE TABLE reklamlar (
      id INTEGER PRIMARY KEY, ad TEXT NOT NULL,
      medya_url TEXT NOT NULL DEFAULT '',
      baslangic_tarihi TEXT NOT NULL, bitis_tarihi TEXT NOT NULL,
      hedefleme TEXT NOT NULL DEFAULT '{}', aktif INTEGER NOT NULL DEFAULT 1,
      surum INTEGER NOT NULL DEFAULT 1,
      olusturulma_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      guncellenme_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));

    CREATE TABLE oturum_outbox (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      idempotency_anahtari TEXT UNIQUE,
      payload TEXT NOT NULL,
      olusturulma_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      gonderilme_tarihi TEXT);

    CREATE TABLE reklam_gosterim_outbox (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      idempotency_anahtari TEXT UNIQUE,
      payload TEXT NOT NULL,
      olusturulma_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      gonderilme_tarihi TEXT);
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
