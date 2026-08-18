/**
 * kiosk_event_outbox yazma yardımcısı (Faz 4).
 *
 * Aynı event_type'ın DEDUP_WINDOW_MS içinde tekrar kaydedilmesini engeller
 * (in-memory throttle). Bu sayede senkronizasyon döngüsündeki tekrar eden
 * hatalar panelde log şişirmesine yol açmaz.
 *
 * Veri akışı:
 *   recordKioskEvent(db, {...}) → kiosk_event_outbox INSERT
 *   pushKioskEvents (scheduler) → /api/kiosk/v1/kiosk-events/ → backend KioskEvent tablosu
 */
import crypto from 'node:crypto';

// In-memory throttle map: event_type → last insert timestamp (ms)
const _lastEventAt = new Map();

/** Aynı event_type için minimum süre (ms) — varsayılan 2 dakika. */
const DEDUP_WINDOW_MS = 120_000;

/**
 * Kiosk teknik olayını outbox'a yazar.
 *
 * @param {import('better-sqlite3').Database} db
 * @param {{ event_type: string, severity?: string, message?: string, occurred_at?: string }} opts
 * @returns {boolean} true = kaydedildi, false = throttle (atlandı)
 */
export function recordKioskEvent(db, { event_type, severity = 'WARNING', message = '', occurred_at = null }) {
  if (!db) return false;

  // In-memory throttle: aynı event_type DEDUP_WINDOW_MS içinde yeniden yazılmaz
  const now = Date.now();
  const last = _lastEventAt.get(event_type);
  if (last !== undefined && now - last < DEDUP_WINDOW_MS) return false;

  try {
    const event_id = crypto.randomUUID();
    const ts = occurred_at || new Date().toISOString();
    const inserted = db.prepare(
      `INSERT OR IGNORE INTO kiosk_event_outbox
         (event_id, event_type, severity, message, occurred_at)
       VALUES (?, ?, ?, ?, ?)`,
    ).run(event_id, event_type, severity, String(message).slice(0, 512), ts);

    if (inserted.changes > 0) {
      _lastEventAt.set(event_type, now);
      return true;
    }
    return false;
  } catch {
    // DB hatası outbox yazma denemesini durdurmamalı
    return false;
  }
}
