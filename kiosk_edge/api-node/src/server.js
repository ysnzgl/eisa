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
import { buildReceiptBuffer, sendToTransport } from './printer.js';
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
import { buildMediaUrl, getLocalMediaMeta, mediaKindFromMime } from './mediaCache.js';
import { istanbulNow } from './timezone.js';
import { requestWithRetry } from './scheduler.js';
import { handle401Error, handle403Error, hasAppKeyCredentials } from './provisioning.js';
import { generateNextQr, CROCKFORD_QR_RE } from './qrGen.js';
import {
  seciSonrakiLogo,
  artirGunlukSayi,
  setLastLogoId,
  getOrderedLogoCandidates,
  commitBasariliBaski,
} from './barkodLogoService.js';

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

  // Dev ortamı: barkod logo PNG dosyasını doğrudan sun (yazıcı simülasyonu için)
  app.get('/api/barkod-logo-gorsel/:id', async (req, reply) => {
    const row = db.prepare('SELECT local_path, cache_status FROM barkod_logolar WHERE id = ?').get(req.params.id);
    if (!row || row.cache_status !== 'ready' || !row.local_path || !fs.existsSync(row.local_path)) {
      return fail(reply, 404, 'Logo bulunamadi');
    }
    reply.header('Content-Type', 'image/png');
    reply.header('Cache-Control', 'public, max-age=3600');
    return reply.send(fs.createReadStream(row.local_path));
  });

  app.get('/api/media/:assetType/:assetId', async (req, reply) => {
    const { assetType } = req.params;
    // URL'e video tespiti icin eklenen uzantiyi ayikla (asset_id UUID/_active'tir).
    const assetId = req.params.assetId.replace(
      /\.(mp4|webm|ogv|ogg|jpg|jpeg|png|gif|webp)$/i, '',
    );
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
        `SELECT id, slug, ad, ikon, ust_kategori_id, aktif, sira
           FROM danisma_kategorileri WHERE aktif = 1 ORDER BY COALESCE(sira, 100), id`,
      )
      .all();
    const toplevel = rows.filter((r) => r.ust_kategori_id === null);
    return toplevel.map((parent) => ({
      id: parent.id,
      slug: parent.slug,
      ad: parent.ad,
      ikon: parent.ikon,
      sira: parent.sira ?? 100,
      alt_kategoriler: rows
        .filter((r) => r.ust_kategori_id === parent.id)
        .map((c) => ({ id: c.id, slug: c.slug, ad: c.ad, ikon: c.ikon, sira: c.sira ?? 100 })),
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

  // -- oturum gonder (offline-first) ──────────────────────────────────────────
  // Tamamlanan oturumlar icin QR yerel uretilir, SQLite'a atomik kaydedilir,
  // hemen donulur; backend push arka planda tetiklenir (HTTP cevabi beklenmez).
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

    const olusturulmaTarihi = new Date().toISOString();
    const idempotencyAnahtari = body.idempotency_anahtari
      ? String(body.idempotency_anahtari)
      : crypto.randomUUID();

    // Idempotency: ayni key daha once yerel QR ile kaydedilmis mi?
    const existingRow = db.prepare(
      'SELECT payload, gonderilme_tarihi FROM oturum_outbox WHERE idempotency_anahtari = ? LIMIT 1'
    ).get(idempotencyAnahtari);
    if (existingRow) {
      const existingPayload = safeJson(existingRow.payload, {});
      if (existingPayload.qr_kodu) {
        app.log.info({ event: 'session_idempotent_redelivery' }, 'Idempotent yeniden teslim; mevcut QR donuluyor');
        let printerOk = true;
        let printerError = null;
        // Aynı logo yeniden basılır (yeni seçim yapılmaz, sayaç artırılmaz, cursor ilerletilmez)
        const existingLogoId = existingPayload.barkod_logo_id || null;
        let rePrintLogoPath = null;
        if (existingLogoId) {
          const logoRow = db.prepare('SELECT local_path, cache_status FROM barkod_logolar WHERE id = ?').get(existingLogoId);
          if (logoRow && logoRow.cache_status === 'ready' && logoRow.local_path) {
            rePrintLogoPath = logoRow.local_path;
          }
        }
        try {
          printReceipt({
            qrCode: existingPayload.qr_kodu,
            qrPayload: existingPayload.qr_kodu,
            categoryName: body.kategori_slug || body.danisma_kategorisi_slug,
            ingredients: body.onerilen_etken_maddeler,
            isSensitive: body.hassas_akis,
            barkodLogoPath: rePrintLogoPath,
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
          durum: 'kaydedildi',
          yazici_ok: printerOk,
          sync_durum: existingRow.gonderilme_tarihi ? 'gonderildi' : 'bekliyor',
          ...(printerError ? { yazici_hatasi: printerError } : {}),
        });
      }
      if (!body.tamamlandi) {
        return reply.status(201).send({ qr_kodu: null, durum: 'kaydedildi', yazici_ok: true });
      }
    }

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

    if (!body.tamamlandi) {
      // Terk edilmis oturum: QR yok, outbox'a kaydet, arka planda gonder
      db.prepare(
        'INSERT OR IGNORE INTO oturum_outbox (idempotency_anahtari, payload) VALUES (?, ?)',
      ).run(idempotencyAnahtari, JSON.stringify(payload));
      if (settings.centralApiBase && hasAppKeyCredentials(db)) {
        setImmediate(async () => {
          try {
            const res = await requestWithRetry(
              db, settings, 'POST', '/api/kiosk/v1/sessions/', { items: [payload] }, app.log
            );
            if (res.status === 200 || res.status === 207) {
              let resBody = {};
              try { resBody = await res.json(); } catch { resBody = {}; }
              const accepted = (resBody?.results || []).some(
                (r) => String(r.idempotency_key) === String(idempotencyAnahtari)
              );
              if (accepted) {
                db.prepare(
                  'UPDATE oturum_outbox SET gonderilme_tarihi = ? WHERE idempotency_anahtari = ?',
                ).run(new Date().toISOString(), idempotencyAnahtari);
              }
            } else if (res.status === 401) {
              handle401Error(db, settings, app.log);
            } else if (res.status === 403) {
              handle403Error(db, settings, app.log);
            }
          } catch (err) {
            app.log.warn({ err: err.message }, 'Terk edilmis oturum backend iletilemedi, scheduler deneyecek');
          }
        });
      }
      return reply.status(201).send({ qr_kodu: null, durum: 'kaydedildi', yazici_ok: true });
    }

    // Tamamlanan oturum: offline-first QR uretimi (eczane_kiosk_no varsa)
    // Settings'e değil, doğrudan kiosk_meta'ya bakılır (provisioning.js bağımsız).
    const kioskNoRow = db.prepare("SELECT value FROM kiosk_meta WHERE key='eczane_kiosk_no'").get();
    const eczaneKioskNo = kioskNoRow ? parseInt(kioskNoRow.value, 10) : null;
    const hasSlot = Number.isInteger(eczaneKioskNo) && eczaneKioskNo >= 1 && eczaneKioskNo <= 31;

    if (!hasSlot) {
      // eczane_kiosk_no atanmamış → provisioning tamamlanmadan QR üretilemez.
      return reply.status(503).send({ error: 'Kiosk numarasi atanmamis; QR uretilemedi.', code: 'kiosk_no_missing' });
    }

    // Atomik transaction: QR uret + sayac guncelle + outbox insert
    let qrKodu;
    try {
      const txn = db.transaction(() => {
        qrKodu = generateNextQr(db, eczaneKioskNo);
        // barkod_logo_id başlangıçta null; başarılı baskı sonrası güncellenir.
        const payloadWithQr = { ...payload, qr_kodu: qrKodu, barkod_logo_id: null };
        db.prepare(
          'INSERT OR IGNORE INTO oturum_outbox (idempotency_anahtari, payload) VALUES (?, ?)',
        ).run(idempotencyAnahtari, JSON.stringify(payloadWithQr));
        return qrKodu;
      });
      qrKodu = txn();
    } catch (err) {
      app.log.error({ event: 'qr_local_generate_failed', err: err.message }, 'Yerel QR uretimi basarisiz');
      return reply.status(500).send({
        error: 'QR kodu uretilemedi. Lutfen tekrar deneyin.',
        code: 'qr_generate_error',
      });
    }

    // Barkod logo adayları (rotation sırasında)
    const logoCandidates = getOrderedLogoCandidates(db);

    // Fiş byte'larını bellekte oluştur (tüm adaylar denenir, başarısızlar atlanır)
    const { buffer: receipBuffer, logoId: basilanLogoId } = buildReceiptBuffer({
      qrPayload: qrKodu,
      logoCandidates,
      logger: app.log,
    });

    // Termal yazici: tek tamamlanmış buffer transport'a verilir
    let printerOk = true;
    let printerError = null;
    if (settings.thermalPrinterHost) {
      try {
        sendToTransport({
          buffer: receipBuffer,
          host: settings.thermalPrinterHost,
          port: settings.thermalPrinterPort,
          logger: app.log,
        });
        // Transport başarısı (no throw): counter+cursor+outbox_payload tek transaction
        if (basilanLogoId) {
          commitBasariliBaski(db, basilanLogoId, idempotencyAnahtari);
        }
      } catch (err) {
        printerOk = false;
        printerError = err?.message || 'Yazici hatasi';
        app.log.warn({ err: printerError }, 'Termal yazici gonderilemedi — sayac/cursor ilerlemez');
        // Yazıcı hatasında: sayaç artmaz, cursor ilerlemiyor, barkod_logo_id null kalır
      }
    }

    // Backend push: arka planda, HTTP cevabini bekletmez
    if (settings.centralApiBase && hasAppKeyCredentials(db)) {
      setImmediate(async () => {
        try {
          // Outbox'tan nihai payload'ı oku (commitBasariliBaski'de güncellenmiş olabilir)
          const finalOutboxRow = db.prepare('SELECT payload FROM oturum_outbox WHERE idempotency_anahtari = ?').get(idempotencyAnahtari);
          const finalPayload = finalOutboxRow ? safeJson(finalOutboxRow.payload, {}) : { ...payload, qr_kodu: qrKodu };
          const res = await requestWithRetry(
            db, settings, 'POST', '/api/kiosk/v1/sessions/', { items: [finalPayload] }, app.log
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
            app.log.info({
              event: 'central_sessions_response',
              upstream_status: res.status,
              kiosk_id: settings.kioskId || null,
              accepted_count: resultItem ? 1 : 0,
              rejected_count: errorItem ? 1 : 0,
            }, 'central_sessions_response');
            if (resultItem) {
              db.prepare(
                'UPDATE oturum_outbox SET gonderilme_tarihi = ?, error_reason = NULL WHERE idempotency_anahtari = ?',
              ).run(new Date().toISOString(), idempotencyAnahtari);
            } else if (errorItem) {
              const errorKeys = errorItem.errors ? Object.keys(errorItem.errors) : [];
              db.prepare(
                'UPDATE oturum_outbox SET retry_count = 99, error_reason = ? WHERE idempotency_anahtari = ?',
              ).run(JSON.stringify({ type: 'backend_validation', keys: errorKeys }), idempotencyAnahtari);
            }
          } else if (res.status === 401) {
            handle401Error(db, settings, app.log);
          } else if (res.status === 403) {
            handle403Error(db, settings, app.log);
          } else {
            app.log.warn({ event: 'central_sessions_unexpected', upstream_status: res.status },
              'Merkez beklenmeyen yanit; kayit PENDING olarak bekleyecek');
          }
        } catch (err) {
          app.log.warn({ event: 'backend_unreachable', err: err.message },
            'Backend push basarisiz; scheduler tekrar deneyecek');
        }
      });
    }

    // Dev önizlemesi: yalnız EISA_DEV_MODE=true ortamında göster
    const devMode = settings.devMode;
    const devLogoUrl = devMode && basilanLogoId
      ? `/api/barkod-logo-gorsel/${basilanLogoId}`
      : null;

    return reply.status(201).send({
      qr_kodu: qrKodu,
      durum: 'kaydedildi',
      yazici_ok: printerOk,
      sync_durum: 'bekliyor',
      ...(devMode ? { dev_preview: true, barkod_logo_gorsel_url: devLogoUrl } : {}),
      ...(printerError ? { yazici_hatasi: printerError } : {}),
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
  // ── oturum sync-durum sorgusu (UI polling için) ──────────────────────────
  app.get('/api/oturum/sync-durum/:key', async (req, reply) => {
    const key = String(req.params.key ?? '');
    if (!key || key.length > 128) return fail(reply, 400, 'Gecersiz anahtar');
    const row = db.prepare(
      'SELECT gonderilme_tarihi FROM oturum_outbox WHERE idempotency_anahtari = ? LIMIT 1'
    ).get(key);
    if (!row) return fail(reply, 404, 'Kayit bulunamadi');
    return { sync_durum: row.gonderilme_tarihi ? 'gonderildi' : 'bekliyor' };
  });
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
        .prepare('SELECT id, media_url, active_media_url, duration_seconds, type FROM creatives WHERE aktif = 1')
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
          active_media_url: c.active_media_url
            ? buildMediaUrl(db, 'creative', c.id + '_active', c.active_media_url)
            : '',
          media_type: mediaKindFromMime(getLocalMediaMeta(db, 'creative', c.id)?.mime_type),
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
          active_media_url: '',
          media_type: mediaKindFromMime(getLocalMediaMeta(db, 'house_ad', h.id)?.mime_type),
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
        `SELECT pi.id, pi.playback_order, pi.asset_id, pi.asset_type,
                pi.media_url, pi.duration_seconds, pi.estimated_start_offset_seconds,
                CASE WHEN pi.asset_type = 'creative' THEN COALESCE(c.active_media_url, '') ELSE '' END AS active_media_url
           FROM playlist_items pi
           LEFT JOIN creatives c ON pi.asset_type = 'creative' AND c.id = pi.asset_id
          WHERE pi.playlist_id = ?
          ORDER BY pi.playback_order`,
      )
      .all(playlist.id)
      .map((item) => ({
        ...item,
        media_url: buildMediaUrl(db, item.asset_type, item.asset_id, item.media_url),
        remote_media_url: item.media_url,
        active_media_url: item.active_media_url
          ? buildMediaUrl(db, 'creative', item.asset_id + '_active', item.active_media_url)
          : '',
        media_type: mediaKindFromMime(getLocalMediaMeta(db, item.asset_type, item.asset_id)?.mime_type),
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

    // play_event_id idempotency: aynı olay iki kez kaydedilmesin
    const playEventId = body.play_event_id || null;
    if (playEventId) {
      const exists = db.prepare(
        'SELECT 1 FROM reklam_gosterim_outbox WHERE play_event_id = ? LIMIT 1',
      ).get(playEventId);
      if (exists) {
        reply.code(200);
        return { durum: 'zaten_kayitli' };
      }
    }

    // idempotency_anahtari = play_event_id (varsa) yoksa NULL (INSERT OR IGNORE çalışır)
    db.prepare(
      `INSERT OR IGNORE INTO reklam_gosterim_outbox
         (idempotency_anahtari, payload, play_event_id, status, error_code, occurred_at, expected_duration)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
    ).run(
      playEventId,
      JSON.stringify({
        asset_id: body.asset_id,
        asset_type: body.asset_type,
        played_at: body.played_at,
        duration_played: body.duration_played,
        play_event_id: playEventId,
        status: body.status || 'COMPLETED',
        error_code: body.error_code || '',
        occurred_at: body.occurred_at || null,
        expected_duration: body.expected_duration ?? null,
      }),
      playEventId,
      body.status || 'COMPLETED',
      body.error_code || '',
      body.occurred_at || null,
      body.expected_duration ?? null,
    );
    reply.code(201);
    return { durum: 'kaydedildi' };
  });

  // Faz 4: kiosk teknik olayları (hata, restart, bağlantı vb.)
  app.post('/api/kiosk-event', async (req, reply) => {
    const { kioskEventBatchSchema } = await import('./validators.js');
    const parsed = kioskEventBatchSchema.safeParse(req.body);
    if (!parsed.success) {
      reply.code(400);
      return { error: 'Gecersiz payload', details: parsed.error.issues.slice(0, 5) };
    }
    const { items } = parsed.data;
    const insertStmt = db.prepare(
      `INSERT OR IGNORE INTO kiosk_event_outbox
         (event_id, event_type, severity, message, occurred_at)
       VALUES (?, ?, ?, ?, ?)`,
    );
    const tx = db.transaction((evts) => {
      for (const evt of evts) {
        insertStmt.run(evt.event_id, evt.event_type, evt.severity, evt.message, evt.occurred_at || null);
      }
    });
    tx(items);
    reply.code(201);
    return { queued: items.length };
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
