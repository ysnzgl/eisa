/**
 * QR Bit-Packing Codec — E-İSA offline-first 41-bit QR şifreleyici/çözücü.
 *
 * Amaç:
 *   İnternet bağlantısı olmayan kiosk cihazının ürettiği oturum sonucunu,
 *   merkezi panele yalnızca 8 karakterlik alfanümerik (Base36) bir kod
 *   üzerinden taşımak. Şifreleme değil, *yoğun kodlama* (lossless packing).
 *
 * ──────────────────────────────────────────────────────────────────────────
 *  BIT LAYOUT  (toplam 41 bit, MSB → LSB)
 * ──────────────────────────────────────────────────────────────────────────
 *
 *   bit index :  40 ............................................. 0
 *   ┌───────────────┬──────┬──────────┬─────────┬────────────────┐
 *   │ pharmacyId 15 │ k 4  │ cat   7  │ qa   6  │ productId   9  │
 *   └───────────────┴──────┴──────────┴─────────┴────────────────┘
 *      shift 26       22       15         9            0
 *
 *   Alan            | Bit | Maks değer (2^n − 1) | Shift offset
 *   ----------------+-----+----------------------+-------------
 *   pharmacyId      | 15  |        32 767        |     26
 *   kioskId         |  4  |            15        |     22
 *   categoryId      |  7  |           127        |     15
 *   qaCombo         |  6  |            63        |      9
 *   productId       |  9  |           511        |      0
 *
 *   Toplam: 15 + 4 + 7 + 6 + 9 = 41 bit  →  2^41 = 2 199 023 255 552
 *   Base36 uzunluğu: ⌈ 41 / log2(36) ⌉ = 8 karakter (sol '0' padding ile).
 *
 *   NOT: 41-bit, 32-bit signed int sınırını (2^31 − 1) aşar. Bu yüzden
 *   tüm bitwise işlemler JavaScript'te BigInt ile yapılır; aksi halde
 *   shift operatörleri sayıyı 32-bit'e indirger ve veri bozulur.
 * ──────────────────────────────────────────────────────────────────────────
 */

// ---- Alan boyutları (bit) ------------------------------------------------
const BITS_PHARMACY = 15n;
const BITS_KIOSK    =  4n;
const BITS_CATEGORY =  7n;
const BITS_QA       =  6n;
const BITS_PRODUCT  =  9n;

// ---- Shift offsetleri ----------------------------------------------------
// Her alan, kendisinden DAHA DÜŞÜK öneme sahip alanların toplam bit sayısı
// kadar sola kaydırılır. En sağdaki alan (productId) shift = 0'dır.
const SHIFT_PRODUCT  = 0n;
const SHIFT_QA       = SHIFT_PRODUCT + BITS_PRODUCT;        // 9
const SHIFT_CATEGORY = SHIFT_QA      + BITS_QA;             // 15
const SHIFT_KIOSK    = SHIFT_CATEGORY + BITS_CATEGORY;      // 22
const SHIFT_PHARMACY = SHIFT_KIOSK   + BITS_KIOSK;          // 26

// ---- Maskeler ((1 << n) - 1) --------------------------------------------
// Bir alanı çözerken: (packed >> shift) & mask  → o alana ait n bit kalır.
const MASK_PHARMACY = (1n << BITS_PHARMACY) - 1n; // 0x7FFF
const MASK_KIOSK    = (1n << BITS_KIOSK)    - 1n; // 0x0F
const MASK_CATEGORY = (1n << BITS_CATEGORY) - 1n; // 0x7F
const MASK_QA       = (1n << BITS_QA)       - 1n; // 0x3F
const MASK_PRODUCT  = (1n << BITS_PRODUCT)  - 1n; // 0x1FF

const TOTAL_BITS = BITS_PHARMACY + BITS_KIOSK + BITS_CATEGORY + BITS_QA + BITS_PRODUCT; // 41n
const MAX_PACKED = (1n << TOTAL_BITS) - 1n;

export const QR_BITPACK_LENGTH = 8;
export const QR_BITPACK_RE = /^[0-9A-Z]{8}$/;

/**
 * Tek bir alanın sınırlarını doğrular; aksi hâlde hata fırlatır.
 * @param {string} name
 * @param {number|bigint} value
 * @param {bigint} mask
 */
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

/**
 * 5 integer alanı 41-bit BigInt olarak paketler.
 * @param {{pharmacyId:number,kioskId:number,categoryId:number,qaCombo:number,productId:number}} f
 * @returns {bigint}
 */
export function packBits(f) {
  const p  = assertRange('pharmacyId', f.pharmacyId, MASK_PHARMACY);
  const k  = assertRange('kioskId',    f.kioskId,    MASK_KIOSK);
  const c  = assertRange('categoryId', f.categoryId, MASK_CATEGORY);
  const q  = assertRange('qaCombo',    f.qaCombo,    MASK_QA);
  const pr = assertRange('productId',  f.productId,  MASK_PRODUCT);

  // Bit-shift (<<) ile her alanı kendi yuvasına yerleştirip
  // bitwise OR (|) ile birleştiriyoruz. Alanlar arasında çakışma
  // olmaması için maks değerleri shift miktarlarıyla uyumlu seçildi.
  return (p  << SHIFT_PHARMACY)
       | (k  << SHIFT_KIOSK)
       | (c  << SHIFT_CATEGORY)
       | (q  << SHIFT_QA)
       | (pr << SHIFT_PRODUCT);
}

/**
 * 41-bit BigInt'i sabit 8 karakterlik UPPERCASE Base36 string'e çevirir.
 * Çıktı 8 karakterden kısa ise sol tarafa '0' ile padding yapılır.
 * @param {bigint} packed
 * @returns {string}
 */
export function toBase36Padded(packed) {
  if (packed < 0n || packed > MAX_PACKED) {
    throw new RangeError('packed değer 41-bit aralığını aşıyor');
  }
  const s = packed.toString(36).toUpperCase();
  return s.length >= QR_BITPACK_LENGTH ? s : '0'.repeat(QR_BITPACK_LENGTH - s.length) + s;
}

/**
 * Görev A — Encoder.
 * 5 alanı alıp 8 karakterlik Base36 QR koduna çevirir.
 */
export function encodeQrCode(fields) {
  return toBase36Padded(packBits(fields));
}

/**
 * 8 karakterlik Base36 string'i 41-bit BigInt'e dönüştürür.
 * @param {string} code
 * @returns {bigint}
 */
export function fromBase36(code) {
  if (typeof code !== 'string' || !QR_BITPACK_RE.test(code)) {
    throw new Error('Geçersiz QR kod formatı (8 karakter, 0-9 A-Z bekleniyor)');
  }
  // BigInt yerleşik olarak yalnızca 0b/0o/0x prefix'lerini destekler;
  // base36 için elle parse ediyoruz.
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

/**
 * Paketlenmiş 41-bit değerden alanları ayrıştırır.
 *
 *   Her alan için işlem:
 *     1) packed >> SHIFT_X    → ilgili alanı en sağa kaydır
 *     2) … & MASK_X           → sadece o alanın bitlerini bırak
 *
 *   Örn. categoryId çözümü:
 *     (packed >> 15n) & 0x7Fn
 *
 * @param {bigint} packed
 */
export function unpackBits(packed) {
  return {
    pharmacyId: Number((packed >> SHIFT_PHARMACY) & MASK_PHARMACY),
    kioskId:    Number((packed >> SHIFT_KIOSK)    & MASK_KIOSK),
    categoryId: Number((packed >> SHIFT_CATEGORY) & MASK_CATEGORY),
    qaCombo:    Number((packed >> SHIFT_QA)       & MASK_QA),
    productId:  Number((packed >> SHIFT_PRODUCT)  & MASK_PRODUCT),
  };
}

/**
 * Görev B — Decoder.
 * 8 karakterlik Base36 QR kodu alır, orijinal 5 alanı döndürür.
 */
export function decodeQrCode(code) {
  return unpackBits(fromBase36(code));
}

// Test / debug için iç sabitleri dışa aç:
export const __internals = {
  BITS:   { BITS_PHARMACY, BITS_KIOSK, BITS_CATEGORY, BITS_QA, BITS_PRODUCT },
  SHIFTS: { SHIFT_PHARMACY, SHIFT_KIOSK, SHIFT_CATEGORY, SHIFT_QA, SHIFT_PRODUCT },
  MASKS:  { MASK_PHARMACY, MASK_KIOSK, MASK_CATEGORY, MASK_QA, MASK_PRODUCT },
  TOTAL_BITS,
  MAX_PACKED,
};
