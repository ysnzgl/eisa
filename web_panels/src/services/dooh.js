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

export const getCampaignRules = (id) =>
  http.get(`/api/campaigns/v2/campaigns/${id}/rules/`);

export const setCampaignRules = (id, rules) =>
  http.post(`/api/campaigns/v2/campaigns/${id}/rules/`, rules);

export const getCampaignTimeline = (params = {}) =>
  http.get('/api/campaigns/v2/campaigns/timeline/', { params });

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
