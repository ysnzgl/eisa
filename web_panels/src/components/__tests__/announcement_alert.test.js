import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { get, post, put, push, success, error } = vi.hoisted(() => ({
  get: vi.fn(), post: vi.fn(), put: vi.fn(), push: vi.fn(), success: vi.fn(), error: vi.fn(),
}));
vi.mock('../../services/api', () => ({ http: { get, post, put, patch: vi.fn(), delete: vi.fn() } }));
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }));
vi.mock('vue-sonner', () => ({ toast: { success, error } }));

import DutyAlertModal from '../pharmacist/DutyAlertModal.vue';
import AnnouncementManagement from '../../views/admin/AnnouncementManagement.vue';

const general = (id, title) => ({
  id, kind: 'GENERAL', severity: 'INFO', title, message: `${title} mesajı`, action_label: '',
});

describe('eczacı duyuru kuyruğu', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    get.mockReset(); post.mockReset(); put.mockReset(); push.mockReset();
  });

  it('aktif genel duyuruyu yerleşim açılır açılmaz gösterir ve açık onaydan sonra sıradakine geçer', async () => {
    get.mockResolvedValue({ data: [general(1, 'İlk duyuru'), general(2, 'İkinci duyuru')] });
    post.mockResolvedValue({ data: {} });
    const wrapper = mount(DutyAlertModal, { attachTo: document.body });
    await flushPromises();

    expect(document.body.textContent).toContain('İlk duyuru');
    expect(document.body.textContent).not.toContain('İkinci duyuru');
    document.body.querySelector('.announcement-alert-actions .eisa-btn-cta').click();
    await flushPromises();

    expect(post).toHaveBeenCalledWith('/api/announcements/1/read/');
    expect(document.body.textContent).toContain('İkinci duyuru');
    wrapper.unmount();
  });

  it('okundu isteği başarısızsa duyuruyu kapatmaz', async () => {
    get.mockResolvedValue({ data: [general(3, 'Kalıcı duyuru')] });
    post.mockRejectedValue({ response: { data: { detail: 'Bağlantı hatası' } } });
    const wrapper = mount(DutyAlertModal, { attachTo: document.body });
    await flushPromises();
    document.body.querySelector('.announcement-alert-actions .eisa-btn-cta').click();
    await flushPromises();

    expect(document.body.textContent).toContain('Kalıcı duyuru');
    expect(document.body.textContent).toContain('Bağlantı hatası');
    wrapper.unmount();
  });

  it('yeniden mount edildiğinde aktif duyuruları sunucudan tekrar sorgular', async () => {
    get.mockResolvedValue({ data: [] });
    const first = mount(DutyAlertModal);
    await flushPromises();
    first.unmount();
    const second = mount(DutyAlertModal);
    await flushPromises();
    second.unmount();
    expect(get).toHaveBeenCalledTimes(2);
  });
});

describe('admin duyuru sunumu', () => {
  it('backend sistem anahtarını liste ve düzenleme modalında göstermez', async () => {
    get.mockImplementation((url) => {
      if (url === '/api/announcements/admin/') return Promise.resolve({ data: [{
        id: 9, kind: 'SYSTEM', system_key: 'DUTY_CURRENT_MONTH_MISSING', title: 'Nöbet bilgisi eksik',
        message: 'Takvimi tamamlayın.', action_label: 'Takvime Git', severity: 'WARNING', active: true,
      }] });
      return Promise.resolve({ data: [] });
    });
    const wrapper = mount(AnnouncementManagement, { attachTo: document.body });
    await flushPromises();
    expect(wrapper.text()).toContain('Sistem Duyurusu');
    expect(document.body.textContent).not.toContain('DUTY_CURRENT_MONTH_MISSING');

    await wrapper.get('.system-card').trigger('click');
    await flushPromises();
    expect(document.body.textContent).toContain('Sistem Duyurusunu Düzenle');
    expect(document.body.textContent).not.toContain('DUTY_CURRENT_MONTH_MISSING');
    wrapper.unmount();
  });
});
