/**
 * Offline-first Crockford Base32 QR üretimi (9 karakter).
 *
 * Format:
 *   [PREFIX][COUNTER x7][CHECK]
 *
 *   PREFIX  (1 char): CROCKFORD_ALPHABET[eczane_kiosk_no]  (1-31 → '1'-'Z')
 *   COUNTER (7 char): mantıksal zaman/sayaç, Crockford Base32
 *   CHECK   (1 char): CROCKFORD_ALPHABET[sum(index(c)*(i+1) for i,c in enumerate(first8)) % 32]
 *
 * Sayaç: nextValue = max(Math.floor(Date.now()/1000), lastValue + 1)
 * SQLite'ta kalıcı tutulur; cihaz yeniden başlasa bile tekrar üretilmez.
 *
 * Üretim, sayaç güncelleme ve outbox insert tek transaction'da yapılmalı.
 */

export const CROCKFORD_ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';

/**
 * Sayıyı N karakterli Crockford Base32 string'e dönüştürür.
 * @param {number} value  - negatif olmayan tamsayı
 * @param {number} length - karakter sayısı
 */
export function encodeCrockford(value, length) {
  const base = CROCKFORD_ALPHABET.length; // 32
  let n = Math.floor(value);
  const chars = [];
  for (let i = 0; i < length; i++) {
    chars.push(CROCKFORD_ALPHABET[n % base]);
    n = Math.floor(n / base);
  }
  return chars.reverse().join('');
}

/**
 * Checksum karakterini hesaplar (son karakter doğrulama).
 * @param {string} first8 - 8 karakterlik prefix (PREFIX + COUNTER)
 * @returns {string} tek karakter
 */
export function computeChecksum(first8) {
  let total = 0;
  for (let i = 0; i < 8; i++) {
    const idx = CROCKFORD_ALPHABET.indexOf(first8[i]);
    if (idx < 0) throw new Error(`Geçersiz Crockford karakter: ${first8[i]}`);
    total += idx * (i + 1);
  }
  return CROCKFORD_ALPHABET[total % 32];
}

/**
 * Checksum doğrulaması.
 * @param {string} code - 9 karakterlik tam kod
 */
export function validateChecksum(code) {
  if (code.length !== 9) return false;
  try {
    return code[8] === computeChecksum(code.slice(0, 8));
  } catch {
    return false;
  }
}

/**
 * Crockford QR regex — sadece alfabe karakterleri, 9 karakter.
 */
export const CROCKFORD_QR_RE = /^[0123456789ABCDEFGHJKMNPQRSTVWXYZ]{9}$/;

/**
 * Bir sonraki QR kodu üretir.
 *
 * @param {import('better-sqlite3').Database} db  - SQLite bağlantısı
 * @param {number} eczaneKioskNo - 1..31, Crockford prefix
 * @returns {string} 9 karakterlik QR kodu
 * @throws {Error} eczane_kiosk_no yoksa veya geçersizse
 */
export function generateNextQr(db, eczaneKioskNo) {
  if (!Number.isInteger(eczaneKioskNo) || eczaneKioskNo < 1 || eczaneKioskNo > 31) {
    throw new Error(
      `eczane_kiosk_no geçersiz: ${eczaneKioskNo}. Kiosk yeniden senkronize edilmeli.`
    );
  }

  const prefix = CROCKFORD_ALPHABET[eczaneKioskNo]; // 1→'1', 10→'A', 31→'Z'

  // Sayacı monoton artır (tek transaction içinde yapılmalı)
  const counterRow = db.prepare('SELECT last_value FROM qr_counter WHERE id = 1').get();
  const lastValue = counterRow ? Number(counterRow.last_value) : 0;
  const nowSec = Math.floor(Date.now() / 1000);
  const nextValue = Math.max(nowSec, lastValue + 1);

  // 7 karaktere sığması için 32^7 = 34,359,738,368 üst sınır
  // Mevcut Unix timestamp (~1.75 milyar) çok altında; onlarca yıl yeterli.
  const counterStr = encodeCrockford(nextValue, 7);
  const first8 = prefix + counterStr;
  const check = computeChecksum(first8);
  const qrKodu = first8 + check;

  // Sayacı güncelle (çağıran transaction içinde olduğundan atomik)
  db.prepare(
    `UPDATE qr_counter SET last_value = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = 1`
  ).run(nextValue);

  return qrKodu;
}
