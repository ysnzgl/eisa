/**
 * kiosk_edge UI — merkezi API istemcisi
 * Tüm fetch çağrıları burada, bileşenler sadece bu fonksiyonları kullanır.
 */

const API_BASE = 'http://127.0.0.1:8765';

export async function fetchCategories() {
  const res = await fetch(`${API_BASE}/api/categories`, {
    signal: AbortSignal.timeout(4000),
  });
  if (!res.ok) throw new Error('HTTP ' + res.status);
  return res.json();
}

export async function fetchQuestions(categorySlug) {
  const res = await fetch(`${API_BASE}/api/categories/${categorySlug}/questions`, {
    signal: AbortSignal.timeout(4000),
  });
  if (!res.ok) throw new Error('HTTP ' + res.status);
  return res.json();
}

/**
 * @param {object} payload
 * @param {string} payload.ageRange
 * @param {string} payload.gender
 * @param {string} payload.categorySlug
 * @param {boolean} payload.isSensitiveFlow
 * @param {object} payload.answersPayload  — { seed_id: 'Y'|'N' }
 * @param {string[]} payload.ingredientList
 * @returns {Promise<{qrCode: string, qrPayload: string}>}
 */
export async function submitSession({ ageRange, gender, categorySlug, isSensitiveFlow, answersPayload, ingredientList }) {
  const res = await fetch(`${API_BASE}/api/session/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      age_range:             ageRange,
      gender,
      category_slug:         categorySlug,
      is_sensitive_flow:     isSensitiveFlow,
      answers_payload:       answersPayload,
      suggested_ingredients: ingredientList,
    }),
    signal: AbortSignal.timeout(5000),
  });
  if (!res.ok) throw new Error('HTTP ' + res.status);
  const data = await res.json();
  // Şifreli payload yoksa (eski edge), kısa kodu fallback olarak kullan.
  return { qrCode: data.qr_code, qrPayload: data.qr_payload || data.qr_code };
}

export async function fetchActiveCampaigns() {
  const res = await fetch(`${API_BASE}/api/campaigns/active`, {
    signal: AbortSignal.timeout(4000),
  });
  if (!res.ok) throw new Error('HTTP ' + res.status);
  return res.json();
}

export async function logAdImpression({ campaignId, shownAt, durationMs }) {
  await fetch(`${API_BASE}/api/ad-impression`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      campaign_id: campaignId,
      shown_at:    shownAt,
      duration_ms: durationMs,
    }),
  }).catch(() => {/* görmezden gel */});
}
