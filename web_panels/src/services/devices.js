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
 */
import { http } from './api';

// ─── Eşleştiriciler ─────────────────────────────────────────────────────────

function mapPharmacyFromApi(p) {
  if (!p) return null;
  return {
    id: p.id,
    name: p.ad,
    province: p.il_adi ?? String(p.il ?? ''),
    district: p.ilce_adi ?? String(p.ilce ?? ''),
    owner: p.sahip_adi ?? '',
    kioskCount: p.kiosk_sayisi ?? 0,
    isActive: p.aktif !== false,
  };
}

function mapPharmacyToApi(data) {
  const out = {};
  if (data.name !== undefined) out.ad = data.name;
  if (data.owner !== undefined) out.sahip_adi = data.owner;
  if (data.isActive !== undefined) out.aktif = data.isActive;
  // il/ilce backend'de integer FK (id) gönderilmeli
  if (data.il !== undefined) out.il = data.il;
  if (data.ilce !== undefined) out.ilce = data.ilce;
  return out;
}

function mapKioskFromApi(k) {
  if (!k) return null;
  return {
    id: k.id,
    pharmacyId: k.eczane,
    pharmacyName: k.eczane_adi ?? '',
    mac: k.mac_adresi,
    appKey: k.uygulama_anahtari,
    isActive: k.aktif !== false,
    lastPing: k.son_goruldu,
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

export async function getKioskStatus() {
  const { data } = await http.get('/api/pharmacies/kiosks/');
  const items = Array.isArray(data) ? data : (data?.results ?? []);
  return items.map(mapKioskFromApi);
}
