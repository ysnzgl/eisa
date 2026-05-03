import { describe, it, expect, beforeEach } from 'vitest';
import { buildServer } from '../src/server.js';
import { makeMemoryDb, fakeSettings } from './helpers.js';

async function makeApp() {
  const db = makeMemoryDb();

  // Seed: 1 kategori + 2 soru + 1 aktif kampanya
  db.prepare(
    `INSERT INTO categories (id, slug, name, icon, is_sensitive, is_active)
     VALUES (1, 'energy', 'Enerji', 'fa-bolt', 0, 1)`,
  ).run();
  db.prepare(
    `INSERT INTO questions (id, category_id, seed_id, text, priority, match_rules)
     VALUES (1, 1, 'en_q1', 'Yorgun musunuz?', 1, '[]'),
            (2, 1, 'en_q2', 'Uykunuz nasıl?', 2, '[]')`,
  ).run();

  const now = new Date();
  const past = new Date(now.getTime() - 24 * 3600 * 1000).toISOString();
  const future = new Date(now.getTime() + 24 * 3600 * 1000).toISOString();
  db.prepare(
    `INSERT INTO campaigns (id, name, media_local_path, starts_at, ends_at, targeting, is_active)
     VALUES (10, 'C1', '/m1.png', ?, ?, '{}', 1)`,
  ).run(past, future);

  const app = await buildServer({ db, settings: fakeSettings, logger: false });
  return { app, db };
}

describe('Kiosk API', () => {
  let app, db;
  beforeEach(async () => {
    ({ app, db } = await makeApp());
  });

  it('GET /health', async () => {
    const r = await app.inject({ method: 'GET', url: '/health' });
    expect(r.statusCode).toBe(200);
    expect(r.json()).toEqual({ status: 'ok' });
  });

  it('GET /api/categories aktif olanları döner', async () => {
    const r = await app.inject({ method: 'GET', url: '/api/categories' });
    expect(r.statusCode).toBe(200);
    const data = r.json();
    expect(data).toHaveLength(1);
    expect(data[0].slug).toBe('energy');
  });

  it('GET /api/categories/:slug/questions priority sırasıyla', async () => {
    const r = await app.inject({
      method: 'GET',
      url: '/api/categories/energy/questions',
    });
    expect(r.statusCode).toBe(200);
    const qs = r.json();
    expect(qs).toHaveLength(2);
    expect(qs[0].seed_id).toBe('en_q1');
  });

  it('GET /api/categories/:slug/questions 404', async () => {
    const r = await app.inject({
      method: 'GET',
      url: '/api/categories/yok/questions',
    });
    expect(r.statusCode).toBe(404);
  });

  it('POST /api/session/submit qr üretir ve outbox\'a yazar', async () => {
    const r = await app.inject({
      method: 'POST',
      url: '/api/session/submit',
      headers: { 'content-type': 'application/json' },
      payload: {
        age_range: '26-35',
        gender: 'M',
        category_slug: 'energy',
        answers_payload: { en_q1: 'Y' },
      },
    });
    expect(r.statusCode).toBe(200);
    const data = r.json();
    expect(data.status).toBe('saved');
    expect(data.qr_code).toMatch(/^[A-F0-9]{12}$/);

    const row = db.prepare('SELECT payload FROM session_log_outbox').get();
    expect(row).toBeTruthy();
    const payload = JSON.parse(row.payload);
    expect(payload.qr_code).toBe(data.qr_code);
    expect(payload.gender).toBe('M');
  });

  it('POST /api/session/submit geçersiz yaş 422', async () => {
    const r = await app.inject({
      method: 'POST',
      url: '/api/session/submit',
      payload: { age_range: 'X', gender: 'M', category_slug: 'energy' },
    });
    expect(r.statusCode).toBe(422);
  });

  it('GET /api/session/:qr Bearer secret olmadan 401', async () => {
    const r = await app.inject({
      method: 'GET',
      url: '/api/session/ABCDEF123456',
    });
    expect(r.statusCode).toBe(401);
  });

  it('GET /api/session/:qr başarılı sorgu', async () => {
    const submit = await app.inject({
      method: 'POST',
      url: '/api/session/submit',
      payload: {
        age_range: '26-35',
        gender: 'F',
        category_slug: 'energy',
        qr_code: 'ABCDEF123456',
        answers_payload: {},
      },
    });
    expect(submit.statusCode).toBe(200);

    const r = await app.inject({
      method: 'GET',
      url: '/api/session/ABCDEF123456',
      headers: { authorization: `Bearer ${fakeSettings.localApiSecret}` },
    });
    expect(r.statusCode).toBe(200);
    const data = r.json();
    expect(data.found).toBe(true);
    expect(data.session.qr_code).toBe('ABCDEF123456');
  });

  it('GET /api/session/:qr bulunamadı 404', async () => {
    const r = await app.inject({
      method: 'GET',
      url: '/api/session/NOTEXIST1234',
      headers: { authorization: `Bearer ${fakeSettings.localApiSecret}` },
    });
    expect(r.statusCode).toBe(404);
  });

  it('GET /api/campaigns/active aktif kampanyaları döner', async () => {
    const r = await app.inject({ method: 'GET', url: '/api/campaigns/active' });
    expect(r.statusCode).toBe(200);
    const data = r.json();
    expect(data).toHaveLength(1);
    expect(data[0].id).toBe(10);
  });

  it('POST /api/ad-impression 201 ve outbox\'a yazar', async () => {
    const r = await app.inject({
      method: 'POST',
      url: '/api/ad-impression',
      payload: {
        campaign_id: 10,
        shown_at: new Date().toISOString(),
        duration_ms: 3000,
      },
    });
    expect(r.statusCode).toBe(201);
    const row = db.prepare('SELECT payload FROM ad_impression_outbox').get();
    expect(row).toBeTruthy();
    const p = JSON.parse(row.payload);
    expect(p.campaign_id).toBe(10);
  });
});
