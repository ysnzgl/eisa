/**
 * Kiosk otomatik kimlik yonetimi (provisioning + IoT token).
 *
 * Durum makinesi:
 *   UNREGISTERED      — Henuz bootstrap yapilmamis
 *       ↓ bootstrap request (fleet key + HMAC)
 *   PENDING_APPROVAL  — Backend 202 dondu, admin onayi bekleniyor
 *       ↓ polling (retry_after_seconds veya backoff)
 *   APPROVED          — Admin onayladi, kiosk_id ve iot_token mevcut
 *       ↓ normal IoT auth akisina gec
 *   PROVISIONED       — iot_token SQLite'a yazildi, normal operation
 *   REJECTED          — Admin reddetti, manuel mudahale gerekir
 *
 * Akis:
 *   1. MAC adresi sistemden okunur (veya DB cache'ten).
 *   2. Gecerli bir IoT token varsa (suresine en az 24h kalmis) kullanilir.
 *   3. Token yoksa:
 *      a. PENDING_APPROVAL durumundaysa → bootstrap yeniden dene (backoff)
 *      b. Aksi halde → HMAC-SHA256(MAC_UPPER + iso_timestamp, provisioningSecret) imzalanir.
 *      c. POST /api/pharmacies/kiosks/bootstrap/ cagrilir.
 *      d. 200  → IoT token kiosk_meta'ya yazilir (PROVISIONED)
 *      e. 202  → PENDING_APPROVAL, registration_id kiosk_meta'ya yazilir
 *      f. 403  → REJECTED durumu; token alinmaz
 *   4. getAuthHeaders(db, settings): her backend istegi icin header nesnesi doner.
 *
 * Guvenlik:
 *   - KIOSK_PROVISIONING_SECRET ve KIOSK_FLEET_KEY loglarda goruntulenmez.
 *   - REJECTED durumunda iot_token verilmez, normal API'lere erisim engellenir.
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

/**
 * Makine uzerinden guvenli cihaz metadata toplar.
 * Kimlik bilgisi, token veya secret ICERMEZ.
 */
export function collectDeviceMetadata() {
  const metadata = {};

  // Makine adi ve isletim sistemi
  try { metadata.hostname         = os.hostname(); } catch {}
  try { metadata.os_type          = os.type(); } catch {}       // Linux / Windows_NT / Darwin
  try { metadata.os_platform      = os.platform(); } catch {}   // linux / win32 / darwin
  try { metadata.os_release       = os.release(); } catch {}    // kernel / OS surumu
  try { metadata.arch             = os.arch(); } catch {}        // x64 / arm64 / arm

  // CPU
  try {
    const cpus = os.cpus();
    if (cpus?.length) {
      metadata.cpu_model   = cpus[0].model.trim();
      metadata.cpu_cores   = cpus.length;
    }
  } catch {}

  // Bellek (MB)
  try { metadata.total_memory_mb = Math.round(os.totalmem() / 1048576); } catch {}

  // IPv4 adresleri (dahili olmayan, loopback haric)
  try {
    const ips = [];
    for (const [name, entries] of Object.entries(os.networkInterfaces() || {})) {
      for (const iface of entries || []) {
        if (iface.internal || iface.family !== 'IPv4') continue;
        ips.push({ iface: name, address: iface.address });
      }
    }
    if (ips.length) metadata.ip_addresses = ips;
  } catch {}

  // Node.js surumu
  try { metadata.node_version = process.version; } catch {}

  // Sistem uptime (saniye, tam sayi)
  try { metadata.uptime_seconds = Math.floor(os.uptime()); } catch {}

  return metadata;
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

// ── Provisioning state yardimcilari ─────────────────────────────────────────

/** Izin verilen provisioning durumlar */
const PROVISIONING_STATE = Object.freeze({
  UNREGISTERED:     'UNREGISTERED',
  PENDING_APPROVAL: 'PENDING_APPROVAL',
  APPROVED:         'APPROVED',
  REJECTED:         'REJECTED',
});

export function getProvisioningState(db) {
  try {
    const row = db.prepare("SELECT value FROM kiosk_meta WHERE key='provisioning_state'").get();
    return row?.value || PROVISIONING_STATE.UNREGISTERED;
  } catch {
    return PROVISIONING_STATE.UNREGISTERED;
  }
}

function setProvisioningState(db, state, registrationId = null) {
  db.prepare(
    `INSERT INTO kiosk_meta (key, value) VALUES ('provisioning_state', ?)
     ON CONFLICT(key) DO UPDATE SET value=excluded.value`,
  ).run(state);
  if (registrationId !== null) {
    db.prepare(
      `INSERT INTO kiosk_meta (key, value) VALUES ('registration_id', ?)
       ON CONFLICT(key) DO UPDATE SET value=excluded.value`,
    ).run(String(registrationId));
  }
}

// ── Backend provision istegi ─────────────────────────────────────────────────

/**
 * Bootstrap endpoint'ine istek gonderir.
 * Dondurulen nesne: { status, httpStatus, data }
 *   status:     'PROVISIONED' | 'PENDING_APPROVAL' | 'REJECTED' | 'ERROR'
 *   httpStatus: HTTP durum kodu (200, 202, 403, ...)
 *   data:       backend'den gelen JSON
 *
 * GÜVENLİK: kioskProvisioningSecret ve kioskFleetKey loglarda goruntulenmez.
 */
async function fetchBootstrapResult(settings, mac, log) {
  if (!settings.kioskProvisioningSecret || !settings.kioskFleetKey) {
    log?.warn?.('Bootstrap atlandiː KIOSK_FLEET_KEY veya KIOSK_PROVISIONING_SECRET tanimlanmamis');
    return { status: 'ERROR', httpStatus: 0, data: null };
  }

  const timestamp = new Date().toISOString();
  const hmac = signProvisionRequest(mac, timestamp, settings.kioskProvisioningSecret);
  const base = settings.centralApiBase.replace(/\/+$/, '');
  const url = `${base}${settings.kioskBootstrapPath}`;
  const agent = new Agent({ connect: { rejectUnauthorized: !!settings.verifyTls } });

  // Cihaz metadata — kimlik bilgisi/secret icermez
  const deviceMetadata = collectDeviceMetadata();
  const hostname = deviceMetadata.hostname || '';

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Kiosk-Key': settings.kioskFleetKey,
      },
      body: JSON.stringify({ mac_adresi: mac, timestamp, hmac, hostname, device_metadata: deviceMetadata }),
      dispatcher: agent,
      signal: AbortSignal.timeout(10000),
    });

    let data = null;
    try { data = await res.json(); } catch { /* JSON parse basarisiz */ }

    if (res.ok && res.status === 200 && data?.iot_token) {
      return { status: 'PROVISIONED', httpStatus: 200, data };
    }
    if (res.status === 202 && data?.status === 'PENDING') {
      return { status: 'PENDING_APPROVAL', httpStatus: 202, data };
    }
    if (res.status === 403 && data?.status === 'REJECTED') {
      return { status: 'REJECTED', httpStatus: 403, data };
    }
    if (res.ok && res.status === 200 && data?.iot_token) {
      return { status: 'PROVISIONED', httpStatus: 200, data };
    }
    log?.warn?.({ httpStatus: res.status }, 'Bootstrap yaniti tanimsiz');
    return { status: 'ERROR', httpStatus: res.status, data };
  } catch (err) {
    log?.warn?.({ err: err?.message }, 'Bootstrap istegi basarisiz');
    return { status: 'ERROR', httpStatus: 0, data: null };
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

  // 2) Mevcut IoT token kontrolu (PROVISIONED durumu)
  const cachedToken = getMeta(db, 'iot_token');
  if (isIotTokenAlive(cachedToken)) {
    const payload = parseIotTokenPayload(cachedToken);
    runtime.iotToken    = cachedToken;
    runtime.kioskId     = runtime.kioskId     || payload?.kiosk_id    || 0;
    runtime.pharmacyId  = runtime.pharmacyId  || payload?.pharmacy_id || 0;
    // Onaylanmis durumu guncelle
    setProvisioningState(db, PROVISIONING_STATE.APPROVED);
    log?.info?.({ kioskId: runtime.kioskId }, 'IoT token gecerli, provision atlanıyor');
    return Object.freeze(runtime);
  }

  // 3) REJECTED durumu — token alinmaz, normal API'lere erisim engellenir
  const currentState = getProvisioningState(db);
  if (currentState === PROVISIONING_STATE.REJECTED) {
    log?.warn?.('Provisioning durumu REJECTED. Admin onayi gerekmektedir.');
    // Legacy AppKey fallback (dev/test ortami icin)
    runtime.kioskAppKey = runtime.kioskAppKey || getMeta(db, 'kiosk_app_key');
    runtime.kioskId     = runtime.kioskId     || parseIntSafe(getMeta(db, 'kiosk_id'));
    runtime.pharmacyId  = runtime.pharmacyId  || parseIntSafe(getMeta(db, 'pharmacy_id'));
    return Object.freeze(runtime);
  }

  // 4) Token yok — bootstrap dene (UNREGISTERED veya PENDING_APPROVAL)
  if (runtime.kioskMac && runtime.kioskProvisioningSecret && runtime.kioskFleetKey) {
    const result = await fetchBootstrapResult(runtime, runtime.kioskMac, log);

    if (result.status === 'PROVISIONED' && result.data?.iot_token) {
      runtime.iotToken   = result.data.iot_token;
      runtime.kioskId    = result.data.kiosk_id    || 0;
      runtime.pharmacyId = result.data.pharmacy_id || 0;
      setMeta(db, 'iot_token',   runtime.iotToken);
      setMeta(db, 'kiosk_id',    runtime.kioskId);
      setMeta(db, 'pharmacy_id', runtime.pharmacyId);
      setProvisioningState(db, PROVISIONING_STATE.APPROVED);
      log?.info?.({ kioskId: runtime.kioskId, pharmacyId: runtime.pharmacyId }, 'Kiosk provision tamamlandi');

    } else if (result.status === 'PENDING_APPROVAL') {
      const registrationId = result.data?.registration_id || '';
      const retryAfter     = result.data?.retry_after_seconds || 30;
      setProvisioningState(db, PROVISIONING_STATE.PENDING_APPROVAL, registrationId);
      log?.info?.({ registrationId, retryAfter }, 'Kiosk provision onay bekliyor (PENDING_APPROVAL)');

    } else if (result.status === 'REJECTED') {
      setProvisioningState(db, PROVISIONING_STATE.REJECTED);
      log?.warn?.('Kiosk provision reddedildi (REJECTED). Sistem yoneticiyle iletisime gecin.');

    } else if (result.status === 'ERROR') {
      // Agdaki hata: mevcut state'i koru, bir sonraki dogu denemesinde tekrar denenir
      log?.warn?.({ httpStatus: result.httpStatus }, 'Bootstrap yaniti alinamadi, sonraki dongude tekrar denecek');
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
 *
 * PENDING_APPROVAL durumundaysa da dener: admin onaylamissa 200 ile token alir.
 */
export async function refreshIotTokenIfNeeded(db, settings, log = console) {
  const token = getMeta(db, 'iot_token');
  if (isIotTokenAlive(token, 24)) return; // henuz erken

  // REJECTED durumunda token yenileme denemesi yapilmaz
  const currentState = getProvisioningState(db);
  if (currentState === PROVISIONING_STATE.REJECTED) return;

  const mac = getMeta(db, 'kiosk_mac') || settings.kioskMac;
  if (!mac || !settings.kioskProvisioningSecret || !settings.kioskFleetKey) return;

  log?.info?.('IoT token yenileniyor');
  const result = await fetchBootstrapResult(settings, mac, log);
  if (result.status === 'PROVISIONED' && result.data?.iot_token) {
    setMeta(db, 'iot_token', result.data.iot_token);
    if (result.data.kiosk_id) setMeta(db, 'kiosk_id', result.data.kiosk_id);
    if (result.data.pharmacy_id) setMeta(db, 'pharmacy_id', result.data.pharmacy_id);
    setProvisioningState(db, PROVISIONING_STATE.APPROVED);
    log?.info?.('IoT token yenilendi');
  } else if (result.status === 'PENDING_APPROVAL') {
    const registrationId = result.data?.registration_id || getMeta(db, 'registration_id') || '';
    setProvisioningState(db, PROVISIONING_STATE.PENDING_APPROVAL, registrationId);
    log?.info?.({ registrationId }, 'Token yenileme: hala onay bekliyor (PENDING_APPROVAL)');
  } else if (result.status === 'REJECTED') {
    setProvisioningState(db, PROVISIONING_STATE.REJECTED);
    log?.warn?.('Token yenileme: provision reddedildi (REJECTED)');
  }
}

/**
 * IoT token'i temizle — 403 hatasi alindiginda cagrilir.
 * Token gecersiz kalmis olabilir (kiosk silinmis, token revoke edilmis, vb.).
 * Token temizlenince bir sonraki sync dongusunde provision yeniden yapilir.
 */
export function clearIotToken(db, log = console) {
  try {
    db.prepare('DELETE FROM kiosk_meta WHERE key IN (?, ?, ?)').run('iot_token', 'kiosk_id', 'pharmacy_id');
    log?.warn?.('IoT token temizlendi, bir sonraki sync\'te provision yeniden yapilacak');
  } catch (err) {
    log?.error?.({ err: err?.message }, 'IoT token temizleme basarisiz');
  }
}

/**
 * Backend'den 403 hatasi alindiysa token'i temizle.
 * HTTP 403 = Unauthorized, token backend tarafinda gecersiz.
 */
export function handle403Error(db, settings, log = console) {
  const token = getMeta(db, 'iot_token');
  if (token) {
    log?.warn?.('Backend HTTP 403 dondu, IoT token gecersiz olabilir — token temizleniyor');
    clearIotToken(db, log);
  } else if (settings.kioskAppKey) {
    log?.warn?.('Backend HTTP 403 dondu: KIOSK_APP_KEY veya KIOSK_MAC eslesmesini kontrol edin');
  } else {
    log?.warn?.('Backend HTTP 403 dondu: kiosk kimligi provision edilmemis veya gecersiz');
  }
}
