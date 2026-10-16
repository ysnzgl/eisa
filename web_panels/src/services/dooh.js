/**
 * Kiosk Sponsorluk (DOOH) servis katmanı.
 *
 * Yeni sözleşme: cihaz (kiosk) bazlı sponsorluk yönetimi.
 *   - Sponsorluk tanımları (campaigns) + creative medyaları
 *   - Kiosk bazlı atama / önizleme / kopyalama / simülasyon
 *   - Generation job izleme + kiosk sağlık durumu (Kontrol Merkezi)
 *
 * Base: /api/campaigns/v2/
 */
import { http } from './api';

// ── Sponsorluk tanımları (Campaign) ──────────────────────────────────────────
export const listCampaignsV2 = (params = {}) =>
  http.get('/api/campaigns/v2/campaigns/', { params });

export const getCampaignV2 = (id) =>
  http.get(`/api/campaigns/v2/campaigns/${id}/`);

export const createCampaignV2 = (data) =>
  http.post('/api/campaigns/v2/campaigns/', data);

export const updateCampaignV2 = (id, data) =>
  http.patch(`/api/campaigns/v2/campaigns/${id}/`, data);

export const deleteCampaignV2 = (id) =>
  http.delete(`/api/campaigns/v2/campaigns/${id}/`);

export const bulkActionCampaignsV2 = (action, ids) =>
  http.post('/api/campaigns/v2/campaigns/bulk-action/', { action, ids });

/** Bir sponsorluğa atanmış kioskların salt-okunur listesi. */
export const getCampaignKiosks = (campaignId) =>
  http.get(`/api/campaigns/v2/campaigns/${campaignId}/kiosks/`);

/**
 * Sponsorluğu birden çok kioska ata (çoklu seçim + pencere/sayım).
 * @param {string} campaignId
 * @param {object} body {kiosk_ids:[int], window_start, window_end, count,
 *                        active_weekdays|null, start_date|null, end_date|null, dry_run:bool}
 */
export const assignKiosksToCampaign = (campaignId, body) =>
  http.post(`/api/campaigns/v2/campaigns/${campaignId}/assign-kiosks/`, body);

// ── Creatives (medya) ────────────────────────────────────────────────────────
export const listCreatives = (params = {}) =>
  http.get('/api/campaigns/v2/creatives/', { params });

export const createCreative = (data) =>
  http.post('/api/campaigns/v2/creatives/', data);

export const updateCreative = (id, data) =>
  http.patch(`/api/campaigns/v2/creatives/${id}/`, data);

export const deleteCreative = (id) =>
  http.delete(`/api/campaigns/v2/creatives/${id}/`);

/** Orijinal Creative medyasını indirmek için blob URL üretir (SuperAdmin). */
export const downloadCreativeMedia = (creativeId) =>
  http.get(`/api/campaigns/v2/creatives/${creativeId}/download/`, { responseType: 'blob' });

// ── Medya upload ─────────────────────────────────────────────────────────────
export async function uploadMedia(file, mediaKind) {
  const fd = new FormData();
  fd.append('file', file);
  if (mediaKind) fd.append('media_kind', mediaKind);
  const { data } = await http.post('/api/campaigns/upload-media/', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

// ── Kiosk bazlı sponsorluk yönetimi ──────────────────────────────────────────

/**
 * Sponsorluk yönetimi için kiosk listesi.
 * @param {object} params {search?, unassigned?:1}
 */
export const listSponsorshipKiosks = (params = {}) =>
  http.get('/api/campaigns/v2/sponsorship-kiosks/', { params });

/** Bir kioskun kayıtlı sponsorlukları (+ kiosk özeti). */
export const getKioskSponsorships = (kioskId) =>
  http.get(`/api/campaigns/v2/sponsorship-kiosks/${kioskId}/sponsorships/`);

/**
 * Kioskun sponsorluk setini tamamen değiştirir (atomik, kapasite doğrulanır).
 * @param {number} kioskId
 * @param {Array} items [{campaign_id, window_start, window_end, count,
 *                        active_weekdays, start_date, end_date, is_active}]
 */
export const putKioskSponsorships = (kioskId, items) =>
  http.put(`/api/campaigns/v2/sponsorship-kiosks/${kioskId}/sponsorships/`, { items });

/**
 * Taslak ya da kayıtlı sete göre günlük yayın önizlemesi (yerleşim motoru).
 * @param {number} kioskId
 * @param {object} body {date, items?} — items verilmezse kayıtlı set kullanılır.
 */
export const previewKioskSponsorships = (kioskId, body) =>
  http.post(`/api/campaigns/v2/sponsorship-kiosks/${kioskId}/preview/`, body);

/**
 * Kaynak kioskun takvimini hedef kiosklara KOPYALA (üzerine yazar).
 * @param {number} kioskId kaynak
 * @param {object} body {target_kiosk_ids:[int], dry_run:bool}
 */
export const copyKioskSponsorships = (kioskId, body) =>
  http.post(`/api/campaigns/v2/sponsorship-kiosks/${kioskId}/copy/`, body);

/**
 * Cihaz simülasyonu: probe (tek görsel kaç kez sığar) + senaryo hesabı.
 * @param {number} kioskId
 * @param {object} body {date_from, date_to, include_existing, probe|null, scenario:[]}
 */
export const simulateKioskSponsorship = (kioskId, body) =>
  http.post(`/api/campaigns/v2/sponsorship-kiosks/${kioskId}/simulate/`, body);

// ── Yayın Akışı — kiosk günlük playlist özeti (yayında olan, read-only) ───────
export const getKioskDayStream = (kioskId, date) =>
  http.get('/api/campaigns/v2/playlists/day-stream/', { params: { kiosk: kioskId, date } });

// ── Idle Screen Content (İçerik Yönetimi — başlık/metin idle içerikleri) ──────
export const listIdleContents = () =>
  http.get('/api/campaigns/v2/idle-contents/');

export const createIdleContent = (data) =>
  http.post('/api/campaigns/v2/idle-contents/', data);

export const updateIdleContent = (id, data) =>
  http.patch(`/api/campaigns/v2/idle-contents/${id}/`, data);

export const deleteIdleContent = (id) =>
  http.delete(`/api/campaigns/v2/idle-contents/${id}/`);

export const bulkDeleteIdleContents = (ids) =>
  Promise.all(ids.map(id => http.delete(`/api/campaigns/v2/idle-contents/${id}/`)));

export const listKategoriler = () =>
  http.get('/api/products/categories/');

// ── Playlist generation (Kontrol Merkezi — manuel tetikleme) ──────────────────
export const generatePlaylists = (payload = {}) =>
  http.post('/api/campaigns/v2/playlists/generate/', payload);

export const forceRegenerateKiosk = (kioskId, targetDate = null) =>
  http.post('/api/campaigns/v2/playlists/generate/', {
    kiosk: kioskId,
    ...(targetDate ? { date: targetDate } : {}),
  });

// ── Generation Jobs (progress tracking) ──────────────────────────────────────
export const listGenerationJobs = () =>
  http.get('/api/campaigns/v2/playlists/jobs/');

export const getGenerationJob = (id) =>
  http.get(`/api/campaigns/v2/playlists/jobs/${id}/`);

// ── Kiosk DOOH health (desired/applied version) ──────────────────────────────
export const getKioskHealth = () =>
  http.get('/api/pharmacies/kiosks/');

// ── Kiosk listesi (genel amaçlı) ──────────────────────────────────────────────
export const listKiosks = (params = {}) =>
  http.get('/api/pharmacies/kiosks/', { params });
