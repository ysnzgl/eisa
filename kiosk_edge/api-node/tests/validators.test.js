import { describe, it, expect } from 'vitest';
import {
  QR_RE,
  oturumGonderSchema,
  reklamGosterimSchema,
} from '../src/validators.js';

describe('QR_RE', () => {
  it('valid kodlari kabul eder', () => {
    expect(QR_RE.test('ABC12345')).toBe(true);
    expect(QR_RE.test('ABCDEF12345')).toBe(true);
  });
  it('kisa veya gecersiz kodlari reddeder', () => {
    expect(QR_RE.test('AB12')).toBe(false);
    expect(QR_RE.test('ab123456')).toBe(false); // kucuk harf
    expect(QR_RE.test('!!invalid')).toBe(false);
  });
});

describe('oturumGonderSchema', () => {
  const base = {
    yas_araligi_kod: '26-35',
    cinsiyet_kod: 'M',
    kategori_slug: 'enerji',
  };

  it('minimal gecerli payload', () => {
    const r = oturumGonderSchema.safeParse(base);
    expect(r.success).toBe(true);
    expect(r.data.hassas_akis).toBe(false);
    expect(r.data.onerilen_etken_maddeler).toEqual([]);
  });

  it('gecersiz yas araligini reddeder', () => {
    const r = oturumGonderSchema.safeParse({ ...base, yas_araligi_kod: '99-200' });
    expect(r.success).toBe(false);
  });

  it('gecersiz cinsiyet kodunu reddeder', () => {
    const r = oturumGonderSchema.safeParse({ ...base, cinsiyet_kod: 'X' });
    expect(r.success).toBe(false);
  });

  it('51 bileseni reddeder', () => {
    const r = oturumGonderSchema.safeParse({
      ...base,
      onerilen_etken_maddeler: Array.from({ length: 51 }, (_, i) => `ing_${i}`),
    });
    expect(r.success).toBe(false);
  });

  it('gecersiz qr formatini reddeder', () => {
    const r = oturumGonderSchema.safeParse({ ...base, qr_kodu: '!!!' });
    expect(r.success).toBe(false);
  });
});

describe('reklamGosterimSchema', () => {
  it('gecerli payload', () => {
    const r = reklamGosterimSchema.safeParse({
      reklam_id: 1,
      gosterilme_tarihi: new Date().toISOString(),
      sure_ms: 5000,
    });
    expect(r.success).toBe(true);
  });
  it('reklam_id < 1 reddedilir', () => {
    const r = reklamGosterimSchema.safeParse({
      reklam_id: 0,
      gosterilme_tarihi: 'now',
    });
    expect(r.success).toBe(false);
  });
  it('sure_ms ust sinir', () => {
    const r = reklamGosterimSchema.safeParse({
      reklam_id: 1,
      gosterilme_tarihi: 'now',
      sure_ms: 24 * 60 * 60 * 1000 + 1,
    });
    expect(r.success).toBe(false);
  });
});
