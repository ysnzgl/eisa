import { describe, it, expect, beforeEach } from 'vitest';
import { buildServer } from '../src/server.js';
import { makeMemoryDb, fakeSettings } from './helpers.js';

async function makeApp() {
  const db = makeMemoryDb();

  // Lookup seed (cinsiyet/yas_araligi)
  db.prepare("INSERT INTO cinsiyetler (kod, ad) VALUES ('M','Erkek'),('F','Kadin'),('O','Diger')").run();
  db.prepare(
    "INSERT INTO yas_araliklari (kod, ad, alt_sinir, ust_sinir) VALUES ('26-35','26-35',26,35)",
  ).run();

  // 1 kategori + 2 soru + 1 aktif reklam
  db.prepare(
    `INSERT INTO kategoriler (id, slug, ad, ikon, hassas, aktif)
     VALUES (1, 'enerji', 'Enerji', 'fa-bolt', 0, 1)`,
  ).run();
  db.prepare(
    `INSERT INTO sorular (id, kategori_id, seed_id, metin, sira, eslesme_kurallari)
     VALUES (1, 1, 'en_q1', 'Yorgun musunuz?', 1, '[]'),
            (2, 1, 'en_q2', 'Uykunuz nasil?', 2, '[]')`,
  ).run();

  const now = new Date();
  const past = new Date(now.getTime() - 24 * 3600 * 1000).toISOString();
  const future = new Date(now.getTime() + 24 * 3600 * 1000).toISOString();
  db.prepare(
    `INSERT INTO reklamlar (id, ad, medya_url, baslangic_tarihi, bitis_tarihi, hedefleme, aktif)
     VALUES (10, 'R1', '/m1.png', ?, ?, '{}', 1)`,
  ).run(past, future);

  const app = await buildServer({ db, settings: fakeSettings, logger: false });
  return { app, db };
}

describe('Kiosk API (Turkce sema)', () => {
  let app, db;
  beforeEach(async () => { ({ app, db } = await makeApp()); });

  it('GET /health', async () => {
    const r = await app.inject({ method: 'GET', url: '/health' });
    expect(r.statusCode).toBe(200);
    expect(r.json()).toEqual({ status: 'ok' });
  });

  it('GET /api/kategoriler aktif olanlari doner', async () => {
    const r = await app.inject({ method: 'GET', url: '/api/kategoriler' });
    expect(r.statusCode).toBe(200);
    const data = r.json();
    expect(data).toHaveLength(1);
    expect(data[0].slug).toBe('enerji');
    expect(data[0].ad).toBe('Enerji');
    expect(data[0].hassas).toBe(false);
    expect(data[0].hedef_cinsiyetler).toEqual([]);
    expect(data[0].hedef_yas_araliklari).toEqual([]);
  });

  it('GET /api/kategoriler/:slug/sorular sira ile gelir', async () => {
    const r = await app.inject({
      method: 'GET',
      url: '/api/kategoriler/enerji/sorular',
    });
    expect(r.statusCode).toBe(200);
    const qs = r.json();
    expect(qs).toHaveLength(2);
    expect(qs[0].seed_id).toBe('en_q1');
    expect(qs[0].metin).toBe('Yorgun musunuz?');
  });

  it('GET /api/kategoriler/:slug/sorular 404', async () => {
    const r = await app.inject({
      method: 'GET',
      url: '/api/kategoriler/yok/sorular',
    });
    expect(r.statusCode).toBe(404);
  });

  it('POST /api/oturum/gonder qr uretir ve outbox\'a yazar', async () => {
    const r = await app.inject({
      method: 'POST',
      url: '/api/oturum/gonder',
      headers: { 'content-type': 'application/json' },
      payload: {
        yas_araligi_kod: '26-35',
        cinsiyet_kod: 'M',
        kategori_slug: 'enerji',
        cevaplar: { en_q1: 'Y' },
      },
    });
    expect(r.statusCode).toBe(200);
    const data = r.json();
    expect(data.durum).toBe('kaydedildi');
    expect(data.qr_kodu).toMatch(/^[A-F0-9]{12}$/);

    const row = db.prepare('SELECT payload FROM oturum_outbox').get();
    expect(row).toBeTruthy();
    const payload = JSON.parse(row.payload);
    expect(payload.qr_kodu).toBe(data.qr_kodu);
    expect(payload.cinsiyet_kod).toBe('M');
    expect(payload.idempotency_anahtari).toBeTruthy();
  });

  it('POST /api/oturum/gonder gecersiz yas 422', async () => {
    const r = await app.inject({
      method: 'POST',
      url: '/api/oturum/gonder',
      payload: { yas_araligi_kod: 'X', cinsiyet_kod: 'M', kategori_slug: 'enerji' },
    });
    expect(r.statusCode).toBe(422);
  });

  it('GET /api/oturum/:qr Bearer secret olmadan 401', async () => {
    const r = await app.inject({ method: 'GET', url: '/api/oturum/ABCDEF123456' });
    expect(r.statusCode).toBe(401);
  });

  it('GET /api/oturum/:qr basarili sorgu', async () => {
    const submit = await app.inject({
      method: 'POST',
      url: '/api/oturum/gonder',
      payload: {
        yas_araligi_kod: '26-35',
        cinsiyet_kod: 'F',
        kategori_slug: 'enerji',
        qr_kodu: 'ABCDEF123456',
        cevaplar: {},
      },
    });
    expect(submit.statusCode).toBe(200);
    const r = await app.inject({
      method: 'GET',
      url: '/api/oturum/ABCDEF123456',
      headers: { authorization: 'Bearer test-secret' },
    });
    expect(r.statusCode).toBe(200);
    expect(r.json().bulundu).toBe(true);
  });

  it('GET /api/reklamlar/aktif aktif reklami doner', async () => {
    const r = await app.inject({ method: 'GET', url: '/api/reklamlar/aktif' });
    expect(r.statusCode).toBe(200);
    const data = r.json();
    expect(data).toHaveLength(1);
    expect(data[0].id).toBe(10);
    expect(data[0].ad).toBe('R1');
  });

  it('POST /api/reklam-gosterim outbox\'a yazar', async () => {
    const r = await app.inject({
      method: 'POST',
      url: '/api/reklam-gosterim',
      payload: {
        reklam_id: 10,
        gosterilme_tarihi: new Date().toISOString(),
        sure_ms: 1500,
      },
    });
    expect(r.statusCode).toBe(201);
    expect(r.json()).toEqual({ durum: 'kaydedildi' });
    const row = db.prepare('SELECT payload FROM reklam_gosterim_outbox').get();
    expect(row).toBeTruthy();
    const payload = JSON.parse(row.payload);
    expect(payload.reklam_id).toBe(10);
    expect(payload.idempotency_anahtari).toBeTruthy();
  });
});
