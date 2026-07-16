/**
 * Merkezi frontend logger — Vue web panelleri.
 *
 * Kurallar:
 *   - Development'ta console cikisina izin verir.
 *   - Production'da yalnizca warning/error olaylari islenir, INFO/DEBUG bastirilir.
 *   - Kritik hatalari sanitize edip backend'e (`/api/analytics/client-events/`)
 *     bildirir. Kullanici verisi, form icerigi, query string DEGERLERI GONDERILMEZ.
 *   - Kendisinin ureettigi hata backend'e sonsuz dongude gonderilmez.
 */

const IS_PROD = import.meta?.env?.PROD === true;

let _appVersion = 'unknown';
let _reportEndpoint = null;
let _correlationSource = null;
let _apiInstance = null;
// Ayni hata mesajinin arka arkaya gonderilmesini engelle.
const _recentSignatures = new Map();
const _RECENT_WINDOW_MS = 30_000;
let _reportInFlight = false;

const SENSITIVE_QUERY_KEYS = new Set([
  'token', 'access_token', 'refresh_token', 'code', 'password', 'secret',
  'qr', 'qr_kodu', 'qr_code',
]);

export function initLogger({ appVersion, apiClient, reportEndpoint = '/api/analytics/client-events/', correlationSource } = {}) {
  if (appVersion) _appVersion = String(appVersion);
  if (apiClient) _apiInstance = apiClient;
  if (reportEndpoint) _reportEndpoint = reportEndpoint;
  if (typeof correlationSource === 'function') _correlationSource = correlationSource;
}

function _sanitizeRoute(route) {
  if (!route || typeof route !== 'string') return '';
  const trimmed = route.length > 256 ? `${route.slice(0, 256)}…` : route;
  try {
    const url = new URL(trimmed, 'http://placeholder');
    // Query'yi maskele: anahtar korunur, degeri '***' olur.
    const cleaned = [];
    for (const [key, value] of url.searchParams.entries()) {
      cleaned.push([key, SENSITIVE_QUERY_KEYS.has(key.toLowerCase()) ? '***' : (value.length > 32 ? '***' : value)]);
    }
    let path = url.pathname;
    if (cleaned.length) {
      path += '?' + cleaned.map(([k, v]) => `${k}=${v}`).join('&');
    }
    return path;
  } catch {
    return trimmed;
  }
}

function _makeSignature(event, message) {
  return `${event}|${(message || '').slice(0, 96)}`;
}

function _shouldSuppress(signature) {
  const now = Date.now();
  const last = _recentSignatures.get(signature) || 0;
  if (now - last < _RECENT_WINDOW_MS) return true;
  _recentSignatures.set(signature, now);
  if (_recentSignatures.size > 128) {
    for (const [k, t] of _recentSignatures) {
      if (now - t > _RECENT_WINDOW_MS * 4) _recentSignatures.delete(k);
    }
  }
  return false;
}

async function _report(level, event, message, extras = {}) {
  if (!_apiInstance || !_reportEndpoint) return;
  const signature = _makeSignature(event, message);
  if (_shouldSuppress(signature)) return;
  if (_reportInFlight) return; // basit backpressure
  _reportInFlight = true;
  const payload = {
    items: [{
      level,
      event,
      message: (message || event).slice(0, 4096),
      stack: extras.stack ? String(extras.stack).slice(0, 8192) : undefined,
      component: extras.component ? String(extras.component).slice(0, 128) : undefined,
      route: _sanitizeRoute(extras.route || (typeof window !== 'undefined' ? window.location.pathname + window.location.search : '')),
      correlation_id: extras.correlationId || (_correlationSource?.() ?? undefined),
      occurred_at: new Date().toISOString(),
    }],
  };
  try {
    await _apiInstance.post(_reportEndpoint, payload, { __silent: true });
  } catch {
    // Sonsuz dongu olmasin: report basarisizsa tekrar report etme.
  } finally {
    _reportInFlight = false;
  }
}

function _makeDevMethod(consoleMethod) {
  return (...args) => {
    if (!IS_PROD) {
      // eslint-disable-next-line no-console
      console[consoleMethod](...args);
    }
  };
}

export const logger = {
  debug: _makeDevMethod('debug'),
  info: _makeDevMethod('info'),
  warn(event, message, extras = {}) {
    if (!IS_PROD) {
      // eslint-disable-next-line no-console
      console.warn(`[${event}]`, message, extras);
    }
    _report('WARNING', event, message, extras);
  },
  error(event, message, extras = {}) {
    if (!IS_PROD) {
      // eslint-disable-next-line no-console
      console.error(`[${event}]`, message, extras);
    }
    _report('ERROR', event, message, extras);
  },
  critical(event, message, extras = {}) {
    if (!IS_PROD) {
      // eslint-disable-next-line no-console
      console.error(`[${event}]`, message, extras);
    }
    _report('CRITICAL', event, message, extras);
  },
  appVersion() { return _appVersion; },
};

/**
 * Vue uygulamasi + tarayici globallerine hata koprusu takar.
 */
export function installGlobalHandlers(app) {
  if (app?.config) {
    app.config.errorHandler = (err, instance, info) => {
      const componentName = instance?.$options?.name || instance?.$options?.__name || 'unknown';
      logger.error('vue_error_handler', err?.message || String(err), {
        stack: err?.stack,
        component: componentName,
      });
      if (!IS_PROD) {
        // eslint-disable-next-line no-console
        console.error('[vue_error_handler]', info, err);
      }
    };
    app.config.warnHandler = (msg, instance) => {
      if (IS_PROD) return; // Vue warning'leri prod'da bastirilir.
      // eslint-disable-next-line no-console
      console.warn('[vue_warn]', msg, instance?.$options?.name);
    };
  }
  if (typeof window !== 'undefined') {
    window.addEventListener('error', (event) => {
      const err = event?.error;
      logger.error('window_error', err?.message || event?.message || 'window_error', {
        stack: err?.stack,
      });
    });
    window.addEventListener('unhandledrejection', (event) => {
      const reason = event?.reason;
      const message = reason instanceof Error ? reason.message : String(reason);
      logger.error('unhandled_rejection', message, {
        stack: reason instanceof Error ? reason.stack : undefined,
      });
    });
  }
}
