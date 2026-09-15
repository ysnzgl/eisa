import { describe, expect, it } from 'vitest';

import { normalizeIdleIcon } from '../lib/idleIcon.js';

describe('AdPromo idle içerik ikonu', () => {
  it('kategori ikonunun tam Font Awesome sınıf biçimini normalize eder', () => {
    expect(normalizeIdleIcon('fa-solid fa-bolt')).toBe('fa-bolt');
    expect(normalizeIdleIcon('fas fa-seedling')).toBe('fa-seedling');
  });

  it('kategori ikonu olmayan içerikte görünür fallback ikon üretir', () => {
    expect(normalizeIdleIcon('')).toBe('fa-heart-pulse');
    expect(normalizeIdleIcon(null)).toBe('fa-heart-pulse');
  });
});
