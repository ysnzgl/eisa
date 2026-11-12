import { http } from './api';

export const listPhysicalDevices = (params = {}) => http.get('/api/pharmacies/cihazlar/', { params });
export const createPhysicalDevice = data => http.post('/api/pharmacies/cihazlar/', data);
export const updatePhysicalDevice = (id, data) => http.patch(`/api/pharmacies/cihazlar/${id}/`, data);
export const matchPhysicalDevice = (id, kiosk) => http.post(`/api/pharmacies/cihazlar/${id}/eslestir/`, { kiosk });
