/**
 * Algoritma & Karar Ağacı Servis Katmanı
 * Kategori → Soru → Eşleşme Kuralı hiyerarşisini yönetir.
 *
 * Gerçek endpoint'ler:
 *   GET    /api/products/categories/
 *   GET    /api/products/questions/?category={id}
 *   POST   /api/products/questions/
 *   PATCH  /api/products/questions/{id}/
 *   DELETE /api/products/questions/{id}/
 *   GET    /api/products/active-ingredients/
 *   PATCH  /api/products/questions/{id}/  (match_rules alanını günceller)
 */
import { http } from './api';

// ─── Mock: Etken Maddeler ─────────────────────────────────────────────────────
const _ingredients = [
  { id: 1,  name: 'B12 Vitamini'       },
  { id: 2,  name: 'Demir (Fe)'         },
  { id: 3,  name: 'Magnezyum'          },
  { id: 4,  name: 'D3 Vitamini'        },
  { id: 5,  name: 'Çinko'              },
  { id: 6,  name: 'Omega-3'            },
  { id: 7,  name: 'Melatonin'          },
  { id: 8,  name: 'L-Teanin'           },
  { id: 9,  name: 'Valerian Kökü'      },
  { id: 10, name: 'Ashwagandha'        },
  { id: 11, name: 'Koenzim Q10'        },
  { id: 12, name: 'Folat (B9)'         },
  { id: 13, name: 'C Vitamini'         },
  { id: 14, name: 'Probiyotik'         },
  { id: 15, name: 'Çuha Çiçeği Yağı'  },
];

// ─── Mock: Kategoriler + Sorular + Kurallar ────────────────────────────────────
let _ruleIdSeq = 100;
const _categories = [
  {
    id: 1, name: 'Enerji & Yorgunluk', slug: 'enerji', icon: '⚡',
    is_sensitive: false, is_active: true,
    questions: [
      {
        id: 1, seed_id: 'Q_ENR_001', text: 'Yorgunluğunuz gün içinde ne zaman artıyor?', order: 0,
        match_rules: [
          { id: _ruleIdSeq++, gender: 'all', age_min: 18, age_max: 40, primary_id: 1, supportive_id: 3 },
          { id: _ruleIdSeq++, gender: 'F',   age_min: 18, age_max: 50, primary_id: 2, supportive_id: 4 },
        ],
      },
      {
        id: 2, seed_id: 'Q_ENR_002', text: 'Egzersiz sonrası kendinizi nasıl hissediyorsunuz?', order: 1,
        match_rules: [
          { id: _ruleIdSeq++, gender: 'M', age_min: 20, age_max: 55, primary_id: 11, supportive_id: 5 },
        ],
      },
    ],
  },
  {
    id: 2, name: 'Uyku Kalitesi', slug: 'uyku', icon: '🌙',
    is_sensitive: false, is_active: true,
    questions: [
      {
        id: 3, seed_id: 'Q_UYK_001', text: 'Uykuya dalmakta güçlük çekiyor musunuz?', order: 0,
        match_rules: [
          { id: _ruleIdSeq++, gender: 'all', age_min: 18, age_max: 65, primary_id: 7, supportive_id: 8 },
          { id: _ruleIdSeq++, gender: 'all', age_min: 50, age_max: 99, primary_id: 7, supportive_id: 9 },
        ],
      },
      {
        id: 4, seed_id: 'Q_UYK_002', text: 'Gece kaç kez uyanıyorsunuz?', order: 1,
        match_rules: [],
      },
    ],
  },
  {
    id: 3, name: 'Bağışıklık', slug: 'bagisiklik', icon: '🛡️',
    is_sensitive: false, is_active: true,
    questions: [
      {
        id: 5, seed_id: 'Q_BAG_001', text: 'Yılda kaç kez hastalanıyorsunuz?', order: 0,
        match_rules: [
          { id: _ruleIdSeq++, gender: 'all', age_min: 0, age_max: 17, primary_id: 13, supportive_id: 5 },
          { id: _ruleIdSeq++, gender: 'all', age_min: 18, age_max: 99, primary_id: 13, supportive_id: 4 },
        ],
      },
    ],
  },
  {
    id: 4, name: 'Sindirim', slug: 'sindirim', icon: '🌿',
    is_sensitive: false, is_active: true,
    questions: [
      {
        id: 6, seed_id: 'Q_SND_001', text: 'Yemek sonrası şişkinlik hissediyor musunuz?', order: 0,
        match_rules: [
          { id: _ruleIdSeq++, gender: 'all', age_min: 18, age_max: 99, primary_id: 14, supportive_id: 6 },
        ],
      },
    ],
  },
  {
    id: 5, name: 'Gebelik / Emzirme', slug: 'gebelik', icon: '🤱',
    is_sensitive: true, is_active: true,
    questions: [
      {
        id: 7, seed_id: 'Q_GEB_001', text: 'Gebelik kaçıncı trimesterinde?', order: 0,
        match_rules: [
          { id: _ruleIdSeq++, gender: 'F', age_min: 18, age_max: 45, primary_id: 12, supportive_id: 4 },
        ],
      },
    ],
  },
  {
    id: 6, name: 'Stres & Anksiyete', slug: 'stres', icon: '🧠',
    is_sensitive: false, is_active: true,
    questions: [
      {
        id: 8, seed_id: 'Q_STR_001', text: 'Stres günlük yaşamınızı etkiliyor mu?', order: 0,
        match_rules: [
          { id: _ruleIdSeq++, gender: 'all', age_min: 18, age_max: 65, primary_id: 10, supportive_id: 3 },
        ],
      },
    ],
  },
];

let _qIdSeq = 100;

function _delay(ms = 300) {
  return new Promise((r) => setTimeout(r, ms));
}

function _deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

// ─── Kategori Servisleri ──────────────────────────────────────────────────────

/**
 * Tüm kategorileri listeler.
 * Gerçek API: return http.get('/api/products/categories/').then(r => r.data);
 */
export async function getCategories() {
  await _delay();
  return _categories.map(({ questions: _, ...cat }) => _deepClone(cat));
}

// ─── Soru Servisleri ──────────────────────────────────────────────────────────

/**
 * Kategoriye ait soruları getirir.
 * Gerçek API: return http.get('/api/products/questions/', { params: { category: categoryId } }).then(r => r.data);
 * @param {number} categoryId
 */
export async function getQuestions(categoryId) {
  await _delay();
  const cat = _categories.find((c) => c.id === categoryId);
  if (!cat) return [];
  return _deepClone(cat.questions);
}

/**
 * Yeni soru ekler.
 * Gerçek API: return http.post('/api/products/questions/', data).then(r => r.data);
 * @param {number} categoryId
 * @param {{ text: string, order?: number }} data
 */
export async function createQuestion(categoryId, data) {
  await _delay();
  const cat = _categories.find((c) => c.id === categoryId);
  if (!cat) throw new Error('Kategori bulunamadı');
  const q = {
    id: _qIdSeq++,
    seed_id: null,
    text: data.text,
    order: data.order ?? cat.questions.length,
    match_rules: [],
  };
  cat.questions.push(q);
  return _deepClone(q);
}

/**
 * Soruyu günceller.
 * Gerçek API: return http.patch(`/api/products/questions/${id}/`, data).then(r => r.data);
 * @param {number} id
 * @param {{ text?: string, match_rules?: Array }} data
 */
export async function updateQuestion(id, data) {
  await _delay();
  for (const cat of _categories) {
    const q = cat.questions.find((q) => q.id === id);
    if (q) {
      Object.assign(q, data);
      return _deepClone(q);
    }
  }
  throw new Error(`Soru bulunamadı: ${id}`);
}

/**
 * Soruyu siler.
 * Gerçek API: return http.delete(`/api/products/questions/${id}/`);
 * @param {number} id
 */
export async function deleteQuestion(id) {
  await _delay();
  for (const cat of _categories) {
    const idx = cat.questions.findIndex((q) => q.id === id);
    if (idx !== -1) { cat.questions.splice(idx, 1); return; }
  }
}

// ─── Match Rule Yardımcıları (client-side, patch ile gönderilir) ──────────────

/** Bir soruya yeni kural ekler, güncellenmiş soruyu döner. */
export async function addMatchRule(questionId, ruleData) {
  await _delay(200);
  for (const cat of _categories) {
    const q = cat.questions.find((q) => q.id === questionId);
    if (q) {
      const rule = { id: _ruleIdSeq++, ...ruleData };
      q.match_rules.push(rule);
      // Gerçek API: await http.patch(`/api/products/questions/${questionId}/`, { match_rules: q.match_rules });
      return _deepClone(q);
    }
  }
  throw new Error('Soru bulunamadı');
}

/** Varolan bir kuralı günceller. */
export async function updateMatchRule(questionId, ruleId, ruleData) {
  await _delay(200);
  for (const cat of _categories) {
    const q = cat.questions.find((q) => q.id === questionId);
    if (q) {
      const idx = q.match_rules.findIndex((r) => r.id === ruleId);
      if (idx !== -1) Object.assign(q.match_rules[idx], ruleData);
      // Gerçek API: await http.patch(`/api/products/questions/${questionId}/`, { match_rules: q.match_rules });
      return _deepClone(q);
    }
  }
  throw new Error('Soru veya kural bulunamadı');
}

/** Kuralı siler. */
export async function deleteMatchRule(questionId, ruleId) {
  await _delay(200);
  for (const cat of _categories) {
    const q = cat.questions.find((q) => q.id === questionId);
    if (q) {
      q.match_rules = q.match_rules.filter((r) => r.id !== ruleId);
      // Gerçek API: await http.patch(`/api/products/questions/${questionId}/`, { match_rules: q.match_rules });
      return;
    }
  }
}

// ─── Etken Madde Servisleri ───────────────────────────────────────────────────

/**
 * Tüm etken maddeleri listeler.
 * Gerçek API: return http.get('/api/products/active-ingredients/').then(r => r.data);
 */
export async function getActiveIngredients() {
  await _delay(150);
  return _deepClone(_ingredients);
}
