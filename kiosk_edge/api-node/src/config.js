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

const central = process.env.EISA_CENTRAL_API_BASE || 'https://api.e-isa.local';
const appKey = process.env.EISA_KIOSK_APP_KEY || '';
const mac = process.env.EISA_KIOSK_MAC || '';

if (!appKey || !mac) {
  throw new Error(
    'EISA_KIOSK_APP_KEY ve EISA_KIOSK_MAC environment değişkenleri zorunludur.',
  );
}

if (!central.toLowerCase().startsWith('https://')) {
  const isLocal =
    central.startsWith('http://localhost') ||
    central.startsWith('http://127.0.0.1');
  if (!isLocal) {
    throw new Error('EISA_CENTRAL_API_BASE üretimde HTTPS olmalıdır.');
  }
}

export const settings = Object.freeze({
  sqlitePath: process.env.EISA_SQLITE_PATH || '/var/lib/eisa/local.db',
  centralApiBase: central,
  kioskAppKey: appKey,
  kioskMac: mac,
  // QR payload için kiosk kimlik bilgileri (provizyonda set edilir).
  kioskId: readInt(process.env.EISA_KIOSK_ID, 0),
  pharmacyId: readInt(process.env.EISA_PHARMACY_ID, 0),
  // Termal yazıcı (opsiyonel — TCP raw 9100). Tanımsızsa fiş basılmaz.
  thermalPrinterHost: process.env.EISA_THERMAL_PRINTER_HOST || '',
  thermalPrinterPort: readInt(process.env.EISA_THERMAL_PRINTER_PORT, 9100),
  localApiSecret: process.env.EISA_LOCAL_API_SECRET || '',
  pullIntervalSec: readInt(process.env.EISA_PULL_INTERVAL_SEC, 900),
  pushIntervalSec: readInt(process.env.EISA_PUSH_INTERVAL_SEC, 300),
  verifyTls: readBool(process.env.EISA_VERIFY_TLS, true),
  devMode: readBool(process.env.EISA_DEV_MODE, false),
  host: process.env.EISA_HOST || '127.0.0.1',
  port: readInt(process.env.EISA_PORT, 8765),
  // Log dosyası yolu — kiosk eMMC dolmasın diye pino-roll ile rotate edilir.
  logDir: process.env.EISA_LOG_DIR || '/var/log/eisa',
  logLevel: process.env.EISA_LOG_LEVEL || 'info',
  // 5 MB üst sınır, en fazla 3 dosya saklanır (≈15 MB).
  logMaxSizeMb: readInt(process.env.EISA_LOG_MAX_SIZE_MB, 5),
  logMaxFiles: readInt(process.env.EISA_LOG_MAX_FILES, 3),
  // SQLite outbox FIFO koruması — eşik aşılırsa en eski kayıtlar silinir.
  outboxMaxRows: readInt(process.env.EISA_OUTBOX_MAX_ROWS, 10000),
});
