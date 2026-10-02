/**
 * Abonelik & Ödeme API servisi.
 * Admin: sözleşme/cihaz planı/fatura yönetimi.
 * Eczacı: kendi hesabı, faturaları ve "Ödeme Yap".
 */
import { http } from './api';

// ── Admin: Sözleşmeler ──────────────────────────────────────────────────────
export const listSozlesmeler = (params = {}) =>
  http.get('/api/abonelik/sozlesmeler/', { params });

export const getSozlesme = (id) =>
  http.get(`/api/abonelik/sozlesmeler/${id}/`);

export const createSozlesme = (data) =>
  http.post('/api/abonelik/sozlesmeler/', data);

export const updateSozlesme = (id, data) =>
  http.patch(`/api/abonelik/sozlesmeler/${id}/`, data);

export const saveCihazPlanlari = (sozlesmeId, plans) =>
  http.put(`/api/abonelik/sozlesmeler/${sozlesmeId}/cihaz-planlari/`, plans);

export const uploadIslakImza = (sozlesmeId, file) => {
  const fd = new FormData();
  fd.append('belge', file);
  return http.post(`/api/abonelik/sozlesmeler/${sozlesmeId}/islak-imza-yukle/`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const getIslakImzaUrl = (sozlesmeId) =>
  `/api/abonelik/sozlesmeler/${sozlesmeId}/islak-imza-indir/`;

export const uzatSozlesme = (sozlesmeId, data) =>
  http.post(`/api/abonelik/sozlesmeler/${sozlesmeId}/uzat/`, data);

export const iptalSozlesme = (sozlesmeId, data = {}) =>
  http.post(`/api/abonelik/sozlesmeler/${sozlesmeId}/iptal/`, data);

export const getSozlesmeGecmis = (sozlesmeId) =>
  http.get(`/api/abonelik/sozlesmeler/${sozlesmeId}/gecmis/`);

// ── Admin: Faturalar ────────────────────────────────────────────────────────
export const listFaturalar = (params = {}) =>
  http.get('/api/abonelik/faturalar/', { params });

export const getFaturaAdmin = (faturaId) =>
  http.get(`/api/abonelik/faturalar/${faturaId}/`);

export const odeFaturaAdmin = (faturaId, yontem = 'MANUEL', aciklama = '') =>
  http.post(`/api/abonelik/faturalar/${faturaId}/ode/`, { yontem, aciklama });

export const faturalandir = () =>
  http.post('/api/abonelik/faturalar/faturalandir/', {});

export const onaylaSozlesme = (sozlesmeId) =>
  http.post(`/api/abonelik/sozlesmelerim/${sozlesmeId}/onayla/`, {});

export const sozlesmeOnayBekleyen = () =>
  http.get('/api/abonelik/talepler/onay-bekleyen/', { __silent: true });

// ── Admin: Fiyat tanımları (parametre) ──────────────────────────────────────
export const listFiyatlar = (params = {}) =>
  http.get('/api/abonelik/fiyatlar/', { params });

export const createFiyat = (data) =>
  http.post('/api/abonelik/fiyatlar/', data);

export const deleteFiyat = (id) =>
  http.delete(`/api/abonelik/fiyatlar/${id}/`);

export const getAktifFiyat = () =>
  http.get('/api/abonelik/fiyatlar/aktif/', { __silent: true });

// ── Admin: Talepler & Ödemeler ──────────────────────────────────────────────
export const listTalepler = (params = {}) =>
  http.get('/api/abonelik/talepler/', { params });

export const kararVerTalep = (talepId, onayla, redNedeni = '', detay = {}) =>
  http.post(`/api/abonelik/talepler/${talepId}/karar/`, {
    onayla,
    red_nedeni: redNedeni,
    ...detay,
  });

export const bekleyenTalepSayisi = () =>
  http.get('/api/abonelik/talepler/bekleyen-sayisi/', { __silent: true });

export const listOdemeler = (params = {}) =>
  http.get('/api/abonelik/odemeler/', { params });

// ── Eczacı: Hesabım ─────────────────────────────────────────────────────────
export const getHesabim = () =>
  http.get('/api/abonelik/hesabim/');

export const getFaturalarim = (params = {}) =>
  http.get('/api/abonelik/faturalarim/', { params });

export const odeFatura = (faturaId, yontem = 'KREDI_KARTI', aciklama = '') =>
  http.post(`/api/abonelik/faturalarim/${faturaId}/ode/`, { yontem, aciklama });

export const getOdemelerim = () =>
  http.get('/api/abonelik/odemelerim/');

export const getHareketlerim = () =>
  http.get('/api/abonelik/hareketlerim/');

export const getTaleplerim = () =>
  http.get('/api/abonelik/taleplerim/');

export const createTalep = (data) =>
  http.post('/api/abonelik/taleplerim/', data);
