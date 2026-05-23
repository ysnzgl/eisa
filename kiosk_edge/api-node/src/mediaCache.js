import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { Agent, fetch } from 'undici';

let _running = false;
let _agent = null;

function getAgent(verifyTls) {
  if (_agent) return _agent;
  _agent = new Agent({ connect: { rejectUnauthorized: !!verifyTls } });
  return _agent;
}

function keyOf(assetType, assetId) {
  return `${assetType}:${String(assetId)}`;
}

function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) fs.mkdirSync(dirPath, { recursive: true });
}

function extensionFromUrl(rawUrl) {
  try {
    const { pathname } = new URL(rawUrl);
    const ext = path.extname(pathname || '').toLowerCase();
    if (!ext || ext.length > 8) return '.bin';
    return ext;
  } catch {
    return '.bin';
  }
}

function mimeFromExt(ext) {
  const e = String(ext || '').toLowerCase();
  if (e === '.mp4') return 'video/mp4';
  if (e === '.webm') return 'video/webm';
  if (e === '.ogg') return 'video/ogg';
  if (e === '.jpg' || e === '.jpeg') return 'image/jpeg';
  if (e === '.png') return 'image/png';
  if (e === '.gif') return 'image/gif';
  if (e === '.webp') return 'image/webp';
  return 'application/octet-stream';
}

function normalizeAssets(db) {
  const creatives = db
    .prepare('SELECT id, media_url, checksum FROM creatives WHERE aktif = 1')
    .all()
    .filter((x) => !!x.media_url)
    .map((x) => ({
      asset_id: String(x.id),
      asset_type: 'creative',
      media_url: x.media_url,
      source_checksum: x.checksum || '',
    }));

  const houseAds = db
    .prepare('SELECT id, media_url FROM house_ads WHERE aktif = 1')
    .all()
    .filter((x) => !!x.media_url)
    .map((x) => ({
      asset_id: String(x.id),
      asset_type: 'house_ad',
      media_url: x.media_url,
      source_checksum: '',
    }));

  return [...creatives, ...houseAds];
}

async function downloadToFile(url, filePath, verifyTls) {
  const res = await fetch(url, {
    method: 'GET',
    dispatcher: getAgent(verifyTls),
    signal: AbortSignal.timeout(30000),
  });

  if (!res.ok) {
    throw new Error(`Medya indirme HTTP ${res.status}`);
  }

  const data = Buffer.from(await res.arrayBuffer());
  fs.writeFileSync(filePath, data);
  return {
    size: data.length,
    sha256: crypto.createHash('sha256').update(data).digest('hex'),
  };
}

export async function syncMediaCache(db, settings, log = console) {
  if (_running) return;
  _running = true;

  try {
    ensureDir(settings.mediaDir);

    const assets = normalizeAssets(db);
    const liveKeys = new Set(assets.map((a) => keyOf(a.asset_type, a.asset_id)));

    const cached = db.prepare('SELECT * FROM media_cache').all();
    const cachedMap = new Map(cached.map((r) => [keyOf(r.asset_type, r.asset_id), r]));

    const upsert = db.prepare(`
      INSERT INTO media_cache
        (asset_id, asset_type, source_url, source_checksum, file_checksum,
         local_path, mime_type, file_size, status, error_message, synced_at)
      VALUES
        (@asset_id, @asset_type, @source_url, @source_checksum, @file_checksum,
         @local_path, @mime_type, @file_size, @status, @error_message,
         strftime('%Y-%m-%dT%H:%M:%fZ','now'))
      ON CONFLICT(asset_id, asset_type) DO UPDATE SET
        source_url=excluded.source_url,
        source_checksum=excluded.source_checksum,
        file_checksum=excluded.file_checksum,
        local_path=excluded.local_path,
        mime_type=excluded.mime_type,
        file_size=excluded.file_size,
        status=excluded.status,
        error_message=excluded.error_message,
        synced_at=excluded.synced_at
    `);

    const delCache = db.prepare('DELETE FROM media_cache WHERE asset_id = ? AND asset_type = ?');

    for (const asset of assets) {
      const ext = extensionFromUrl(asset.media_url);
      const mimeType = mimeFromExt(ext);
      const localName = `${asset.asset_type}_${asset.asset_id}${ext}`;
      const localPath = path.join(settings.mediaDir, localName);
      const k = keyOf(asset.asset_type, asset.asset_id);
      const prev = cachedMap.get(k);

      const localReady = !!prev
        && prev.status === 'ready'
        && prev.source_url === asset.media_url
        && prev.source_checksum === asset.source_checksum
        && fs.existsSync(prev.local_path);

      if (localReady) continue;

      try {
        const tmpPath = `${localPath}.tmp`;
        const downloaded = await downloadToFile(asset.media_url, tmpPath, settings.verifyTls);
        fs.renameSync(tmpPath, localPath);

        upsert.run({
          asset_id: asset.asset_id,
          asset_type: asset.asset_type,
          source_url: asset.media_url,
          source_checksum: asset.source_checksum,
          file_checksum: downloaded.sha256,
          local_path: localPath,
          mime_type: mimeType,
          file_size: downloaded.size,
          status: 'ready',
          error_message: '',
        });
      } catch (err) {
        upsert.run({
          asset_id: asset.asset_id,
          asset_type: asset.asset_type,
          source_url: asset.media_url,
          source_checksum: asset.source_checksum,
          file_checksum: prev?.file_checksum || '',
          local_path: prev?.local_path || localPath,
          mime_type: prev?.mime_type || mimeType,
          file_size: prev?.file_size || 0,
          status: fs.existsSync(prev?.local_path || '') ? 'ready' : 'error',
          error_message: err?.message || 'Indirme hatasi',
        });
        log.warn?.({ asset: k, err: err?.message }, 'Medya indirilemedi; varsa lokal kopya kullanilacak');
      }
    }

    for (const row of cached) {
      const k = keyOf(row.asset_type, row.asset_id);
      if (liveKeys.has(k)) continue;
      try {
        if (row.local_path && fs.existsSync(row.local_path)) fs.unlinkSync(row.local_path);
      } catch {
        // file cleanup best-effort
      }
      delCache.run(row.asset_id, row.asset_type);
    }
  } finally {
    _running = false;
  }
}

export function getLocalMediaMeta(db, assetType, assetId) {
  return db.prepare(
    `SELECT local_path, mime_type, status
       FROM media_cache
      WHERE asset_type = ? AND asset_id = ?
      LIMIT 1`,
  ).get(assetType, String(assetId));
}

export function buildMediaUrl(db, assetType, assetId, sourceUrl) {
  const row = getLocalMediaMeta(db, assetType, assetId);
  if (row && row.status === 'ready' && row.local_path && fs.existsSync(row.local_path)) {
    return `/api/media/${assetType}/${assetId}`;
  }
  return sourceUrl;
}
