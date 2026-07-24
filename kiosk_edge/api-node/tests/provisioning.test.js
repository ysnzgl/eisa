// Kiosk provisioning + App Key auth birim testleri (ag gerektirmez).
import { describe, it, expect, beforeEach, vi } from 'vitest';
import Database from 'better-sqlite3';
import {
  getAuthHeaders,
  hasAppKeyCredentials,
  handle401Error,
  handle403Error,
  cleanupLegacyIotToken,
  resolveRuntimeSettings,
  enrollDeviceId,
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

  it('401: App Key hemen silinir; 403: App Key korunur', () => {
    setMeta(db, 'kiosk_app_key', 'CLEAR_ME');
    handle401Error(db, baseSettings, silent);
    expect(getMeta(db, 'kiosk_app_key')).toBe('');          // 401 → silinmeli
    expect(getMeta(db, 'device_id_enrolled')).toBe('0');

    setMeta(db, 'kiosk_app_key', 'KEEP');
    handle403Error(db, baseSettings, silent);
    expect(getMeta(db, 'kiosk_app_key')).toBe('KEEP');      // 403 → korunmali
  });

  it('401: key zaten yoksa ikinci cagri idempotent', () => {
    setMeta(db, 'kiosk_app_key', '');
    handle401Error(db, baseSettings, silent);               // key yok → warn, temizleme yok
    expect(getMeta(db, 'kiosk_app_key')).toBe('');
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

  it('enrollDeviceId: device_id yoksa error doner', async () => {
    const result = await enrollDeviceId(db, baseSettings, silent);
    expect(result).toBe('error');
  });

  it('enrollDeviceId: zaten enrolled ise already_enrolled doner', async () => {
    setMeta(db, 'device_id', 'aaaa-bbbb-cccc');
    setMeta(db, 'kiosk_app_key', 'APPKEY');
    setMeta(db, 'kiosk_mac', 'AA:BB:CC:DD:EE:FF');
    setMeta(db, 'device_id_enrolled', '1');
    const result = await enrollDeviceId(db, baseSettings, silent);
    expect(result).toBe('already_enrolled');
  });

  it('enrollDeviceId: credential eksikse error doner', async () => {
    setMeta(db, 'device_id', 'aaaa-bbbb-cccc');
    // No app_key set
    const result = await enrollDeviceId(db, { centralApiBase: '' }, silent);
    expect(result).toBe('error');
  });

  it('enrollDeviceId: 200 yanıtında enrolled ve flag kaydeder', async () => {
    setMeta(db, 'device_id', 'aaaa-bbbb-cccc');
    setMeta(db, 'kiosk_app_key', 'APPKEY');
    setMeta(db, 'kiosk_mac', 'AA:BB:CC:DD:EE:FF');

    const mockFetch = async () => ({
      status: 200,
      json: async () => ({ status: 'enrolled', device_id: 'aaaa-bbbb-cccc' }),
    });

    const result = await enrollDeviceId(db, baseSettings, silent, mockFetch);
    expect(result).toBe('enrolled');
    expect(getMeta(db, 'device_id_enrolled')).toBe('1');
  });

  it('enrollDeviceId: 409 already_bound → conflict (farkli device_id bagli, idempotent degil)', async () => {
    setMeta(db, 'device_id', 'aaaa-bbbb-cccc');
    setMeta(db, 'kiosk_app_key', 'APPKEY');
    setMeta(db, 'kiosk_mac', 'AA:BB:CC:DD:EE:FF');

    const mockFetch = async () => ({
      status: 409,
      json: async () => ({ code: 'already_bound' }),
    });

    const result = await enrollDeviceId(db, baseSettings, silent, mockFetch);
    expect(result).toBe('conflict');
    expect(getMeta(db, 'device_id_conflict')).toBe('1');   // conflict flag set
    expect(getMeta(db, 'device_id_enrolled')).not.toBe('1'); // enrolled olmamali
  });

  it('enrollDeviceId: 401 device_id_mismatch → conflict flag set', async () => {
    setMeta(db, 'device_id', 'aaaa-bbbb-cccc');
    setMeta(db, 'kiosk_app_key', 'APPKEY');
    setMeta(db, 'kiosk_mac', 'AA:BB:CC:DD:EE:FF');

    const mockFetch = async () => ({
      status: 401,
      json: async () => ({ code: 'device_id_mismatch' }),
    });

    const result = await enrollDeviceId(db, baseSettings, silent, mockFetch);
    expect(result).toBe('conflict');
    expect(getMeta(db, 'device_id_conflict')).toBe('1');
  });

  it('enrollDeviceId: 200 basari → conflict flag temizlenir', async () => {
    setMeta(db, 'device_id', 'aaaa-bbbb-cccc');
    setMeta(db, 'kiosk_app_key', 'APPKEY');
    setMeta(db, 'kiosk_mac', 'AA:BB:CC:DD:EE:FF');
    setMeta(db, 'device_id_conflict', '1');

    const mockFetch = async () => ({ status: 200 });

    const result = await enrollDeviceId(db, baseSettings, silent, mockFetch);
    expect(result).toBe('enrolled');
    expect(getMeta(db, 'device_id_conflict')).toBe('0');   // conflict temizlendi
    expect(getMeta(db, 'device_id_enrolled')).toBe('1');
  });

  it('enrollDeviceId: getAuthHeaders device_id header tasir (enrolled sonrasi)', () => {
    setMeta(db, 'kiosk_app_key', 'APPKEY123');
    setMeta(db, 'kiosk_mac', 'AA:BB:CC:DD:EE:FF');
    setMeta(db, 'device_id', 'test-uuid-1234');
    const h = getAuthHeaders(db);
    expect(h['X-Kiosk-Device-ID']).toBe('test-uuid-1234');
  });
});
