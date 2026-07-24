/**
 * Cihaz Yönetimi Servisi — Eczane & Kiosk (ARC-003).
 *
 * Backend ile gerçek HTTP iletişimi. Form bileşeni `province` / `owner` /
 * `kioskCount` / `lastPing` isimlerini kullandığı için bu katman backend
 * Türkçe alanları (`ad` / `sahip_adi` / `kiosk_sayisi` / `son_goruldu`) ile
 * eşleştirme yapar.
 *
 * Backend endpoint'leri:
 *   GET    /api/pharmacies/                         — liste
 *   POST   /api/pharmacies/                         — oluştur
 *   PATCH  /api/pharmacies/{id}/                    — güncelle
 *   DELETE /api/pharmacies/{id}/                    — sil
 *   GET    /api/pharmacies/kiosks/                  — kiosk durum listesi
 *   POST   /api/pharmacies/kiosks/                  — kiosk oluştur
 *   DELETE /api/pharmacies/kiosks/{id}/             — kiosk sil
 */
import { http } from './api';

// ─── Eşleştiriciler ─────────────────────────────────────────────────────────

export function mapPharmacyFromApi(p) {
  if (!p) return null;
  return {
    id: p.id,
    name: p.ad,
    il: p.il,                              // FK id
    ilAdi: p.il_adi ?? '',
    ilce: p.ilce,                          // FK id
    ilceAdi: p.ilce_adi ?? '',
    adres: p.adres ?? '',
    owner: p.sahip_adi ?? '',
    telefon: p.telefon ?? '',
    eczaneKodu: p.eczane_kodu ?? '',
    kioskCount: p.kiosk_sayisi ?? 0,
    isActive: p.aktif !== false,
  };
}

function mapPharmacyToApi(data) {
  const out = {};
  if (data.name      !== undefined) out.ad          = data.name;
  if (data.owner     !== undefined) out.sahip_adi   = data.owner;
  if (data.adres     !== undefined) out.adres        = data.adres;
  if (data.telefon   !== undefined) out.telefon      = data.telefon;
  if (data.eczaneKodu !== undefined) out.eczane_kodu = data.eczaneKodu || null;
  if (data.isActive  !== undefined) out.aktif        = data.isActive;
  if (data.il        !== undefined) out.il           = data.il;   // integer FK
  if (data.ilce      !== undefined) out.ilce         = data.ilce; // integer FK
  return out;
}

export function mapKioskFromApi(k) {
  if (!k) return null;
  return {
    id: k.id,
    pharmacyId: k.eczane,
    pharmacyName: k.eczane_adi ?? '',
    mac: k.mac_adresi,
    ad:k.ad,
    appKey: k.uygulama_anahtari,
    isActive: k.aktif !== false,
    lastPing: k.son_goruldu,
    lastIp: k.last_ip ?? null,
    health: k.durum ?? null,
  };
}

// ─── Eczane Servisleri ──────────────────────────────────────────────────────

export async function getPharmacies() {
  const { data } = await http.get('/api/pharmacies/');
  const items = Array.isArray(data) ? data : (data?.results ?? []);
  return items.map(mapPharmacyFromApi);
}

export async function createPharmacy(data) {
  const { data: created } = await http.post('/api/pharmacies/', mapPharmacyToApi(data));
  return mapPharmacyFromApi(created);
}

export async function updatePharmacy(id, data) {
  const { data: updated } = await http.patch(
    `/api/pharmacies/${id}/`,
    mapPharmacyToApi(data),
  );
  return mapPharmacyFromApi(updated);
}

export async function deletePharmacy(id) {
  await http.delete(`/api/pharmacies/${id}/`);
}

// ─── Kiosk Servisleri ───────────────────────────────────────────────────────

export async function getKioskStatus(pharmacyId = null) {
  const params = pharmacyId ? { eczane: pharmacyId } : {};
  const { data } = await http.get('/api/pharmacies/kiosks/', { params });
  const items = Array.isArray(data) ? data : (data?.results ?? []);
  return items.map(mapKioskFromApi);
}

/**
 * Eczaneye yeni kiosk ekler.
 * @param {{ pharmacyId: number, mac: string, ad: string }} data
 */
export async function createKiosk(data) {
  const { data: created } = await http.post('/api/pharmacies/kiosks/', {
    eczane: data.pharmacyId,
    mac_adresi: data.mac,
    ad: data.ad,
    aktif: true,
  });
  return mapKioskFromApi(created);
}

/**
 * Kiosk bilgilerini günceller.
 * @param {number} id - Kiosk ID
 * @param {{ mac?: string, ad?: string, isActive?: boolean }} data
 */
export async function updateKiosk(id, data) {
  const payload = {};
  if (data.mac !== undefined) payload.mac_adresi = data.mac;
  if (data.ad !== undefined) payload.ad = data.ad;
  if (data.isActive !== undefined) payload.aktif = data.isActive;
  const { data: updated } = await http.patch(`/api/pharmacies/kiosks/${id}/`, payload);
  return mapKioskFromApi(updated);
}

export async function deleteKiosk(id) {
  await http.delete(`/api/pharmacies/kiosks/${id}/`);
}

/**
 * Kiosk device_id'sini sifirlar (admin). Kiosk bir sonraki enrollment'ta yeniden baglanir.
 */
export async function resetKioskDeviceId(id) {
  const { data } = await http.post(`/api/pharmacies/kiosks/${id}/reset-device-id/`);
  return data;
}

// ── Provisioning (Onay Bekleyen Cihazlar) ───────────────────────────────────

export function mapProvisioningRequestFromApi(r) {
  if (!r) return null;
  return {
    id: r.id,
    mac: r.mac_adresi,
    hostname: r.hostname ?? '',
    deviceMetadata: r.device_metadata ?? {},
    status: r.status,
    firstSeenAt: r.first_seen_at,
    lastSeenAt: r.last_seen_at,
    requestCount: r.request_count ?? 1,
    approvedAt: r.approved_at,
    approvedBy: r.approved_by_username ?? null,
    rejectedAt: r.rejected_at,
    rejectedBy: r.rejected_by_username ?? null,
    rejectionReason: r.rejection_reason ?? '',
    kioskId: r.kiosk_id ?? null,
    kioskAd: r.kiosk_ad ?? null,
  };
}

/**
 * Onay bekleyen (veya reddedilen) cihaz listesini getirir.
 * Yalnızca SuperAdmin erişebilir.
 * @param {{ status?: string, mac?: string, hostname?: string }} filters
 */
export async function listProvisioningRequests(filters = {}) {
  const params = {};
  if (filters.status) params.status = filters.status;
  if (filters.mac) params.mac = filters.mac;
  if (filters.hostname) params.hostname = filters.hostname;
  const { data } = await http.get('/api/pharmacies/kiosks/provisioning/', { params });
  const items = Array.isArray(data) ? data : (data?.results ?? []);
  return items.map(mapProvisioningRequestFromApi);
}

/**
 * Cihazı eczaneye bağlayarak onaylar.
 * @param {string} id - KioskProvisioningRequest UUID
 * @param {{ eczane_id: number, ad: string }} data
 */
export async function approveProvisioningRequest(id, data) {
  const { data: result } = await http.post(
    `/api/pharmacies/kiosks/provisioning/${id}/approve/`,
    { eczane_id: data.eczane_id, ad: data.ad },
  );
  return mapProvisioningRequestFromApi(result);
}

/**
 * Cihazı reddeder.
 * @param {string} id - KioskProvisioningRequest UUID
 * @param {{ rejection_reason?: string }} data
 */
export async function rejectProvisioningRequest(id, data = {}) {
  const { data: result } = await http.post(
    `/api/pharmacies/kiosks/provisioning/${id}/reject/`,
    { rejection_reason: data.rejection_reason ?? '' },
  );
  return mapProvisioningRequestFromApi(result);
}

