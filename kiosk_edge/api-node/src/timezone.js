// Kiosk saat dilimi yardimcilari.
//
// Backend (Django, USE_TZ=True, TIME_ZONE="Europe/Istanbul") playlist'leri
// `target_hour` 0-23 olarak YEREL (Istanbul) saate gore uretir. Kiosk cihazi
// UTC veya farkli bir TZ ile calisiyor olabilecegi icin, oynatilacak playlist'i
// dogru secebilmek adina duvar saatini DAIMA Europe/Istanbul'a gore hesaplariz.
//
// (Turkiye 2016'dan beri sabit UTC+3; yine de DST'ye dayanikli olsun diye
//  Intl.DateTimeFormat ile cihazdan bagimsiz hesaplanir.)

const TZ = 'Europe/Istanbul';

const _fmt = new Intl.DateTimeFormat('en-CA', {
  timeZone: TZ,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  hour12: false,
});

/**
 * Verilen an icin Istanbul yerel tarih + saatini doner.
 * @param {Date} [d=new Date()]
 * @returns {{ date: string, hour: number }} date "YYYY-MM-DD", hour 0-23
 */
export function istanbulNow(d = new Date()) {
  const parts = _fmt.formatToParts(d);
  const get = (type) => parts.find((p) => p.type === type)?.value;
  let hour = Number.parseInt(get('hour'), 10);
  if (hour === 24) hour = 0; // bazi motorlar gece yarisini "24" verir
  return { date: `${get('year')}-${get('month')}-${get('day')}`, hour };
}
