// Kiosk konfigürasyonu — environment veya .env dosyasından okur.
import 'dotenv/config';

function readBool(value, fallback) {
  if (value === undefined || value === null || value === '') return fallback;
  return ['1', 'true', 'yes', 'on'].includes(String(value).toLowerCase());
}

function readInt(value, fallback) {
  const n = parseInt(value, 10);
  return Number.isFinite(n) ? n : fallback;
}

const central = process.env.EISA_CENTRAL_API_BASE || 'https://api.eisa.com.tr';
const devMode = readBool(process.env.EISA_DEV_MODE, false);

// IoT auth
const kioskFleetKey           = process.env.EISA_KIOSK_FLEET_KEY           || process.env.KIOSK_FLEET_KEY           || '';
const kioskProvisioningSecret = process.env.EISA_KIOSK_PROVISIONING_SECRET || process.env.KIOSK_PROVISIONING_SECRET || '';

// Opsiyonel: legacy AppKey override (bootstrapsiz dev/test ortami icin)
const appKey = process.env.EISA_KIOSK_APP_KEY || process.env.APP_KEY || '';

// Loglama — Kubernetes stdout/stderr uyumlu. Detay: docs/operations/logging.md
const serviceName = process.env.SERVICE_NAME || 'eisa-kiosk-api';
const appEnv      = process.env.APP_ENV || process.env.EISA_ENVIRONMENT || (devMode ? 'development' : 'production');
const appVersion  = process.env.APP_VERSION || '0.0.0';
const logLevel    = (process.env.LOG_LEVEL || process.env.EISA_LOG_LEVEL || (devMode ? 'debug' : 'info')).toLowerCase();
const logFormat   = (process.env.LOG_FORMAT || 'json').toLowerCase();
const prettyLogs  = devMode && logFormat !== 'json';

export const settings = Object.freeze({
  sqlitePath:               process.env.EISA_SQLITE_PATH  || '/var/lib/eisa/local.db',
  mediaDir:                 process.env.EISA_MEDIA_DIR    || '/var/lib/eisa/media',
  centralApiBase:           central,
  // IoT auth (ana yontem)
  kioskFleetKey,
  kioskProvisioningSecret,
  kioskBootstrapPath:       process.env.EISA_KIOSK_BOOTSTRAP_PATH || '/api/pharmacies/kiosks/bootstrap/',
  // Legacy AppKey (opsiyonel, dev/test icin)
  kioskAppKey:              appKey,
  kioskMac:                 process.env.EISA_KIOSK_MAC || '',
  // Provision sonrasi kiosk kimlik bilgileri (provisioning.js tarafindan doldurulur).
  kioskId:                  readInt(process.env.EISA_KIOSK_ID,     0),
  pharmacyId:               readInt(process.env.EISA_PHARMACY_ID,  0),
  // Termal yazici (opsiyonel — TCP raw 9100). Tanimsizsa fis basilmaz.
  thermalPrinterHost:       process.env.EISA_THERMAL_PRINTER_HOST || '',
  thermalPrinterPort:       readInt(process.env.EISA_THERMAL_PRINTER_PORT, 9100),
  pullIntervalSec:          readInt(process.env.EISA_PULL_INTERVAL_SEC,   900),
  pushIntervalSec:          readInt(process.env.EISA_PUSH_INTERVAL_SEC,   300),
  pingIntervalSec:          readInt(process.env.EISA_PING_INTERVAL_SEC,    60),
  diagnosticPushIntervalSec: readInt(process.env.EISA_DIAG_PUSH_INTERVAL_SEC, 120),
  verifyTls:                readBool(process.env.EISA_VERIFY_TLS, true),
  devMode,
  host:                     process.env.EISA_HOST || '127.0.0.1',
  port:                     readInt(process.env.EISA_PORT, 8765),
  // Loglama — dosya yerine JSON stdout.
  serviceName,
  appEnv,
  appVersion,
  logLevel,
  logFormat,
  pretty:                   prettyLogs,
  outboxMaxRows:            readInt(process.env.EISA_OUTBOX_MAX_ROWS, 10000),
  diagnosticMaxRows:        readInt(process.env.EISA_DIAG_MAX_ROWS,    5000),
  diagnosticMaxAgeDays:     readInt(process.env.EISA_DIAG_MAX_AGE_DAYS,   7),
  diagnosticBatchSize:      readInt(process.env.EISA_DIAG_BATCH_SIZE,   100),
});

