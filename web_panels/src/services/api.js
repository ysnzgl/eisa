import axios from 'axios';
import { useToastStore } from '../stores/toast';

const API_BASE = import.meta.env.VITE_API_BASE || 'https://api.e-isa.local';

// httpOnly JWT çerezleri otomatik gönderilsin diye `withCredentials` (SEC-002).
export const http = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
});

// Belirli endpoint'ler için varsayılan toast bastırılabilsin (örn. login formu
// kendi hata mesajını göstermek istiyorsa `{ silent: true }` flag'i ile çağırır).
function _isSilent(config) {
  return config?.__silent === true;
}

// Eşzamanlı istekler tek bir refresh promise paylaşır.
let _refreshPromise = null;

async function _refreshAccess() {
  if (!_refreshPromise) {
    _refreshPromise = http
      .post('/api/auth/token/refresh/', null, { __silent: true })
      .finally(() => {
        _refreshPromise = null;
      });
  }
  return _refreshPromise;
}

function _humanError(error) {
  const status = error.response?.status;
  const data = error.response?.data;
  if (data?.detail) return String(data.detail);
  // DRF field error formatı: { field: ["mesaj"] }
  if (data && typeof data === 'object') {
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
      try {
        useToastStore().error(_humanError(error));
      } catch {
        // Pinia henüz mount edilmemişse (ör. uygulama açılırken) sessizce geç.
      }
    }
    return Promise.reject(error);
  },
);

export async function login(username, password) {
  // Backend httpOnly çerezleri set eder; yanıt gövdesinde yalnızca profil var.
  // Login formu kendi hatasını gösterdiği için interceptor toast'ını bastırıyoruz.
  const { data } = await http.post(
    '/api/auth/token/',
    { username, password },
    { __silent: true },
  );
  return {
    role: data?.role || 'pharmacist',
    pharmacyId: data?.pharmacy ?? null,
    userId: data?.id ?? null,
  };
}

export async function logout() {
  try {
    await http.post('/api/auth/logout/');
  } catch {
    // Çerezler istemci tarafında her durumda temizlenecek.
  }
}

export async function fetchProfile() {
  const { data } = await http.get('/api/users/me/');
  return {
    role: data?.role || 'pharmacist',
    pharmacyId: data?.pharmacy ?? null,
    userId: data?.id ?? null,
  };
}
