/**
 * kiosk_edge UI — merkezi API istemcisi
 * Tüm fetch çağrıları burada, bileşenler sadece bu fonksiyonları kullanır.
 */

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8765';

function _normalizeMediaUrl(url) {
  if (!url || typeof url !== 'string') return url;
  if (url.startsWith('/')) return `${API_BASE}${url}`;
  return url;
}

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

export async function fetchDanismaCategories() {
  return _request(`${API_BASE}/api/danisma-kategorileri`, { timeoutMs: 4000 });
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
 * @param {string} [payload.oturumTipi]   — 'SIKAYET' veya 'OZEL_DANISMANLIK' (varsayilan: SIKAYET)
 * @param {string} [payload.categorySlug] — sikayet icin kategori slug
 * @param {string} [payload.danismaKategorisiSlug] — ozel danismanlik icin danisma kategorisi slug
 * @param {boolean} payload.isSensitiveFlow
 * @param {object} payload.answersPayload — { seed_id: 'Y'|'N' }
 * @param {string[]} payload.ingredientList
 * @param {boolean} [payload.completed]  — false ise 10sn etkilesimsizlik ile terk edilmis oturum
 * @returns {Promise<{qrCode: string, qrPayload: string}>}
 */
export async function submitSession({ ageRange, gender, oturumTipi, categorySlug, danismaKategorisiSlug, isSensitiveFlow, answersPayload, ingredientList, completed = true, sessionId = null }) {
  // Backend'e gönderirken tamamlanma durumunu bildir
  const data = await _request(`${API_BASE}/api/oturum/gonder`, {
    method: 'POST',
    body: {
      yas_araligi_kod:         ageRange,
      cinsiyet_kod:            gender,
      oturum_tipi:             oturumTipi || 'SIKAYET',
      kategori_slug:           categorySlug || null,
      danisma_kategorisi_slug: danismaKategorisiSlug || null,
      hassas_akis:             isSensitiveFlow,
      cevaplar:                answersPayload,
      onerilen_etken_maddeler: ingredientList,
      tamamlandi:              completed,
      // UI'dan gelen kararlı sessionId — sunucunun her istekte yeni UUID üretmesini önler
      ...(sessionId ? { idempotency_anahtari: sessionId } : {}),
    },
    timeoutMs: 5000,
    // retry: 0 — idempotency outbox tarafından garanti edilir;
    // retry, Node'un her seferinde farklı UUID üretmesine yol açar → çift kayıt
    retry: 0,
  });
  return { qrCode: data.qr_kodu, qrPayload: data.qr_payload || data.qr_kodu };
}

// ── WiFi API ────────────────────────────────────────────────────────────────

/**
 * @returns {Promise<{connected: boolean, ssid: string|null}>}
 */
export async function fetchWifiStatus() {
  return _request(`${API_BASE}/api/wifi/status`, { timeoutMs: 8000 });
}

/**
 * @returns {Promise<Array<{ssid: string, signal: number, secured: boolean}>>}
 */
export async function fetchWifiNetworks() {
  return _request(`${API_BASE}/api/wifi/scan`, { timeoutMs: 25000 });
}

/**
 * @param {string} ssid
 * @param {string} [password]
 * @returns {Promise<{success: boolean, message: string}>}
 */
export async function connectToWifi(ssid, password) {
  return _request(`${API_BASE}/api/wifi/connect`, {
    method: 'POST',
    body: { ssid, ...(password ? { password } : {}) },
    timeoutMs: 45000,
  });
}

export async function fetchActiveCampaigns() {
  const list = await _request(`${API_BASE}/api/reklamlar/aktif`, { timeoutMs: 4000 });
  return (list || []).map((item) => ({
    ...item,
    media_url: _normalizeMediaUrl(item.media_url),
    remote_media_url: _normalizeMediaUrl(item.remote_media_url),
  }));
}

/**
 * Bugünün belirtilen saatine ait playlist'i döner.
 * @param {number} [hour]  — verilmezse api-node kendi saatini kullanır
 * @returns {Promise<{version:number, target_date:string, target_hour:number,
 *                    loop_duration_seconds:number, is_fallback:boolean, items:object[]}>}
 */
export async function fetchCurrentPlaylist(hour) {
  const query = hour !== undefined ? `?hour=${hour}` : '';
  const pl = await _request(`${API_BASE}/api/playlist/current${query}`, { timeoutMs: 4000 });
  return {
    ...pl,
    items: (pl?.items || []).map((item) => ({
      ...item,
      media_url: _normalizeMediaUrl(item.media_url),
      remote_media_url: _normalizeMediaUrl(item.remote_media_url),
    })),
  };
}

export async function logAdImpression({ assetId, assetType, shownAt, durationMs }) {
  try {
    await _request(`${API_BASE}/api/reklam-gosterim`, {
      method: 'POST',
      body: {
        asset_id:       assetId,
        asset_type:     assetType,
        played_at:      shownAt,
        duration_played: Math.round((durationMs || 0) / 1000),
      },
      timeoutMs: 3000,
    });
  } catch (err) {
    console.warn('[reklamGosterim] kayit basarisiz:', err?.userMessage || err?.message);
  }
}
