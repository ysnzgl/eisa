/**
 * Kampanya servis katmanı.
 * CRUD işlemleri için merkezi API'ye istek atar.
 */
import { http } from './api';

/** Tüm kampanyaları listele. Filtreler: is_active, city vb. */
export const getCampaigns = (params = {}) =>
  http.get('/api/campaigns/', { params });

/** Yeni kampanya oluştur. */
export const createCampaign = (data) =>
  http.post('/api/campaigns/', data);

/** Kampanyayı kısmen güncelle (örn. is_active toggle). */
export const updateCampaign = (id, data) =>
  http.patch(`/api/campaigns/${id}/`, data);

/** Kampanyayı tamamen güncelle. */
export const replaceCampaign = (id, data) =>
  http.put(`/api/campaigns/${id}/`, data);

/** Kampanyayı sil. */
export const deleteCampaign = (id) =>
  http.delete(`/api/campaigns/${id}/`);
