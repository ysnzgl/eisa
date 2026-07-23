/**
 * API servis katmanı testleri.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';

vi.mock('axios', async () => {
  const mockHttp = {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  };
  return {
    default: {
      create: vi.fn(() => mockHttp),
    },
    __mockHttp: mockHttp,
  };
});

import { login } from '../../services/api';

describe('login()', () => {
  it('doğru endpoint\'e POST atar ve user bilgilerini döner', async () => {
    const { default: axiosMock } = await import('axios');
    const httpMock = axiosMock.create();
    // Backend: { id, username, rol, eczane } döner (JWT cookie'de)
    httpMock.post.mockResolvedValueOnce({
      data: { id: 1, username: 'admin', rol: 'superadmin', eczane: null }
    });

    const result = await login('admin', 'pass');
    // login() geriye { role, pharmacyId, userId } eşlemesi döner
    expect(result.role).toBe('superadmin');
    expect(result.userId).toBe(1);
    expect(result.pharmacyId).toBeNull();
  });

  it('role yoksa "pharmacist" varsayılan döner', async () => {
    const { default: axiosMock } = await import('axios');
    const httpMock = axiosMock.create();
    httpMock.post.mockResolvedValueOnce({
      data: { access: 'a', refresh: 'r' }
    });

    const result = await login('u', 'p');
    expect(result.role).toBe('pharmacist');
  });
});
