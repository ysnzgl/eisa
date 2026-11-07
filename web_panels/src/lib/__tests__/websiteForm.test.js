/**
 * lib/websiteForm.js — şema varsayılanları, doğrulama, hata ağacı, slug.
 */
import { describe, it, expect } from 'vitest';
import {
  varsayilanVeri, veriyiTamamla, veriyiDogrula, hataVarMi, hatalariAgacaCevir, hataMesajlari,
  altHata, slugOlustur, izinliHref, blokOzeti, htmlMedyaMutlak, htmlMedyaGoreli, medyaDosyaHatasi, GENEL_HATA,
} from '../websiteForm';

const KARTLAR = {
  ad: 'kartlar', etiket: 'Kartlar', tur: 'liste', min_adet: 1, max_adet: 3,
  alanlar: [
    { ad: 'ikon', etiket: 'İkon', tur: 'ikon', zorunlu: true, varsayilan: 'Sparkle' },
    { ad: 'baslik', etiket: 'Başlık', tur: 'metin', zorunlu: true, max_uzunluk: 10 },
  ],
};
const ALANLAR = [
  { ad: 'baslik', etiket: 'Başlık', tur: 'metin', zorunlu: true, varsayilan: '' },
  { ad: 'sutun', etiket: 'Sütun', tur: 'secim', varsayilan: 3, secenekler: [{ deger: 2, etiket: '2' }, { deger: 3, etiket: '3' }] },
  { ad: 'buton', etiket: 'Buton', tur: 'buton' },
  { ad: 'gorsel', etiket: 'Görsel', tur: 'medya' },
  KARTLAR,
];

describe('varsayılanlar', () => {
  it('varsayilanVeri liste için min_adet kadar öğe üretir', () => {
    const v = varsayilanVeri(ALANLAR);
    expect(v.baslik).toBe('');
    expect(v.sutun).toBe(3);
    expect(v.buton).toBeNull(); // opsiyonel buton boşken null (backend boş nesneyi reddeder)
    expect(varsayilanVeri([{ ad: 'b', tur: 'buton', zorunlu: true }]).b).toEqual({ etiket: '', href: '', stil: 'birincil' });
    expect(v.gorsel).toBeNull();
    expect(v.kartlar).toEqual([{ ikon: 'Sparkle', baslik: '' }]);
  });
  it('veriyiTamamla eksik alanları ve liste öğelerini doldurur', () => {
    const v = veriyiTamamla(ALANLAR, { baslik: 'X', kartlar: [{ baslik: 'A' }] });
    expect(v.baslik).toBe('X');
    expect(v.kartlar[0]).toEqual({ baslik: 'A', ikon: 'Sparkle' });
    expect(v.buton).toBeNull();
  });
  it('butonlar listesindeki href (metin) alanı da bağlantı kuralıyla doğrulanır', () => {
    const butonlar = { ad: 'butonlar', tur: 'liste', alanlar: [
      { ad: 'etiket', tur: 'metin', zorunlu: true }, { ad: 'href', tur: 'metin', zorunlu: true },
    ] };
    const h = veriyiDogrula([butonlar], { butonlar: [{ etiket: 'A', href: 'javascript:x' }, { etiket: 'B', href: '/#pilot' }] });
    expect(h.butonlar['0'].href[0]).toMatch(/ile başlamalıdır/);
    expect(h.butonlar['1']).toBeUndefined();
  });
});

describe('doğrulama', () => {
  it('zorunlu alan ve iç içe liste hataları', () => {
    const h = veriyiDogrula(ALANLAR, {
      baslik: ' ', sutun: 3, buton: { etiket: 'Git', href: 'javascript:alert(1)' }, gorsel: null,
      kartlar: [{ ikon: 'Sparkle', baslik: 'Uzun bir başlık' }, { ikon: '', baslik: '' }],
    });
    expect(h.baslik).toEqual(['Bu alan zorunludur.']);
    expect(h.buton.href[0]).toMatch(/ile başlamalıdır/);
    expect(h.kartlar['0'].baslik[0]).toMatch(/En fazla 10/);
    expect(h.kartlar['1'].ikon).toBeTruthy();
    expect(h.kartlar['1'].baslik).toEqual(['Bu alan zorunludur.']);
    expect(hataVarMi(h)).toBe(true);
  });
  it('liste min/max adet', () => {
    expect(veriyiDogrula([KARTLAR], { kartlar: [] }).kartlar[GENEL_HATA][0]).toMatch(/En az 1/);
    const dort = Array.from({ length: 4 }, () => ({ ikon: 'Star', baslik: 'a' }));
    expect(hataMesajlari(veriyiDogrula([KARTLAR], { kartlar: dort }).kartlar)[0]).toMatch(/En fazla 3/);
  });
  it('geçerli veri hata üretmez', () => {
    const h = veriyiDogrula(ALANLAR, {
      baslik: 'Merhaba', sutun: 2, buton: { etiket: '', href: '' }, gorsel: null,
      kartlar: [{ ikon: 'Star', baslik: 'Kısa' }],
    });
    expect(hataVarMi(h)).toBe(false);
  });
});

describe('hata ağacı', () => {
  it('noktalı anahtarları ve DRF liste hatalarını iç içe nesneye çevirir', () => {
    const a = hatalariAgacaCevir({ 'bloklar.2.baslik': ['Zorunlu'] });
    expect(a.bloklar['2'].baslik).toEqual(['Zorunlu']);
    const b = hatalariAgacaCevir({ bloklar: [{}, { kartlar: [{}, { baslik: ['X'] }] }] });
    expect(altHata(altHata(altHata(b.bloklar, 1).kartlar, 1), 'baslik')).toEqual(['X']);
    const c = hatalariAgacaCevir({ bloklar: { 2: { baslik: ['Bu alan zorunludur.'] } } });
    expect(c.bloklar['2'].baslik).toEqual(['Bu alan zorunludur.']);
  });
});

describe('slug ve yardımcılar', () => {
  it('Türkçe karakterleri dönüştürür', () => {
    expect(slugOlustur('Reçete Bekleme Süresi Neden Bir Fırsat?')).toBe('recete-bekleme-suresi-neden-bir-firsat');
    expect(slugOlustur('İLAÇ & Şifalı Öğüt')).toBe('ilac-ve-sifali-ogut');
    expect(slugOlustur('  --Çağrı--  ')).toBe('cagri');
  });
  it('izinliHref', () => {
    expect(izinliHref('/#pilot')).toBe(true);
    expect(izinliHref('#sss')).toBe(true);
    expect(izinliHref('https://wa.me/90')).toBe(true);
    expect(izinliHref('mailto:a@b.c')).toBe(true);
    expect(izinliHref('javascript:alert(1)')).toBe(false);
    expect(izinliHref('http://x.com')).toBe(false);
    expect(izinliHref('//evil.com')).toBe(false);
  });
  it('blokOzeti başlık veya HTML metninden özet çıkarır', () => {
    expect(blokOzeti({ baslik: 'Merhaba' })).toBe('Merhaba');
    expect(blokOzeti({ icerik_html: '<p>KVKK <b>metni</b></p>' })).toBe('KVKK metni');
  });
  it('zengin metin medya yolları mutlak ↔ göreli', () => {
    const goreli = '<img src="/api/media/website/a.webp">';
    const mutlak = htmlMedyaMutlak(goreli, 'https://api.eisa.com.tr');
    expect(mutlak).toBe('<img src="https://api.eisa.com.tr/api/media/website/a.webp">');
    expect(htmlMedyaGoreli(mutlak, 'https://api.eisa.com.tr')).toBe(goreli);
    expect(htmlMedyaMutlak(goreli, '')).toBe(goreli);
  });
  it('medya dosya ön kontrolü (tip / 10 MB / SVG)', () => {
    expect(medyaDosyaHatasi({ name: 'a.svg', type: 'image/svg+xml', size: 10 })).toMatch(/yalnızca/);
    expect(medyaDosyaHatasi({ name: 'a.png', type: 'image/png', size: 11 * 1024 * 1024 })).toMatch(/10 MB/);
    expect(medyaDosyaHatasi({ name: 'a.webp', type: 'image/webp', size: 1000 })).toBeNull();
  });
});
