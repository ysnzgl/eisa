/**
 * QR Bit-Packing Codec (panel tarafı) — kiosk ile aynı algoritma.
 *
 * Muadil: kiosk_edge/api-node/src/qrBitpack.js
 *
 * Format: 5 integer alan → 41 bit BigInt → 8 karakter Base36 (UPPERCASE).
 * Tarayıcıda da çalışır; yalnızca BigInt kullanılır (Buffer/atob YOK).
 *
 *   ┌───────────────┬──────┬──────────┬─────────┬────────────────┐
 *   │ pharmacyId 15 │ k 4  │ cat   7  │ qa   6  │ productId   9  │
 *   └───────────────┴──────┴──────────┴─────────┴────────────────┘
 *      shift 26       22       15         9            0
 */

const BITS_PHARMACY = 15n;
const BITS_KIOSK    =  4n;
const BITS_CATEGORY =  7n;
const BITS_QA       =  6n;
const BITS_PRODUCT  =  9n;

const SHIFT_PRODUCT  = 0n;
const SHIFT_QA       = SHIFT_PRODUCT + BITS_PRODUCT;        // 9
const SHIFT_CATEGORY = SHIFT_QA      + BITS_QA;             // 15
const SHIFT_KIOSK    = SHIFT_CATEGORY + BITS_CATEGORY;      // 22
const SHIFT_PHARMACY = SHIFT_KIOSK   + BITS_KIOSK;          // 26

const MASK_PHARMACY = (1n << BITS_PHARMACY) - 1n;
const MASK_KIOSK    = (1n << BITS_KIOSK)    - 1n;
const MASK_CATEGORY = (1n << BITS_CATEGORY) - 1n;
const MASK_QA       = (1n << BITS_QA)       - 1n;
const MASK_PRODUCT  = (1n << BITS_PRODUCT)  - 1n;

const TOTAL_BITS = BITS_PHARMACY + BITS_KIOSK + BITS_CATEGORY + BITS_QA + BITS_PRODUCT;
const MAX_PACKED = (1n << TOTAL_BITS) - 1n;

export const QR_BITPACK_LENGTH = 8;
export const QR_BITPACK_RE = /^[0-9A-Z]{8}$/;

function assertRange(name, value, mask) {
  if (value === null || value === undefined) {
    throw new RangeError(`${name} zorunlu`);
  }
  const v = BigInt(value);
  if (v < 0n || v > mask) {
    throw new RangeError(`${name} aralık dışı (0..${mask})`);
  }
  return v;
}

/** 5 alanı 41-bit BigInt'e paketler (<<, |). */
export function packBits(f) {
  const p  = assertRange('pharmacyId', f.pharmacyId, MASK_PHARMACY);
  const k  = assertRange('kioskId',    f.kioskId,    MASK_KIOSK);
  const c  = assertRange('categoryId', f.categoryId, MASK_CATEGORY);
  const q  = assertRange('qaCombo',    f.qaCombo,    MASK_QA);
  const pr = assertRange('productId',  f.productId,  MASK_PRODUCT);
  return (p  << SHIFT_PHARMACY)
       | (k  << SHIFT_KIOSK)
       | (c  << SHIFT_CATEGORY)
       | (q  << SHIFT_QA)
       | (pr << SHIFT_PRODUCT);
}

/** 41-bit BigInt → sabit 8 karakter UPPERCASE Base36 (sol '0' padding). */
export function toBase36Padded(packed) {
  if (packed < 0n || packed > MAX_PACKED) {
    throw new RangeError('packed değer 41-bit aralığını aşıyor');
  }
  const s = packed.toString(36).toUpperCase();
  return s.length >= QR_BITPACK_LENGTH ? s : '0'.repeat(QR_BITPACK_LENGTH - s.length) + s;
}

/** Encoder. */
export function encodeQrCode(fields) {
  return toBase36Padded(packBits(fields));
}

/** 8 karakter Base36 → BigInt. */
export function fromBase36(code) {
  if (typeof code !== 'string' || !QR_BITPACK_RE.test(code)) {
    throw new Error('Geçersiz QR kod formatı (8 karakter, 0-9 A-Z bekleniyor)');
  }
  let n = 0n;
  for (const ch of code) {
    const d = parseInt(ch, 36);
    if (Number.isNaN(d)) throw new Error('Geçersiz Base36 karakteri');
    n = n * 36n + BigInt(d);
  }
  if (n > MAX_PACKED) {
    throw new RangeError('Çözülen değer 41-bit aralığını aşıyor');
  }
  return n;
}

/** Bit-shift (>>) + maskeleme (&) ile alanları ayrıştırır. */
export function unpackBits(packed) {
  return {
    pharmacyId: Number((packed >> SHIFT_PHARMACY) & MASK_PHARMACY),
    kioskId:    Number((packed >> SHIFT_KIOSK)    & MASK_KIOSK),
    categoryId: Number((packed >> SHIFT_CATEGORY) & MASK_CATEGORY),
    qaCombo:    Number((packed >> SHIFT_QA)       & MASK_QA),
    productId:  Number((packed >> SHIFT_PRODUCT)  & MASK_PRODUCT),
  };
}

/** Decoder. */
export function decodeQrCode(code) {
  return unpackBits(fromBase36(code));
}

export const __internals = {
  BITS:   { BITS_PHARMACY, BITS_KIOSK, BITS_CATEGORY, BITS_QA, BITS_PRODUCT },
  SHIFTS: { SHIFT_PHARMACY, SHIFT_KIOSK, SHIFT_CATEGORY, SHIFT_QA, SHIFT_PRODUCT },
  MASKS:  { MASK_PHARMACY, MASK_KIOSK, MASK_CATEGORY, MASK_QA, MASK_PRODUCT },
  TOTAL_BITS,
  MAX_PACKED,
};
