/**
 * printer.js buildReceiptBuffer — bozuk logo atlanır, sıradaki denenir.
 * Bu dosya printer.js'i mock'lamaz; pngToEscposRaster gerçek implementasyonu çalışır.
 * Gerçek (ama minimal) PNG dosyaları tmpdir'de oluşturulur.
 */
import { describe, it, expect } from 'vitest';
import { mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { deflateSync } from 'node:zlib';

import { buildReceiptBuffer } from '../src/printer.js';

// ── Test PNG oluşturucu ────────────────────────────────────────────────────

function _crc32(buf) {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
    t[n] = c;
  }
  let crc = 0xffffffff;
  for (let i = 0; i < buf.length; i++) crc = t[(crc ^ buf[i]) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

function _chunk(type, data) {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
  const tb = Buffer.from(type, 'ascii');
  const cv = Buffer.alloc(4); cv.writeUInt32BE(_crc32(Buffer.concat([tb, data])));
  return Buffer.concat([len, tb, data, cv]);
}

function makeMinimal1x1GrayscalePng() {
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(1, 0); ihdr.writeUInt32BE(1, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 0; // grayscale
  const rawRow = Buffer.from([0x00, 0xff]); // filter=None, pixel=white
  const idat = deflateSync(rawRow);
  return Buffer.concat([
    Buffer.from('89504e470d0a1a0a', 'hex'),
    _chunk('IHDR', ihdr),
    _chunk('IDAT', idat),
    _chunk('IEND', Buffer.alloc(0)),
  ]);
}

const TEST_TMP = join(tmpdir(), 'eisa-printer-test-' + Date.now());
mkdirSync(TEST_TMP, { recursive: true });

const VALID_PNG = join(TEST_TMP, 'valid.png');
writeFileSync(VALID_PNG, makeMinimal1x1GrayscalePng());

const INVALID_FILE = join(TEST_TMP, 'invalid.bin');
writeFileSync(INVALID_FILE, Buffer.alloc(64, 0xff)); // not valid PNG

const QR = 'TEST1234X';
const RASTER_COMMAND = Buffer.from([0x1d, 0x76, 0x30, 0x00]);
const QR_PRINT_COMMAND = Buffer.from([0x1d, 0x28, 0x6b, 0x03, 0x00, 0x31, 0x51, 0x30]);

function countRasterCommands(buffer) {
  let count = 0;
  let offset = 0;
  while ((offset = buffer.indexOf(RASTER_COMMAND, offset)) !== -1) {
    count += 1;
    offset += RASTER_COMMAND.length;
  }
  return count;
}

describe('buildReceiptBuffer — bozuk aday atlanır', () => {
  it('boş liste → e-ISA fallback, logoId=null', () => {
    const { logoId, buffer } = buildReceiptBuffer({ qrPayload: QR, logoCandidates: [] });
    expect(logoId).toBeNull();
    expect(buffer.length).toBeGreaterThan(10);
    expect(countRasterCommands(buffer)).toBe(1); // sabit alt e-isa logosu
  });

  it('tek geçerli PNG → logoId döner, buffer ESC/POS içerir', () => {
    const { logoId, buffer } = buildReceiptBuffer({
      qrPayload: QR,
      logoCandidates: [{ id: 'good', local_path: VALID_PNG }],
    });
    expect(logoId).toBe('good');
    expect(buffer.length).toBeGreaterThan(10);
    expect(countRasterCommands(buffer)).toBe(2); // sponsor üstte + sabit e-isa altta
    const sponsorPosition = buffer.indexOf(RASTER_COMMAND);
    const qrPosition = buffer.indexOf(QR_PRINT_COMMAND);
    const eisaPosition = buffer.indexOf(RASTER_COMMAND, sponsorPosition + RASTER_COMMAND.length);
    expect(sponsorPosition).toBeLessThan(qrPosition);
    expect(qrPosition).toBeLessThan(eisaPosition);
  });

  it('A bozuk, B geçerliyken B basılır, logoId=B', () => {
    const { logoId } = buildReceiptBuffer({
      qrPayload: QR,
      logoCandidates: [
        { id: 'A', local_path: INVALID_FILE },
        { id: 'B', local_path: VALID_PNG },
      ],
    });
    expect(logoId).toBe('B');
  });

  it('A ve B bozuk, C geçerliyken C basılır', () => {
    const { logoId } = buildReceiptBuffer({
      qrPayload: QR,
      logoCandidates: [
        { id: 'A', local_path: INVALID_FILE },
        { id: 'B', local_path: INVALID_FILE },
        { id: 'C', local_path: VALID_PNG },
      ],
    });
    expect(logoId).toBe('C');
  });

  it('tüm adaylar bozuksa e-ISA fallback, logoId=null', () => {
    const { logoId } = buildReceiptBuffer({
      qrPayload: QR,
      logoCandidates: [
        { id: 'A', local_path: INVALID_FILE },
        { id: 'B', local_path: INVALID_FILE },
      ],
    });
    expect(logoId).toBeNull();
  });

  it('payload yalnız gerçekten kullanılan logonun ID\'sini içerir (A bozuk → B)', () => {
    const { logoId, buffer } = buildReceiptBuffer({
      qrPayload: QR,
      logoCandidates: [
        { id: 'X', local_path: INVALID_FILE },
        { id: 'Y', local_path: VALID_PNG },
      ],
    });
    expect(logoId).toBe('Y');
    expect(buffer.length).toBeGreaterThan(0);
  });

  it('bozuk adaylar cursor/sayaç üzerinde değil yalnız logoId etkiler', () => {
    // buildReceiptBuffer cursor/sayaç güncellemez — bu testte return değeri doğrulanır
    const { logoId } = buildReceiptBuffer({
      qrPayload: QR,
      logoCandidates: [{ id: 'Z', local_path: INVALID_FILE }],
    });
    expect(logoId).toBeNull(); // bozuk → fallback, sayaç ilerlemez (çağıran commitBasariliBaski kullanır)
  });
});
