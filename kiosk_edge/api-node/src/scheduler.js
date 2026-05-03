// Push/Pull mantigi — Turkce sema, Turkce backend payload'lari.
// PULL: kategori/soru/etken_madde + reklamlari merkezden cekip SQLite'a upsert eder.
// PUSH: outbox'taki anonim loglari merkeze iter; idempotency_anahtari ile guvenli silme.
import cron from 'node-cron';
import { Agent, fetch } from 'undici';
import { checkOutboxPressure } from './db.js';

let _tasks = [];
let _undiciAgent = null;

function getAgent(verifyTls) {
  if (_undiciAgent) return _undiciAgent;
  _undiciAgent = new Agent({ connect: { rejectUnauthorized: !!verifyTls } });
  return _undiciAgent;
}

function authHeaders(settings) {
  return {
    Authorization: `AppKey ${settings.kioskAppKey}`,
    'X-Kiosk-MAC': settings.kioskMac,
  };
}

async function request(settings, method, pathPart, body) {
  const url = settings.centralApiBase.replace(/\/+$/, '') + pathPart;
  const headers = authHeaders(settings);
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const res = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    dispatcher: getAgent(settings.verifyTls),
    signal: AbortSignal.timeout(15000),
  });
  return res;
}

// Exponential backoff ile retry (ERR-002).
async function requestWithRetry(settings, method, pathPart, body, log) {
  const delays = [0, 1000, 3000];
  let lastErr;
  for (let attempt = 0; attempt < delays.length; attempt++) {
    if (delays[attempt] > 0) await new Promise((r) => setTimeout(r, delays[attempt]));
    try {
      const res = await request(settings, method, pathPart, body);
      if (res.status >= 500) {
        lastErr = new Error(`HTTP ${res.status}`);
        log?.warn?.(`PUSH ${pathPart} HTTP ${res.status} (deneme ${attempt + 1}/${delays.length})`);
        continue;
      }
      return res;
    } catch (err) {
      lastErr = err;
      log?.warn?.(
        { err: err.message },
        `PUSH ${pathPart} ag hatasi (deneme ${attempt + 1}/${delays.length})`,
      );
    }
  }
  throw lastErr;
}

// ── upsert yardimcilari (Turkce alanlar) ─────────────────────────────────
function upsertKategori(db, c) {
  const exists = db.prepare('SELECT id FROM kategoriler WHERE id = ?').get(c.id);
  const params = {
    id: c.id,
    slug: c.slug,
    ad: c.ad,
    ikon: c.ikon || 'fa-circle',
    hassas: c.hassas ? 1 : 0,
    aktif: c.aktif === false ? 0 : 1,
    hedef_cinsiyetler: JSON.stringify(c.hedef_cinsiyetler ?? []),
    hedef_yas_araliklari: JSON.stringify(c.hedef_yas_araliklari ?? []),
  };
  if (exists) {
    db.prepare(
      `UPDATE kategoriler
          SET slug=@slug, ad=@ad, ikon=@ikon, hassas=@hassas, aktif=@aktif,
              hedef_cinsiyetler=@hedef_cinsiyetler,
              hedef_yas_araliklari=@hedef_yas_araliklari,
              guncellenme_tarihi=strftime('%Y-%m-%dT%H:%M:%fZ','now')
        WHERE id=@id`,
    ).run(params);
  } else {
    db.prepare(
      `INSERT INTO kategoriler
         (id, slug, ad, ikon, hassas, aktif, hedef_cinsiyetler, hedef_yas_araliklari)
       VALUES (@id, @slug, @ad, @ikon, @hassas, @aktif,
               @hedef_cinsiyetler, @hedef_yas_araliklari)`,
    ).run(params);
  }
}

function upsertSoru(db, q, kategoriId) {
  const exists = db.prepare('SELECT id FROM sorular WHERE id = ?').get(q.id);
  const params = {
    id: q.id,
    kategori_id: kategoriId,
    seed_id: q.seed_id || `q_${q.id}`,
    metin: q.metin ?? q.text ?? '',
    sira: q.sira ?? q.priority ?? 0,
    eslesme_kurallari: JSON.stringify(q.eslesme_kurallari ?? q.match_rules ?? []),
    hedef_cinsiyetler: JSON.stringify(q.hedef_cinsiyetler ?? []),
    hedef_yas_araliklari: JSON.stringify(q.hedef_yas_araliklari ?? []),
  };
  if (exists) {
    db.prepare(
      `UPDATE sorular SET metin=@metin, sira=@sira, eslesme_kurallari=@eslesme_kurallari,
              hedef_cinsiyetler=@hedef_cinsiyetler,
              hedef_yas_araliklari=@hedef_yas_araliklari,
              guncellenme_tarihi=strftime('%Y-%m-%dT%H:%M:%fZ','now')
        WHERE id=@id`,
    ).run(params);
  } else {
    db.prepare(
      `INSERT INTO sorular
         (id, kategori_id, seed_id, metin, sira, eslesme_kurallari,
          hedef_cinsiyetler, hedef_yas_araliklari)
       VALUES (@id, @kategori_id, @seed_id, @metin, @sira, @eslesme_kurallari,
               @hedef_cinsiyetler, @hedef_yas_araliklari)`,
    ).run(params);
  }
}

function upsertCevap(db, a, soruId) {
  const exists = db.prepare('SELECT id FROM cevaplar WHERE id = ?').get(a.id);
  const params = { id: a.id, soru_id: soruId, metin: a.metin ?? '', agirlik: a.agirlik ?? 0 };
  if (exists) {
    db.prepare('UPDATE cevaplar SET metin=@metin, agirlik=@agirlik WHERE id=@id').run(params);
  } else {
    db.prepare(
      'INSERT INTO cevaplar (id, soru_id, metin, agirlik) VALUES (@id, @soru_id, @metin, @agirlik)',
    ).run(params);
  }
}

function upsertEtkenMadde(db, em) {
  db.prepare(
    `INSERT INTO etken_maddeler (id, ad, aciklama) VALUES (@id, @ad, @aciklama)
     ON CONFLICT(id) DO UPDATE SET ad=excluded.ad, aciklama=excluded.aciklama`,
  ).run({ id: em.id, ad: em.ad, aciklama: em.aciklama || '' });
}

function upsertReklam(db, r) {
  // Backend: hedef_eczaneler id listesi doner; bos = herkese goster.
  const hedefleme = {
    eczaneler: r.hedef_eczaneler ?? [],
  };
  const exists = db.prepare('SELECT id FROM reklamlar WHERE id = ?').get(r.id);
  const params = {
    id: r.id,
    ad: r.ad,
    medya_url: r.medya_url || '',
    baslangic_tarihi: r.baslangic_tarihi,
    bitis_tarihi: r.bitis_tarihi,
    hedefleme: JSON.stringify(hedefleme),
    aktif: r.aktif === false ? 0 : 1,
  };
  if (exists) {
    db.prepare(
      `UPDATE reklamlar SET ad=@ad, medya_url=@medya_url,
              baslangic_tarihi=@baslangic_tarihi, bitis_tarihi=@bitis_tarihi,
              hedefleme=@hedefleme, aktif=@aktif,
              guncellenme_tarihi=strftime('%Y-%m-%dT%H:%M:%fZ','now')
        WHERE id=@id`,
    ).run(params);
  } else {
    db.prepare(
      `INSERT INTO reklamlar (id, ad, medya_url, baslangic_tarihi, bitis_tarihi, hedefleme, aktif)
       VALUES (@id, @ad, @medya_url, @baslangic_tarihi, @bitis_tarihi, @hedefleme, @aktif)`,
    ).run(params);
  }
}

// ── PULL ─────────────────────────────────────────────────────────────────
export async function pullFromCentral(db, settings, log = console) {
  try {
    // 1) products/sync — { kategoriler: [...], etken_maddeler: [...] }
    const r1 = await requestWithRetry(settings, 'GET', '/api/products/sync/', undefined, log);
    if (r1.ok) {
      const data = await r1.json();
      const tx = db.transaction((payload) => {
        for (const cat of payload.kategoriler || []) {
          upsertKategori(db, cat);
          for (const q of cat.sorular || []) {
            upsertSoru(db, q, cat.id);
            for (const a of q.cevaplar || []) upsertCevap(db, a, q.id);
          }
        }
        for (const em of payload.etken_maddeler || []) upsertEtkenMadde(db, em);
      });
      tx(data);
      log.info?.(`PULL: ${(data.kategoriler || []).length} kategori, ${(data.etken_maddeler || []).length} etken madde guncellendi`);
    } else {
      log.warn?.(`PULL products/sync HTTP ${r1.status}`);
    }

    // 2) campaigns/sync — Reklam[]
    const r2 = await requestWithRetry(settings, 'GET', '/api/campaigns/sync/', undefined, log);
    if (r2.ok) {
      const reklamlar = await r2.json();
      const tx = db.transaction((items) => {
        for (const r of items) upsertReklam(db, r);
      });
      tx(reklamlar);
      log.info?.(`PULL: ${reklamlar.length} reklam guncellendi`);
    } else {
      log.warn?.(`PULL campaigns/sync HTTP ${r2.status}`);
    }
  } catch (err) {
    log.error?.({ err: err.message || String(err) }, 'PULL basarisiz (offline mod)');
  }
}

// ── PUSH ─────────────────────────────────────────────────────────────────
export async function pushToCentral(db, settings, log = console) {
  try {
    // 1) oturum_outbox → /api/analytics/sessions/
    const oturumlar = db
      .prepare(
        `SELECT id, idempotency_anahtari, payload FROM oturum_outbox
          WHERE gonderilme_tarihi IS NULL LIMIT 50`,
      )
      .all();
    if (oturumlar.length) {
      try {
        const r = await requestWithRetry(
          settings, 'POST', '/api/analytics/sessions/',
          { items: oturumlar.map((s) => JSON.parse(s.payload)) }, log,
        );
        await consumeBulkPushResponse(db, 'oturum_outbox', oturumlar, r, log, 'sessions');
      } catch (err) {
        log.warn?.({ err: err.message }, 'PUSH sessions kalici hata; kayitlar saklaniyor');
      }
    }

    // 2) reklam_gosterim_outbox → /api/analytics/impressions/
    const gosterimler = db
      .prepare(
        `SELECT id, idempotency_anahtari, payload FROM reklam_gosterim_outbox
          WHERE gonderilme_tarihi IS NULL LIMIT 100`,
      )
      .all();
    if (gosterimler.length) {
      try {
        const r = await requestWithRetry(
          settings, 'POST', '/api/analytics/impressions/',
          { items: gosterimler.map((i) => JSON.parse(i.payload)) }, log,
        );
        await consumeBulkPushResponse(db, 'reklam_gosterim_outbox', gosterimler, r, log, 'impressions');
      } catch (err) {
        log.warn?.({ err: err.message }, 'PUSH impressions kalici hata; kayitlar saklaniyor');
      }
    }
  } catch (err) {
    log.error?.({ err }, 'PUSH basarisiz (offline mod)');
  }
}

/**
 * Backend 200/207 yanitini isler:
 *  - `accepted_keys` listesindeki idempotency_anahtari'na sahip outbox satirlari silinir.
 *  - `errors` icindeki kayitlar lokalde tutulmaya devam eder.
 */
async function consumeBulkPushResponse(db, table, rows, res, log, label) {
  if (!(res.status === 200 || res.status === 201 || res.status === 207)) {
    log?.warn?.(`PUSH ${label} HTTP ${res.status}; kayitlar saklaniyor`);
    return;
  }
  let body = null;
  try { body = await res.json(); } catch { body = {}; }
  const acceptedKeys = new Set(
    Array.isArray(body?.accepted_keys) ? body.accepted_keys.map(String) : [],
  );
  if (!acceptedKeys.size) {
    log?.warn?.(`PUSH ${label} accepted_keys bos; kayitlar saklaniyor`);
    return;
  }

  const toDelete = rows.filter((r) => acceptedKeys.has(String(r.idempotency_anahtari)));
  if (toDelete.length) {
    const del = db.prepare(`DELETE FROM ${table} WHERE id = ?`);
    const tx = db.transaction((items) => {
      for (const it of items) del.run(it.id);
    });
    tx(toDelete);
  }

  const rejected = rows.length - toDelete.length;
  log?.info?.(
    `PUSH ${label}: ${toDelete.length} kabul ve silindi` +
      (rejected ? `, ${rejected} reddedildi (lokalde tutuluyor)` : ''),
  );
  if (Array.isArray(body?.errors) && body.errors.length) {
    log?.warn?.({ errors: body.errors }, `PUSH ${label} kismi hata`);
  }
}

export function startScheduler(db, settings, log = console) {
  if (_tasks.length) return;
  const pullEvery = settings.pullIntervalSec * 1000;
  const pushEvery = settings.pushIntervalSec * 1000;

  const pullTimer = setInterval(() => pullFromCentral(db, settings, log), pullEvery);
  const pushTimer = setInterval(() => pushToCentral(db, settings, log), pushEvery);
  const pressureTimer = setInterval(() => {
    try { checkOutboxPressure(log, settings.outboxMaxRows); }
    catch (err) { log?.warn?.({ err: err?.message }, 'Outbox basinc kontrolu basarisiz'); }
  }, pushEvery);
  pullTimer.unref?.(); pushTimer.unref?.(); pressureTimer.unref?.();
  _tasks.push(pullTimer, pushTimer, pressureTimer);

  log.info?.(
    `Scheduler baslatildi — pull:${settings.pullIntervalSec}s push:${settings.pushIntervalSec}s`,
  );
}

export function stopScheduler() {
  for (const t of _tasks) clearInterval(t);
  _tasks = [];
}

export { cron };
