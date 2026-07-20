/**
 * Kiosk otomatik kimlik yonetimi (provisioning + App Key).
 *
 * Durum makinesi:
 *   UNREGISTERED      — Henuz bootstrap yapilmamis
 *       ↓ bootstrap request (fleet key + HMAC)
 *   PENDING_APPROVAL  — Backend 202 dondu, admin onayi bekleniyor
 *       ↓ polling (retry_after_seconds veya backoff)
 *   APPROVED          — Admin onayladi, kiosk_id ve app_key mevcut
 *       ↓ normal App Key akisi
 *   REJECTED          — Admin reddetti, manuel mudahale gerekir
 *
 * Akis:
 *   1. MAC adresi sistemden okunur (veya DB cache'ten).
 *   2. Gecerli bir App Key varsa kullanilir.
 *   3. App Key yoksa:
 *      a. PENDING_APPROVAL durumundaysa → bootstrap yeniden dene (backoff)
 *      b. Aksi halde → HMAC-SHA256(MAC_UPPER + iso_timestamp, provisioningSecret) imzalanir.
 *      c. POST /api/kiosk/v1/bootstrap/ cagrilir.
 *      d. 200  → app_key, kiosk_id, pharmacy_id kiosk_meta'ya yazilir (APPROVED)
 *      e. 202  → PENDING_APPROVAL, registration_id kiosk_meta'ya yazilir
 *      f. 403  → REJECTED durumu; app_key alinmaz
 *   4. getAuthHeaders(db, settings): her backend istegi icin header nesnesi doner.
 *
 * Guvenlik:
 *   - KIOSK_PROVISIONING_SECRET ve KIOSK_FLEET_KEY loglarda goruntulenmez.
 *   - REJECTED durumunda App Key verilmez, normal API'lere erisim engellenir.
 */
import crypto from 'node:crypto';
import os from 'node:os';
import { Agent, fetch } from 'undici';

// ── Yardimcilar ──────────────────────────────────────────────────────────────

function getMeta(db, key) {
  try {
    const row = db.prepare('SELECT value FROM kiosk_meta WHERE key = ?').get(key);
    return row?.value ?? '';
  } catch {
    // kiosk_meta yoksa/erisilemezse guvenli varsayilan (500 yerine bos).
    return '';
  }
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

// ── App Key durum yardimcisi ──────────────────

function isProvisioned(db) {
  return getProvisioningState(db) === PROVISIONING_STATE.APPROVED && Boolean(getMeta(db, 'kiosk_app_key'));
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
 *   status:     'APPROVED' | 'PENDING_APPROVAL' | 'REJECTED' | 'ERROR'
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

    if (res.ok && res.status === 200 && data?.app_key) {
      return { status: 'APPROVED', httpStatus: 200, data };
    }
    if (res.status === 202 && data?.status === 'PENDING') {
      return { status: 'PENDING_APPROVAL', httpStatus: 202, data };
    }
    if (res.status === 403) {
      return { status: 'REJECTED', httpStatus: 403, data };
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

  // Legacy kimlik kaydini (varsa) bir defalik temizle.
  cleanupLegacyIotToken(db, log);

  // 1) MAC — once SQLite cache, sonra sistem tespiti; restart'ta sabit kalir.
  runtime.kioskMac = normalizeMac(getMeta(db, 'kiosk_mac') || detectSystemMacAddress());
  if (runtime.kioskMac) setMeta(db, 'kiosk_mac', runtime.kioskMac);

  const applyStoredIdentity = () => {
    runtime.kioskAppKey = getMeta(db, 'kiosk_app_key');
    runtime.kioskId     = parseIntSafe(getMeta(db, 'kiosk_id'));
    runtime.pharmacyId  = parseIntSafe(getMeta(db, 'pharmacy_id'));
  };

  const currentState = getProvisioningState(db);

  // 2) Zaten onayli + App Key mevcut → bootstrap gerekmez.
  if (isProvisioned(db)) {
    applyStoredIdentity();
    log?.info?.({ kioskId: runtime.kioskId, has_app_key: true }, 'App Key mevcut, provision atlaniyor');
    return Object.freeze(runtime);
  }

  // 3) REJECTED → bootstrap denenmez.
  if (currentState === PROVISIONING_STATE.REJECTED) {
    log?.warn?.('Provisioning durumu REJECTED. Admin onayi gerekmektedir.');
    applyStoredIdentity();
    return Object.freeze(runtime);
  }

  // 4) App Key yok → bootstrap dene (UNREGISTERED veya PENDING_APPROVAL).
  if (runtime.kioskMac && runtime.kioskProvisioningSecret && runtime.kioskFleetKey) {
    const result = await fetchBootstrapResult(runtime, runtime.kioskMac, log);

    if (result.status === 'APPROVED' && result.data?.app_key) {
      setMeta(db, 'kiosk_app_key', result.data.app_key);
      setMeta(db, 'kiosk_id',      result.data.kiosk_id ?? 0);
      setMeta(db, 'pharmacy_id',   result.data.pharmacy_id ?? 0);
      setProvisioningState(db, PROVISIONING_STATE.APPROVED);
      log?.info?.({ kioskId: result.data.kiosk_id, pharmacyId: result.data.pharmacy_id, has_app_key: true },
        'Kiosk provision tamamlandi (App Key alindi)');

    } else if (result.status === 'PENDING_APPROVAL') {
      const registrationId = result.data?.registration_id || '';
      const retryAfter     = result.data?.retry_after_seconds || 30;
      setProvisioningState(db, PROVISIONING_STATE.PENDING_APPROVAL, registrationId);
      log?.info?.({ registrationId, retryAfter }, 'Kiosk provision onay bekliyor (PENDING_APPROVAL)');

    } else if (result.status === 'REJECTED') {
      setProvisioningState(db, PROVISIONING_STATE.REJECTED);
      log?.warn?.('Kiosk provision reddedildi (REJECTED). Sistem yoneticiyle iletisime gecin.');

    } else {
      // Agdaki hata: mevcut state korunur, bir sonraki dongude tekrar denenir.
      log?.warn?.({ httpStatus: result.httpStatus }, 'Bootstrap yaniti alinamadi, sonraki dongude tekrar denecek');
    }
  } else {
    log?.warn?.('Provision atlaniyor: kioskMac, kioskFleetKey veya kioskProvisioningSecret eksik');
  }

  applyStoredIdentity();
  return Object.freeze(runtime);
}

// ── Public: her backend istegi icin auth header nesnesi ─────────────────────

/**
 * Operasyonel Main API istekleri icin TEK auth contract'i.
 * Credential'lar HER istekte SQLite'tan okunur (provision sonrasi restart gerekmez).
 * Fleet Key / IoT / Bearer EKLENMEZ.
 */
export function getAuthHeaders(db) {
  const headers = {};
  const appKey = getMeta(db, 'kiosk_app_key');
  const mac = getMeta(db, 'kiosk_mac');
  if (appKey && mac) {
    headers['Authorization'] = `AppKey ${appKey}`;
    headers['X-Kiosk-MAC']   = mac;
  }
  return headers;
}

/** App Key + MAC credential'lari SQLite'ta mevcut mu? */
export function hasAppKeyCredentials(db) {
  return Boolean(getMeta(db, 'kiosk_app_key') && getMeta(db, 'kiosk_mac'));
}

/**
 * Legacy kimlik kaydini SQLite'tan bir defalik temizler (kullanimdan kaldirildi).
 * Migration gerektirmez; kayit yoksa sorun degil.
 */
export function cleanupLegacyIotToken(db, log = console) {
  try {
    const info = db.prepare("DELETE FROM kiosk_meta WHERE key = 'iot_token'").run();
    if (info?.changes) log?.info?.('Legacy kimlik kaydi kiosk_meta\'dan temizlendi');
  } catch { /* yoksa sorun degil */ }
}

/**
 * Backend 401 → App Key eksik/gecersiz.
 * Bearer/Fleet/IoT fallback YAPILMAZ. App Key hemen silinmez; kontrollu backoff
 * icin isaretlenir (scheduler dogal araliginda tekrar dener).
 */
export function handle401Error(db, settings, log = console) {
  try { setMeta(db, 'app_key_last_401_at', new Date().toISOString()); } catch {}
  log?.warn?.({ event: 'central_auth_401', has_app_key: Boolean(getMeta(db, 'kiosk_app_key')) },
    'Backend 401: App Key gecersiz/eksik olabilir (fallback yok, backoff)');
}

/**
 * Backend 403 → kiosk pasif/onaysiz/eczanesiz veya bloke.
 * App Key SILINMEZ; provisioning dongusu baslatilmaz; backoff uygulanir.
 */
export function handle403Error(db, settings, log = console) {
  try { setMeta(db, 'app_key_last_403_at', new Date().toISOString()); } catch {}
  log?.warn?.({ event: 'central_auth_403', has_app_key: Boolean(getMeta(db, 'kiosk_app_key')) },
    'Backend 403: kiosk pasif/onaysiz/eczanesiz olabilir (App Key korunuyor, backoff)');
}
