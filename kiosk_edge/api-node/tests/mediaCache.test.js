/**
 * Faz 0.5 — mediaCache.js birim testleri
 *
 * Her test vi.resetModules() ile taze modul yukler; _running module
 * flag'i testler arasinda sifirlanir. fetch, undici modulunden mocklenir.
 *
 * Kapsanan senaryolar:
 *   KC-01  Stabil URL den medya indirilir, media_cache status=ready
 *   KC-02  Indirilen dosyanin sha256 hex i file_checksum olarak kaydedilir
 *   KC-03  Ayni source_url+source_checksum+mevcut dosya -> yeniden indirme yok
 *   KC-04  source_url degisince yeniden indirilir
 *   KC-05  source_checksum degisince yeniden indirilir
 *   KC-06  Indirme basarisiz olsa mevcut cache dosyasi korunur
 *   KC-07  HTTP 404 -> media_cache status=error kaydedilir
 *   KC-08  Backend sha256:<hex> checksum source_checksum olarak korunur
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

import { makeMemoryDb, fakeSettings } from './helpers.js';

// ─────────────────────────────────────────────────────────────────────────────
// Sabitler
// ─────────────────────────────────────────────────────────────────────────────

const STABLE_URL = 'https://files.eisa.com.tr/eisa-files/ads/testfile.mp4';
const FAKE_BYTES = Buffer.from('fake video bytes for kiosk cache test 1234567890');
const FAKE_SHA256 = crypto.createHash('sha256').update(FAKE_BYTES).digest('hex');
// Backend sha256:<hex> formatinda gonderir; kiosk source_checksum olarak saklar
const BACKEND_CHECKSUM = `sha256:${FAKE_SHA256}`;

function makeSettings(tmpDir) {
  return { ...fakeSettings, mediaDir: tmpDir, verifyTls: false };
}

function seedCreative(db, id, mediaUrl, checksum = '') {
  db.prepare(
    `INSERT OR REPLACE INTO creatives
       (id, media_url, duration_seconds, checksum, type, aktif)
     VALUES (?, ?, 15, ?, 'creative', 1)`
  ).run(id, mediaUrl, checksum);
}

function getCacheRow(db, assetType, assetId) {
  return db.prepare(
    'SELECT * FROM media_cache WHERE asset_type = ? AND asset_id = ?'
  ).get(assetType, assetId);
}

// Sahte basarili fetch yaniti
function makeOkResponse() {
  const buf = Buffer.allocUnsafe(FAKE_BYTES.length);
  FAKE_BYTES.copy(buf);
  return {
    ok: true,
    status: 200,
    arrayBuffer: async () => buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength),
  };
}

// Sahte basarisiz fetch yaniti
function makeErrorResponse(status = 404) {
  return { ok: false, status };
}

// ─────────────────────────────────────────────────────────────────────────────
// Her test icin taze modul + tmpDir
// ─────────────────────────────────────────────────────────────────────────────

let tmpDir;
let db;
let syncMediaCache;
let fetchMock;

beforeEach(async () => {
  // Taze tmpDir
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'eisa-kc-'));
  db = makeMemoryDb();

  // Her testte modulu sifirla: _running flag resetlenir
  vi.resetModules();

  // undici mock ONCE (modul sifirlandiktan sonra tanimla)
  fetchMock = vi.fn();
  vi.doMock('undici', () => ({
    Agent: function AgentMock() { return {}; },
    fetch: fetchMock,
  }));

  // Taze modulu yukle
  const mod = await import('../src/mediaCache.js');
  syncMediaCache = mod.syncMediaCache;
});

afterEach(() => {
  vi.clearAllMocks();
  try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch {}
});

// ─────────────────────────────────────────────────────────────────────────────
// KC-01  Stabil URL den medya indirilir, dosya olusur
// ─────────────────────────────────────────────────────────────────────────────

it('KC-01: stabil URL den indirir ve cache kaydi olusturur', async () => {
  seedCreative(db, 'creative-01', STABLE_URL, BACKEND_CHECKSUM);
  fetchMock.mockResolvedValueOnce(makeOkResponse());

  await syncMediaCache(db, makeSettings(tmpDir));

  const row = getCacheRow(db, 'creative', 'creative-01');
  expect(row).toBeTruthy();
  expect(row.status).toBe('ready');
  expect(row.source_url).toBe(STABLE_URL);
  expect(row.source_checksum).toBe(BACKEND_CHECKSUM);
  expect(fs.existsSync(row.local_path)).toBe(true);
  expect(fetchMock).toHaveBeenCalledOnce();
});

// ─────────────────────────────────────────────────────────────────────────────
// KC-02  Indirilen sha256 hex i file_checksum olarak kaydedilir
// ─────────────────────────────────────────────────────────────────────────────

it('KC-02: indirilen dosyanin sha256 hex i file_checksum olarak kaydedilir', async () => {
  seedCreative(db, 'creative-02', STABLE_URL, BACKEND_CHECKSUM);
  fetchMock.mockResolvedValueOnce(makeOkResponse());

  await syncMediaCache(db, makeSettings(tmpDir));

  const row = getCacheRow(db, 'creative', 'creative-02');
  expect(row.status).toBe('ready');
  // file_checksum raw hex (prefix yok) - downloadToFile sha256 hesaplar
  expect(row.file_checksum).toBe(FAKE_SHA256);
  // source_checksum backend degerini korur ('sha256:<hex>' formati)
  expect(row.source_checksum).toBe(BACKEND_CHECKSUM);
});

// ─────────────────────────────────────────────────────────────────────────────
// KC-03  Ayni URL + checksum + mevcut dosya -> yeniden indirme yok
// ─────────────────────────────────────────────────────────────────────────────

it('KC-03: ayni source_url + source_checksum + mevcut dosya -> yeniden indirme yok', async () => {
  seedCreative(db, 'creative-03', STABLE_URL, BACKEND_CHECKSUM);

  // Ilk sync: indir
  fetchMock.mockResolvedValueOnce(makeOkResponse());
  const settings = makeSettings(tmpDir);
  await syncMediaCache(db, settings);

  expect(fetchMock).toHaveBeenCalledOnce();
  const rowAfterFirst = getCacheRow(db, 'creative', 'creative-03');
  expect(rowAfterFirst.status).toBe('ready');

  // Ikinci sync: yeniden indirme olmamali
  // _running resetlenmeli - modul sifirlandigi icin bu testde tek cagri yapilir
  await syncMediaCache(db, settings);

  // fetch toplam 1 kez cagrilmis olmali (ikinci sync cache hit)
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

// ─────────────────────────────────────────────────────────────────────────────
// KC-04  source_url degisince yeniden indirilir
// ─────────────────────────────────────────────────────────────────────────────

it('KC-04: source_url degisince yeniden indirilir', async () => {
  const urlV1 = `${STABLE_URL}?v=1`;
  const urlV2 = `${STABLE_URL}?v=2`;
  seedCreative(db, 'creative-04', urlV1, BACKEND_CHECKSUM);

  // Ilk sync: urlV1 indir
  fetchMock.mockResolvedValueOnce(makeOkResponse());
  await syncMediaCache(db, makeSettings(tmpDir));
  expect(fetchMock).toHaveBeenCalledTimes(1);

  // URL guncelle
  db.prepare('UPDATE creatives SET media_url = ? WHERE id = ?').run(urlV2, 'creative-04');

  // Ikinci sync: URL degisti -> yeniden indir
  fetchMock.mockResolvedValueOnce(makeOkResponse());
  await syncMediaCache(db, makeSettings(tmpDir));
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

// ─────────────────────────────────────────────────────────────────────────────
// KC-05  source_checksum degisince yeniden indirilir
// ─────────────────────────────────────────────────────────────────────────────

it('KC-05: source_checksum degisince yeniden indirilir', async () => {
  seedCreative(db, 'creative-05', STABLE_URL, 'sha256:oldchecksum');

  // Ilk sync: eski checksum ile indir
  fetchMock.mockResolvedValueOnce(makeOkResponse());
  await syncMediaCache(db, makeSettings(tmpDir));
  expect(fetchMock).toHaveBeenCalledTimes(1);

  // Checksum guncelle
  db.prepare('UPDATE creatives SET checksum = ? WHERE id = ?').run(BACKEND_CHECKSUM, 'creative-05');

  // Ikinci sync: checksum degisti -> yeniden indir
  fetchMock.mockResolvedValueOnce(makeOkResponse());
  await syncMediaCache(db, makeSettings(tmpDir));
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

// ─────────────────────────────────────────────────────────────────────────────
// KC-06  Indirme basarisiz olsa mevcut cache dosyasi korunur
// ─────────────────────────────────────────────────────────────────────────────

it('KC-06: indirme basarisiz olsa mevcut cache dosyasi korunur', async () => {
  seedCreative(db, 'creative-06', STABLE_URL, BACKEND_CHECKSUM);

  // Ilk sync: basarili
  fetchMock.mockResolvedValueOnce(makeOkResponse());
  await syncMediaCache(db, makeSettings(tmpDir));
  const rowReady = getCacheRow(db, 'creative', 'creative-06');
  expect(rowReady.status).toBe('ready');
  const originalPath = rowReady.local_path;
  expect(fs.existsSync(originalPath)).toBe(true);

  // URL degistir -> yeni indirme gerekecek; indirme ag hatasi
  const brokenUrl = `${STABLE_URL}?v=broken`;
  db.prepare('UPDATE creatives SET media_url = ? WHERE id = ?').run(brokenUrl, 'creative-06');
  fetchMock.mockRejectedValueOnce(new Error('Network error'));

  await syncMediaCache(db, makeSettings(tmpDir));

  const rowAfterError = getCacheRow(db, 'creative', 'creative-06');
  // Orijinal dosya hala mevcut - mediaCache.js offline fallback tasarimi:
  // catch blogu: status = fs.existsSync(prev.local_path) ? 'ready' : 'error'
  // Eski dosya mevcut oldugundan status 'ready' kalir (local copy serve edilir)
  expect(fs.existsSync(originalPath)).toBe(true);
  expect(rowAfterError.local_path).toBe(originalPath);
  // error_message log'a yazilir (stderr'e yazildigini goruyoruz)
  // status 'ready' (offline fallback - eski dosya mevcut)
  expect(rowAfterError.status).toBe('ready');
});

// ─────────────────────────────────────────────────────────────────────────────
// KC-07  HTTP 404 -> media_cache status=error kaydedilir
// ─────────────────────────────────────────────────────────────────────────────

it('KC-07: HTTP 404 -> media_cache status=error kaydedilir', async () => {
  seedCreative(db, 'creative-07', STABLE_URL, BACKEND_CHECKSUM);
  fetchMock.mockResolvedValueOnce(makeErrorResponse(404));

  await syncMediaCache(db, makeSettings(tmpDir));

  const row = getCacheRow(db, 'creative', 'creative-07');
  expect(row.status).toBe('error');
  expect(row.error_message).toContain('404');
});

// ─────────────────────────────────────────────────────────────────────────────
// KC-08  Backend sha256:<hex> checksum source_checksum olarak korunur
// ─────────────────────────────────────────────────────────────────────────────

it('KC-08: backend sha256: prefix li checksum source_checksum olarak korunur', async () => {
  seedCreative(db, 'creative-08', STABLE_URL, BACKEND_CHECKSUM);
  fetchMock.mockResolvedValueOnce(makeOkResponse());

  await syncMediaCache(db, makeSettings(tmpDir));

  const row = getCacheRow(db, 'creative', 'creative-08');
  // source_checksum backend den geleni korur (sha256: prefix dahil)
  expect(row.source_checksum).toBe(BACKEND_CHECKSUM);
  expect(row.source_checksum.startsWith('sha256:')).toBe(true);
  // file_checksum raw hex (mediaCache.js downloadToFile tarafindan hesaplanir)
  expect(row.file_checksum).toBe(FAKE_SHA256);
  expect(row.file_checksum.startsWith('sha256:')).toBe(false);
});
