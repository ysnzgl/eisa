/**
 * DOOH v2 reklam motoru servis katmanı.
 * Yeni Campaign / Creative / ScheduleRule / Playlist / PricingMatrix endpoint'leri.
 */
import { http } from './api';

// ── Campaigns ──
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

export const getCampaignRules = (id) =>
  http.get(`/api/campaigns/v2/campaigns/${id}/rules/`);

export const setCampaignRules = (id, rules) =>
  http.post(`/api/campaigns/v2/campaigns/${id}/rules/`, rules);

export const getCampaignTimeline = (params = {}) =>
  http.get('/api/campaigns/v2/campaigns/timeline/', { params });

export const getCampaignCalendar = (params = {}) =>
  http.get('/api/campaigns/v2/campaigns/calendar/', { params });

// ── Campaign Targets (IL / ILCE / ECZANE hiyerarşik hedefleme) ──
export const getCampaignTargets = (campaignId) =>
  http.get(`/api/campaigns/v2/campaigns/${campaignId}/targets/`);

/** targets = [{target_type: "IL"|"ILCE"|"ECZANE", il?, ilce?, eczane?}] */
export const setCampaignTargets = (campaignId, targets) =>
  http.post(`/api/campaigns/v2/campaigns/${campaignId}/targets/`, targets);

// ── Simulate & Activate (Faz 3) ──

/**
 * Kampanyayı simüle et (read-only, kalıcı mutation yok).
 * DOOH_ENGINE_V2=shadow|active gerektirir.
 * @returns SimulationResultSerializer response
 */
export const simulateCampaign = (id) =>
  http.post(`/api/campaigns/v2/campaigns/${id}/simulate/`);

/**
 * Kampanyayı aktive et (DOOH_ENGINE_V2=active gerektirir).
 * @returns ActivationResultSerializer response
 */
export const activateCampaign = (id) =>
  http.post(`/api/campaigns/v2/campaigns/${id}/activate/`);

// ── Kapasite Önizleme (Before / After) ──
/**
 * Yeni bir kural eklemeden önce kapasite etkisini simüle eder.
 * @param {object} params - { kiosk, date, creative_duration, frequency_type, frequency_value, target_hours }
 */
export const previewCampaignCapacity = (params) =>
  http.post('/api/campaigns/v2/campaigns/preview/', params);

// ── Creatives ──
export const listCreatives = (params = {}) =>
  http.get('/api/campaigns/v2/creatives/', { params });

export const createCreative = (data) =>
  http.post('/api/campaigns/v2/creatives/', data);

// ── Media upload ──
export async function uploadMedia(file) {
  const fd = new FormData();
  fd.append('file', file);
  const { data } = await http.post('/api/campaigns/upload-media/', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

// ── House ads ──
export const listHouseAds = () =>
  http.get('/api/campaigns/v2/house-ads/');

export const createHouseAd = (data) =>
  http.post('/api/campaigns/v2/house-ads/', data);

// ── Inventory ──
export const getInventoryAvailability = (params) =>
  http.get('/api/inventory/availability/', { params });

// ── Pricing matrix ──
export const getPricingMatrix = () =>
  http.get('/api/campaigns/v2/pricing-matrix/');

export const updatePricingMatrix = (data) =>
  http.put('/api/campaigns/v2/pricing-matrix/', data);

// ── Playlist generation (manual trigger) ──
export const generatePlaylists = (payload = {}) =>
  http.post('/api/campaigns/v2/playlists/generate/', payload);

// ── Generation Jobs (progress tracking) ──
export const listGenerationJobs = () =>
  http.get('/api/campaigns/v2/playlists/jobs/');

export const getGenerationJob = (id) =>
  http.get(`/api/campaigns/v2/playlists/jobs/${id}/`);

// ── Kiosk DOOH health (desired/applied version) ──
/**
 * Tüm kiosklara ait desired/applied version ve horizon bilgisini döner.
 * Backend: GET /api/pharmacies/kiosks/ — KioskSerializer Faz4/5 alanlarını içerir.
 */
export const getKioskHealth = () =>
  http.get('/api/pharmacies/kiosks/');

// ── Playlist Templates ──
export const listPlaylistTemplates = () =>
  http.get('/api/campaigns/v2/playlist-templates/');

export const createPlaylistTemplate = (data) =>
  http.post('/api/campaigns/v2/playlist-templates/', data);

export const updatePlaylistTemplate = (id, data) =>
  http.patch(`/api/campaigns/v2/playlist-templates/${id}/`, data);

export const deletePlaylistTemplate = (id) =>
  http.delete(`/api/campaigns/v2/playlist-templates/${id}/`);

// ── Hour Plans ──
export const listHourPlans = () =>
  http.get('/api/campaigns/v2/hour-plans/');

export const createHourPlan = (data) =>
  http.post('/api/campaigns/v2/hour-plans/', data);

export const updateHourPlan = (id, data) =>
  http.patch(`/api/campaigns/v2/hour-plans/${id}/`, data);

export const deleteHourPlan = (id) =>
  http.delete(`/api/campaigns/v2/hour-plans/${id}/`);

// ── Day Plans ──
export const listDayPlans = () =>
  http.get('/api/campaigns/v2/day-plans/');

export const createDayPlan = (data) =>
  http.post('/api/campaigns/v2/day-plans/', data);

export const updateDayPlan = (id, data) =>
  http.patch(`/api/campaigns/v2/day-plans/${id}/`, data);

export const deleteDayPlan = (id) =>
  http.delete(`/api/campaigns/v2/day-plans/${id}/`);

// ── Schedule Rules ──
export const listScheduleRules = () =>
  http.get('/api/campaigns/v2/rules/');

export const createScheduleRule = (data) =>
  http.post('/api/campaigns/v2/rules/', data);

export const updateScheduleRule = (id, data) =>
  http.patch(`/api/campaigns/v2/rules/${id}/`, data);

export const deleteScheduleRule = (id) =>
  http.delete(`/api/campaigns/v2/rules/${id}/`);

// ── Kiosk listesi (playlist hedefleme icin) ──
export const listKiosks = (params = {}) =>
  http.get('/api/pharmacies/kiosks/', { params });

export const forceRegenerateKiosk = (kioskId, targetDate = null) =>
  http.post('/api/campaigns/v2/playlists/generate/', {
    kiosk: kioskId,
    ...(targetDate ? { date: targetDate } : {}),
  });

// ── Lokasyon Lookup'ları (hedefleme ağacı için) ──
// getIller / getIlceler → lookups.js'den kullanın

export async function getEczanelerByIlce(ilceId) {
  if (!ilceId) return [];
  const { data } = await http.get('/api/pharmacies/', { params: { ilce: ilceId } });
  const items = Array.isArray(data) ? data : (data?.results ?? []);
  return items.map((p) => ({ id: p.id, ad: p.ad, ilce_id: p.ilce }));
}

// ── Eczane listesi (hedefleme dropdown'i icin, geriye dönük) ──
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
