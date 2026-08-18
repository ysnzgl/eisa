/**
 * Targeted tests: Crockford QR üretimi, checksum, atomik sayaç, offline davranış.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import Database from 'better-sqlite3';
import { openDb, closeDb } from '../src/db.js';
import {
  CROCKFORD_ALPHABET,
  encodeCrockford,
  computeChecksum,
  validateChecksum,
  generateNextQr,
  CROCKFORD_QR_RE,
} from '../src/qrGen.js';

// ── Hafıza içi SQLite (her test taze) ──────────────────────────────────────
let db;
beforeEach(() => {
  if (db) { try { db.close(); } catch {} }
  db = new Database(':memory:');
  db.pragma('journal_mode = WAL');
  // qr_counter tablosunu başlat
  db.exec(`
    CREATE TABLE IF NOT EXISTS schema_meta (version INTEGER NOT NULL);
    INSERT INTO schema_meta VALUES (14);
    CREATE TABLE qr_counter (
      id INTEGER PRIMARY KEY CHECK(id = 1),
      last_value INTEGER NOT NULL DEFAULT 0,
      updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );
    INSERT INTO qr_counter (id, last_value) VALUES (1, 0);
  `);
});

// ── Crockford alfabe kontrolleri ───────────────────────────────────────────
describe('CROCKFORD_ALPHABET', () => {
  it('32 karakter içerir', () => {
    expect(CROCKFORD_ALPHABET.length).toBe(32);
  });

  it('I, L, O, U içermez', () => {
    expect(CROCKFORD_ALPHABET).not.toContain('I');
    expect(CROCKFORD_ALPHABET).not.toContain('L');
    expect(CROCKFORD_ALPHABET).not.toContain('O');
    expect(CROCKFORD_ALPHABET).not.toContain('U');
  });

  it('0-9 ile başlar', () => {
    expect(CROCKFORD_ALPHABET.slice(0, 10)).toBe('0123456789');
  });
});

// ── encodeCrockford ────────────────────────────────────────────────────────
describe('encodeCrockford', () => {
  it('0 → 7 sıfır', () => {
    expect(encodeCrockford(0, 7)).toBe('0000000');
  });

  it('1 → 0000001', () => {
    expect(encodeCrockford(1, 7)).toBe('0000001');
  });

  it('32 → 0000010 (32 = 1 * 32^1)', () => {
    expect(encodeCrockford(32, 7)).toBe('0000010');
  });

  it('Unix timestamp aralığında 7 karaktere sığar', () => {
    // ~1.75 milyar unix sn < 32^7 = 34 milyar
    const unix2026 = 1_754_438_400;
    const encoded = encodeCrockford(unix2026, 7);
    expect(encoded.length).toBe(7);
    expect(encoded).toMatch(/^[0123456789ABCDEFGHJKMNPQRSTVWXYZ]{7}$/);
  });
});

// ── computeChecksum / validateChecksum ────────────────────────────────────
describe('checksum', () => {
  it('8 karakterlik giriş için tek karakter döner', () => {
    const check = computeChecksum('10000000');
    expect(check.length).toBe(1);
    expect(CROCKFORD_ALPHABET).toContain(check);
  });

  it('computeChecksum deterministik', () => {
    expect(computeChecksum('10000000')).toBe(computeChecksum('10000000'));
  });

  it('validateChecksum — geçerli kod', () => {
    const first8 = '10000000';
    const check = computeChecksum(first8);
    expect(validateChecksum(first8 + check)).toBe(true);
  });

  it('validateChecksum — hatalı checksum', () => {
    const first8 = '10000000';
    const wrongCheck = computeChecksum(first8) === 'A' ? 'B' : 'A';
    expect(validateChecksum(first8 + wrongCheck)).toBe(false);
  });

  it('validateChecksum — 8 karakter (eksik)', () => {
    expect(validateChecksum('10000000')).toBe(false);
  });

  it('validateChecksum — 10 karakter (fazla)', () => {
    expect(validateChecksum('1000000000')).toBe(false);
  });
});

// ── generateNextQr ────────────────────────────────────────────────────────
describe('generateNextQr', () => {
  it('9 karakterlik Crockford QR döner', () => {
    const qr = generateNextQr(db, 1);
    expect(qr.length).toBe(9);
    expect(CROCKFORD_QR_RE.test(qr)).toBe(true);
  });

  it('ilk karakter kiosk numarasının Crockford karşılığı', () => {
    const qr1 = generateNextQr(db, 1);
    expect(qr1[0]).toBe(CROCKFORD_ALPHABET[1]); // '1'

    // counter'ı sıfırla (farklı kiosk numarası testi için)
    db.exec("UPDATE qr_counter SET last_value = 0");
    const qr10 = generateNextQr(db, 10);
    expect(qr10[0]).toBe(CROCKFORD_ALPHABET[10]); // 'A'
  });

  it('checksum geçerli', () => {
    const qr = generateNextQr(db, 5);
    expect(validateChecksum(qr)).toBe(true);
  });

  it('monoton artar (her çağrıda farklı QR)', () => {
    const q1 = generateNextQr(db, 1);
    const q2 = generateNextQr(db, 1);
    const q3 = generateNextQr(db, 1);
    expect(q1).not.toBe(q2);
    expect(q2).not.toBe(q3);
    // Counter değeri artar
    const counter = db.prepare('SELECT last_value FROM qr_counter WHERE id=1').get();
    expect(counter.last_value).toBeGreaterThan(0);
  });

  it('sayaç geriye gitmez (eski timestamp durumu)', () => {
    // Counter'ı gelecekte bir değere set et
    const futureValue = Math.floor(Date.now() / 1000) + 1000;
    db.exec(`UPDATE qr_counter SET last_value = ${futureValue}`);
    const qr = generateNextQr(db, 1);
    expect(validateChecksum(qr)).toBe(true);
    const row = db.prepare('SELECT last_value FROM qr_counter WHERE id=1').get();
    expect(row.last_value).toBeGreaterThan(futureValue); // futureValue + 1
  });

  it('geçersiz kiosk numarası (0) hata fırlatır', () => {
    expect(() => generateNextQr(db, 0)).toThrow();
  });

  it('geçersiz kiosk numarası (32) hata fırlatır', () => {
    expect(() => generateNextQr(db, 32)).toThrow();
  });

  it('geçerli aralık uç değerleri: 1 ve 31', () => {
    expect(() => generateNextQr(db, 1)).not.toThrow();
    db.exec("UPDATE qr_counter SET last_value = 0");
    expect(() => generateNextQr(db, 31)).not.toThrow();
  });

  it('atomik transaction: QR + outbox insert birlikte', () => {
    // oturum_outbox tablosu simülasyonu
    db.exec(`
      CREATE TABLE oturum_outbox (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        idempotency_anahtari TEXT UNIQUE,
        payload TEXT NOT NULL,
        olusturulma_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
        gonderilme_tarihi TEXT,
        retry_count INTEGER NOT NULL DEFAULT 0,
        error_reason TEXT
      );
    `);

    const idem = 'test-key-123';
    const txn = db.transaction(() => {
      const qr = generateNextQr(db, 1);
      db.prepare(
        'INSERT OR IGNORE INTO oturum_outbox (idempotency_anahtari, payload) VALUES (?, ?)'
      ).run(idem, JSON.stringify({ qr_kodu: qr }));
      return qr;
    });
    const qr = txn();

    expect(validateChecksum(qr)).toBe(true);
    const row = db.prepare('SELECT payload FROM oturum_outbox WHERE idempotency_anahtari = ?').get(idem);
    expect(row).toBeTruthy();
    const payload = JSON.parse(row.payload);
    expect(payload.qr_kodu).toBe(qr);
  });

  it('CROCKFORD_QR_RE sadece geçerli 9 char formatı kabul eder', () => {
    expect(CROCKFORD_QR_RE.test('1K7M9QX5C')).toBe(true);
    expect(CROCKFORD_QR_RE.test('A1B2C3D4')).toBe(false); // 8 char
    expect(CROCKFORD_QR_RE.test('1K7M9QX5CI')).toBe(false); // I yasak
    expect(CROCKFORD_QR_RE.test('1K7M9QX5L')).toBe(false); // L yasak
    expect(CROCKFORD_QR_RE.test('abcdefghi')).toBe(false); // küçük harf
  });
});
