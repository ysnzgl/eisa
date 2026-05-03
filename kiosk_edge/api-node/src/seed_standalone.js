// Standalone kiosk SQLite seed scripti.
// Kullanım: node src/seed_standalone.js [--db ./local.db] [--seed ../../master_seed.json] [--force]
import { parseArgs } from 'node:util';
import path from 'node:path';
import fs from 'node:fs';
import Database from 'better-sqlite3';
import { DEFAULT_SEED_PATH, seedCategoriesIfEmpty, seedCampaignsIfEmpty } from './seed.js';

const { values } = parseArgs({
  options: {
    db: { type: 'string', default: './local_dev.db' },
    seed: { type: 'string', default: DEFAULT_SEED_PATH },
    force: { type: 'boolean', default: false },
  },
});

const dbPath = path.resolve(values.db);
const seedPath = path.resolve(values.seed);

if (!fs.existsSync(seedPath)) {
  console.error(`HATA: Seed dosyası bulunamadı: ${seedPath}`);
  process.exit(1);
}

const db = new Database(dbPath);
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

// Şemayı garantile (api-node ile aynı)
db.exec(`
  CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT 'fa-circle',
    is_sensitive INTEGER NOT NULL DEFAULT 0, is_active INTEGER NOT NULL DEFAULT 1);
  CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    seed_id TEXT NOT NULL UNIQUE, text TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0, match_rules TEXT NOT NULL DEFAULT '[]');
  CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL,
    media_local_path TEXT NOT NULL DEFAULT '',
    starts_at TEXT NOT NULL, ends_at TEXT NOT NULL,
    targeting TEXT NOT NULL DEFAULT '{}', is_active INTEGER NOT NULL DEFAULT 1);
`);

if (values.force) {
  db.exec('DELETE FROM questions; DELETE FROM categories;');
  console.log('--force: questions ve categories tabloları temizlendi.');
}

const result = seedCategoriesIfEmpty(db, seedPath);
if (result.skipped) {
  console.log('Kiosk DB zaten dolu, seed atlandı. --force ile zorla.');
} else {
  console.log(
    `✓ Kiosk SQLite seed tamamlandı: ${result.cats} kategori, ${result.qs} soru → ${dbPath}`,
  );
}

const camp = seedCampaignsIfEmpty(db);
if (!camp.skipped) {
  console.log(`✓ ${camp.count} demo kampanya yüklendi.`);
}

db.close();
