import { http } from './api';

export async function getSirketProfili() {
  const { data } = await http.get('/api/sirket/profil/');
  return data;
}

export async function updateSirketProfili(payload) {
  const { data } = await http.put('/api/sirket/profil/', payload);
  return data;
}

export async function createBankaHesabi(payload) {
  const { data } = await http.post('/api/sirket/banka-hesaplari/', payload);
  return data;
}

export async function updateBankaHesabi(id, payload) {
  const { data } = await http.patch(`/api/sirket/banka-hesaplari/${id}/`, payload);
  return data;
}

export async function deleteBankaHesabi(id) {
  await http.delete(`/api/sirket/banka-hesaplari/${id}/`);
}
