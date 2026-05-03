// E-İSA Kiosk API — entrypoint.
import { settings } from './config.js';
import { openDb, closeDb } from './db.js';
import {
  seedLookupsIfEmpty,
  seedKategorilerIfEmpty,
  seedReklamlarIfEmpty,
} from './seed.js';
import { buildServer } from './server.js';
import { startScheduler, stopScheduler } from './scheduler.js';

const db = openDb(settings.sqlitePath, { outboxMaxRows: settings.outboxMaxRows });
seedLookupsIfEmpty(db);
seedKategorilerIfEmpty(db);
seedReklamlarIfEmpty(db);

const app = await buildServer({ db, settings });
startScheduler(db, settings, app.log);

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
