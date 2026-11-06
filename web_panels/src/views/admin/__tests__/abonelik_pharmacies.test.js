import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { get, error } = vi.hoisted(() => ({ get: vi.fn(), error: vi.fn() }));
vi.mock('../../../services/api', () => ({ http: { get } }));
vi.mock('vue-router', () => ({ useRoute: () => ({ query: {} }) }));
vi.mock('vue-sonner', () => ({ toast: { error, success: vi.fn() } }));

import AbonelikYonetimi from '../AbonelikYonetimi.vue';
import EisaLookup from '../../../components/shared/EisaLookup.vue';
import SozlesmeForm from '../../../components/shared/SozlesmeForm.vue';

const pharmacies = [
  { id: 7, ad: 'Merkez Eczanesi', il_adi: 'İstanbul', ilce_adi: 'Kadıköy' },
  { id: 12, ad: 'Sahil Eczanesi', il_adi: 'İzmir', ilce_adi: 'Konak' },
];
let wrapper;

function mountPage({ realMatbu = false } = {}) {
  wrapper = mount(AbonelikYonetimi, {
    attachTo: document.body,
    global: { stubs: { SozlesmeForm: true, SozlesmeMatbu: !realMatbu, EczanePicker: true } },
  });
  return wrapper;
}

async function openCreate() {
  const button = wrapper.findAll('button').find((b) => b.text().includes('Yeni Sözleşme'));
  await button.trigger('click');
  await flushPromises();
  return wrapper.getComponent(EisaLookup);
}

beforeEach(() => {
  get.mockReset();
  error.mockReset();
  get.mockImplementation((url) => Promise.resolve({ data: url === '/api/pharmacies/' ? pharmacies : [] }));
});

afterEach(() => {
  wrapper?.unmount();
  document.body.innerHTML = '';
});

describe('Yeni Sözleşme eczane seçimi', () => {
  it('görüntüle ikonundan doğru sözleşme metnini açar, kapatır ve başka sözleşmeye geçer', async () => {
    const contracts = [7, 12].map(id => ({ id, eczane_ad: `Eczane ${id}`, tur: 'STANDART',
      durum: 'AKTIF', etkin_durum: 'AKTIF', kalan_gun: 100, cihaz_planlari: [] }));
    get.mockImplementation(url => Promise.resolve({ data:
      url === '/api/abonelik/sozlesmeler/' ? contracts
        : url.endsWith('/metin/') ? { html: `<h1>Sözleşme metni ${url.includes('/7/') ? 7 : 12}</h1>` } : [],
    }));
    mountPage({ realMatbu: true });
    await flushPromises();
    const buttons = wrapper.findAll('button[aria-label="Sözleşmeyi Görüntüle"]');
    await buttons[0].trigger('click');
    await flushPromises();
    expect(get).toHaveBeenCalledWith('/api/abonelik/sozlesmeler/7/metin/');
    expect(document.body.querySelector('.matbu-body').textContent).toContain('Sözleşme metni 7');
    document.body.querySelector('.eisa-modal-close').click();
    await flushPromises();
    expect(document.body.querySelector('.sozlesme-matbu')).toBeNull();
    await buttons[1].trigger('click');
    await flushPromises();
    expect(get).toHaveBeenCalledWith('/api/abonelik/sozlesmeler/12/metin/');
    expect(document.body.querySelector('.matbu-body').textContent).toContain('Sözleşme metni 12');
    expect(document.body.querySelector('.matbu-body').textContent).not.toContain('Sözleşme metni 7');
  });

  it('eklenen cihaz planına tanımlı cihaz KDV oranını kopyalar', async () => {
    const form = { tur: 'STANDART', cihaz_kdv_orani: 10, cihaz_planlari: [], baslangic_tarihi: '2026-11-03' };
    const component = mount(SozlesmeForm, { props: { form } });
    await component.get('.sf-add-plan').trigger('click');
    expect(form.cihaz_planlari[0].cihaz_kdv_orani).toBe(10);
    form.cihaz_planlari[0].cihaz_kdv_orani = 0;
    await component.get('.sf-add-plan').trigger('click');
    expect(form.cihaz_planlari[0].cihaz_kdv_orani).toBe(0);
    expect(form.cihaz_planlari[1].cihaz_kdv_orani).toBe(10);
    component.unmount();
  });

  it('yeni sözleşmede güncel fiyat ve KDV varsayılanlarını doldurur', async () => {
    let amount = '5200.00';
    get.mockImplementation((url) => Promise.resolve({ data: url === '/api/abonelik/fiyatlar/aktif/'
      ? { abonelik_bedeli: amount, abonelik_kdv_orani: 20, cihaz_kdv_orani: 10, iptal_ceza_orani: '3.00' }
      : [],
    }));
    mountPage();
    await flushPromises();
    amount = '5500.00';
    await openCreate();
    const form = wrapper.getComponent(SozlesmeForm).props('form');
    expect(form.aylik_kullanim_bedeli).toBe('5500.00');
    expect(form.kdv_orani).toBe(20);
    expect(form.cihaz_kdv_orani).toBe(10);
    expect(form.iptal_ceza_orani).toBe('3.00');
  });

  it('ıslak imzada tarih boş olsa da bekliyor göstermez, dijital durumları korur', async () => {
    const base = { eczane: 7, eczane_ad: 'Test Eczanesi', tur: 'STANDART', durum: 'AKTIF',
      etkin_durum: 'AKTIF', kalan_gun: 100, cihaz_planlari: [] };
    get.mockImplementation((url) => Promise.resolve({ data:
      url === '/api/abonelik/sozlesmeler/' ? [
        { ...base, id: 1, imza_tipi: 'ISLAK', eczaci_onay_tarihi: null },
        { ...base, id: 2, imza_tipi: 'DIJITAL', eczaci_onay_tarihi: null },
        { ...base, id: 3, imza_tipi: 'DIJITAL', eczaci_onay_tarihi: '2026-11-03T00:00:00Z' },
      ] : [],
    }));
    mountPage();
    await flushPromises();
    const rows = wrapper.findAll('tbody tr');
    expect(rows[0].text()).toContain('Islak imzalı');
    expect(rows[0].text()).not.toContain('Onay bekliyor');
    expect(rows[1].text()).toContain('Onay bekliyor');
    expect(rows[2].text()).toContain('Onaylandı');
  });

  it.each(['array', 'paginated'])('%s API yanıtından eczaneleri yükler, arar ve seçer', async (format) => {
    get.mockImplementation((url) => Promise.resolve({
      data: url === '/api/pharmacies/'
        ? (format === 'array' ? pharmacies : { results: pharmacies })
        : [],
    }));
    mountPage();
    await flushPromises();
    const lookup = await openCreate();
    expect(get).toHaveBeenCalledWith('/api/pharmacies/');
    expect(lookup.props('options')).toHaveLength(2);

    await lookup.get('.lookup-trigger').trigger('click');
    await lookup.get('input').setValue('Kadıköy');
    const items = lookup.findAll('.lookup-item');
    expect(items).toHaveLength(1);
    expect(items[0].text()).toContain('Merkez Eczanesi');
    await items[0].trigger('click');
    expect(lookup.props('modelValue')).toBe(7);
    expect(lookup.get('.lookup-selected').text()).toContain('Merkez Eczanesi');
    expect(error).not.toHaveBeenCalled();
  });

  it('yükleme hatasını bildirir ve modal açılırken yeniden dener', async () => {
    get.mockImplementation((url) => url === '/api/pharmacies/'
      ? Promise.reject(new Error('unavailable'))
      : Promise.resolve({ data: [] }));
    mountPage();
    await flushPromises();
    expect(error).toHaveBeenCalledWith('Eczaneler yüklenemedi. Lütfen tekrar deneyin.');
    get.mockImplementation((url) => Promise.resolve({ data: url === '/api/pharmacies/' ? pharmacies : [] }));
    const lookup = await openCreate();
    await flushPromises();
    expect(lookup.props('options')).toHaveLength(2);
  });
});
