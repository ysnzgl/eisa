import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { get, markSessionReviewed, completeSession, getDashboardSeries, push } = vi.hoisted(() => ({
  get: vi.fn(), markSessionReviewed: vi.fn(), completeSession: vi.fn(), getDashboardSeries: vi.fn(), push: vi.fn(),
}));
vi.mock('../../services/api', () => ({ http: { get } }));
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }));
vi.mock('../../services/analytics', () => ({
  markSessionReviewed,
  completeSession,
  getDashboardSeries,
}));

import SessionDetailModal from '../SessionDetailModal.vue';
import QrSessionCard from '../QrSessionCard.vue';
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

describe('satış yapılmadı sonucunu satışa dönüştürme', () => {
  const notSold = {
    ...session, status: 3, sold: false, danisma_tamamlandi: true,
    danisma_notu: 'İlk görüşme notu',
    onerilen_etken_madde_detaylari: [{ id: 7, ad: 'Önerilen Etken', satildi: false, source: 'RECOMMENDED' }],
  };

  beforeEach(() => {
    get.mockReset().mockResolvedValue({ data: [] });
    completeSession.mockReset();
  });

  it('önerilen etken maddeyi seçip mevcut notla satış kaydedebilir', async () => {
    const sold = { ...notSold, status: 2, sold: true };
    completeSession.mockResolvedValue({ data: sold });
    const wrapper = mount(QrSessionCard, { props: { session: notSold } });
    await flushPromises();
    expect(wrapper.get('textarea').element.value).toBe('İlk görüşme notu');
    expect(wrapper.find('.eisa-btn-danger').exists()).toBe(false);
    await wrapper.get('.qsc-ing-label').trigger('click');
    await wrapper.get('.eisa-btn-success').trigger('click');
    await flushPromises();
    expect(completeSession).toHaveBeenCalledWith(41, 'İlk görüşme notu', 'sold', [7]);
    expect(wrapper.emitted('completed')[0][0]).toMatchObject({ status: 2, sold: true });
    await wrapper.setProps({ session: sold });
    expect(wrapper.find('textarea').exists()).toBe(false);
    wrapper.unmount();
  });

  it('kayıt hatasında seçim ve notu koruyup yeniden denemeye izin verir', async () => {
    completeSession.mockRejectedValue({ response: { data: { detail: 'Satış kaydedilemedi.' } } });
    const wrapper = mount(QrSessionCard, { props: { session: notSold } });
    await flushPromises();
    await wrapper.get('.qsc-ing-label').trigger('click');
    await wrapper.get('.eisa-btn-success').trigger('click');
    await flushPromises();
    expect(wrapper.text()).toContain('Satış kaydedilemedi.');
    expect(wrapper.get('.qsc-ing-label').classes()).toContain('qsc-ing-label--selected');
    expect(wrapper.get('textarea').element.value).toBe('İlk görüşme notu');
    expect(wrapper.emitted('completed')).toBeUndefined();
    wrapper.unmount();
  });

  it.each([
    { session: notSold, readonly: true },
    { session: { ...notSold, status: 2, sold: true } },
  ])('salt okunur ve satış yapılmış kayıtlarda formu gizler: %j', (props) => {
    const wrapper = mount(QrSessionCard, { props });
    expect(wrapper.find('textarea').exists()).toBe(false);
    expect(wrapper.find('.eisa-btn-success').exists()).toBe(false);
    expect(wrapper.find('.qsc-ing-label').exists()).toBe(false);
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
