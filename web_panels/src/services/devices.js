/**
 * Cihaz Yönetimi Servisi — Eczane & Kiosk (ARC-003).
 *
 * Backend ile gerçek HTTP iletişimi. Form bileşeni `province` / `owner` /
 * `kioskCount` / `lastPing` isimlerini kullandığı için bu katman backend
 * alanları (`city` / `owner_name` / `kiosk_count` / `last_seen_at`) ile
 * eşleştirme yapar.
 *
 * Backend endpoint'leri:
 *   GET    /api/pharmacies/                         — liste (kiosk_count ile)
 *   POST   /api/pharmacies/                         — oluştur
 *   PATCH  /api/pharmacies/{id}/                    — güncelle
 *   DELETE /api/pharmacies/{id}/                    — sil
 *   GET    /api/pharmacies/kiosks/                  — kiosk durum listesi
 */
import { http } from './api';

// ─── Eşleştiriciler ─────────────────────────────────────────────────────────

function mapPharmacyFromApi(p) {
  if (!p) return null;
  return {
    id: p.id,
    name: p.name,
    province: p.city,
    district: p.district,
    owner: p.owner_name || '',
    kioskCount: p.kiosk_count ?? 0,
    isActive: p.is_active !== false,
  };
}

function mapPharmacyToApi(data) {
  const out = {};
  if (data.name !== undefined) out.name = data.name;
  if (data.province !== undefined) out.city = data.province;
  if (data.district !== undefined) out.district = data.district;
  if (data.owner !== undefined) out.owner_name = data.owner;
  if (data.isActive !== undefined) out.is_active = data.isActive;
  return out;
}

function mapKioskFromApi(k) {
  if (!k) return null;
  return {
    id: k.id,
    pharmacyId: k.pharmacy,
    pharmacyName: k.pharmacy_name || '',
    mac: k.mac_address,
    isActive: k.is_active !== false,
    lastPing: k.last_seen_at,
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

export async function getKioskStatus() {
  const { data } = await http.get('/api/pharmacies/kiosks/');
  const items = Array.isArray(data) ? data : (data?.results ?? []);
  return items.map(mapKioskFromApi);
}
