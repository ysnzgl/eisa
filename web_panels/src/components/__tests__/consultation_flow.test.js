import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { get, markSessionReviewed, getDashboardSeries } = vi.hoisted(() => ({
  get: vi.fn(), markSessionReviewed: vi.fn(), getDashboardSeries: vi.fn(),
}));
vi.mock('../../services/api', () => ({ http: { get } }));
vi.mock('../../services/analytics', () => ({
  markSessionReviewed,
  completeSession: vi.fn(),
  getDashboardSeries,
}));

import SessionDetailModal from '../SessionDetailModal.vue';
import DashboardPeriodCharts from '../DashboardPeriodCharts.vue';

const session = { id: 41, qr_kodu: 'ABCDEFGH', status: 0, tamamlandi: true, onerilen_etken_madde_detaylari: [] };

describe('eczacı zorunlu danışmanlık modalı', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    get.mockReset().mockResolvedValue({ data: session });
    markSessionReviewed.mockReset().mockResolvedValue({ data: { ...session, status: 1 } });
  });

  it('detay yüklenince incelendi çağrısı yapar ve Escape/backdrop ile kapanmaz', async () => {
    const wrapper = mount(SessionDetailModal, { attachTo: document.body, props: { session, mandatory: true } });
    await flushPromises();
    expect(markSessionReviewed).toHaveBeenCalledWith(41);
    expect(document.body.querySelector('.eisa-modal-close')).toBeNull();
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    document.body.querySelector('.eisa-modal-backdrop').click();
    expect(wrapper.emitted('close')).toBeUndefined();
    wrapper.unmount();
  });

  it('admin salt-okunur modalında kapatma aksiyonlarını korur ve incelendi çağrısı yapmaz', async () => {
    const wrapper = mount(SessionDetailModal, { attachTo: document.body, props: { session, readonly: true } });
    await flushPromises();
    expect(markSessionReviewed).not.toHaveBeenCalled();
    expect(document.body.querySelector('.eisa-modal-close')).not.toBeNull();
    document.body.querySelector('.eisa-modal-close').click();
    expect(wrapper.emitted('close')).toHaveLength(1);
    wrapper.unmount();
  });
});

describe('dashboard dönem grafikleri', () => {
  it('dört ana grafik kartını gösterir', async () => {
    const days = [{ date:'2026-08-18', value:0 }];
    getDashboardSeries.mockResolvedValue({ data: {
      month:'2026-08', week_start:'2026-08-17', week_end:'2026-08-23',
      monthly_interactions:days, monthly_sales:days, weekly_interactions:days, weekly_sales:days,
      totals:{ monthly_interactions:0, monthly_sales:0, weekly_interactions:0, weekly_sales:0 },
    }});
    const wrapper = mount(DashboardPeriodCharts);
    await flushPromises();
    expect(wrapper.findAll('.period-card')).toHaveLength(4);
    expect(wrapper.text()).toContain('Aylık Gün Gün Satış');
    expect(wrapper.text()).toContain('Haftalık Gün Gün Etkileşim');
  });
});
