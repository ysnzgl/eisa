import axios from 'axios';
import { toast } from 'vue-sonner';

// API base URL çözümleme önceliği:
//   1) Runtime config (window.__APP_CONFIG__.API_BASE_URL) — container ENV'den
//      `docker-entrypoint.sh` tarafından `/config.js` içine yazılır.
//   2) Build-time VITE_API_BASE (geliştirme/legacy).
//   3) Boş string → same-origin (dev'de Vite proxy, prod'da ingress aynı host).
const RUNTIME_BASE =
  typeof window !== 'undefined' && window.__APP_CONFIG__?.API_BASE_URL;
const API_BASE = RUNTIME_BASE || import.meta.env.VITE_API_BASE || '';

// httpOnly JWT çerezleri otomatik gönderilsin diye `withCredentials` (SEC-002).
export const http = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
});

// Response'daki X-Correlation-ID degerini yakalayalim; frontend logger'i bu
// degeri hata bildirimine ekliyor ve backend log akisiyla ayni ID kullanilir.
http.interceptors.response.use((response) => {
  const cid = response.headers?.['x-correlation-id'] || response.headers?.['X-Correlation-ID'];
  if (cid && typeof window !== 'undefined') {
    window.__EISA_LAST_CORRELATION_ID__ = String(cid).slice(0, 64);
  }
  return response;
});

// Belirli endpoint'ler için varsayılan toast bastırılabilsin (örn. login formu
// kendi hata mesajını göstermek istiyorsa `{ __silent: true }` flag'i ile çağırır).
function _isSilent(config) {
  return config?.__silent === true;
}

// Eşzamanlı istekler tek bir refresh promise paylaşır.
let _refreshPromise = null;

async function _refreshAccess() {
  if (!_refreshPromise) {
    // Refresh token httpOnly çerezde; body boş gidecek, backend cookie'den okur.
    _refreshPromise = http
      .post('/api/auth/token/refresh/', null, { __silent: true })
      .finally(() => {
        _refreshPromise = null;
      });
  }
  return _refreshPromise;
}

// Django password validator mesajlarını Türkçeye çevirir.
const PASSWORD_MSG_MAP = [
  [/too short/i,       'Parola çok kısa, en az 10 karakter olmalı.'],
  [/too common/i,      'Parola çok yaygın, daha özgün bir parola seçin.'],
  [/entirely numeric/i,'Parola yalnızca rakamlardan oluşamaz.'],
  [/similar.*user/i,   'Parola kullanıcı adına çok benziyor.'],
];

function _translatePassword(msg) {
  for (const [pattern, tr] of PASSWORD_MSG_MAP) {
    if (pattern.test(msg)) return tr;
  }
  return 'Parola uygun değil.';
}

function _humanError(error) {
  const status = error.response?.status;
  const data = error.response?.data;
  if (data?.detail) return String(data.detail);
  // DRF field error formatı: { field: ["mesaj"] }
  if (data && typeof data === 'object') {
    // Parola hataları Türkçeye çevrilir.
    if (Array.isArray(data.password) && data.password.length) {
      return _translatePassword(String(data.password[0]));
    }
    const first = Object.values(data).find((v) => Array.isArray(v) && v.length);
    if (first) return String(first[0]);
  }
  if (error.code === 'ECONNABORTED') return 'İstek zaman aşımına uğradı.';
  if (!error.response) return 'Sunucuya ulaşılamadı, ağ bağlantısını kontrol edin.';
  if (status >= 500) return 'Sunucu hatası, lütfen daha sonra tekrar deneyin.';
  if (status === 403) return 'Bu işlem için yetkiniz yok.';
  if (status === 404) return 'İstenen kaynak bulunamadı.';
  if (status === 429) return 'Çok fazla istek attınız, lütfen bekleyin.';
  if (status === 400) return 'Geçersiz istek.';
  return 'Beklenmeyen bir hata oluştu.';
}

// ERR-001: Tüm response'ları merkezi olarak yakala. 401 ise sessizce refresh
// dener; diğer hatalar kullanıcıya toast olarak gösterilir.
http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config || {};
    const status = error.response?.status;
    const url = original.url || '';
    const isAuthEndpoint =
      url.includes('/api/auth/token/') || url.includes('/api/auth/logout/');

    if (status === 401 && !original.__retry && !isAuthEndpoint) {
      original.__retry = true;
      try {
        await _refreshAccess();
        return http(original);
      } catch {
        // Refresh de başarısızsa: kullanıcıyı login'e yönlendirmek üst katmanın işi.
      }
    }

    if (!_isSilent(original)) {
      toast.error(_humanError(error));
    }
    return Promise.reject(error);
  },
);

export async function login(username, password) {
  // Backend httpOnly cookie set eder; body'de { id, username, rol, eczane } döner.
  // Login formu kendi hatasını gösterdiği için interceptor toast'ını bastırıyoruz.
  const { data } = await http.post(
    '/api/auth/token/',
    { username, password },
    { __silent: true },
  );
  return {
    role: data?.rol ?? 'pharmacist',
    pharmacyId: data?.eczane ?? null,
    userId: data?.id ?? null,
  };
}

export async function logout() {
  try {
    await http.post('/api/auth/logout/');
  } catch {
    // Sunucu ulaşılamazsa da yerel state temizlenir.
  }
}

export async function fetchProfile() {
  // GET /api/users/me/ → Kullanici schema: { id, username, rol, eczane }
  const { data } = await http.get('/api/users/me/');
  return {
    role: data?.rol ?? 'pharmacist',
    pharmacyId: data?.eczane ?? null,
    userId: data?.id ?? null,
  };
}
