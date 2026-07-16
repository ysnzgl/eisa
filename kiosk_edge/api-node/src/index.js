// E-İSA Kiosk API — entrypoint.
import { settings } from './config.js';
import { openDb, closeDb } from './db.js';
import { buildServer } from './server.js';
import { startScheduler, stopScheduler, pullFromCentral } from './scheduler.js';
import { resolveRuntimeSettings } from './provisioning.js';
import { recordDiagnostic } from './diagnosticOutbox.js';

const db = openDb(settings.sqlitePath, {
  outboxMaxRows: settings.outboxMaxRows,
  diagnosticMaxRows: settings.diagnosticMaxRows,
});
const runtimeSettings = await resolveRuntimeSettings(db, settings, console);

const app = await buildServer({ db, settings: runtimeSettings });
startScheduler(db, runtimeSettings, app.log);

// İlk açılışta veri yoksa (boş DB) backend'den hemen çek.
const isEmpty = !db.prepare('SELECT 1 FROM kategoriler LIMIT 1').get();
if (isEmpty) {
  app.log.info({ event: 'first_pull_triggered' }, 'DB bos — backend\'den ilk veri cekiliyor');
  pullFromCentral(db, runtimeSettings, app.log).catch((err) =>
    app.log.warn({ event: 'first_pull_failed', err: err?.message }, 'Ilk pull basarisiz, scheduler tekrar deneyecek'),
  );
}

try {
  await app.listen({ host: settings.host, port: settings.port });
  app.log.info({ event: 'service_started', host: settings.host, port: settings.port }, 'Kiosk API hazir');
} catch (err) {
  app.log.error({ event: 'service_start_failed', err: err?.message }, 'Kiosk API baslatilamadi');
  process.exit(1);
}

// ── Global hata yakalayicilar (uncaught → JSON log + diagnostic outbox) ─────
process.on('uncaughtException', (err) => {
  try {
    app.log.error({ event: 'uncaught_exception', err: err?.message, stack: err?.stack }, 'Uncaught exception');
    recordDiagnostic(db, {
      level: 'CRITICAL',
      event: 'uncaught_exception',
      message: err?.message || 'uncaught_exception',
      context: { stack: (err?.stack || '').slice(0, 4096) },
    });
  } catch { /* logger arizasi da uygulamayi durdurmasin */ }
});
process.on('unhandledRejection', (reason) => {
  const message = reason instanceof Error ? reason.message : String(reason);
  try {
    app.log.error({ event: 'unhandled_rejection', reason: message }, 'Unhandled promise rejection');
    recordDiagnostic(db, {
      level: 'ERROR',
      event: 'unhandled_rejection',
      message,
    });
  } catch { /* sessiz */ }
});

async function shutdown(signal) {
  app.log.info({ event: 'service_shutdown', signal }, `${signal} alindi, kapatiliyor`);
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

