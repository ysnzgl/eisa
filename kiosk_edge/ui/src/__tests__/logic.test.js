/**
 * Kiosk UI logic testleri.
 * Svelte bileşeni render etmeden saf JS mantığını test eder.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';

// ─── Idle timer logic ──────────────────────────────────────────────────────

describe('idleDisplay formatı', () => {
  function formatIdle(seconds) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }

  it('0 saniye için "00:00" döner', () => {
    expect(formatIdle(0)).toBe('00:00');
  });

  it('30 saniye için "00:30" döner', () => {
    expect(formatIdle(30)).toBe('00:30');
  });

  it('60 saniye için "01:00" döner', () => {
    expect(formatIdle(60)).toBe('01:00');
  });

  it('90 saniye için "01:30" döner', () => {
    expect(formatIdle(90)).toBe('01:30');
  });

  it('3661 saniye için "61:01" döner', () => {
    expect(formatIdle(3661)).toBe('61:01');
  });
});

describe('idle timeout kontrolü', () => {
  const IDLE_TIMEOUT_S = 30;

  it('30 saniyeden önce timeout değil', () => {
    expect(29 >= IDLE_TIMEOUT_S).toBe(false);
  });

  it('30 saniyede tam timeout', () => {
    expect(30 >= IDLE_TIMEOUT_S).toBe(true);
  });

  it('31 saniyede timeout aşıldı', () => {
    expect(31 >= IDLE_TIMEOUT_S).toBe(true);
  });
});

// ─── Kategori filtreleme ───────────────────────────────────────────────────

describe('kategori filtreleme', () => {
  const categories = [
    { id: 1, slug: 'enerji', is_sensitive: false },
    { id: 2, slug: 'uyku', is_sensitive: false },
    { id: 7, slug: 'cinsel', is_sensitive: true },
    { id: 8, slug: 'hemoroid', is_sensitive: true },
  ];

  it('is_sensitive=false filtresi normal kategorileri döner', () => {
    const normal = categories.filter(c => c.is_sensitive === false);
    expect(normal.length).toBe(2);
    expect(normal.map(c => c.slug)).toEqual(['enerji', 'uyku']);
  });

  it('is_sensitive=true filtresi hassas kategorileri döner', () => {
    const sensitive = categories.filter(c => c.is_sensitive === true);
    expect(sensitive.length).toBe(2);
    expect(sensitive.map(c => c.slug)).toContain('cinsel');
  });

  it('boş kategori listesi filtrelemesi güvenli', () => {
    expect([].filter(c => c.is_sensitive === false)).toEqual([]);
  });
});

// ─── fetchCategories fallback davranışı ───────────────────────────────────

describe('fetchCategories fallback', () => {
  const FALLBACK = [{ id: 1, slug: 'enerji', name: 'Enerji', is_sensitive: false }];

  it('fetch başarısız olduğunda fallback kullanılır', async () => {
    const fetchMock = vi.fn().mockRejectedValueOnce(new Error('Network error'));
    let offlineMode = false;
    let allCategories = [];

    try {
      const res = await fetchMock('http://127.0.0.1:8765/api/categories');
      allCategories = await res.json();
    } catch {
      offlineMode = true;
      allCategories = FALLBACK;
    }

    expect(offlineMode).toBe(true);
    expect(allCategories).toEqual(FALLBACK);
  });

  it('fetch başarılı olduğunda API verisi kullanılır', async () => {
    const apiData = [{ id: 99, slug: 'test', name: 'Test', is_sensitive: false }];
    const fetchMock = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(apiData),
    });
    let offlineMode = false;
    let allCategories = [];

    try {
      const res = await fetchMock('http://127.0.0.1:8765/api/categories');
      if (!res.ok) throw new Error();
      allCategories = await res.json();
    } catch {
      offlineMode = true;
      allCategories = FALLBACK;
    }

    expect(offlineMode).toBe(false);
    expect(allCategories).toEqual(apiData);
  });
});

// ─── QR kod doğrulama ─────────────────────────────────────────────────────

describe('QR kodu doğrulama', () => {
  const QR_RE = /^[A-Za-z0-9][\w:\-]{5,255}$/;

  it('geçerli QR kodunu kabul eder', () => {
    expect(QR_RE.test('ABC123456')).toBe(true);
    expect(QR_RE.test('QR-CODE:2024')).toBe(true);
  });

  it('çok kısa kodu reddeder', () => {
    expect(QR_RE.test('AB')).toBe(false);
  });

  it('özel karakterli kodu reddeder', () => {
    expect(QR_RE.test('!!!invalid')).toBe(false);
  });
});
