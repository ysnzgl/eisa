// E-ISA Kiosk Lokal API â€” Fastify uygulamasi (Turkce sema).
// Svelte UI yalnizca bu API ile (localhost:8765) konusur. Offline-First.
import crypto from 'node:crypto';
import fs from 'node:fs';
import Fastify from 'fastify';
import cors from '@fastify/cors';
import { safeJson } from './db.js';
import {
  QR_RE,
  reklamGosterimSchema,
  oturumGonderSchema,
  clientLogSchema,
} from './validators.js';
import { requireLocalSecret } from './auth.js';
import { encodeQrCode } from './qrBitpack.js';
import { printReceipt } from './printer.js';
import { buildLoggerOptions } from './logger.js';
import {
  CORRELATION_HEADER,
  CORRELATION_HEADER_PRETTY,
  newCorrelationId,
  runWithCorrelation,
  sanitizeIncoming,
} from './correlationId.js';
import { recordDiagnostic } from './diagnosticOutbox.js';
import { getWifiStatus, scanWifi, connectWifi } from './wifi.js';
import { buildMediaUrl, getLocalMediaMeta } from './mediaCache.js';
import { istanbulNow } from './timezone.js';
import { requestWithRetry } from './scheduler.js';
import { handle401Error, handle403Error, hasAppKeyCredentials } from './provisioning.js';

/**
 * @param {object} opts
 * @param {import('better-sqlite3').Database} opts.db
 * @param {object} opts.settings
 */
export async function buildServer({ db, settings, logger }) {
  const loggerOption = logger ?? buildLoggerOptions(settings);
  const app = Fastify({
    logger: loggerOption,
    // Fastify istek ID'sini uretirken bizim correlation degerimizi kullansin.
    genReqId(req) {
      const incoming = sanitizeIncoming(req.headers[CORRELATION_HEADER]);
      return incoming || newCorrelationId();
    },
    disableRequestLogging: false,
  });

  // â”€â”€ Korelasyon ID + request-lifecycle hooks â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  app.addHook('onRequest', (req, reply, done) => {
    const cid = req.id;
    reply.header(CORRELATION_HEADER_PRETTY, cid);
    // Her istegi kendi contextvars uzerinde calistir; nested async cagrilar da ayni ID'yi gorur.
    runWithCorrelation(cid, () => {
      req.log = req.log.child({ correlation_id: cid });
      done();
    });
  });

  // Sadece 4xx/5xx icin ek "request_failed" log; basarili istekler Fastify'in
  // varsayilan onResponse loguyla yeterli.
  app.addHook('onResponse', (req, reply, done) => {
    const status = reply.statusCode;
    // Health endpoint gurultusunu azalt.
    if ((req.url === '/health' || req.url === '/healthz') && status < 400) {
      return done();
    }
    if (status >= 500) {
      req.log.error({
        event: 'request_failed',
        request_method: req.method,
        request_path: req.url,
        status_code: status,
      }, 'request_failed');
      recordDiagnostic(db, {
        level: 'ERROR',
        event: 'request_failed',
        message: `HTTP ${status} ${req.method} ${req.url}`,
        context: { status },
        correlationId: req.id,
      });
    }
    done();
  });

  app.setErrorHandler((err, req, reply) => {
    const status = err?.statusCode && err.statusCode >= 400 ? err.statusCode : 500;
    if (status >= 500) {
      req.log.error({ event: 'request_error', err: err?.message, stack: err?.stack }, 'request_error');
      recordDiagnostic(db, {
        level: 'ERROR',
        event: 'request_error',
        message: err?.message || 'request_error',
        context: { status, path: req.url },
        correlationId: req.id,
      });
    }
    reply.code(status).send({
      detail: status >= 500 ? 'Beklenmeyen bir hata olustu.' : (err?.message || 'Hata'),
      correlation_id: req.id,
    });
  });

  await app.register(cors, {
  origin: '*',
  methods: ['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  allowedHeaders: '*',
  exposedHeaders: [CORRELATION_HEADER_PRETTY],
  credentials: false,
  strictPreflight: false,
  optionsSuccessStatus: 204,
});

  // â”€â”€ helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  function fail(reply, status, detail) {
    return reply.code(status).send({ detail });
  }

  const selKategoriYas = db.prepare(
    'SELECT yas_araligi_id FROM kategori_hedef_yas_araliklari WHERE kategori_id = ? ORDER BY yas_araligi_id',
  );
  const selSoruYas = db.prepare(
    'SELECT yas_araligi_id FROM soru_hedef_yas_araliklari WHERE soru_id = ? ORDER BY yas_araligi_id',
  );
  const selSoruEtken = db.prepare(
    `SELECT etken_madde_id, rol
       FROM soru_etken_maddeler
      WHERE soru_id = ?
      ORDER BY etken_madde_id`,
  );

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

  // â”€â”€ health â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  app.get('/health', async () => ({ status: 'ok' }));

  app.get('/api/media/:assetType/:assetId', async (req, reply) => {
    const { assetType, assetId } = req.params;
    if (!['creative', 'house_ad'].includes(assetType)) {
      return fail(reply, 400, 'Gecersiz asset_tipi');
    }
    const media = getLocalMediaMeta(db, assetType, assetId);
    if (!media || media.status !== 'ready' || !media.local_path || !fs.existsSync(media.local_path)) {
      return fail(reply, 404, 'Lokal medya bulunamadi');
    }

    reply.header('Cache-Control', 'public, max-age=3600');
    if (media.mime_type) reply.type(media.mime_type);
    return reply.send(fs.createReadStream(media.local_path));
  });

  // â”€â”€ lookup'lar (UI demografi ekrani icin) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  app.get('/api/lookups/yas-araliklari', async () => {
    return db
      .prepare('SELECT id, kod, ad, alt_sinir, ust_sinir FROM yas_araliklari ORDER BY id')
      .all();
  });

  app.get('/api/lookups/cinsiyetler', async () => {
    return db.prepare('SELECT id, kod, ad FROM cinsiyetler ORDER BY id').all();
  });

  // Not: il/ilce lookup'lari kiosk semasindan kaldirildi (db.js v9); kiosk bu
  // verileri kullanmiyor. Eski /api/lookups/iller* endpoint'leri kaldirildi.

  // â”€â”€ kategoriler â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  app.get('/api/kategoriler', async () => {
    const rows = db
      .prepare(
        `SELECT id, slug, ad, ikon, bagli_kategori_id, aktif,
                hedef_cinsiyet_id, hedef_cinsiyetler, hedef_yas_araliklari
           FROM kategoriler WHERE aktif = 1 ORDER BY id`,
      )
      .all();
    return rows.map((r) => {
      const yasIds = selKategoriYas.all(r.id).map((x) => x.yas_araligi_id);
      const legacyAges = safeJson(r.hedef_yas_araliklari, []);
      const legacyGender = safeJson(r.hedef_cinsiyetler, []);
      return {
        id: r.id,
        slug: r.slug,
        ad: r.ad,
        ikon: r.ikon,
        bagli_kategori_id: r.bagli_kategori_id ?? null,
        hedef_cinsiyet: r.hedef_cinsiyet_id ?? null,
        hedef_cinsiyetler: legacyGender,
        hedef_yas_araliklari: yasIds.length ? yasIds : legacyAges,
      };
    });
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
                hedef_cinsiyet_id, hedef_cinsiyetler, hedef_yas_araliklari
           FROM sorular WHERE kategori_id = ? ORDER BY sira`,
      )
      .all(cat.id);
    return rows.map((r) => {
      const yasIds = selSoruYas.all(r.id).map((x) => x.yas_araligi_id);
      const legacyAges = safeJson(r.hedef_yas_araliklari, []);
      return {
        id: r.id,
        seed_id: r.seed_id,
        metin: r.metin,
        sira: r.sira,
        eslesme_kurallari: safeJson(r.eslesme_kurallari, []),
        hedef_cinsiyet: r.hedef_cinsiyet_id ?? null,
        hedef_cinsiyetler: safeJson(r.hedef_cinsiyetler, []),
        hedef_yas_araliklari: yasIds.length ? yasIds : legacyAges,
        hedef_etken_maddeler: selSoruEtken.all(r.id).map((x) => ({
          etken_madde: x.etken_madde_id,
          rol: x.rol,
        })),
      };
    });
  });

  // â”€â”€ oturum gonder â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  app.post('/api/oturum/gonder', async (req, reply) => {
    const body = parseBody(oturumGonderSchema, req.body, reply);
    if (!body) return;

    const yas = db.prepare('SELECT 1 FROM yas_araliklari WHERE kod = ? LIMIT 1').get(body.yas_araligi_kod);
    if (!yas) return fail(reply, 422, 'Gecersiz yas araligi kodu');

    const cinsiyet = db.prepare('SELECT 1 FROM cinsiyetler WHERE kod = ? LIMIT 1').get(body.cinsiyet_kod);
    if (!cinsiyet) return fail(reply, 422, 'Gecersiz cinsiyet kodu');

    const oturumTipi = body.oturum_tipi || 'SIKAYET';
    let cat = null;
    let danismaKategoriId = null;

    if (oturumTipi === 'SIKAYET') {
      if (!body.kategori_slug) return fail(reply, 422, 'Sikayet icin kategori_slug zorunlu');
      cat = db.prepare('SELECT id FROM kategoriler WHERE slug = ? LIMIT 1').get(body.kategori_slug);
      if (!cat) return fail(reply, 422, 'Gecersiz kategori slug');
    } else if (oturumTipi === 'OZEL_DANISMANLIK') {
      if (!body.danisma_kategorisi_slug && !body.danisma_kategorisi_id) {
        return fail(reply, 422, 'Ozel danismanlik icin danisma_kategorisi_slug zorunlu');
      }
      if (body.cevaplar && Object.keys(body.cevaplar).length > 0) {
        return fail(reply, 422, 'Ozel danismanlik oturumunda cevap bulunmamali');
      }
      if (body.onerilen_etken_maddeler && body.onerilen_etken_maddeler.length > 0) {
        return fail(reply, 422, 'Ozel danismanlik oturumunda etken madde onerisi bulunmamali');
      }
      // Danisma kategorisi ID'sini lokal katalogdan coz (slug → id)
      if (body.danisma_kategorisi_id) {
        danismaKategoriId = body.danisma_kategorisi_id;
      } else {
        const danismaRow = db.prepare(
          'SELECT id FROM danisma_kategorileri WHERE slug = ? AND aktif = 1 LIMIT 1'
        ).get(body.danisma_kategorisi_slug);
        if (!danismaRow) return fail(reply, 422, 'Gecersiz danisma_kategorisi_slug');
        danismaKategoriId = danismaRow.id;
      }
    }

    // 41-bit bitpack QR payload â€” yerel offline-scan meta verisi (opsiyonel).
    // Authoritative QR kodu backend'den gelir; bu deger yalnizca yazici veya
    // QR gorsel encode icin ek bilgi tasir.
    let qrPayload = null;
    try {
      const yCount = Object.values(body.cevaplar ?? {}).filter((v) => v === 'Y').length;
      qrPayload = encodeQrCode({
        pharmacyId: Math.min(settings.pharmacyId || 0, 32767),
        kioskId:    Math.min(settings.kioskId    || 0,    15),
        categoryId: Math.min(cat?.id             ?? 0,   127),
        qaCombo:    Math.min(yCount,                       63),
        productId:  0,
      });
    } catch (err) {
      app.log.warn({ err: err.message }, 'QR bitpack encode basarisiz, sadece backend QR kullanilacak');
    }

    const olusturulmaTarihi = new Date().toISOString();
    // UI'dan gelen kararlı sessionId varsa kullan; yoksa yeni UUID üret.
    // Bu sayede aynı request tekrar geldiğinde aynı idempotency key kullanılır.
    const idempotencyAnahtari = body.idempotency_anahtari
      ? String(body.idempotency_anahtari)
      : crypto.randomUUID();

    // Backend payload — qr_kodu GONDERILMEZ; backend uretir ve response'ta doner.
    // danisma_kategorisi_id: lokal katalogdan cozulmus gercek ID (slug yerine ID tercih edilir).
    const payload = {
      idempotency_anahtari: idempotencyAnahtari,
      kiosk_mac: settings.kioskMac,
      yas_araligi_kod: body.yas_araligi_kod,
      cinsiyet_kod: body.cinsiyet_kod,
      oturum_tipi: oturumTipi,
      kategori_slug: body.kategori_slug || null,
      danisma_kategorisi_id: danismaKategoriId || null,
      danisma_kategorisi_slug: body.danisma_kategorisi_slug || null,
      hassas_akis: body.hassas_akis,
      cevaplar: body.cevaplar,
      onerilen_etken_maddeler: body.onerilen_etken_maddeler,
      tamamlandi: body.tamamlandi,
      olusturulma_tarihi: olusturulmaTarihi,
    };

    // Tamamlanan oturumlar (QR gosterilecek) backend'e aninda iletilmeli.
    // Backend QR uretir ve doner; UI yalniz backend'den gelen QR'i gosterir.
    // Eger backend erisilemazsa UI'a hata doner (sahte QR gosterilmez).
    if (body.tamamlandi) {
      if (!settings.centralApiBase || !hasAppKeyCredentials(db)) {
        return reply.status(503).send({
          error: 'Merkez API yapilandirilmamis veya kimlik bilgisi eksik.',
          code: 'backend_unavailable',
        });
      }

      // 1. Outbox'a ONCE kaydet — bu garantidir; merkez çağrısı başarısız olsa bile kayıt kaybolmaz.
      db.prepare(
        'INSERT OR IGNORE INTO oturum_outbox (idempotency_anahtari, payload) VALUES (?, ?)',
      ).run(idempotencyAnahtari, JSON.stringify(payload));

      // 2. Idempotent yeniden teslim: aynı key daha önce başarıyla gönderilmiş mi?
      const existingRow = db.prepare(
        'SELECT payload, gonderilme_tarihi FROM oturum_outbox WHERE idempotency_anahtari = ?',
      ).get(idempotencyAnahtari);
      if (existingRow?.gonderilme_tarihi) {
        const existingPayload = safeJson(existingRow.payload, {});
        if (existingPayload.qr_kodu) {
          app.log.info({ event: 'session_idempotent_redelivery' }, 'Idempotent yeniden teslim; mevcut QR donuluyor');
          let printerOk = true;
          let printerError = null;
          try {
            printReceipt({
              qrCode: existingPayload.qr_kodu,
              qrPayload: existingPayload.qr_payload || existingPayload.qr_kodu,
              categoryName: body.kategori_slug || body.danisma_kategorisi_slug,
              ingredients: body.onerilen_etken_maddeler,
              isSensitive: body.hassas_akis,
              host: settings.thermalPrinterHost,
              port: settings.thermalPrinterPort,
              logger: app.log,
            });
          } catch (err) {
            printerOk = false;
            printerError = err?.message || 'Yazici hatasi';
          }
          return reply.status(201).send({
            qr_kodu: existingPayload.qr_kodu,
            qr_payload: existingPayload.qr_payload || existingPayload.qr_kodu,
            durum: 'kaydedildi',
            yazici_ok: printerOk,
            sync_durum: 'onceden_gonderildi',
            ...(printerError ? { yazici_hatasi: printerError } : {}),
          });
        }
      }

      // 3. Backend'e QR için gönder
      let backendQr = null;
      let isValidationRejection = false;

      try {
        const res = await requestWithRetry(
          db, settings, 'POST', '/api/kiosk/v1/sessions/',
          { items: [payload] }, app.log
        );

        if (res.status === 200 || res.status === 207) {
          let resBody = {};
          try { resBody = await res.json(); } catch { resBody = {}; }

          const resultItem = (resBody?.results || []).find(
            (r) => String(r.idempotency_key) === String(idempotencyAnahtari)
          );
          const errorItem = (resBody?.errors || []).find(
            (e) => String(e.idempotency_anahtari) === String(idempotencyAnahtari)
          );

          // Yapısal log — güvenli: secret/QR/kişisel veri içermez
          app.log.info({
            event: 'central_sessions_response',
            upstream_path: '/api/kiosk/v1/sessions/',
            upstream_status: res.status,
            kiosk_id: settings.kioskId || null,
            batch_size: 1,
            accepted_count: resultItem ? 1 : 0,
            duplicate_count: resultItem?.status === 'existing' ? 1 : 0,
            rejected_count: errorItem ? 1 : 0,
          }, 'central_sessions_response');

          if (resultItem?.qr_kodu) {
            backendQr = resultItem.qr_kodu;
          } else if (errorItem) {
            // Kalıcı doğrulama hatası — scheduler'ın sonsuz tekrar denemesini engelle
            isValidationRejection = true;
            const errorKeys = errorItem.errors ? Object.keys(errorItem.errors) : [];
            db.prepare(
              'UPDATE oturum_outbox SET retry_count = 99, error_reason = ? WHERE idempotency_anahtari = ?',
            ).run(
              JSON.stringify({ type: 'backend_validation', keys: errorKeys }),
              String(idempotencyAnahtari),
            );
            recordDiagnostic(db, {
              level: 'WARNING',
              event: 'session_backend_rejected',
              message: 'Backend oturumu dogrulama hatasi ile reddetti',
              context: {
                upstream_status: res.status,
                error_field_count: errorKeys.length,
                error_keys: errorKeys,  // alan adları güvenli; değerler loglanmaz
                // devMode'da hata mesajları da loglanır (prod'da kapalı)
                ...(settings.devMode ? { error_messages: errorItem.errors } : {}),
              },
              correlationId: req.id,
            });
          }
        } else if (res.status === 401) {
          handle401Error(db, settings, app.log);
          return reply.status(401).send({ error: 'Kimlik dogrulamasi basarisiz.', code: 'auth_failed' });
        } else if (res.status === 403) {
          handle403Error(db, settings, app.log);
          return reply.status(403).send({ error: 'Yetki hatasi.', code: 'forbidden' });
        } else {
          app.log.warn({
            event: 'central_sessions_unexpected',
            upstream_status: res.status,
          }, 'Merkez beklenmeyen yanit; kayit outbox\'ta bekliyor');
          return reply.status(503).send({
            error: 'Merkez sunucu hatasi. Oturum lokal olarak kaydedildi, daha sonra gonderilecek.',
            code: 'backend_error',
            sync_durum: 'bekliyor',
          });
        }
      } catch (err) {
        app.log.warn({ event: 'backend_unreachable', err: err.message }, 'Backend erisimi basarisiz; kayit outbox\'ta bekliyor');
        return reply.status(503).send({
          error: 'Merkez sunucusuna ulasilamiyor. Oturum lokal olarak kaydedildi, daha sonra gonderilecek.',
          code: 'backend_unreachable',
          sync_durum: 'bekliyor',
        });
      }

      if (isValidationRejection) {
        return reply.status(422).send({
          error: 'Oturum merkez tarafindan reddedildi. Veri dogrulama hatasi.',
          code: 'backend_rejected',
        });
      }

      if (!backendQr) {
        return reply.status(502).send({
          error: 'Merkez QR kodu dondurmedi.',
          code: 'backend_no_qr',
        });
      }

      // 4. QR alındı — outbox kaydını güncelle (QR + gönderilme zamanı)
      const payloadWithQr = { ...payload, qr_kodu: backendQr };
      db.prepare(
        'UPDATE oturum_outbox SET payload = ?, gonderilme_tarihi = ?, error_reason = NULL WHERE idempotency_anahtari = ?',
      ).run(JSON.stringify(payloadWithQr), new Date().toISOString(), String(idempotencyAnahtari));

      // Termal yazici (opsiyonel)
      let printerOk = true;
      let printerError = null;
      try {
        printReceipt({
          qrCode: backendQr,
          qrPayload: qrPayload || backendQr,
          categoryName: body.kategori_slug || body.danisma_kategorisi_slug,
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

      return reply.status(201).send({
        qr_kodu: backendQr,
        qr_payload: qrPayload || backendQr,
        durum: 'kaydedildi',
        yazici_ok: printerOk,
        sync_durum: 'gonderildi',
        ...(printerError ? { yazici_hatasi: printerError } : {}),
      });
    }

    // Tamamlanmamis (terk edilmis) oturum â€” QR gerekmez, outbox'a kaydet.
    db.prepare(
      'INSERT OR IGNORE INTO oturum_outbox (idempotency_anahtari, payload) VALUES (?, ?)',
    ).run(idempotencyAnahtari, JSON.stringify(payload));

    // Bağlantı varsa arka planda gönder (hata olursa scheduler tekrar dener)
    if (settings.centralApiBase && hasAppKeyCredentials(db)) {
      try {
        const res = await requestWithRetry(
          db, settings, 'POST', '/api/kiosk/v1/sessions/',
          { items: [payload] }, app.log
        );
        if (res.status === 200 || res.status === 207) {
          let resBody2 = {};
          try { resBody2 = await res.json(); } catch { resBody2 = {}; }
          // Yalniz results[] listesinde olan kayitlari gonderildi olarak isaretle
          const accepted = (resBody2?.results || []).some(
            (r) => String(r.idempotency_key) === String(idempotencyAnahtari)
          );
          if (accepted) {
            db.prepare(
              'UPDATE oturum_outbox SET gonderilme_tarihi = ? WHERE idempotency_anahtari = ?',
            ).run(new Date().toISOString(), idempotencyAnahtari);
          }
          // errors[] icindekiler outbox'ta bekler; scheduler tekrar dener
        } else if (res.status === 401) {
          handle401Error(db, settings, app.log);
        } else if (res.status === 403) {
          handle403Error(db, settings, app.log);
        }
      } catch (err) {
        app.log.warn({ err: err.message }, 'Terk edilmis oturum backend iletilemedi, scheduler deneyecek');
      }
    }

    return reply.status(201).send({
      qr_kodu: null,
      durum: 'kaydedildi',
      yazici_ok: true,
    });
  });

  // â”€â”€ eczaci sorgulamasi (yerel sirla korunur) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  app.get(
    '/api/oturum/*',
    { preHandler: requireLocalSecret(settings.kioskProvisioningSecret) },
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

  // â”€â”€ reklamlar / DOOH assets (geriye dÃ¶nÃ¼k uyumluluk) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  app.get('/api/reklamlar/aktif', async () => {
    const creatives = db
      .prepare('SELECT id, media_url, duration_seconds, type FROM creatives WHERE aktif = 1')
      .all();
    const houseAds = db
      .prepare('SELECT id, name, media_url, duration_seconds, type FROM house_ads WHERE aktif = 1')
      .all();
    return [
      ...creatives.map((c) => ({
        id: c.id,
        media_url: buildMediaUrl(db, 'creative', c.id, c.media_url),
        remote_media_url: c.media_url,
        duration_seconds: c.duration_seconds,
        type: c.type,
      })),
      ...houseAds.map((h) => ({
        id: h.id,
        name: h.name,
        media_url: buildMediaUrl(db, 'house_ad', h.id, h.media_url),
        remote_media_url: h.media_url,
        duration_seconds: h.duration_seconds,
        type: h.type,
      })),
    ];
  });

  // â”€â”€ playlist â€” bugÃ¼nÃ¼n aktif saati iÃ§in sÄ±ralÄ± oynatma listesi â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  /**
   * GET /api/playlist/current?hour=<0-23>
   *
   * hour verilmezse ÅŸu anki saat kullanÄ±lÄ±r.
   * Playlist yoksa â†’ fallback: /api/reklamlar/aktif ile aynÄ± veri.
   *
   * DÃ¶ner:
   *   { version, target_date, target_hour, loop_duration_seconds, items: [...] }
   */
  app.get('/api/playlist/current', async (req) => {
    // Playlist'ler backend tarafindan Istanbul yerel saatine gore uretilir;
    // dogru saati secmek icin duvar saatini Europe/Istanbul'a gore hesapla.
    const { date: today, hour: localHour } = istanbulNow();
    const hour = req.query.hour !== undefined
      ? parseInt(req.query.hour, 10)
      : localHour;

    const playlist = db
      .prepare('SELECT * FROM playlists WHERE target_date = ? AND target_hour = ?')
      .get(today, hour);

    if (!playlist) {
      // Fallback: yapÄ±landÄ±rÄ±lmamÄ±ÅŸ tÃ¼m asset'ler
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
          media_url: buildMediaUrl(db, 'creative', c.id, c.media_url),
          remote_media_url: c.media_url,
          duration_seconds: c.duration_seconds,
          estimated_start_offset_seconds: 0,
        })),
        ...houseAds.map((h, i) => ({
          id: `fallback-h-${h.id}`,
          playback_order: creatives.length + i,
          asset_id: h.id,
          asset_type: 'house_ad',
          media_url: buildMediaUrl(db, 'house_ad', h.id, h.media_url),
          remote_media_url: h.media_url,
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
      .all(playlist.id)
      .map((item) => ({
        ...item,
        media_url: buildMediaUrl(db, item.asset_type, item.asset_id, item.media_url),
        remote_media_url: item.media_url,
      }));

    return {
      version: playlist.version,
      target_date: playlist.target_date,
      target_hour: playlist.target_hour,
      loop_duration_seconds: playlist.loop_duration_seconds,
      is_fallback: false,
      items,
    };
  });

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

const wifiMockEnabled =
  String(process.env.EISA_WIFI_MOCK || '').toLowerCase() === 'true';

const wifiMockNetworks = [
  { ssid: 'EISA-Test-WiFi', signal: 92, secured: true },
  { ssid: 'Eczane-Misafir', signal: 68, secured: true },
  { ssid: 'Acik-Ag', signal: 41, secured: false },
];


app.get('/api/wifi/status', async (_req, reply) => {
  if (wifiMockEnabled) {
    return {
      connected: false,
      ssid: null,
    };
  }

  try {
    return await getWifiStatus();
  } catch (err) {
    return fail(reply, 500, err.message);
  }
});

app.get('/api/wifi/scan', async (_req, reply) => {
  if (wifiMockEnabled) {
    return wifiMockNetworks;
  }

  try {
    return await scanWifi();
  } catch (err) {
    return fail(reply, 500, err.message);
  }
});

app.post('/api/wifi/connect', {
  schema: {
    body: {
      type: 'object',
      required: ['ssid'],
      properties: {
        ssid: { type: 'string', minLength: 1, maxLength: 64 },
        password: { type: 'string', minLength: 0, maxLength: 128 },
      },
      additionalProperties: false,
    },
  },
}, async (req, reply) => {
  const { ssid, password } = req.body;

  if (wifiMockEnabled) {
    if (ssid === 'EISA-Test-WiFi' && password === 'eisa1234') {
      return {
        success: true,
        message: 'Wi-Fi bağlantısı başarılı.',
      };
    }

    if (ssid === 'Acik-Ag') {
      return {
        success: true,
        message: 'Wi-Fi bağlantısı başarılı.',
      };
    }

    return fail(reply, 422, 'Wi-Fi parolası hatalı.');
  }

  const wifiResult = await connectWifi(ssid, password ?? null);

  if (!wifiResult.success) {
    return fail(reply, 422, wifiResult.message);
  }

  return wifiResult;
});

 // Svelte UI'nin yakaladigi kritik hatalari alir; sanitize edip JSON stdout'a
  // yazar ve WARNING/ERROR ise diagnostic outbox'a dusurur. Kullanici verisi,
  // QR kodu, cevaplar, ilaÃ§ listesi vb. buraya gonderilmemelidir.
  app.post('/api/log/client', async (req, reply) => {
    const body = parseBody(clientLogSchema, req.body, reply);
    if (!body) return;
    const level = body.level;
    req.log[level === 'CRITICAL' ? 'error' : level.toLowerCase()]({
      event: body.event,
      source: 'kiosk_ui',
      route: body.route,
      component: body.component,
      stack: body.stack,
      context: body.context,
    }, body.message || body.event);
    recordDiagnostic(db, {
      level,
      event: body.event,
      message: body.message || body.event,
      correlationId: body.correlation_id || req.id,
      occurredAt: body.occurred_at,
      context: {
        route: body.route,
        component: body.component,
        stack: body.stack,
        ...body.context,
      },
    });
    reply.code(202);
    return { durum: 'kaydedildi', correlation_id: req.id };
  });

  return app;
}
