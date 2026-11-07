/**
 * Web Sitesi araması — ortak yardımcılar.
 *  - normalize(): backend (services/arama.py) ile aynı Türkçe katlama; uzunluk korunur.
 *  - hedefRotasi(): arama sonucunu ilgili editörün adresine çevirir.
 *  - alanaOdaklan(): editör yüklendikten sonra alanı bulur, görünür yapar, vurgular,
 *    imleci koyar ve (metin alanlarında) aranan ifadeyi seçili getirir.
 */
import { nextTick } from 'vue';

const KATLA = { ç: 'c', ğ: 'g', ı: 'i', ö: 'o', ş: 's', ü: 'u', â: 'a', î: 'i', û: 'u' };

/** Türkçe küçük harf + aksan katlama (karakter başına 1 karakter → konumlar korunur). */
export function normalize(metin) {
  let sonuc = '';
  for (const c of String(metin ?? '')) {
    let k;
    if (c === 'İ') k = 'i';
    else if (c === 'I') k = 'ı';
    else {
      const l = c.toLocaleLowerCase('tr-TR');
      k = l.length === 1 ? l : c;
    }
    sonuc += KATLA[k] ?? k;
  }
  return sonuc;
}

/** Metinde aranan ifadenin ilk konumu: { bas, son } | null */
export function eslesmeKonumu(metin, aranan) {
  const igne = normalize(aranan).trim();
  if (!igne) return null;
  const i = normalize(metin).indexOf(igne);
  return i < 0 ? null : { bas: i, son: i + igne.length };
}

/** Arama sonucu → vue-router konumu (query: alan, q ve ekrana özgü kimlikler). */
export function hedefRotasi(sonuc, q) {
  const h = sonuc?.hedef || {};
  const query = { alan: h.alan, q };
  switch (h.ekran) {
    case 'sayfa':
      if (h.blok_id) query.blok = String(h.blok_id);
      return { path: `/admin/web-sitesi/sayfalar/${h.sayfa_id}`, query };
    case 'blog':
      return { path: `/admin/web-sitesi/blog/${h.yazi_id}`, query };
    case 'menu':
      return { path: '/admin/web-sitesi/menuler', query: { ...query, konum: h.konum, oge: String(h.oge_id) } };
    case 'ayarlar':
      return { path: '/admin/web-sitesi/ayarlar', query };
    case 'blog_kategori':
      return { path: '/admin/web-sitesi/blog', query: { ...query, kategori: String(h.kategori_id) } };
    case 'medya':
      // Medya listesi Türkçe katlama yapmaz; metindeki gerçek eşleşme ile filtrelenir.
      return { path: '/admin/web-sitesi/medya', query: { q: sonuc.parca?.eslesen || q, medya: String(h.medya_id) } };
    default:
      return { path: '/admin/web-sitesi' };
  }
}

function bul(secici) {
  try {
    return document.querySelector(secici);
  } catch {
    return null;
  }
}

/**
 * Alanı bul → kaydır → vurgula → odakla → aranan ifadeyi seç.
 * `seciciler`: denenecek CSS seçicileri (ilk bulunan kullanılır). Veri yolu verilirse
 * (`[data-alan-yolu="kartlar.1.metin"]`) bulunamazsa üst yollar sırayla denenir.
 */
export async function alanaOdaklan({ seciciler = [], veriYolu = '', aranan = '' } = {}) {
  const adaylar = [...seciciler];
  if (veriYolu) {
    const parca = veriYolu.split('.');
    for (let n = parca.length; n > 0; n--) adaylar.push(`[data-alan-yolu="${parca.slice(0, n).join('.')}"]`);
  }
  // Liste öğeleri açılırken / çekmece animasyonunda DOM birkaç karede oturur.
  let el = null;
  for (let deneme = 0; deneme < 12 && !el; deneme++) {
    await nextTick();
    el = adaylar.map(bul).find(Boolean) || null;
    if (!el) await new Promise((r) => setTimeout(r, 60));
  }
  if (!el) return false;

  const kap = el.closest('.ws-alan') || el;
  kap.scrollIntoView({ behavior: 'smooth', block: 'center' });
  kap.classList.remove('ws-alan--arama-vurgu');
  void kap.offsetWidth; // animasyonu yeniden başlat
  kap.classList.add('ws-alan--arama-vurgu');
  setTimeout(() => kap.classList.remove('ws-alan--arama-vurgu'), 2600);

  const giris = el.matches('input, textarea, [contenteditable="true"]')
    ? el
    : el.querySelector('input:not([type="hidden"]):not([type="checkbox"]), textarea, [contenteditable="true"]');
  if (giris) {
    giris.focus({ preventScroll: true });
    if (aranan && (giris.tagName === 'INPUT' || giris.tagName === 'TEXTAREA')) {
      const k = eslesmeKonumu(giris.value, aranan);
      if (k) giris.setSelectionRange(k.bas, k.son);
    }
  }
  return true;
}
/**
 * Basit form ekranları için: route.query.alan → harita[alan] seçicisi ile alana odaklan.
 * `harita`: { alanAdi: '#element-id' | '[data-alan-yolu="..."]' }
 */
export function sorgudanOdaklan(query, harita) {
  const alan = typeof query?.alan === 'string' ? query.alan : '';
  if (!alan || !harita[alan]) return Promise.resolve(false);
  return alanaOdaklan({ seciciler: [harita[alan]], aranan: typeof query.q === 'string' ? query.q : '' });
}