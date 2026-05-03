import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || 'https://api.e-isa.local';

export const http = axios.create({ baseURL: API_BASE });

// Her istekte JWT access token başlığını ekle
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('eisa_access');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export async function login(username, password) {
  const { data } = await http.post('/api/auth/token/', { username, password });
  // access token'ı geçici olarak hemen ayarla; profil çağrısı bu token'ı kullanır.
  localStorage.setItem('eisa_access', data.access);
  let role = 'pharmacist';
  let pharmacyId = null;
  let userId = null;
  try {
    const me = await http.get('/api/users/me/');
    role = me.data?.role || role;
    pharmacyId = me.data?.pharmacy ?? null;
    userId = me.data?.id ?? null;
  } catch {
    // Profil alınamazsa rol fallback'iyle devam et.
  }
  return { access: data.access, refresh: data.refresh, role, pharmacyId, userId };
}
