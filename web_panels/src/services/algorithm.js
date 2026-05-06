/**
 * Algoritma & Karar Ağacı Servis Katmanı
 * Kategori → Soru → Eşleşme Kuralı hiyerarşisini yönetir.
 *
 * Backend field mapping:
 *   Kategori: ad→name, ikon→icon, hassas→is_sensitive, aktif→is_active
 *             hedef_cinsiyetler→target_genders, hedef_yas_araliklari→target_age_ranges
 *   Soru: metin→text, sira→order, eslesme_kurallari→match_rules
 *   EtkenMadde: ad→name
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
    target_genders: c.hedef_cinsiyetler ?? [],
    target_age_ranges: c.hedef_yas_araliklari ?? [],
  };
}

function mapCategoryToApi(data) {
  const out = {};
  if (data.name         !== undefined) out.ad                   = data.name;
  if (data.slug         !== undefined) out.slug                 = data.slug;
  if (data.icon         !== undefined) out.ikon                 = data.icon;
  if (data.is_sensitive !== undefined) out.hassas               = data.is_sensitive;
  if (data.is_active    !== undefined) out.aktif                = data.is_active;
  if (data.target_genders    !== undefined) out.hedef_cinsiyetler     = data.target_genders;
  if (data.target_age_ranges !== undefined) out.hedef_yas_araliklari  = data.target_age_ranges;
  return out;
}

function mapQuestionFromApi(q) {
  if (!q) return null;
  return {
    id: q.id,
    category_id: q.kategori,
    seed_id: q.seed_id ?? null,
    text: q.metin,
    order: q.sira,
    match_rules: q.eslesme_kurallari ?? [],
    target_genders: q.hedef_cinsiyetler ?? [],
    target_age_ranges: q.hedef_yas_araliklari ?? [],
  };
}

function mapIngredientFromApi(i) {
  if (!i) return null;
  return { id: i.id, name: i.ad, description: i.aciklama ?? '' };
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
 * @param {{ text: string, order?: number }} data
 */
export async function createQuestion(categoryId, data) {
  const payload = {
    kategori: categoryId,
    metin: data.text,
    sira: data.order ?? 0,
    eslesme_kurallari: [],
  };
  const { data: created } = await http.post('/api/products/questions/', payload);
  return mapQuestionFromApi(created);
}

/**
 * Soruyu günceller.
 * @param {number} id
 * @param {{ text?: string, match_rules?: Array }} data
 */
export async function updateQuestion(id, data) {
  const payload = {};
  if (data.text        !== undefined) payload.metin             = data.text;
  if (data.order       !== undefined) payload.sira              = data.order;
  if (data.match_rules !== undefined) payload.eslesme_kurallari = data.match_rules;
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

// ─── Match Rule Yardımcıları ──────────────────────────────────────────────────

let _ruleIdSeq = Date.now();

/** Bir soruya yeni kural ekler, güncellenmiş soruyu döner. */
export async function addMatchRule(questionId, ruleData) {
  const question = await getQuestionById(questionId);
  const newRule = { id: _ruleIdSeq++, ...ruleData };
  const updatedRules = [...(question.match_rules ?? []), newRule];
  return updateQuestion(questionId, { match_rules: updatedRules });
}

/** Varolan bir kuralı günceller. */
export async function updateMatchRule(questionId, ruleId, ruleData) {
  const question = await getQuestionById(questionId);
  const updatedRules = (question.match_rules ?? []).map((r) =>
    r.id === ruleId ? { ...r, ...ruleData } : r,
  );
  return updateQuestion(questionId, { match_rules: updatedRules });
}

/** Kuralı siler. */
export async function deleteMatchRule(questionId, ruleId) {
  const question = await getQuestionById(questionId);
  const updatedRules = (question.match_rules ?? []).filter((r) => r.id !== ruleId);
  await updateQuestion(questionId, { match_rules: updatedRules });
}

/** Tek soruyu id ile getirir. */
async function getQuestionById(id) {
  const { data } = await http.get(`/api/products/questions/${id}/`);
  return mapQuestionFromApi(data);
}

// ─── Etken Madde Servisleri ───────────────────────────────────────────────────

/** Tüm etken maddeleri listeler. */
export async function getActiveIngredients() {
  const { data } = await http.get('/api/products/ingredients/');
  const items = Array.isArray(data) ? data : (data?.results ?? []);
  return items.map(mapIngredientFromApi);
}
