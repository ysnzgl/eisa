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
export const completeSession = (sessionId, note = '') =>
  http.post(`/api/analytics/sessions/${sessionId}/complete/`, { note });
