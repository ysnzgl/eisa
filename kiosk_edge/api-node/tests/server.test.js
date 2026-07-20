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

  // 1 kategori + 2 soru + 1 aktif reklam asset
  db.prepare(
    `INSERT INTO kategoriler (id, slug, ad, ikon, hassas, aktif)
     VALUES (1, 'enerji', 'Enerji', 'fa-bolt', 0, 1)`,
  ).run();
  db.prepare(
    `INSERT INTO sorular (id, kategori_id, seed_id, metin, sira, eslesme_kurallari)
     VALUES (1, 1, 'en_q1', 'Yorgun musunuz?', 1, '[]'),
            (2, 1, 'en_q2', 'Uykunuz nasil?', 2, '[]')`,
  ).run();

  db.prepare(
     `INSERT INTO house_ads (id, name, media_url, duration_seconds, type, aktif)
      VALUES ('11111111-1111-4111-8111-111111111111', 'R1', '/m1.png', 10, 'house_ad', 1)`,
    ).run();

  // 1 danisma kategorisi (OZEL_DANISMANLIK testi icin)
  db.prepare(
    `INSERT INTO danisma_kategorileri (id, slug, ad, aktif)
     VALUES (10, 'recete', 'Recete Danismanligi', 1)`,
  ).run();

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

  it('POST /api/oturum/gonder terk edilmis oturum outbox\'a yazar', async () => {
    // Abandoned sessions (tamamlandi=false) don't need backend QR.
    const r = await app.inject({
      method: 'POST',
      url: '/api/oturum/gonder',
      headers: { 'content-type': 'application/json' },
      payload: {
        yas_araligi_kod: '26-35',
        cinsiyet_kod: 'M',
        oturum_tipi: 'SIKAYET',
        kategori_slug: 'enerji',
        cevaplar: { en_q1: 'Y' },
        tamamlandi: false,
      },
    });
    expect(r.statusCode).toBe(201);
    const data = r.json();
    expect(data.durum).toBe('kaydedildi');
    expect(data.qr_kodu).toBeNull();

    const row = db.prepare('SELECT payload FROM oturum_outbox').get();
    expect(row).toBeTruthy();
    const payload = JSON.parse(row.payload);
    expect(payload.cinsiyet_kod).toBe('M');
    expect(payload.idempotency_anahtari).toBeTruthy();
    expect(payload.oturum_tipi).toBe('SIKAYET');
  });

  it('POST /api/oturum/gonder OZEL_DANISMANLIK gecersiz slug 422 doner', async () => {
    const r = await app.inject({
      method: 'POST',
      url: '/api/oturum/gonder',
      payload: {
        yas_araligi_kod: '26-35',
        cinsiyet_kod: 'M',
        oturum_tipi: 'OZEL_DANISMANLIK',
        danisma_kategorisi_slug: 'yok',
        tamamlandi: false,
      },
    });
    expect(r.statusCode).toBe(422);
  });

  it('POST /api/oturum/gonder OZEL_DANISMANLIK cevap icerirse 422 doner', async () => {
    const r = await app.inject({
      method: 'POST',
      url: '/api/oturum/gonder',
      payload: {
        yas_araligi_kod: '26-35',
        cinsiyet_kod: 'M',
        oturum_tipi: 'OZEL_DANISMANLIK',
        danisma_kategorisi_slug: 'recete',
        cevaplar: { '1': 'Y' },  // cevap olmamalı
        tamamlandi: false,
      },
    });
    expect(r.statusCode).toBe(422);
  });

  it('POST /api/oturum/gonder OZEL_DANISMANLIK terk edilmis outbox a yazar', async () => {
    const r = await app.inject({
      method: 'POST',
      url: '/api/oturum/gonder',
      payload: {
        yas_araligi_kod: '26-35',
        cinsiyet_kod: 'F',
        oturum_tipi: 'OZEL_DANISMANLIK',
        danisma_kategorisi_slug: 'recete',
        tamamlandi: false,
      },
    });
    expect(r.statusCode).toBe(201);
    const payload = JSON.parse(db.prepare('SELECT payload FROM oturum_outbox').get().payload);
    expect(payload.oturum_tipi).toBe('OZEL_DANISMANLIK');
    expect(payload.danisma_kategorisi_id).toBe(10);  // lokal katalogdan cozuldu
  });

  it('POST /api/oturum/gonder tamamlandi=true backend yoksa 503 doner', async () => {
    // Completed sessions require backend; fakeSettings has centralApiBase but
    // no kiosk_app_key in kiosk_meta → hasAppKeyCredentials() = false → 503
    const r = await app.inject({
      method: 'POST',
      url: '/api/oturum/gonder',
      headers: { 'content-type': 'application/json' },
      payload: {
        yas_araligi_kod: '26-35',
        cinsiyet_kod: 'M',
        kategori_slug: 'enerji',
        cevaplar: {},
        tamamlandi: true,
      },
    });
    expect(r.statusCode).toBe(503);
    expect(r.json().code).toBe('backend_unavailable');
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
    const r = await app.inject({ method: 'GET', url: '/api/oturum/ABCDEF12' });
    expect(r.statusCode).toBe(401);
  });

  it('GET /api/oturum/:qr basarili sorgu', async () => {
    // Insert a completed session directly into the outbox (simulates backend having returned a QR)
    const fakeQr = 'AB12CD34';
    const fakeIdem = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';
    const payload = {
      idempotency_anahtari: fakeIdem,
      qr_kodu: fakeQr,
      yas_araligi_kod: '26-35',
      cinsiyet_kod: 'F',
      kategori_slug: 'enerji',
      tamamlandi: true,
    };
    db.prepare(
      'INSERT INTO oturum_outbox (idempotency_anahtari, payload, gonderilme_tarihi) VALUES (?, ?, ?)'
    ).run(fakeIdem, JSON.stringify(payload), new Date().toISOString());

    const r = await app.inject({
      method: 'GET',
      url: `/api/oturum/${fakeQr}`,
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
    expect(data[0].id).toBe('11111111-1111-4111-8111-111111111111');
    expect(data[0].name).toBe('R1');
  });

  it('POST /api/reklam-gosterim outbox\'a yazar', async () => {
    const r = await app.inject({
      method: 'POST',
      url: '/api/reklam-gosterim',
      payload: {
        asset_id: '11111111-1111-4111-8111-111111111111',
        asset_type: 'house_ad',
        played_at: new Date().toISOString(),
        duration_played: 2,
      },
    });
    expect(r.statusCode).toBe(201);
    expect(r.json()).toEqual({ durum: 'kaydedildi' });
    const row = db.prepare('SELECT payload FROM reklam_gosterim_outbox').get();
    expect(row).toBeTruthy();
    const payload = JSON.parse(row.payload);
    expect(payload.asset_id).toBe('11111111-1111-4111-8111-111111111111');
    expect(payload.asset_type).toBe('house_ad');
  });
});
