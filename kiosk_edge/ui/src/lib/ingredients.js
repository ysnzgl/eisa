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

  for (const ans of answers) {
    if (ans.answer !== 'Y') continue;

    const question = questions.find(q => q.seed_id === ans.id);
    if (!question?.match_rules?.length) continue;

    for (const rule of question.match_rules) {
      if (!rule.gender.includes(gender)) continue;
      if (age < rule.age_min || age > rule.age_max) continue;
      recs.set(rule.primary, rule.supportive);
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
