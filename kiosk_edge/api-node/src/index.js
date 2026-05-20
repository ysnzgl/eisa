// E-İSA Kiosk API — entrypoint.
import { settings } from './config.js';
import { openDb, closeDb } from './db.js';
import { buildServer } from './server.js';
import { startScheduler, stopScheduler, pullFromCentral } from './scheduler.js';

const db = openDb(settings.sqlitePath, { outboxMaxRows: settings.outboxMaxRows });

const app = await buildServer({ db, settings });
startScheduler(db, settings, app.log);

// İlk açılışta veri yoksa (boş DB) backend'den hemen çek.
const isEmpty = !db.prepare('SELECT 1 FROM kategoriler LIMIT 1').get();
if (isEmpty) {
  app.log.info('DB bos — backend\'den ilk veri cekiliyor…');
  pullFromCentral(db, settings, app.log).catch((err) =>
    app.log.warn({ err: err?.message }, 'Ilk pull basarisiz, scheduler tekrar deneyecek'),
  );
}

try {
  await app.listen({ host: settings.host, port: settings.port });
} catch (err) {
  app.log.error(err);
  process.exit(1);
}

async function shutdown(signal) {
  app.log.info(`${signal} alındı, kapatılıyor…`);
  try {
    stopScheduler();
    await app.close();
    closeDb();
  } finally {
    process.exit(0);
  }
}

process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));
