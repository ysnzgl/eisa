import { mount, flushPromises } from '@vue/test-utils';
import { expect, it, vi } from 'vitest';
import GorevYonetimi from '../../views/admin/GorevYonetimi.vue';

const { get, post, patch } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }));
vi.mock('../../services/api', () => ({ http: { get, post, patch } }));
vi.mock('vue-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));
vi.mock('../../composables/useConfirm.js', () => ({ useConfirm: () => ({ confirm: vi.fn() }) }));

it('yükleme hatasından sonra aynı işe kalan dosyayı yükler', async () => {
  get.mockResolvedValue({ data: [] });
  const saved = { id: 9, baslik: 'Test', icerik: 'İçerik', dosyalar: [] };
  post.mockResolvedValueOnce({ data: saved }).mockRejectedValueOnce(new Error('offline'));
  patch.mockResolvedValue({ data: { ...saved, dosyalar: [] } });
  const wrapper = mount(GorevYonetimi, { global: {
    stubs: { GorevDosyalar: { name: 'GorevDosyalar', props: ['modelValue'], template: '<div class="file-stub" />' } },
  }, attachTo: document.body });
  try {
    await flushPromises();
    await wrapper.findAll('button').find(b => b.text().includes('Yeni İş')).trigger('click');
    const modal = document.body.querySelector('form');
    const title = modal.querySelector('input');
    title.value = 'Test';
    title.dispatchEvent(new Event('input', { bubbles: true }));
    const content = modal.querySelector('textarea');
    content.value = 'İçerik';
    content.dispatchEvent(new Event('input', { bubbles: true }));
    wrapper.findComponent({ name: 'GorevDosyalar' }).vm.$emit('update:modelValue', [new File(['%PDF-1.7'], 'test.pdf')]);
    modal.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await flushPromises();
    expect(post).toHaveBeenCalledTimes(2);
    expect(document.body.querySelector('form')).not.toBeNull();
    post.mockResolvedValueOnce({ data: { id: 2, ad: 'test.pdf' } });
    modal.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await flushPromises();
    expect(patch).toHaveBeenCalledWith('/api/is-takip/gorevler/9/', expect.any(Object));
    expect(post).toHaveBeenLastCalledWith('/api/is-takip/gorevler/9/dosyalar/', expect.any(FormData));
    expect(post.mock.calls.filter(([url]) => url === '/api/is-takip/gorevler/')).toHaveLength(1);
    expect(document.body.querySelector('form')).toBeNull();
  } finally {
    wrapper.unmount();
    document.body.innerHTML = '';
  }
});
