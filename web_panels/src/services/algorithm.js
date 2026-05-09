/**
 * Algoritma & Karar Ağacı Servis Katmanı
 * Kategori → Soru → EtkenMadde hiyerarşisini yönetir.
 *
 * Backend field mapping:
 *   Kategori: ad→name, ikon→icon, hassas→is_sensitive, aktif→is_active
 *             hedef_cinsiyet→target_gender, hedef_yas_araliklari→target_age_ranges
 *   Soru: metin→text, sira→order, hedef_cinsiyet→target_gender,
 *         hedef_yas_araliklari→target_age_ranges,
 *         hedef_etken_maddeler→hedef_etken_maddeler (SoruEtkenMadde through model)
 *   EtkenMadde: ad→name
 *   SoruEtkenMadde: soru→question_id, etken_madde→ingredient_id,
 *                   etken_madde_ad→ingredient_name, rol→role
 *
 * Endpoints:
 *   GET    /api/products/categories/
 *   POST   /api/products/categories/
 *   PATCH  /api/products/categories/{id}/
 *   GET    /api/products/questions/?kategori={id}
 *   POST   /api/products/questions/
 *   PATCH  /api/products/questions/{id}/
 *   DELETE /api/products/questions/{id}/
 *   GET    /api/products/ingredients/
 *   POST   /api/products/ingredients/
 *   PATCH  /api/products/ingredients/{id}/
 *   DELETE /api/products/ingredients/{id}/
 *   POST   /api/products/question-ingredients/
 *   DELETE /api/products/question-ingredients/{id}/
 */
import { http } from './api';

// ─── Field mappers ────────────────────────────────────────────────────────────

function mapCategoryFromApi(c) {
  if (!c) return null;
  return {
    id: c.id,
    name: c.ad,
    slug: c.slug,
    icon: c.ikon,
    is_sensitive: c.hassas,
    is_active: c.aktif,
    target_gender: c.hedef_cinsiyet ?? null,
    target_age_ranges: c.hedef_yas_araliklari ?? [],
  };
}

function mapCategoryToApi(data) {
  const out = {};
  if (data.name         !== undefined) out.ad                  = data.name;
  if (data.slug         !== undefined) out.slug                = data.slug;
  if (data.icon         !== undefined) out.ikon                = data.icon;
  if (data.is_sensitive !== undefined) out.hassas              = data.is_sensitive;
  if (data.is_active    !== undefined) out.aktif               = data.is_active;
  if (data.target_gender     !== undefined) out.hedef_cinsiyet      = data.target_gender;
  if (data.target_age_ranges !== undefined) out.hedef_yas_araliklari = data.target_age_ranges;
  return out;
}

function mapQuestionIngredientFromApi(qi) {
  if (!qi) return null;
  return {
    id: qi.id,
    question_id: qi.soru,
    ingredient_id: qi.etken_madde,
    ingredient_name: qi.etken_madde_ad,
    role: qi.rol,
  };
}

function mapQuestionFromApi(q) {
  if (!q) return null;
  return {
    id: q.id,
    category_id: q.kategori,
    text: q.metin,
    order: q.sira,
    target_gender: q.hedef_cinsiyet ?? null,
    target_age_ranges: q.hedef_yas_araliklari ?? [],
    hedef_etken_maddeler: (q.hedef_etken_maddeler ?? []).map(mapQuestionIngredientFromApi),
  };
}

function mapIngredientFromApi(i) {
  if (!i) return null;
  return {
    id: i.id,
    name: i.ad,
    description: i.aciklama ?? '',
    is_active: i.aktif ?? true,
  };
}

// ─── Kategori Servisleri ──────────────────────────────────────────────────────

/** Tüm kategorileri listeler. */
export async function getCategories() {
  const { data } = await http.get('/api/products/categories/');
  const items = Array.isArray(data) ? data : (data?.results ?? []);
  return items.map(mapCategoryFromApi);
}

/**
 * Yeni kategori oluşturur.
 * @param {{ name: string, slug?: string, icon?: string, is_sensitive?: boolean }} data
 */
export async function createCategory(data) {
  if (!data.slug) {
    data = {
      ...data,
      slug: data.name
        .toLowerCase()
        .replace(/ğ/g, 'g').replace(/ü/g, 'u').replace(/ş/g, 's')
        .replace(/ı/g, 'i').replace(/ö/g, 'o').replace(/ç/g, 'c')
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$$/g, ''),
    };
  }
  const { data: created } = await http.post('/api/products/categories/', mapCategoryToApi(data));
  return mapCategoryFromApi(created);
}

/**
 * Kategoriyi günceller (hedefleme alanları dahil).
 * @param {number} id
 * @param {object} data
 */
export async function updateCategory(id, data) {
  const { data: updated } = await http.patch(
    `/api/products/categories/${id}/`,
    mapCategoryToApi(data),
  );
  return mapCategoryFromApi(updated);
}

// ─── Soru Servisleri ──────────────────────────────────────────────────────────

/**
 * Kategoriye ait soruları getirir.
 * @param {number} categoryId
 */
export async function getQuestions(categoryId) {
  const { data } = await http.get('/api/products/questions/', {
    params: { kategori: categoryId },
  });
  const items = Array.isArray(data) ? data : (data?.results ?? []);
  return items.map(mapQuestionFromApi);
}

/**
 * Yeni soru ekler.
 * @param {number} categoryId
 * @param {{ text: string, order?: number, target_gender?: number|null, target_age_ranges?: number[] }} data
 */
export async function createQuestion(categoryId, data) {
  const payload = {
    kategori: categoryId,
    metin: data.text,
    sira: data.order ?? 0,
    hedef_cinsiyet: data.target_gender ?? null,
    hedef_yas_araliklari: data.target_age_ranges ?? [],
  };
  const { data: created } = await http.post('/api/products/questions/', payload);
  return mapQuestionFromApi(created);
}

/**
 * Soruyu günceller.
 * @param {number} id
 * @param {{ text?: string, order?: number, target_gender?: number|null, target_age_ranges?: number[] }} data
 */
export async function updateQuestion(id, data) {
  const payload = {};
  if (data.text              !== undefined) payload.metin                = data.text;
  if (data.order             !== undefined) payload.sira                 = data.order;
  if (data.target_gender     !== undefined) payload.hedef_cinsiyet       = data.target_gender;
  if (data.target_age_ranges !== undefined) payload.hedef_yas_araliklari = data.target_age_ranges;
  const { data: updated } = await http.patch(`/api/products/questions/${id}/`, payload);
  return mapQuestionFromApi(updated);
}

/**
 * Soruyu siler.
 * @param {number} id
 */
export async function deleteQuestion(id) {
  await http.delete(`/api/products/questions/${id}/`);
}

// ─── Soru–EtkenMadde Bağlantı Servisleri ─────────────────────────────────────

/**
 * Soruya etken madde ekler.
 * @param {number} questionId
 * @param {number} ingredientId
 * @param {'ana'|'destekleyici'} role
 */
export async function addQuestionIngredient(questionId, ingredientId, role = 'ana') {
  const { data } = await http.post('/api/products/question-ingredients/', {
    soru: questionId,
    etken_madde: ingredientId,
    rol: role,
  });
  return mapQuestionIngredientFromApi(data);
}

/**
 * Soru–EtkenMadde bağlantısını siler.
 * @param {number} linkId  SoruEtkenMadde kaydının id'si
 */
export async function removeQuestionIngredient(linkId) {
  await http.delete(`/api/products/question-ingredients/${linkId}/`);
}

// ─── Etken Madde Servisleri ───────────────────────────────────────────────────

/** Tüm aktif etken maddeleri listeler. */
export async function getActiveIngredients() {
  const { data } = await http.get('/api/products/ingredients/');
  const items = Array.isArray(data) ? data : (data?.results ?? []);
  return items.map(mapIngredientFromApi);
}

/** Pasif dahil tüm etken maddeleri listeler (yönetim ekranı için). */
export async function getAllIngredients() {
  const { data } = await http.get('/api/products/ingredients/', {
    params: { include_inactive: 1 },
  });
  const items = Array.isArray(data) ? data : (data?.results ?? []);
  return items.map(mapIngredientFromApi);
}

/** Yeni etken madde ekler. */
export async function createIngredient(data) {
  const payload = {
    ad: data.name,
    aciklama: data.description ?? '',
  };
  const { data: created } = await http.post('/api/products/ingredients/', payload);
  return mapIngredientFromApi(created);
}

/** Etken madde ad/aciklama alanlarini gunceller. */
export async function updateIngredient(id, data) {
  const payload = {};
  if (data.name !== undefined) payload.ad = data.name;
  if (data.description !== undefined) payload.aciklama = data.description;
  if (data.is_active !== undefined) payload.aktif = data.is_active;
  const { data: updated } = await http.patch(`/api/products/ingredients/${id}/`, payload);
  return mapIngredientFromApi(updated);
}

/** Pasif bir etken maddeyi aktifleştirir. */
export async function reactivateIngredient(id) {
  const { data: updated } = await http.patch(`/api/products/ingredients/${id}/`, { aktif: true });
  return mapIngredientFromApi(updated);
}

/** Etken maddeyi soft-delete ile pasiflestirir. */
export async function softDeleteIngredient(id) {
  await http.delete(`/api/products/ingredients/${id}/`);
}
