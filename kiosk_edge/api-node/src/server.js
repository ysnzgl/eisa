// E-İSA Kiosk Lokal API — Fastify uygulaması.
// Svelte UI yalnızca bu API ile (localhost:8765) konuşur. Offline-First.
import crypto from 'node:crypto';
import Fastify from 'fastify';
import cors from '@fastify/cors';
import { rowToCampaign, rowToCategory, rowToQuestion, safeJson } from './db.js';
import {
  ALLOWED_AGE_RANGES,
  ALLOWED_GENDERS,
  QR_RE,
  adImpressionSchema,
  sessionSubmitSchema,
} from './validators.js';
import { requireLocalSecret } from './auth.js';
import { encodeQrCode } from './qrBitpack.js';
import { printReceipt } from './printer.js';
import { buildLoggerOptions } from './logger.js';

/**
 * @param {object} opts
 * @param {import('better-sqlite3').Database} opts.db
 * @param {object} opts.settings
 */
export async function buildServer({ db, settings, logger }) {
  // Logger: çağıran taraf override edebilir; aksi hâlde config'ten dosya rotasyonlu pino kur.
  const loggerOption = logger ?? buildLoggerOptions(settings);
  const app = Fastify({ logger: loggerOption });

  await app.register(cors, {
    origin: ['http://localhost', 'http://127.0.0.1', 'http://localhost:5173'],
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
    allowedHeaders: '*',
  });

  // ── helpers ────────────────────────────────────────────────────────────
  function fail(reply, status, detail) {
    return reply.code(status).send({ detail });
  }

  function parseBody(schema, body, reply) {
    const result = schema.safeParse(body ?? {});
    if (!result.success) {
      const first = result.error.issues[0];
      reply.code(422).send({
        detail: [
          {
            loc: first.path,
            msg: first.message,
            type: first.code,
          },
        ],
      });
      return null;
    }
    return result.data;
  }

  // ── health ─────────────────────────────────────────────────────────────
  app.get('/health', async () => ({ status: 'ok' }));

  // ── categories ─────────────────────────────────────────────────────────
  app.get('/api/categories', async () => {
    const rows = db
      .prepare(
        'SELECT id, slug, name, icon, is_sensitive, is_active FROM categories WHERE is_active = 1 ORDER BY id',
      )
      .all();
    return rows.map((r) => ({
      id: r.id,
      slug: r.slug,
      name: r.name,
      icon: r.icon,
      is_sensitive: !!r.is_sensitive,
    }));
  });

  app.get('/api/categories/:slug/questions', async (req, reply) => {
    const { slug } = req.params;
    const cat = db.prepare('SELECT id FROM categories WHERE slug = ?').get(slug);
    if (!cat) return fail(reply, 404, 'Kategori bulunamadı');

    const rows = db
      .prepare(
        `SELECT id, seed_id, text, priority, match_rules
         FROM questions WHERE category_id = ? ORDER BY priority`,
      )
      .all(cat.id);
    return rows.map((r) => ({
      id: r.id,
      seed_id: r.seed_id,
      text: r.text,
      priority: r.priority,
      match_rules: safeJson(r.match_rules, []),
    }));
  });

  // ── session ────────────────────────────────────────────────────────────
  app.post('/api/session/submit', async (req, reply) => {
    const body = parseBody(sessionSubmitSchema, req.body, reply);
    if (!body) return;

    const qr = body.qr_code || crypto.randomBytes(6).toString('hex').toUpperCase();
    const createdAt = new Date().toISOString();
    const payload = {
      age_range: body.age_range,
      gender: body.gender,
      category_slug: body.category_slug,
      is_sensitive_flow: body.is_sensitive_flow,
      qr_code: qr,
      answers_payload: body.answers_payload,
      suggested_ingredients: body.suggested_ingredients,
      created_at: createdAt,
    };

    db.prepare('INSERT INTO session_log_outbox (payload) VALUES (?)').run(
      JSON.stringify(payload),
    );

    // 41-bit bitpack QR payload — offline okunabilir, 8 karakter Base36.
    let qrPayload = qr;
    try {
      const catRow = db.prepare('SELECT id FROM categories WHERE slug = ?').get(body.category_slug);
      const yCount = Object.values(body.answers_payload ?? {}).filter(v => v === 'Y').length;
      qrPayload = encodeQrCode({
        pharmacyId: Math.min(settings.pharmacyId || 0, 32767),
        kioskId:    Math.min(settings.kioskId    || 0,    15),
        categoryId: Math.min(catRow?.id          ?? 0,   127),
        qaCombo:    Math.min(yCount,                       63),
        productId:  0,
      });
    } catch (err) {
      app.log.warn({ err: err.message }, 'QR payload oluşturulamadı, düz kod kullanılıyor');
    }

    // Termal yazıcı (opsiyonel, fire-and-forget).
    try {
      printReceipt({
        qrCode: qr,
        qrPayload,
        categoryName: body.category_slug,
        ingredients: body.suggested_ingredients,
        isSensitive: body.is_sensitive_flow,
        host: settings.thermalPrinterHost,
        port: settings.thermalPrinterPort,
        logger: app.log,
      });
    } catch (err) {
      app.log.warn({ err: err.message }, 'Termal yazıcı tetiklenemedi');
    }

    return { qr_code: qr, qr_payload: qrPayload, status: 'saved' };
  });

  app.get(
    '/api/session/*',
    { preHandler: requireLocalSecret(settings.localApiSecret) },
    async (req, reply) => {
      const qrCode = req.params['*'];
      if (!qrCode || qrCode.length > 256 || !QR_RE.test(qrCode)) {
        return fail(reply, 400, 'Geçersiz QR kodu');
      }

      const row = db
        .prepare(
          `SELECT payload FROM session_log_outbox
           WHERE json_extract(payload, '$.qr_code') = ?
           LIMIT 1`,
        )
        .get(qrCode);

      if (!row) return fail(reply, 404, 'QR koda ait oturum bulunamadı');

      return { found: true, session: JSON.parse(row.payload) };
    },
  );

  // ── campaigns ──────────────────────────────────────────────────────────
  app.get('/api/campaigns/active', async () => {
    const now = new Date();
    const rows = db
      .prepare(
        `SELECT id, name, media_local_path, starts_at, ends_at, targeting
         FROM campaigns WHERE is_active = 1`,
      )
      .all();

    const out = [];
    for (const r of rows) {
      const starts = new Date(r.starts_at);
      const ends = new Date(r.ends_at);
      if (!(starts <= now && now <= ends)) continue;

      const targeting = safeJson(r.targeting, {});
      const hs = targeting.hours_start;
      const he = targeting.hours_end;
      if (hs != null && he != null) {
        const h = now.getHours();
        if (!(h >= hs && h < he)) continue;
      }
      out.push({
        id: r.id,
        name: r.name,
        media_local_path: r.media_local_path,
        targeting,
      });
    }
    return out;
  });

  // ── ad impression ──────────────────────────────────────────────────────
  app.post('/api/ad-impression', async (req, reply) => {
    const body = parseBody(adImpressionSchema, req.body, reply);
    if (!body) return;
    db.prepare('INSERT INTO ad_impression_outbox (payload) VALUES (?)').run(
      JSON.stringify({
        campaign_id: body.campaign_id,
        shown_at: body.shown_at,
        duration_ms: body.duration_ms,
      }),
    );
    reply.code(201);
    return { status: 'logged' };
  });

  // suppress unused import warning (re-export helpers if needed)
  void rowToCampaign;
  void rowToCategory;
  void rowToQuestion;
  void ALLOWED_AGE_RANGES;
  void ALLOWED_GENDERS;

  return app;
}
