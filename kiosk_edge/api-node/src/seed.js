// master_seed.json → SQLite seed yükleyici.
// Uygulama başlangıcında tablolar boşsa verileri yazar.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// kiosk_edge/api-node/src/seed.js → monorepo kökü = ../../../
export const DEFAULT_SEED_PATH = path.resolve(
  __dirname,
  '..',
  '..',
  '..',
  'master_seed.json',
);

const DEMO_CAMPAIGNS = [
  {
    name: 'Kış Bağışıklık Paketi',
    media_local_path:
      'https://images.unsplash.com/photo-1607619056574-7b8d3ee536b2?w=794&h=900&fit=crop',
    targeting: { hours_start: 8, hours_end: 22 },
  },
  {
    name: 'Omega-3 & Beyin Sağlığı',
    media_local_path:
      'https://images.unsplash.com/photo-1628771065518-0d82f1938462?w=794&h=900&fit=crop',
    targeting: { hours_start: 8, hours_end: 22 },
  },
  {
    name: 'Probiyotik — Bağırsak Dostunuz',
    media_local_path:
      'https://images.unsplash.com/photo-1543362906-acfc16c67564?w=794&h=900&fit=crop',
    targeting: { hours_start: 8, hours_end: 22 },
  },
];

export function seedCategoriesIfEmpty(db, seedPath = DEFAULT_SEED_PATH, logger = console) {
  const exists = db.prepare('SELECT 1 FROM categories LIMIT 1').get();
  if (exists) return { skipped: true };

  if (!fs.existsSync(seedPath)) {
    logger.warn?.(`master_seed.json bulunamadı: ${seedPath}`);
    return { skipped: true, missing: true };
  }

  const seed = JSON.parse(fs.readFileSync(seedPath, 'utf-8'));

  const insertCat = db.prepare(
    `INSERT INTO categories (slug, name, icon, is_sensitive, is_active)
     VALUES (@slug, @name, @icon, @is_sensitive, @is_active)`,
  );
  const insertQ = db.prepare(
    `INSERT INTO questions (category_id, seed_id, text, priority, match_rules)
     VALUES (@category_id, @seed_id, @text, @priority, @match_rules)`,
  );

  const tx = db.transaction((items) => {
    let cats = 0;
    let qs = 0;
    for (const c of items) {
      const info = insertCat.run({
        slug: c.category_slug,
        name: c.title,
        icon: c.icon || 'fa-circle',
        is_sensitive: 0,
        is_active: 1,
      });
      cats += 1;
      const categoryId = info.lastInsertRowid;
      for (const q of c.questions || []) {
        insertQ.run({
          category_id: categoryId,
          seed_id: q.id,
          text: q.text,
          priority: q.priority ?? 0,
          match_rules: JSON.stringify(q.match_rules ?? []),
        });
        qs += 1;
      }
    }
    return { cats, qs };
  });

  const result = tx(seed);
  return { skipped: false, ...result };
}

export function seedCampaignsIfEmpty(db) {
  const exists = db.prepare('SELECT 1 FROM campaigns LIMIT 1').get();
  if (exists) return { skipped: true };

  const now = new Date();
  const farFuture = new Date(now.getTime() + 365 * 24 * 60 * 60 * 1000);
  const insert = db.prepare(
    `INSERT INTO campaigns (name, media_local_path, starts_at, ends_at, targeting, is_active)
     VALUES (@name, @media_local_path, @starts_at, @ends_at, @targeting, 1)`,
  );

  const tx = db.transaction(() => {
    for (const c of DEMO_CAMPAIGNS) {
      insert.run({
        name: c.name,
        media_local_path: c.media_local_path,
        starts_at: now.toISOString(),
        ends_at: farFuture.toISOString(),
        targeting: JSON.stringify(c.targeting || {}),
      });
    }
  });
  tx();
  return { skipped: false, count: DEMO_CAMPAIGNS.length };
}
