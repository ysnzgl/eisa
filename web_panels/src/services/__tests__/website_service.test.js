/**
 * website.js servis katmanı — CONTRACT §5 admin uçları için URL/metot/gövde testleri.
 * axios mock'lanır (dooh_service.test.js ile aynı desen).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('axios', async () => {
  const mockHttp = {
    defaults: { baseURL: '' },
    get: vi.fn(() => Promise.resolve({ data: {} })),
    post: vi.fn(() => Promise.resolve({ data: {} })),
    patch: vi.fn(() => Promise.resolve({ data: {} })),
    put: vi.fn(() => Promise.resolve({ data: {} })),
    delete: vi.fn(() => Promise.resolve({ data: {} })),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  };
  return { default: { create: vi.fn(() => mockHttp) }, __mockHttp: mockHttp };
});

import * as ws from '../website.js';

const B = '/api/website/admin';
let http;
beforeEach(async () => {
  vi.clearAllMocks();
  const { default: axiosMock } = await import('axios');
  http = axiosMock.create();
  http.defaults.baseURL = '';
});

describe('medyaUrl', () => {
  it('same-origin iken göreli yolu korur', () => {
    expect(ws.medyaUrl('/api/media/website/2026/11/a.webp')).toBe('/api/media/website/2026/11/a.webp');
  });
  it('API_BASE varsa öne ekler (sondaki / temizlenir)', () => {
    http.defaults.baseURL = 'https://api.eisa.com.tr/';
    expect(ws.medyaUrl('/api/media/website/x.png')).toBe('https://api.eisa.com.tr/api/media/website/x.png');
  });
  it('boş ve mutlak adresleri dönüştürmez', () => {
    expect(ws.medyaUrl('')).toBe('');
    expect(ws.medyaUrl(null)).toBe('');
    expect(ws.medyaUrl('https://cdn.test/a.png')).toBe('https://cdn.test/a.png');
  });
});

describe('Sayfalar', () => {
  it('listSayfalar GET sayfalar/ ve düz dizi döner', async () => {
    http.get.mockResolvedValueOnce({ data: [{ id: 1, slug: 'anasayfa' }] });
    const r = await ws.listSayfalar();
    expect(http.get).toHaveBeenCalledWith(`${B}/sayfalar/`);
    expect(r).toEqual([{ id: 1, slug: 'anasayfa' }]);
  });
  it('createSayfa POST (sessiz — alan hataları ekranda gösterilir)', () => {
    ws.createSayfa({ slug: 'x', baslik: 'X' });
    expect(http.post).toHaveBeenCalledWith(`${B}/sayfalar/`, { slug: 'x', baslik: 'X' }, { __silent: true });
  });
  it('updateSayfa PATCH sayfalar/{id}/ surum ile', () => {
    ws.updateSayfa(5, { baslik: 'Y', surum: 3 });
    expect(http.patch).toHaveBeenCalledWith(`${B}/sayfalar/5/`, { baslik: 'Y', surum: 3 }, { __silent: true });
  });
  it('saveBloklar PUT sayfalar/{id}/bloklar/ { surum, bloklar }', () => {
    const bloklar = [{ tip: 'hero', veri: {}, gorunur: true, anchor_id: '' }];
    ws.saveBloklar(7, 4, bloklar);
    expect(http.put).toHaveBeenCalledWith(`${B}/sayfalar/7/bloklar/`, { surum: 4, bloklar }, { __silent: true });
  });
  it('yayinla / yayindan-kaldir / onizleme / revizyonlar / geri-al', () => {
    ws.yayinlaSayfa(7, 'not');
    expect(http.post).toHaveBeenCalledWith(`${B}/sayfalar/7/yayinla/`, { not: 'not' });
    ws.yayindanKaldirSayfa(7);
    expect(http.post).toHaveBeenCalledWith(`${B}/sayfalar/7/yayindan-kaldir/`);
    ws.sayfaOnizleme(7);
    expect(http.post).toHaveBeenCalledWith(`${B}/sayfalar/7/onizleme/`);
    ws.listRevizyonlar(7);
    expect(http.get).toHaveBeenCalledWith(`${B}/sayfalar/7/revizyonlar/`);
    ws.geriAlRevizyon(7, 2);
    expect(http.post).toHaveBeenCalledWith(`${B}/sayfalar/7/revizyonlar/2/geri-al/`);
  });
  it('deleteSayfa DELETE', () => {
    ws.deleteSayfa(9);
    expect(http.delete).toHaveBeenCalledWith(`${B}/sayfalar/9/`);
  });
});

describe('Blok tipleri, menüler, ayarlar', () => {
  it('listBlokTipleri GET blok-tipleri/', () => {
    ws.listBlokTipleri();
    expect(http.get).toHaveBeenCalledWith(`${B}/blok-tipleri/`);
  });
  it('saveMenu PUT menuler/{konum}/ ağacın tamamı', () => {
    ws.saveMenu('footer_alt', [{ etiket: 'KVKK' }]);
    expect(http.put).toHaveBeenCalledWith(`${B}/menuler/footer_alt/`, [{ etiket: 'KVKK' }], { __silent: true });
  });
  it('getAyarlar / updateAyarlar', () => {
    ws.getAyarlar();
    expect(http.get).toHaveBeenCalledWith(`${B}/ayarlar/`);
    ws.updateAyarlar({ site_adi: 'e-isa' });
    expect(http.patch).toHaveBeenCalledWith(`${B}/ayarlar/`, { site_adi: 'e-isa' }, { __silent: true });
  });
});

describe('Blog', () => {
  it('kategoriler CRUD', () => {
    ws.listBlogKategorileri();
    expect(http.get).toHaveBeenCalledWith(`${B}/blog/kategoriler/`);
    ws.createBlogKategori({ ad: 'A' });
    expect(http.post).toHaveBeenCalledWith(`${B}/blog/kategoriler/`, { ad: 'A' });
    ws.updateBlogKategori(2, { sira: 1 });
    expect(http.patch).toHaveBeenCalledWith(`${B}/blog/kategoriler/2/`, { sira: 1 });
    ws.deleteBlogKategori(2);
    expect(http.delete).toHaveBeenCalledWith(`${B}/blog/kategoriler/2/`);
  });
  it('yazılar ve önizleme', () => {
    ws.listBlogYazilari({ durum: 'taslak' });
    expect(http.get).toHaveBeenCalledWith(`${B}/blog/yazilar/`, { params: { durum: 'taslak' } });
    ws.updateBlogYazisi(3, { surum: 1 });
    expect(http.patch).toHaveBeenCalledWith(`${B}/blog/yazilar/3/`, { surum: 1 }, { __silent: true });
    ws.blogYazisiOnizleme(3);
    expect(http.post).toHaveBeenCalledWith(`${B}/blog/yazilar/3/onizleme/`);
  });
});

describe('Medya', () => {
  it('listMedya {count, results} döner', async () => {
    http.get.mockResolvedValueOnce({ data: { count: 1, results: [{ id: 1 }] } });
    const r = await ws.listMedya({ q: 'kiosk', page: 2, page_size: 24 });
    expect(http.get).toHaveBeenCalledWith(`${B}/medya/`, { params: { q: 'kiosk', page: 2, page_size: 24 } });
    expect(r).toEqual({ count: 1, results: [{ id: 1 }] });
  });
  it('uploadMedya multipart dosya + alt gönderir', async () => {
    const dosya = new File(['x'], 'a.png', { type: 'image/png' });
    await ws.uploadMedya(dosya, 'Kiosk');
    const [url, form, config] = http.post.mock.calls[0];
    expect(url).toBe(`${B}/medya/`);
    expect(form).toBeInstanceOf(FormData);
    expect(form.get('dosya')).toBeTruthy();
    expect(form.get('alt')).toBe('Kiosk');
    expect(config.__silent).toBe(true);
  });
  it('updateMedya PATCH alt, deleteMedya DELETE', () => {
    ws.updateMedya(4, { alt: 'x' });
    expect(http.patch).toHaveBeenCalledWith(`${B}/medya/4/`, { alt: 'x' });
    ws.deleteMedya(4);
    expect(http.delete).toHaveBeenCalledWith(`${B}/medya/4/`);
  });
});

describe('Başvurular', () => {
  it('listBasvurular filtre parametreleri ve yeni_sayisi', async () => {
    http.get.mockResolvedValueOnce({ data: { count: 2, results: [{}, {}], yeni_sayisi: 1 } });
    const r = await ws.listBasvurular({ tip: 'pilot', durum: 'yeni', q: 'a', page: 1, page_size: 24 });
    expect(http.get).toHaveBeenCalledWith(`${B}/basvurular/`, { params: { tip: 'pilot', durum: 'yeni', q: 'a', page: 1, page_size: 24 } });
    expect(r.yeni_sayisi).toBe(1);
  });
  it('updateBasvuru PATCH durum/notlar/atanan_id', () => {
    ws.updateBasvuru(8, { durum: 'incelendi', notlar: 'n', atanan_id: 1 });
    expect(http.patch).toHaveBeenCalledWith(`${B}/basvurular/8/`, { durum: 'incelendi', notlar: 'n', atanan_id: 1 });
  });
  it('getBasvuruOzet sessiz çağrılır ve { yeni } döner', async () => {
    http.get.mockResolvedValueOnce({ data: { yeni: 3 } });
    const r = await ws.getBasvuruOzet();
    expect(http.get).toHaveBeenCalledWith(`${B}/basvurular/ozet/`, { __silent: true });
    expect(r).toEqual({ yeni: 3 });
  });
});
