/**
 * DOOH saat-mutlak slot cozumleyici testleri (playlistSlot.js).
 * Her test kendi acik input/output degerini tasir; ticari sabit yoktur.
 */
import { describe, it, expect } from 'vitest';
import {
  resolveActiveItem,
  secondsUntilBoundary,
  currentHourPosition,
  HOUR_SECONDS,
} from '../lib/playlistSlot.js';

const item = (id, offset, duration, type = 'creative') => ({
  id,
  asset_id: id,
  asset_type: type,
  estimated_start_offset_seconds: offset,
  duration_seconds: duration,
});

describe('resolveActiveItem — [offset, offset+duration) araligi', () => {
  // Kayitli veri: offset=0 dur=15, sonraki offset=60 dur=15
  const items = [item('a', 0, 15), item('b', 60, 15)];

  it('#1 pos=0 → ilk item aktif', () => {
    expect(resolveActiveItem(items, 0)?.id).toBe('a');
  });

  it('#1 pos=14 → ilk item hala aktif (sinir ic)', () => {
    expect(resolveActiveItem(items, 14)?.id).toBe('a');
  });

  it('#1 pos=15 → ilk item aktif DEGIL (sinir dis)', () => {
    expect(resolveActiveItem(items, 15)).toBeNull();
  });

  it('#2 pos=30 → [15,60) boslugu, aktif item yok', () => {
    expect(resolveActiveItem(items, 30)).toBeNull();
  });

  it('#2 pos=59 → hala bosluk', () => {
    expect(resolveActiveItem(items, 59)).toBeNull();
  });

  it('pos=60 → ikinci item aktif', () => {
    expect(resolveActiveItem(items, 60)?.id).toBe('b');
  });
});

describe('resolveActiveItem — degisken sureler (config-bagimsiz)', () => {
  it('#4 30sn item tam [0,30) aktif', () => {
    const items = [item('x', 0, 30)];
    expect(resolveActiveItem(items, 29)?.id).toBe('x');
    expect(resolveActiveItem(items, 30)).toBeNull();
  });

  it('#5 45sn item tam [0,45) aktif', () => {
    const items = [item('x', 0, 45)];
    expect(resolveActiveItem(items, 44)?.id).toBe('x');
    expect(resolveActiveItem(items, 45)).toBeNull();
  });

  it('#6 60sn item tam [0,60) aktif', () => {
    const items = [item('x', 0, 60)];
    expect(resolveActiveItem(items, 59)?.id).toBe('x');
    expect(resolveActiveItem(items, 60)).toBeNull();
  });
});

describe('resolveActiveItem — house_ad item defensive skip', () => {
  it('#3 house_ad item atlanir (HouseAd kaldirildi), yalniz creative aktif olur', () => {
    // creative [0,15), house_ad [20,35) (legacy — atlanir), creative [60,75)
    const items = [
      item('c1', 0, 15, 'creative'),
      item('h1', 20, 15, 'house_ad'),
      item('c2', 60, 15, 'creative'),
    ];
    expect(resolveActiveItem(items, 10)?.id).toBe('c1');
    expect(resolveActiveItem(items, 17)).toBeNull();     // c1 bitti, c2 baslamadi
    expect(resolveActiveItem(items, 25)).toBeNull();     // house_ad atlanir → bosluk (idle)
    expect(resolveActiveItem(items, 40)).toBeNull();     // bosluk
    expect(resolveActiveItem(items, 65)?.id).toBe('c2');
  });
});

describe('resolveActiveItem — ayni asset farkli slotlar', () => {
  it('#9 ayni asset_id farkli offsetlerde ayri slot; her biri kendi araliginda', () => {
    const items = [item('same', 0, 15), item('same', 60, 15)];
    // Farkli slot kimlikleri: PlaylistItem.id benzersiz kabul edilir (burada asset_id ayni)
    const a = resolveActiveItem(items, 5);
    const b = resolveActiveItem(items, 65);
    expect(a?.estimated_start_offset_seconds).toBe(0);
    expect(b?.estimated_start_offset_seconds).toBe(60);
  });
});

describe('secondsUntilBoundary — sonraki durum degisimi', () => {
  const items = [item('a', 0, 15), item('b', 60, 15)];

  it('pos=0 → item sonuna (15) kadar 15sn', () => {
    expect(secondsUntilBoundary(items, 0)).toBe(15);
  });

  it('pos=10 → item sonuna kadar 5sn', () => {
    expect(secondsUntilBoundary(items, 10)).toBe(5);
  });

  it('#7 pos=15 (bosluk) → sonraki item basina (60) kadar 45sn (son item saat sonuna uzatilmaz)', () => {
    expect(secondsUntilBoundary(items, 15)).toBe(45);
  });

  it('son item sonrasi → saat sonuna (3600) kadar sarilir', () => {
    expect(secondsUntilBoundary(items, 75)).toBe(HOUR_SECONDS - 75);
  });
});

describe('currentHourPosition — saat-ici 0..3599', () => {
  it('epoch%3600 saat-ici saniyeyi verir', () => {
    // 01:02:03 UTC → 2*60+3 = 123
    const ms = Date.UTC(2026, 0, 1, 1, 2, 3);
    expect(currentHourPosition(ms)).toBe(123);
  });

  it('#8 gercek offsetli veri sequential carousel gerektirmez (deterministik pozisyon)', () => {
    const ms = Date.UTC(2026, 0, 1, 5, 20, 58); // within-hour 20*60+58 = 1258
    expect(currentHourPosition(ms)).toBe(1258);
  });
});
