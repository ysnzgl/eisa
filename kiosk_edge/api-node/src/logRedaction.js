// Hassas veri maskeleme yardimcilari.
// Pino redact ve elle sanitize icin ortak alan listesi.

/**
 * Fastify request/reply Pino redact yollarindan gelen sabit set.
 * Buyuk-kucuk harf duyarli calisir; hem duz alan hem headers[*] kapsanir.
 */
export function redactionPaths() {
  return [
    // Request/response headers (Fastify Pino serializer duzlestirmesi)
    'req.headers.authorization',
    'req.headers.Authorization',
    'req.headers.cookie',
    'req.headers.Cookie',
    'req.headers["x-csrftoken"]',
    'req.headers["x-api-key"]',
    'req.headers["x-app-key"]',
    'req.headers["x-kiosk-key"]',
    'req.headers["x-kiosk-app-key"]',
    'res.headers["set-cookie"]',
    // Kiosk ve backend gizli alanlari
    'iot_token',
    'iotToken',
    'access',
    'accessToken',
    'refresh',
    'refreshToken',
    'token',
    'password',
    'secret',
    'signature',
    'sig',
    'hmac',
    'app_key',
    'appKey',
    'kioskAppKey',
    'kioskFleetKey',
    'kioskProvisioningSecret',
    'X-Kiosk-Key',
    'x-kiosk-key',
    'X-Kiosk-App-Key',
    'x-kiosk-app-key',
    'X-Kiosk-MAC',
    'x-kiosk-mac',
    'qr_kodu',
    'qr_payload',
    'cevaplar',
    'onerilen_etken_maddeler',
    'raw_body',
    'response_body',
  ];
}

const SENSITIVE_SET = new Set(
  redactionPaths()
    .map((p) => p.split('.').pop().replace(/\[|\]|"/g, '').toLowerCase())
    .filter(Boolean),
);

const MAX_STRING = 1024;
const MAX_LIST = 50;

/**
 * Bir nesneyi ozyinelemeli olarak sanitize eder.
 * Hassas alanlar '***' olur, cok uzun string'ler kirpilir, non-serializable degerler repr olur.
 */
export function sanitize(value) {
  if (value === null || value === undefined) return value;
  if (typeof value === 'string') return _clip(value);
  if (typeof value === 'number' || typeof value === 'boolean') return value;
  if (Array.isArray(value)) {
    const out = value.slice(0, MAX_LIST).map(sanitize);
    if (value.length > MAX_LIST) out.push(`…[+${value.length - MAX_LIST}]`);
    return out;
  }
  if (typeof value === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(value)) {
      if (SENSITIVE_SET.has(String(k).toLowerCase())) {
        out[k] = '***';
      } else {
        try { out[k] = sanitize(v); }
        catch { out[k] = '<unrepr>'; }
      }
    }
    return out;
  }
  try { return _clip(String(value)); }
  catch { return '<unrepr>'; }
}

function _clip(text) {
  if (text.length <= MAX_STRING) return text;
  return `${text.slice(0, MAX_STRING)}…[+${text.length - MAX_STRING}c]`;
}

/**
 * Genel amacli guvenli path kirpici; query string cikar.
 */
export function safePath(value) {
  if (!value || typeof value !== 'string') return '/';
  const trimmed = value.length > 256 ? `${value.slice(0, 256)}…` : value;
  const q = trimmed.indexOf('?');
  return q >= 0 ? trimmed.slice(0, q) : trimmed;
}
