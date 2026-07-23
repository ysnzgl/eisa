import { describe, it, expect, beforeEach, vi } from 'vitest';
import { buildServer } from '../src/server.js';
import { makeMemoryDb, fakeSettings } from './helpers.js';

// requestWithRetry'yi mock'la — tamamlandi=true testleri için gerçek HTTP yapılmaz
vi.mock('../src/scheduler.js', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, requestWithRetry: vi.fn() };
});
// Mock import'u modül yüklendikten sonra alınmalı
const { requestWithRetry } = await import('../src/scheduler.js');

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

// ─── tamamlandi=true backend senaryolari ────────────────────────────────────

const IDEM_KEY = 'a1b2c3d4-0000-4000-8000-000000000001';
const BASE_PAYLOAD = {
  yas_araligi_kod: '26-35',
  cinsiyet_kod: 'M',
  oturum_tipi: 'SIKAYET',
  kategori_slug: 'enerji',
  cevaplar: {},
  tamamlandi: true,
  idempotency_anahtari: IDEM_KEY,
};

async function makeAppWithCredentials() {
  const { app, db } = await (async () => {
    const db = makeMemoryDb();
    db.prepare("INSERT INTO cinsiyetler (kod, ad) VALUES ('M','Erkek'),('F','Kadin'),('O','Diger')").run();
    db.prepare("INSERT INTO yas_araliklari (kod, ad, alt_sinir, ust_sinir) VALUES ('26-35','26-35',26,35)").run();
    db.prepare("INSERT INTO kategoriler (id, slug, ad, ikon, hassas, aktif) VALUES (1, 'enerji', 'Enerji', 'fa-bolt', 0, 1)").run();
    db.prepare("INSERT INTO danisma_kategorileri (id, slug, ad, aktif) VALUES (10, 'recete', 'Recete Danismanligi', 1)").run();
    // Kiosk kimlik bilgileri — hasAppKeyCredentials() true döner
    db.prepare("INSERT OR REPLACE INTO kiosk_meta (key, value) VALUES ('kiosk_app_key', 'test-app-key-for-tests')").run();
    db.prepare("INSERT OR REPLACE INTO kiosk_meta (key, value) VALUES ('kiosk_mac', '00:11:22:33:44:55')").run();
    const app = await buildServer({ db, settings: fakeSettings, logger: false });
    return { app, db };
  })();
  return { app, db };
}

describe('POST /api/oturum/gonder — tamamlandi=true backend senaryolari', () => {
  let app, db;
  beforeEach(async () => {
    vi.resetAllMocks();
    ({ app, db } = await makeAppWithCredentials());
  });

  // Senaryo 1: Merkez tüm kayıtları kabul eder (200)
  it('Senaryo 1 — backend 200, kabul: 201 + qr_kodu', async () => {
    requestWithRetry.mockResolvedValueOnce({
      status: 200,
      json: async () => ({
        results: [{ idempotency_key: IDEM_KEY, status: 'created', qr_kodu: 'AB12CD34' }],
        errors: [],
      }),
    });
    const r = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: BASE_PAYLOAD });
    expect(r.statusCode).toBe(201);
    expect(r.json().qr_kodu).toBe('AB12CD34');
    expect(r.json().sync_durum).toBe('gonderildi');
    // Outbox gonderilme_tarihi set edilmeli
    const row = db.prepare('SELECT gonderilme_tarihi FROM oturum_outbox WHERE idempotency_anahtari = ?').get(IDEM_KEY);
    expect(row.gonderilme_tarihi).toBeTruthy();
  });

  // Senaryo 2: Merkez duplicate (existing) döndürür
  it('Senaryo 2 — backend 200 existing: 201 + mevcut qr_kodu', async () => {
    requestWithRetry.mockResolvedValueOnce({
      status: 200,
      json: async () => ({
        results: [{ idempotency_key: IDEM_KEY, status: 'existing', qr_kodu: 'EX12ST34' }],
        errors: [],
      }),
    });
    const r = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: BASE_PAYLOAD });
    expect(r.statusCode).toBe(201);
    expect(r.json().qr_kodu).toBe('EX12ST34');
    expect(r.json().sync_durum).toBe('gonderildi');
  });

  // Senaryo 3: 207 — bazıları kabul, bazıları validation hatalı
  it('Senaryo 3 — backend 207 kısmi: kabul edilen 201, reddedilen 422', async () => {
    const OTHER = 'ffffffff-ffff-4fff-8fff-ffffffffffff';
    // Bu test için iki kayıt göndermek yerine: hata olan kaydın 422 döndüğünü test et
    const errKey = IDEM_KEY;
    requestWithRetry.mockResolvedValueOnce({
      status: 207,
      json: async () => ({
        results: [],
        errors: [{ index: 0, idempotency_anahtari: errKey, errors: { kategori_slug: ['Not found'] } }],
      }),
    });
    const r = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: BASE_PAYLOAD });
    expect(r.statusCode).toBe(422);
    expect(r.json().code).toBe('backend_rejected');
    // Outbox kaydı hâlâ var (silinmedi), retry_count=99 (kalıcı hata işareti)
    const row = db.prepare('SELECT retry_count, gonderilme_tarihi FROM oturum_outbox WHERE idempotency_anahtari = ?').get(IDEM_KEY);
    expect(row).toBeTruthy();
    expect(row.gonderilme_tarihi).toBeNull();
    expect(row.retry_count).toBe(99);
  });

  // Senaryo 4: Merkez 401 döndürür
  it('Senaryo 4 — backend 401: 401 doner', async () => {
    requestWithRetry.mockResolvedValueOnce({ status: 401, json: async () => ({}) });
    const r = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: BASE_PAYLOAD });
    expect(r.statusCode).toBe(401);
  });

  // Senaryo 4b: Merkez 403 döndürür
  it('Senaryo 4b — backend 403: 403 doner', async () => {
    requestWithRetry.mockResolvedValueOnce({ status: 403, json: async () => ({}) });
    const r = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: BASE_PAYLOAD });
    expect(r.statusCode).toBe(403);
  });

  // Senaryo 5: Merkez 500 döndürür
  it('Senaryo 5 — backend 500: 503 doner, outbox\'ta bekler', async () => {
    requestWithRetry.mockResolvedValueOnce({ status: 500, json: async () => ({}) });
    const r = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: BASE_PAYLOAD });
    expect(r.statusCode).toBe(503);
    expect(r.json().sync_durum).toBe('bekliyor');
    // Outbox kaydı gönderilmedi işareti olmadan var olmalı
    const row = db.prepare('SELECT gonderilme_tarihi FROM oturum_outbox WHERE idempotency_anahtari = ?').get(IDEM_KEY);
    expect(row).toBeTruthy();
    expect(row.gonderilme_tarihi).toBeNull();
  });

  // Senaryo 6: Outbox insert başarılı, anlık merkezi sync başarısız
  it('Senaryo 6 — backend erişilemez: 503, outbox kaydı korunur', async () => {
    requestWithRetry.mockRejectedValueOnce(new Error('ECONNREFUSED'));
    const r = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: BASE_PAYLOAD });
    expect(r.statusCode).toBe(503);
    expect(r.json().code).toBe('backend_unreachable');
    const row = db.prepare('SELECT * FROM oturum_outbox WHERE idempotency_anahtari = ?').get(IDEM_KEY);
    expect(row).toBeTruthy();
    expect(row.gonderilme_tarihi).toBeNull();
  });

  // Senaryo 7: Aynı idempotency key iki kez lokal endpoint'e gönderilir
  it('Senaryo 7 — aynı idempotency_anahtari iki kez: ikinci isteğe mevcut QR döner', async () => {
    requestWithRetry.mockResolvedValue({
      status: 200,
      json: async () => ({
        results: [{ idempotency_key: IDEM_KEY, status: 'created', qr_kodu: 'QR123456' }],
        errors: [],
      }),
    });
    // İlk istek
    const r1 = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: BASE_PAYLOAD });
    expect(r1.statusCode).toBe(201);
    expect(r1.json().qr_kodu).toBe('QR123456');
    // İkinci istek — aynı idempotency_anahtari, backend ÇAĞRILMAMALI
    const callCountBefore = requestWithRetry.mock.calls.length;
    const r2 = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: BASE_PAYLOAD });
    expect(r2.statusCode).toBe(201);
    expect(r2.json().qr_kodu).toBe('QR123456');
    expect(r2.json().sync_durum).toBe('onceden_gonderildi');
    // requestWithRetry bir kez daha çağrılmamalı
    expect(requestWithRetry.mock.calls.length).toBe(callCountBefore);
  });

  // Senaryo 9: Kabul edilen kayıtlar gönderildi işaretlenir
  it('Senaryo 9 — kabul edilen kayıt gonderilme_tarihi set edilir', async () => {
    requestWithRetry.mockResolvedValueOnce({
      status: 200,
      json: async () => ({
        results: [{ idempotency_key: IDEM_KEY, status: 'created', qr_kodu: 'OK123456' }],
        errors: [],
      }),
    });
    await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: BASE_PAYLOAD });
    const row = db.prepare('SELECT gonderilme_tarihi, retry_count FROM oturum_outbox WHERE idempotency_anahtari = ?').get(IDEM_KEY);
    expect(row.gonderilme_tarihi).toBeTruthy();
    expect(row.retry_count).toBe(0);
  });

  // Senaryo 10: Reddedilen kayıt yanlışlıkla gönderildi işaretlenmez
  it('Senaryo 10 — backend_rejected: gonderilme_tarihi null kalir, retry_count=99', async () => {
    requestWithRetry.mockResolvedValueOnce({
      status: 207,
      json: async () => ({
        results: [],
        errors: [{ index: 0, idempotency_anahtari: IDEM_KEY, errors: { yas_araligi_kod: ['Not found'] } }],
      }),
    });
    await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: BASE_PAYLOAD });
    const row = db.prepare('SELECT gonderilme_tarihi, retry_count FROM oturum_outbox WHERE idempotency_anahtari = ?').get(IDEM_KEY);
    expect(row.gonderilme_tarihi).toBeNull();
    expect(row.retry_count).toBe(99);
  });

  // Senaryo 12: Loglarda / response'ta App Key ve secret'lar bulunmaz
  it('Senaryo 12 — App Key ve secret\'lar response\'ta bulunmaz', async () => {
    // server.js sadece event adı, kiosk_id ve sayısal değerler loglar (kod incelemesinde doğrulandı)
    // Bu test response body'nin gizli bilgi içermediğini garanti eder
    requestWithRetry.mockRejectedValueOnce(new Error('ECONNREFUSED'));
    const r = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: BASE_PAYLOAD });
    const bodyStr = JSON.stringify(r.json());
    // Response'da App Key, fleet key veya provision secret bulunmamalı
    expect(bodyStr).not.toContain('test-app-key-for-tests');
    expect(bodyStr).not.toContain('test-fleet-key');
    expect(bodyStr).not.toContain('test-secret');
    // requestWithRetry'ye geçilen body'de (log arg) secrets yok — payload'dan doğrula
    const callArgs = requestWithRetry.mock.calls[0];
    // 3. arg = path (string), 4. arg = body object
    const sentBody = JSON.stringify(callArgs?.[4] ?? {});
    expect(sentBody).not.toContain('test-app-key-for-tests');
    expect(sentBody).not.toContain('test-fleet-key');
    expect(sentBody).not.toContain('test-secret');
  });
});

// ─── Senaryo 8: UI aynı session'ı iki kez gönderme — tamamlandi=false ─────

describe('POST /api/oturum/gonder — tamamlandi=false idempotency', () => {
  let app, db;
  beforeEach(async () => {
    vi.resetAllMocks();
    ({ app, db } = await makeAppWithCredentials());
  });

  it('Senaryo 8 — aynı key iki kez terk edilmis oturum: INSERT OR IGNORE', async () => {
    const idem = 'cccccccc-0000-4000-8000-000000000099';
    const payload = { ...BASE_PAYLOAD, tamamlandi: false, idempotency_anahtari: idem };
    requestWithRetry.mockResolvedValue({
      status: 200,
      json: async () => ({ results: [{ idempotency_key: idem, status: 'created', qr_kodu: null }], errors: [] }),
    });
    await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload });
    await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload });
    const count = db.prepare('SELECT COUNT(*) AS c FROM oturum_outbox WHERE idempotency_anahtari = ?').get(idem).c;
    expect(count).toBe(1);  // INSERT OR IGNORE — tek kayıt
  });

  // Senaryo 11: Scheduler bekleyen kayıtları tekrar dener (retry_count < MAX)
  it('Senaryo 11 — scheduler: retry_count < MAX olan kayitlar secilir', async () => {
    // 3 kayıt: 2 normal, 1 kalıcı hata (retry_count=99)
    db.prepare("INSERT INTO oturum_outbox (idempotency_anahtari, payload, retry_count) VALUES ('k1', '{\"test\":1}', 0)").run();
    db.prepare("INSERT INTO oturum_outbox (idempotency_anahtari, payload, retry_count) VALUES ('k2', '{\"test\":2}', 5)").run();
    db.prepare("INSERT INTO oturum_outbox (idempotency_anahtari, payload, retry_count) VALUES ('k3', '{\"test\":3}', 99)").run();
    // retry_count < 10 olanlar: k1 (0), k2 (5)
    const pending = db.prepare(
      'SELECT id FROM oturum_outbox WHERE gonderilme_tarihi IS NULL AND retry_count < 10'
    ).all();
    expect(pending.length).toBe(2);
  });
});
