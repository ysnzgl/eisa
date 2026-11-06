/**
 * Regresyon: backend her yeniden üretimde yeni playlist id verir. Daha önce item
 * içeren bir saat yeni id ile gelince upsert FK ihlaline düşüp tüm sync'i geri
 * alıyordu (kiosk eski/boş playlist'te kalıyordu).
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import Database from 'better-sqlite3';

const fetchMock = vi.fn();
vi.mock('undici', () => ({ Agent: class {}, fetch: (...a) => fetchMock(...a) }));
vi.mock('../src/mediaCache.js', () => ({ syncMediaCache: vi.fn(async () => {}) }));
vi.mock('../src/timezone.js', () => ({ istanbulNow: () => ({ date: '2026-11-03', hour: 4 }) }));
vi.mock('../src/provisioning.js', () => ({
  getAuthHeaders: () => ({}),
  getProvisioningState: () => 'APPROVED',
  handle401Error: vi.fn(),
  handle403Error: vi.fn(),
  hasAppKeyCredentials: () => true,
  enrollDeviceId: vi.fn(),
  resolveRuntimeSettings: (_db, s) => s,
}));

const { pingAndSyncPlaylist } = await import('../src/scheduler.js');

function makeDb() {
  const db = new Database(':memory:');
  db.pragma('foreign_keys = ON');
  db.exec(`
    CREATE TABLE kiosk_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL DEFAULT '');
    CREATE TABLE playlists (
      id TEXT PRIMARY KEY, target_date TEXT NOT NULL, target_hour INTEGER NOT NULL,
      loop_duration_seconds INTEGER NOT NULL DEFAULT 60, version INTEGER NOT NULL DEFAULT 1,
      synced_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      UNIQUE(target_date, target_hour)
    );
    CREATE TABLE playlist_items (
      id TEXT PRIMARY KEY,
      playlist_id TEXT NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
      playback_order INTEGER NOT NULL DEFAULT 0, asset_id TEXT NOT NULL,
      asset_type TEXT NOT NULL CHECK(asset_type IN ('creative','house_ad')),
      media_url TEXT NOT NULL DEFAULT '', duration_seconds INTEGER NOT NULL DEFAULT 15,
      estimated_start_offset_seconds INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE creatives (
      id TEXT PRIMARY KEY, media_url TEXT NOT NULL DEFAULT '', active_media_url TEXT NOT NULL DEFAULT '',
      duration_seconds INTEGER NOT NULL DEFAULT 15, checksum TEXT NOT NULL DEFAULT '',
      type TEXT NOT NULL DEFAULT 'creative', aktif INTEGER NOT NULL DEFAULT 1,
      guncellenme_tarihi TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );
  `);
  return db;
}

function jsonRes(body) {
  return { ok: true, status: 200, json: async () => body };
}

function playlistBody(version, plId, items) {
  return {
    playlists: [{
      id: plId, target_date: '2026-11-03', target_hour: 8, loop_duration_seconds: 60, version,
      items: items.map(([id, offset]) => ({
        id, asset_id: 'cr-1', asset_type: 'creative', media_url: 'http://central/full.png',
        active_media_url: 'http://central/half.png', duration_seconds: 15,
        playback_order: 0, estimated_start_offset_seconds: offset,
      })),
    }],
  };
}

const settings = { centralApiBase: 'http://central', verifyTls: false };
const log = { info: vi.fn(), warn: vi.fn(), debug: vi.fn() };

describe('pingAndSyncPlaylist — playlist id değişimi', () => {
  let db;
  beforeEach(() => { db = makeDb(); fetchMock.mockReset(); log.warn.mockReset(); });

  it('dolu saat yeni playlist id ile gelince eski item\'lar değiştirilir', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonRes({ playlist_version: 9 }))
      .mockResolvedValueOnce(jsonRes(playlistBody(9, 'pl-old', [['it-a', 120], ['it-b', 600]])));
    await pingAndSyncPlaylist(db, settings, log);

    fetchMock
      .mockResolvedValueOnce(jsonRes({ playlist_version: 12 }))
      .mockResolvedValueOnce(jsonRes(playlistBody(12, 'pl-new', [['it-c', 300]])));
    await pingAndSyncPlaylist(db, settings, log);

    expect(log.warn).not.toHaveBeenCalled();
    expect(db.prepare('SELECT id, version FROM playlists').all()).toEqual([{ id: 'pl-new', version: 12 }]);
    expect(db.prepare('SELECT id, playlist_id FROM playlist_items').all()).toEqual([{ id: 'it-c', playlist_id: 'pl-new' }]);
    expect(db.prepare("SELECT value FROM kiosk_meta WHERE key='playlist_version'").get().value).toBe('12');
    // Katalog pull'u beklemeden medya cache'inin indirebilmesi için creative kaydı açılır.
    expect(db.prepare('SELECT id, media_url, active_media_url, aktif FROM creatives').all()).toEqual([
      { id: 'cr-1', media_url: 'http://central/full.png', active_media_url: 'http://central/half.png', aktif: 1 },
    ]);
  });
});
