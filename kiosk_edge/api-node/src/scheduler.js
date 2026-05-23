import cron from 'node-cron';
import { Agent, fetch } from 'undici';
import { checkOutboxPressure } from './db.js';
import { syncMediaCache } from './mediaCache.js';

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
    bagli_kategori_id: c.bagli_kategori ?? null,
    aktif: c.aktif === false ? 0 : 1,
    hedef_cinsiyetler: JSON.stringify(c.hedef_cinsiyetler ?? []),
    hedef_yas_araliklari: JSON.stringify(c.hedef_yas_araliklari ?? []),
  };
  if (exists) {
    db.prepare(
      `UPDATE kategoriler
          SET slug=@slug, ad=@ad, ikon=@ikon,
              bagli_kategori_id=@bagli_kategori_id, aktif=@aktif,
              hedef_cinsiyetler=@hedef_cinsiyetler,
              hedef_yas_araliklari=@hedef_yas_araliklari,
              guncellenme_tarihi=strftime('%Y-%m-%dT%H:%M:%fZ','now')
        WHERE id=@id`,
    ).run(params);
  } else {
    db.prepare(
      `INSERT INTO kategoriler
         (id, slug, ad, ikon, bagli_kategori_id, aktif, hedef_cinsiyetler, hedef_yas_araliklari)
       VALUES (@id, @slug, @ad, @ikon, @bagli_kategori_id, @aktif,
               @hedef_cinsiyetler, @hedef_yas_araliklari)`,
    ).run(params);
  }
}

function upsertDanismaKategori(db, d) {
  db.prepare(
    `INSERT INTO danisma_kategorileri (id, slug, ad, ikon, ust_kategori_id, aktif)
     VALUES (@id, @slug, @ad, @ikon, @ust_kategori_id, @aktif)
     ON CONFLICT(id) DO UPDATE SET
       slug=excluded.slug, ad=excluded.ad, ikon=excluded.ikon,
       ust_kategori_id=excluded.ust_kategori_id, aktif=excluded.aktif,
       guncellenme_tarihi=strftime('%Y-%m-%dT%H:%M:%fZ','now')`,
  ).run({
    id: d.id,
    slug: d.slug,
    ad: d.ad,
    ikon: d.ikon || 'fa-comments',
    ust_kategori_id: d.ust_kategori ?? null,
    aktif: d.aktif === false ? 0 : 1,
  });
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

function upsertCreative(db, c) {
  db.prepare(
    `INSERT INTO creatives (id, media_url, duration_seconds, checksum, type, aktif)
     VALUES (@id, @media_url, @duration_seconds, @checksum, 'creative', 1)
     ON CONFLICT(id) DO UPDATE SET
       media_url=excluded.media_url,
       duration_seconds=excluded.duration_seconds,
       checksum=excluded.checksum,
       guncellenme_tarihi=strftime('%Y-%m-%dT%H:%M:%fZ','now')`,
  ).run({
    id: String(c.id),
    media_url: c.media_url || '',
    duration_seconds: c.duration_seconds ?? 15,
    checksum: c.checksum || '',
  });
}

function upsertHouseAd(db, h) {
  db.prepare(
    `INSERT INTO house_ads (id, name, media_url, duration_seconds, type, aktif)
     VALUES (@id, @name, @media_url, @duration_seconds, 'house_ad', 1)
     ON CONFLICT(id) DO UPDATE SET
       name=excluded.name,
       media_url=excluded.media_url,
       duration_seconds=excluded.duration_seconds,
       guncellenme_tarihi=strftime('%Y-%m-%dT%H:%M:%fZ','now')`,
  ).run({
    id: String(h.id),
    name: h.name || '',
    media_url: h.media_url || '',
    duration_seconds: h.duration_seconds ?? 15,
  });
}

function upsertLookups(db, lookups) {
  if (!lookups) return;

  const insCinsiyet = db.prepare(
    'INSERT INTO cinsiyetler (id, kod, ad) VALUES (@id, @kod, @ad) ON CONFLICT(id) DO UPDATE SET kod=excluded.kod, ad=excluded.ad',
  );
  const insYas = db.prepare(
    `INSERT INTO yas_araliklari (id, kod, ad, alt_sinir, ust_sinir) VALUES (@id, @kod, @ad, @alt_sinir, @ust_sinir)
     ON CONFLICT(id) DO UPDATE SET kod=excluded.kod, ad=excluded.ad, alt_sinir=excluded.alt_sinir, ust_sinir=excluded.ust_sinir`,
  );
  const insIl = db.prepare(
    'INSERT INTO iller (id, ad) VALUES (@id, @ad) ON CONFLICT(id) DO UPDATE SET ad=excluded.ad',
  );
  const insIlce = db.prepare(
    'INSERT INTO ilceler (id, il_id, ad) VALUES (@id, @il_id, @ad) ON CONFLICT(id) DO UPDATE SET il_id=excluded.il_id, ad=excluded.ad',
  );

  const tx = db.transaction((l) => {
    for (const c of l.cinsiyetler ?? []) insCinsiyet.run(c);
    for (const y of l.yas_araliklari ?? []) insYas.run(y);
    for (const il of l.iller ?? []) insIl.run(il);
    for (const ilce of l.ilceler ?? []) insIlce.run(ilce);
  });
  tx(lookups);
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
        for (const d of payload.danisma_kategorileri || []) {
          upsertDanismaKategori(db, d);
          for (const alt of d.alt_kategoriler || []) upsertDanismaKategori(db, { ...alt, ust_kategori: d.id });
        }
      });
      tx(data);
      log.info?.(`PULL: ${(data.kategoriler || []).length} kategori, ${(data.etken_maddeler || []).length} etken madde, ${(data.danisma_kategorileri || []).length} danisma guncellendi`);
    } else {
      log.warn?.(`PULL products/sync HTTP ${r1.status}`);
    }

    // 2) kiosk/v1/{id}/sync — { creatives: [...], house_ads: [...], lookups: {...} }
    const kioskId = settings.kioskId;
    if (!kioskId) {
      log.warn?.('PULL kiosk/v1/sync atlandi: EISA_KIOSK_ID ayarlanmamis');
    } else {
      const r2 = await requestWithRetry(settings, 'GET', `/api/kiosk/v1/${kioskId}/sync/`, undefined, log);
      if (r2.ok) {
        const data = await r2.json();
        const tx = db.transaction((payload) => {
          upsertLookups(db, payload.lookups);
          for (const c of payload.creatives || []) upsertCreative(db, c);
          for (const h of payload.house_ads || []) upsertHouseAd(db, h);
        });
        tx(data);
        await syncMediaCache(db, settings, log);
        log.info?.(`PULL: ${(data.creatives || []).length} creative, ${(data.house_ads || []).length} house_ad, ${(data.lookups?.iller || []).length} il guncellendi`);
      } else if (r2.status === 403) {
        log.warn?.('PULL kiosk/v1/sync HTTP 403: EISA_KIOSK_ID ile AppKey/MAC eslesmesini kontrol edin');
      } else {
        log.warn?.(`PULL kiosk/v1/sync HTTP ${r2.status}`);
      }
    }
  } catch (err) {
    log.error?.({ err: err.message || String(err) }, 'PULL basarisiz (offline mod)');
  }
}

// ── PING + PLAYLIST SYNC ─────────────────────────────────────────────────
/**
 * 1) /api/kiosk/v1/{id}/ping/ → sunucudan bugünkü playlist versiyonunu al.
 * 2) Yerel kayıtlı versiyondan farklıysa → playlist'i çek ve SQLite'a yaz.
 *
 * Kiosk offline ise hata yutulur; mevcut yerel playlist oynatılmaya devam eder.
 */
export async function pingAndSyncPlaylist(db, settings, log = console) {
  const kioskId = settings.kioskId;
  if (!kioskId) return;

  try {
    const today = new Date().toISOString().slice(0, 10);
    const pingRes = await requestWithRetry(
      settings, 'GET', `/api/kiosk/v1/${kioskId}/ping/`, undefined, log,
    );
    if (!pingRes.ok) {
      log.warn?.(`PING HTTP ${pingRes.status}`);
      return;
    }
    const ping = await pingRes.json();
    const serverVersion = ping.playlist_version ?? 0;

    // Yerel versiyonu oku
    const metaRow = db
      .prepare("SELECT value FROM kiosk_meta WHERE key = 'playlist_version'")
      .get();
    const localVersion = metaRow ? parseInt(metaRow.value, 10) : 0;

    if (serverVersion === 0) {
      log.debug?.('PING: sunucuda henuz playlist yok');
      return;
    }

    if (serverVersion <= localVersion) {
      log.debug?.(`PING: playlist guncel (v${localVersion})`);
      return;
    }

    log.info?.(`PING: yeni playlist versiyonu ${localVersion} → ${serverVersion}; indiriliyor…`);

    // Bugün için tüm saatleri çek (tek istek — ?date=YYYY-MM-DD)
    const plRes = await requestWithRetry(
      settings, 'GET',
      `/api/kiosk/v1/${kioskId}/playlist/?date=${today}`,
      undefined, log,
    );
    if (!plRes.ok) {
      log.warn?.(`PLAYLIST çekme HTTP ${plRes.status}`);
      return;
    }
    const body = await plRes.json();
    // Backend { kiosk_id, target_date, loop_duration_seconds, playlists: [...] } döner
    const playlists = Array.isArray(body) ? body : (body.playlists ?? []);

    const upsertPlaylist = db.prepare(`
      INSERT INTO playlists (id, target_date, target_hour, loop_duration_seconds, version)
      VALUES (@id, @target_date, @target_hour, @loop_duration_seconds, @version)
      ON CONFLICT(target_date, target_hour) DO UPDATE SET
        id=excluded.id,
        loop_duration_seconds=excluded.loop_duration_seconds,
        version=excluded.version,
        synced_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
    `);

    const delItems  = db.prepare('DELETE FROM playlist_items WHERE playlist_id = ?');
    const insItem   = db.prepare(`
      INSERT OR REPLACE INTO playlist_items
        (id, playlist_id, playback_order, asset_id, asset_type,
         media_url, duration_seconds, estimated_start_offset_seconds)
      VALUES
        (@id, @playlist_id, @playback_order, @asset_id, @asset_type,
         @media_url, @duration_seconds, @estimated_start_offset_seconds)
    `);

    const upsertMeta = db.prepare(`
      INSERT INTO kiosk_meta (key, value) VALUES (?, ?)
      ON CONFLICT(key) DO UPDATE SET value=excluded.value
    `);

    const tx = db.transaction((list) => {
      for (const pl of list) {
        upsertPlaylist.run({
          id: String(pl.id),
          target_date: pl.target_date,
          target_hour: pl.target_hour,
          loop_duration_seconds: pl.loop_duration_seconds ?? 60,
          version: pl.version,
        });
        delItems.run(String(pl.id));
        for (const item of pl.items ?? []) {
          insItem.run({
            id: String(item.id),
            playlist_id: String(pl.id),
            playback_order: item.playback_order ?? 0,
            asset_id: String(item.asset_id),
            asset_type: item.asset_type ?? 'creative',
            media_url: item.media_url ?? '',
            duration_seconds: item.duration_seconds ?? 15,
            estimated_start_offset_seconds: item.estimated_start_offset_seconds ?? 0,
          });
        }
      }
      upsertMeta.run('playlist_version', String(serverVersion));
      upsertMeta.run('playlist_date', today);
    });
    tx(playlists);
    await syncMediaCache(db, settings, log);

    log.info?.(`PLAYLIST sync tamam: ${playlists.length} saat kaydedildi (v${serverVersion})`);
  } catch (err) {
    log.warn?.({ err: err.message }, 'PING/PLAYLIST sync basarisiz (offline mod)');
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

    // 2) reklam_gosterim_outbox → /api/kiosk/v1/{id}/proof-of-play/
    const gosterimler = db
      .prepare(
        `SELECT id, payload FROM reklam_gosterim_outbox
          WHERE gonderilme_tarihi IS NULL LIMIT 100`,
      )
      .all();
    if (gosterimler.length) {
      try {
        const logs = gosterimler.map((i) => {
          const p = JSON.parse(i.payload);
          const entry = { played_at: p.played_at, duration_played: p.duration_played ?? 0 };
          if (p.asset_type === 'house_ad') entry.house_ad_id = p.asset_id;
          else entry.creative_id = p.asset_id;
          return entry;
        });
        const kioskId = settings.kioskId;
        const r = await requestWithRetry(
          settings, 'POST', `/api/kiosk/v1/${kioskId}/proof-of-play/`,
          { logs }, log,
        );
        if (r.status === 201) {
          const del = db.prepare('DELETE FROM reklam_gosterim_outbox WHERE id = ?');
          const tx = db.transaction((items) => { for (const it of items) del.run(it.id); });
          tx(gosterimler);
          log.info?.(`PUSH proof-of-play: ${gosterimler.length} kayit gonderildi`);
        } else {
          let body = null;
          try { body = await r.json(); } catch { body = null; }
          log.warn?.({ status: r.status, body }, 'PUSH proof-of-play basarisiz; kayitlar saklaniyor');
        }
      } catch (err) {
        log.warn?.({ err: err.message }, 'PUSH proof-of-play kalici hata; kayitlar saklaniyor');
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
  const pingEvery = (settings.pingIntervalSec ?? 60) * 1000;

  const pullTimer    = setInterval(() => pullFromCentral(db, settings, log), pullEvery);
  const pushTimer    = setInterval(() => pushToCentral(db, settings, log), pushEvery);
  const pingTimer    = setInterval(() => pingAndSyncPlaylist(db, settings, log), pingEvery);
  const pressureTimer = setInterval(() => {
    try { checkOutboxPressure(log, settings.outboxMaxRows); }
    catch (err) { log?.warn?.({ err: err?.message }, 'Outbox basinc kontrolu basarisiz'); }
  }, pushEvery);
  pullTimer.unref?.();
  pushTimer.unref?.();
  pingTimer.unref?.();
  pressureTimer.unref?.();
  _tasks.push(pullTimer, pushTimer, pingTimer, pressureTimer);

  // İlk açılışta hemen bir ping yap
  pingAndSyncPlaylist(db, settings, log);
  syncMediaCache(db, settings, log).catch((err) =>
    log.warn?.({ err: err?.message }, 'Baslangicta medya cache senkronizasyonu basarisiz'),
  );

  log.info?.(
    `Scheduler baslatildi — pull:${settings.pullIntervalSec}s push:${settings.pushIntervalSec}s ping:${settings.pingIntervalSec ?? 60}s`,
  );
}

export function stopScheduler() {
  for (const t of _tasks) clearInterval(t);
  _tasks = [];
}

export { cron };
