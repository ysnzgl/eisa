/**
 * "Sitede ara" — normalizasyon, hedef rota ve arama penceresi.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { nextTick } from 'vue';

const push = vi.fn();
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }));
vi.mock('../../services/website', () => ({ siteAra: vi.fn() }));

import { normalize, eslesmeKonumu, hedefRotasi } from '../../lib/websiteArama';
import { siteAra } from '../../services/website';
import SiteArama from '../website/SiteArama.vue';

describe('websiteArama yardımcıları', () => {
  it('Türkçe katlama yapar ve uzunluğu korur (backend ile aynı)', () => {
    const metin = 'SAĞLIK İçin IŞIK Çözüm';
    expect(normalize(metin)).toBe('saglik icin isik cozum');
    expect(normalize(metin)).toHaveLength(metin.length);
  });

  it('eşleşme konumu orijinal metinde doğru aralığı verir', () => {
    const metin = 'Son karar ECZACIDA kalır';
    const k = eslesmeKonumu(metin, 'eczacida');
    expect(metin.slice(k.bas, k.son)).toBe('ECZACIDA');
    expect(eslesmeKonumu(metin, 'yok')).toBeNull();
  });

  it('her ekran için doğru rota üretir', () => {
    expect(hedefRotasi({ hedef: { ekran: 'sayfa', sayfa_id: 3, blok_id: 9, alan: 'kartlar.1.metin' } }, 'x'))
      .toEqual({ path: '/admin/web-sitesi/sayfalar/3', query: { alan: 'kartlar.1.metin', q: 'x', blok: '9' } });
    expect(hedefRotasi({ hedef: { ekran: 'sayfa', sayfa_id: 3, alan: 'meta:seo_baslik' } }, 'x').query.blok).toBeUndefined();
    expect(hedefRotasi({ hedef: { ekran: 'blog', yazi_id: 5, alan: 'ozet' } }, 'x').path).toBe('/admin/web-sitesi/blog/5');
    expect(hedefRotasi({ hedef: { ekran: 'menu', konum: 'footer', oge_id: 7, alan: 'etiket' } }, 'x').query)
      .toEqual({ alan: 'etiket', q: 'x', konum: 'footer', oge: '7' });
    expect(hedefRotasi({ hedef: { ekran: 'ayarlar', alan: 'adres' } }, 'x').path).toBe('/admin/web-sitesi/ayarlar');
    expect(hedefRotasi({ hedef: { ekran: 'blog_kategori', kategori_id: 4, alan: 'ad' } }, 'x'))
      .toEqual({ path: '/admin/web-sitesi/blog', query: { alan: 'ad', q: 'x', kategori: '4' } });
    // Medya: listede gerçek eşleşen metinle filtrelenir (backend Türkçe katlama yapmaz)
    expect(hedefRotasi({ hedef: { ekran: 'medya', medya_id: 9, alan: 'alt' }, parca: { eslesen: 'Vitrin' } }, 'vitrin'))
      .toEqual({ path: '/admin/web-sitesi/medya', query: { q: 'Vitrin', medya: '9' } });
  });
});

describe('SiteArama penceresi', () => {
  const YANIT = {
    q: 'pilot', toplam: 2, kesildi: false,
    sonuclar: [
      {
        grup: { tur: 'sayfa', id: 1, baslik: 'Anasayfa', slug: 'anasayfa', durum: 'yayinda' },
        blok: { id: 4, tip: 'hero', ad: 'Hero', sira: 1, gizli: false },
        konum: ['Hero', 'Butonlar', '1. öğe', 'Etiket'],
        hedef: { ekran: 'sayfa', sayfa_id: 1, blok_id: 4, alan: 'butonlar.0.etiket' },
        parca: { onceki: '', eslesen: 'Pilot', sonraki: ' Süreci İncele' }, adet: 1,
      },
      {
        grup: { tur: 'blog', id: 2, baslik: 'Pilot yazısı', slug: 'pilot', durum: 'taslak' },
        konum: ['Başlık'], hedef: { ekran: 'blog', yazi_id: 2, alan: 'baslik' },
        parca: { onceki: '', eslesen: 'Pilot', sonraki: ' yazısı' }, adet: 1,
      },
    ],
  };

  beforeEach(() => { vi.useFakeTimers(); push.mockClear(); siteAra.mockReset(); siteAra.mockResolvedValue(YANIT); });
  afterEach(() => { vi.useRealTimers(); document.body.innerHTML = ''; });

  async function acVeAra(w, q) {
    w.vm.ac();
    await nextTick();
    const girdi = document.querySelector('.ws-arama-girdi input');
    girdi.value = q;
    girdi.dispatchEvent(new Event('input'));
    await vi.advanceTimersByTimeAsync(300);
    await flushPromises();
    return girdi;
  }

  it('Ctrl+K ile açılır', async () => {
    const w = mount(SiteArama, { attachTo: document.body });
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }));
    await nextTick();
    expect(document.querySelector('.ws-arama')).not.toBeNull();
    w.unmount();
  });

  it('gecikmeli arar, grupları ve vurgulu parçayı gösterir', async () => {
    const w = mount(SiteArama, { attachTo: document.body });
    await acVeAra(w, 'pilot');
    expect(siteAra).toHaveBeenCalledTimes(1);
    expect(siteAra.mock.calls[0][0]).toBe('pilot');
    const basliklar = [...document.querySelectorAll('.ws-arama-grup-baslik')].map((e) => e.textContent);
    expect(basliklar[0]).toContain('Anasayfa');
    expect(basliklar[1]).toContain('Taslak');
    expect(document.querySelector('.ws-arama-konum').textContent).toContain('Hero › Butonlar › 1. öğe › Etiket');
    expect(document.querySelector('mark').textContent).toBe('Pilot');
    w.unmount();
  });

  it('kısa sorguda istek atmaz', async () => {
    const w = mount(SiteArama, { attachTo: document.body });
    await acVeAra(w, 'p');
    expect(siteAra).not.toHaveBeenCalled();
    w.unmount();
  });

  it('ok tuşu + Enter ile seçili sonucun editörüne gider', async () => {
    const w = mount(SiteArama, { attachTo: document.body });
    const girdi = await acVeAra(w, 'pilot');
    girdi.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }));
    girdi.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    await nextTick();
    expect(push).toHaveBeenCalledWith({ path: '/admin/web-sitesi/blog/2', query: { alan: 'baslik', q: 'pilot' } });
    expect(document.querySelector('.ws-arama')).toBeNull();
    w.unmount();
  });
});