/**
 * Web Sitesi (eisa.com.tr) yönetim servisi — portal "Web Sitesi" modülü.
 *
 * Sözleşme: docs/web-sitesi/CONTRACT.md §5 — prefix `/api/website/admin/`.
 * Yetki: superadmin veya editor (backend `IsWebsiteEditor`).
 *
 * Liste uçları düz dizi döner; `medya` ve `basvurular` `{ count, results }`
 * biçiminde sayfalanır (`?page=&page_size=`).
 *
 * Not: Sayfa/blok/blog kayıtları `__silent` çağrılır; 400 (alan hataları) ve
 * 409 (sürüm çakışması) ekran tarafından alan bazında gösterilir. Diğer
 * hatalar için ekran `humanError` ile toast basar.
 */
import { http } from './api';

const BASE = '/api/website/admin';
const SESSIZ = { __silent: true };

function _dizi(data) {
  return Array.isArray(data) ? data : (data?.results ?? []);
}

/** API kök adresi (boş → same-origin). Zengin metindeki göreli medya yolları için. */
export function apiBase() {
  return String(http.defaults?.baseURL || '').replace(/\/+$/, '');
}

/**
 * Medya `yol` alanından tam URL üretir (CONTRACT §2: portal `API_BASE + yol`).
 * Zaten mutlak olan (http/https/blob/data) adresler olduğu gibi döner.
 */
export function medyaUrl(yol) {
  if (!yol) return '';
  if (/^(https?:|blob:|data:)/i.test(yol)) return yol;
  return `${apiBase()}${yol}`;
}

// ── Ayarlar ───────────────────────────────────────────────────────────────────
export async function getAyarlar() {
  const { data } = await http.get(`${BASE}/ayarlar/`);
  return data;
}

export async function updateAyarlar(payload) {
  const { data } = await http.patch(`${BASE}/ayarlar/`, payload, SESSIZ);
  return data;
}

// ── Blok tipleri ──────────────────────────────────────────────────────────────
// ── Arama ("Sitede ara") ──────────────────────────────────────────────────────
/**
 * Tüm site içeriğinde (taslak) arama. `signal` ile önceki istek iptal edilebilir.
 * → { q, toplam, kesildi, sonuclar: [{ grup, blok?, konum[], hedef, parca, adet }] }
 */
export async function siteAra(q, { signal } = {}) {
  const { data } = await http.get(`${BASE}/arama/`, { params: { q }, signal, ...SESSIZ });
  return data;
}
export async function listBlokTipleri() {
  const { data } = await http.get(`${BASE}/blok-tipleri/`);
  return _dizi(data);
}

// ── Menüler ───────────────────────────────────────────────────────────────────
export async function getMenuler() {
  const { data } = await http.get(`${BASE}/menuler/`);
  return data;
}

/** Konumun (header | footer | footer_alt) ağacını atomik olarak değiştirir. */
export async function saveMenu(konum, agac) {
  const { data } = await http.put(`${BASE}/menuler/${konum}/`, agac, SESSIZ);
  return data;
}

// ── Sayfalar ──────────────────────────────────────────────────────────────────
export async function listSayfalar() {
  const { data } = await http.get(`${BASE}/sayfalar/`);
  return _dizi(data);
}

export async function createSayfa(payload) {
  const { data } = await http.post(`${BASE}/sayfalar/`, payload, SESSIZ);
  return data;
}

export async function getSayfa(id) {
  const { data } = await http.get(`${BASE}/sayfalar/${id}/`);
  return data;
}

/** Meta alanları + `surum` (optimistic concurrency; uyuşmazsa 409). */
export async function updateSayfa(id, payload) {
  const { data } = await http.patch(`${BASE}/sayfalar/${id}/`, payload, SESSIZ);
  return data;
}

export async function deleteSayfa(id) {
  await http.delete(`${BASE}/sayfalar/${id}/`);
}

/** Taslak blokların tamamını değiştirir; dizi sırası `sira`yı belirler. */
export async function saveBloklar(id, surum, bloklar) {
  const { data } = await http.put(`${BASE}/sayfalar/${id}/bloklar/`, { surum, bloklar }, SESSIZ);
  return data;
}

export async function yayinlaSayfa(id, not = '') {
  const { data } = await http.post(`${BASE}/sayfalar/${id}/yayinla/`, { not });
  return data;
}

export async function yayindanKaldirSayfa(id) {
  const { data } = await http.post(`${BASE}/sayfalar/${id}/yayindan-kaldir/`);
  return data;
}

export async function listRevizyonlar(id) {
  const { data } = await http.get(`${BASE}/sayfalar/${id}/revizyonlar/`);
  return _dizi(data);
}

export async function geriAlRevizyon(id, rid) {
  const { data } = await http.post(`${BASE}/sayfalar/${id}/revizyonlar/${rid}/geri-al/`);
  return data;
}

/** → `{ url }` (site önizleme linki, 1 saat geçerli). */
export async function sayfaOnizleme(id) {
  const { data } = await http.post(`${BASE}/sayfalar/${id}/onizleme/`);
  return data;
}

// ── Blog ──────────────────────────────────────────────────────────────────────
export async function listBlogKategorileri() {
  const { data } = await http.get(`${BASE}/blog/kategoriler/`);
  return _dizi(data);
}

export async function createBlogKategori(payload) {
  const { data } = await http.post(`${BASE}/blog/kategoriler/`, payload);
  return data;
}

export async function updateBlogKategori(id, payload) {
  const { data } = await http.patch(`${BASE}/blog/kategoriler/${id}/`, payload);
  return data;
}

export async function deleteBlogKategori(id) {
  await http.delete(`${BASE}/blog/kategoriler/${id}/`);
}

export async function listBlogYazilari(params = {}) {
  const { data } = await http.get(`${BASE}/blog/yazilar/`, { params });
  return _dizi(data);
}

export async function getBlogYazisi(id) {
  const { data } = await http.get(`${BASE}/blog/yazilar/${id}/`);
  return data;
}

export async function createBlogYazisi(payload) {
  const { data } = await http.post(`${BASE}/blog/yazilar/`, payload, SESSIZ);
  return data;
}

export async function updateBlogYazisi(id, payload) {
  const { data } = await http.patch(`${BASE}/blog/yazilar/${id}/`, payload, SESSIZ);
  return data;
}

export async function deleteBlogYazisi(id) {
  await http.delete(`${BASE}/blog/yazilar/${id}/`);
}

export async function blogYazisiOnizleme(id) {
  const { data } = await http.post(`${BASE}/blog/yazilar/${id}/onizleme/`);
  return data;
}

// ── Medya ─────────────────────────────────────────────────────────────────────
/** `{ q, page, page_size }` → `{ count, results }` */
export async function listMedya(params = {}) {
  const { data } = await http.get(`${BASE}/medya/`, { params });
  return { count: data?.count ?? 0, results: data?.results ?? [] };
}

/** Multipart yükleme: `dosya` + opsiyonel `alt`. `onProgress(0..100)` opsiyonel. */
export async function uploadMedya(dosya, alt = '', onProgress) {
  const form = new FormData();
  form.append('dosya', dosya);
  if (alt) form.append('alt', alt);
  const { data } = await http.post(`${BASE}/medya/`, form, {
    __silent: true,
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
    },
  });
  return data;
}

export async function updateMedya(id, payload) {
  const { data } = await http.patch(`${BASE}/medya/${id}/`, payload);
  return data;
}

export async function deleteMedya(id) {
  await http.delete(`${BASE}/medya/${id}/`);
}

// ── Başvurular ────────────────────────────────────────────────────────────────
/** `{ tip, durum, q, page, page_size }` → `{ count, results, yeni_sayisi }` */
export async function listBasvurular(params = {}) {
  const { data } = await http.get(`${BASE}/basvurular/`, { params });
  return {
    count: data?.count ?? 0,
    results: data?.results ?? [],
    yeni_sayisi: data?.yeni_sayisi ?? 0,
  };
}

export async function getBasvuru(id) {
  const { data } = await http.get(`${BASE}/basvurular/${id}/`);
  return data;
}

/** Değişebilen alanlar: `durum`, `notlar`, `atanan_id`. */
export async function updateBasvuru(id, payload) {
  const { data } = await http.patch(`${BASE}/basvurular/${id}/`, payload);
  return data;
}

export async function deleteBasvuru(id) {
  await http.delete(`${BASE}/basvurular/${id}/`);
}

/** Menü rozeti için yeni başvuru sayısı. Hata kullanıcıyı engellemez (sessiz). */
export async function getBasvuruOzet() {
  const { data } = await http.get(`${BASE}/basvurular/ozet/`, SESSIZ);
  return { yeni: data?.yeni ?? 0 };
}
