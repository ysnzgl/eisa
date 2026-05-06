/**
 * Kullanıcı Yönetimi Servisi (Admin)
 *
 * Backend endpoint'leri (apps.users.urls):
 *   GET    /api/users/                          — liste
 *   POST   /api/users/                          — oluştur
 *   GET    /api/users/{id}/                     — detay
 *   PATCH  /api/users/{id}/                     — güncelle
 *   DELETE /api/users/{id}/                     — soft delete (is_active=false)
 *   POST   /api/users/{id}/reset-password/      — parola sıfırla
 *   POST   /api/users/{id}/activate/            — yeniden aktifleştir
 */
import { http } from './api';

export async function getUsers() {
  const { data } = await http.get('/api/users/');
  return Array.isArray(data) ? data : (data?.results ?? []);
}

export async function createUser(payload) {
  const { data } = await http.post('/api/users/', payload);
  return data;
}

export async function updateUser(id, payload) {
  const { data } = await http.patch(`/api/users/${id}/`, payload);
  return data;
}

export async function deactivateUser(id) {
  // Soft delete (is_active=false)
  await http.delete(`/api/users/${id}/`);
}

export async function activateUser(id) {
  const { data } = await http.post(`/api/users/${id}/activate/`);
  return data;
}

export async function resetPassword(id, password) {
  await http.post(`/api/users/${id}/reset-password/`, { password });
}
