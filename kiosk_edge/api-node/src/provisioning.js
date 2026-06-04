/**
 * Kiosk otomatik kimlik yonetimi (provisioning + IoT token).
 *
 * Akis:
 *   1. MAC adresi sistemden okunur (veya DB cache'ten).
 *   2. Gecerli bir IoT token varsa (suresine en az 24h kalmis) kullanilir.
 *   3. Token yoksa ya da yukleniyor:
 *      - HMAC-SHA256(MAC_UPPER + iso_timestamp, provisioningSecret) imzalanir.
 *      - POST /api/pharmacies/kiosks/bootstrap/ cagrilir (X-Kiosk-Key + HMAC body).
 *      - Donen IoT token kiosk_meta'ya yazilir.
 *   4. getAuthHeaders(db, settings): her backend istegi icin header nesnesi doner.
 *
 * eczaci terminali sorgu sifresi olarak KIOSK_PROVISIONING_SECRET kullanilir.
 */
import crypto from 'node:crypto';
import os from 'node:os';
import { Agent, fetch } from 'undici';

// ── Yardimcilar ──────────────────────────────────────────────────────────────

function getMeta(db, key) {
  const row = db.prepare('SELECT value FROM kiosk_meta WHERE key = ?').get(key);
  return row?.value ?? '';
}

function setMeta(db, key, value) {
  db.prepare(
    `INSERT INTO kiosk_meta (key, value) VALUES (?, ?)
     ON CONFLICT(key) DO UPDATE SET value=excluded.value`,
  ).run(key, String(value));
}

function parseIntSafe(value, fallback = 0) {
  const n = Number.parseInt(value, 10);
  return Number.isFinite(n) ? n : fallback;
}

export function normalizeMac(raw) {
  return String(raw || '').trim().toUpperCase().replace(/-/g, ':');
}

export function detectSystemMacAddress() {
  const ifaces = os.networkInterfaces();
  for (const entries of Object.values(ifaces)) {
    for (const item of entries || []) {
      if (!item || item.internal) continue;
      const mac = normalizeMac(item.mac);
      if (!mac || mac === '00:00:00:00:00:00') continue;
      if (!/^([0-9A-F]{2}:){5}[0-9A-F]{2}$/.test(mac)) continue;
      return mac;
    }
  }
  return '';
}

// ── HMAC imzalama ────────────────────────────────────────────────────────────

function signProvisionRequest(mac, isoTimestamp, secret) {
  const message = mac.toUpperCase() + isoTimestamp;
  return crypto.createHmac('sha256', secret).update(message).digest('hex');
}

// ── IoT token ayristirma (imza dogrulamadan sadece payload) ──────────────────

function parseIotTokenPayload(token) {
  try {
    const [payloadB64] = token.split('.');
    const padding = 4 - (payloadB64.length % 4);
    const padded = payloadB64 + '='.repeat(padding % 4);
    return JSON.parse(Buffer.from(padded, 'base64url').toString('utf8'));
  } catch {
    return null;
  }
}

function isIotTokenAlive(token, minRemainingHours = 24) {
  if (!token) return false;
  const payload = parseIotTokenPayload(token);
  if (!payload?.exp) return false;
  const remaining = payload.exp - Math.floor(Date.now() / 1000);
  return remaining > minRemainingHours * 3600;
}

// ── Backend provision istegi ─────────────────────────────────────────────────

async function fetchIotToken(settings, mac, log) {
  if (!settings.kioskProvisioningSecret || !settings.kioskFleetKey) {
    log?.warn?.('IoT token alinamadi: KIOSK_FLEET_KEY veya KIOSK_PROVISIONING_SECRET tanimlanmamis');
    return null;
  }

  const timestamp = new Date().toISOString();
  const hmac = signProvisionRequest(mac, timestamp, settings.kioskProvisioningSecret);
  const base = settings.centralApiBase.replace(/\/+$/, '');
  const url = `${base}${settings.kioskBootstrapPath}`;
  const agent = new Agent({ connect: { rejectUnauthorized: !!settings.verifyTls } });

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Kiosk-Key': settings.kioskFleetKey,
      },
      body: JSON.stringify({ mac_adresi: mac, timestamp, hmac }),
      dispatcher: agent,
      signal: AbortSignal.timeout(10000),
    });

    if (!res.ok) {
      const detail = await res.text();
      log?.warn?.({ status: res.status, detail }, 'Kiosk provision yaniti basarisiz');
      return null;
    }

    const data = await res.json();
    return data;
  } catch (err) {
    log?.warn?.({ err: err?.message }, 'Kiosk provision istegi basarisiz');
    return null;
  } finally {
    try { await agent.close(); } catch {}
  }
}

// ── Public: tam runtime ayarlarini coz ───────────────────────────────────────

export async function resolveRuntimeSettings(db, baseSettings, log = console) {
  const runtime = { ...baseSettings };

  // 1) MAC
  runtime.kioskMac = normalizeMac(
    runtime.kioskMac || getMeta(db, 'kiosk_mac') || detectSystemMacAddress(),
  );
  if (runtime.kioskMac) setMeta(db, 'kiosk_mac', runtime.kioskMac);

  // 2) IoT token icin PROVISIONING_SECRET ayni zamanda eczaci terminali sorgusu icin de kullanilir.

  // 3) Mevcut IoT token kontrolu
  const cachedToken = getMeta(db, 'iot_token');
  if (isIotTokenAlive(cachedToken)) {
    const payload = parseIotTokenPayload(cachedToken);
    runtime.iotToken    = cachedToken;
    runtime.kioskId     = runtime.kioskId     || payload?.kiosk_id    || 0;
    runtime.pharmacyId  = runtime.pharmacyId  || payload?.pharmacy_id || 0;
    log?.info?.({ kioskId: runtime.kioskId }, 'IoT token gecerli, provision atlanıyor');
    return Object.freeze(runtime);
  }

  // 4) Token yok veya suresi yakin — provision yap
  if (runtime.kioskMac && runtime.kioskProvisioningSecret && runtime.kioskFleetKey) {
    const data = await fetchIotToken(runtime, runtime.kioskMac, log);
    if (data?.iot_token) {
      runtime.iotToken   = data.iot_token;
      runtime.kioskId    = data.kiosk_id    || 0;
      runtime.pharmacyId = data.pharmacy_id || 0;
      setMeta(db, 'iot_token',   runtime.iotToken);
      setMeta(db, 'kiosk_id',    runtime.kioskId);
      setMeta(db, 'pharmacy_id', runtime.pharmacyId);
      log?.info?.({ kioskId: runtime.kioskId, pharmacyId: runtime.pharmacyId }, 'Kiosk provision tamamlandi');
    }
  } else {
    log?.warn?.('Provision atlanıyor: kioskMac, kioskFleetKey veya kioskProvisioningSecret eksik');
  }

  // 5) Legacy AppKey fallback (dev/test)
  if (!runtime.iotToken) {
    runtime.kioskAppKey = runtime.kioskAppKey || getMeta(db, 'kiosk_app_key');
    runtime.kioskId     = runtime.kioskId     || parseIntSafe(getMeta(db, 'kiosk_id'));
    runtime.pharmacyId  = runtime.pharmacyId  || parseIntSafe(getMeta(db, 'pharmacy_id'));
  }

  return Object.freeze(runtime);
}

// ── Public: her backend istegi icin auth header nesnesi ─────────────────────

/**
 * Her scheduler/push/pull isteginde cagrilir.
 * Token suresine 24h'den az kalmissa arka planda yeniler.
 */
export function getAuthHeaders(db, settings) {
  const headers = {};

  if (settings.kioskFleetKey) {
    headers['X-Kiosk-Key'] = settings.kioskFleetKey;
  }

  // IoT token tercih edilir — sadece suresi dolmamis token gonder
  const iotToken = getMeta(db, 'iot_token');
  if (iotToken && isIotTokenAlive(iotToken, 0)) {
    headers['Authorization'] = `Bearer ${iotToken}`;
    return headers;
  }

  // Legacy AppKey fallback
  if (settings.kioskAppKey && settings.kioskMac) {
    headers['Authorization'] = `AppKey ${settings.kioskAppKey}`;
    headers['X-Kiosk-MAC']   = settings.kioskMac;
  }

  return headers;
}

/**
 * Arka planda token yenileme — scheduler her ping dongusunde cagirabilir.
 * Token suresine 24h'den az kaldiysa provision yenilenir.
 */
export async function refreshIotTokenIfNeeded(db, settings, log = console) {
  const token = getMeta(db, 'iot_token');
  if (isIotTokenAlive(token, 24)) return; // henuz erken

  const mac = getMeta(db, 'kiosk_mac') || settings.kioskMac;
  if (!mac || !settings.kioskProvisioningSecret || !settings.kioskFleetKey) return;

  log?.info?.('IoT token yenileniyor…');
  const data = await fetchIotToken(settings, mac, log);
  if (data?.iot_token) {
    setMeta(db, 'iot_token', data.iot_token);
    log?.info?.('IoT token yenilendi');
  }
}
