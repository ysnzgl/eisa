/**
 * useSponsorship — Kiosk sponsorluk ekranları için saf (test edilebilir) yardımcılar.
 *
 * Buradaki fonksiyonlar DOM / API'ye bağımlı değildir; zaman dönüşümü, satır
 * doğrulama, ısı haritası renkleri, önizleme gruplama, diff ve hata ayıklama
 * mantığını tek yerde toplar. Bileşenler bu composable'ı import ederek kullanır.
 */

// ── Hafta günleri (ISO 1=Pzt … 7=Paz) ────────────────────────────────────────
export const WEEKDAYS = [
  { value: 1, label: 'Pzt', full: 'Pazartesi' },
  { value: 2, label: 'Sal', full: 'Salı' },
  { value: 3, label: 'Çar', full: 'Çarşamba' },
  { value: 4, label: 'Per', full: 'Perşembe' },
  { value: 5, label: 'Cum', full: 'Cuma' },
  { value: 6, label: 'Cmt', full: 'Cumartesi' },
  { value: 7, label: 'Paz', full: 'Pazar' },
];

export function weekdayLabel(value) {
  const d = WEEKDAYS.find((w) => w.value === Number(value));
  return d ? d.label : String(value);
}

/**
 * Hafta günü dizisini okunabilir metne çevirir.
 * Boş / null => "Her gün".
 */
export function weekdaysText(list) {
  if (!list || !Array.isArray(list) || list.length === 0 || list.length === 7) return 'Her gün';
  return [...list]
    .map(Number)
    .sort((a, b) => a - b)
    .map(weekdayLabel)
    .join(', ');
}

// ── Zaman dönüşümleri ("HH:MM" <-> dakika) ───────────────────────────────────

/**
 * "HH:MM" metnini gün başından itibaren dakikaya çevirir.
 * "24:00" => 1440 (yalnız pencere sonu için anlamlı). Geçersiz => null.
 */
export function hhmmToMinutes(hhmm) {
  if (typeof hhmm !== 'string') return null;
  const m = /^(\d{1,2}):(\d{2})$/.exec(hhmm.trim());
  if (!m) return null;
  const h = Number(m[1]);
  const min = Number(m[2]);
  if (min > 59) return null;
  if (h > 24) return null;
  if (h === 24 && min !== 0) return null;   // yalnız tam "24:00" geçerli
  return h * 60 + min;
}

/** Dakika değerini "HH:MM" metnine çevirir. 1440 => "24:00". */
export function minutesToHHMM(mins) {
  const total = Math.max(0, Math.min(1440, Math.round(Number(mins) || 0)));
  const h = Math.floor(total / 60);
  const m = total % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

/** Gün içi saniyeyi "HH:MM:SS" metnine çevirir (0..86399). */
export function secondToHHMMSS(sec) {
  const total = Math.max(0, Math.round(Number(sec) || 0));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return [h, m, s].map((x) => String(x).padStart(2, '0')).join(':');
}

/** Pencere uzunluğu (saniye) — bitiş dahil değil. */
export function windowSeconds(windowStart, windowEnd) {
  const s = hhmmToMinutes(windowStart);
  const e = hhmmToMinutes(windowEnd);
  if (s == null || e == null) return 0;
  return Math.max(0, (e - s) * 60);
}

/**
 * Pencerede bir görselin kaç kez sığabileceğine dair üst sınır tahmini.
 * floor(pencere_saniye / min_süre). Saat sınırı kısıtı göz ardı edilir (kaba tahmin).
 */
export function maxCountHint(windowStart, windowEnd, minDuration) {
  const dur = Number(minDuration);
  if (!dur || dur <= 0) return 0;
  return Math.floor(windowSeconds(windowStart, windowEnd) / dur);
}

// ── Satır doğrulama ──────────────────────────────────────────────────────────

/**
 * Bir sponsorluk satırını doğrular.
 * @returns {{valid:boolean, errors:string[]}}
 */
export function validateRow(row, minDuration = 1) {
  const errors = [];
  const s = hhmmToMinutes(row?.window_start);
  const e = hhmmToMinutes(row?.window_end);
  if (s == null) errors.push('Başlangıç saati geçersiz.');
  if (e == null) errors.push('Bitiş saati geçersiz.');
  if (s != null && e != null && e <= s) {
    errors.push('Bitiş saati başlangıçtan büyük olmalı.');
  }
  const count = Number(row?.count);
  if (!Number.isInteger(count) || count < 1) {
    errors.push('Gösterim sayısı en az 1 olmalı.');
  }
  if (row?.start_date && row?.end_date && row.end_date < row.start_date) {
    errors.push('Bitiş tarihi başlangıç tarihinden önce olamaz.');
  }
  const hint = maxCountHint(row?.window_start, row?.window_end, minDuration);
  if (hint > 0 && count > hint) {
    errors.push(`Bu pencereye en fazla ~${hint} gösterim sığar.`);
  }
  return { valid: errors.length === 0, errors };
}

/**
 * PUT gövdesi için bir satırı sunucu şekline dönüştürür.
 * active_weekdays boş dizi ise null gönderilir (her gün).
 */
export function rowToPayload(row) {
  const wd = Array.isArray(row.active_weekdays) && row.active_weekdays.length
    ? [...row.active_weekdays].map(Number).sort((a, b) => a - b)
    : null;
  return {
    campaign_id: row.campaign_id,
    window_start: row.window_start,
    window_end: row.window_end,
    count: Number(row.count),
    active_weekdays: wd,
    start_date: row.start_date || null,
    end_date: row.end_date || null,
    is_active: row.is_active !== false,
  };
}

// ── Isı haritası renk ölçeği ─────────────────────────────────────────────────

/**
 * Kullanım oranına (0..1) göre ısı haritası rengi döner.
 * Boş saatler açık gri; doluluk arttıkça yeşil → sarı → turuncu → kırmızı.
 */
export function heatmapColor(utilization) {
  const u = Number(utilization);
  if (!(u > 0)) return '#F1F0EC';
  if (u < 0.25) return '#D1FAE5';
  if (u < 0.5) return '#6EE7B7';
  if (u < 0.75) return '#FCD34D';
  if (u < 0.95) return '#FB923C';
  return '#EF4444';
}

// ── Önizleme gruplama ────────────────────────────────────────────────────────

/**
 * Önizleme item'larını saate göre gruplar (0..23). Her saat için item dizisi.
 * @returns {Array<{hour:number, items:Array}>} 24 elemanlı dizi
 */
export function groupByHour(items) {
  const buckets = Array.from({ length: 24 }, (_, hour) => ({ hour, items: [] }));
  for (const it of items || []) {
    const h = Number(it.hour);
    if (Number.isInteger(h) && h >= 0 && h < 24) buckets[h].items.push(it);
  }
  for (const b of buckets) {
    b.items.sort((a, z) => (a.offset ?? a.start_second ?? 0) - (z.offset ?? z.start_second ?? 0));
  }
  return buckets;
}

/** Belirli bir saate ait item'ları, dakika-cinsinden offset ile döner. */
export function hourTimeline(items, hour) {
  return (items || [])
    .filter((it) => Number(it.hour) === Number(hour))
    .map((it) => ({
      ...it,
      offset: Number(it.offset ?? 0),
      duration: Number(it.duration ?? 0),
      leftPct: (Number(it.offset ?? 0) / 3600) * 100,
      widthPct: Math.max(0.2, (Number(it.duration ?? 0) / 3600) * 100),
    }))
    .sort((a, z) => a.offset - z.offset);
}

// ── Diff (kopyalama önizlemesi için yardımcı) ────────────────────────────────

/**
 * Kaynak ve hedef sponsorluk ad listelerini kıyaslar.
 * @returns {{added:string[], removed:string[], kept:string[]}}
 *   added   = kaynakta olup hedefte olmayan (eklenecek)
 *   removed = hedefte olup kaynakta olmayan (silinecek)
 *   kept    = her ikisinde de olan
 */
export function diffCampaignNames(sourceNames = [], targetNames = []) {
  const src = new Set(sourceNames);
  const tgt = new Set(targetNames);
  const added = [...src].filter((n) => !tgt.has(n));
  const removed = [...tgt].filter((n) => !src.has(n));
  const kept = [...src].filter((n) => tgt.has(n));
  return { added, removed, kept };
}

// ── Hata ayıklama (capacity_exceeded) ────────────────────────────────────────

/**
 * Bir hata/yanıt gövdesinden kapasite aşımı bilgisini çıkarır.
 * @returns {null | {code, detail, conflicts, rejected, skipped}}
 */
export function extractCapacityError(err) {
  const data = err?.response?.data ?? err?.data ?? err ?? null;
  if (!data || data.code !== 'capacity_exceeded') return null;
  return {
    code: 'capacity_exceeded',
    detail: data.detail || 'Kapasite aşıldı.',
    conflicts: Array.isArray(data.conflicts) ? data.conflicts : [],
    rejected: Array.isArray(data.rejected) ? data.rejected : [],
    skipped: Array.isArray(data.skipped_already_assigned) ? data.skipped_already_assigned : [],
  };
}

// ── Tarih yardımcıları ───────────────────────────────────────────────────────

/** Europe/Istanbul bugünü "YYYY-MM-DD" formatında döner. */
export function getIstanbulToday() {
  try {
    return new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Istanbul' }).format(new Date());
  } catch {
    return new Date().toISOString().slice(0, 10);
  }
}

/** Medya URL'si video mu? (uzantı + query string dayanıklı) */
export function isVideoUrl(url) {
  if (!url) return false;
  return /\.(mp4|webm|ogg|mov)(\?|$)/i.test(url);
}

export function useSponsorship() {
  return {
    WEEKDAYS,
    weekdayLabel,
    weekdaysText,
    hhmmToMinutes,
    minutesToHHMM,
    secondToHHMMSS,
    windowSeconds,
    maxCountHint,
    validateRow,
    rowToPayload,
    heatmapColor,
    groupByHour,
    hourTimeline,
    diffCampaignNames,
    extractCapacityError,
    getIstanbulToday,
    isVideoUrl,
  };
}

export default useSponsorship;
