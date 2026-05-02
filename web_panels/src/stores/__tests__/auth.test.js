/**
 * Auth store testleri — Pinia ile JWT durumu yönetimi.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useAuthStore } from '../auth';

// api.js mock
vi.mock('../../services/api', () => ({
  login: vi.fn(),
}));

import { login as mockLogin } from '../../services/api';

// localStorage mock
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: (key) => store[key] ?? null,
    setItem: (key, value) => { store[key] = String(value); },
    removeItem: (key) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();

vi.stubGlobal('localStorage', localStorageMock);

describe('useAuthStore', () => {
  beforeEach(() => {
    localStorageMock.clear();
    setActivePinia(createPinia());
  });

  it('başlangıçta boş token ile yüklenir', () => {
    const store = useAuthStore();
    expect(store.accessToken).toBe('');
    expect(store.isAuthenticated).toBe(false);
  });

  it('localStorage\'da token varsa yükler', () => {
    localStorageMock.setItem('eisa_access', 'existing-token');
    localStorageMock.setItem('eisa_role', 'superadmin');
    const store = useAuthStore();
    expect(store.accessToken).toBe('existing-token');
    expect(store.role).toBe('superadmin');
    expect(store.isAuthenticated).toBe(true);
  });

  it('login başarılı olduğunda token\'ları saklar', async () => {
    mockLogin.mockResolvedValueOnce({
      access: 'acc-token',
      refresh: 'ref-token',
      role: 'superadmin',
    });

    const store = useAuthStore();
    await store.login('admin', 'password');

    expect(store.accessToken).toBe('acc-token');
    expect(store.refreshToken).toBe('ref-token');
    expect(store.role).toBe('superadmin');
    expect(localStorageMock.getItem('eisa_access')).toBe('acc-token');
    expect(store.isAuthenticated).toBe(true);
  });

  it('logout token\'ları temizler', async () => {
    mockLogin.mockResolvedValueOnce({ access: 'a', refresh: 'r', role: 'pharmacist' });
    const store = useAuthStore();
    await store.login('u', 'p');
    store.logout();

    expect(store.accessToken).toBe('');
    expect(store.refreshToken).toBe('');
    expect(store.role).toBe('');
    expect(store.isAuthenticated).toBe(false);
    expect(localStorageMock.getItem('eisa_access')).toBeNull();
  });

  it('pharmacist rolüyle login', async () => {
    mockLogin.mockResolvedValueOnce({ access: 't', refresh: 'r', role: 'pharmacist' });
    const store = useAuthStore();
    await store.login('eczaci', 'pass');
    expect(store.role).toBe('pharmacist');
  });
});
