/**
 * Web Sitesi ekranları — duman (smoke) testi: her ekran sahte API verisiyle
 * hatasız çizilir ve temel içerik görünür. Sayfa Editörü'nde blok seçimi,
 * kirli (dirty) takibi ve 400 hata eşlemesi doğrulanır.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { defineComponent, h } from 'vue';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createMemoryHistory, RouterView } from 'vue-router';
import { createPinia, setActivePinia } from 'pinia';

vi.mock('vue-sonner', () => ({
  toast: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() }),
}));
vi.mock('../../../../services/api', () => ({
  http: { defaults: { baseURL: '' }, get: vi.fn(() => Promise.resolve({ data: [] })), post: vi.fn() },
  humanError: () => 'Sunucu hatası',
  login: vi.fn(),
  logout: vi.fn(),
}));

const TIPLER = [
  {
    tip: 'hero', ad: 'Hero', aciklama: 'Anasayfa girişi', ikon: 'Sparkle',
    alanlar: [
      { ad: 'baslik', etiket: 'Başlık', tur: 'metin', zorunlu: true, max_uzunluk: 160 },
      { ad: 'butonlar', etiket: 'Butonlar', tur: 'liste', max_adet: 3, alanlar: [{ ad: 'buton', etiket: 'Buton', tur: 'buton' }] },
    ],
  },
  { tip: 'sss', ad: 'SSS', ikon: 'ChatCircleText', alanlar: [{ ad: 'baslik', etiket: 'Başlık', tur: 'metin', zorunlu: true }] },
];
const SAYFA = {
  id: 1, slug: 'anasayfa', baslik: 'Anasayfa', durum: 'yayinda', sira: 0, surum: 4, taslak_degisti: false,
  seo_baslik: '', seo_aciklama: '', og_gorsel: null,
  bloklar: [
    { id: 'b_1', tip: 'hero', veri: { baslik: 'Reçete beklerken' }, sira: 0, gorunur: true, anchor_id: '' },
    { id: 'b_2', tip: 'sss', veri: { baslik: 'Sık Sorulanlar' }, sira: 1, gorunur: true, anchor_id: 'sss' },
  ],
};

const svc = vi.hoisted(() => ({}));
vi.mock('../../../../services/website', () => {
  const r = (v) => vi.fn(() => Promise.resolve(typeof v === 'function' ? v() : v));
  Object.assign(svc, {
    medyaUrl: (y) => y || '',
    apiBase: () => '',
    listSayfalar: r(() => [{ ...SAYFA, bloklar: undefined }, { id: 2, slug: 'teknoloji', baslik: 'Teknoloji', durum: 'taslak', taslak_degisti: true }]),
    getSayfa: r(() => JSON.parse(JSON.stringify(SAYFA))),
    listBlokTipleri: r(TIPLER),
    saveBloklar: vi.fn(),
    updateSayfa: vi.fn(),
    getMenuler: r({ header: [{ id: 1, etiket: 'Çözüm', link_tipi: 'bolum', sayfa_id: 1, bolum_anchor: 'sss', url: '', yeni_sekme: false, cta: false, aktif: true, cocuklar: [] }], footer: [], footer_alt: [] }),
    listBlogYazilari: r([{ id: 1, slug: 'pilot', baslik: 'Pilot süreci', durum: 'yayinda', kategori: null }]),
    listBlogKategorileri: r([{ id: 1, ad: 'Duyurular', slug: 'duyurular', sira: 0 }]),
    getBlogYazisi: r({ id: 1, slug: 'pilot', baslik: 'Pilot süreci', ozet: '', icerik_html: '<p>Merhaba</p>', etiketler: ['pilot'], durum: 'taslak', surum: 1 }),
    listMedya: r({ count: 1, results: [{ id: 1, yol: '/api/media/website/a.webp', alt: 'Kiosk', dosya_adi: 'a.webp' }] }),
    listBasvurular: r({ count: 1, results: [{ id: 1, tip: 'pilot', ad_soyad: 'Ayşe Yılmaz', eposta: 'a@b.c', durum: 'yeni' }], yeni_sayisi: 1 }),
    getAyarlar: r({ site_adi: 'e-isa', seo_baslik_sablonu: '%s | e-isa', sosyal_linkler: [{ platform: 'linkedin', url: 'https://www.linkedin.com/company/e-isa' }] }),
    getBasvuruOzet: r({ yeni: 1 }),
  });
  return svc;
});

const stubs = { ZenginMetinEditoru: true };

async function ekran(yol, bilesen) {
  setActivePinia(createPinia());
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/admin/web-sitesi', component: { render: () => null } },
      { path: '/admin/web-sitesi/:yol(.*)*', component: { render: () => null } },
      { path: '/test/:id?', component: bilesen },
    ],
  });
  router.push(yol);
  await router.isReady();
  const kok = defineComponent({ render: () => h(RouterView) });
  const wrapper = mount(kok, { global: { plugins: [router], stubs }, attachTo: document.body });
  await flushPromises();
  return { wrapper, router };
}

beforeEach(() => { document.body.innerHTML = ''; vi.clearAllMocks(); });

// İlk testler ağır bileşenleri (TipTap, vuedraggable) soğuk yükler; yüklü makinede 5 sn yetmeyebilir.
describe('Web Sitesi ekranları (smoke)', { timeout: 20000 }, () => {
  it('Sayfalar listesi: korumalı sayfanın silme butonu pasif, taslak_degisti göstergesi', async () => {
    const { wrapper } = await ekran('/test', (await import('../WebSitesiSayfalar.vue')).default);
    expect(wrapper.text()).toContain('Teknoloji');
    expect(wrapper.text()).toContain('Yayınlanmamış değişiklik');
    const satirlar = wrapper.findAll('tbody tr');
    const anasayfa = satirlar.find((s) => s.text().includes('Anasayfa'));
    expect(anasayfa.find('[aria-label="Sil"]').attributes('disabled')).toBeDefined();
  });

  it('Sayfa Editörü: bloklar listelenir, form çizilir, değişiklik kirli olur, 400 hatası bloğa işlenir', async () => {
    const { wrapper } = await ekran('/test/1', (await import('../SayfaEditoru.vue')).default);
    const ogeler = wrapper.findAll('.ws-blok-oge');
    expect(ogeler).toHaveLength(2);
    expect(ogeler[0].text()).toContain('Hero');
    expect(ogeler[0].text()).toContain('Reçete beklerken');
    expect(wrapper.find('.ws-editor-form').text()).toContain('Başlık');
    expect(wrapper.text()).not.toContain('Kaydedilmedi');

    await wrapper.find('.ws-editor-form [data-alan="baslik"] input').setValue('Yeni başlık');
    expect(wrapper.text()).toContain('Kaydedilmedi');

    svc.saveBloklar.mockRejectedValueOnce({ response: { status: 400, data: { bloklar: { 1: { baslik: ['Bu alan zorunludur.'] } } } } });
    const kaydet = wrapper.findAll('button').find((b) => b.text().includes('Taslağı Kaydet'));
    await kaydet.trigger('click');
    await flushPromises();
    expect(svc.saveBloklar).toHaveBeenCalledWith(1, 4, expect.any(Array));
    const gonderilen = svc.saveBloklar.mock.calls[0][2];
    expect(gonderilen[0]).toMatchObject({ id: 'b_1', tip: 'hero', gorunur: true });
    expect(gonderilen[0].veri.baslik).toBe('Yeni başlık');
    const ikinci = wrapper.findAll('.ws-blok-oge')[1];
    expect(ikinci.classes()).toContain('is-hatali');
    expect(ikinci.classes()).toContain('is-active');
    expect(wrapper.find('.ws-editor-form .ws-alan-hata').text()).toBe('Bu alan zorunludur.');
  });

  it('Sayfa Editörü: 409 çakışma bandı gösterilir', async () => {
    const { wrapper } = await ekran('/test/1', (await import('../SayfaEditoru.vue')).default);
    await wrapper.find('.ws-editor-form [data-alan="baslik"] input').setValue('Değişti');
    svc.saveBloklar.mockRejectedValueOnce({ response: { status: 409, data: {} } });
    await wrapper.findAll('button').find((b) => b.text().includes('Taslağı Kaydet')).trigger('click');
    await flushPromises();
    expect(wrapper.text()).toContain('Sürüm çakışması');
  });

  it.each([
    ['Menüler', () => import('../WebSitesiMenuler.vue'), 'Çözüm'],
    ['Blog', () => import('../BlogYazilar.vue'), 'Pilot süreci'],
    ['Blog editörü', () => import('../BlogYaziEditoru.vue'), '/blog/pilot'],
    ['Medya', () => import('../MedyaKutuphanesi.vue'), 'a.webp'],
    ['Başvurular', () => import('../Basvurular.vue'), 'Ayşe Yılmaz'],
    ['Site Ayarları', () => import('../SiteAyarlari.vue'), 'Sosyal Medya'],
  ])('%s ekranı çizilir', async (_ad, yukle, beklenen) => {
    const { wrapper } = await ekran('/test/1', (await yukle()).default);
    expect(wrapper.text()).toContain(beklenen);
  });
});
