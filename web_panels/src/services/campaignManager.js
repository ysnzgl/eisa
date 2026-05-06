/**
 * Reklam Yönetimi Servisi — DOOH Idle-Screen Reklam Sistemi
 *
 * Gerçek API endpoint'leri:
 *   GET    /api/campaigns/          — liste
 *   POST   /api/campaigns/          — oluştur
 *   PATCH  /api/campaigns/{id}/     — güncelle
 *   DELETE /api/campaigns/{id}/     — sil
 *   GET    /api/pharmacies/         — hedefleme için eczane listesi
 */
import { http } from './api';

// ─── Field mappers ─────────────────────────────────────────────────────────

function mapAdFromApi(r) {
  if (!r) return null;
  return {
    id: r.id,
    name: r.ad,
    client: r.musteri ?? '',
    media_url: r.medya_url,
    duration_sec: r.sure_saniye ?? 15,
    starts_at: r.baslangic_tarihi,
    ends_at: r.bitis_tarihi,
    broadcast_start: r.yayin_baslangic ?? '08:00',
    broadcast_end: r.yayin_bitis ?? '22:00',
    target_pharmacy_ids: r.hedef_eczaneler ?? [],
    is_active: r.aktif !== false,
    created_at: r.olusturulma_tarihi,
  };
}

function mapAdToApi(data) {
  const out = {};
  if (data.name          !== undefined) out.ad               = data.name;
  if (data.client        !== undefined) out.musteri          = data.client;
  if (data.media_url     !== undefined) out.medya_url        = data.media_url;
  if (data.duration_sec  !== undefined) out.sure_saniye      = data.duration_sec;
  if (data.starts_at     !== undefined) out.baslangic_tarihi = data.starts_at;
  if (data.ends_at       !== undefined) out.bitis_tarihi     = data.ends_at;
  if (data.broadcast_start !== undefined) out.yayin_baslangic = data.broadcast_start;
  if (data.broadcast_end   !== undefined) out.yayin_bitis    = data.broadcast_end;
  if (data.target_pharmacy_ids !== undefined) out.hedef_eczaneler = data.target_pharmacy_ids;
  if (data.is_active     !== undefined) out.aktif            = data.is_active;
  return out;
}

// ─── Servis Fonksiyonları ─────────────────────────────────────────────────────

/** Tüm reklamları getirir. */
export async function getCampaigns() {
  const { data } = await http.get('/api/campaigns/');
  const items = Array.isArray(data) ? data : (data?.results ?? []);
  return items.map(mapAdFromApi);
}

/** Yeni reklam oluşturur. */
export async function createCampaign(data) {
  const { data: created } = await http.post('/api/campaigns/', mapAdToApi(data));
  return mapAdFromApi(created);
}

/** Reklamı günceller. */
export async function updateCampaign(id, data) {
  const { data: updated } = await http.patch(`/api/campaigns/${id}/`, mapAdToApi(data));
  return mapAdFromApi(updated);
}

/** Reklamı siler. */
export async function deleteCampaign(id) {
  await http.delete(`/api/campaigns/${id}/`);
}

// ─── Hedefleme ─────────────────────────────────────────────────────────────

/** Tüm eczaneleri getirir (hedefleme için). */
export async function getPharmaciesForTargeting() {
  const { data } = await http.get('/api/pharmacies/');
  const items = Array.isArray(data) ? data : (data?.results ?? []);
  return items.map((p) => ({
    id: p.id,
    name: p.ad,
    province: p.il_adi ?? '',
    district: p.ilce_adi ?? '',
  }));
}

// ─── Yardımcı ─────────────────────────────────────────────────────────────────

/**
 * Reklamın durumunu hesaplar.
 * @param {{ starts_at: string, ends_at: string }} c
 * @returns {'active'|'upcoming'|'ended'}
 */
export function campaignStatus(c) {
  const now = Date.now();
  const start = new Date(c.starts_at).getTime();
  const end   = new Date(c.ends_at).getTime();
  if (now < start) return 'upcoming';
  if (now > end)   return 'ended';
  return 'active';
}

/**
 * Medya dosyasını sunucuya yükler.
 * @param {File} file
 * @returns {Promise<string>} Yüklenen dosyanın tam URL'i
 */
export async function uploadMedia(file) {
  const fd = new FormData();
  fd.append('file', file);
  const { data } = await http.post('/api/campaigns/upload-media/', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data.url;
}
