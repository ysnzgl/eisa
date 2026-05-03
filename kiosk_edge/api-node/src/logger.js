// Fastify (pino) için dosya bazlı, rotasyonlu logger.
// Kiosk diski (16/32 GB eMMC) dolmasın diye:
//   - Tek dosya en fazla `logMaxSizeMb` MB (varsayılan 5 MB)
//   - En fazla `logMaxFiles` dosya saklanır (varsayılan 3) → eskiler otomatik silinir
//   - Stdout'a da yazılır (development / systemd journal için)
import path from 'node:path';
import fs from 'node:fs';
import pino from 'pino';

/**
 * @param {object} settings — config.js çıktısı
 * @returns {import('pino').LoggerOptions | import('pino').Logger | object} Fastify `logger` opsiyonu
 */
export function buildLoggerOptions(settings) {
  // Dev modda renkli, tek satır insan-okur log; üretimde JSON + dosyaya rotate.
  if (settings.devMode) {
    return {
      level: settings.logLevel,
      transport: {
        target: 'pino-pretty',
        options: { translateTime: 'SYS:HH:MM:ss', singleLine: true },
      },
    };
  }

  try {
    fs.mkdirSync(settings.logDir, { recursive: true });
  } catch {
    // Yetkisiz/okunaksız dizinde uygulamayı çökertme; stdout fallback.
    return { level: settings.logLevel };
  }

  const logFile = path.join(settings.logDir, 'kiosk-api.log');
  const sizeLimit = `${Math.max(1, settings.logMaxSizeMb)}m`;
  const limit = { count: Math.max(1, settings.logMaxFiles) };

  // pino-roll: boyut tabanlı rotasyon + tutulacak dosya sayısı.
  // mkdir: true → dizin yoksa oluştur. limit.count → en eski dosyaları sil.
  return {
    level: settings.logLevel,
    transport: {
      targets: [
        {
          target: 'pino-roll',
          level: settings.logLevel,
          options: {
            file: logFile,
            frequency: 'daily',  // günlük + boyut sınırı; ikisinden biri tetiklendiğinde rotate.
            size: sizeLimit,
            limit,
            mkdir: true,
            dateFormat: 'yyyy-MM-dd',
          },
        },
        {
          target: 'pino/file',
          level: 'info',
          options: { destination: 1 }, // stdout
        },
      ],
    },
  };
}
