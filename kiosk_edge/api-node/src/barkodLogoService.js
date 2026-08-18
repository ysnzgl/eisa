/**
 * Barkod Logo Servisi — round-robin rotasyon, günlük sayaç, cache yönetimi.
 *
 * Bağımlılıklar: yalnız Node.js built-in modüller + better-sqlite3 (zaten projede mevcut).
 * Yeni bağımlılık eklenmez.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { Agent, fetch } from 'undici';

import { istanbulNow } from './timezone.js';
import { getAuthHeaders } from './provisioning.js';

let _agent = null;
function getAgent(verifyTls) {
  if (_agent) return _agent;
  _agent = new Agent({ connect: { rejectUnauthorized: !!verifyTls } });
  return _agent;
}

// ─── Sayaç yardımcıları ───────────────────────────────────────────────────

/** Backend URL'leri için App Key auth header'ları üret; dış URL'ler için boş ob. */
function _mediaAuthHeaders(db, settings, url) {
  if (!settings?.centralApiBase || !url) return {};
  const base = settings.centralApiBase.replace(/\/+$/, '');
  if (!url.startsWith(base)) return {};
  return getAuthHeaders(db);
}


/** Bugünün Istanbul takvim tarihini 'YYYY-MM-DD' formatında döner. */
function todayIstanbul() {
  return istanbulNow().date;
}

/**
 * Bir logo için bugün kaç kez başarıyla basıldığını döner.
 * Sayaç `barkod_logo_baski_sayaclari` tablosunda saklanır.
 */
export function getGunlukSayi(db, logoId) {
  const today = todayIstanbul();
  const row = db
    .prepare('SELECT sayi FROM barkod_logo_baski_sayaclari WHERE logo_id = ? AND tarih_istanbul = ?')
    .get(logoId, today);
  return row ? row.sayi : 0;
}

/**
 * Başarılı baskı sonrası günlük sayacı 1 artırır.
 * Yalnız başarılı yazıcı transport'u sonrası çağrılmalıdır.
 */
export function artirGunlukSayi(db, logoId) {
  const today = todayIstanbul();
  db.prepare(`
    INSERT INTO barkod_logo_baski_sayaclari (logo_id, tarih_istanbul, sayi)
    VALUES (?, ?, 1)
    ON CONFLICT(logo_id, tarih_istanbul) DO UPDATE SET sayi = sayi + 1
  `).run(logoId, today);
}

/**
 * 7 günden eski sayaç kayıtlarını temizler (yalnız verimlilik için; veri kaybı olmaz).
 * Periyodik çağrılabilir; her gece bir kez yeterli.
 */
export function temizleEskiSayaclar(db) {
  const cutoff = istanbulNow();
  // 7 gün önce (ISO string karşılaştırması çalışır çünkü YYYY-MM-DD formatı sıralı)
  const cutoffDate = new Date(cutoff.isoString);
  cutoffDate.setDate(cutoffDate.getDate() - 7);
  const cutoffStr = cutoffDate.toISOString().slice(0, 10);
  db.prepare('DELETE FROM barkod_logo_baski_sayaclari WHERE tarih_istanbul < ?').run(cutoffStr);
}

// ─── Round-robin cursor ───────────────────────────────────────────────────

/** Son başarıyla basılan logo ID'sini kiosk_meta'dan okur. */
function getLastLogoId(db) {
  const row = db.prepare("SELECT value FROM kiosk_meta WHERE key = 'last_barkod_logo_id'").get();
  return row?.value ? String(row.value) : null;
}

/** Son başarıyla basılan logo ID'sini kiosk_meta'ya yazar. */
export function setLastLogoId(db, logoId) {
  db.prepare(`
    INSERT INTO kiosk_meta (key, value) VALUES ('last_barkod_logo_id', ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
  `).run(String(logoId ?? ''));
}

/**
 * Başarılı baskı sonrası tek atomik SQLite transaction:
 *   - Günlük sayaç +1
 *   - Round-robin cursor ilerlet
 *   - Outbox payload'a barkod_logo_id yaz
 *
 * Yazıcı transport hatası durumunda bu fonksiyon ÇAĞRILMAZ.
 * Süreç çökmesi (transport başarılı ama transaction tamamlanmadan):
 *   → outbox barkod_logo_id null kalır → scheduler null ile gönderir
 *   → Bu muhafazakâr/güvenli davranıştır: baskı gerçekleşmiş olsa da
 *     backend'e "fallback kullanıldı" bildirilir. Fiziksel baskıyı
 *     yazılım teyit edemediği için bu en dürüst yaklaşımdır.
 */
export function commitBasariliBaski(db, logoId, idempotencyAnahtari) {
  db.transaction(() => {
    artirGunlukSayi(db, logoId);
    setLastLogoId(db, logoId);
    const row = db.prepare('SELECT payload FROM oturum_outbox WHERE idempotency_anahtari = ?').get(idempotencyAnahtari);
    if (row) {
      try {
        const p = JSON.parse(row.payload);
        p.barkod_logo_id = logoId;
        db.prepare('UPDATE oturum_outbox SET payload = ? WHERE idempotency_anahtari = ?').run(JSON.stringify(p), idempotencyAnahtari);
      } catch { /* JSON parse hatası: barkod_logo_id null kalır, güvenli */ }
    }
  })();
}

// ─── Uygunluk kontrolü ────────────────────────────────────────────────────

/**
 * Bir logo o an için uygun mu?
 * Koşullar:
 *   1. aktif = 1
 *   2. baslangic_zamani <= now (UTC ISO string karşılaştırması)
 *   3. now < bitis_zamani
 *   4. Günlük limit dolmamış
 *   5. Lokal cache dosyası mevcut ve geçerli (checksum uyuşuyor)
 */
function isLogoUygun(db, logo, nowIso) {
  if (!logo.aktif) return false;
  if (logo.baslangic_zamani > nowIso) return false;
  if (logo.bitis_zamani <= nowIso) return false;

  if (logo.gunluk_limit !== null && logo.gunluk_limit !== undefined) {
    const sayi = getGunlukSayi(db, logo.id);
    if (sayi >= logo.gunluk_limit) return false;
  }

  if (!logo.local_path || logo.cache_status !== 'ready') return false;
  if (!fs.existsSync(logo.local_path)) return false;
  // Checksum doğrulama
  if (logo.checksum) {
    try {
      const data = fs.readFileSync(logo.local_path);
      const computed = crypto.createHash('sha256').update(data).digest('hex');
      const expected = logo.checksum.startsWith('sha256:')
        ? logo.checksum.slice(7)
        : logo.checksum;
      if (computed !== expected) return false;
    } catch {
      return false;
    }
  }
  return true;
}

// ─── Logo seçimi (round-robin) ────────────────────────────────────────────

/**
 * Tüm uygun logoları round-robin sırasında döner.
 * İlk eleman "şu an seçilmesi gereken" logo, ardından sıradakiler.
 * Bozuk (raster hatası) bir aday atlandığında bir sonraki denenir.
 * Cursor yalnız başarılı baskı sonrası ilerler (setLastLogoId çağrısıyla).
 * Boş dizi → hiç uygun logo yok → e-ISA fallback kullanılacak.
 */
export function getOrderedLogoCandidates(db) {
  const nowIso = new Date().toISOString();
  const tum = db.prepare(`
    SELECT id, ad, media_url, checksum, baslangic_zamani, bitis_zamani,
           aktif, gunluk_limit, local_path, cache_status
    FROM barkod_logolar
    ORDER BY synced_at ASC, id ASC
  `).all();

  const uygunlar = tum.filter((l) => isLogoUygun(db, l, nowIso));
  if (!uygunlar.length) return [];

  const lastId = getLastLogoId(db);
  if (!lastId) return uygunlar;

  const lastIdx = uygunlar.findIndex((l) => String(l.id) === lastId);
  if (lastIdx === -1) return uygunlar;

  const nextIdx = (lastIdx + 1) % uygunlar.length;
  return [...uygunlar.slice(nextIdx), ...uygunlar.slice(0, nextIdx)];
}

/**
 * Bir sonraki uygun logoyu döner (round-robin). Yalnız ilk adayı verir.
 * Birden fazla adayı denemek için getOrderedLogoCandidates kullanılır.
 */
export function seciSonrakiLogo(db) {
  return getOrderedLogoCandidates(db)[0] ?? null;
}

// ─── Cache yönetimi ────────────────────────────────────────────────────────

/**
 * Barkod logolarının local cache'ini günceller.
 * Catalog'dan alınan logo listesini SQLite'a yazar ve gerekli görselleri indirir.
 *
 * @param {import('better-sqlite3').Database} db
 * @param {object[]} logolar - catalog endpoint'inden gelen barkod_logolar listesi
 * @param {string} mediaDir - lokal medya dizini
 * @param {boolean} verifyTls
 * @param {object} log
 */
export async function syncBarkodLogoCache(db, logolar, mediaDir, verifyTls, log, settings = null) {
  if (!logolar || !logolar.length) {
    // Catalog'da logo yok → DB'yi temizle (snapshot reconciliation)
    db.prepare('DELETE FROM barkod_logolar').run();
    return;
  }

  // 1) Gelen ID'leri kaydet
  const gelenIds = new Set(logolar.map((l) => String(l.id)));

  // 2) Artık katalogda olmayan logoları kaldır (snapshot reconciliation)
  const eskiler = db.prepare('SELECT id FROM barkod_logolar').all();
  for (const eski of eskiler) {
    if (!gelenIds.has(eski.id)) {
      db.prepare('DELETE FROM barkod_logolar WHERE id = ?').run(eski.id);
      // Cache dosyasını temizle (güvenli: sadece bu logo için olan dosyayı sil)
      const localPath = path.join(mediaDir, `barkod_logo_${eski.id}.png`);
      if (fs.existsSync(localPath)) {
        try { fs.unlinkSync(localPath); } catch { /* dosya zaten silinmiş */ }
      }
    }
  }

  // 3) Gelen logoları upsert et ve gerekirse indir
  if (!fs.existsSync(mediaDir)) {
    fs.mkdirSync(mediaDir, { recursive: true });
  }

  for (const logo of logolar) {
    const logoId = String(logo.id);
    const localPath = path.join(mediaDir, `barkod_logo_${logoId}.png`);
    const existing = db.prepare('SELECT checksum, cache_status FROM barkod_logolar WHERE id = ?').get(logoId);

    // Cache hit: checksum uyuşuyor ve dosya var
    const cacheHit = existing
      && existing.checksum === (logo.checksum || '')
      && existing.cache_status === 'ready'
      && fs.existsSync(localPath);

    let cacheStatus = 'pending';
    if (cacheHit) {
      cacheStatus = 'ready';
    } else if (logo.media_url) {
      // İndir
      try {
        const tmpPath = `${localPath}.tmp`;
        const authHeaders = _mediaAuthHeaders(db, settings, logo.media_url);
        const res = await fetch(logo.media_url, {
          method: 'GET',
          headers: authHeaders,
          dispatcher: getAgent(verifyTls),
          signal: AbortSignal.timeout(30000),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const buf = Buffer.from(await res.arrayBuffer());
        fs.writeFileSync(tmpPath, buf);
        fs.renameSync(tmpPath, localPath);
        cacheStatus = 'ready';
        log?.info?.({ logoId, size: buf.length }, 'Barkod logo indirildi');
      } catch (err) {
        cacheStatus = existing?.cache_status === 'ready' && fs.existsSync(localPath) ? 'ready' : 'error';
        log?.warn?.({ logoId, err: err?.message }, 'Barkod logo indirilemedi; varsa eski cache kullanılır');
      }
    }

    db.prepare(`
      INSERT INTO barkod_logolar
        (id, ad, media_url, checksum, baslangic_zamani, bitis_zamani, aktif, gunluk_limit, local_path, cache_status, synced_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))
      ON CONFLICT(id) DO UPDATE SET
        ad = excluded.ad,
        media_url = excluded.media_url,
        checksum = excluded.checksum,
        baslangic_zamani = excluded.baslangic_zamani,
        bitis_zamani = excluded.bitis_zamani,
        aktif = excluded.aktif,
        gunluk_limit = excluded.gunluk_limit,
        local_path = excluded.local_path,
        cache_status = excluded.cache_status,
        synced_at = excluded.synced_at
    `).run(
      logoId,
      logo.ad || '',
      logo.media_url || '',
      logo.checksum || '',
      logo.baslangic_zamani || '',
      logo.bitis_zamani || '',
      1,  // catalog'da olanlar aktif (pasifler zaten gelmez)
      logo.gunluk_baski_limiti ?? null,
      cacheStatus === 'ready' ? localPath : (existing?.local_path || localPath),
      cacheStatus,
    );
  }
}

/**
 * DB'deki eksik/hatalı barkod logo dosyalarını yeniden indirir.
 * Catalog listesi gerekmez — mevcut barkod_logolar tablosunu okur.
 * syncMediaCache ile birlikte çağrılır: DOOH media sync sırasında logoları da günceller.
 */
export async function syncBarkodLogoFiles(db, mediaDir, verifyTls, log, settings = null) {
  const eksik = db.prepare(`
    SELECT id, media_url, checksum, local_path
    FROM barkod_logolar
    WHERE media_url != ''
      AND (cache_status != 'ready' OR local_path = '' OR local_path IS NULL)
  `).all();

  // Dosyası silinmiş ama cache_status='ready' olanları da yakala
  const silinmis = db.prepare(`
    SELECT id, media_url, checksum, local_path
    FROM barkod_logolar
    WHERE cache_status = 'ready' AND local_path != '' AND local_path IS NOT NULL AND media_url != ''
  `).all().filter((r) => !fs.existsSync(r.local_path));

  const hedefler = [...eksik, ...silinmis];
  if (!hedefler.length) return;

  if (!fs.existsSync(mediaDir)) fs.mkdirSync(mediaDir, { recursive: true });

  for (const logo of hedefler) {
    const logoId = String(logo.id);
    const localPath = path.join(mediaDir, `barkod_logo_${logoId}.png`);
    try {
      const tmpPath = `${localPath}.tmp`;
      const authHeaders = _mediaAuthHeaders(db, settings, logo.media_url);
      const res = await fetch(logo.media_url, {
        method: 'GET',
        headers: authHeaders,
        dispatcher: getAgent(verifyTls),
        signal: AbortSignal.timeout(30000),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const buf = Buffer.from(await res.arrayBuffer());
      fs.writeFileSync(tmpPath, buf);
      fs.renameSync(tmpPath, localPath);
      db.prepare(
        "UPDATE barkod_logolar SET local_path = ?, cache_status = 'ready' WHERE id = ?",
      ).run(localPath, logoId);
      log?.info?.({ logoId, size: buf.length }, 'Barkod logo dosyası (retry) indirildi');
    } catch (err) {
      log?.warn?.({ logoId, err: err?.message }, 'Barkod logo dosyası retry indirilemedi');
    }
  }
}
