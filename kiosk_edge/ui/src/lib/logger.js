/**
 * Svelte kiosk UI merkezi logger.
 *
 * Kurallar:
 *   - Development'ta console cikisi acik.
 *   - Production'da INFO/DEBUG bastirilir; sadece WARNING/ERROR/CRITICAL islenir.
 *   - Kritik UI hatalari yerel Fastify API'ye (`/api/log/client`) gonderilir.
 *   - Kullanici verisi (yas, cinsiyet, cevaplar, QR icerigi, oneri listesi vb.)
 *     asla loglanmaz. UI yalnizca operasyonel event kodlarini gonderir:
 *       screen_render_failed, local_api_unreachable, media_playback_failed,
 *       session_submit_failed, playlist_invalid
 *   - Ayni hatanin sonsuz tekrari icin in-memory rate limit.
 */

const IS_PROD = import.meta?.env?.PROD === true;
const API_BASE = import.meta?.env?.VITE_API_BASE ?? 'http://127.0.0.1:8765';
const REPORT_URL = `${API_BASE}/api/log/client`;

const _recent = new Map();
const RATE_WINDOW_MS = 15_000;
let _inFlight = false;

// Yalnizca izin verilen event kodlari alinir.
const ALLOWED_EVENTS = new Set([
  'screen_render_failed',
  'local_api_unreachable',
  'media_playback_failed',
  'session_submit_failed',
  'playlist_invalid',
  'window_error',
  'unhandled_rejection',
  'wifi_operation_failed',
]);

function _clip(text, max) {
  if (!text) return '';
  const s = String(text);
  return s.length > max ? s.slice(0, max) + '…' : s;
}

async function _report(level, event, message, extras = {}) {
  if (!event || !ALLOWED_EVENTS.has(event)) return;
  const key = `${event}|${level}`;
  const now = Date.now();
  const last = _recent.get(key) || 0;
  if (now - last < RATE_WINDOW_MS) return;
  _recent.set(key, now);
  if (_inFlight) return;
  _inFlight = true;
  const payload = {
    level,
    event,
    message: _clip(message || event, 4096),
    stack: extras.stack ? _clip(extras.stack, 8192) : undefined,
    component: extras.component ? _clip(extras.component, 128) : undefined,
    route: extras.route ? _clip(extras.route, 256) : undefined,
    occurred_at: new Date().toISOString(),
  };
  try {
    await fetch(REPORT_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(3000),
    });
  } catch {
    // Sonsuz dongu olmasin — hata bildirimi basarisizsa yeniden bildirme.
  } finally {
    _inFlight = false;
  }
}

export const logger = {
  debug(...args) {
    if (!IS_PROD) console.debug(...args); // eslint-disable-line no-console
  },
  info(...args) {
    if (!IS_PROD) console.info(...args); // eslint-disable-line no-console
  },
  warn(event, message, extras) {
    if (!IS_PROD) console.warn(`[${event}]`, message, extras); // eslint-disable-line no-console
    _report('WARNING', event, message, extras);
  },
  error(event, message, extras) {
    if (!IS_PROD) console.error(`[${event}]`, message, extras); // eslint-disable-line no-console
    _report('ERROR', event, message, extras);
  },
  critical(event, message, extras) {
    if (!IS_PROD) console.error(`[${event}]`, message, extras); // eslint-disable-line no-console
    _report('CRITICAL', event, message, extras);
  },
};

/**
 * Tarayici globallerini yakala.
 */
export function installGlobalHandlers() {
  if (typeof window === 'undefined') return;
  window.addEventListener('error', (ev) => {
    const err = ev?.error;
    logger.error('window_error', err?.message || ev?.message || 'window_error', {
      stack: err?.stack,
    });
  });
  window.addEventListener('unhandledrejection', (ev) => {
    const reason = ev?.reason;
    const message = reason instanceof Error ? reason.message : String(reason);
    logger.error('unhandled_rejection', message, {
      stack: reason instanceof Error ? reason.stack : undefined,
    });
  });
}
