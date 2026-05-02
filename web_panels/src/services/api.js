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
  // Rol bilgisi backend'den döndürülecek; şimdilik decode placeholder.
  return { access: data.access, refresh: data.refresh, role: data.role || 'pharmacist' };
}
