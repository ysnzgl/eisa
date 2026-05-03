import { describe, it, expect } from 'vitest';
import {
  QR_RE,
  sessionSubmitSchema,
  adImpressionSchema,
} from '../src/validators.js';

describe('QR_RE', () => {
  it('valid kodları kabul eder', () => {
    expect(QR_RE.test('ABC12345')).toBe(true);
    expect(QR_RE.test('a1b2c3:d4-e5')).toBe(true);
  });
  it('kısa veya geçersiz kodları reddeder', () => {
    expect(QR_RE.test('AB12')).toBe(false);
    expect(QR_RE.test('!!invalid!!')).toBe(false);
  });
});

describe('sessionSubmitSchema', () => {
  const base = {
    age_range: '26-35',
    gender: 'M',
    category_slug: 'energy',
  };

  it('minimal geçerli payload', () => {
    const r = sessionSubmitSchema.safeParse(base);
    expect(r.success).toBe(true);
    expect(r.data.is_sensitive_flow).toBe(false);
    expect(r.data.suggested_ingredients).toEqual([]);
  });

  it('geçersiz yaş aralığını reddeder', () => {
    const r = sessionSubmitSchema.safeParse({ ...base, age_range: '99-200' });
    expect(r.success).toBe(false);
  });

  it('geçersiz cinsiyeti reddeder', () => {
    const r = sessionSubmitSchema.safeParse({ ...base, gender: 'X' });
    expect(r.success).toBe(false);
  });

  it('51 bileşeni reddeder', () => {
    const r = sessionSubmitSchema.safeParse({
      ...base,
      suggested_ingredients: Array.from({ length: 51 }, (_, i) => `ing_${i}`),
    });
    expect(r.success).toBe(false);
  });

  it('geçersiz qr formatını reddeder', () => {
    const r = sessionSubmitSchema.safeParse({ ...base, qr_code: '!!!' });
    expect(r.success).toBe(false);
  });
});

describe('adImpressionSchema', () => {
  it('geçerli payload', () => {
    const r = adImpressionSchema.safeParse({
      campaign_id: 1,
      shown_at: new Date().toISOString(),
      duration_ms: 5000,
    });
    expect(r.success).toBe(true);
  });
  it('campaign_id < 1 reddedilir', () => {
    const r = adImpressionSchema.safeParse({
      campaign_id: 0,
      shown_at: 'now',
    });
    expect(r.success).toBe(false);
  });
  it('duration_ms üst sınır', () => {
    const r = adImpressionSchema.safeParse({
      campaign_id: 1,
      shown_at: 'now',
      duration_ms: 24 * 60 * 60 * 1000 + 1,
    });
    expect(r.success).toBe(false);
  });
});
