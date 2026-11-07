import { mount, flushPromises } from '@vue/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import GorevDosyalar from '../GorevDosyalar.vue';

const { get, error } = vi.hoisted(() => ({ get: vi.fn(), error: vi.fn() }));
vi.mock('../../services/api', () => ({ http: { get } }));
vi.mock('vue-sonner', () => ({ toast: { error } }));

let wrapper;
afterEach(() => { wrapper?.unmount(); vi.clearAllMocks(); document.body.innerHTML = ''; });

describe('İş dosyaları', () => {
  it('DOCX önizleme metnini HTML olarak çalıştırmadan gösterir', async () => {
    get.mockResolvedValue({ data: { paragraflar: ['<img src=x onerror=alert(1)>'] } });
    wrapper = mount(GorevDosyalar, { props: {
      gorevId: 12, dosyalar: [{ id: 4, ad: 'örnek.docx', boyut: 100 }],
    }, attachTo: document.body });
    await wrapper.findAll('button').find(b => b.text() === 'Önizle').trigger('click');
    await flushPromises();
    expect(get).toHaveBeenCalledWith('/api/is-takip/gorevler/12/dosyalar/4/', { params: { onizleme: 'metin' } });
    expect(document.body.textContent).toContain('<img src=x onerror=alert(1)>');
    expect(document.body.querySelector('img')).toBeNull();
  });

  it('eski DOC için indirme sunar', () => {
    wrapper = mount(GorevDosyalar, { props: {
      gorevId: 12, dosyalar: [{ id: 4, ad: 'eski.doc', boyut: 100 }],
    } });
    expect(wrapper.text()).toContain('İndir');
    expect(wrapper.text()).not.toContain('Önizle');
  });

  it('desteklenmeyen ve büyük dosyaları kuyruğa eklemez', async () => {
    wrapper = mount(GorevDosyalar, { props: { modelValue: [] } });
    const input = wrapper.find('input');
    const big = new File(['a'], 'big.pdf');
    Object.defineProperty(big, 'size', { value: 26 * 1024 * 1024 });
    const good = new File(['%PDF-1.7'], 'test.pdf');
    Object.defineProperty(input.element, 'files', { value: [new File(['x'], 'bad.exe'), big, good] });
    await input.trigger('change');
    expect(error).toHaveBeenCalledTimes(2);
    expect(wrapper.emitted('update:modelValue').at(-1)[0]).toEqual([good]);
  });
});
