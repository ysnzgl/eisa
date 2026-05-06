/**
 * Lookup (sabit veri) Servis Katmanı
 * İl, İlçe, Cinsiyet ve Yaş Aralığı listelerini backend'den alır.
 */
import { http } from './api';

/** Tüm illeri döner. */
export async function getIller() {
  const r = await http.get('/api/lookups/iller/');
  return r.data; // [{ id, ad, plaka }]
}

/**
 * İle ait ilçeleri döner.
 * @param {number} ilId
 */
export async function getIlceler(ilId) {
  if (!ilId) return [];
  const r = await http.get('/api/lookups/ilceler/', { params: { il: ilId } });
  return r.data; // [{ id, ad, il_id }]
}

/** Cinsiyet listesini döner. */
export async function getCinsiyetler() {
  const r = await http.get('/api/lookups/cinsiyetler/');
  return r.data; // [{ id, kod, ad }]
}

/** Yaş aralıklarını döner. */
export async function getYasAraliklari() {
  const r = await http.get('/api/lookups/yas-araliklari/');
  return r.data; // [{ id, kod, ad, alt_sinir, ust_sinir }]
}
