// master_seed.json + lookup → SQLite seed yukleyici (Turkce sema).
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// kiosk_edge/api-node/src/seed.js → monorepo koku = ../../../
export const DEFAULT_SEED_PATH = path.resolve(__dirname, '..', '..', '..', 'master_seed.json');

const HASSAS_SLUGLAR = new Set(['cinsel', 'hemoroid', 'koku', 'mantar', 'sac', 'ishal']);

const CINSIYET_SEED = [
  { kod: 'F', ad: 'Kadin' },
  { kod: 'M', ad: 'Erkek' },
  { kod: 'O', ad: 'Diger' },
];

const YAS_ARALIGI_SEED = [
  { kod: '0-17',  ad: '0-17',  alt_sinir: 0,  ust_sinir: 17 },
  { kod: '18-25', ad: '18-25', alt_sinir: 18, ust_sinir: 25 },
  { kod: '26-35', ad: '26-35', alt_sinir: 26, ust_sinir: 35 },
  { kod: '36-50', ad: '36-50', alt_sinir: 36, ust_sinir: 50 },
  { kod: '51-65', ad: '51-65', alt_sinir: 51, ust_sinir: 65 },
  { kod: '65+',   ad: '65+',   alt_sinir: 65, ust_sinir: null },
];

const IL_ILCE_SEED = {
  Istanbul: ['Kadikoy', 'Besiktas', 'Sisli', 'Uskudar', 'Bakirkoy', 'Atasehir'],
  Ankara:   ['Cankaya', 'Kecioren', 'Mamak', 'Yenimahalle'],
  Izmir:    ['Konak', 'Bornova', 'Karsiyaka', 'Buca'],
  Bursa:    ['Osmangazi', 'Nilufer', 'Yildirim'],
  Antalya:  ['Muratpasa', 'Konyaalti', 'Kepez'],
};

const DEMO_REKLAMLAR = [
  {
    ad: 'Kis Bagisiklik Paketi',
    medya_url:
      'https://images.unsplash.com/photo-1607619056574-7b8d3ee536b2?w=794&h=900&fit=crop',
    hedefleme: { saat_baslangic: 8, saat_bitis: 22 },
  },
  {
    ad: 'Omega-3 ve Beyin Sagligi',
    medya_url:
      'https://images.unsplash.com/photo-1628771065518-0d82f1938462?w=794&h=900&fit=crop',
    hedefleme: { saat_baslangic: 8, saat_bitis: 22 },
  },
  {
    ad: 'Probiyotik — Bagirsak Dostunuz',
    medya_url:
      'https://images.unsplash.com/photo-1543362906-acfc16c67564?w=794&h=900&fit=crop',
    hedefleme: { saat_baslangic: 8, saat_bitis: 22 },
  },
];

/**
 * Tum lookup tablolarini idempotent sekilde tohumlar (mevcut kayit varsa atlanir).
 */
export function seedLookupsIfEmpty(db) {
  const out = { cinsiyet: 0, yas_araligi: 0, il: 0, ilce: 0 };

  const insCinsiyet = db.prepare('INSERT OR IGNORE INTO cinsiyetler (kod, ad) VALUES (?, ?)');
  const insYas = db.prepare(
    'INSERT OR IGNORE INTO yas_araliklari (kod, ad, alt_sinir, ust_sinir) VALUES (?, ?, ?, ?)',
  );
  const insIl = db.prepare('INSERT OR IGNORE INTO iller (ad) VALUES (?)');
  const insIlce = db.prepare('INSERT OR IGNORE INTO ilceler (il_id, ad) VALUES (?, ?)');
  const selIl = db.prepare('SELECT id FROM iller WHERE ad = ?');

  const tx = db.transaction(() => {
    for (const c of CINSIYET_SEED) out.cinsiyet += insCinsiyet.run(c.kod, c.ad).changes;
    for (const y of YAS_ARALIGI_SEED) {
      out.yas_araligi += insYas.run(y.kod, y.ad, y.alt_sinir, y.ust_sinir).changes;
    }
    for (const [il, ilceler] of Object.entries(IL_ILCE_SEED)) {
      out.il += insIl.run(il).changes;
      const ilRow = selIl.get(il);
      if (ilRow) {
        for (const ilceAd of ilceler) out.ilce += insIlce.run(ilRow.id, ilceAd).changes;
      }
    }
  });
  tx();
  return out;
}

export function seedKategorilerIfEmpty(db, seedPath = DEFAULT_SEED_PATH, logger = console) {
  const exists = db.prepare('SELECT 1 FROM kategoriler LIMIT 1').get();
  if (exists) return { skipped: true };

  if (!fs.existsSync(seedPath)) {
    logger.warn?.(`master_seed.json bulunamadi: ${seedPath}`);
    return { skipped: true, missing: true };
  }

  const seed = JSON.parse(fs.readFileSync(seedPath, 'utf-8'));

  const insKat = db.prepare(
    `INSERT INTO kategoriler (slug, ad, ikon, hassas, aktif)
     VALUES (@slug, @ad, @ikon, @hassas, @aktif)`,
  );
  const insSoru = db.prepare(
    `INSERT INTO sorular (kategori_id, seed_id, metin, sira, eslesme_kurallari)
     VALUES (@kategori_id, @seed_id, @metin, @sira, @eslesme_kurallari)`,
  );
  const insEm = db.prepare(
    `INSERT OR IGNORE INTO etken_maddeler (ad, aciklama) VALUES (?, ?)`,
  );

  const tx = db.transaction((items) => {
    let cats = 0, qs = 0, ems = 0;
    for (const c of items) {
      const slug = c.category_slug;
      const info = insKat.run({
        slug,
        ad: c.title,
        ikon: c.icon || 'fa-circle',
        hassas: HASSAS_SLUGLAR.has(slug) ? 1 : 0,
        aktif: 1,
      });
      cats += 1;
      const kategoriId = info.lastInsertRowid;
      for (const q of c.questions || []) {
        insSoru.run({
          kategori_id: kategoriId,
          seed_id: q.id,
          metin: q.text,
          sira: q.priority ?? 0,
          eslesme_kurallari: JSON.stringify(q.match_rules ?? []),
        });
        qs += 1;
        for (const rule of q.match_rules ?? []) {
          for (const em of [rule.primary, rule.supportive]) {
            if (em) ems += insEm.run(em, '').changes;
          }
        }
      }
    }
    return { cats, qs, ems };
  });

  const result = tx(seed);
  return { skipped: false, ...result };
}

export function seedReklamlarIfEmpty(db) {
  const exists = db.prepare('SELECT 1 FROM reklamlar LIMIT 1').get();
  if (exists) return { skipped: true };

  const now = new Date();
  const farFuture = new Date(now.getTime() + 365 * 24 * 60 * 60 * 1000);
  const insert = db.prepare(
    `INSERT INTO reklamlar (ad, medya_url, baslangic_tarihi, bitis_tarihi, hedefleme, aktif)
     VALUES (@ad, @medya_url, @baslangic_tarihi, @bitis_tarihi, @hedefleme, 1)`,
  );

  const tx = db.transaction(() => {
    for (const r of DEMO_REKLAMLAR) {
      insert.run({
        ad: r.ad,
        medya_url: r.medya_url,
        baslangic_tarihi: now.toISOString(),
        bitis_tarihi: farFuture.toISOString(),
        hedefleme: JSON.stringify(r.hedefleme || {}),
      });
    }
  });
  tx();
  return { skipped: false, count: DEMO_REKLAMLAR.length };
}

// ── Geriye uyumlu eski isimler (scheduler/server icinde dogrudan import edenler icin) ──
export const seedCategoriesIfEmpty = seedKategorilerIfEmpty;
export const seedCampaignsIfEmpty = seedReklamlarIfEmpty;
