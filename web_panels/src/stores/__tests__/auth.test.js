/**
 * Auth store testleri — httpOnly çerez tabanlı JWT (SEC-002).
 *
 * Token'lar artık çerezlerde saklanır; store yalnızca rol/pharmacyId/userId
 * gibi UI ipuçlarını localStorage'da tutar.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useAuthStore } from '../auth';

// api.js mock
vi.mock('../../services/api', () => ({
  login: vi.fn(),
  logout: vi.fn().mockResolvedValue(undefined),
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

  it('başlangıçta boş rol ile yüklenir ve isAuthenticated=false döner', () => {
    const store = useAuthStore();
    expect(store.role).toBe('');
    expect(store.isAuthenticated).toBe(false);
  });

  it("localStorage'da rol varsa yükler ve authenticated kabul edilir", () => {
    localStorageMock.setItem('eisa_role', 'superadmin');
    localStorageMock.setItem('eisa_pharmacy_id', '7');
    const store = useAuthStore();
    expect(store.role).toBe('superadmin');
    expect(store.pharmacyId).toBe(7);
    expect(store.isAuthenticated).toBe(true);
  });

  it('login başarılı olduğunda profil bilgilerini saklar (token YOK)', async () => {
    mockLogin.mockResolvedValueOnce({
      role: 'superadmin',
      pharmacyId: null,
      userId: 1,
    });

    const store = useAuthStore();
    await store.login('admin', 'password');

    expect(store.role).toBe('superadmin');
    expect(store.userId).toBe(1);
    expect(localStorageMock.getItem('eisa_role')).toBe('superadmin');
    // Token'lar artık localStorage'da SAKLANMAMALI (SEC-002).
    expect(localStorageMock.getItem('eisa_access')).toBeNull();
    expect(localStorageMock.getItem('eisa_refresh')).toBeNull();
    expect(store.isAuthenticated).toBe(true);
  });

  it("logout state ve localStorage'ı temizler", async () => {
    mockLogin.mockResolvedValueOnce({ role: 'pharmacist', pharmacyId: 3, userId: 2 });
    const store = useAuthStore();
    await store.login('u', 'p');
    await store.logout();

    expect(store.role).toBe('');
    expect(store.pharmacyId).toBeNull();
    expect(store.userId).toBeNull();
    expect(store.isAuthenticated).toBe(false);
    expect(localStorageMock.getItem('eisa_role')).toBeNull();
    expect(localStorageMock.getItem('eisa_pharmacy_id')).toBeNull();
  });

  it('pharmacist rolüyle login', async () => {
    mockLogin.mockResolvedValueOnce({ role: 'pharmacist', pharmacyId: 5, userId: 9 });
    const store = useAuthStore();
    await store.login('eczaci', 'pass');
    expect(store.role).toBe('pharmacist');
    expect(store.pharmacyId).toBe(5);
  });
});
