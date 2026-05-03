import { describe, it, expect } from 'vitest';
import {
  encodeQrCode,
  decodeQrCode,
  packBits,
  unpackBits,
  fromBase36,
  toBase36Padded,
  QR_BITPACK_RE,
  __internals,
} from '../src/qrBitpack.js';

const sample = {
  pharmacyId: 12345, // < 32768
  kioskId: 7,        // < 16
  categoryId: 100,   // < 128
  qaCombo: 42,       // < 64
  productId: 333,    // < 512
};

describe('qrBitpack — bit dağılımı', () => {
  it('toplam 41 bit', () => {
    expect(__internals.TOTAL_BITS).toBe(41n);
  });
  it('shift offsetleri doğru', () => {
    expect(__internals.SHIFTS.SHIFT_PRODUCT).toBe(0n);
    expect(__internals.SHIFTS.SHIFT_QA).toBe(9n);
    expect(__internals.SHIFTS.SHIFT_CATEGORY).toBe(15n);
    expect(__internals.SHIFTS.SHIFT_KIOSK).toBe(22n);
    expect(__internals.SHIFTS.SHIFT_PHARMACY).toBe(26n);
  });
});

describe('encodeQrCode / decodeQrCode', () => {
  it('round-trip orijinal veriyi korur', () => {
    const code = encodeQrCode(sample);
    expect(code).toMatch(QR_BITPACK_RE);
    expect(code).toHaveLength(8);
    expect(decodeQrCode(code)).toEqual(sample);
  });

  it('tüm alanlar maksimumdayken doğru paketlenir', () => {
    const max = {
      pharmacyId: 32767,
      kioskId: 15,
      categoryId: 127,
      qaCombo: 63,
      productId: 511,
    };
    const code = encodeQrCode(max);
    expect(code).toHaveLength(8);
    expect(decodeQrCode(code)).toEqual(max);
  });

  it('tüm alanlar sıfırken 8 karakter padding yapar', () => {
    const zero = { pharmacyId: 0, kioskId: 0, categoryId: 0, qaCombo: 0, productId: 0 };
    expect(encodeQrCode(zero)).toBe('00000000');
    expect(decodeQrCode('00000000')).toEqual(zero);
  });

  it('alanlar arası bit çakışması yoktur (izolasyon testi)', () => {
    // Her alanı sırayla yalnız maks değere çekip diğerlerinin 0 kaldığını doğrula
    const fields = ['pharmacyId', 'kioskId', 'categoryId', 'qaCombo', 'productId'];
    const maxes  = { pharmacyId: 32767, kioskId: 15, categoryId: 127, qaCombo: 63, productId: 511 };
    for (const f of fields) {
      const data = { pharmacyId: 0, kioskId: 0, categoryId: 0, qaCombo: 0, productId: 0, [f]: maxes[f] };
      const out = decodeQrCode(encodeQrCode(data));
      expect(out).toEqual(data);
    }
  });
});

describe('hata durumları', () => {
  it('aralık dışı değer reddedilir', () => {
    expect(() => encodeQrCode({ ...sample, pharmacyId: 32768 })).toThrow(/aralık dışı/);
    expect(() => encodeQrCode({ ...sample, kioskId: 16 })).toThrow(/aralık dışı/);
    expect(() => encodeQrCode({ ...sample, categoryId: -1 })).toThrow(/aralık dışı/);
  });
  it('geçersiz kod formatı reddedilir', () => {
    expect(() => decodeQrCode('abc')).toThrow();
    expect(() => decodeQrCode('lowercas')).toThrow();
    expect(() => decodeQrCode('!!@@##$$')).toThrow();
  });
});

describe('düşük seviye yardımcılar', () => {
  it('packBits 41-bit BigInt üretir', () => {
    const packed = packBits(sample);
    expect(typeof packed).toBe('bigint');
    expect(packed).toBeLessThanOrEqual(__internals.MAX_PACKED);
    expect(unpackBits(packed)).toEqual(sample);
  });
  it('toBase36Padded ↔ fromBase36 simetrisi', () => {
    const packed = packBits(sample);
    expect(fromBase36(toBase36Padded(packed))).toBe(packed);
  });
});
