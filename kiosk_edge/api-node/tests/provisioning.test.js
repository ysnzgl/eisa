// Kiosk provisioning + App Key auth birim testleri (ag gerektirmez).
import { describe, it, expect, beforeEach } from 'vitest';
import Database from 'better-sqlite3';
import {
  getAuthHeaders,
  hasAppKeyCredentials,
  handle401Error,
  handle403Error,
  cleanupLegacyIotToken,
  resolveRuntimeSettings,
} from '../src/provisioning.js';

function metaDb() {
  const db = new Database(':memory:');
  db.exec("CREATE TABLE kiosk_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL DEFAULT '');");
  return db;
}
function setMeta(db, k, v) {
  db.prepare(
    'INSERT INTO kiosk_meta (key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
  ).run(k, String(v));
}
function getMeta(db, k) {
  return db.prepare('SELECT value FROM kiosk_meta WHERE key=?').get(k)?.value ?? '';
}

const baseSettings = {
  kioskFleetKey: 'fleet',
  kioskProvisioningSecret: 'secret',
  centralApiBase: 'http://127.0.0.1:9',
  verifyTls: false,
  kioskBootstrapPath: '/api/kiosk/v1/bootstrap/',
};
const silent = { info() {}, warn() {}, error() {}, debug() {} };

describe('kiosk provisioning + App Key auth', () => {
  let db;
  beforeEach(() => { db = metaDb(); });

  it('getAuthHeaders: yalniz AppKey + X-Kiosk-MAC (Bearer/Fleet yok)', () => {
    setMeta(db, 'kiosk_app_key', 'APPKEY123');
    setMeta(db, 'kiosk_mac', 'AA:BB:CC:DD:EE:FF');
    const h = getAuthHeaders(db);
    expect(h['Authorization']).toBe('AppKey APPKEY123');
    expect(h['X-Kiosk-MAC']).toBe('AA:BB:CC:DD:EE:FF');
    expect(h['X-Kiosk-Key']).toBeUndefined();
    expect(h['Authorization']).not.toMatch(/Bearer/);
  });

  it('getAuthHeaders: App Key yoksa bos header', () => {
    expect(getAuthHeaders(db)).toEqual({});
    expect(hasAppKeyCredentials(db)).toBe(false);
  });

  it('hasAppKeyCredentials: app_key + mac varsa true', () => {
    setMeta(db, 'kiosk_app_key', 'x');
    setMeta(db, 'kiosk_mac', 'AA:BB:CC:DD:EE:FF');
    expect(hasAppKeyCredentials(db)).toBe(true);
  });

  it('401 ve 403: App Key SILINMEZ (fallback yok)', () => {
    setMeta(db, 'kiosk_app_key', 'KEEP');
    handle401Error(db, baseSettings, silent);
    handle403Error(db, baseSettings, silent);
    expect(getMeta(db, 'kiosk_app_key')).toBe('KEEP');
  });

  it('cleanupLegacyIotToken: eski iot_token bir defalik silinir', () => {
    setMeta(db, 'iot_token', 'legacy-token');
    cleanupLegacyIotToken(db, silent);
    expect(getMeta(db, 'iot_token')).toBe('');
  });

  it('resolveRuntimeSettings: APPROVED + app_key → bootstrap yok, runtime App Key set', async () => {
    setMeta(db, 'provisioning_state', 'APPROVED');
    setMeta(db, 'kiosk_app_key', 'APPKEY123');
    setMeta(db, 'kiosk_mac', 'AA:BB:CC:DD:EE:FF');
    setMeta(db, 'kiosk_id', '7');
    setMeta(db, 'pharmacy_id', '3');

    const rt = await resolveRuntimeSettings(db, baseSettings, silent);
    expect(rt.kioskAppKey).toBe('APPKEY123');
    expect(rt.kioskId).toBe(7);
    expect(rt.pharmacyId).toBe(3);

    const h = getAuthHeaders(db);
    expect(h['Authorization']).toBe('AppKey APPKEY123');
    expect(h['X-Kiosk-Key']).toBeUndefined();
  });

  it('resolveRuntimeSettings: REJECTED → bootstrap denenmez', async () => {
    setMeta(db, 'provisioning_state', 'REJECTED');
    setMeta(db, 'kiosk_mac', 'AA:BB:CC:DD:EE:FF');
    const rt = await resolveRuntimeSettings(db, baseSettings, silent);
    // App Key yok; operasyonel auth uretilemez.
    expect(hasAppKeyCredentials(db)).toBe(false);
    expect(rt.kioskAppKey).toBe('');
  });
});
