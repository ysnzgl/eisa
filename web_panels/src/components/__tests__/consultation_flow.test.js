import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { get, markSessionReviewed, getDashboardSeries, push } = vi.hoisted(() => ({
  get: vi.fn(), markSessionReviewed: vi.fn(), getDashboardSeries: vi.fn(), push: vi.fn(),
}));
vi.mock('../../services/api', () => ({ http: { get } }));
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }));
vi.mock('../../services/analytics', () => ({
  markSessionReviewed,
  completeSession: vi.fn(),
  getDashboardSeries,
}));

import SessionDetailModal from '../SessionDetailModal.vue';
import DashboardPeriodCharts from '../DashboardPeriodCharts.vue';
import adminDashboardSource from '../../views/admin/Dashboard.vue?raw';
import pharmacistDashboardSource from '../../views/pharmacist/Dashboard.vue?raw';

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
  beforeEach(() => {
    push.mockReset();
    getDashboardSeries.mockReset();
  });

  it('dört ana grafik kartını gösterir', async () => {
    const days = [{ date:'2026-08-18', value:4, pending:2, recommended:3, sold:1, not_sold:1 }];
    getDashboardSeries.mockResolvedValue({ data: {
      month:'2026-08', week_start:'2026-08-17', week_end:'2026-08-23',
      monthly_interactions:days, monthly_sales:days, weekly_interactions:days, weekly_sales:days,
      totals:{ monthly_interactions:0, monthly_sales:0, weekly_interactions:0, weekly_sales:0 },
    }});
    const wrapper = mount(DashboardPeriodCharts);
    await flushPromises();
    expect(wrapper.findAll('.period-card')).toHaveLength(4);
    expect(wrapper.text()).toContain('Aylık Satış');
    expect(wrapper.text()).toContain('Haftalık Etkileşim');
    expect(wrapper.text()).toContain('3 Önerilen');
    expect(wrapper.text()).toContain('1 Satılan');
    expect(wrapper.text()).toContain('2 Bekleyen');
    expect(wrapper.text()).toContain('1 Satış Yapılan');
    expect(wrapper.text()).toContain('1 Satış Yapılmayan');
    expect(getDashboardSeries).toHaveBeenCalledTimes(4);
    expect(wrapper.findAll('.period-nav button')).toHaveLength(6);
    expect(wrapper.find('.fa-calendar-day').exists()).toBe(true);
    expect(wrapper.find('.fa-calendar-week').exists()).toBe(true);
    expect(wrapper.text()).not.toContain('Önceki Ay');
  });

  it('etkileşim gününü QR sekmesine, satış gününü satışlar sekmesine yönlendirir', async () => {
    const days = [{ date:'2026-08-18', value:2 }];
    getDashboardSeries.mockResolvedValue({ data: {
      month:'2026-08', week_start:'2026-08-17', week_end:'2026-08-23',
      monthly_interactions:days, monthly_sales:days, weekly_interactions:days, weekly_sales:days,
      totals:{ monthly_interactions:2, monthly_sales:2, weekly_interactions:2, weekly_sales:2 },
    }});
    const wrapper = mount(DashboardPeriodCharts, { props: { filters: { eczane_id: 7 } } });
    await flushPromises();

    await wrapper.findAll('.period-card')[0].get('.period-bar-cell').trigger('click');
    expect(push).toHaveBeenLastCalledWith({
      path: '/admin/kiosk-activities',
      query: { tab: 'sessions', start_date: '2026-08-18', end_date: '2026-08-18', eczane_id: 7 },
    });
    await wrapper.findAll('.period-card')[1].get('.period-bar-cell').trigger('click');
    expect(push).toHaveBeenLastCalledWith({
      path: '/admin/kiosk-activities',
      query: { tab: 'sales', start_date: '2026-08-18', end_date: '2026-08-18', eczane_id: 7 },
    });
  });

  it('iki dashboard da yalnızca ortak dört dönem grafiğini kullanır', () => {
    expect(adminDashboardSource).not.toContain('Kiosk Etkileşimleri');
    expect(adminDashboardSource.match(/<DashboardPeriodCharts/g)).toHaveLength(1);
    expect(pharmacistDashboardSource.match(/<DashboardPeriodCharts/g)).toHaveLength(1);
    expect(adminDashboardSource.match(/<DashboardAsyncDonut/g)).toHaveLength(4);
    expect(adminDashboardSource).toContain('Önerilen Etken Madde Dağılımı');
    expect(adminDashboardSource).toContain('<EczanePicker');
    expect(adminDashboardSource).toContain('selectedProvince');
  });
});
