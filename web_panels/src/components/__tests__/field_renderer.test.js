/**
 * FieldRenderer — şemadan dinamik form üretimi (liste / iç içe alan / zorunlu alan).
 * Ağır bileşenler (TipTap, medya diyaloğu) stub'lanır.
 */
import { describe, it, expect, vi } from 'vitest';
import { defineComponent, h, reactive, nextTick } from 'vue';
import { mount } from '@vue/test-utils';

vi.mock('../../services/api', () => ({
  http: { defaults: { baseURL: '' }, get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() },
  humanError: () => 'hata',
}));

import FieldRenderer from '../website/FieldRenderer.vue';
import BlokFormu from '../website/BlokFormu.vue';

const stubs = { ZenginMetinEditoru: true, MedyaSecici: true, MedyaKutuphanesiDialog: true };

const KARTLAR = {
  ad: 'kartlar', etiket: 'Kartlar', tur: 'liste', min_adet: 1, max_adet: 2,
  alanlar: [
    { ad: 'baslik', etiket: 'Kart başlığı', tur: 'metin', zorunlu: true, max_uzunluk: 40 },
    { ad: 'ikon', etiket: 'İkon', tur: 'ikon', zorunlu: true, varsayilan: 'Sparkle' },
    {
      ad: 'maddeler', etiket: 'Maddeler', tur: 'liste', max_adet: 3,
      alanlar: [{ ad: 'metin', etiket: 'Madde', tur: 'metin', zorunlu: true }],
    },
  ],
};

/** Gerçek editördeki gibi reaktif bir `veri` üzerinde v-model ile kullanır. */
function sarmala(alan, baslangic) {
  const state = reactive({ deger: baslangic, hata: null });
  const Sarmalayici = defineComponent({
    setup() {
      return () => h(FieldRenderer, {
        alan,
        modelValue: state.deger,
        hata: state.hata,
        'onUpdate:modelValue': (v) => { state.deger = v; },
      });
    },
  });
  const wrapper = mount(Sarmalayici, { global: { stubs }, attachTo: document.body });
  return { wrapper, state };
}

describe('FieldRenderer', () => {
  it('metin alanı: zorunlu işareti, maxlength ve değer güncelleme', async () => {
    const { wrapper, state } = sarmala({ ad: 'baslik', etiket: 'Başlık', tur: 'metin', zorunlu: true, max_uzunluk: 160 }, '');
    expect(wrapper.find('label').text()).toContain('Başlık');
    expect(wrapper.find('.ws-zorunlu').exists()).toBe(true);
    const input = wrapper.find('input[type="text"]');
    expect(input.attributes('maxlength')).toBe('160');
    await input.setValue('Merhaba');
    expect(state.deger).toBe('Merhaba');
    expect(wrapper.find('.ws-sayac').text()).toBe('7/160');
  });

  it('zorunlu alan hatası gösterilir ve alan işaretlenir', async () => {
    const { wrapper, state } = sarmala({ ad: 'baslik', etiket: 'Başlık', tur: 'metin', zorunlu: true }, '');
    state.hata = ['Bu alan zorunludur.'];
    await nextTick();
    expect(wrapper.find('.ws-alan').classes()).toContain('ws-alan--hatali');
    expect(wrapper.find('.ws-alan-hata').text()).toBe('Bu alan zorunludur.');
  });

  it('liste: öğe ekler (max_adet sınırı), iç içe alanları çizer ve siler (min_adet sınırı)', async () => {
    const { wrapper, state } = sarmala(KARTLAR, [{ baslik: 'İlk', ikon: 'Star', maddeler: [] }]);
    expect(wrapper.findAll('.ws-liste-oge')).toHaveLength(1);
    // İç içe alan etiketleri çizildi (ilk öğe açık başlar).
    expect(wrapper.text()).toContain('Kart başlığı');
    expect(wrapper.text()).toContain('Maddeler');

    // min_adet=1 → tek öğe silinemez
    const silBtn = wrapper.find('.ws-liste-oge [aria-label="Sil"]');
    expect(silBtn.attributes('disabled')).toBeDefined();

    // Öğe ekle → varsayılanlarla yeni öğe
    // Dış listenin ekle butonu DOM'da sondadır (iç içe 'Maddeler' listesinin butonu öğe içindedir).
    const disEkle = () => wrapper.findAll('.ws-liste-ekle').at(-1);
    const ekle = disEkle();
    await ekle.trigger('click');
    expect(state.deger).toHaveLength(2);
    expect(state.deger[1]).toEqual({ baslik: '', ikon: 'Sparkle', maddeler: [] });

    // max_adet=2 → artık eklenemez
    await nextTick();
    const ekle2 = disEkle();
    expect(ekle2.attributes('disabled')).toBeDefined();

    // İç içe öğenin metin alanı yerinde güncellenir
    const ikinciOgeInput = wrapper.findAll('.ws-liste-oge')[1].find('input[type="text"]');
    await ikinciOgeInput.setValue('İkinci');
    expect(state.deger[1].baslik).toBe('İkinci');

    // Artık 2 öğe var → silinebilir
    await wrapper.findAll('.ws-liste-oge')[0].find('[aria-label="Sil"]').trigger('click');
    expect(state.deger).toHaveLength(1);
    expect(state.deger[0].baslik).toBe('İkinci');
  });

  it('liste: iç içe öğe hatası ilgili alanda gösterilir', async () => {
    const { wrapper, state } = sarmala(KARTLAR, [{ baslik: '', ikon: 'Star', maddeler: [] }]);
    state.hata = { 0: { baslik: ['Bu alan zorunludur.'] } };
    await nextTick();
    expect(wrapper.find('.ws-liste-oge').classes()).toContain('is-hatali');
    expect(wrapper.find('.ws-liste-oge-govde .ws-alan--hatali .ws-alan-hata').text()).toBe('Bu alan zorunludur.');
  });

  it('secim (≤4 seçenek) segment kontrolü tipli değeri korur', async () => {
    const { wrapper, state } = sarmala({
      ad: 'sutun', etiket: 'Sütun', tur: 'secim', secenekler: [2, 3, 4].map((n) => ({ deger: n, etiket: String(n) })),
    }, 3);
    const btnlar = wrapper.findAll('.ws-segment button');
    expect(btnlar).toHaveLength(3);
    expect(btnlar[1].classes()).toContain('is-active');
    await btnlar[2].trigger('click');
    expect(state.deger).toBe(4);
  });

  it('bool ve sayi alanları', async () => {
    const b = sarmala({ ad: 'goster', etiket: 'Tabloyu göster', tur: 'bool' }, false);
    await b.wrapper.find('input[type="checkbox"]').setValue(true);
    expect(b.state.deger).toBe(true);
    const s = sarmala({ ad: 'adet', etiket: 'Adet', tur: 'sayi', min: 1, max: 6 }, 3);
    await s.wrapper.find('input[type="number"]').setValue('5');
    expect(s.state.deger).toBe(5);
    await s.wrapper.find('input[type="number"]').setValue('');
    expect(s.state.deger).toBeNull();
  });
});

describe('BlokFormu', () => {
  it('şemadaki tüm alanları ve anchor alanını üretir; anchor küçük harfe çevrilir', async () => {
    const blok = reactive({ _key: 'k1', tip: 'sss', veri: { baslik: 'SSS', sorular: [] }, gorunur: true, anchor_id: '' });
    const tanim = {
      tip: 'sss', ad: 'SSS', ikon: 'ChatCircleText',
      alanlar: [
        { ad: 'baslik', etiket: 'Başlık', tur: 'metin', zorunlu: true },
        { ad: 'sorular', etiket: 'Sorular', tur: 'liste', min_adet: 1, alanlar: [{ ad: 'soru', etiket: 'Soru', tur: 'metin', zorunlu: true }] },
      ],
    };
    const wrapper = mount(BlokFormu, { props: { blok, tipTanimi: tanim }, global: { stubs } });
    expect(wrapper.findAll('.ws-alan[data-alan]')).toHaveLength(2);
    await wrapper.find('#anchor-k1').setValue('Sik Sorulan');
    expect(blok.anchor_id).toBe('sik-sorulan');
    await wrapper.find('[data-alan="baslik"] input').setValue('Sıkça Sorulanlar');
    expect(blok.veri.baslik).toBe('Sıkça Sorulanlar');
  });
});

describe('FieldRenderer — "Sitede ara" hedefi', () => {
  it('veri yolunu yazar ve hedefin bulunduğu kapalı liste öğesini açar', async () => {
    const { ref: vueRef } = await import('vue');
    const alan = { ad: 'kartlar', etiket: 'Kartlar', tur: 'liste', alanlar: [{ ad: 'metin', etiket: 'Metin', tur: 'metin' }] };
    const deger = [{ metin: 'a' }, { metin: 'b' }, { metin: 'hedef' }]; // 2'den fazla → öğeler kapalı başlar
    const w = mount(FieldRenderer, {
      props: { alan, modelValue: deger },
      global: { stubs, provide: { wsHedefYol: vueRef('kartlar.2.metin') } },
    });
    await nextTick();
    expect(w.find('[data-alan-yolu="kartlar"]').exists()).toBe(true);
    const govdeler = w.findAll('.ws-liste-oge-govde');
    expect(govdeler[0].attributes('style') || '').toContain('display: none');
    expect(govdeler[2].attributes('style') || '').not.toContain('display: none');
    expect(w.find('[data-alan-yolu="kartlar.2.metin"] input').element.value).toBe('hedef');
  });
});