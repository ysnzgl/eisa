/**
 * EISA1 QR kodu formatı.
 *
 * Format:
 *   EISA1:{ageRange}:{gender}:{categorySlug}:{qId1}:{ans1}:{qId2}:{ans2}:...:{8hexChecksum}
 *
 * Hassas akış:
 *   EISA1:{ageRange}:{gender}:{categorySlug}:S:{8hexChecksum}
 *
 * Checksum: SHA-256(payload before last colon-segment), ilk 8 hex karakter.
 */

/**
 * @param {{ ageRange: string, gender: string, categorySlug: string, answers: Array<{id:string, answer:'Y'|'N'}>, isSensitive?: boolean }} opts
 * @returns {Promise<string>}
 */
export async function buildEisaQr({ ageRange, gender, categorySlug, answers, isSensitive = false }) {
  const parts = ['EISA1', ageRange, gender, categorySlug];

  if (isSensitive || answers.length === 0) {
    parts.push('S');
  } else {
    for (const a of answers) {
      parts.push(a.id, a.answer);
    }
  }

  const payload = parts.join(':');
  const checksum = await _sha256short(payload);
  return `${payload}:${checksum}`;
}

/**
 * EISA1 QR kodunu ayrıştırır.
 * @param {string} qrString
 * @returns {{ ageRange:string, gender:string, categorySlug:string, answers:Array<{id:string,answer:string}>, isSensitive:boolean, checksum:string }|null}
 */
export function parseEisaQr(qrString) {
  if (!qrString || !qrString.startsWith('EISA1:')) return null;

  const parts = qrString.split(':');
  // Minimum: EISA1 + ageRange + gender + slug + (S or q+ans) + checksum = 6
  if (parts.length < 6) return null;

  const checksum = parts[parts.length - 1];
  const inner = parts.slice(1, -1); // without EISA1 and checksum
  const [ageRange, gender, categorySlug, ...rest] = inner;

  let isSensitive = false;
  const answers = [];

  if (rest[0] === 'S') {
    isSensitive = true;
  } else {
    for (let i = 0; i + 1 < rest.length; i += 2) {
      answers.push({ id: rest[i], answer: rest[i + 1] });
    }
  }

  return { ageRange, gender, categorySlug, answers, isSensitive, checksum };
}

/**
 * EISA1 QR kodunun checksum'ını doğrular.
 * @param {string} qrString
 * @returns {Promise<boolean>}
 */
export async function verifyEisaQr(qrString) {
  const lastColon = qrString.lastIndexOf(':');
  if (lastColon < 0) return false;
  const payload = qrString.substring(0, lastColon);
  const claimed = qrString.substring(lastColon + 1);
  const expected = await _sha256short(payload);
  return claimed === expected;
}

async function _sha256short(text) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(buf))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')
    .substring(0, 8);
}
