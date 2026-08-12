/**
 * Analytics servis katmanı.
 * Dashboard istatistiklerini ve oturum loglarını merkezi API'den çeker.
 */
import { http } from './api';

/** Toplam oturum sayısı, yaş/cinsiyet/kategori dağılımı ve günlük trend. */
export const getStats = () => http.get('/api/analytics/sessions/stats/');

/** Sayfalı oturum log listesi. Filtreler: is_sensitive_flow, qr_code, ordering vb. */
export const getSessions = (params = {}) =>
  http.get('/api/analytics/sessions/', { params });

/** Bir oturum danışmasını tamamlandı olarak işaretler. */
export const completeSession = (sessionId, note = '', saleResult = null, selectedIngredients = []) => {
  const payload = { note };
  if (saleResult) payload.sale_result = saleResult;
  if (selectedIngredients?.length) payload.satildi_ids = selectedIngredients;
  return http.post(`/api/analytics/sessions/${sessionId}/complete/`, payload);
};

/**
 * Kiosk hareketleri listesi (QR/oturum).
 *
 * Admin filtreleri: kiosk_id, eczane_id, il_id, ilce_id
 * Ortak: oturum_tipi, durum (COMPLETED|ABANDONED|EXPIRED), hassas_akis,
 *         danisma_tamamlandi, start_date, end_date, page, page_size
 */
export const getKioskActivities = (params = {}) =>
  http.get('/api/analytics/kiosk-activities/', { params });

/**
 * Kampanya gösterim (PlayLog) listesi.
 *
 * Admin filtreleri: campaign_id, eczane_id, il_id, ilce_id
 * Ortak: kiosk_id, start_date, end_date, page, page_size
 */
export const getCampaignImpressions = (params = {}) =>
  http.get('/api/analytics/campaign-impressions/', { params });

/**
 * Kiosk teknik olayları (KioskEvent) listesi (Faz 4).
 *
 * Admin filtreleri: eczane_id, il_id
 * Ortak: kiosk_id, event_type, severity, start_date, end_date, page, page_size
 */
export const getKioskEvents = (params = {}) =>
  http.get('/api/analytics/kiosk-events/', { params });
