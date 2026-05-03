/**
 * match_rules tabanlı takviye önerisi motoru.
 *
 * match_rules format:
 *   [{ gender: ["M"|"F"], age_min: int, age_max: int, primary: string, supportive: string }]
 *
 * Kullanım:
 *   const recs = getRecommendations(questions, answers, ageRange, gender);
 *   // => [{ primary: "...", supportive: "..." }, ...]
 */

/** Yaş aralığı stringinden temsil edici tam sayı yaş. */
export function representativeAge(ageRange) {
  const map = {
    '0-17': 10, '18-25': 21, '26-35': 30,
    '36-50': 43, '51-65': 58, '65+': 70,
  };
  return map[ageRange] ?? 30;
}

/**
 * @param {Array<{seed_id:string, match_rules:Array}>} questions  - API'den gelen sorular
 * @param {Array<{id:string, answer:'Y'|'N'}>}        answers     - Kullanıcı cevapları
 * @param {string}                                     ageRange   - "18-25" vb.
 * @param {'M'|'F'}                                    gender
 * @returns {Array<{primary:string, supportive:string}>}
 */
export function getRecommendations(questions, answers, ageRange, gender) {
  const age = representativeAge(ageRange);
  const recs = new Map(); // primary → supportive  (deduplicate)

  if (!Array.isArray(questions) || !Array.isArray(answers)) return [];

  for (const ans of answers) {
    if (!ans || ans.answer !== 'Y') continue;

    const question = questions.find((q) => q && q.seed_id === ans.id);
    // Backend yeni şemada `eslesme_kurallari` gönderir; eski `match_rules` da fallback olarak kabul edilir.
    const rules = question?.eslesme_kurallari ?? question?.match_rules;
    if (!Array.isArray(rules) || rules.length === 0) continue;

    for (const rule of rules) {
      if (!rule || typeof rule !== 'object') continue;
      const ruleGenders = Array.isArray(rule.gender) ? rule.gender : [];
      if (!ruleGenders.includes(gender)) continue;
      const minAge = Number.isFinite(rule.age_min) ? rule.age_min : 0;
      const maxAge = Number.isFinite(rule.age_max) ? rule.age_max : 200;
      if (age < minAge || age > maxAge) continue;
      if (!rule.primary) continue;
      recs.set(rule.primary, rule.supportive || '');
      break; // ilk eşleşen kural yeterli
    }
  }

  return [...recs.entries()].map(([primary, supportive]) => ({ primary, supportive }));
}

/**
 * Önerileri düz metin listesine dönüştürür (submit payload için).
 * @param {Array<{primary:string, supportive:string}>} recs
 * @returns {string[]}
 */
export function recsToIngredientList(recs) {
  return recs.flatMap(r => [r.primary, r.supportive].filter(Boolean));
}
