/**
 * DOOH v2 reklam motoru servis katmanı.
 * Yeni Campaign / Creative / ScheduleRule / Playlist / PricingMatrix endpoint'leri.
 */
import { http } from './api';

// ── Campaigns ──
export const listCampaignsV2 = (params = {}) =>
  http.get('/api/campaigns/v2/campaigns/', { params });

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

// ── Medya upload (creative + house ad ortak) ──
export async function uploadMedia(file) {
  const fd = new FormData();
  fd.append('file', file);
  const { data } = await http.post('/api/campaigns/upload-media/', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data; // { url, filename, object_name }
}

// ── Lokasyon Lookup'ları (hedefleme ağacı için) ──
export async function getIller() {
  const { data } = await http.get('/api/lookups/iller/', { params: { has_pharmacies: true } });
  return Array.isArray(data) ? data : [];
}

export async function getIlceler(ilId) {
  if (!ilId) return [];
  const { data } = await http.get('/api/lookups/ilceler/', { params: { il: ilId, has_pharmacies: true } });
  return Array.isArray(data) ? data : [];
}

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
