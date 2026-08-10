// Saat-mutlak DOOH slot cozumleyici.
//
// `estimated_start_offset_seconds` saat icinde 0..3599 arasi MUTLAK ofsettir
// (backend: loop_index*loop_seconds + slot_offset). Bir PlaylistItem yalniz
// kendi [offset, offset+duration_seconds) araliginda aktiftir. Bu araligin
// disinda o item aktif DEGILDIR; hicbir item bir sonraki slota kadar
// uzatilmaz. Aktif item yoksa cagiran taraf fallback (AdPromo) gosterir.
//
// Kural tamamen playlist verisine baglidir: creative/HouseAd suresi, adet ve
// ofsetler backend kaydindan gelir; burada hicbir sure/frekans sabiti yoktur.

export const HOUR_SECONDS = 3600;

function offsetOf(it) {
  return it?.estimated_start_offset_seconds ?? 0;
}

function durationOf(it) {
  return it?.duration_seconds ?? 0;
}

/**
 * Duvar saatine gore saat-ici konum (0..3599 saniye).
 * Europe/Istanbul tam-saat (UTC+3) offseti oldugundan `epoch % 3600` yerel
 * saat-ici saniyeye esittir; ayri bir TZ donusumu gerekmez.
 * @param {number} nowMs
 * @returns {number} 0..3599
 */
export function currentHourPosition(nowMs = Date.now()) {
  return Math.floor(nowMs / 1000) % HOUR_SECONDS;
}

/**
 * `pos` saat-ici konumunda GERCEKTEN aktif olan PlaylistItem'i dondurur.
 * Aktiflik: `offset <= pos < offset + duration_seconds`. Aktif item yoksa null.
 * Cakisan (ayni pos'u kapsayan) birden fazla item varsa en gec baslayan secilir.
 * @param {Array} items
 * @param {number} pos
 * @returns {object|null}
 */
export function resolveActiveItem(items, pos) {
  if (!Array.isArray(items)) return null;
  let best = null;
  for (const it of items) {
    const off = offsetOf(it);
    const dur = durationOf(it);
    if (dur > 0 && off <= pos && pos < off + dur) {
      if (best === null || off > offsetOf(best)) best = it;
    }
  }
  return best;
}

/**
 * `pos`'tan sonra aktif-item durumunun degisecegi ilk sinira kadar saniye.
 * Sinirlar her item'in basi (offset) ve sonu (offset+duration). Hicbir sinir
 * kalmazsa saat sonunda (HOUR_SECONDS) sarilir. En az 1 saniye doner.
 * @param {Array} items
 * @param {number} pos
 * @param {number} hourSeconds
 * @returns {number} saniye (>=1)
 */
export function secondsUntilBoundary(items, pos, hourSeconds = HOUR_SECONDS) {
  let next = hourSeconds;
  if (Array.isArray(items)) {
    for (const it of items) {
      const off = offsetOf(it);
      const end = off + durationOf(it);
      if (off > pos && off < next) next = off;
      if (end > pos && end < next) next = end;
    }
  }
  return Math.max(1, next - pos);
}
