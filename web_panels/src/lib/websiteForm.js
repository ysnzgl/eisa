/**
 * Web Sitesi modülü — saf yardımcılar (şema tabanlı form, doğrulama, slug, özet).
 *
 * Blok şeması `GET /api/website/admin/blok-tipleri/` ile gelir (CONTRACT §5 "Alan").
 * Buradaki fonksiyonlar DOM'a bağımlı değildir; birim testleri kolaydır.
 */
import { IKON_ADLARI } from '../data/websiteIkonlari';

export const SLUG_REGEX = /^[a-z0-9-]+$/;
// Backend ANCHOR_RE ile aynı: harf/rakamla başlar; küçük harf, rakam, tire, alt çizgi.
export const ANCHOR_REGEX = /^[a-z0-9][a-z0-9_-]*$/;
export const AYRILMIS_SLUGLAR = ['blog', 'api', '_next', 'admin'];
export const KORUMALI_SAYFALAR = ['anasayfa', 'kvkk', 'cerez-politikasi'];

export const IZINLI_MEDYA_TIPLERI = ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/avif'];
export const MAKS_MEDYA_BOYUTU = 10 * 1024 * 1024; // 10 MB

export const BUTON_STILLERI = [
  { deger: 'birincil', etiket: 'Birincil (kırmızı)' },
  { deger: 'ikincil', etiket: 'İkincil (çerçeveli)' },
  { deger: 'hayalet', etiket: 'Hayalet (sade)' },
];

// Genel (alan dışı) hata anahtarı — liste düzeyi mesajları için.
export const GENEL_HATA = '_genel';

// Şemada "metin" türünde gelen ama bağlantı içeren alan adları (backend `link=True`).
const BAGLANTI_ALANLARI = ['href', 'url'];
const HREF_HATA = 'Bağlantı /, #, https://, mailto: veya tel: ile başlamalıdır.';

export function klonla(v) {
  if (v === undefined) return undefined;
  return JSON.parse(JSON.stringify(v));
}

// ── Varsayılanlar ─────────────────────────────────────────────────────────────

export function varsayilanDeger(alan) {
  const v = alan?.varsayilan;
  if (alan?.tur === 'liste') {
    if (Array.isArray(v)) return klonla(v).map((o) => veriyiTamamla(alan.alanlar || [], o));
    const adet = Math.max(0, Number(alan.min_adet) || 0);
    return Array.from({ length: adet }, () => varsayilanVeri(alan.alanlar || []));
  }
  // Buton: opsiyonelse boş değer null'dır (backend boş nesneyi zorunlu alan hatasıyla reddeder).
  if (alan?.tur === 'buton') {
    if (v && typeof v === 'object') return { etiket: '', href: '', stil: 'birincil', ...klonla(v) };
    return alan.zorunlu ? { etiket: '', href: '', stil: 'birincil' } : null;
  }
  if (v !== undefined && v !== null) return klonla(v);
  switch (alan?.tur) {
    case 'metin':
    case 'uzun_metin':
    case 'zengin_metin':
    case 'ikon':
      return '';
    case 'sayi':
      return null;
    case 'bool':
      return false;
    case 'secim':
      return alan.secenekler?.[0]?.deger ?? '';
    case 'medya':
      return null;
    default:
      return null;
  }
}

export function varsayilanVeri(alanlar = []) {
  const veri = {};
  for (const alan of alanlar) veri[alan.ad] = varsayilanDeger(alan);
  return veri;
}

/**
 * Sunucudan gelen `veri`deki eksik alanları varsayılanla doldurur (liste
 * öğeleri dahil). Bilinmeyen anahtarlar korunur; backend kayıtta atar.
 */
export function veriyiTamamla(alanlar = [], veri) {
  const sonuc = veri && typeof veri === 'object' && !Array.isArray(veri) ? { ...veri } : {};
  for (const alan of alanlar) {
    const mevcut = sonuc[alan.ad];
    if (mevcut === undefined) {
      sonuc[alan.ad] = varsayilanDeger(alan);
    } else if (alan.tur === 'liste') {
      sonuc[alan.ad] = Array.isArray(mevcut)
        ? mevcut.map((o) => veriyiTamamla(alan.alanlar || [], o))
        : varsayilanDeger(alan);
    } else if (alan.tur === 'buton' && mevcut) {
      sonuc[alan.ad] = { etiket: '', href: '', stil: 'birincil', ...mevcut };
    }
  }
  return sonuc;
}

// ── Doğrulama ─────────────────────────────────────────────────────────────────

/** CONTRACT §2 Buton.href: `/`, `#`, `https://`, `mailto:`, `tel:` (wa.me https'tir). */
export function izinliHref(href) {
  const h = String(href || '').trim();
  if (!h) return false;
  if (h.startsWith('//')) return false;
  return /^(\/|#|https:\/\/|mailto:|tel:)/i.test(h);
}

export function htmlMetin(html) {
  return String(html || '')
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function _bos(v) {
  return v === undefined || v === null || (typeof v === 'string' && v.trim() === '');
}

/**
 * Tek alanı doğrular. Dönüş: `null` (hata yok) | `string[]` | nesne (iç içe).
 */
export function alaniDogrula(alan, deger) {
  const zorunlu = !!alan.zorunlu;
  switch (alan.tur) {
    case 'metin':
    case 'uzun_metin': {
      if (zorunlu && _bos(deger)) return ['Bu alan zorunludur.'];
      if (alan.max_uzunluk && String(deger || '').length > alan.max_uzunluk) {
        return [`En fazla ${alan.max_uzunluk} karakter olabilir.`];
      }
      // Bağlantı alanları (ör. butonlar[].href) — backend aynı şema kontrolünü yapar.
      if (BAGLANTI_ALANLARI.includes(alan.ad) && !_bos(deger) && !izinliHref(deger)) return [HREF_HATA];
      return null;
    }
    case 'zengin_metin':
      if (zorunlu && !htmlMetin(deger)) return ['Bu alan zorunludur.'];
      return null;
    case 'sayi': {
      if (_bos(deger)) return zorunlu ? ['Bu alan zorunludur.'] : null;
      const n = Number(deger);
      if (Number.isNaN(n)) return ['Geçerli bir sayı girin.'];
      if (alan.min !== undefined && alan.min !== null && n < alan.min) return [`En az ${alan.min} olmalıdır.`];
      if (alan.max !== undefined && alan.max !== null && n > alan.max) return [`En fazla ${alan.max} olabilir.`];
      return null;
    }
    case 'bool':
      return null;
    case 'secim': {
      if (_bos(deger)) return zorunlu ? ['Bir seçim yapın.'] : null;
      const secenekler = alan.secenekler || [];
      if (secenekler.length && !secenekler.some((s) => String(s.deger) === String(deger))) {
        return ['Geçersiz seçim.'];
      }
      return null;
    }
    case 'ikon':
      if (_bos(deger)) return zorunlu ? ['Bir ikon seçin.'] : null;
      if (!IKON_ADLARI.includes(deger)) return ['Geçersiz ikon.'];
      return null;
    case 'medya':
      if (zorunlu && !deger?.id) return ['Bir görsel seçin.'];
      return null;
    case 'buton': {
      const b = deger || {};
      const etiketVar = !_bos(b.etiket);
      const hrefVar = !_bos(b.href);
      if (!zorunlu && !etiketVar && !hrefVar) return null;
      const h = {};
      if (!etiketVar) h.etiket = ['Buton etiketi zorunludur.'];
      if (!hrefVar) h.href = ['Bağlantı zorunludur.'];
      else if (!izinliHref(b.href)) h.href = [HREF_HATA];
      return Object.keys(h).length ? h : null;
    }
    case 'liste': {
      const dizi = Array.isArray(deger) ? deger : [];
      const h = {};
      const genel = [];
      if (alan.min_adet && dizi.length < alan.min_adet) genel.push(`En az ${alan.min_adet} öğe eklenmelidir.`);
      if (alan.max_adet && dizi.length > alan.max_adet) genel.push(`En fazla ${alan.max_adet} öğe eklenebilir.`);
      if (genel.length) h[GENEL_HATA] = genel;
      dizi.forEach((oge, i) => {
        const oh = veriyiDogrula(alan.alanlar || [], oge);
        if (hataVarMi(oh)) h[String(i)] = oh;
      });
      return Object.keys(h).length ? h : null;
    }
    default:
      return null;
  }
}

/** Tüm alanları doğrular → `{ alan_adi: hata }` (hata yoksa boş nesne). */
export function veriyiDogrula(alanlar = [], veri = {}) {
  const hatalar = {};
  for (const alan of alanlar) {
    const h = alaniDogrula(alan, veri?.[alan.ad]);
    if (h) hatalar[alan.ad] = h;
  }
  return hatalar;
}

export function hataVarMi(h) {
  if (!h) return false;
  if (Array.isArray(h)) return h.some((x) => (typeof x === 'string' ? !!x : hataVarMi(x)));
  if (typeof h === 'object') return Object.values(h).some(hataVarMi);
  return !!h;
}

/**
 * Backend hata ağacını normalize eder:
 *  - `{"kartlar.0.baslik": [..]}` noktalı anahtarlar → iç içe nesne
 *  - `[{}, {baslik: [..]}]` (DRF ListField) → `{ "1": { baslik: [..] } }`
 *  - `{ alan: ["mesaj"] }` olduğu gibi kalır
 */
export function hatalariAgacaCevir(h) {
  if (h === null || h === undefined) return null;
  if (typeof h === 'string') return [h];
  if (Array.isArray(h)) {
    if (h.every((x) => typeof x === 'string')) return h;
    const nesne = {};
    const genel = [];
    h.forEach((x, i) => {
      if (typeof x === 'string') genel.push(x);
      else if (hataVarMi(x)) nesne[String(i)] = hatalariAgacaCevir(x);
    });
    if (genel.length) nesne[GENEL_HATA] = genel;
    return nesne;
  }
  if (typeof h === 'object') {
    const sonuc = {};
    for (const [anahtar, deger] of Object.entries(h)) {
      const parcalar = anahtar === 'non_field_errors' ? [GENEL_HATA] : anahtar.split('.');
      let hedef = sonuc;
      for (let i = 0; i < parcalar.length - 1; i += 1) {
        const p = parcalar[i];
        if (!hedef[p] || Array.isArray(hedef[p])) {
          const onceki = Array.isArray(hedef[p]) ? hedef[p] : null;
          hedef[p] = onceki ? { [GENEL_HATA]: onceki } : {};
        }
        hedef = hedef[p];
      }
      const son = parcalar[parcalar.length - 1];
      const normal = hatalariAgacaCevir(deger);
      if (hedef[son] && typeof hedef[son] === 'object' && !Array.isArray(hedef[son]) && Array.isArray(normal)) {
        hedef[son][GENEL_HATA] = normal;
      } else {
        hedef[son] = normal;
      }
    }
    return sonuc;
  }
  return null;
}

/** Bu düzeydeki mesajlar (string[]). */
export function hataMesajlari(h) {
  if (!h) return [];
  if (Array.isArray(h)) return h.filter((x) => typeof x === 'string');
  if (typeof h === 'object') return hataMesajlari(h[GENEL_HATA]);
  return [String(h)];
}

/** Alt alan / liste öğesi hatası. */
export function altHata(h, anahtar) {
  if (!h || typeof h !== 'object' || Array.isArray(h)) return null;
  return h[String(anahtar)] ?? null;
}

// ── Slug ──────────────────────────────────────────────────────────────────────

const TR_HARITA = {
  ç: 'c', Ç: 'c', ğ: 'g', Ğ: 'g', ı: 'i', I: 'i', İ: 'i', ö: 'o', Ö: 'o',
  ş: 's', Ş: 's', ü: 'u', Ü: 'u', â: 'a', Â: 'a', î: 'i', Î: 'i', û: 'u', Û: 'u',
};

/** Türkçe karakter dönüşümlü URL slug'ı: "Reçete Süresi?" → "recete-suresi". */
export function slugOlustur(metin, maks = 80) {
  return String(metin || '')
    .replace(/[çÇğĞıIİöÖşŞüÜâÂîÎûÛ]/g, (c) => TR_HARITA[c] || c)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/&/g, ' ve ')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, maks)
    .replace(/-+$/g, '');
}

// ── Blok özeti ────────────────────────────────────────────────────────────────

const OZET_ANAHTARLARI = ['baslik', 'rozet', 'ust_baslik', 'metin', 'aciklama', 'alt_metin', 'icerik_html'];

export function blokOzeti(veri, tipTanimi, maks = 70) {
  if (!veri || typeof veri !== 'object') return '';
  const adaylar = [...OZET_ANAHTARLARI];
  for (const alan of tipTanimi?.alanlar || []) {
    if (['metin', 'uzun_metin', 'zengin_metin'].includes(alan.tur) && !adaylar.includes(alan.ad)) {
      adaylar.push(alan.ad);
    }
  }
  for (const k of adaylar) {
    const v = veri[k];
    if (typeof v === 'string') {
      const t = htmlMetin(v);
      if (t) return t.length > maks ? `${t.slice(0, maks - 1)}…` : t;
    }
  }
  return '';
}

// ── Medya ─────────────────────────────────────────────────────────────────────

/** Medya kaydından CONTRACT §2 MediaRef nesnesi. */
export function medyaRef(m) {
  if (!m) return null;
  return {
    id: m.id,
    yol: m.yol,
    alt: m.alt ?? '',
    genislik: m.genislik ?? null,
    yukseklik: m.yukseklik ?? null,
    mime: m.mime ?? '',
  };
}

/** İstemci tarafı yükleme ön kontrolü. Hata mesajı veya null döner. */
export function medyaDosyaHatasi(dosya) {
  if (!dosya) return 'Dosya seçilmedi.';
  if (!IZINLI_MEDYA_TIPLERI.includes(dosya.type)) {
    return `${dosya.name}: yalnızca JPEG, PNG, WEBP, GIF veya AVIF yüklenebilir.`;
  }
  if (dosya.size > MAKS_MEDYA_BOYUTU) return `${dosya.name}: dosya 10 MB sınırını aşıyor.`;
  return null;
}

function _escapeRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Zengin metinde göreli medya yollarını (`/api/media/website/...`) editörde
 * görüntülenebilsin diye API_BASE ile mutlaklaştırır.
 */
export function htmlMedyaMutlak(html, base) {
  const b = String(base || '').replace(/\/+$/, '');
  if (!b || !html) return html || '';
  return html.replace(/(src=["'])(\/api\/media\/website\/)/g, `$1${b}$2`);
}

/** Kaydetmeden önce tersini uygular: backend yalnız göreli `/api/media/website/` kabul eder. */
export function htmlMedyaGoreli(html, base) {
  const b = String(base || '').replace(/\/+$/, '');
  if (!b || !html) return html || '';
  const re = new RegExp(`(src=["'])${_escapeRegex(b)}(\\/api\\/media\\/website\\/)`, 'g');
  return html.replace(re, '$1$2');
}

// ── Tarih ─────────────────────────────────────────────────────────────────────

export function tarihFormat(iso, saatli = true) {
  if (!iso) return '—';
  try {
    const opts = { day: '2-digit', month: 'short', year: 'numeric' };
    if (saatli) Object.assign(opts, { hour: '2-digit', minute: '2-digit' });
    return new Date(iso).toLocaleString('tr-TR', opts);
  } catch {
    return iso;
  }
}

/** ISO → `<input type="datetime-local">` değeri (yerel saat). */
export function isoToLocalInput(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

/** `datetime-local` değeri → ISO (UTC) ya da null. */
export function localInputToIso(v) {
  if (!v) return null;
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

export const SAYFA_DURUMLARI = {
  taslak: { etiket: 'Taslak', sinif: 'eisa-pill-muted' },
  yayinda: { etiket: 'Yayında', sinif: 'eisa-pill-success' },
  arsiv: { etiket: 'Arşiv', sinif: 'eisa-pill-warning' },
};
