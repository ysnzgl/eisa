// Fastify (Pino) JSON stdout logger.
// Loglar dosyaya yazilmaz; container stdout/stderr uzerinden Kubernetes
// node collector (Alloy) tarafindan Loki'ye iletilir.
// Detay: docs/operations/logging.md
import { redactionPaths } from './logRedaction.js';

const LEVEL_MAP = { trace: 'DEBUG', debug: 'DEBUG', info: 'INFO', warn: 'WARNING', error: 'ERROR', fatal: 'CRITICAL' };

/**
 * Fastify icin Pino logger opsiyonlarini uretir.
 * Production: JSON stdout (level, service, environment, version alanlariyla).
 * Development: pino-pretty istenirse acilabilir; varsayilan yine JSON stdout.
 *
 * @param {object} settings — config.js ciktisi. Beklenen alanlar:
 *   logLevel, serviceName, appEnv, appVersion, devMode, pretty
 */
export function buildLoggerOptions(settings) {
  const level = (settings.logLevel || (settings.devMode ? 'debug' : 'info')).toLowerCase();
  const serviceName = settings.serviceName || 'eisa-kiosk-api';
  const environment = settings.appEnv || (settings.devMode ? 'development' : 'production');
  const version = settings.appVersion || '0.0.0';

  const base = {
    level,
    base: {
      service: serviceName,
      environment,
      version,
    },
    formatters: {
      level(label) {
        return { level: LEVEL_MAP[label] || label.toUpperCase() };
      },
      // Merkezi log semasi ile hizali cikti; req/res nesnelerini duz alanlara indir.
      log(object) {
        const { req, res, ...rest } = object;
        if (req && typeof req === 'object') {
          rest.request_method = req.method;
          rest.request_path   = _safePath(req.url);
        }
        if (res && typeof res === 'object') {
          rest.status_code = res.statusCode;
        }
        return rest;
      },
    },
    timestamp: () => `,"timestamp":"${new Date().toISOString()}"`,
    messageKey: 'message',
    redact: {
      paths: redactionPaths(),
      censor: '***',
      remove: false,
    },
  };

  if (settings.devMode && settings.pretty) {
    base.transport = {
      target: 'pino-pretty',
      options: { translateTime: 'SYS:HH:MM:ss', singleLine: true, colorize: true },
    };
  }

  return base;
}

function _safePath(value) {
  if (!value || typeof value !== 'string') return '/';
  if (value.length > 256) return value.slice(0, 256) + '…';
  // Query string'i kes; parametreler hassas olabilir.
  const q = value.indexOf('?');
  return q >= 0 ? value.slice(0, q) : value;
}

