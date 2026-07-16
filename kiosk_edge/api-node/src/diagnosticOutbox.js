// Kiosk diagnostic outbox — bounded, sanitized teknik log kuyrugu.
// Sadece WARNING/ERROR/CRITICAL kayitlari ve merkezi sistem acisindan onemli
// operasyonel event'ler tutulur. INFO/DEBUG YAZILMAZ. Detay:
// docs/operations/logging.md
import crypto from 'node:crypto';
import { getCorrelationId } from './correlationId.js';
import { sanitize } from './logRedaction.js';

const ALLOWED_LEVELS = new Set(['WARNING', 'ERROR', 'CRITICAL']);
const MAX_MESSAGE_LEN = 4096;
const MAX_EVENT_LEN = 128;
const CONTEXT_MAX_JSON = 6144;

// Ayni event/message icin kisa surede yuzlerce satir olusmasin diye
// yumusak in-memory rate limiter (event basina saniyede 1).
const _lastEmittedAt = new Map();
const _RATE_WINDOW_MS = 5000;

/**
 * Diagnostic outbox'a bir kayit ekler.
 *
 * @param {import('better-sqlite3').Database} db
 * @param {{ level: string, event: string, message?: string, context?: object,
 *   correlationId?: string, occurredAt?: string }} entry
 * @returns {boolean} kayit eklendi mi?
 */
export function recordDiagnostic(db, entry) {
  if (!db || !entry) return false;
  const level = String(entry.level || '').toUpperCase();
  if (!ALLOWED_LEVELS.has(level)) return false;
  const event = _clip(entry.event || 'kiosk_diagnostic', MAX_EVENT_LEN);
  if (!event) return false;

  const key = `${event}|${level}|${_clip(entry.message || '', 64)}`;
  const now = Date.now();
  const last = _lastEmittedAt.get(key) || 0;
  if (now - last < _RATE_WINDOW_MS) return false;
  _lastEmittedAt.set(key, now);
  if (_lastEmittedAt.size > 512) {
    for (const [k, t] of _lastEmittedAt) {
      if (now - t > _RATE_WINDOW_MS * 12) _lastEmittedAt.delete(k);
    }
  }

  const message = _clip(entry.message || event, MAX_MESSAGE_LEN);
  const contextClean = sanitize(entry.context || {});
  let contextJson = JSON.stringify(contextClean);
  if (contextJson.length > CONTEXT_MAX_JSON) {
    contextJson = JSON.stringify({ truncated: true, size: contextJson.length });
  }
  const correlationId = _clip(entry.correlationId || getCorrelationId() || '', 64);

  try {
    db.prepare(
      `INSERT INTO diagnostic_outbox (created_at, level, event, message, context_json, correlation_id)
       VALUES (COALESCE(?, strftime('%Y-%m-%dT%H:%M:%fZ','now')), ?, ?, ?, ?, ?)`,
    ).run(
      entry.occurredAt || null,
      level,
      event,
      message,
      contextJson,
      correlationId || null,
    );
    return true;
  } catch {
    // Diagnostic outbox arizasi uygulamayi durdurmamali; sessizce dus.
    return false;
  }
}

/**
 * Gonderilecek pending kayitlari verir (retry backoff uygular).
 * `sent_at` NULL, `next_retry_at` NULL veya gecmisteki kayitlar dahil edilir.
 */
export function fetchPendingDiagnostics(db, limit = 100) {
  if (!db) return [];
  return db
    .prepare(
      `SELECT id, level, event, message, context_json, correlation_id,
              created_at, retry_count
         FROM diagnostic_outbox
        WHERE sent_at IS NULL
          AND (next_retry_at IS NULL OR next_retry_at <= strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        ORDER BY id ASC
        LIMIT ?`,
    )
    .all(Math.max(1, Math.min(limit, 500)))
    .map((row) => ({
      id: row.id,
      level: row.level,
      event: row.event,
      message: row.message,
      context: _safeParse(row.context_json, {}),
      correlation_id: row.correlation_id || undefined,
      occurred_at: row.created_at,
      retry_count: row.retry_count,
    }));
}

/**
 * Basarili gonderilen kayitlari sil.
 */
export function markDiagnosticsSent(db, ids) {
  if (!db || !ids || !ids.length) return;
  const placeholders = ids.map(() => '?').join(',');
  db.prepare(`DELETE FROM diagnostic_outbox WHERE id IN (${placeholders})`).run(...ids);
}

/**
 * Retry sayacini artir, exponential backoff ile next_retry_at kaydet.
 * Max retry asilirsa kayit silinir (sonsuz retry olmasin).
 */
export function reschedulePendingDiagnostics(db, ids, retryCount, maxRetries = 6) {
  if (!db || !ids || !ids.length) return;
  const placeholders = ids.map(() => '?').join(',');
  const next = new Date(Date.now() + Math.min(3600, 30 * 2 ** retryCount) * 1000).toISOString();
  if (retryCount >= maxRetries) {
    db.prepare(`DELETE FROM diagnostic_outbox WHERE id IN (${placeholders})`).run(...ids);
    return;
  }
  db.prepare(
    `UPDATE diagnostic_outbox
        SET retry_count = retry_count + 1,
            next_retry_at = ?
      WHERE id IN (${placeholders})`,
  ).run(next, ...ids);
}

/**
 * Yaslanmis kayitlari (varsayilan 7 gun) temizle.
 */
export function cleanupOldDiagnostics(db, maxAgeDays = 7) {
  if (!db) return 0;
  const days = Math.max(1, Number(maxAgeDays) | 0);
  const res = db
    .prepare(
      `DELETE FROM diagnostic_outbox
        WHERE created_at < datetime('now', '-' || ? || ' days')`,
    )
    .run(days);
  return res.changes || 0;
}

function _clip(value, limit) {
  const s = String(value || '');
  return s.length > limit ? s.slice(0, limit) : s;
}

function _safeParse(raw, fallback) {
  try { return JSON.parse(raw); } catch { return fallback; }
}

/**
 * Yardimci: Pino logger'in warn/error mesajlarindan diagnostic kayit uret.
 * `event` ve `context` obje icinden alinir.
 */
export function diagnosticFromLog(db, level, msgObj, msg) {
  if (!db) return;
  let event = 'kiosk_diagnostic';
  let context = {};
  if (msgObj && typeof msgObj === 'object') {
    event = String(msgObj.event || event);
    context = { ...msgObj };
    delete context.event;
  }
  recordDiagnostic(db, {
    level,
    event,
    message: msg || event,
    context,
  });
}

/**
 * `randomId` yerel bir 64-hex UUID uretir (retry testleri icin).
 */
export function _randomId() {
  return crypto.randomUUID().replace(/-/g, '');
}
