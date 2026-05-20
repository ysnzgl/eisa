// E-ISA Kiosk Lokal API — Fastify uygulamasi (Turkce sema).
// Svelte UI yalnizca bu API ile (localhost:8765) konusur. Offline-First.
import crypto from 'node:crypto';
import Fastify from 'fastify';
import cors from '@fastify/cors';
import { rowToKategori, rowToDanismaKategori, rowToSoru, safeJson } from './db.js';
import {
  ALLOWED_YAS_ARALIKLARI,
  ALLOWED_CINSIYETLER,
  QR_RE,
  reklamGosterimSchema,
  oturumGonderSchema,
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
  const loggerOption = logger ?? buildLoggerOptions(settings);
  const app = Fastify({ logger: loggerOption });

  await app.register(cors, {
    origin: (origin, cb) => {
      // Allow any localhost / 127.0.0.1 origin regardless of port (dev kiosk UI)
      if (!origin || /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin)) {
        cb(null, true);
      } else {
        cb(new Error('CORS: not allowed'), false);
      }
    },
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
        detail: [{ loc: first.path, msg: first.message, type: first.code }],
      });
      return null;
    }
    return result.data;
  }

  // ── health ─────────────────────────────────────────────────────────────
  app.get('/health', async () => ({ status: 'ok' }));

  // ── lookup'lar (UI demografi ekrani icin) ──────────────────────────────
  app.get('/api/lookups/yas-araliklari', async () => {
    return db
      .prepare('SELECT id, kod, ad, alt_sinir, ust_sinir FROM yas_araliklari ORDER BY id')
      .all();
  });

  app.get('/api/lookups/cinsiyetler', async () => {
    return db.prepare('SELECT id, kod, ad FROM cinsiyetler ORDER BY id').all();
  });

  app.get('/api/lookups/iller', async () => {
    return db.prepare('SELECT id, ad FROM iller ORDER BY ad').all();
  });

  app.get('/api/lookups/iller/:ilId/ilceler', async (req) => {
    return db
      .prepare('SELECT id, il_id, ad FROM ilceler WHERE il_id = ? ORDER BY ad')
      .all(req.params.ilId);
  });

  // ── kategoriler ────────────────────────────────────────────────────────
  app.get('/api/kategoriler', async () => {
    const rows = db
      .prepare(
        `SELECT id, slug, ad, ikon, bagli_kategori_id, aktif,
                hedef_cinsiyetler, hedef_yas_araliklari
           FROM kategoriler WHERE aktif = 1 ORDER BY id`,
      )
      .all();
    return rows.map((r) => ({
      id: r.id,
      slug: r.slug,
      ad: r.ad,
      ikon: r.ikon,
      bagli_kategori_id: r.bagli_kategori_id ?? null,
      hedef_cinsiyetler: safeJson(r.hedef_cinsiyetler, []),
      hedef_yas_araliklari: safeJson(r.hedef_yas_araliklari, []),
    }));
  });

  app.get('/api/danisma-kategorileri', async () => {
    const rows = db
      .prepare(
        `SELECT id, slug, ad, ikon, ust_kategori_id, aktif
           FROM danisma_kategorileri WHERE aktif = 1 ORDER BY id`,
      )
      .all();
    const toplevel = rows.filter((r) => r.ust_kategori_id === null);
    return toplevel.map((parent) => ({
      id: parent.id,
      slug: parent.slug,
      ad: parent.ad,
      ikon: parent.ikon,
      alt_kategoriler: rows
        .filter((r) => r.ust_kategori_id === parent.id)
        .map((c) => ({ id: c.id, slug: c.slug, ad: c.ad, ikon: c.ikon })),
    }));
  });

  app.get('/api/kategoriler/:slug/sorular', async (req, reply) => {
    const { slug } = req.params;
    const cat = db.prepare('SELECT id FROM kategoriler WHERE slug = ?').get(slug);
    if (!cat) return fail(reply, 404, 'Kategori bulunamadi');

    const rows = db
      .prepare(
        `SELECT id, seed_id, metin, sira, eslesme_kurallari,
                hedef_cinsiyetler, hedef_yas_araliklari
           FROM sorular WHERE kategori_id = ? ORDER BY sira`,
      )
      .all(cat.id);
    return rows.map((r) => ({
      id: r.id,
      seed_id: r.seed_id,
      metin: r.metin,
      sira: r.sira,
      eslesme_kurallari: safeJson(r.eslesme_kurallari, []),
      hedef_cinsiyetler: safeJson(r.hedef_cinsiyetler, []),
      hedef_yas_araliklari: safeJson(r.hedef_yas_araliklari, []),
    }));
  });

  // ── oturum gonder ──────────────────────────────────────────────────────
  app.post('/api/oturum/gonder', async (req, reply) => {
    const body = parseBody(oturumGonderSchema, req.body, reply);
    if (!body) return;

    const qr = body.qr_kodu || crypto.randomBytes(6).toString('hex').toUpperCase();
    const olusturulmaTarihi = new Date().toISOString();
    const idempotencyAnahtari = crypto.randomUUID();

    // Backend `OturumLoguItemSerializer` ile birebir uyumlu payload.
    const payload = {
      idempotency_anahtari: idempotencyAnahtari,
      kiosk_mac: settings.kioskMac,
      yas_araligi_kod: body.yas_araligi_kod,
      cinsiyet_kod: body.cinsiyet_kod,
      kategori_slug: body.kategori_slug,
      hassas_akis: body.hassas_akis,
      qr_kodu: qr,
      cevaplar: body.cevaplar,
      onerilen_etken_maddeler: body.onerilen_etken_maddeler,
      olusturulma_tarihi: olusturulmaTarihi,
    };

    db.prepare(
      'INSERT INTO oturum_outbox (idempotency_anahtari, payload) VALUES (?, ?)',
    ).run(idempotencyAnahtari, JSON.stringify(payload));

    // 41-bit bitpack QR payload — offline okunabilir, 8 karakter Base36.
    let qrPayload = qr;
    try {
      const catRow = db.prepare('SELECT id FROM kategoriler WHERE slug = ?').get(body.kategori_slug);
      const yCount = Object.values(body.cevaplar ?? {}).filter((v) => v === 'Y').length;
      qrPayload = encodeQrCode({
        pharmacyId: Math.min(settings.pharmacyId || 0, 32767),
        kioskId:    Math.min(settings.kioskId    || 0,    15),
        categoryId: Math.min(catRow?.id          ?? 0,   127),
        qaCombo:    Math.min(yCount,                       63),
        productId:  0,
      });
    } catch (err) {
      app.log.warn({ err: err.message }, 'QR payload olusturulamadi, duz kod kullaniliyor');
    }

    // Termal yazici (opsiyonel).
    let printerOk = true;
    let printerError = null;
    try {
      printReceipt({
        qrCode: qr,
        qrPayload,
        categoryName: body.kategori_slug,
        ingredients: body.onerilen_etken_maddeler,
        isSensitive: body.hassas_akis,
        host: settings.thermalPrinterHost,
        port: settings.thermalPrinterPort,
        logger: app.log,
      });
    } catch (err) {
      printerOk = false;
      printerError = err?.message || 'Yazici hatasi';
      app.log.warn({ err: printerError }, 'Termal yazici tetiklenemedi');
    }

    return {
      qr_kodu: qr,
      qr_payload: qrPayload,
      durum: 'kaydedildi',
      yazici_ok: printerOk,
      ...(printerError ? { yazici_hatasi: printerError } : {}),
    };
  });

  // ── eczaci sorgulamasi (yerel sirla korunur) ───────────────────────────
  app.get(
    '/api/oturum/*',
    { preHandler: requireLocalSecret(settings.localApiSecret) },
    async (req, reply) => {
      const qrCode = req.params['*'];
      if (!qrCode || qrCode.length > 256 || !QR_RE.test(qrCode)) {
        return fail(reply, 400, 'Gecersiz QR kodu');
      }

      const row = db
        .prepare(
          `SELECT payload FROM oturum_outbox
            WHERE json_extract(payload, '$.qr_kodu') = ?
            LIMIT 1`,
        )
        .get(qrCode);

      if (!row) return fail(reply, 404, 'QR koda ait oturum bulunamadi');
      return { bulundu: true, oturum: JSON.parse(row.payload) };
    },
  );

  // ── reklamlar / DOOH assets (geriye dönük uyumluluk) ─────────────────────
  app.get('/api/reklamlar/aktif', async () => {
    const creatives = db
      .prepare('SELECT id, media_url, duration_seconds, type FROM creatives WHERE aktif = 1')
      .all();
    const houseAds = db
      .prepare('SELECT id, name, media_url, duration_seconds, type FROM house_ads WHERE aktif = 1')
      .all();
    return [
      ...creatives.map((c) => ({ id: c.id, media_url: c.media_url, duration_seconds: c.duration_seconds, type: c.type })),
      ...houseAds.map((h) => ({ id: h.id, name: h.name, media_url: h.media_url, duration_seconds: h.duration_seconds, type: h.type })),
    ];
  });

  // ── playlist — bugünün aktif saati için sıralı oynatma listesi ──────────
  /**
   * GET /api/playlist/current?hour=<0-23>
   *
   * hour verilmezse şu anki saat kullanılır.
   * Playlist yoksa → fallback: /api/reklamlar/aktif ile aynı veri.
   *
   * Döner:
   *   { version, target_date, target_hour, loop_duration_seconds, items: [...] }
   */
  app.get('/api/playlist/current', async (req) => {
    const now     = new Date();
    const today   = now.toISOString().slice(0, 10);
    const hour    = req.query.hour !== undefined
      ? parseInt(req.query.hour, 10)
      : now.getUTCHours();

    const playlist = db
      .prepare('SELECT * FROM playlists WHERE target_date = ? AND target_hour = ?')
      .get(today, hour);

    if (!playlist) {
      // Fallback: yapılandırılmamış tüm asset'ler
      const creatives = db
        .prepare('SELECT id, media_url, duration_seconds, type FROM creatives WHERE aktif = 1')
        .all();
      const houseAds  = db
        .prepare('SELECT id, name, media_url, duration_seconds, type FROM house_ads WHERE aktif = 1')
        .all();
      const fallbackItems = [
        ...creatives.map((c, i) => ({
          id: `fallback-c-${c.id}`,
          playback_order: i,
          asset_id: c.id,
          asset_type: 'creative',
          media_url: c.media_url,
          duration_seconds: c.duration_seconds,
          estimated_start_offset_seconds: 0,
        })),
        ...houseAds.map((h, i) => ({
          id: `fallback-h-${h.id}`,
          playback_order: creatives.length + i,
          asset_id: h.id,
          asset_type: 'house_ad',
          media_url: h.media_url,
          duration_seconds: h.duration_seconds,
          estimated_start_offset_seconds: 0,
        })),
      ];
      return {
        version: 0,
        target_date: today,
        target_hour: hour,
        loop_duration_seconds: 60,
        is_fallback: true,
        items: fallbackItems,
      };
    }

    const items = db
      .prepare(
        `SELECT id, playback_order, asset_id, asset_type,
                media_url, duration_seconds, estimated_start_offset_seconds
           FROM playlist_items
          WHERE playlist_id = ?
          ORDER BY playback_order`,
      )
      .all(playlist.id);

    return {
      version: playlist.version,
      target_date: playlist.target_date,
      target_hour: playlist.target_hour,
      loop_duration_seconds: playlist.loop_duration_seconds,
      is_fallback: false,
      items,
    };
  });

  // ── reklam gosterim (proof-of-play) ──────────────────────────────────────
  app.post('/api/reklam-gosterim', async (req, reply) => {
    const body = parseBody(reklamGosterimSchema, req.body, reply);
    if (!body) return;
    db.prepare(
      'INSERT INTO reklam_gosterim_outbox (payload) VALUES (?)',
    ).run(
      JSON.stringify({
        asset_id: body.asset_id,
        asset_type: body.asset_type,
        played_at: body.played_at,
        duration_played: body.duration_played,
      }),
    );
    reply.code(201);
    return { durum: 'kaydedildi' };
  });

  // unused-import suppression
  void rowToKategori;
  void rowToSoru;
  void ALLOWED_YAS_ARALIKLARI;
  void ALLOWED_CINSIYETLER;

  return app;
}
