/**
 * useSponsorship — saf yardımcı fonksiyon birim testleri.
 */
import { describe, it, expect } from 'vitest';
import {
  hhmmToMinutes, minutesToHHMM, secondToHHMMSS, windowSeconds, maxCountHint,
  validateRow, rowToPayload, heatmapColor, groupByHour, hourTimeline,
  diffCampaignNames, extractCapacityError, weekdaysText, weekdayLabel,
  WEEKDAYS,
} from '../../composables/useSponsorship.js';

// ── Zaman dönüşümü ───────────────────────────────────────────────────────────
describe('hhmmToMinutes', () => {
  it('normal saatleri dakikaya çevirir', () => {
    expect(hhmmToMinutes('08:00')).toBe(480);
    expect(hhmmToMinutes('19:30')).toBe(1170);
    expect(hhmmToMinutes('00:00')).toBe(0);
  });
  it('24:00 yalnız tam değer olarak 1440 döner', () => {
    expect(hhmmToMinutes('24:00')).toBe(1440);
    expect(hhmmToMinutes('24:01')).toBeNull();
    expect(hhmmToMinutes('25:00')).toBeNull();
  });
  it('geçersiz girdilerde null döner', () => {
    expect(hhmmToMinutes('8:60')).toBeNull();
    expect(hhmmToMinutes('abc')).toBeNull();
    expect(hhmmToMinutes('')).toBeNull();
    expect(hhmmToMinutes(null)).toBeNull();
  });
});

describe('minutesToHHMM', () => {
  it('dakikayı HH:MM formatına çevirir', () => {
    expect(minutesToHHMM(480)).toBe('08:00');
    expect(minutesToHHMM(1170)).toBe('19:30');
    expect(minutesToHHMM(1440)).toBe('24:00');
    expect(minutesToHHMM(0)).toBe('00:00');
  });
  it('sınır dışı değerleri kırpar', () => {
    expect(minutesToHHMM(-5)).toBe('00:00');
    expect(minutesToHHMM(9999)).toBe('24:00');
  });
  it('round-trip tutarlı', () => {
    for (const t of ['08:15', '12:45', '23:59', '24:00']) {
      expect(minutesToHHMM(hhmmToMinutes(t))).toBe(t);
    }
  });
});

describe('secondToHHMMSS', () => {
  it('gün içi saniyeyi biçimlendirir', () => {
    expect(secondToHHMMSS(0)).toBe('00:00:00');
    expect(secondToHHMMSS(3661)).toBe('01:01:01');
    expect(secondToHHMMSS(86399)).toBe('23:59:59');
  });
});

describe('windowSeconds / maxCountHint', () => {
  it('pencere saniyesini hesaplar', () => {
    expect(windowSeconds('08:00', '19:00')).toBe(11 * 3600);
    expect(windowSeconds('08:00', '08:00')).toBe(0);
    expect(windowSeconds('10:00', '09:00')).toBe(0);
  });
  it('max gösterim tahmini = floor(pencere/süre)', () => {
    expect(maxCountHint('08:00', '09:00', 15)).toBe(240);  // 3600/15
    expect(maxCountHint('08:00', '19:00', 30)).toBe(Math.floor(11 * 3600 / 30));
    expect(maxCountHint('08:00', '19:00', 0)).toBe(0);
  });
});

// ── Satır doğrulama ──────────────────────────────────────────────────────────
describe('validateRow', () => {
  const base = { window_start: '08:00', window_end: '19:00', count: 10 };
  it('geçerli satır', () => {
    expect(validateRow(base, 15).valid).toBe(true);
  });
  it('bitiş başlangıçtan küçükse hata', () => {
    const r = validateRow({ ...base, window_start: '19:00', window_end: '08:00' }, 15);
    expect(r.valid).toBe(false);
    expect(r.errors.join()).toMatch(/büyük/);
  });
  it('count < 1 hata', () => {
    expect(validateRow({ ...base, count: 0 }, 15).valid).toBe(false);
    expect(validateRow({ ...base, count: -3 }, 15).valid).toBe(false);
  });
  it('count max hint üstündeyse hata', () => {
    const r = validateRow({ window_start: '08:00', window_end: '09:00', count: 1000 }, 15);
    expect(r.valid).toBe(false);
    expect(r.errors.join()).toMatch(/sığar/);
  });
  it('bitiş tarihi başlangıçtan önceyse hata', () => {
    const r = validateRow({ ...base, start_date: '2026-05-10', end_date: '2026-05-01' }, 15);
    expect(r.valid).toBe(false);
  });
});

describe('rowToPayload', () => {
  it('boş weekday dizisini null yapar', () => {
    const p = rowToPayload({ campaign_id: 1, window_start: '08:00', window_end: '19:00', count: 5, active_weekdays: [], start_date: '', end_date: '', is_active: true });
    expect(p.active_weekdays).toBeNull();
    expect(p.start_date).toBeNull();
    expect(p.count).toBe(5);
    expect(p.is_active).toBe(true);
  });
  it('weekday dizisini sıralı sayılara çevirir', () => {
    const p = rowToPayload({ campaign_id: 2, window_start: '08:00', window_end: '19:00', count: 3, active_weekdays: [5, 1, 3] });
    expect(p.active_weekdays).toEqual([1, 3, 5]);
  });
});

// ── Isı haritası ─────────────────────────────────────────────────────────────
describe('heatmapColor', () => {
  it('boş saat açık gri', () => {
    expect(heatmapColor(0)).toBe('#F1F0EC');
    expect(heatmapColor(null)).toBe('#F1F0EC');
  });
  it('doluluk arttıkça renk değişir ve en yüksek kırmızı', () => {
    expect(heatmapColor(0.1)).not.toBe(heatmapColor(0.6));
    expect(heatmapColor(1)).toBe('#EF4444');
    expect(heatmapColor(0.99)).toBe('#EF4444');
  });
});

// ── Gruplama ─────────────────────────────────────────────────────────────────
describe('groupByHour / hourTimeline', () => {
  const items = [
    { hour: 8, offset: 100, duration: 15 },
    { hour: 8, offset: 10, duration: 15 },
    { hour: 10, offset: 0, duration: 30 },
  ];
  it('24 saatlik kovaya böler ve offset sıralar', () => {
    const buckets = groupByHour(items);
    expect(buckets.length).toBe(24);
    expect(buckets[8].items.map((i) => i.offset)).toEqual([10, 100]);
    expect(buckets[10].items.length).toBe(1);
  });
  it('hourTimeline yüzde konum hesaplar', () => {
    const tl = hourTimeline(items, 8);
    expect(tl.length).toBe(2);
    expect(tl[0].offset).toBe(10);
    expect(tl[0].leftPct).toBeCloseTo((10 / 3600) * 100);
    expect(tl[0].widthPct).toBeGreaterThan(0);
  });
});

// ── Diff ─────────────────────────────────────────────────────────────────────
describe('diffCampaignNames', () => {
  it('eklenecek / silinecek / kalacak ayırır', () => {
    const d = diffCampaignNames(['A', 'B', 'C'], ['B', 'C', 'D']);
    expect(d.added).toEqual(['A']);
    expect(d.removed).toEqual(['D']);
    expect(d.kept.sort()).toEqual(['B', 'C']);
  });
  it('boş hedef hepsini ekler', () => {
    const d = diffCampaignNames(['X', 'Y'], []);
    expect(d.added).toEqual(['X', 'Y']);
    expect(d.removed).toEqual([]);
  });
});

// ── Hata ayıklama ────────────────────────────────────────────────────────────
describe('extractCapacityError', () => {
  it('capacity_exceeded yanıtını ayıklar', () => {
    const err = { response: { status: 400, data: {
      code: 'capacity_exceeded', detail: 'Kapasite aşıldı.',
      conflicts: [{ date: '2026-05-01', campaign_id: 1, campaign_name: 'A', requested: 100, placed: 80 }],
    } } };
    const r = extractCapacityError(err);
    expect(r.code).toBe('capacity_exceeded');
    expect(r.detail).toBe('Kapasite aşıldı.');
    expect(r.conflicts).toHaveLength(1);
    expect(r.conflicts[0].placed).toBe(80);
  });
  it('rejected / skipped alanlarını ayıklar', () => {
    const err = { response: { data: {
      code: 'capacity_exceeded', detail: 'x',
      rejected: [{ kiosk_id: 3, kiosk_name: 'K3', conflicts: [] }],
      skipped_already_assigned: [5, 6],
    } } };
    const r = extractCapacityError(err);
    expect(r.rejected).toHaveLength(1);
    expect(r.skipped).toEqual([5, 6]);
  });
  it('kapasite hatası değilse null', () => {
    expect(extractCapacityError({ response: { data: { detail: 'başka' } } })).toBeNull();
    expect(extractCapacityError(null)).toBeNull();
  });
});

// ── Hafta günleri ────────────────────────────────────────────────────────────
describe('weekdays', () => {
  it('ISO 1=Pzt … 7=Paz', () => {
    expect(WEEKDAYS[0]).toMatchObject({ value: 1, label: 'Pzt' });
    expect(WEEKDAYS[6]).toMatchObject({ value: 7, label: 'Paz' });
    expect(weekdayLabel(3)).toBe('Çar');
  });
  it('weekdaysText boş/tam => Her gün', () => {
    expect(weekdaysText([])).toBe('Her gün');
    expect(weekdaysText(null)).toBe('Her gün');
    expect(weekdaysText([1, 2, 3, 4, 5, 6, 7])).toBe('Her gün');
  });
  it('weekdaysText seçili günleri sıralı listeler', () => {
    expect(weekdaysText([3, 1])).toBe('Pzt, Çar');
  });
});
