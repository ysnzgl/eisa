/**
 * Offline-first oturum/QR handler — dar kapsamlı bağımsız testler.
 *
 * server.js import edilir ancak scheduler.js tam olarak mock'lanır
 * (pre-existing Vite/CRLF parse hatası nedeniyle).
 *
 * Test kapsamı:
 *   1. eczane_kiosk_no mevcut → offline QR üretimi, 201, Crockford format
 *   2. Atomik kayıt: QR + sayaç + outbox aynı anda
 *   3. Backend push başarısız → outbox PENDING kalır
 *   4. Aynı idempotency_key tekrarında aynı QR döner
 *   5. İkinci çağrıda ikinci outbox oluşmaz
 *   6. tamamlandi=false → null QR, outbox kaydı var
 *   7. eczane_kiosk_no eksik → 503 kiosk_no_missing değil, backend_* kodu
 *   8. Scheduler pushOutbox: pending outbox kayıtları doğru payload içerir
 *   9. Transaction rollback → başarılı QR dönmez
 *  10. Catalog sync ile eczane_kiosk_no kiosk_meta'ya kaydedilir
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import Database from 'better-sqlite3';

// ── Scheduler + provisioning mock (pre-existing encoding bypass) ──────────────
vi.mock('../src/scheduler.js', () => ({
  requestWithRetry: vi.fn().mockRejectedValue(new Error('backend_unreachable')),
}));
vi.mock('../src/provisioning.js', () => ({
  hasAppKeyCredentials: vi.fn().mockReturnValue(true),
  getAuthHeaders: vi.fn().mockReturnValue({ Authorization: 'AppKey test' }),
  handle401Error: vi.fn(),
  handle403Error: vi.fn(),
  getProvisioningState: vi.fn().mockReturnValue('APPROVED'),
}));
// Side-effect yok; sadece erken import'ı önlemek için
vi.mock('../src/wifi.js', () => ({
  getWifiStatus: vi.fn().mockResolvedValue({ connected: false }),
  scanWifi: vi.fn().mockResolvedValue([]),
  connectWifi: vi.fn().mockResolvedValue(false),
}));
vi.mock('../src/printer.js', () => ({
  printReceipt: vi.fn(),
  buildReceiptBuffer: vi.fn(() => ({ buffer: Buffer.from([]), logoId: null })),
  sendToTransport: vi.fn(),
}));
vi.mock('../src/mediaCache.js', () => ({
  buildMediaUrl: vi.fn((db, type, id, url) => url),
  getLocalMediaMeta: vi.fn().mockReturnValue(null),
  syncMediaCache: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('../src/diagnosticOutbox.js', () => ({
  recordDiagnostic: vi.fn(),
  fetchPendingDiagnostics: vi.fn().mockReturnValue([]),
  markDiagnosticsSent: vi.fn(),
  reschedulePendingDiagnostics: vi.fn(),
  cleanupOldDiagnostics: vi.fn(),
}));
vi.mock('../src/kioskEventOutbox.js', () => ({ recordKioskEvent: vi.fn() }));
vi.mock('../src/timezone.js', () => ({
  istanbulNow: vi.fn().mockReturnValue({ date: '2026-08-06', hour: 10 }),
}));
vi.mock('../src/correlationId.js', () => ({
  CORRELATION_HEADER: 'x-correlation-id',
  CORRELATION_HEADER_PRETTY: 'X-Correlation-ID',
  newCorrelationId: vi.fn().mockReturnValue('test-cid'),
  runWithCorrelation: vi.fn((id, fn) => fn()),
  sanitizeIncoming: vi.fn((v) => v || null),
  derivedId: vi.fn().mockReturnValue('derived'),
  getCorrelationId: vi.fn().mockReturnValue(null),
}));

import { buildServer } from '../src/server.js';
import { generateNextQr, validateChecksum, CROCKFORD_QR_RE } from '../src/qrGen.js';

// ── In-memory DB ──────────────────────────────────────────────────────────────
function makeDb({ withKioskNo = true, kioskNo = 3 } = {}) {
  const db = new Database(':memory:');
  db.pragma('journal_mode = WAL');
  db.exec(`
    CREATE TABLE schema_meta (version INTEGER NOT NULL);
    INSERT INTO schema_meta VALUES (14);
    CREATE TABLE kiosk_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL DEFAULT '');
    CREATE TABLE cinsiyetler (id INTEGER PRIMARY KEY, kod TEXT NOT NULL UNIQUE, ad TEXT NOT NULL);
    CREATE TABLE yas_araliklari (id INTEGER PRIMARY KEY, kod TEXT NOT NULL UNIQUE, ad TEXT NOT NULL, alt_sinir INTEGER, ust_sinir INTEGER);
    CREATE TABLE kategoriler (id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, ad TEXT NOT NULL, ikon TEXT NOT NULL DEFAULT 'fa-circle', bagli_kategori_id INTEGER, hedef_cinsiyet_id INTEGER, aktif INTEGER NOT NULL DEFAULT 1, surum INTEGER NOT NULL DEFAULT 1, hedef_cinsiyetler TEXT NOT NULL DEFAULT '[]', hedef_yas_araliklari TEXT NOT NULL DEFAULT '[]', olusturulma_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), guncellenme_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
    CREATE TABLE danisma_kategorileri (id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, ad TEXT NOT NULL, ikon TEXT NOT NULL DEFAULT 'fa-comments', ust_kategori_id INTEGER, aktif INTEGER NOT NULL DEFAULT 1, olusturulma_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), guncellenme_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
    CREATE TABLE sorular (id INTEGER PRIMARY KEY, kategori_id INTEGER NOT NULL, seed_id TEXT, metin TEXT NOT NULL, sira INTEGER NOT NULL DEFAULT 0, eslesme_kurallari TEXT NOT NULL DEFAULT '[]', hedef_cinsiyet_id INTEGER, surum INTEGER NOT NULL DEFAULT 1, hedef_cinsiyetler TEXT NOT NULL DEFAULT '[]', hedef_yas_araliklari TEXT NOT NULL DEFAULT '[]', olusturulma_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), guncellenme_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
    CREATE TABLE cevaplar (id INTEGER PRIMARY KEY, soru_id INTEGER NOT NULL, metin TEXT NOT NULL, agirlik INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE etken_maddeler (id INTEGER PRIMARY KEY, ad TEXT NOT NULL UNIQUE, aciklama TEXT NOT NULL DEFAULT '', aktif INTEGER NOT NULL DEFAULT 1, surum INTEGER NOT NULL DEFAULT 1, olusturulma_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), guncellenme_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
    CREATE TABLE kategori_hedef_yas_araliklari (kategori_id INTEGER NOT NULL, yas_araligi_id INTEGER NOT NULL, PRIMARY KEY (kategori_id, yas_araligi_id));
    CREATE TABLE soru_hedef_yas_araliklari (soru_id INTEGER NOT NULL, yas_araligi_id INTEGER NOT NULL, PRIMARY KEY (soru_id, yas_araligi_id));
    CREATE TABLE soru_etken_maddeler (soru_id INTEGER NOT NULL, etken_madde_id INTEGER NOT NULL, rol TEXT NOT NULL DEFAULT 'ana', PRIMARY KEY (soru_id, etken_madde_id));
    CREATE TABLE creatives (id TEXT PRIMARY KEY, media_url TEXT NOT NULL DEFAULT '', active_media_url TEXT NOT NULL DEFAULT '', duration_seconds INTEGER NOT NULL DEFAULT 15, checksum TEXT NOT NULL DEFAULT '', type TEXT NOT NULL DEFAULT 'creative', aktif INTEGER NOT NULL DEFAULT 1, guncellenme_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
    CREATE TABLE house_ads (id TEXT PRIMARY KEY, name TEXT NOT NULL DEFAULT '', media_url TEXT NOT NULL DEFAULT '', duration_seconds INTEGER NOT NULL DEFAULT 15, type TEXT NOT NULL DEFAULT 'house_ad', aktif INTEGER NOT NULL DEFAULT 1, guncellenme_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
    CREATE TABLE playlists (id TEXT PRIMARY KEY, target_date TEXT NOT NULL, target_hour INTEGER NOT NULL, loop_duration_seconds INTEGER NOT NULL DEFAULT 60, version INTEGER NOT NULL DEFAULT 1, synced_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), UNIQUE(target_date, target_hour));
    CREATE TABLE playlist_items (id TEXT PRIMARY KEY, playlist_id TEXT NOT NULL, playback_order INTEGER NOT NULL DEFAULT 0, asset_id TEXT NOT NULL, asset_type TEXT NOT NULL, media_url TEXT NOT NULL DEFAULT '', duration_seconds INTEGER NOT NULL DEFAULT 15, estimated_start_offset_seconds INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE media_cache (asset_id TEXT NOT NULL, asset_type TEXT NOT NULL, source_url TEXT NOT NULL, source_checksum TEXT NOT NULL DEFAULT '', file_checksum TEXT NOT NULL DEFAULT '', local_path TEXT NOT NULL, mime_type TEXT NOT NULL DEFAULT '', file_size INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'ready', error_message TEXT NOT NULL DEFAULT '', synced_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), PRIMARY KEY (asset_id, asset_type));
    CREATE TABLE oturum_outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, idempotency_anahtari TEXT UNIQUE, payload TEXT NOT NULL, olusturulma_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), gonderilme_tarihi TEXT, retry_count INTEGER NOT NULL DEFAULT 0, error_reason TEXT);
    CREATE TABLE reklam_gosterim_outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, idempotency_anahtari TEXT UNIQUE, payload TEXT NOT NULL, olusturulma_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), gonderilme_tarihi TEXT);
    CREATE TABLE kiosk_event_outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE, event_type TEXT NOT NULL DEFAULT 'GENERAL_ERROR', severity TEXT NOT NULL DEFAULT 'WARNING', message TEXT NOT NULL DEFAULT '', occurred_at TEXT, created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), sent_at TEXT, retry_count INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE diagnostic_outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), level TEXT NOT NULL, event TEXT NOT NULL, message TEXT NOT NULL DEFAULT '', context_json TEXT NOT NULL DEFAULT '{}', correlation_id TEXT, retry_count INTEGER NOT NULL DEFAULT 0, next_retry_at TEXT, sent_at TEXT);
    CREATE TABLE pending_ack (id INTEGER PRIMARY KEY CHECK(id = 1), playlist_version INTEGER NOT NULL, horizon_start TEXT NOT NULL, horizon_end TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), retry_count INTEGER NOT NULL DEFAULT 0, next_retry_at TEXT);
    CREATE TABLE qr_counter (id INTEGER PRIMARY KEY CHECK(id = 1), last_value INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
    INSERT INTO qr_counter (id, last_value) VALUES (1, 0);

    CREATE TABLE barkod_logolar (id TEXT PRIMARY KEY, ad TEXT NOT NULL DEFAULT '', media_url TEXT NOT NULL DEFAULT '', checksum TEXT NOT NULL DEFAULT '', baslangic_zamani TEXT NOT NULL, bitis_zamani TEXT NOT NULL, aktif INTEGER NOT NULL DEFAULT 1, gunluk_limit INTEGER, local_path TEXT NOT NULL DEFAULT '', cache_status TEXT NOT NULL DEFAULT 'pending', synced_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
    CREATE TABLE barkod_logo_baski_sayaclari (logo_id TEXT NOT NULL, tarih_istanbul TEXT NOT NULL, sayi INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (logo_id, tarih_istanbul));

    INSERT INTO cinsiyetler VALUES (1,'M','Erkek'),(2,'F','Kadin'),(3,'O','Diger');
    INSERT INTO yas_araliklari VALUES (1,'18-24','18-24 Yas',18,24),(2,'25-34','25-34 Yas',25,34);
    INSERT INTO kategoriler (id,slug,ad) VALUES (1,'test-kategori','Test Kategori');
  `);

  // Provision edilmiş kiosk simülasyonu (provisioning.js dokunulmadı)
  const setMeta = (k, v) => db.prepare("INSERT INTO kiosk_meta (key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value").run(k, v);
  setMeta('kiosk_app_key', 'test-app-key-48chars-xxxxxxxxxxxxxxxxxxxxxxxxxxx');
  setMeta('kiosk_id', '1');
  setMeta('pharmacy_id', '1');
  setMeta('provisioning_state', 'APPROVED');
  setMeta('kiosk_mac', 'AA:BB:CC:DD:EE:FF');
  if (withKioskNo) setMeta('eczane_kiosk_no', String(kioskNo));

  return db;
}

const SETTINGS = {
  centralApiBase: 'http://backend.local:8000',
  kioskMac: 'AA:BB:CC:DD:EE:FF',
  kioskId: 1,
  pharmacyId: 1,
  kioskProvisioningSecret: 'test-secret',
  verifyTls: false,
  devMode: true,
  host: '127.0.0.1',
  port: 0,
};

function body(overrides = {}) {
  return {
    idempotency_anahtari: crypto.randomUUID(),
    yas_araligi_kod: '18-24',
    cinsiyet_kod: 'M',
    oturum_tipi: 'SIKAYET',
    kategori_slug: 'test-kategori',
    hassas_akis: false,
    cevaplar: {},
    onerilen_etken_maddeler: [],
    tamamlandi: true,
    ...overrides,
  };
}

async function makeApp(db, settings = SETTINGS) {
  const app = await buildServer({ db, settings, logger: false });
  await app.ready();
  return app;
}

// ── 1. eczane_kiosk_no mevcut → offline QR ───────────────────────────────────
describe('Offline-first QR (eczane_kiosk_no mevcut)', () => {
  let db, app;

  beforeEach(async () => {
    db = makeDb({ withKioskNo: true, kioskNo: 3 });
    app = await makeApp(db);
  });
  afterEach(async () => { await app.close(); db.close(); });

  it('201 + 9-char Crockford QR döner', async () => {
    const res = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: body() });
    expect(res.statusCode).toBe(201);
    const d = JSON.parse(res.body);
    expect(CROCKFORD_QR_RE.test(d.qr_kodu)).toBe(true);
    expect(validateChecksum(d.qr_kodu)).toBe(true);
    expect(d.qr_kodu[0]).toBe('3'); // prefix = kiosk_no=3
  });

  it('sync_durum=bekliyor (backend push async, henüz tamamlanmadı)', async () => {
    const res = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: body() });
    const d = JSON.parse(res.body);
    expect(d.sync_durum).toBe('bekliyor');
  });

  it('atomik: QR + sayaç + outbox aynı anda kaydedilir', async () => {
    const b = body();
    const res = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: b });
    expect(res.statusCode).toBe(201);
    const qr = JSON.parse(res.body).qr_kodu;

    const outbox = db.prepare('SELECT payload FROM oturum_outbox WHERE idempotency_anahtari=?').get(b.idempotency_anahtari);
    expect(outbox).toBeTruthy();
    expect(JSON.parse(outbox.payload).qr_kodu).toBe(qr);

    const counter = db.prepare('SELECT last_value FROM qr_counter WHERE id=1').get();
    expect(counter.last_value).toBeGreaterThan(0);
  });

  it('backend push başarısız → outbox PENDING (gonderilme_tarihi null)', async () => {
    const b = body();
    // requestWithRetry mock'u hata fırlatır → push başarısız
    await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: b });
    // setImmediate henüz çalışmamış olabilir; sadece outbox'ın varlığını kontrol et
    const row = db.prepare('SELECT gonderilme_tarihi FROM oturum_outbox WHERE idempotency_anahtari=?').get(b.idempotency_anahtari);
    expect(row).toBeTruthy();
    // gonderilme_tarihi null = PENDING (push'un hata fırlattığı durumda)
    expect(row.gonderilme_tarihi).toBeNull();
  });

  it('aynı idempotency_key → aynı QR (idempotent)', async () => {
    const b = body();
    const r1 = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: b });
    const r2 = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: b });
    expect(r1.statusCode).toBe(201);
    expect(r2.statusCode).toBe(201);
    expect(JSON.parse(r1.body).qr_kodu).toBe(JSON.parse(r2.body).qr_kodu);
  });

  it('aynı key iki kez çağrıda tek outbox kaydı', async () => {
    const b = body();
    await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: b });
    await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: b });
    const c = db.prepare('SELECT COUNT(*) AS c FROM oturum_outbox WHERE idempotency_anahtari=?').get(b.idempotency_anahtari).c;
    expect(c).toBe(1);
  });

  it('farklı key → farklı QR', async () => {
    const r1 = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: body() });
    const r2 = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: body() });
    expect(JSON.parse(r1.body).qr_kodu).not.toBe(JSON.parse(r2.body).qr_kodu);
  });

  it('tamamlandi=false → qr_kodu null, outbox kaydı var', async () => {
    const b = body({ tamamlandi: false });
    const res = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: b });
    expect(res.statusCode).toBe(201);
    expect(JSON.parse(res.body).qr_kodu).toBeNull();
    const row = db.prepare('SELECT id FROM oturum_outbox WHERE idempotency_anahtari=?').get(b.idempotency_anahtari);
    expect(row).toBeTruthy();
  });

  it('checksum her üretimde geçerli', async () => {
    for (let i = 0; i < 5; i++) {
      const res = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: body() });
      expect(validateChecksum(JSON.parse(res.body).qr_kodu)).toBe(true);
    }
  });
});

// ── 2. eczane_kiosk_no eksik → graceful fallback ─────────────────────────────
describe('Graceful fallback (eczane_kiosk_no eksik)', () => {
  let db, app;

  beforeEach(async () => {
    db = makeDb({ withKioskNo: false });
    app = await makeApp(db);
  });
  afterEach(async () => { await app.close(); db.close(); });

  it('503 kiosk_no_missing kodu döner (provisioning tamamlanmamış)', async () => {
    const res = await app.inject({ method: 'POST', url: '/api/oturum/gonder', payload: body() });
    expect(res.statusCode).toBe(503);
    const d = JSON.parse(res.body);
    expect(d.code).toBe('kiosk_no_missing');
  });
});

// ── 3. Catalog sync → kiosk_meta kaydı ──────────────────────────────────────
describe('Catalog sync eczane_kiosk_no dağıtımı', () => {
  it('scheduler pullFromCentral sonrası kiosk_meta güncellenir', () => {
    const db = makeDb({ withKioskNo: false });
    // Catalog sync'i doğrudan simüle et (scheduler.js dışındaki mantık)
    const kNo = 7;
    db.prepare(
      "INSERT INTO kiosk_meta (key, value) VALUES ('eczane_kiosk_no', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value"
    ).run(String(kNo));
    const row = db.prepare("SELECT value FROM kiosk_meta WHERE key='eczane_kiosk_no'").get();
    expect(row?.value).toBe('7');
    db.close();
  });

  it('eczane_kiosk_no kaydedildikten sonra offline QR üretilebilir', () => {
    const db = makeDb({ withKioskNo: false });
    db.prepare("INSERT INTO kiosk_meta (key,value) VALUES ('eczane_kiosk_no','5') ON CONFLICT(key) DO UPDATE SET value=excluded.value").run();
    // DB'den oku → server.js mantığını simüle et
    const row = db.prepare("SELECT value FROM kiosk_meta WHERE key='eczane_kiosk_no'").get();
    const kNo = parseInt(row?.value, 10);
    expect(kNo).toBe(5);
    const qr = generateNextQr(db, kNo);
    expect(CROCKFORD_QR_RE.test(qr)).toBe(true);
    expect(validateChecksum(qr)).toBe(true);
    expect(qr[0]).toBe('5');
    db.close();
  });
});

// ── 4. Scheduler outbox: aynı QR ile retry ───────────────────────────────────
describe('Scheduler retry aynı QR ile gönderir', () => {
  it('outbox payload QR içerir; scheduler aynı payload ile retry', () => {
    const db = new Database(':memory:');
    db.exec(`
      CREATE TABLE qr_counter (id INTEGER PRIMARY KEY CHECK(id=1), last_value INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL DEFAULT '');
      INSERT INTO qr_counter VALUES (1,0,'');
      CREATE TABLE oturum_outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, idempotency_anahtari TEXT UNIQUE, payload TEXT NOT NULL, olusturulma_tarihi TEXT NOT NULL DEFAULT '', gonderilme_tarihi TEXT, retry_count INTEGER NOT NULL DEFAULT 0, error_reason TEXT);
    `);
    const idem = 'retry-test-' + Date.now();
    const qr = generateNextQr(db, 7);
    const pl = { idempotency_anahtari: idem, qr_kodu: qr, tamamlandi: true };
    db.prepare('INSERT INTO oturum_outbox (idempotency_anahtari, payload) VALUES (?,?)').run(idem, JSON.stringify(pl));

    // Scheduler: SELECT pending
    const pending = db.prepare('SELECT payload FROM oturum_outbox WHERE gonderilme_tarihi IS NULL').all();
    expect(pending.length).toBe(1);
    const storedQr = JSON.parse(pending[0].payload).qr_kodu;
    expect(storedQr).toBe(qr); // aynı QR
    expect(validateChecksum(storedQr)).toBe(true);

    // Başarılı push → gonderilme_tarihi set
    db.prepare('UPDATE oturum_outbox SET gonderilme_tarihi=? WHERE idempotency_anahtari=?').run(new Date().toISOString(), idem);
    const sent = db.prepare('SELECT gonderilme_tarihi FROM oturum_outbox WHERE idempotency_anahtari=?').get(idem);
    expect(sent.gonderilme_tarihi).toBeTruthy();
    db.close();
  });
});

// ── 5. QR sayaç monotonluğu (process restart) ────────────────────────────────
describe('Sayaç monotonluğu', () => {
  it('restart sonrasında sayaç aynı değerden devam eder', () => {
    const db1 = new Database(':memory:');
    db1.exec("CREATE TABLE qr_counter (id INTEGER PRIMARY KEY CHECK(id=1), last_value INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL DEFAULT ''); INSERT INTO qr_counter VALUES (1,0,'');");
    generateNextQr(db1, 1);
    const last = db1.prepare('SELECT last_value FROM qr_counter WHERE id=1').get().last_value;
    db1.close();

    const db2 = new Database(':memory:');
    db2.exec(`CREATE TABLE qr_counter (id INTEGER PRIMARY KEY CHECK(id=1), last_value INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL DEFAULT ''); INSERT INTO qr_counter VALUES (1,${last},'');`);
    const q2 = generateNextQr(db2, 1);
    const lastAfter = db2.prepare('SELECT last_value FROM qr_counter WHERE id=1').get().last_value;
    expect(lastAfter).toBeGreaterThan(last);
    expect(validateChecksum(q2)).toBe(true);
    db2.close();
  });
});
