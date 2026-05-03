import { defineStore } from 'pinia';
import { login as apiLogin } from '../services/api';

// JWT tabanlı kimlik durumu (paneller için).
export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: localStorage.getItem('eisa_access') || '',
    refreshToken: localStorage.getItem('eisa_refresh') || '',
    role: localStorage.getItem('eisa_role') || '',
    pharmacyId: Number(localStorage.getItem('eisa_pharmacy_id') || '') || null,
    userId: Number(localStorage.getItem('eisa_user_id') || '') || null,
  }),
  getters: {
    isAuthenticated: (s) => !!s.accessToken
  },
  actions: {
    async login(username, password) {
      const { access, refresh, role, pharmacyId, userId } = await apiLogin(username, password);
      this.accessToken = access;
      this.refreshToken = refresh;
      this.role = role;
      this.pharmacyId = pharmacyId ?? null;
      this.userId = userId ?? null;
      localStorage.setItem('eisa_access', access);
      localStorage.setItem('eisa_refresh', refresh);
      localStorage.setItem('eisa_role', role);
      if (pharmacyId != null) localStorage.setItem('eisa_pharmacy_id', String(pharmacyId));
      else localStorage.removeItem('eisa_pharmacy_id');
      if (userId != null) localStorage.setItem('eisa_user_id', String(userId));
      else localStorage.removeItem('eisa_user_id');
    },
    logout() {
      this.accessToken = '';
      this.refreshToken = '';
      this.role = '';
      this.pharmacyId = null;
      this.userId = null;
      [
        'eisa_access',
        'eisa_refresh',
        'eisa_role',
        'eisa_pharmacy_id',
        'eisa_user_id',
      ].forEach((k) => localStorage.removeItem(k));
    }
  }
});
