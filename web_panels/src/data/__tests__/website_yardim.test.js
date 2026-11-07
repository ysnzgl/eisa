import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { YARDIM, YARDIM_KONULARI } from '../websiteYardim';

const VIEWS = join(__dirname, '../../views/admin/web-sitesi');

describe('Web Sitesi yardım dokümanı', () => {
  it('konu anahtarları benzersiz ve zorunlu alanlar dolu', () => {
    const anahtarlar = YARDIM_KONULARI.map((k) => k.key);
    expect(new Set(anahtarlar).size).toBe(anahtarlar.length);
    for (const k of YARDIM_KONULARI) {
      expect(k.baslik).toBeTruthy();
      expect(k.ikon).toMatch(/^fa-/);
    }
  });

  it('ekranlardaki YardimButonu konuları dokümanda tanımlı', () => {
    const dosyalar = readdirSync(VIEWS).filter((f) => f.endsWith('.vue'));
    let kullanim = 0;
    for (const f of dosyalar) {
      const kaynak = readFileSync(join(VIEWS, f), 'utf8');
      for (const m of kaynak.matchAll(/<YardimButonu :konular="\[([^\]]*)\]"/g)) {
        for (const anahtar of m[1].split(',').map((x) => x.trim().replace(/'/g, ''))) {
          kullanim++;
          expect(YARDIM[anahtar], `${f}: '${anahtar}'`).toBeDefined();
        }
      }
    }
    expect(kullanim).toBeGreaterThanOrEqual(8);
  });
});