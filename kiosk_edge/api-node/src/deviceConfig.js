import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { Agent, fetch } from 'undici';

import { getAuthHeaders } from './provisioning.js';

export const DEFAULT_DEVICE_CONFIG = Object.freeze({
  interaction_timeout_seconds: 20,
  idle_content_min_seconds: 10,
  idle_content_max_seconds: 12,
  idle_content_refresh_seconds: 300,
  idle_audio_delay_seconds: 1200,
  idle_audio_repeat_seconds: 300,
  idle_audio_schedule_mode: 'ALL_DAY',
  idle_audio_play_on_duty: false,
  idle_audio_duty_dates: [],
});

let _agent = null;
function getAgent(verifyTls) {
  if (!_agent) _agent = new Agent({ connect: { rejectUnauthorized: !!verifyTls } });
  return _agent;
}

function ensureDeviceConfigTable(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS kiosk_device_config (
      id INTEGER PRIMARY KEY CHECK(id = 1),
      interaction_timeout_seconds INTEGER NOT NULL DEFAULT 20,
      idle_content_min_seconds INTEGER NOT NULL DEFAULT 10,
      idle_content_max_seconds INTEGER NOT NULL DEFAULT 12,
      idle_content_refresh_seconds INTEGER NOT NULL DEFAULT 300,
      idle_audio_delay_seconds INTEGER NOT NULL DEFAULT 1200,
      idle_audio_repeat_seconds INTEGER NOT NULL DEFAULT 300,
      idle_audio_schedule_mode TEXT NOT NULL DEFAULT 'ALL_DAY',
      idle_audio_play_on_duty INTEGER NOT NULL DEFAULT 0,
      idle_audio_duty_dates TEXT NOT NULL DEFAULT '[]',
      idle_audio_enabled INTEGER NOT NULL DEFAULT 0,
      audio_source_url TEXT NOT NULL DEFAULT '',
      audio_source_checksum TEXT NOT NULL DEFAULT '',
      audio_original_name TEXT NOT NULL DEFAULT '',
      audio_content_type TEXT NOT NULL DEFAULT '',
      audio_local_path TEXT NOT NULL DEFAULT '',
      audio_status TEXT NOT NULL DEFAULT 'empty',
      updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );
    INSERT OR IGNORE INTO kiosk_device_config (id) VALUES (1);
    CREATE TABLE IF NOT EXISTS kiosk_device_audio_files (
      audio_id TEXT PRIMARY KEY,
      playback_order INTEGER NOT NULL DEFAULT 0,
      source_url TEXT NOT NULL,
      source_checksum TEXT NOT NULL DEFAULT '',
      original_name TEXT NOT NULL DEFAULT '',
      content_type TEXT NOT NULL DEFAULT '',
      local_path TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT 'pending',
      updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );
  `);
  const columns = db.prepare('PRAGMA table_info(kiosk_device_config)').all();
  if (!columns.some((column) => column.name === 'idle_audio_repeat_seconds')) {
    db.exec('ALTER TABLE kiosk_device_config ADD COLUMN idle_audio_repeat_seconds INTEGER NOT NULL DEFAULT 300');
  }
  if (!columns.some((column) => column.name === 'idle_audio_schedule_mode')) {
    db.exec("ALTER TABLE kiosk_device_config ADD COLUMN idle_audio_schedule_mode TEXT NOT NULL DEFAULT 'ALL_DAY'");
  }
  if (!columns.some((column) => column.name === 'idle_audio_play_on_duty')) {
    db.exec('ALTER TABLE kiosk_device_config ADD COLUMN idle_audio_play_on_duty INTEGER NOT NULL DEFAULT 0');
  }
  if (!columns.some((column) => column.name === 'idle_audio_duty_dates')) {
    db.exec("ALTER TABLE kiosk_device_config ADD COLUMN idle_audio_duty_dates TEXT NOT NULL DEFAULT '[]'");
  }
  // Onceki tek-dosya cache'ini cihaz offline olsa bile yeni listeye tasir.
  db.exec(`
    INSERT OR IGNORE INTO kiosk_device_audio_files (
      audio_id, playback_order, source_url, source_checksum, original_name,
      content_type, local_path, status, updated_at
    )
    SELECT
      'legacy', 0, audio_source_url, audio_source_checksum, audio_original_name,
      audio_content_type, audio_local_path, audio_status, updated_at
    FROM kiosk_device_config
    WHERE id=1 AND audio_status='ready' AND audio_local_path<>'';
  `);
}

function boundedInt(value, fallback, minimum, maximum) {
  const number = Number.parseInt(value, 10);
  return Number.isInteger(number) && number >= minimum && number <= maximum ? number : fallback;
}

function normalizedTimings(payload = {}) {
  const min = boundedInt(payload.idle_content_min_seconds, DEFAULT_DEVICE_CONFIG.idle_content_min_seconds, 5, 300);
  const max = boundedInt(payload.idle_content_max_seconds, DEFAULT_DEVICE_CONFIG.idle_content_max_seconds, min, 300);
  return {
    interaction_timeout_seconds: boundedInt(payload.interaction_timeout_seconds, DEFAULT_DEVICE_CONFIG.interaction_timeout_seconds, 5, 3600),
    idle_content_min_seconds: min,
    idle_content_max_seconds: Math.max(min, max),
    idle_content_refresh_seconds: boundedInt(payload.idle_content_refresh_seconds, DEFAULT_DEVICE_CONFIG.idle_content_refresh_seconds, 30, 3600),
    idle_audio_delay_seconds: boundedInt(payload.idle_audio_delay_seconds, DEFAULT_DEVICE_CONFIG.idle_audio_delay_seconds, 60, 86400),
    idle_audio_repeat_seconds: boundedInt(payload.idle_audio_repeat_seconds, DEFAULT_DEVICE_CONFIG.idle_audio_repeat_seconds, 60, 86400),
    idle_audio_schedule_mode: payload.idle_audio_schedule_mode === 'BUSINESS_HOURS' ? 'BUSINESS_HOURS' : 'ALL_DAY',
    idle_audio_play_on_duty: payload.idle_audio_play_on_duty === true ? 1 : 0,
    idle_audio_duty_dates: JSON.stringify(
      Array.isArray(payload.idle_audio_duty_dates)
        ? payload.idle_audio_duty_dates.filter((date) => /^\d{4}-\d{2}-\d{2}$/.test(date)).slice(0, 400)
        : [],
    ),
  };
}

function extensionFor(contentType, sourceUrl = '') {
  if (contentType === 'audio/mpeg') return '.mp3';
  if (contentType === 'audio/wav' || contentType === 'audio/x-wav') return '.wav';
  if (contentType === 'audio/ogg') return '.ogg';
  try {
    const ext = path.extname(new URL(sourceUrl).pathname).toLowerCase();
    return ['.mp3', '.wav', '.ogg'].includes(ext) ? ext : '.bin';
  } catch {
    return '.bin';
  }
}

function isCentralApiUrl(candidate, centralApiBase) {
  try {
    return new URL(candidate).origin === new URL(centralApiBase).origin;
  } catch {
    return false;
  }
}

function manifestFiles(audio = {}) {
  const source = Array.isArray(audio.files) && audio.files.length
    ? audio.files
    : (audio.media_url ? [{ ...audio, id: 'legacy', order: 0 }] : []);
  return source
    .filter((item) => item && typeof item.media_url === 'string' && item.media_url)
    .map((item, index) => ({
      id: String(item.id ?? index),
      order: boundedInt(item.order, index, 0, 65535),
      media_url: item.media_url,
      checksum: item.checksum || '',
      original_name: item.original_name || '',
      content_type: item.content_type || '',
    }))
    .sort((a, b) => a.order - b.order || a.id.localeCompare(b.id));
}

function updateTimings(db, timings) {
  db.prepare(`
    UPDATE kiosk_device_config SET
      interaction_timeout_seconds=@interaction_timeout_seconds,
      idle_content_min_seconds=@idle_content_min_seconds,
      idle_content_max_seconds=@idle_content_max_seconds,
      idle_content_refresh_seconds=@idle_content_refresh_seconds,
      idle_audio_delay_seconds=@idle_audio_delay_seconds,
      idle_audio_repeat_seconds=@idle_audio_repeat_seconds,
      idle_audio_schedule_mode=@idle_audio_schedule_mode,
      idle_audio_play_on_duty=@idle_audio_play_on_duty,
      idle_audio_duty_dates=@idle_audio_duty_dates,
      updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
    WHERE id=1
  `).run(timings);
}

async function downloadAudioFile(db, item, settings) {
  const response = await fetch(item.media_url, {
    headers: isCentralApiUrl(item.media_url, settings.centralApiBase) ? getAuthHeaders(db) : {},
    dispatcher: getAgent(settings.verifyTls),
    signal: AbortSignal.timeout(30000),
  });
  if (!response.ok) throw new Error(`Idle ses indirme HTTP ${response.status}`);
  const bytes = Buffer.from(await response.arrayBuffer());
  const rawChecksum = crypto.createHash('sha256').update(bytes).digest('hex');
  const fileChecksum = `sha256:${rawChecksum}`;
  if (item.checksum && fileChecksum !== item.checksum) throw new Error(`Idle ses checksum uyusmazligi: ${item.id}`);

  const safeId = item.id.replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 80) || 'audio';
  const finalPath = path.join(settings.mediaDir, `idle_audio_${safeId}_${rawChecksum.slice(0, 12)}${extensionFor(item.content_type, item.media_url)}`);
  if (!fs.existsSync(finalPath)) {
    const tempPath = `${finalPath}.${process.pid}.${Date.now()}.tmp`;
    try {
      fs.writeFileSync(tempPath, bytes);
      fs.renameSync(tempPath, finalPath);
    } finally {
      try { if (fs.existsSync(tempPath)) fs.unlinkSync(tempPath); } catch { /* best effort */ }
    }
  }
  return finalPath;
}

export async function syncDeviceConfig(db, payload = {}, settings, log = console) {
  ensureDeviceConfigTable(db);
  updateTimings(db, normalizedTimings(payload));

  const audio = payload.idle_audio || {};
  const requested = manifestFiles(audio);
  if (audio.enabled !== true || requested.length === 0) {
    db.prepare(`UPDATE kiosk_device_config SET idle_audio_enabled=0, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=1`).run();
    return getDeviceConfig(db);
  }

  fs.mkdirSync(settings.mediaDir, { recursive: true });
  const oldRows = db.prepare('SELECT * FROM kiosk_device_audio_files ORDER BY playback_order, audio_id').all();
  const oldById = new Map(oldRows.map((row) => [row.audio_id, row]));
  const resolved = [];
  const newlyDownloaded = [];
  try {
    for (const item of requested) {
      const current = oldById.get(item.id);
      const sameReady = current?.status === 'ready'
        && current.source_url === item.media_url
        && current.source_checksum === item.checksum
        && current.local_path
        && fs.existsSync(current.local_path);
      const localPath = sameReady ? current.local_path : await downloadAudioFile(db, item, settings);
      if (!sameReady) newlyDownloaded.push(localPath);
      resolved.push({ ...item, localPath });
    }
  } catch (error) {
    for (const filePath of newlyDownloaded) {
      if (!oldRows.some((row) => row.local_path === filePath)) {
        try { if (fs.existsSync(filePath)) fs.unlinkSync(filePath); } catch { /* best effort */ }
      }
    }
    const hasFallback = oldRows.some((row) => row.status === 'ready' && row.local_path && fs.existsSync(row.local_path));
    db.prepare(`UPDATE kiosk_device_config SET idle_audio_enabled=?, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=1`).run(hasFallback ? 1 : 0);
    log.warn?.({ event: 'idle_audio_cache_failed', err: error?.message }, 'Idle ses listesi indirilemedi; son calisan liste korunuyor');
    return getDeviceConfig(db);
  }

  const applySnapshot = db.transaction((items) => {
    db.prepare('DELETE FROM kiosk_device_audio_files').run();
    const insert = db.prepare(`
      INSERT INTO kiosk_device_audio_files (
        audio_id, playback_order, source_url, source_checksum, original_name,
        content_type, local_path, status, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ready', strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    `);
    for (const item of items) {
      insert.run(item.id, item.order, item.media_url, item.checksum, item.original_name, item.content_type, item.localPath);
    }
    db.prepare(`UPDATE kiosk_device_config SET idle_audio_enabled=1, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=1`).run();
  });
  applySnapshot(resolved);

  const activePaths = new Set(resolved.map((item) => item.localPath));
  for (const row of oldRows) {
    if (row.local_path && !activePaths.has(row.local_path)) {
      try { if (fs.existsSync(row.local_path)) fs.unlinkSync(row.local_path); } catch { /* best effort */ }
    }
  }
  log.info?.({ event: 'idle_audio_cached', count: resolved.length }, 'Kiosk idle ses listesi lokal cache guncellendi');
  return getDeviceConfig(db);
}

function readyAudioRows(db) {
  return db.prepare(`
    SELECT * FROM kiosk_device_audio_files
    WHERE status='ready'
    ORDER BY playback_order, audio_id
  `).all().filter((row) => row.local_path && fs.existsSync(row.local_path));
}

export function getDeviceConfig(db) {
  ensureDeviceConfigTable(db);
  const row = db.prepare('SELECT * FROM kiosk_device_config WHERE id=1').get() || {};
  const files = row.idle_audio_enabled === 1 ? readyAudioRows(db) : [];
  const publicFiles = files.map((file) => ({
    id: file.audio_id,
    media_url: `/api/device-audio/${encodeURIComponent(file.audio_id)}`,
    original_name: file.original_name || '',
    order: file.playback_order,
  }));
  let dutyDates = [];
  try { dutyDates = JSON.parse(row.idle_audio_duty_dates || '[]'); } catch { dutyDates = []; }
  return {
    interaction_timeout_seconds: row.interaction_timeout_seconds ?? DEFAULT_DEVICE_CONFIG.interaction_timeout_seconds,
    idle_content_min_seconds: row.idle_content_min_seconds ?? DEFAULT_DEVICE_CONFIG.idle_content_min_seconds,
    idle_content_max_seconds: row.idle_content_max_seconds ?? DEFAULT_DEVICE_CONFIG.idle_content_max_seconds,
    idle_content_refresh_seconds: row.idle_content_refresh_seconds ?? DEFAULT_DEVICE_CONFIG.idle_content_refresh_seconds,
    idle_audio_delay_seconds: row.idle_audio_delay_seconds ?? DEFAULT_DEVICE_CONFIG.idle_audio_delay_seconds,
    idle_audio_repeat_seconds: row.idle_audio_repeat_seconds ?? DEFAULT_DEVICE_CONFIG.idle_audio_repeat_seconds,
    idle_audio_schedule_mode: row.idle_audio_schedule_mode === 'BUSINESS_HOURS' ? 'BUSINESS_HOURS' : 'ALL_DAY',
    idle_audio_play_on_duty: row.idle_audio_play_on_duty === 1,
    idle_audio_duty_dates: Array.isArray(dutyDates) ? dutyDates : [],
    idle_audio: {
      enabled: publicFiles.length > 0,
      files: publicFiles,
      media_url: publicFiles[0]?.media_url || '',
      original_name: publicFiles[0]?.original_name || '',
    },
  };
}

export function getDeviceAudioFile(db, audioId = null) {
  ensureDeviceConfigTable(db);
  const enabled = db.prepare('SELECT idle_audio_enabled FROM kiosk_device_config WHERE id=1').get()?.idle_audio_enabled === 1;
  if (!enabled) return null;
  const row = audioId === null
    ? db.prepare(`SELECT * FROM kiosk_device_audio_files WHERE status='ready' ORDER BY playback_order, audio_id LIMIT 1`).get()
    : db.prepare(`SELECT * FROM kiosk_device_audio_files WHERE audio_id=? AND status='ready'`).get(String(audioId));
  if (!row || !row.local_path || !fs.existsSync(row.local_path)) return null;
  return { path: row.local_path, contentType: row.content_type || 'audio/mpeg' };
}
