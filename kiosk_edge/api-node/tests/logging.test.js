import { describe, it, expect, beforeEach } from 'vitest';
import { buildServer } from '../src/server.js';
import { makeMemoryDb, fakeSettings } from './helpers.js';
import { CORRELATION_HEADER_PRETTY, newCorrelationId, sanitizeIncoming } from '../src/correlationId.js';
import { recordDiagnostic, fetchPendingDiagnostics } from '../src/diagnosticOutbox.js';
import { sanitize } from '../src/logRedaction.js';

function extendDbForDiagnostic(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS diagnostic_outbox (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      level TEXT NOT NULL,
      event TEXT NOT NULL,
      message TEXT NOT NULL DEFAULT '',
      context_json TEXT NOT NULL DEFAULT '{}',
      correlation_id TEXT,
      retry_count INTEGER NOT NULL DEFAULT 0,
      next_retry_at TEXT,
      sent_at TEXT
    );
  `);
}

async function makeApp() {
  const db = makeMemoryDb();
  extendDbForDiagnostic(db);
  // Loglama capture icin en dusuk seviye
  const app = await buildServer({ db, settings: { ...fakeSettings, logLevel: 'debug' }, logger: { level: 'silent' } });
  return { app, db };
}

describe('logRedaction.sanitize', () => {
  it('masks known sensitive keys case-insensitively', () => {
    const cleaned = sanitize({ Authorization: 'Bearer x', COOKIE: 'y', safe: 'z' });
    expect(cleaned.Authorization).toBe('***');
    expect(cleaned.COOKIE).toBe('***');
    expect(cleaned.safe).toBe('z');
  });

  it('recursively sanitizes nested structures', () => {
    const cleaned = sanitize({ nested: { token: 'x', ok: 'y' }, list: [{ password: 'p' }] });
    expect(cleaned.nested.token).toBe('***');
    expect(cleaned.nested.ok).toBe('y');
    expect(cleaned.list[0].password).toBe('***');
  });

  it('truncates very long strings', () => {
    const long = 'a'.repeat(3000);
    const cleaned = sanitize({ note: long });
    expect(cleaned.note.length).toBeLessThan(long.length);
  });
});

describe('correlationId helpers', () => {
  it('sanitizeIncoming rejects unsafe values', () => {
    expect(sanitizeIncoming('')).toBeNull();
    expect(sanitizeIncoming(null)).toBeNull();
    expect(sanitizeIncoming('bad value!!')).toBeNull();
    expect(sanitizeIncoming('x'.repeat(200))).toBeNull();
  });

  it('sanitizeIncoming accepts uuid-like strings', () => {
    const cid = newCorrelationId();
    expect(sanitizeIncoming(cid)).toBe(cid);
  });
});

describe('diagnostic outbox', () => {
  it('rejects INFO/DEBUG levels', () => {
    const db = makeMemoryDb();
    extendDbForDiagnostic(db);
    expect(recordDiagnostic(db, { level: 'INFO', event: 'foo' })).toBe(false);
    expect(recordDiagnostic(db, { level: 'DEBUG', event: 'bar' })).toBe(false);
    expect(fetchPendingDiagnostics(db)).toHaveLength(0);
  });

  it('accepts WARNING and above; rate limits duplicates', () => {
    const db = makeMemoryDb();
    extendDbForDiagnostic(db);
    expect(recordDiagnostic(db, { level: 'ERROR', event: 'x', message: 'boom' })).toBe(true);
    // Ayni event kisa surede tekrar eklenmez.
    expect(recordDiagnostic(db, { level: 'ERROR', event: 'x', message: 'boom' })).toBe(false);
    const pending = fetchPendingDiagnostics(db);
    expect(pending).toHaveLength(1);
    expect(pending[0].event).toBe('x');
  });

  it('sanitizes context values before storing', () => {
    const db = makeMemoryDb();
    extendDbForDiagnostic(db);
    recordDiagnostic(db, {
      level: 'ERROR',
      event: 'unique_ctx',
      message: 'ctx test',
      context: { token: 'SECRET', ok: 'yes' },
    });
    const pending = fetchPendingDiagnostics(db);
    const ctx = pending[0].context;
    expect(ctx.token).toBe('***');
    expect(ctx.ok).toBe('yes');
  });
});

describe('Fastify server: correlation + client log', () => {
  let app, db;
  beforeEach(async () => { ({ app, db } = await makeApp()); });

  it('emits X-Correlation-ID header on every response', async () => {
    const r = await app.inject({ method: 'GET', url: '/health' });
    expect(r.statusCode).toBe(200);
    const cid = r.headers[CORRELATION_HEADER_PRETTY.toLowerCase()];
    expect(cid).toBeTruthy();
    expect(cid.length).toBeGreaterThan(8);
  });

  it('preserves incoming X-Correlation-ID', async () => {
    const provided = newCorrelationId();
    const r = await app.inject({
      method: 'GET',
      url: '/health',
      headers: { [CORRELATION_HEADER_PRETTY]: provided },
    });
    expect(r.headers[CORRELATION_HEADER_PRETTY.toLowerCase()]).toBe(provided);
  });

  it('POST /api/log/client stores allowed events in diagnostic outbox', async () => {
    const r = await app.inject({
      method: 'POST',
      url: '/api/log/client',
      payload: {
        level: 'ERROR',
        event: 'screen_render_failed',
        message: 'Boom',
        stack: 'at UI\n  at line',
        component: 'ResultScreen',
        route: '/result',
      },
    });
    expect(r.statusCode).toBe(202);
    const body = r.json();
    expect(body.durum).toBe('kaydedildi');
    expect(body.correlation_id).toBeTruthy();

    const pending = fetchPendingDiagnostics(db);
    expect(pending).toHaveLength(1);
    expect(pending[0].event).toBe('screen_render_failed');
    expect(pending[0].level).toBe('ERROR');
  });

  it('POST /api/log/client rejects unknown level with 422', async () => {
    const r = await app.inject({
      method: 'POST',
      url: '/api/log/client',
      payload: { level: 'CHATTY', event: 'x', message: 'y' },
    });
    expect(r.statusCode).toBe(422);
  });
});
