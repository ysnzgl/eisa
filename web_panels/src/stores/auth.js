import { defineStore } from 'pinia';
import { login as apiLogin } from '../services/api';

// JWT tabanlı kimlik durumu (paneller için).
export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: localStorage.getItem('eisa_access') || '',
    refreshToken: localStorage.getItem('eisa_refresh') || '',
    role: localStorage.getItem('eisa_role') || ''
  }),
  getters: {
    isAuthenticated: (s) => !!s.accessToken
  },
  actions: {
    async login(username, password) {
      const { access, refresh, role } = await apiLogin(username, password);
      this.accessToken = access;
      this.refreshToken = refresh;
      this.role = role;
      localStorage.setItem('eisa_access', access);
      localStorage.setItem('eisa_refresh', refresh);
      localStorage.setItem('eisa_role', role);
    },
    logout() {
      this.accessToken = this.refreshToken = this.role = '';
      ['eisa_access', 'eisa_refresh', 'eisa_role'].forEach((k) => localStorage.removeItem(k));
    }
  }
});
