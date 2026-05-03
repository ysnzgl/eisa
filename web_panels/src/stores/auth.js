import { defineStore } from 'pinia';
import { login as apiLogin, logout as apiLogout } from '../services/api';

// Panel kimlik durumu (SEC-002).
// JWT access/refresh token'ları artık httpOnly çerezlerde tutulur; localStorage
// yalnızca XSS riski olmayan UI ipuçlarını (rol, pharmacyId, userId) saklar.
export const useAuthStore = defineStore('auth', {
  state: () => ({
    role: localStorage.getItem('eisa_role') || '',
    pharmacyId: Number(localStorage.getItem('eisa_pharmacy_id') || '') || null,
    userId: Number(localStorage.getItem('eisa_user_id') || '') || null,
  }),
  getters: {
    // Rol set edilmişse kullanıcı login olmuş kabul edilir; gerçek doğrulama
    // backend tarafından her API çağrısında çerez ile yapılır.
    isAuthenticated: (s) => !!s.role,
  },
  actions: {
    async login(username, password) {
      const { role, pharmacyId, userId } = await apiLogin(username, password);
      this.role = role;
      this.pharmacyId = pharmacyId ?? null;
      this.userId = userId ?? null;
      if (role) localStorage.setItem('eisa_role', role);
      else localStorage.removeItem('eisa_role');
      if (pharmacyId != null) localStorage.setItem('eisa_pharmacy_id', String(pharmacyId));
      else localStorage.removeItem('eisa_pharmacy_id');
      if (userId != null) localStorage.setItem('eisa_user_id', String(userId));
      else localStorage.removeItem('eisa_user_id');
    },
    async logout() {
      await apiLogout();
      this.role = '';
      this.pharmacyId = null;
      this.userId = null;
      ['eisa_role', 'eisa_pharmacy_id', 'eisa_user_id'].forEach((k) =>
        localStorage.removeItem(k),
      );
      // Eski şemadan kalan token kalıntılarını da temizle.
      ['eisa_access', 'eisa_refresh'].forEach((k) => localStorage.removeItem(k));
    },
  },
});
