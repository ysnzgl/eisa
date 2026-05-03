/**
 * kiosk_edge UI — merkezi API istemcisi
 * Tüm fetch çağrıları burada, bileşenler sadece bu fonksiyonları kullanır.
 */

const API_BASE = 'http://127.0.0.1:8765';

/**
 * ERR-005 + ERR-007: Tutarlı fetch sarmalayıcısı.
 *  - AbortError → kullanıcı dostu zaman aşımı mesajı.
 *  - Network error → bağlantı mesajı.
 *  - HTTP 4xx/5xx → status'e göre okunur metin.
 *  - Hata objesinin `userMessage` alanı UI'da bileşenlere gösterilebilir.
 */
async function _request(url, { method = 'GET', body, timeoutMs = 4000, retry = 0 } = {}) {
  const init = {
    method,
    signal: AbortSignal.timeout(timeoutMs),
  };
  if (body !== undefined) {
    init.headers = { 'Content-Type': 'application/json' };
    init.body = JSON.stringify(body);
  }

  let lastErr;
  for (let attempt = 0; attempt <= retry; attempt += 1) {
    try {
      const res = await fetch(url, init);
      if (!res.ok) {
        const err = new Error(`HTTP ${res.status}`);
        err.status = res.status;
        err.userMessage = _statusMessage(res.status);
        throw err;
      }
      if (res.status === 204) return null;
      return await res.json();
    } catch (err) {
      lastErr = err;
      if (err?.name === 'AbortError' || err?.name === 'TimeoutError') {
        lastErr.userMessage = 'Bağlantı yavaş, istek zaman aşımına uğradı.';
      } else if (!err.userMessage && !err.status) {
        lastErr.userMessage = 'Cihaz servisine ulaşılamadı, lütfen tekrar deneyin.';
      }
      if (attempt < retry) continue;
      throw lastErr;
    }
  }
  throw lastErr;
}

function _statusMessage(status) {
  if (status >= 500) return 'Sunucu hatası, lütfen tekrar deneyin.';
  if (status === 429) return 'Çok fazla istek, lütfen bekleyin.';
  if (status === 404) return 'İstenen kaynak bulunamadı.';
  if (status === 401 || status === 403) return 'Yetkilendirme hatası.';
  if (status === 400) return 'Geçersiz istek.';
  return 'Beklenmeyen bir hata oluştu.';
}

export async function fetchCategories() {
  return _request(`${API_BASE}/api/kategoriler`, { timeoutMs: 4000 });
}

export async function fetchQuestions(categorySlug) {
  return _request(`${API_BASE}/api/kategoriler/${categorySlug}/sorular`, {
    timeoutMs: 4000,
  });
}

/**
 * @param {object} payload
 * @param {string} payload.ageRange       — yas araligi kodu (ornek: "18-25")
 * @param {'M'|'F'|'O'} payload.gender    — cinsiyet kodu
 * @param {string} payload.categorySlug
 * @param {boolean} payload.isSensitiveFlow
 * @param {object} payload.answersPayload — { seed_id: 'Y'|'N' }
 * @param {string[]} payload.ingredientList
 * @returns {Promise<{qrCode: string, qrPayload: string}>}
 */
export async function submitSession({ ageRange, gender, categorySlug, isSensitiveFlow, answersPayload, ingredientList }) {
  const data = await _request(`${API_BASE}/api/oturum/gonder`, {
    method: 'POST',
    body: {
      yas_araligi_kod:         ageRange,
      cinsiyet_kod:            gender,
      kategori_slug:           categorySlug,
      hassas_akis:             isSensitiveFlow,
      cevaplar:                answersPayload,
      onerilen_etken_maddeler: ingredientList,
    },
    timeoutMs: 5000,
    retry: 1,
  });
  return { qrCode: data.qr_kodu, qrPayload: data.qr_payload || data.qr_kodu };
}

export async function fetchActiveCampaigns() {
  return _request(`${API_BASE}/api/reklamlar/aktif`, { timeoutMs: 4000 });
}

export async function logAdImpression({ campaignId, shownAt, durationMs }) {
  try {
    await _request(`${API_BASE}/api/reklam-gosterim`, {
      method: 'POST',
      body: {
        reklam_id:         campaignId,
        gosterilme_tarihi: shownAt,
        sure_ms:           durationMs,
      },
      timeoutMs: 3000,
    });
  } catch (err) {
    console.warn('[reklamGosterim] kayit basarisiz:', err?.userMessage || err?.message);
  }
}
