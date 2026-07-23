import cron from 'node-cron';
import { Agent, fetch } from 'undici';
import { checkOutboxPressure } from './db.js';
import { syncMediaCache } from './mediaCache.js';
import { getAuthHeaders, getProvisioningState, handle401Error, handle403Error, hasAppKeyCredentials, enrollDeviceId } from './provisioning.js';
import { istanbulNow } from './timezone.js';
import {
  CORRELATION_HEADER_PRETTY,
  derivedId,
  getCorrelationId,
  newCorrelationId,
  runWithCorrelation,
} from './correlationId.js';
import {
  cleanupOldDiagnostics,
  fetchPendingDiagnostics,
  markDiagnosticsSent,
  recordDiagnostic,
  reschedulePendingDiagnostics,
} from './diagnosticOutbox.js';

// Outbox'taki bir kaydın en fazla kaç kez scheduler tarafından deneneceği.
// Bu sayıya ulaşan kayıtlar kalıcı hata olarak kabul edilir ve atlanır.
const OUTBOX_MAX_RETRY = 10;

let _tasks = [];
let _undiciAgent = null;

function getAgent(verifyTls) {
  if (_undiciAgent) return _undiciAgent;
  _undiciAgent = new Agent({ connect: { rejectUnauthorized: !!verifyTls } });
  return _undiciAgent;
}

function authHeaders(db) {
  return getAuthHeaders(db);
}

function hasCentralAuth(db) {
  return hasAppKeyCredentials(db);
}

async function request(db, settings, method, pathPart, body) {
  const url = settings.centralApiBase.replace(/\/+$/, '') + pathPart;
  const headers = authHeaders(db);
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  // Correlation ID: aktif contextvars degeri varsa iletir, yoksa yeni uretir.
  const correlationId = getCorrelationId() || newCorrelationId();
  headers[CORRELATION_HEADER_PRETTY] = correlationId;
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
export async function requestWithRetry(db, settings, method, pathPart, body, log) {
  const delays = [0, 1000, 3000];
  let lastErr;
  const target = pathPart;
  for (let attempt = 0; attempt < delays.length; attempt++) {
    if (delays[attempt] > 0) await new Promise((r) => setTimeout(r, delays[attempt]));
    try {
      const res = await request(db, settings, method, pathPart, body);
      if (res.status >= 500) {
        lastErr = new Error(`HTTP ${res.status}`);
        log?.warn?.({
          event: 'central_request_retry',
          target_service: target,
          attempt: attempt + 1,
          max_attempts: delays.length,
          retry_delay_ms: delays[attempt],
          status_code: res.status,
        }, `PUSH ${target} HTTP ${res.status}`);
        continue;
      }
      return res;
    } catch (err) {
      lastErr = err;
      log?.warn?.({
        event: 'central_request_retry',
        target_service: target,
        attempt: attempt + 1,
        max_attempts: delays.length,
        retry_delay_ms: delays[attempt],
        err: err?.message,
      }, `PUSH ${target} ag hatasi`);
    }
  }
  throw lastErr;
}

// ── upsert yardimcilari (Turkce alanlar) ─────────────────────────────────
function upsertKategori(db, c) {
  const hedefCinsiyetId = resolveCinsiyetId(db, c.hedef_cinsiyet ?? c.hedef_cinsiyetler ?? null);
  const hedefYasAraliklari = normalizeLookupIds(c.hedef_yas_araliklari);
  const exists = db.prepare('SELECT id FROM kategoriler WHERE id = ?').get(c.id);
  const params = {
    id: c.id,
    slug: c.slug,
    ad: c.ad,
    ikon: c.ikon || 'fa-circle',
    bagli_kategori_id: c.bagli_kategori ?? null,
    hedef_cinsiyet_id: hedefCinsiyetId,
    aktif: c.aktif === false ? 0 : 1,
    hedef_cinsiyetler: JSON.stringify(legacyCinsiyetArray(c, hedefCinsiyetId)),
    hedef_yas_araliklari: JSON.stringify(hedefYasAraliklari),
  };
  if (exists) {
    db.prepare(
      `UPDATE kategoriler
          SET slug=@slug, ad=@ad, ikon=@ikon,
              bagli_kategori_id=@bagli_kategori_id, aktif=@aktif,
              hedef_cinsiyet_id=@hedef_cinsiyet_id,
              hedef_cinsiyetler=@hedef_cinsiyetler,
              hedef_yas_araliklari=@hedef_yas_araliklari,
              guncellenme_tarihi=strftime('%Y-%m-%dT%H:%M:%fZ','now')
        WHERE id=@id`,
    ).run(params);
  } else {
    db.prepare(
      `INSERT INTO kategoriler
         (id, slug, ad, ikon, bagli_kategori_id, hedef_cinsiyet_id, aktif, hedef_cinsiyetler, hedef_yas_araliklari)
       VALUES (@id, @slug, @ad, @ikon, @bagli_kategori_id, @hedef_cinsiyet_id, @aktif,
               @hedef_cinsiyetler, @hedef_yas_araliklari)`,
    ).run(params);
  }

  replaceKategoriYasAraliklari(db, c.id, hedefYasAraliklari);
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
  const hedefCinsiyetId = resolveCinsiyetId(db, q.hedef_cinsiyet ?? q.hedef_cinsiyetler ?? null);
  const hedefYasAraliklari = normalizeLookupIds(q.hedef_yas_araliklari);
  const exists = db.prepare('SELECT id FROM sorular WHERE id = ?').get(q.id);
  const params = {
    id: q.id,
    kategori_id: kategoriId,
    seed_id: q.seed_id || `q_${q.id}`,
    metin: q.metin ?? q.text ?? '',
    sira: q.sira ?? q.priority ?? 0,
    eslesme_kurallari: JSON.stringify(q.eslesme_kurallari ?? q.match_rules ?? []),
    hedef_cinsiyet_id: hedefCinsiyetId,
    hedef_cinsiyetler: JSON.stringify(legacyCinsiyetArray(q, hedefCinsiyetId)),
    hedef_yas_araliklari: JSON.stringify(hedefYasAraliklari),
  };
  if (exists) {
    db.prepare(
      `UPDATE sorular SET kategori_id=@kategori_id, metin=@metin, sira=@sira,
              eslesme_kurallari=@eslesme_kurallari,
              hedef_cinsiyet_id=@hedef_cinsiyet_id,
              hedef_cinsiyetler=@hedef_cinsiyetler,
              hedef_yas_araliklari=@hedef_yas_araliklari,
              guncellenme_tarihi=strftime('%Y-%m-%dT%H:%M:%fZ','now')
        WHERE id=@id`,
    ).run(params);
  } else {
    db.prepare(
      `INSERT INTO sorular
         (id, kategori_id, seed_id, metin, sira, eslesme_kurallari,
          hedef_cinsiyet_id, hedef_cinsiyetler, hedef_yas_araliklari)
       VALUES (@id, @kategori_id, @seed_id, @metin, @sira, @eslesme_kurallari,
               @hedef_cinsiyet_id, @hedef_cinsiyetler, @hedef_yas_araliklari)`,
    ).run(params);
  }

  replaceSoruYasAraliklari(db, q.id, hedefYasAraliklari);
  replaceSoruEtkenMaddeler(db, q.id, q.hedef_etken_maddeler ?? []);
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
    `INSERT INTO etken_maddeler (id, ad, aciklama, aktif)
     VALUES (@id, @ad, @aciklama, @aktif)
     ON CONFLICT(id) DO UPDATE SET
       ad=excluded.ad,
       aciklama=excluded.aciklama,
       aktif=excluded.aktif,
       guncellenme_tarihi=strftime('%Y-%m-%dT%H:%M:%fZ','now')`,
  ).run({
    id: em.id,
    ad: em.ad,
    aciklama: em.aciklama || '',
    aktif: em.aktif === false ? 0 : 1,
  });
}

function legacyCinsiyetArray(payload, hedefCinsiyetId) {
  if (Array.isArray(payload?.hedef_cinsiyetler)) return payload.hedef_cinsiyetler;
  return hedefCinsiyetId ? [hedefCinsiyetId] : [];
}

function normalizeLookupIds(value) {
  if (Array.isArray(value)) {
    return [...new Set(value.map((v) => Number.parseInt(v, 10)).filter(Number.isFinite))];
  }
  if (value === null || value === undefined || value === '') return [];
  const n = Number.parseInt(value, 10);
  return Number.isFinite(n) ? [n] : [];
}

function resolveCinsiyetId(db, value) {
  if (value === null || value === undefined || value === '') return null;
  if (Array.isArray(value)) {
    for (const item of value) {
      const resolved = resolveCinsiyetId(db, item);
      if (resolved) return resolved;
    }
    return null;
  }

  const n = Number.parseInt(value, 10);
  if (Number.isFinite(n)) {
    const row = db.prepare('SELECT id FROM cinsiyetler WHERE id = ?').get(n);
    return row ? row.id : null;
  }

  const row = db.prepare('SELECT id FROM cinsiyetler WHERE kod = ?').get(String(value));
  return row ? row.id : null;
}

function replaceKategoriYasAraliklari(db, kategoriId, yasAraligiIds) {
  db.prepare('DELETE FROM kategori_hedef_yas_araliklari WHERE kategori_id = ?').run(kategoriId);
  const ins = db.prepare(
    'INSERT INTO kategori_hedef_yas_araliklari (kategori_id, yas_araligi_id) VALUES (?, ?)',
  );
  for (const yasId of yasAraligiIds) {
    const exists = db.prepare('SELECT 1 FROM yas_araliklari WHERE id = ?').get(yasId);
    if (exists) ins.run(kategoriId, yasId);
  }
}

function replaceSoruYasAraliklari(db, soruId, yasAraligiIds) {
  db.prepare('DELETE FROM soru_hedef_yas_araliklari WHERE soru_id = ?').run(soruId);
  const ins = db.prepare(
    'INSERT INTO soru_hedef_yas_araliklari (soru_id, yas_araligi_id) VALUES (?, ?)',
  );
  for (const yasId of yasAraligiIds) {
    const exists = db.prepare('SELECT 1 FROM yas_araliklari WHERE id = ?').get(yasId);
    if (exists) ins.run(soruId, yasId);
  }
}

function replaceSoruEtkenMaddeler(db, soruId, hedefEtkenMaddeler) {
  db.prepare('DELETE FROM soru_etken_maddeler WHERE soru_id = ?').run(soruId);
  const ins = db.prepare(
    'INSERT INTO soru_etken_maddeler (soru_id, etken_madde_id, rol) VALUES (?, ?, ?)',
  );
  for (const item of hedefEtkenMaddeler) {
    const etkenMaddeId = Number.parseInt(item?.etken_madde, 10);
    if (!Number.isFinite(etkenMaddeId)) continue;
    const exists = db.prepare('SELECT 1 FROM etken_maddeler WHERE id = ?').get(etkenMaddeId);
    if (!exists) continue;
    ins.run(soruId, etkenMaddeId, item?.rol || 'ana');
  }
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

  const tx = db.transaction((l) => {
    for (const c of l.cinsiyetler ?? []) insCinsiyet.run(c);
    for (const y of l.yas_araliklari ?? []) insYas.run(y);
  });
  tx(lookups);
}

// ── PULL ─────────────────────────────────────────────────────────────────
export async function pullFromCentral(db, settings, log = console) {
  if (!hasCentralAuth(db, settings)) {
    log.warn?.('PULL atlandi: kiosk kimligi henuz provision edilmedi');
    return;
  }

  // Device ID enrollment — App Key alındıktan sonra henüz enrolled değilse bağla.
  // İdempotent: zaten enrolled ise hızla döner.
  await enrollDeviceId(db, settings, log).catch((err) =>
    log.warn?.({ err: err?.message }, 'enrollDeviceId pull sirasinda basarisiz')
  );
  try {
    // 1) kiosk/v1/sync — { creatives: [...], house_ads: [...], lookups: {...} }
    const r2 = await requestWithRetry(db, settings, 'GET', '/api/kiosk/v1/sync/', undefined, log);
    if (r2.ok) {
      const data = await r2.json();
      const tx = db.transaction((payload) => {
        upsertLookups(db, payload.lookups);
        for (const c of payload.creatives || []) upsertCreative(db, c);
        for (const h of payload.house_ads || []) upsertHouseAd(db, h);
      });
      tx(data);
      await syncMediaCache(db, settings, log);
      log.info?.(`PULL: ${(data.creatives || []).length} creative, ${(data.house_ads || []).length} house_ad guncellendi`);
    } else if (r2.status === 401) {
      handle401Error(db, settings, log);
    } else if (r2.status === 403) {
      handle403Error(db, settings, log);
    } else {
      log.warn?.(`PULL kiosk/v1/sync HTTP ${r2.status}`);
    }

    // 2) kiosk/v1/catalog — { kategoriler: [...], etken_maddeler: [...], danisma_kategorileri: [...], lookups: {...} }
    const r1 = await requestWithRetry(db, settings, 'GET', '/api/kiosk/v1/catalog/', undefined, log);
    if (r1.ok) {
      const data = await r1.json();
      
      // Insert lookups first, outside transaction to avoid rollback on FK errors
      if (data.lookups) {
        try {
          upsertLookups(db, data.lookups);
          log.info?.(`PULL: ${(data.lookups.cinsiyetler || []).length} cinsiyet, ${(data.lookups.yas_araliklari || []).length} yas_araligi yuklendi`);
        } catch (err) {
          log.error?.({ err: err?.message }, 'Lookup upsert basarisiz');
        }
      }
      
      // Temporarily disable FK checks for self-referencing categories (must be outside transaction)
      db.exec('PRAGMA foreign_keys = OFF');
      
      const tx = db.transaction((payload) => {
        for (const em of payload.etken_maddeler || []) upsertEtkenMadde(db, em);
        for (const cat of payload.kategoriler || []) {
          upsertKategori(db, cat);
          for (const q of cat.sorular || []) {
            upsertSoru(db, q, cat.id);
            for (const a of q.cevaplar || []) upsertCevap(db, a, q.id);
          }
        }
        for (const d of payload.danisma_kategorileri || []) {
          upsertDanismaKategori(db, d);
          for (const alt of d.alt_kategoriler || []) upsertDanismaKategori(db, { ...alt, ust_kategori: d.id });
        }
      });
      tx(data);
      
      // Re-enable FK checks
      db.exec('PRAGMA foreign_keys = ON');
      tx(data);
      log.info?.(`PULL: ${(data.kategoriler || []).length} kategori, ${(data.etken_maddeler || []).length} etken madde, ${(data.danisma_kategorileri || []).length} danisma guncellendi`);
    } else if (r1.status === 401) {
      handle401Error(db, settings, log);
    } else if (r1.status === 403) {
      handle403Error(db, settings, log);
    } else {
      log.warn?.(`PULL kiosk/v1/catalog HTTP ${r1.status}`);
    }
  } catch (err) {
    log.error?.({ event: 'pull_scheduler_error', err: err.message || String(err) }, 'PULL basarisiz (offline mod)');
    recordDiagnostic(db, {
      level: 'ERROR',
      event: 'pull_scheduler_error',
      message: err?.message || 'pull scheduler error',
    });
  }
}

// ── PING + PLAYLIST SYNC ─────────────────────────────────────────────────
/**
 * 1) /api/kiosk/v1/ping/ → sunucudan bugünkü playlist versiyonunu al.
 * 2) Yerel kayıtlı versiyondan farklıysa → playlist'i çek ve SQLite'a yaz.
 *
 * Kiosk offline ise hata yutulur; mevcut yerel playlist oynatılmaya devam eder.
 */
export async function pingAndSyncPlaylist(db, settings, log = console) {
  if (!hasCentralAuth(db, settings)) return;

  try {
    const today = istanbulNow().date;
    const pingRes = await requestWithRetry(
      db, settings, 'GET', '/api/kiosk/v1/ping/', undefined, log,
    );
    if (!pingRes.ok) {
      if (pingRes.status === 401) {
        handle401Error(db, settings, log);
      } else if (pingRes.status === 403) {
        handle403Error(db, settings, log);
      } else {
        log.warn?.(`PING HTTP ${pingRes.status}`);
      }
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
      db, settings, 'GET',
      `/api/kiosk/v1/playlist/?date=${today}`,
      undefined, log,
    );
    if (!plRes.ok) {
      if (plRes.status === 401) {
        handle401Error(db, settings, log);
      } else if (plRes.status === 403) {
        handle403Error(db, settings, log);
      } else {
        log.warn?.(`PLAYLIST çekme HTTP ${plRes.status}`);
      }
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

// ── Faz 5: Manifest + ACK sync ────────────────────────────────────────────
/**
 * DOOH_KIOSK_ACK=true modunda çalışır.
 *
 * Adımlar:
 *   1. Ping → desired version + horizon bilgisi al.
 *   2. Sync gerekiyor mu? (version farkı VEYA horizon eksik/güncellenmiş VEYA bugün değişmiş)
 *   3. /manifest/ endpoint'inden 3 günlük authoritative veriyi çek.
 *   4. Manifest doğrula (3 ardışık gün, zorunlu alanlar).
 *   5. SQLite'a atomik uygula (3 gün birlikte ya da hiç).
 *   6. Pending ACK kaydet (aynı transaction).
 *   7. ACK endpoint'ine gönder.
 *   8. Başarıyla gönderilince pending ACK sil.
 */
export async function pingAndSyncManifest(db, settings, log = console) {
  if (!hasCentralAuth(db, settings)) return;

  const { savePendingAck, clearPendingAckIfMatches, setAckNextRetry } =
    await import('./db.js');

  try {
    const now = istanbulNow();
    const today = now.date;

    // 1. Ping
    const pingRes = await requestWithRetry(
      db, settings, 'GET', '/api/kiosk/v1/ping/', undefined, log,
    );
    if (!pingRes.ok) {
      if (pingRes.status === 401) handle401Error(db, settings, log);
      else if (pingRes.status === 403) handle403Error(db, settings, log);
      else log.warn?.(`PING HTTP ${pingRes.status}`);
      return;
    }
    const ping = await pingRes.json();
    const serverVersion = ping.desired_playlist_version ?? ping.playlist_version ?? 0;
    const serverHorizonEnd = ping.horizon_end ?? null;

    if (serverVersion === 0) {
      log.debug?.('MANIFEST-PING: sunucuda henüz playlist yok');
      return;
    }

    // Yerel state
    const localVersionRow = db.prepare("SELECT value FROM kiosk_meta WHERE key='playlist_version'").get();
    const localVersion = localVersionRow ? parseInt(localVersionRow.value, 10) : 0;
    const localHorizonEndRow = db.prepare("SELECT value FROM kiosk_meta WHERE key='applied_horizon_end'").get();
    const localHorizonEnd = localHorizonEndRow?.value ?? null;
    const localTodayRow = db.prepare("SELECT value FROM kiosk_meta WHERE key='playlist_date'").get();
    const localToday = localTodayRow?.value ?? null;

    // 2. Sync gerekiyor mu?
    const needsSync = (
      serverVersion !== localVersion ||
      serverHorizonEnd !== localHorizonEnd ||
      localToday !== today
    );

    if (!needsSync) {
      log.debug?.(`MANIFEST-PING: güncel (v${localVersion}, horizon=${localHorizonEnd})`);
      return;
    }

    log.info?.(`MANIFEST-PING: sync gerekli (local=v${localVersion} server=v${serverVersion})`);

    // 3. Manifest çek
    const mRes = await requestWithRetry(
      db, settings, 'GET', '/api/kiosk/v1/manifest/', undefined, log,
    );
    if (!mRes.ok) {
      if (mRes.status === 401) handle401Error(db, settings, log);
      else if (mRes.status === 403) handle403Error(db, settings, log);
      else log.warn?.(`MANIFEST HTTP ${mRes.status}`);
      return;
    }
    const manifest = await mRes.json();

    // 4. Doğrula
    const { days, horizon_start, horizon_end, playlist_version: manifestVersion } = manifest;
    if (!Array.isArray(days) || days.length !== 3) {
      log.warn?.({ event: 'manifest_invalid', reason: 'days.length != 3' }, 'Manifest reddedildi');
      return;
    }
    // Her gün doğru mu?
    for (const day of days) {
      if (!day.target_date || !Array.isArray(day.playlists)) {
        log.warn?.({ event: 'manifest_invalid', reason: 'eksik gün alanı' }, 'Manifest reddedildi');
        return;
      }
    }

    // 5. Atomik SQLite uygulama
    const upsertPlaylist = db.prepare(`
      INSERT INTO playlists (id, target_date, target_hour, loop_duration_seconds, version)
      VALUES (@id, @target_date, @target_hour, @loop_duration_seconds, @version)
      ON CONFLICT(target_date, target_hour) DO UPDATE SET
        id=excluded.id,
        loop_duration_seconds=excluded.loop_duration_seconds,
        version=excluded.version,
        synced_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
    `);
    const delItems = db.prepare('DELETE FROM playlist_items WHERE playlist_id = ?');
    const insItem = db.prepare(`
      INSERT OR REPLACE INTO playlist_items
        (id, playlist_id, playback_order, asset_id, asset_type,
         media_url, duration_seconds, estimated_start_offset_seconds)
      VALUES (@id, @playlist_id, @playback_order, @asset_id, @asset_type,
              @media_url, @duration_seconds, @estimated_start_offset_seconds)
    `);
    const delDatePlaylists = db.prepare('DELETE FROM playlists WHERE target_date = ?');
    const upsertMeta = db.prepare(
      `INSERT INTO kiosk_meta (key, value) VALUES (?, ?)
       ON CONFLICT(key) DO UPDATE SET value=excluded.value`,
    );

    // Tüm 3 gün tek transaction — commit veya tamamen rollback
    db.transaction(() => {
      for (const day of days) {
        const dateStr = day.target_date;
        const playlists = day.playlists ?? [];

        if (playlists.length === 0) {
          // Boş authoritative gün: eski playlistleri sil
          delDatePlaylists.run(dateStr);
        } else {
          for (const pl of playlists) {
            upsertPlaylist.run({
              id: String(pl.id),
              target_date: dateStr,
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
        }
      }

      upsertMeta.run('playlist_version', String(manifestVersion ?? serverVersion));
      upsertMeta.run('playlist_date', today);
      upsertMeta.run('applied_horizon_start', horizon_start ?? '');
      upsertMeta.run('applied_horizon_end', horizon_end ?? '');

      // 6. Pending ACK kaydet (aynı transaction içinde)
      savePendingAck(db, {
        playlistVersion: manifestVersion ?? serverVersion,
        horizonStart: horizon_start ?? today,
        horizonEnd: horizon_end ?? today,
      });
    })();

    log.info?.(`MANIFEST sync tamam: 3 gün uygulandı (v${manifestVersion ?? serverVersion})`);
    await syncMediaCache(db, settings, log);

    // 7. ACK gönder
    const ackPayload = {
      playlist_version: manifestVersion ?? serverVersion,
      horizon_start: horizon_start ?? today,
      horizon_end: horizon_end ?? today,
    };
    try {
      const ackRes = await requestWithRetry(
        db, settings, 'POST', '/api/kiosk/v1/ack/', ackPayload, log,
      );
      if (ackRes.ok) {
        // 8. Koşullu sil: yalnızca bu manifest için pending ACK varsa temizle
        // Yeni manifest uygulanmışsa (daha yeni pending_ack) eski cevap onu silmez
        clearPendingAckIfMatches(db, {
          playlistVersion: ackPayload.playlist_version,
          horizonStart: ackPayload.horizon_start,
          horizonEnd: ackPayload.horizon_end,
        });
        log.info?.('ACK gönderildi ve temizlendi');
      } else {
        setAckNextRetry(db, 0);
        log.warn?.(`ACK HTTP ${ackRes.status}; pending bırakıldı`);
      }
    } catch (ackErr) {
      setAckNextRetry(db, 0);
      log.warn?.({ err: ackErr.message }, 'ACK gönderilemedi; pending ACK bırakıldı (retry)');
    }

  } catch (err) {
    log.warn?.({ err: err.message }, 'MANIFEST sync başarısız (offline mod)');
  }
}

/**
 * Pending ACK'i tekrar gönder (push cycle'da çağrılır).
 * Process crash + restart durumunda SQLite commit edilmiş ama ACK gönderilmemiş olabilir.
 */
export async function retryPendingAck(db, settings, log = console) {
  if (!hasCentralAuth(db, settings)) return;
  if (!settings.doohKioskAck) return;

  const { getPendingAck, clearPendingAckIfMatches, setAckNextRetry } = await import('./db.js');

  const pending = getPendingAck(db);
  if (!pending) return;

  // Capped backoff: skip this cycle if not yet time to retry
  if (pending.next_retry_at) {
    const nextRetryMs = new Date(pending.next_retry_at).getTime();
    if (!Number.isNaN(nextRetryMs) && nextRetryMs > Date.now()) {
      log.debug?.(`Pending ACK retry bekleniyor: next_retry_at=${pending.next_retry_at}`);
      return;
    }
  }

  try {
    const res = await requestWithRetry(
      db, settings, 'POST', '/api/kiosk/v1/ack/', {
        playlist_version: pending.playlist_version,
        horizon_start: pending.horizon_start,
        horizon_end: pending.horizon_end,
      }, log,
    );

    if (res.ok) {
      // Koşullu sil: daha yeni manifest uygulanmışsa (farklı version/horizon) silme
      clearPendingAckIfMatches(db, {
        playlistVersion: pending.playlist_version,
        horizonStart: pending.horizon_start,
        horizonEnd: pending.horizon_end,
      });
      log.info?.(`Pending ACK gönderildi (retry=${pending.retry_count})`);
    } else if (res.status === 409) {
      // FUTURE_REJECTED: backend'den daha ileri version ACK gönderildi.
      // Bu olanaksız ama eğer olursa manifesti zorla yeniden çek.
      // Pending ACK'i silme — yeni manifest sync onu üzerine yazacak.
      const { setAckNextRetry: setNextRetry } = await import('./db.js');
      setNextRetry(db, pending.retry_count);
      // Sonraki ping cycle'da resync zorla
      db.prepare(
        `INSERT INTO kiosk_meta (key, value) VALUES ('needs_manifest_resync', 'true')
         ON CONFLICT(key) DO UPDATE SET value='true'`,
      ).run();
      log.warn?.({ status: 409 }, 'Pending ACK FUTURE_REJECTED (409) — manifesti yeniden çek gerekiyor; ACK korunuyor');
    } else if (res.status === 401 || res.status === 403) {
      // Auth hatası: pending ACK'i koru, App Key'i değiştirme
      const { setAckNextRetry: setNextRetry } = await import('./db.js');
      setNextRetry(db, pending.retry_count);
      log.warn?.({ status: res.status }, 'Pending ACK auth hatası; korunuyor (App Key değiştirilmedi)');
    } else {
      // Diğer HTTP hataları (5xx, 429, vb.) — capped backoff ile tut
      const { setAckNextRetry: setNextRetry } = await import('./db.js');
      const { backoff } = setNextRetry(db, pending.retry_count);
      log.warn?.({ status: res.status, backoff }, `Pending ACK HTTP ${res.status}; ${backoff}s sonra tekrar denenir`);
    }
  } catch (err) {
    // Network timeout, connection error vb. — capped backoff, silme
    const { setAckNextRetry: setNextRetry } = await import('./db.js');
    const { backoff } = setNextRetry(db, pending.retry_count);
    log.warn?.({ err: err.message, backoff }, `Pending ACK ağ hatası; ${backoff}s sonra tekrar denenir`);
  }
}

// ── PUSH ─────────────────────────────────────────────────────────────────
export async function pushToCentral(db, settings, log = console) {
  if (!hasCentralAuth(db, settings)) {
    log.warn?.({ event: 'push_skipped_no_auth' }, 'PUSH atlandi: kiosk kimligi henuz provision edilmedi');
    return;
  }
  try {
    // Faz 5: Pending ACK retry (crash recovery — SQLite commit ama ACK gönderilmemiş olabilir)
    if (settings.doohKioskAck) {
      await retryPendingAck(db, settings, log).catch((err) =>
        log.warn?.({ err: err?.message }, 'Pending ACK retry atlandi'),
      );
    }

    // 1) oturum_outbox → /api/kiosk/v1/sessions/
    const oturumlar = db
      .prepare(
        `SELECT id, idempotency_anahtari, payload FROM oturum_outbox
          WHERE gonderilme_tarihi IS NULL AND retry_count < ${OUTBOX_MAX_RETRY} LIMIT 50`,
      )
      .all();
    if (oturumlar.length) {
      try {
        const r = await requestWithRetry(
          db, settings, 'POST', '/api/kiosk/v1/sessions/',
          { items: oturumlar.map((s) => JSON.parse(s.payload)) }, log,
        );
        if (r.status === 401) {
          handle401Error(db, settings, log);
        } else if (r.status === 403) {
          handle403Error(db, settings, log);
        } else {
          await consumeBulkPushResponse(db, 'oturum_outbox', oturumlar, r, log, 'sessions');
        }
      } catch (err) {
        log.warn?.({ event: 'push_sessions_failed', err: err.message }, 'PUSH sessions kalici hata; kayitlar saklaniyor');
        recordDiagnostic(db, {
          level: 'WARNING',
          event: 'sync_sessions_failed',
          message: err?.message || 'sessions push failed',
          context: { count: oturumlar.length, target_service: '/api/kiosk/v1/sessions/' },
        });
      }
    }

    // 2) reklam_gosterim_outbox → /api/kiosk/v1/proof-of-play/
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
        const r = await requestWithRetry(
          db, settings, 'POST', '/api/kiosk/v1/proof-of-play/',
          { logs }, log,
        );
        if (r.status === 201) {
          const del = db.prepare('DELETE FROM reklam_gosterim_outbox WHERE id = ?');
          const tx = db.transaction((items) => { for (const it of items) del.run(it.id); });
          tx(gosterimler);
          log.info?.({ event: 'proof_of_play_pushed', count: gosterimler.length }, 'PUSH proof-of-play basarili');
        } else if (r.status === 401) {
          handle401Error(db, settings, log);
        } else if (r.status === 403) {
          handle403Error(db, settings, log);
        } else {
          let body = null;
          try { body = await r.json(); } catch { body = null; }
          log.warn?.({ event: 'proof_of_play_push_failed', status: r.status, body }, 'PUSH proof-of-play basarisiz; kayitlar saklaniyor');
          recordDiagnostic(db, {
            level: 'WARNING',
            event: 'sync_proof_of_play_failed',
            message: `HTTP ${r.status}`,
            context: { count: gosterimler.length, status: r.status },
          });
        }
      } catch (err) {
        log.warn?.({ event: 'proof_of_play_push_error', err: err.message }, 'PUSH proof-of-play kalici hata; kayitlar saklaniyor');
        recordDiagnostic(db, {
          level: 'WARNING',
          event: 'sync_proof_of_play_failed',
          message: err?.message || 'proof-of-play push failed',
          context: { count: gosterimler.length },
        });
      }
    }
  } catch (err) {
    log.error?.({ event: 'push_scheduler_error', err: err?.message }, 'PUSH basarisiz (offline mod)');
    recordDiagnostic(db, {
      level: 'ERROR',
      event: 'push_scheduler_error',
      message: err?.message || 'push scheduler error',
    });
  }
}

/**
 * Backend 200/207 yanıtını işler — gerçek response şeması:
 *   { results: [{idempotency_key, status, qr_kodu}], errors: [{index, idempotency_anahtari, errors}] }
 *
 * Kabul edilenler (results): gonderilme_tarihi güncellenir.
 * Reddedilenler (errors):    retry_count artırılır, error_reason kaydedilir.
 */
async function consumeBulkPushResponse(db, table, rows, res, log, label) {
  if (!(res.status === 200 || res.status === 201 || res.status === 207)) {
    log?.warn?.({
      event: `push_${label}_http_error`,
      upstream_status: res.status,
      pending_count: rows.length,
    }, `PUSH ${label} HTTP ${res.status}; kayitlar saklaniyor`);
    return;
  }
  let body = null;
  try { body = await res.json(); } catch { body = {}; }

  // results[].idempotency_key — kabul edilen kayıtlar (created veya existing)
  const acceptedKeys = new Set(
    Array.isArray(body?.results)
      ? body.results
          .filter((r) => r.status === 'created' || r.status === 'existing')
          .map((r) => String(r.idempotency_key))
      : [],
  );

  // errors[].idempotency_anahtari — backend tarafından reddedilen kayıtlar
  const rejectedKeyErrors = new Map();
  if (Array.isArray(body?.errors)) {
    for (const e of body.errors) {
      if (e.idempotency_anahtari) {
        const keys = e.errors ? Object.keys(e.errors) : [];
        rejectedKeyErrors.set(String(e.idempotency_anahtari), keys);
      }
    }
  }

  const toAccept = rows.filter((r) => acceptedKeys.has(String(r.idempotency_anahtari)));
  const toReject = rows.filter((r) => rejectedKeyErrors.has(String(r.idempotency_anahtari)));

  if (toAccept.length) {
    const upd = db.prepare(`UPDATE ${table} SET gonderilme_tarihi = ? WHERE id = ?`);
    const tx = db.transaction((items) => {
      for (const it of items) upd.run(new Date().toISOString(), it.id);
    });
    tx(toAccept);
  }

  if (toReject.length && table === 'oturum_outbox') {
    const updErr = db.prepare(
      'UPDATE oturum_outbox SET retry_count = retry_count + 1, error_reason = ? WHERE id = ?',
    );
    const tx = db.transaction((items) => {
      for (const it of items) {
        const errorKeys = rejectedKeyErrors.get(String(it.idempotency_anahtari)) || [];
        updErr.run(JSON.stringify({ type: 'backend_validation', keys: errorKeys }), it.id);
      }
    });
    tx(toReject);
  }

  const unmatched = rows.length - toAccept.length - toReject.length;
  log?.info?.({
    event: `push_${label}_complete`,
    upstream_path: '/api/kiosk/v1/sessions/',
    upstream_status: res.status,
    kiosk_id: null,  // settings burada yok; scheduler çağıranı loglar
    batch_size: rows.length,
    accepted_count: toAccept.length,
    duplicate_count: Array.isArray(body?.results)
      ? body.results.filter((r) => r.status === 'existing').length
      : 0,
    rejected_count: toReject.length,
    unmatched_count: unmatched,
  }, `PUSH ${label}: ${toAccept.length} kabul, ${toReject.length} reddedildi, ${unmatched} eslesmeyen`);
}

export function startScheduler(db, settings, log = console) {
  if (_tasks.length) return;
  const pullEvery = settings.pullIntervalSec * 1000;
  const pushEvery = settings.pushIntervalSec * 1000;
  const pingEvery = (settings.pingIntervalSec ?? 60) * 1000;
  const diagEvery = (settings.diagnosticPushIntervalSec ?? 120) * 1000;

  const wrap = (label, fn) => () => {
    const cid = derivedId(label);
    runWithCorrelation(cid, () => Promise.resolve(fn()).catch((err) => {
      log?.warn?.({ event: `${label}_scheduler_error`, err: err?.message }, `${label} scheduler hatasi`);
    }));
  };

  const pullTimer = setInterval(wrap('pull', () => pullFromCentral(db, settings, log)), pullEvery);
  const pushTimer = setInterval(wrap('push', () => pushToCentral(db, settings, log)), pushEvery);
  // Faz 5: DOOH_KIOSK_ACK=true → manifest+ACK akışı, false → eski ping+playlist
  const pingFn = settings.doohKioskAck
    ? () => pingAndSyncManifest(db, settings, log)
    : () => pingAndSyncPlaylist(db, settings, log);
  const pingTimer = setInterval(wrap('ping', pingFn), pingEvery);
  const pressureTimer = setInterval(() => {
    try { checkOutboxPressure(log, settings.outboxMaxRows); }
    catch (err) { log?.warn?.({ event: 'outbox_pressure_check_failed', err: err?.message }, 'Outbox basinc kontrolu basarisiz'); }
  }, pushEvery);
  const diagTimer = setInterval(wrap('diag', () => pushDiagnostics(db, settings, log)), diagEvery);
  const cleanupTimer = setInterval(() => {
    try {
      const removed = cleanupOldDiagnostics(db, settings.diagnosticMaxAgeDays);
      if (removed) log?.debug?.({ event: 'diagnostic_cleanup', removed }, 'Yaslanmis diagnostic kayitlari silindi');
    } catch (err) { log?.warn?.({ event: 'diagnostic_cleanup_failed', err: err?.message }, 'Diagnostic temizlik basarisiz'); }
  }, Math.max(3600, (settings.diagnosticPushIntervalSec ?? 120) * 10) * 1000);

  pullTimer.unref?.();
  pushTimer.unref?.();
  pingTimer.unref?.();
  pressureTimer.unref?.();
  diagTimer.unref?.();
  cleanupTimer.unref?.();
  _tasks.push(pullTimer, pushTimer, pingTimer, pressureTimer, diagTimer, cleanupTimer);

  // Provisioning durumunu logla
  try {
    const provState = getProvisioningState(db);
    if (provState === 'PENDING_APPROVAL') {
      log.warn?.({ event: 'provisioning_pending' }, 'Kiosk provisioning PENDING_APPROVAL — admin onayi bekleniyor');
    } else if (provState === 'REJECTED') {
      log.warn?.({ event: 'provisioning_rejected' }, 'Kiosk provisioning REJECTED — admin ile iletisime gecin');
    }
  } catch { /* DB henuz hazir degil */ }

  // İlk açılışta hemen bir ping yap; Faz 5'te pending ACK varsa retry
  if (settings.doohKioskAck) {
    pingAndSyncManifest(db, settings, log);
    retryPendingAck(db, settings, log).catch(() => {});
  } else {
    pingAndSyncPlaylist(db, settings, log);
  }
  syncMediaCache(db, settings, log).catch((err) =>
    log.warn?.({ event: 'media_cache_bootstrap_failed', err: err?.message }, 'Baslangicta medya cache senkronizasyonu basarisiz'),
  );

  log.info?.({
    event: 'scheduler_started',
    pull_interval_sec: settings.pullIntervalSec,
    push_interval_sec: settings.pushIntervalSec,
    ping_interval_sec: settings.pingIntervalSec ?? 60,
    diagnostic_push_interval_sec: settings.diagnosticPushIntervalSec ?? 120,
  }, 'Scheduler baslatildi');
}

/**
 * Diagnostic outbox → backend /api/kiosk/v1/diagnostics/
 * Backend gelen kayitlari DB'ye YAZMAZ; normalize edip kendi stdout'una JSON log yazar.
 */
export async function pushDiagnostics(db, settings, log = console) {
  if (!hasCentralAuth(db, settings)) return;
  const batchSize = Math.min(100, settings.diagnosticBatchSize || 100);
  const pending = fetchPendingDiagnostics(db, batchSize);
  if (!pending.length) return;
  const ids = pending.map((r) => r.id);
  try {
    const res = await requestWithRetry(
      db, settings, 'POST', '/api/kiosk/v1/diagnostics/',
      { items: pending.map((r) => ({
        id: r.id,
        level: r.level,
        event: r.event,
        message: r.message,
        context: r.context,
        correlation_id: r.correlation_id,
        occurred_at: r.occurred_at,
      })) }, log,
    );
    if (res.status === 202 || res.status === 200) {
      markDiagnosticsSent(db, ids);
      log?.debug?.({ event: 'diagnostic_pushed', count: pending.length }, 'Diagnostic kayitlari gonderildi');
    } else if (res.status === 401) {
      handle401Error(db, settings, log);
      reschedulePendingDiagnostics(db, ids, pending[0].retry_count);
    } else if (res.status === 403) {
      handle403Error(db, settings, log);
      reschedulePendingDiagnostics(db, ids, pending[0].retry_count);
    } else {
      reschedulePendingDiagnostics(db, ids, pending[0].retry_count);
      log?.warn?.({ event: 'diagnostic_push_failed', status: res.status }, 'Diagnostic gonderim reddedildi');
    }
  } catch (err) {
    reschedulePendingDiagnostics(db, ids, pending[0]?.retry_count ?? 0);
    log?.warn?.({ event: 'diagnostic_push_error', err: err?.message }, 'Diagnostic gonderim hatasi');
  }
}

export function stopScheduler() {
  for (const t of _tasks) clearInterval(t);
  _tasks = [];
}

export { cron };
